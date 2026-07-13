from __future__ import annotations

from pathlib import Path
import sys
import json

from optagent import MilpConfig, ModelBuilder, solve_milp
from optagent.exact import exact_backend_registry

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
    optx_backend = exact_backend_registry()["optx"].backend
    if not optx_backend.is_available():
        print(
            json.dumps(
                {
                    "title": "assignment solved by internal OptX MP backend",
                    "status": "skipped",
                    "backend": "optx",
                    "reason": optx_backend.availability_error(),
                    "extra": data,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return
    solution = solve_milp(
        program,
        config=MilpConfig(
            backend="optx",
            time_limit_s=10.0,
        ),
    )
    print_solution("assignment solved by internal OptX MP backend", solution, extra=data)


if __name__ == "__main__":
    main()
