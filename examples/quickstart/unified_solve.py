from __future__ import annotations

from optagent import ModelBuilder, solve


def build_model() -> ModelBuilder:
    builder = ModelBuilder(metadata={"case": "quickstart_unified_solve"})
    choose_a = builder.bool_var(name="choose_a")
    choose_b = builder.bool_var(name="choose_b")
    builder.constraint(choose_a + choose_b <= 1, name="capacity")
    builder.maximize(choose_a * 3 + choose_b * 2, name="profit")
    return builder


def main() -> None:
    solution = solve(build_model(), time_limit_s=10, seed=7, threads=1, log_level="off")
    print({"status": solution.status.value, "objective": solution.objective_values})


if __name__ == "__main__":
    main()
