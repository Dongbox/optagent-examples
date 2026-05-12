from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExactBackendName, ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def main() -> None:
    builder = ModelBuilder(
        metadata={"case": "knapsack_mathopt"},
        solve_config={"preferred_backend": "mathopt_mp", "mathopt_solver_type": "GSCIP"},
    )
    weights = [2, 3, 4, 5, 9]
    values = [3, 4, 8, 8, 10]
    picks = [builder.int_var(default=0, lb=0, ub=1, name=f"pick_{idx}") for idx in range(len(weights))]

    total_weight = builder.sum(*((pick * weight) for pick, weight in zip(picks, weights)))
    total_value = builder.sum(*((pick * value) for pick, value in zip(picks, values)))

    builder.constraint(total_weight <= 10, name="capacity")
    builder.maximize(total_value, name="profit")
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            required_backend=ExactBackendName.MATHOPT_MP,
            strict_backend=True,
            phases=[PhaseConfig(name="mathopt_knapsack", solver=OrchestratorSolver.MILP, budget_iterations=20)],
        ),
    )

    print_solution(
        "0/1 knapsack solved by MathOpt bridge",
        result.final_solution,
        extra={
            "weights": weights,
            "values": values,
        },
    )


if __name__ == "__main__":
    main()
