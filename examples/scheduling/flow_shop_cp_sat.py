from __future__ import annotations

from pathlib import Path
import sys

from optagent import ExactBackendName, ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def main() -> None:
    builder = ModelBuilder(metadata={"case": "flow_shop_cp_sat"})
    seq = builder.sequence_var(size=3, default=[2, 1, 0], name="machine_order")
    cut = builder.interval_var(start=0, length=2, lb_start=0, ub_start=5, lb_length=2, ub_length=2, name="cut")
    drill = builder.interval_var(start=0, length=3, lb_start=0, ub_start=6, lb_length=3, ub_length=3, name="drill")
    pack = builder.interval_var(start=0, length=1, lb_start=0, ub_start=8, lb_length=1, ub_length=1, name="pack")

    builder.constraint(builder.no_overlap(seq, cut, drill, pack), name="machine_capacity")
    builder.constraint(builder.precedence(cut, drill, lag=0), name="cut_before_drill")
    builder.constraint(builder.precedence(drill, pack, lag=0), name="drill_before_pack")
    builder.minimize(builder.interval_end(pack), name="makespan")
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            required_backend=ExactBackendName.CP_SAT_NATIVE,
            strict_backend=True,
            phases=[PhaseConfig(name="cp_sat_flow_shop", solver=OrchestratorSolver.CP_SAT, budget_iterations=20)],
        ),
    )

    print_solution(
        "flow shop scheduling solved by CP-SAT native backend",
        result.final_solution,
        extra={"sequence_variable": seq.node_id},
    )


if __name__ == "__main__":
    main()
