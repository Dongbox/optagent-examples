# Linear Examples

This directory contains examples for linear and mixed-integer models that lower through `CanonicalMpModel`.

## Supported modeling style

Typical primitives:

* `int_var(...)`
* `float_var(...)`
* arithmetic with `+`, `-`, `*`, `sum(...)`
* linear constraints with `<=`, `==`, `>=`
* scalar objective with `maximize(...)` / `minimize(...)`

## Supported solve forms

Logical solver family:

* `PhaseConfig(..., solver=OrchestratorSolver.MILP)`

Concrete backend:

* `solver=OrchestratorSolver.MATHOPT_MP`
* `solver=OrchestratorSolver.HIGHS_NATIVE`

Routing controls:

* `required_backend=ExactBackendName.MATHOPT_MP`
* `required_backend=ExactBackendName.HIGHS_NATIVE`
* `allowed_backends=(...)`
* `strict_backend=True`
* `solve_config={"preferred_backend": "..."}`

## Included examples

* [knapsack_mathopt.py](../linear/knapsack_mathopt.py)
  Shows 0/1 knapsack with strict routing to `mathopt_mp`.
* [assignment_highs_native.py](../linear/assignment_highs_native.py)
  Shows binary assignment with strict routing to `highs_native`.
* [facility_location_small.py](../linear/facility_location_small.py)
  Shows facility open/assign modeling with the default `milp` family route and backend selection through the registry.
* [routing_linearized_small.py](../linear/routing_linearized_small.py)
  Shows the same routing domain represented as a linearized MILP instead of a blackbox sequence objective.
