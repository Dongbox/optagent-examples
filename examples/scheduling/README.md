# Scheduling Examples

Scheduling examples use sequence and interval semantics that are best handled by
CP-SAT.

Use direct CP-SAT APIs:

```python
solution = solve_cpsat(program, config=CpSatConfig(time_limit_s=10, workers=1))
```

Included examples:

- [flow_shop_cp_sat.py](../scheduling/flow_shop_cp_sat.py)
  Ordered flow-shop style scheduling solved by CP-SAT.
- [job_shop_small.py](../scheduling/job_shop_small.py)
  Small job shop with machine capacity and precedence constraints.
