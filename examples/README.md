# Examples

Examples are organized by problem type first, then by backend or solve path.

## Categories

- `linear/`: 0/1 selection, assignment, facility location, routing MILP, MathOpt, and HiGHS.
- `scheduling/`: sequence and interval variables, no-overlap, precedence, and CP-SAT.
- `blackbox/`: external Python scoring functions and heuristic search.
- `hybrid/`: mixed linear and scheduling models with multi-stage orchestration.
- `presets/`: built-in preset and automatic preset selection usage.
- `mps/`: MPS import, preset loading, and exact/heuristic solve paths.
- `steel/`: steel coil sequencing examples and search diagnostics.
- `resource_flow/`: public resource-flow CP-SAT and MILP formulations.
- `mg/`: hot-dip galvanizing coil sequencing notebook with inline data.
- `cold_rolling/`: generic cold-rolling coil sequencing notebook with inline data.

## Run

Run examples from the repository root:

```bash
PYTHONPATH=. python examples/linear/knapsack_mathopt.py
PYTHONPATH=. python examples/scheduling/job_shop_small.py
PYTHONPATH=. python examples/blackbox/tsp_blackbox_small.py
PYTHONPATH=. python examples/hybrid/hybrid_production_planning_small.py
PYTHONPATH=. python examples/presets/routing_blackbox_auto_preset.py
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --summary-only
PYTHONPATH=. python examples/steel/run_blackbox.py --instance bundled_head40 --mode preset
PYTHONPATH=. python examples/resource_flow/solve_case.py --formulation cp --summary-only
PYTHONPATH=. python examples/mg/program/main.py examples/mg/program/data/20260407000000.db
```

## Dependency Notes

- `mathopt_mp` and `cp_sat_native` examples require `ortools`.
- `highs_native` examples require `highspy`.
- Some hot-dip galvanizing/MG preprocess compatibility modules import optional APS dependencies only when the APS-compatible preprocess path is used.
