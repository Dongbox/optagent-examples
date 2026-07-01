from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExternalCallbackContext, GaConfig, ModelBuilder, solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


DISTANCES = {
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


def route_cost(order: list[int]) -> int:
    return sum(DISTANCES[(order[index - 1], order[index])] for index in range(1, len(order)))


def main() -> None:
    builder = ModelBuilder()
    route = builder.sequence_var(size=4, default=[3, 2, 1, 0], name="route")

    def route_cost_ctx(ctx: ExternalCallbackContext) -> int:
        return route_cost([int(index) for index in ctx.value(route)])

    builder.minimize(builder.external_call(route_cost_ctx, name="route_cost"), name="route_obj")
    solution = solve(
        builder.freeze(),
        strategy=GaConfig(
            max_iterations=60,
            population_size=6,
            mutation_count=2,
            mutation_portfolio=("sequence_two_opt", "sequence_block_move", "random_swap"),
        ),
        seed=7,
        time_limit_s=10.0,
        trace_output="summary",
    )
    print_solution("blackbox route optimization solved by GaConfig", solution, extra={"sequence_variable": route.node_id})


if __name__ == "__main__":
    main()
