# MG Model Stage

This directory is the formal replacement point for the original APS model phase:

```text
program/model/
```

Instead of calling APS `Agent.run()`, `program/main.py` calls
`mg.program.model.reports.run_production_case(...)` for the model phase.

## Runtime Flow

```text
program/main.py
  -> reports.run_production_case(db_path)
     -> preprocess.data.load_mg_case(...)
     -> reports.build_search_replacement_report(...)
        -> search.solve_mg_sequence(...)
           -> model.build_mg_program(...)
           -> optagent.solve(..., SolveOptions(strategy=...))
     -> postprocess.write_production_output_tables(...)
     -> optional postprocess.write_legacy_compatibility_tables(...)
```

## Files

- `model.py`: declares the `sequence_var`, wires `rules.score_sequence_external(...)`
  into the blackbox objective, and attaches adjacent-edge metadata.
- `search.py`: maps MG modes to current strategy configs:
  - `tabu` -> `TabuConfig`
  - `polish` -> `LnsConfig`
  - `evolutionary` -> `GaConfig`
- `reports.py`: adds APS parity context, structured-edge diagnostics, production
  payload assembly, and SQLite output writes.
- `rules.py`: owns MG scoring semantics.

The final sequence is read from `UnifiedSolution.variable_values` using the
`sequence_node_id` returned by `model.build_mg_program(...)`.
