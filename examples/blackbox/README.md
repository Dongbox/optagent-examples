# Blackbox Examples

Blackbox examples keep business scoring in Python and let OptAgent search over
sequence variables. They use `solve(...)` with explicit strategy objects.

Typical shape:

```python
solution = solve(program, strategy=GaConfig(max_iterations=60))
```

Included examples:

- [routing_heuristic.py](../blackbox/routing_heuristic.py)
  Route ordering scored by a Python function and solved by `GaConfig`.
- [tsp_blackbox_small.py](../blackbox/tsp_blackbox_small.py)
  Small TSP-style path optimized with GA search.
- [tsp_evolutionary_small.py](../blackbox/tsp_evolutionary_small.py)
  The same kind of sequence objective optimized with `GaConfig` and its
  `local_improvement_strategy="lns"` option.
- [steel_transition_sequence.py](../blackbox/steel_transition_sequence.py)
  Compatibility entrypoint that forwards to the canonical steel sequence example.
