# Wind farm layout optimization

Open `wind_farm_layout_optimization_problem_wflop.ipynb` after installing
`optagent` and `jupyter`. Run the declaration cell, then an instance call such as
`main(INSTANCE_DIR / "nT36.json", time_limit=10)` using an actual file from
`instances/` (the notebook contains ready-to-run calls).

Wake loss uses shared sparse coefficient, location, and row-offset arrays.
Nested mapped sums reuse one power formula across all locations and directions. This preserves every nonzero contribution and avoids millions
of separate scalar multiplication nodes. Model construction is separate from the
public solve budget; serialization and native compilation consume that budget.
