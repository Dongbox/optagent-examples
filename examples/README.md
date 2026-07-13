# Examples

Current examples use the solve-first API directly.

```bash
PYTHONPATH=. python examples/linear/assignment_optx.py
PYTHONPATH=. python examples/scheduling/job_shop_small.py
PYTHONPATH=. python examples/blackbox/tsp_blackbox_small.py
PYTHONPATH=. python examples/steel/steel_sequence_external.py
PYTHONPATH=. python examples/steel/steel_dag_path.py
```

Example groups:

- `linear`: direct `solve_milp(...)` with internal `optx` and external `mathopt_mp`.
- `scheduling`: direct `solve_cpsat(...)`.
- `blackbox`: `solve(...)` with `GaConfig`.
- `mps`: MPS import plus direct exact or declared strategy solve modes.
- `resource_flow`: bundled CP/MILP resource-flow formulations.
- `steel`: two independent coil sequencing model files, each declaring GA and ALNS.
- `mg` / `cold_rolling`: domain notebooks and MG migration support.
