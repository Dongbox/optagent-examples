# Linear Examples

Linear examples are algebraic LP/MIP models that lower through the MP exact path.

Use direct exact APIs:

```python
solution = solve_milp(program, config=MilpConfig(backend="optx"))
```

Backends shown here:

- `optx`: internal embedded MP backend.
- `mathopt_mp`: external OR-Tools MathOpt adapter.

Included examples:

- [assignment_highs_native.py](../linear/assignment_highs_native.py)
  Solves a binary assignment model with the internal `optx` backend.
- [knapsack_mathopt.py](../linear/knapsack_mathopt.py)
  Solves 0/1 knapsack with the external `mathopt_mp` adapter.
- [facility_location_small.py](../linear/facility_location_small.py)
  Solves facility open/assign decisions with internal exact MP.
- [routing_linearized_small.py](../linear/routing_linearized_small.py)
  Shows a small route model expressed as linear MIP instead of a blackbox scorer.
