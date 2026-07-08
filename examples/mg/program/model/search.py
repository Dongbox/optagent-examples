from __future__ import annotations

"""OptAgent search configuration and execution for MG sequencing.

This module is the solving layer. It maps coarse MG search modes to the current
solve-first OptAgent API, runs one or more mode/seed attempts, and returns the
best sequence with a compact metadata trace. It does not read/write SQLite and
does not build parity or migration reports; those responsibilities live in
`reports.py`.
"""

from dataclasses import asdict, dataclass
import logging
from time import perf_counter
from typing import Any, Iterable

from optagent import (
    AlnsConfig,
    GaConfig,
    StrategyConfig,
    UnifiedSolution,
    solve,
)

from .model import build_mg_program
from .rules import group_rule_costs, score_sequence
from mg.program.scripts.preprocess.data import MGCase


DEFAULT_SEARCH_MODES = ("ga", "polish", "evolutionary")
OPTAGENT_LOGGER_NAME = "OptAgent"


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


@dataclass(frozen=True)
class MGStrategyRunConfig:
    """Current solve-first configuration for one MG mode.

    The progress/logging fields are retained as data so existing example
    reports can show the selected mode and operator-facing logging intent.
    """

    mode: str
    seed: int
    budget_iterations: int
    generation_limit: int
    strategy: StrategyConfig
    log_level: str = "off"
    trace_output: str = "summary"
    progress_logging: bool = False
    progress_log_level: int | None = None
    progress_mode: str = ""
    heuristic_cost_logging: bool = True
    heuristic_cost_logging_policy: str = "improved"


def build_mg_config(
    *,
    mode: str,
    budget_iterations: int,
    generation_limit: int,
    seed: int,
    progress_logging: bool = False,
    progress_log_level: int | None = None,
    progress_callback: Any | None = None,
    heuristic_cost_logging: bool = True,
    heuristic_cost_logging_policy: str = "improved",
) -> MGStrategyRunConfig:
    """Map an MG search mode to a compact solve-first OptAgent config.

    The modes are deliberately coarse because the production `main.py` should
    not expose low-level tuning flags. Diagnostics can still call this
    module directly with custom budgets when comparing profiles.
    """

    if mode == "polish":
        strategy: StrategyConfig = AlnsConfig(
            max_iterations=budget_iterations,
            destroy_count=2,
        )
    else:
        strategy = GaConfig(
            max_iterations=max(budget_iterations, generation_limit),
            population_size=8,
            mutation_portfolio=("sequence_two_opt", "sequence_block_move", "random_swap"),
            local_improvement_strategy="lns",
            local_improvement_top_k=1,
        )
    return MGStrategyRunConfig(
        mode=mode,
        seed=seed,
        budget_iterations=budget_iterations,
        generation_limit=generation_limit,
        strategy=strategy,
        log_level="summary" if progress_logging else "off",
        trace_output="summary",
        progress_logging=progress_logging,
        progress_log_level=progress_log_level,
        progress_mode=mode,
        heuristic_cost_logging=heuristic_cost_logging,
        heuristic_cost_logging_policy=heuristic_cost_logging_policy,
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


def _sequence_from_result(result: UnifiedSolution, sequence_node_id: int) -> list[int]:
    """Extract the final sequence variable value from an OptAgent result."""

    return [int(index) for index in result.variable_values[sequence_node_id]]


def _solution_metadata(result: UnifiedSolution) -> dict[str, Any]:
    metadata = dict(result.diagnostics)
    metadata.update(
        {
            "strategy": result.result.strategy,
            "iterations": result.result.iterations,
            "termination_reason": result.result.termination_reason,
        }
    )
    return metadata


def _run_score_curve(
    *,
    mode: str,
    seed: int,
    baseline_cost: float,
    result: UnifiedSolution,
    final_cost: float,
) -> list[dict[str, Any]]:
    curve = [
        {
            "mode": mode,
            "seed": seed,
            "step": 0,
            "source": "baseline",
            "score": baseline_cost,
        }
    ]
    step = 1
    for trace in _metadata_trace(result):
        curve.append(
            {
                "mode": mode,
                "seed": seed,
                "step": step,
                "source": "phase",
                "phase_name": trace.get("phase_name", mode),
                "solver_name": trace.get("solver_name", result.solver_name),
                "score": trace.get("best_score", trace.get("score", final_cost)),
                "feasible": trace.get("feasible", result.feasible),
            }
        )
        step += 1
    curve.append(
        {
            "mode": mode,
            "seed": seed,
            "step": step,
            "source": "final",
            "score": final_cost,
            "feasible": bool(result.feasible),
        }
    )
    return curve


def _metadata_trace(result: UnifiedSolution) -> list[dict[str, Any]]:
    trace = result.diagnostics.get("trace")
    if isinstance(trace, list):
        return [dict(entry) for entry in trace if isinstance(entry, dict)]
    return []


def _solver_trace_summary(result: UnifiedSolution, *, mode: str, final_cost: float) -> list[dict[str, Any]]:
    traces = _metadata_trace(result)
    if traces:
        return traces
    metadata = _solution_metadata(result)
    return [
        {
            "phase_name": mode,
            "solver_name": result.solver_name,
            "status": result.status.value,
            "feasible": result.feasible,
            "score": final_cost,
            "strategy": metadata.get("strategy", mode),
            "iterations": metadata.get("iterations"),
            "termination_reason": metadata.get("termination_reason"),
        }
    ]


def _summarize_run(
    *,
    case: MGCase,
    baseline_cost: float,
    mode: str,
    seed: int,
    result: UnifiedSolution,
    sequence: list[int],
    runtime_seconds: float,
) -> MGSearchRun:
    """Score the final candidate again and attach solver trace metadata."""

    score = score_sequence(case, sequence)
    metadata = _solution_metadata(result)
    return MGSearchRun(
        mode=mode,
        seed=seed,
        total_cost=score.total_cost,
        improvement_vs_baseline=round(baseline_cost - score.total_cost, 6),
        feasible=bool(result.feasible),
        status=str(result.status.value),
        runtime_seconds=round(runtime_seconds, 6),
        active_count=len(score.active_sequence),
        inactive_count=len(score.inactive_sequence),
        sequence=list(sequence),
        sequence_head=list(sequence[:30]),
        grouped_rule_costs=group_rule_costs(score.breakdown),
        solver_trace_count=max(1, int(metadata.get("trace_entry_count", len(_metadata_trace(result))) or 0)),
        generation_trace_count=int(metadata.get("generations", 0) or 0),
        heuristic_subphase_trace_count=0,
        solver_traces=_solver_trace_summary(result, mode=mode, final_cost=score.total_cost),
        generation_trace_tail=[],
        mutation_successes=dict(metadata.get("mutation_successes", {}))
        if isinstance(metadata.get("mutation_successes"), dict)
        else {},
        mutation_trials=dict(metadata.get("mutation_trials", {}))
        if isinstance(metadata.get("mutation_trials"), dict)
        else {},
    )


def solve_mg_sequence(
    case: MGCase,
    *,
    modes: Iterable[str] = DEFAULT_SEARCH_MODES,
    seeds: Iterable[int] = (11,),
    budget_iterations: int = 80,
    generation_limit: int = 8,
    use_constructive_default: bool = False,
    progress_logging: bool = False,
    progress_log_level: int | None = None,
    heuristic_cost_logging: bool = True,
    heuristic_cost_logging_policy: str = "improved",
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
    baseline_sequence = list(built.program.default_variable_values()[built.sequence_node_id])
    baseline_score = score_sequence(case, baseline_sequence)

    runs: list[MGSearchRun] = []
    score_curve: list[dict[str, Any]] = []
    for mode in selected_modes:
        for seed in selected_seeds:
            # Each mode/seed pair is an independent solve attempt over the same
            # frozen OptAgent program. This makes comparison deterministic and
            # keeps production best-run selection auditable.
            if progress_logging:
                logging.getLogger(OPTAGENT_LOGGER_NAME).info(
                    "OptAgent baseline cost mode=%s seed=%s score=%s",
                    mode,
                    seed,
                    baseline_score.total_cost,
                )
            start = perf_counter()
            config = build_mg_config(
                mode=mode,
                budget_iterations=budget_iterations,
                generation_limit=generation_limit,
                seed=seed,
                progress_logging=progress_logging,
                progress_log_level=progress_log_level,
                progress_callback=None,
                heuristic_cost_logging=heuristic_cost_logging,
                heuristic_cost_logging_policy=heuristic_cost_logging_policy,
            )
            result = solve(
                built.program,
                strategy=config.strategy,
                max_iterations=config.budget_iterations,
                seed=config.seed,
                log_level=config.log_level,
                trace_output=config.trace_output,
            )
            runtime_seconds = perf_counter() - start
            sequence = _sequence_from_result(result, built.sequence_node_id)
            run = _summarize_run(
                case=case,
                baseline_cost=baseline_score.total_cost,
                mode=mode,
                seed=seed,
                result=result,
                sequence=sequence,
                runtime_seconds=runtime_seconds,
            )
            runs.append(run)
            run_curve = _run_score_curve(
                mode=mode,
                seed=seed,
                baseline_cost=baseline_score.total_cost,
                result=result,
                final_cost=run.total_cost,
            )
            score_curve.extend(run_curve)

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
        "score_curve": score_curve,
    }
