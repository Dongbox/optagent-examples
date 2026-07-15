from __future__ import annotations

from optagent import SolutionStatus, solve_cpsat

from examples.scheduling.flexible_job_shop_small import build_model


def test_flexible_job_shop_example_solves() -> None:
    solution = solve_cpsat(build_model(), time_limit_s=10.0, workers=1)

    assert solution.status in {SolutionStatus.OPTIMAL, SolutionStatus.FEASIBLE}
    assert solution.feasible is True
