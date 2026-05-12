from __future__ import annotations

from optagent import (
    BuiltInStrategyPreset,
    EvolutionaryConfig,
    HeuristicOrchestrationConfig,
    HeuristicPhaseConfig,
    HeuristicPhaseKind,
    HeuristicStrategy,
    HeuristicTerminationConfig,
    HeuristicTerminationMode,
    LocalImprovementTrigger,
    MutationStrategy,
    OrchestratorConfig,
    OrchestratorSolver,
    PhaseConfig,
)


BLACKBOX_DEFAULT_PRESET = BuiltInStrategyPreset.SEQUENCE_EVOLUTIONARY
DAG_DEFAULT_PRESET = BuiltInStrategyPreset.SEQUENCE_EXACT
BLACKBOX_FAST_POLISH_THRESHOLD = 8
BLACKBOX_TARGETED_POLISH_THRESHOLD = 16


def choose_blackbox_preset_mode(*, objective: int) -> tuple[str, str]:
    if objective <= BLACKBOX_FAST_POLISH_THRESHOLD:
        return "fast_polish", "internal_constructive_target_reached_fast_polish"
    if objective <= BLACKBOX_TARGETED_POLISH_THRESHOLD:
        return "targeted_polish", "internal_constructive_midband_targeted_polish"
    return "preset", "no_internal_seed_default_preset"


def build_blackbox_config(*, mode: str, budget_iterations: int, generation_limit: int, seed: int) -> OrchestratorConfig:
    if mode == "targeted_polish":
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="steel_blackbox_targeted_polish",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=budget_iterations,
                    heuristic_plan=HeuristicOrchestrationConfig(
                        phases=[
                            HeuristicPhaseConfig(
                                name="sequence_tabu_break_intensify",
                                kind=HeuristicPhaseKind.INTENSIFY,
                                strategy=HeuristicStrategy.TABU,
                                restart_limit=2,
                                enable_lns=True,
                                lns_every=5,
                                lns_destroy_count=2,
                                termination=HeuristicTerminationConfig(
                                    mode=HeuristicTerminationMode.UNIMPROVED_ITERATIONS,
                                    unimproved_iterations=max(32, min(56, budget_iterations // 2)),
                                ),
                            ),
                            HeuristicPhaseConfig(
                                name="sequence_break_diversify",
                                kind=HeuristicPhaseKind.DIVERSIFY,
                                strategy=HeuristicStrategy.ANNEALING,
                                restart_limit=1,
                                enable_lns=True,
                                lns_every=4,
                                lns_destroy_count=3,
                                termination=HeuristicTerminationConfig(
                                    iteration_limit=max(16, min(28, budget_iterations // 4)),
                                ),
                            ),
                            HeuristicPhaseConfig(
                                name="sequence_tabu_finish",
                                kind=HeuristicPhaseKind.INTENSIFY,
                                strategy=HeuristicStrategy.TABU,
                                start_policy="best_global",
                                restart_limit=1,
                                enable_lns=True,
                                lns_every=5,
                                lns_destroy_count=2,
                                termination=HeuristicTerminationConfig(
                                    mode=HeuristicTerminationMode.UNIMPROVED_ITERATIONS,
                                    unimproved_iterations=max(24, min(48, budget_iterations // 3)),
                                ),
                            ),
                        ]
                    ),
                ),
            ],
        )
    if mode == "fast_polish":
        polish_budget = max(8, min(32, budget_iterations))
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=polish_budget,
            phases=[
                PhaseConfig(
                    name="steel_blackbox_fast_polish",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=polish_budget,
                    strategy=HeuristicStrategy.TABU,
                )
            ],
        )
    if mode == "tabu":
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="steel_blackbox_tabu",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=budget_iterations,
                    strategy=HeuristicStrategy.TABU,
                )
            ],
        )
    if mode == "preset":
        evolutionary_budget = max(24, min(48, budget_iterations // 3))
        polish_budget = max(16, budget_iterations - evolutionary_budget)
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="steel_blackbox_memetic_seeded",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=evolutionary_budget,
                    heuristic_plan=HeuristicOrchestrationConfig(
                        phases=[],
                        evolutionary_plan=EvolutionaryConfig(
                            population_size=12,
                            elite_size=3,
                            generation_limit=max(4, min(8, generation_limit)),
                            stagnation_generations=3,
                            mutation=MutationStrategy.SEQUENCE_TWO_OPT,
                            mutation_portfolio=(
                                MutationStrategy.SEQUENCE_BLOCK_MOVE,
                                MutationStrategy.RUIN_AND_REPAIR,
                                MutationStrategy.RANDOM_SWAP,
                            ),
                            adaptive_mutation=True,
                            island_count=2,
                            migration_interval=2,
                            migration_size=1,
                            local_improvement_trigger=LocalImprovementTrigger.IMPROVING_ONLY,
                            local_improvement_top_k=1,
                            local_improvement_plan=HeuristicOrchestrationConfig(
                                phases=[
                                    HeuristicPhaseConfig(
                                        name="sequence_tabu_seeded_intensify",
                                        kind=HeuristicPhaseKind.INTENSIFY,
                                        strategy=HeuristicStrategy.TABU,
                                        termination=HeuristicTerminationConfig(
                                            mode=HeuristicTerminationMode.UNIMPROVED_ITERATIONS,
                                            unimproved_iterations=16,
                                        ),
                                    )
                                ]
                            ),
                        ),
                    ),
                ),
                PhaseConfig(
                    name="steel_blackbox_tabu_polish",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=polish_budget,
                    strategy=HeuristicStrategy.TABU,
                ),
            ],
        )
    return OrchestratorConfig(
        seed=seed,
        total_budget_iterations=budget_iterations,
        phases=[
            PhaseConfig(
                name="steel_blackbox_evolutionary",
                solver=OrchestratorSolver.HEURISTIC,
                budget_iterations=budget_iterations,
                heuristic_plan=HeuristicOrchestrationConfig(
                    phases=[],
                    evolutionary_plan=EvolutionaryConfig(
                        population_size=24,
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
                                    name="sequence_tabu_memetic_light",
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


def build_dag_config(*, mode: str, budget_iterations: int, seed: int, coil_count: int) -> OrchestratorConfig:
    if mode == "constructive":
        heuristic_budget = max(48, budget_iterations)
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=heuristic_budget,
            phases=[
                PhaseConfig(
                    name="steel_sequence_constructive_tabu",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=heuristic_budget,
                    strategy=HeuristicStrategy.TABU,
                )
            ],
        )
    if mode == "exact":
        return OrchestratorConfig(
            seed=seed,
            total_budget_iterations=budget_iterations,
            phases=[
                PhaseConfig(
                    name="steel_sequence_exact",
                    solver=OrchestratorSolver.MILP,
                    budget_iterations=budget_iterations,
                    fallback_on_failure=False,
                    fallback_on_stall=False,
                )
            ],
        )
    if mode == "preset":
        if coil_count <= 80:
            return build_dag_config(
                mode="exact",
                budget_iterations=budget_iterations,
                seed=seed,
                coil_count=coil_count,
            )
        return build_dag_config(
            mode="constructive",
            budget_iterations=budget_iterations,
            seed=seed,
            coil_count=coil_count,
        )
    return OrchestratorConfig(
        seed=seed,
        total_budget_iterations=budget_iterations,
        phases=[
            PhaseConfig(
                name="steel_sequence_seed",
                solver=OrchestratorSolver.HEURISTIC,
                budget_iterations=max(16, budget_iterations // 4),
                strategy=HeuristicStrategy.TABU,
            ),
            PhaseConfig(
                name="steel_sequence_exact_refine",
                solver=OrchestratorSolver.MILP,
                budget_iterations=budget_iterations,
                fallback_on_failure=False,
                fallback_on_stall=False,
                warm_start=True,
            ),
        ],
    )
