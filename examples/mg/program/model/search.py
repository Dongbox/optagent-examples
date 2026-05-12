from __future__ import annotations

"""OptAgent search configuration and execution for MG sequencing.

This module is the solving layer. It converts MG search modes into OptAgent
orchestrator configs, runs one or more mode/seed attempts, and returns the best
sequence with solver traces. It does not read/write SQLite and does not build
parity or migration reports; those responsibilities live in `reports.py`.
"""

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Iterable

from optagent import (
    EvolutionaryConfig,
    HeuristicOrchestrationConfig,
    HeuristicPhaseConfig,
    HeuristicPhaseKind,
    HeuristicStrategy,
    HeuristicTerminationConfig,
    HeuristicTerminationMode,
    LocalImprovementTrigger,
    MutationStrategy,
    Orchestrator,
    OrchestratorConfig,
    OrchestratorSolver,
    PhaseConfig,
)

from .model import build_mg_program
from .rules import group_rule_costs, score_sequence
from mg.program.scripts.preprocess.data import MGCase


DEFAULT_SEARCH_MODES = ("tabu", "polish", "evolutionary")


@dataclass(frozen=True)
class MGSearchRun:
    """Serializable summary for one mode/seed solve attempt."""

    mode: str
    seed: int
    total_cost: float
    improvement_vs_baseline: float
    feasible: bool
    status: str
    runtime_seconds: float
    active_count: int
    inactive_count: int
    sequence: list[int]
    sequence_head: list[int]
    grouped_rule_costs: dict[str, float]
    solver_trace_count: int
    generation_trace_count: int
    heuristic_subphase_trace_count: int
    solver_traces: list[dict[str, Any]]
    generation_trace_tail: list[dict[str, Any]]
    mutation_successes: dict[str, int]
    mutation_trials: dict[str, int]


def build_mg_config(
    *,
    mode: str,
    budget_iterations: int,
    generation_limit: int,
    seed: int,
) -> OrchestratorConfig:
    """Map an MG search mode to a compact OptAgent orchestration config.

    The modes are deliberately coarse because the production `main.py` should
    not expose low-level tuning flags. Migration diagnostics can still call this
    module directly with custom budgets when comparing profiles.
    """

    if mode == "tabu":
        # Fast local search around the warm-start sequence. This is the default
        # low-overhead replacement for the original GA's local improvement loop.
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="mg_sequence_tabu",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=budget_iterations,
                    strategy=HeuristicStrategy.TABU,
                )
            ],
        )
    if mode == "polish":
        # Intensify first, then diversify with a short annealing/LNS phase. This
        # is useful when the default sequence is plausible but has local defects.
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="mg_repair",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=budget_iterations,
                    heuristic_plan=HeuristicOrchestrationConfig(
                        phases=[
                            HeuristicPhaseConfig(
                                name="mg_tabu_intensify",
                                kind=HeuristicPhaseKind.INTENSIFY,
                                strategy=HeuristicStrategy.TABU,
                                enable_lns=True,
                                lns_every=5,
                                lns_destroy_count=2,
                                termination=HeuristicTerminationConfig(
                                    mode=HeuristicTerminationMode.UNIMPROVED_ITERATIONS,
                                    unimproved_iterations=max(16, budget_iterations // 2),
                                ),
                            ),
                            HeuristicPhaseConfig(
                                name="mg_annealing_diversify",
                                kind=HeuristicPhaseKind.DIVERSIFY,
                                strategy=HeuristicStrategy.ANNEALING,
                                enable_lns=True,
                                lns_every=5,
                                lns_destroy_count=3,
                                termination=HeuristicTerminationConfig(
                                    iteration_limit=max(8, budget_iterations // 4),
                                ),
                            ),
                        ]
                    ),
                )
            ],
        )
    # Evolutionary mode is the closest conceptual replacement for the APS GA:
    # maintain a population, use sequence mutations, and run a light tabu polish
    # only on improving candidates.
    return OrchestratorConfig(
        seed=seed,
        total_budget_iterations=budget_iterations,
        phases=[
            PhaseConfig(
                name="mg_sequence_evolutionary",
                solver=OrchestratorSolver.HEURISTIC,
                budget_iterations=budget_iterations,
                heuristic_plan=HeuristicOrchestrationConfig(
                    phases=[],
                    evolutionary_plan=EvolutionaryConfig(
                        population_size=16,
                        elite_size=4,
                        generation_limit=generation_limit,
                        stagnation_generations=4,
                        mutation=MutationStrategy.SEQUENCE_TWO_OPT,
                        mutation_portfolio=(
                            MutationStrategy.SEQUENCE_BLOCK_MOVE,
                            MutationStrategy.RUIN_AND_REPAIR,
                            MutationStrategy.RANDOM_SWAP,
                        ),
                        adaptive_mutation=True,
                        local_improvement_trigger=LocalImprovementTrigger.IMPROVING_ONLY,
                        local_improvement_top_k=1,
                        local_improvement_plan=HeuristicOrchestrationConfig(
                            phases=[
                                HeuristicPhaseConfig(
                                    name="mg_memetic_tabu_light",
                                    kind=HeuristicPhaseKind.INTENSIFY,
                                    strategy=HeuristicStrategy.TABU,
                                    termination=HeuristicTerminationConfig(
                                        mode=HeuristicTerminationMode.UNIMPROVED_ITERATIONS,
                                        unimproved_iterations=12,
                                    ),
                                )
                            ]
                        ),
                    ),
                ),
            )
        ],
    )


def parse_csv_ints(value: str | Iterable[int]) -> list[int]:
    """Normalize seed inputs from either legacy comma strings or iterables."""

    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return [int(item) for item in items]
    return [int(item) for item in value]


def parse_csv_modes(value: str | Iterable[str]) -> list[str]:
    """Normalize and validate search mode inputs."""

    if isinstance(value, str):
        modes = [item.strip() for item in value.split(",") if item.strip()]
    else:
        modes = [str(item).strip() for item in value if str(item).strip()]
    invalid = [mode for mode in modes if mode not in DEFAULT_SEARCH_MODES]
    if invalid:
        raise ValueError(f"unsupported MG search mode(s): {', '.join(invalid)}")
    return modes


def _sequence_from_result(result: Any, sequence_node_id: int) -> list[int]:
    """Extract the final sequence variable value from an OptAgent result."""

    return [int(index) for index in result.final_solution.variable_values[sequence_node_id]]


def _trace_tail(traces: list[Any], *, limit: int = 3) -> list[dict[str, Any]]:
    return [asdict(trace) for trace in traces[-limit:]]


def _summarize_run(
    *,
    case: MGCase,
    baseline_cost: float,
    mode: str,
    seed: int,
    result: Any,
    sequence: list[int],
    runtime_seconds: float,
) -> MGSearchRun:
    """Score the final candidate again and attach solver trace metadata."""

    score = score_sequence(case, sequence)
    return MGSearchRun(
        mode=mode,
        seed=seed,
        total_cost=score.total_cost,
        improvement_vs_baseline=round(baseline_cost - score.total_cost, 6),
        feasible=bool(result.final_solution.feasible),
        status=str(result.final_solution.status.value),
        runtime_seconds=round(runtime_seconds, 6),
        active_count=len(score.active_sequence),
        inactive_count=len(score.inactive_sequence),
        sequence=list(sequence),
        sequence_head=list(sequence[:30]),
        grouped_rule_costs=group_rule_costs(score.breakdown),
        solver_trace_count=len(result.solver_traces),
        generation_trace_count=len(result.evolutionary_generation_traces),
        heuristic_subphase_trace_count=len(result.heuristic_subphase_traces),
        solver_traces=[asdict(trace) for trace in result.solver_traces],
        generation_trace_tail=_trace_tail(result.evolutionary_generation_traces),
        mutation_successes=dict(getattr(result, "mutation_successes", {})),
        mutation_trials=dict(getattr(result, "mutation_trials", {})),
    )


def solve_mg_sequence(
    case: MGCase,
    *,
    modes: Iterable[str] = DEFAULT_SEARCH_MODES,
    seeds: Iterable[int] = (11,),
    budget_iterations: int = 80,
    generation_limit: int = 8,
    use_constructive_default: bool = False,
) -> dict[str, Any]:
    """Run the actual OptAgent sequence search without report-only baselines."""

    selected_modes = parse_csv_modes(modes)
    selected_seeds = parse_csv_ints(seeds)
    if not selected_modes:
        raise ValueError("at least one search mode is required")
    if not selected_seeds:
        raise ValueError("at least one seed is required")

    built = build_mg_program(case, use_constructive_default=use_constructive_default)
    # The baseline is the frozen program's default state, normally sourced from
    # `t_process_output`. It gives every run a stable improvement reference.
    baseline_sequence = list(built.program.default_state().variable_values[built.sequence_node_id])
    baseline_score = score_sequence(case, baseline_sequence)

    runs: list[MGSearchRun] = []
    for mode in selected_modes:
        for seed in selected_seeds:
            # Each mode/seed pair is an independent solve attempt over the same
            # frozen OptAgent program. This makes comparison deterministic and
            # keeps production best-run selection auditable.
            start = perf_counter()
            result = Orchestrator().run(
                built.program,
                config=build_mg_config(
                    mode=mode,
                    budget_iterations=budget_iterations,
                    generation_limit=generation_limit,
                    seed=seed,
                ),
            )
            runtime_seconds = perf_counter() - start
            sequence = _sequence_from_result(result, built.sequence_node_id)
            runs.append(
                _summarize_run(
                    case=case,
                    baseline_cost=baseline_score.total_cost,
                    mode=mode,
                    seed=seed,
                    result=result,
                    sequence=sequence,
                    runtime_seconds=runtime_seconds,
                )
            )

    sorted_runs = sorted(runs, key=lambda run: (run.total_cost, run.runtime_seconds, run.mode, run.seed))
    best_run = sorted_runs[0]
    return {
        "case": case.summary(),
        "model": built.summary(),
        "search": {
            "modes": selected_modes,
            "seeds": selected_seeds,
            "budget_iterations": budget_iterations,
            "generation_limit": generation_limit,
            "constructive_default": use_constructive_default,
            "run_count": len(runs),
        },
        "baseline": {
            "sequence_source": "program default sequence",
            "total_cost": baseline_score.total_cost,
            "grouped_rule_costs": group_rule_costs(baseline_score.breakdown),
            "diagnostics": baseline_score.diagnostics,
            "sequence_head": list(baseline_sequence[:30]),
        },
        "best": asdict(best_run),
        "runs": [asdict(run) for run in sorted_runs],
    }
