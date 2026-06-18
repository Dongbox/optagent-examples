from __future__ import annotations

from pathlib import Path
import sys

from optagent import MilpConfig, ModelBuilder, solve_milp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> tuple[object, dict[str, object]]:
    builder = ModelBuilder(metadata={"case": "knapsack_mathopt_external"})
    weights = [2, 3, 4, 5, 9]
    values = [3, 4, 8, 8, 10]
    picks = [builder.int_var(default=0, lb=0, ub=1, name=f"pick_{idx}") for idx in range(len(weights))]

    total_weight = builder.sum(*((pick * weight) for pick, weight in zip(picks, weights)))
    total_value = builder.sum(*((pick * value) for pick, value in zip(picks, values)))

    builder.constraint(total_weight <= 10, name="capacity")
    builder.maximize(total_value, name="profit")
    return builder.freeze(), {"weights": weights, "values": values}


def main() -> None:
    program, data = build_model()
    solution = solve_milp(
        program,
        config=MilpConfig(
            backend="mathopt_mp",
            time_limit_s=10.0,
        ),
    )
    print_solution("0/1 knapsack solved by external MathOpt MP backend", solution, extra=data)


if __name__ == "__main__":
    main()
