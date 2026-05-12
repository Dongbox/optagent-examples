from __future__ import annotations

from pathlib import Path
import sys

from optagent import BuiltInStrategyPreset, ModelBuilder, Orchestrator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


DIST = [
    [0, 4, 7, 3],
    [4, 0, 2, 6],
    [7, 2, 0, 5],
    [3, 6, 5, 0],
]

SELECTED_PRESET = BuiltInStrategyPreset.ROUTING_EVOLUTIONARY
# Other built-in options for this example:
# - BuiltInStrategyPreset.ROUTING_BLACKBOX
# - BuiltInStrategyPreset.ROUTING_MEMETIC


def route_cost(order: list[int]) -> int:
    tour = order + [order[0]]
    return sum(DIST[tour[index]][tour[index + 1]] for index in range(len(order)))


def build_program():
    builder = ModelBuilder(metadata={"case": "routing_blackbox_preset"})
    route = builder.sequence_var(size=4, default=[3, 2, 1, 0], name="route")
    builder.minimize(builder.external_call(route_cost, route, name="route_cost"), name="tour_length")
    return builder.freeze(), route.node_id


def main() -> None:
    program, route_node_id = build_program()
    result = Orchestrator().run(program, preset=SELECTED_PRESET)
    print_solution(
        "blackbox routing solved through a fixed built-in preset",
        result.final_solution,
        extra={
            "sequence_variable": route_node_id,
            "selected_preset": result.selected_preset_name,
            "selected_preset_source": result.selected_preset_source,
            "selected_preset_family": result.final_solution.metadata.get("selected_preset_family"),
            "selected_preset_objective": result.final_solution.metadata.get("selected_preset_objective"),
        },
    )


if __name__ == "__main__":
    main()
