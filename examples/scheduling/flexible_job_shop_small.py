from __future__ import annotations

from pathlib import Path
import sys

from optagent import CpSatConfig, ModelBuilder, SchedulingModel, solve_cpsat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> object:
    builder = ModelBuilder(metadata={"case": "flexible_job_shop_small"})
    schedule = SchedulingModel(builder, horizon=30)

    machine_a = schedule.unary_resource("machine_a")
    machine_b = schedule.unary_resource("machine_b")
    shared_operator = schedule.cumulative_resource("shared_operator", capacity=1)

    cutting = schedule.task("cutting")
    cutting.alternative(resource=machine_a, duration=3, demands={shared_operator: 1})
    cutting.alternative(resource=machine_b, duration=4, demands={shared_operator: 1})
    schedule.exactly_one_alternative(cutting)

    drilling = schedule.task("drilling")
    drilling.alternative(resource=machine_a, duration=4, demands={shared_operator: 1})
    drilling.alternative(resource=machine_b, duration=2, demands={shared_operator: 1})
    schedule.exactly_one_alternative(drilling)

    packing = schedule.task("packing")
    packing.alternative(resource=machine_b, duration=2, demands={shared_operator: 1})

    machine_a.no_overlap()
    machine_b.no_overlap()
    shared_operator.cumulative()
    schedule.chain([cutting, drilling, packing])
    builder.minimize(schedule.makespan(), name="makespan")
    return schedule.apply()


def main() -> None:
    solution = solve_cpsat(
        build_model(),
        config=CpSatConfig(time_limit_s=10.0, workers=1),
    )
    print_solution("flexible job shop solved by SchedulingModel and CP-SAT", solution)


if __name__ == "__main__":
    main()
