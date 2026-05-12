from __future__ import annotations

from pathlib import Path
import sys

from optagent import BuiltInStrategyPreset, ModelBuilder, Orchestrator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


SELECTED_PRESET = BuiltInStrategyPreset.SCHEDULING_HYBRID_CP_SAT
# Other built-in options for this example:
# - BuiltInStrategyPreset.SCHEDULING_FOCUS
# - BuiltInStrategyPreset.SCHEDULING_MEMETIC_QUALITY


def build_program():
    builder = ModelBuilder(metadata={"case": "hybrid_production_preset"})

    demand_a = 4
    demand_b = 3
    due_date = 4

    line_sequence = builder.sequence_var(size=2, default=[0, 1], name="line_sequence")
    blend_a = builder.interval_var(start=0, length=2, lb_start=0, ub_start=8, lb_length=0, ub_length=4, name="blend_a")
    blend_b = builder.interval_var(start=0, length=1, lb_start=0, ub_start=8, lb_length=0, ub_length=3, name="blend_b")
    local_a = builder.int_var(default=2, lb=0, ub=4, name="local_a")
    local_b = builder.int_var(default=1, lb=0, ub=3, name="local_b")
    outsource_a = builder.int_var(default=2, lb=0, ub=4, name="outsource_a")
    outsource_b = builder.int_var(default=2, lb=0, ub=3, name="outsource_b")
    tardiness = builder.int_var(default=0, lb=0, ub=8, name="tardiness")

    builder.constraint(builder.no_overlap(line_sequence, blend_a, blend_b), name="single_blending_line")
    builder.constraint(local_a == builder.interval_length(blend_a), name="local_a_matches_blend_length")
    builder.constraint(local_b == builder.interval_length(blend_b), name="local_b_matches_blend_length")
    builder.constraint(local_a + outsource_a == demand_a, name="meet_demand_a")
    builder.constraint(local_b + outsource_b == demand_b, name="meet_demand_b")
    builder.constraint(
        tardiness >= builder.max(builder.interval_end(blend_a), builder.interval_end(blend_b)) - due_date,
        name="due_date_lateness",
    )
    builder.constraint(tardiness >= 0, name="tardiness_nonnegative")
    builder.minimize((outsource_a * 2) + (outsource_b * 3) + (tardiness * 4), name="total_plan_cost")
    return builder.freeze(), due_date


def main() -> None:
    program, due_date = build_program()
    result = Orchestrator().run(program, preset=SELECTED_PRESET)
    print_solution(
        "hybrid production planning solved through a fixed built-in preset",
        result.final_solution,
        extra={
            "due_date": due_date,
            "selected_preset": result.selected_preset_name,
            "selected_preset_source": result.selected_preset_source,
            "selected_preset_family": result.final_solution.metadata.get("selected_preset_family"),
            "selected_preset_objective": result.final_solution.metadata.get("selected_preset_objective"),
        },
    )


if __name__ == "__main__":
    main()
