# OptAgent Examples

Runnable examples for OptAgent live in this public repository. The maintained
surface is organized around four problem categories plus a small quickstart:

- `examples/quickstart/`: general `solve`, linear `solve`/`solve_optx`, and CP-SAT.
- `examples/linear/`: linear and mixed-integer models, including linearized TSP.
- `examples/scheduling/`: basic, flexible, and resource-constrained scheduling.
- `examples/blackbox/`: external evaluators that cannot be expressed structurally.
- `examples/resource_flow/`: CP and MILP resource-flow formulations.

## Install

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Run commands from the repository root:

```bash
PYTHONPATH=. python examples/quickstart/unified_solve.py
PYTHONPATH=. python examples/linear/quickstart_linear_routes.py
PYTHONPATH=. python examples/linear/routing_linearized_small.py
PYTHONPATH=. python examples/scheduling/job_shop_small.py
PYTHONPATH=. python examples/blackbox/steel_sequence_external.py
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --summary-only
```

## Test

```bash
python -m pytest -q
```

Only small, public, reproducible data belongs here. The examples prefer exact
algebraic or structured models whenever the problem can be expressed that way.

## Test Ownership

- MPS, MG and cold-rolling tests were removed with those non-public example
  surfaces; no replacement owner is required because the features are no
  longer part of the downloadable examples.
- `tests/test_blackbox_steel_examples.py` owns the retained external-callback
  blackbox case.
- `tests/test_examples_resource_flow.py` and the maintained linear/scheduling
  example tests own the public resource-flow, linear and scheduling cases.
- Core API and kernel behavior remains owned by the private OptAgent repository;
  this repository only tests the public example contract.
