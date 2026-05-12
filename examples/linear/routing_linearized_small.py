from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


DIST = {
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


def main() -> None:
    builder = ModelBuilder(metadata={"case": "routing_linearized_small"})
    nodes = range(4)
    edges = {
        (i, j): builder.int_var(default=0, lb=0, ub=1, name=f"x_{i}_{j}")
        for i in nodes
        for j in nodes
        if i != j
    }
    order = {
        i: builder.int_var(default=i, lb=0, ub=3, name=f"u_{i}")
        for i in nodes
    }

    for i in nodes:
        outgoing = [edges[(i, j)] for j in nodes if i != j]
        incoming = [edges[(j, i)] for j in nodes if i != j]
        builder.constraint(builder.sum(*outgoing) == 1, name=f"leave_{i}")
        builder.constraint(builder.sum(*incoming) == 1, name=f"enter_{i}")

    builder.constraint(order[0] == 0, name="anchor_depot")
    for i in range(1, 4):
        builder.constraint(order[i] >= 1, name=f"lower_u_{i}")
        builder.constraint(order[i] <= 3, name=f"upper_u_{i}")

    for i in range(1, 4):
        for j in range(1, 4):
            if i == j:
                continue
            builder.constraint(order[i] - order[j] + (4 * edges[(i, j)]) <= 3, name=f"mtz_{i}_{j}")

    builder.minimize(
        builder.sum(*((edges[(i, j)] * DIST[(i, j)]) for (i, j) in edges)),
        name="tour_length",
    )
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            phases=[PhaseConfig(name="milp_routing", solver=OrchestratorSolver.MILP, budget_iterations=30)],
        ),
    )

    print_solution(
        "small routing model solved with linearized MILP formulation",
        result.final_solution,
        extra={"distance_matrix": {f"{i}->{j}": cost for (i, j), cost in DIST.items()}},
    )


if __name__ == "__main__":
    main()
