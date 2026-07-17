from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, solve
# from optagent import OptxConfig, solve_optx

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
    solution = solve(program, time_limit_s=10.0, seed=7, threads=1, log_level="on")
    # To use the OptX exact solver instead, replace the line above with:
    # solution = solve_optx(program, config=OptxConfig(time_limit_s=10.0, threads=1))
    print_solution("0/1 knapsack solved by unified solve", solution, extra=data)


if __name__ == "__main__":
    main()
