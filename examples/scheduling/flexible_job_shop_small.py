from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, SchedulingModel, solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def build_model() -> object:
    builder = ModelBuilder(metadata={"case": "flexible_job_shop_small"})
    schedule = SchedulingModel(builder, horizon=30)

    machine_a = schedule.unary_resource("machine_a")
    machine_b = schedule.unary_resource("machine_b")
    shared_operator = schedule.cumulative_resource("shared_operator", capacity=1)

    cutting = schedule.task("cutting")
    cutting.alternative(resource=machine_a, duration=3, requirements={shared_operator: 1})
    cutting.alternative(resource=machine_b, duration=4, requirements={shared_operator: 1})
    cutting.exactly_one_alternative()

    drilling = schedule.task("drilling")
    drilling.alternative(resource=machine_a, duration=4, requirements={shared_operator: 1})
    drilling.alternative(resource=machine_b, duration=2, requirements={shared_operator: 1})
    drilling.exactly_one_alternative()

    packing = schedule.task("packing")
    packing.alternative(resource=machine_b, duration=2, requirements={shared_operator: 1})

    machine_a.no_overlap()
    machine_b.no_overlap()
    shared_operator.cumulative()
    schedule.chain([cutting, drilling, packing])
    builder.minimize(schedule.makespan(), name="makespan")
    schedule.validate()
    return builder.freeze()


def main() -> None:
    solution = solve(build_model(), time_limit_s=10.0, seed=7, threads=1, log_level="on")
    print_solution("flexible job shop solved by SchedulingModel and unified solve", solution)


if __name__ == "__main__":
    main()
