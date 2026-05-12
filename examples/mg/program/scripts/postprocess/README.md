# MG Postprocess Stage

This directory mirrors the original production layout:

```text
program/scripts/postprocess/
```

The original MG postprocess may continue to run after the OptAgent model stage.
For downstream flows that cannot yet read `o_mg_optagent_*` directly,
`postprocess.py` can create compatibility tables:

- `o_process_output_optagent`
- `o_rules_cost_optagent`

These compatibility tables intentionally use separate names so existing output
tables are not overwritten during migration validation.
