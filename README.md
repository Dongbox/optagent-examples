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
