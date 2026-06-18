# MPS Examples

This directory keeps public `window_*.mps` files and rebuilds them at runtime as
OptAgent `ModelBuilder` programs.

Run from the examples repository root:

```bash
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --summary-only
PYTHONPATH=. python examples/mps/solve_window.py --window 0
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --mode heuristic
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --backend optx
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --backend mathopt_mp
```

Notes:

- `--mode exact` uses `solve_milp(...)`.
- `--mode heuristic` uses `solve(...)` with an explicit `GaConfig`.
- `--backend optx` demonstrates the internal MP backend.
- `--backend mathopt_mp` demonstrates an external OR-Tools MathOpt adapter.
- Use `--summary-only` first for large windows.
