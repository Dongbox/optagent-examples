from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExactBackendName, ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def main() -> None:
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
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            required_backend=ExactBackendName.CP_SAT_NATIVE,
            strict_backend=True,
            phases=[PhaseConfig(name="cp_sat_job_shop", solver=OrchestratorSolver.CP_SAT, budget_iterations=30)],
        ),
    )

    print_solution(
        "small job shop solved by CP-SAT native backend",
        result.final_solution,
        extra={
            "machine_sequences": {
                "machine_a": machine_a.node_id,
                "machine_b": machine_b.node_id,
            }
        },
    )


if __name__ == "__main__":
    main()
