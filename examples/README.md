# OptAgent Examples

This repository contains small, public, reproducible examples organized by
problem requirements rather than by solver internals.

## Example Scope

- `quickstart/`: the three shortest public solve routes.
- `linear/`: linear and mixed-integer models, including a linearized TSP.
- `scheduling/`: basic, flexible, and resource-constrained scheduling models.
- `blackbox/`: problems whose objective or constraints must call external Python code.
- `resource_flow/`: resource-flow formulations expressed with CP and MILP.

The examples prefer an exact algebraic or structured model when the problem can
be expressed that way. Blackbox examples are reserved for simulators, legacy
business code, or other external evaluators that cannot be expanded into model
expressions.

## Install

Install OptAgent from the approved distribution for your environment, then:

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

Only small, public, reproducible data belongs in this repository.
