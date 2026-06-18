# OptAgent Examples

Runnable examples for OptAgent live in this repository.

## Example Scope

The examples are grouped by modeling and solve style:

- `linear/`: algebraic LP/MIP models solved through direct exact APIs.
- `scheduling/`: interval/sequence scheduling models solved through CP-SAT.
- `blackbox/`: sequence objectives scored by Python functions and optimized by declared strategies.
- `mps/`: MPS windows rebuilt into OptAgent models, with exact and strategy-driven modes.
- `resource_flow/`: bundled CP and MILP resource-flow formulations.
- `steel/`: two independent steel coil sequencing models, each declaring GA and ALNS strategies directly.
- `mg/` and `cold_rolling/`: domain notebooks and MG SQLite migration tests.

Cross-family behavior is expressed by strategy configuration, for example ALNS
with exact repair, inside the problem examples that need it.

## Install

Install OptAgent from the approved distribution for your environment, then
install the example dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

For source-based development from the private checkout, put the source tree on
`PYTHONPATH` before the examples package.

## Run

Run commands from the examples repository root:

```bash
PYTHONPATH=. python examples/linear/assignment_highs_native.py
PYTHONPATH=. python examples/linear/knapsack_mathopt.py
PYTHONPATH=. python examples/scheduling/job_shop_small.py
PYTHONPATH=. python examples/blackbox/tsp_blackbox_small.py
PYTHONPATH=. python examples/steel/steel_sequence_external.py
PYTHONPATH=. python examples/steel/steel_dag_path.py
```

From the private source checkout:

```bash
PYTHONPATH=../src:. python examples/linear/assignment_highs_native.py
PYTHONPATH=../src:. python examples/linear/knapsack_mathopt.py
PYTHONPATH=../src:. python examples/scheduling/job_shop_small.py
PYTHONPATH=../src:. python examples/blackbox/tsp_blackbox_small.py
PYTHONPATH=../src:. python examples/steel/steel_sequence_external.py
PYTHONPATH=../src:. python examples/steel/steel_dag_path.py
```

## Test

Default example test collection covers the maintained example surface:

```bash
python -m pytest -q
```

To run explicitly from the private source checkout:

```bash
PYTHONPATH=../src:. python -m pytest -q
```

## Data Policy

Only public, small, and reproducible data belongs here. Small SQLite, JSON, CSV,
MPS, and compressed JSON fixtures are acceptable. Do not commit private business
data, absolute private paths, credentials, or links to internal-only systems.
