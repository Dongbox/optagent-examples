from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, solve
# from optagent import OptxConfig, solve_optx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> tuple[object, dict[str, object]]:
    builder = ModelBuilder(metadata={"case": "assignment_optx"})
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
    return builder.freeze(), {"profit": profit}


def main() -> None:
    program, data = build_model()
    solution = solve(program, time_limit_s=10.0, seed=7, threads=1, log_level="on")
    # To use the OptX exact solver instead, replace the line above with:
    # solution = solve_optx(program, config=OptxConfig(time_limit_s=10.0, threads=1))
    print_solution("assignment solved by unified solve", solution, extra=data)


if __name__ == "__main__":
    main()
