from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

from optagent import (
    EvolutionaryConfig,
    HeuristicOrchestrationConfig,
    ModelBuilder,
    Orchestrator,
    OrchestratorConfig,
    OrchestratorSolver,
    PhaseConfig,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


DIST = [
    [0, 4, 7, 3],
    [4, 0, 2, 6],
    [7, 2, 0, 5],
    [3, 6, 5, 0],
]


def route_cost(order: list[int]) -> int:
    tour = order + [order[0]]
    return sum(DIST[tour[index]][tour[index + 1]] for index in range(len(order)))


def main() -> None:
    builder = ModelBuilder(metadata={"case": "tsp_evolutionary_small"})
    route = builder.sequence_var(size=4, default=[3, 2, 1, 0], name="route")
    builder.minimize(builder.external_call(route_cost, route, name="route_cost"), name="tour_length")
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            total_budget_iterations=24,
            phases=[
                PhaseConfig(
                    name="evolutionary_tsp_blackbox",
                    solver=OrchestratorSolver.HEURISTIC,
                    heuristic_plan=HeuristicOrchestrationConfig(
                        phases=[],
                        evolutionary_plan=EvolutionaryConfig(
                            population_size=6,
                            elite_size=2,
                            generation_limit=4,
                        ),
                    ),
                )
            ],
        ),
    )

    print_solution(
        "small TSP solved by evolutionary heuristic over a blackbox objective",
        result.final_solution,
        extra={
            "distance_matrix": DIST,
            "generation_traces": [asdict(trace) for trace in result.evolutionary_generation_traces],
        },
    )


if __name__ == "__main__":
    main()
