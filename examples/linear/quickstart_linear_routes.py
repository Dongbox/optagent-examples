from __future__ import annotations

from optagent import ModelBuilder, OptxConfig, solve, solve_optx


def build_model() -> ModelBuilder:
    builder = ModelBuilder(metadata={"case": "quickstart_linear_routes"})
    worker_a = builder.bool_var(name="worker_a")
    worker_b = builder.bool_var(name="worker_b")
    builder.constraint(worker_a + worker_b <= 1, name="capacity")
    builder.maximize(worker_a * 8 + worker_b * 6, name="profit")
    return builder


def main() -> None:
    heuristic_solution = solve(build_model(), time_limit_s=10, seed=7, threads=1, log_level="off")
    exact_solution = solve_optx(
        build_model(),
        config=OptxConfig(time_limit_s=10, threads=1),
    )
    print(
        {
            "solve": heuristic_solution.objective_values,
            "solve_optx": exact_solution.objective_values,
        }
    )


if __name__ == "__main__":
    main()
