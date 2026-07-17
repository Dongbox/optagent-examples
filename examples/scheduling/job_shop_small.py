from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> tuple[object, dict[str, int]]:
    builder = ModelBuilder(metadata={"case": "job_shop_small"})
    machine_a = builder.sequence_var(size=2, default=[0, 1], name="machine_a")
    machine_b = builder.sequence_var(size=2, default=[0, 1], name="machine_b")

    job1_a = builder.interval_var(start=0, length=2, lb_start=0, ub_start=8, lb_length=2, ub_length=2, name="job1_a")
    job1_b = builder.interval_var(start=0, length=3, lb_start=0, ub_start=10, lb_length=3, ub_length=3, name="job1_b")
    job2_b = builder.interval_var(start=0, length=2, lb_start=0, ub_start=8, lb_length=2, ub_length=2, name="job2_b")
    job2_a = builder.interval_var(start=0, length=2, lb_start=0, ub_start=10, lb_length=2, ub_length=2, name="job2_a")

    builder.constraint(builder.no_overlap(machine_a, job1_a, job2_a), name="machine_a_capacity")
    builder.constraint(builder.no_overlap(machine_b, job1_b, job2_b), name="machine_b_capacity")
    builder.constraint(builder.precedence(job1_a, job1_b, lag=0), name="job1_flow")
    builder.constraint(builder.precedence(job2_b, job2_a, lag=0), name="job2_flow")
    builder.minimize(builder.max(builder.interval_end(job1_b), builder.interval_end(job2_a)), name="makespan")
    return builder.freeze(), {"machine_a": machine_a.node_id, "machine_b": machine_b.node_id}


def main() -> None:
    program, sequence_ids = build_model()
    solution = solve(program, time_limit_s=10.0, seed=7, threads=1, log_level="on")
    print_solution("small job shop solved by unified solve", solution, extra={"machine_sequences": sequence_ids})


if __name__ == "__main__":
    main()
