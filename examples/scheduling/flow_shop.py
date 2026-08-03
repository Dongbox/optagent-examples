from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> tuple[object, int]:
    builder = ModelBuilder(metadata={"case": "flow_shop"})
    seq = builder.permutation_var(universe=3, default=[2, 1, 0], name="machine_order")
    cut = builder.interval_var(start=0, length=2, lb_start=0, ub_start=5, lb_length=2, ub_length=2, name="cut")
    drill = builder.interval_var(start=0, length=3, lb_start=0, ub_start=6, lb_length=3, ub_length=3, name="drill")
    pack = builder.interval_var(start=0, length=1, lb_start=0, ub_start=8, lb_length=1, ub_length=1, name="pack")

    builder.constraint(builder.no_overlap(seq, cut, drill, pack), name="machine_capacity")
    builder.constraint(builder.precedence(cut, drill, lag=0), name="cut_before_drill")
    builder.constraint(builder.precedence(drill, pack, lag=0), name="drill_before_pack")
    builder.minimize(builder.interval_end(pack), name="makespan")
    return builder.freeze(), seq.node_id


def main() -> None:
    program, sequence_id = build_model()
    solution = solve(program, time_limit_s=10.0, seed=7, threads=1, log_level="on")
    print_solution("flow shop solved by unified solve", solution, extra={"permutation_variable": sequence_id})


if __name__ == "__main__":
    main()
