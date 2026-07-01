from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExternalCallbackContext, GaConfig, ModelBuilder, solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


DIST = [
    [0, 4, 7, 3],
    [4, 0, 2, 6],
    [7, 2, 0, 5],
    [3, 6, 5, 0],
]


def route_cost(order: list[int]) -> int:
    tour = order + [order[0]]
    return sum(DIST[tour[index]][tour[index + 1]] for index in range(len(order)))


def main() -> None:
    builder = ModelBuilder(metadata={"case": "tsp_blackbox_ga"})
    route = builder.sequence_var(size=4, default=[3, 2, 1, 0], name="route")

    def route_cost_ctx(ctx: ExternalCallbackContext) -> int:
        return route_cost([int(index) for index in ctx.value(route)])

    builder.minimize(builder.external_call(route_cost_ctx, name="route_cost"), name="tour_length")
    solution = solve(
        builder.freeze(),
        strategy=GaConfig(
            max_iterations=80,
            population_size=6,
            mutation_count=2,
            mutation_portfolio=("sequence_two_opt", "sequence_block_move", "random_swap"),
        ),
        seed=11,
        time_limit_s=10.0,
        trace_output="summary",
    )
    print_solution("small TSP blackbox route solved by GaConfig", solution, extra={"distance_matrix": DIST})


if __name__ == "__main__":
    main()
