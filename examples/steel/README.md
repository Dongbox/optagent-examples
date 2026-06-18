# Steel Example

This directory is the active example surface for the next round of OptAgent
strategy and architecture work.

The steel workflows are intentionally split by modeling style:

```text
examples/steel/
  steel_sequence_external.py
  steel_dag_path.py
  data/
    steel_coils.json
```

Each file is self-contained. Data loading, welding rules, diagnostics, modeling,
strategy config, solve calls, and output shaping are duplicated intentionally so
the two modeling styles can evolve independently.

Both models deliberately avoid a constructive initial solution. The variable
defaults are the unoptimized natural coil order, and any improvement must come
from the configured GA or ALNS strategy.

`steel_sequence_external.py` shows:

- load the bundled public steel coil data
- define direct-weld compatibility and transition-count diagnostics
- build an OptAgent `sequence_var` model with a ctx-style external objective
- start from the builder's natural sequence default instead of a constructive seed
- call the current strategy-first API with `GaConfig` and `AlnsConfig`
- print or write a comparable result payload

`steel_dag_path.py` shows:

- load the same public data independently
- build explicit edge/order DAG path variables and MTZ path constraints
- use the natural path only as the raw variable default, not as a heuristic seed
- call `GaConfig` and `AlnsConfig` with DAG-specific strategy parameters
- decode selected edges back into a sequence for diagnostics

## Run

Run from the examples repository root:

```bash
PYTHONPATH=. python examples/steel/steel_sequence_external.py
PYTHONPATH=. python examples/steel/steel_dag_path.py
```

When running from the private source checkout, include the source tree first:

```bash
PYTHONPATH=../src:. python examples/steel/steel_sequence_external.py
PYTHONPATH=../src:. python examples/steel/steel_dag_path.py
```

Available instances:

- `toy`
- `bundled_head40`
- `bundled`

## Current Scope

Other example directories remain in the repository for reference, but they are
temporarily not part of the active public example surface or default example
test collection. New strategy and architecture optimization should target this
steel workflow first.
