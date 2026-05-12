# OptAgent Examples

Runnable examples for OptAgent live in this repository.

The private `optagent` repository keeps the core implementation, internal
documents, tests for core behavior, and implementation records. This public
repository keeps example code, example-specific tests, small public data files,
and helper scripts.

## Repository Layout

- `examples/linear/`: MILP, MathOpt, HiGHS, and linearized routing examples.
- `examples/scheduling/`: `sequence_var`, `interval_var`, `no_overlap`, and CP-SAT examples.
- `examples/blackbox/`: `external_call` and heuristic search examples.
- `examples/hybrid/`: mixed linear and scheduling examples.
- `examples/presets/`: built-in and external preset usage.
- `examples/mps/`: MPS import and solve examples.
- `examples/steel/`: steel coil sequencing examples and diagnostics.
- `examples/resource_flow/`: resource-flow CP-SAT and MILP formulations.
- `examples/mg/`: SQLite-driven MG migration example.
- `tests/`: regression tests for the examples.
- `scripts/`: repeatable example experiment helpers.

## Install

For local development next to the private source checkout:

```bash
cd optagent-examples
python -m pip install -e ../optagent
python -m pip install -r requirements-dev.txt
```

If `optagent` is already installed from a wheel, only install the example
dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Optional exact solver examples use `ortools` and/or `highspy`. Tests that need
those backends are skipped or narrowed when the dependency is unavailable.

## Run Examples

Run commands from the repository root.

```bash
PYTHONPATH=. python examples/linear/knapsack_mathopt.py
PYTHONPATH=. python examples/scheduling/job_shop_small.py
PYTHONPATH=. python examples/blackbox/tsp_blackbox_small.py
PYTHONPATH=. python examples/hybrid/hybrid_production_planning_small.py
PYTHONPATH=. python examples/steel/run_blackbox.py --instance bundled_head40 --mode preset
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --summary-only
PYTHONPATH=. python examples/mg/program/main.py examples/mg/program/data/20260407000000.db
```

Each example area has its own README with more specific commands and data notes.

## Test

The pytest configuration adds this repository root and `../optagent/src` to the
Python path for sibling-checkout development.

```bash
python -m pytest -q
```

To run a smaller smoke set:

```bash
python -m pytest -q tests/test_examples_mps_builder.py tests/test_stage6_steel_examples.py
```

## Data Policy

Only public, small, and reproducible data belongs here. Small SQLite, JSON, CSV,
MPS, and compressed JSON fixtures are acceptable. Do not commit private business
data, absolute private paths, credentials, or links to internal-only systems.
