# Scheduling Examples

This directory contains examples for sequence-and-interval scheduling models that lower through `CanonicalCpModel`.

## Supported modeling style

Typical primitives:

* `sequence_var(...)`
* `interval_var(...)`
* `no_overlap(...)`
* `precedence(...)`
* `interval_end(...)`

## Supported solve forms

Logical solver family:

* `PhaseConfig(..., solver=OrchestratorSolver.CP_SAT)`

Concrete backend:

* `solver=OrchestratorSolver.CP_SAT_NATIVE`

Routing controls:

* `required_backend=ExactBackendName.CP_SAT_NATIVE`
* `strict_backend=True`

## Included examples

* [flow_shop_cp_sat.py](/Users/dongbox/work/optagent/examples/scheduling/flow_shop_cp_sat.py)
  Shows a tiny ordered flow-shop style schedule solved by `cp_sat_native`.
* [job_shop_small.py](/Users/dongbox/work/optagent/examples/scheduling/job_shop_small.py)
  Shows a small job shop with two machines, precedence chains and CP-SAT native routing.
