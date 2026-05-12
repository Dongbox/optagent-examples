from __future__ import annotations

from pathlib import Path
import sys

from optagent import ModelBuilder, Orchestrator, OrchestratorConfig, OrchestratorSolver, PhaseConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution


def main() -> None:
    builder = ModelBuilder(metadata={"case": "facility_location_small"})

    open_cost = {"north": 6, "south": 5}
    service_cost = {
        ("north", "alpha"): 2,
        ("north", "beta"): 4,
        ("north", "gamma"): 5,
        ("south", "alpha"): 3,
        ("south", "beta"): 2,
        ("south", "gamma"): 3,
    }

    open_north = builder.int_var(default=0, lb=0, ub=1, name="open_north")
    open_south = builder.int_var(default=0, lb=0, ub=1, name="open_south")

    assign_north_alpha = builder.int_var(default=0, lb=0, ub=1, name="assign_north_alpha")
    assign_north_beta = builder.int_var(default=0, lb=0, ub=1, name="assign_north_beta")
    assign_north_gamma = builder.int_var(default=0, lb=0, ub=1, name="assign_north_gamma")
    assign_south_alpha = builder.int_var(default=0, lb=0, ub=1, name="assign_south_alpha")
    assign_south_beta = builder.int_var(default=0, lb=0, ub=1, name="assign_south_beta")
    assign_south_gamma = builder.int_var(default=0, lb=0, ub=1, name="assign_south_gamma")

    builder.constraint(assign_north_alpha + assign_south_alpha == 1, name="serve_alpha")
    builder.constraint(assign_north_beta + assign_south_beta == 1, name="serve_beta")
    builder.constraint(assign_north_gamma + assign_south_gamma == 1, name="serve_gamma")

    builder.constraint(assign_north_alpha <= open_north, name="alpha_requires_north")
    builder.constraint(assign_north_beta <= open_north, name="beta_requires_north")
    builder.constraint(assign_north_gamma <= open_north, name="gamma_requires_north")
    builder.constraint(assign_south_alpha <= open_south, name="alpha_requires_south")
    builder.constraint(assign_south_beta <= open_south, name="beta_requires_south")
    builder.constraint(assign_south_gamma <= open_south, name="gamma_requires_south")

    builder.minimize(
        (open_north * open_cost["north"])
        + (open_south * open_cost["south"])
        + (assign_north_alpha * service_cost[("north", "alpha")])
        + (assign_north_beta * service_cost[("north", "beta")])
        + (assign_north_gamma * service_cost[("north", "gamma")])
        + (assign_south_alpha * service_cost[("south", "alpha")])
        + (assign_south_beta * service_cost[("south", "beta")])
        + (assign_south_gamma * service_cost[("south", "gamma")]),
        name="total_cost",
    )
    program = builder.freeze()

    result = Orchestrator().run(
        program,
        config=OrchestratorConfig(
            phases=[PhaseConfig(name="default_facility_location", solver=OrchestratorSolver.MILP, budget_iterations=20)],
        ),
    )

    print_solution(
        "facility location solved by default milp family routing",
        result.final_solution,
        extra={
            "open_cost": open_cost,
            "service_cost": {f"{facility}:{customer}": cost for (facility, customer), cost in service_cost.items()},
            "note": "This example uses solver='milp' without forcing a concrete backend.",
        },
    )


if __name__ == "__main__":
    main()
