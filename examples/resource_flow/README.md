# Resource Flow Examples

This directory contains a bundled OptAgent `resource_flow` example adapted from
an APS-style resource-flow project.

Included pieces:

- [case_loader.py](../resource_flow/case_loader.py): loads bundled `zj` case snapshots.
- [cp_builder.py](../resource_flow/cp_builder.py): CP-SAT oriented single-window formulation.
- [milp_builder.py](../resource_flow/milp_builder.py): algebraic MILP formulation.
- [solve_case.py](../resource_flow/solve_case.py): direct exact and strategy-driven solve entrypoint.
- [rolling.py](../resource_flow/rolling.py): workflow-layer CP rolling-window runner.
- [compare_original.py](../resource_flow/compare_original.py): migration-only comparison against the original project.

Run from the examples repository root:

```bash
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --summary-only
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation milp --summary-only
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --mode exact
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --mode alns
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation milp --mode exact --backend optx
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation milp --mode exact --backend mathopt_mp
```

Solve modes:

- `exact`: `solve_cpsat(...)` for CP formulation, `solve_milp(...)` for MILP formulation.
- `ga`: `solve(...)` with `GaConfig`.
- `alns`: `solve(...)` with `AlnsConfig` and exact repair enabled.

Default bundled behavior is self-contained for the shipped `planning_period=3`
`zj` case. `compare_original.py` still needs an external original-project checkout.
