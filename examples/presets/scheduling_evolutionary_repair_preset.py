from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

from optagent import BuiltInStrategyPreset, ModelBuilder, Orchestrator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


SELECTED_PRESET = BuiltInStrategyPreset.SCHEDULING_EVOLUTIONARY_REPAIR
# Other built-in options for this example:
# - BuiltInStrategyPreset.SCHEDULING_FOCUS
# - BuiltInStrategyPreset.SCHEDULING_HYBRID_CP_SAT


def build_program():
    builder = ModelBuilder(metadata={"case": "scheduling_evolutionary_repair_preset"})

    machine_a = builder.sequence_var(size=3, default=[0, 1, 2], name="machine_a")
    machine_b = builder.sequence_var(size=3, default=[0, 1, 2], name="machine_b")

    a0 = builder.interval_var(start=0, length=2, lb_start=0, ub_start=12, lb_length=2, ub_length=2, name="a0")
    a1 = builder.interval_var(start=0, length=3, lb_start=0, ub_start=12, lb_length=3, ub_length=3, name="a1")
    a2 = builder.interval_var(start=0, length=2, lb_start=0, ub_start=12, lb_length=2, ub_length=2, name="a2")
    b0 = builder.interval_var(start=0, length=1, lb_start=0, ub_start=12, lb_length=1, ub_length=1, name="b0")
    b1 = builder.interval_var(start=0, length=2, lb_start=0, ub_start=12, lb_length=2, ub_length=2, name="b1")
    b2 = builder.interval_var(start=0, length=3, lb_start=0, ub_start=12, lb_length=3, ub_length=3, name="b2")

    builder.constraint(builder.no_overlap(machine_a, a0, a1, a2), name="machine_a_no_overlap")
    builder.constraint(builder.no_overlap(machine_b, b0, b1, b2), name="machine_b_no_overlap")
    builder.constraint(builder.precedence(a0, b0, lag=0), name="job0_flow")
    builder.constraint(builder.precedence(a1, b1, lag=0), name="job1_flow")
    builder.constraint(builder.precedence(a2, b2, lag=0), name="job2_flow")
    builder.minimize(
        builder.max(builder.interval_end(b0), builder.interval_end(b1), builder.interval_end(b2)),
        name="makespan",
    )
    return builder.freeze(), {"machine_a": machine_a.node_id, "machine_b": machine_b.node_id}


def main() -> None:
    program, machine_sequences = build_program()
    result = Orchestrator().run(program, preset=SELECTED_PRESET)
    print_solution(
        "small scheduling model solved by scheduling_evolutionary_repair",
        result.final_solution,
        extra={
            "selected_preset": result.selected_preset_name,
            "selected_preset_source": result.selected_preset_source,
            "machine_sequences": machine_sequences,
            "heuristic_subphase_traces": [asdict(trace) for trace in result.heuristic_subphase_traces],
            "evolutionary_generation_traces": [asdict(trace) for trace in result.evolutionary_generation_traces],
        },
    )


if __name__ == "__main__":
    main()
