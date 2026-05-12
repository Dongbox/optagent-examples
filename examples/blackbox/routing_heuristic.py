from __future__ import annotations

from pathlib import Path
import sys

from optagent import HeuristicStrategy, ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def route_cost(order: list[int]) -> int:
    distances = {
        (0, 1): 4,
        (0, 2): 7,
        (0, 3): 3,
        (1, 0): 4,
        (1, 2): 2,
        (1, 3): 6,
        (2, 0): 7,
        (2, 1): 2,
        (2, 3): 5,
        (3, 0): 3,
        (3, 1): 6,
        (3, 2): 5,
    }
    return sum(distances[(order[index - 1], order[index])] for index in range(1, len(order)))


def main() -> None:
    builder = ModelBuilder(metadata={"case": "blackbox_route_heuristic"})
    route = builder.sequence_var(size=4, default=[3, 2, 1, 0], name="route")
    builder.minimize(builder.external_call(route_cost, route, name="route_cost"), name="route_obj")
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            total_budget_iterations=40,
            phases=[
                PhaseConfig(
                    name="heuristic_blackbox",
                    solver=OrchestratorSolver.HEURISTIC,
                    budget_iterations=40,
                    strategy=HeuristicStrategy.TABU,
                )
            ],
        ),
    )

    print_solution(
        "blackbox route optimization solved by heuristic",
        result.final_solution,
        extra={"sequence_variable": route.node_id},
    )


if __name__ == "__main__":
    main()
