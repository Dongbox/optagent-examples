from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExactBackendName, ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def main() -> None:
    builder = ModelBuilder(
        metadata={"case": "assignment_highs_native"},
        solve_config={"preferred_backend": "highs_native"},
    )

    profit = {
        "a_x": 8,
        "a_y": 6,
        "b_x": 7,
        "b_y": 9,
    }
    a_x = builder.int_var(default=0, lb=0, ub=1, name="a_x")
    a_y = builder.int_var(default=0, lb=0, ub=1, name="a_y")
    b_x = builder.int_var(default=0, lb=0, ub=1, name="b_x")
    b_y = builder.int_var(default=0, lb=0, ub=1, name="b_y")

    builder.constraint(a_x + a_y == 1, name="assign_worker_a")
    builder.constraint(b_x + b_y == 1, name="assign_worker_b")
    builder.constraint(a_x + b_x == 1, name="fill_job_x")
    builder.constraint(a_y + b_y == 1, name="fill_job_y")

    builder.maximize(
        (a_x * profit["a_x"]) + (a_y * profit["a_y"]) + (b_x * profit["b_x"]) + (b_y * profit["b_y"]),
        name="profit",
    )
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            required_backend=ExactBackendName.HIGHS_NATIVE,
            strict_backend=True,
            phases=[PhaseConfig(name="highs_assignment", solver=OrchestratorSolver.MILP, budget_iterations=20)],
        ),
    )

    print_solution(
        "assignment solved by native HiGHS backend",
        result.final_solution,
        extra={"profit": profit},
    )


if __name__ == "__main__":
    main()
