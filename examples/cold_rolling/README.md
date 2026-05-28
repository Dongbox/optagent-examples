# Generic Cold-Rolling OptAgent Example

This example demonstrates how OptAgent can cover a generic cold-rolling coil
sequencing problem with a compact and readable modeling declaration.

The main path is intentionally small:

```text
examples/cold_rolling/README.ipynb
examples/cold_rolling/src/cold_rolling_model.ipynb
```

The notebook uses inline public coil tables instead of a SQLite handoff. It does
not bind the example to a specific real mill. The focus is solver capability:
declare a sequence variable, attach a business scoring function, and let
OptAgent search for a lower-cost rolling order.

## Business Problem

A generic cold-rolling planner receives coils that differ by entry thickness,
target thickness, width, grade family, hardness family, surface grade, oiling
route, due-date bucket, due priority, and target position. The sequence should
avoid unstable rolling transitions while preserving surface-sensitive blocks and
schedule pressure.

The example objective includes:

- width, entry-thickness, target-thickness, and reduction-ratio smoothness;
- grade-family and hardness-family changes;
- surface-sensitive block breaks;
- high-reduction transitions;
- oiling-route changes;
- width-up roll-profile risk;
- due-date bucket spread;
- due-position risk for urgent orders that appear too late.

The notebook includes a business-requirement mapping table that shows where each
README requirement is declared: the input table, field names, and corresponding
rule-cost names are shown side by side.

## Model Shape

The core declaration is deliberately short:

```python
builder = ModelBuilder(metadata={"case": "generic_cold_rolling_coil_sequence"})
sequence = builder.sequence_var(size=len(coils), default=baseline_sequence)
builder.minimize(
    builder.external_call(cold_rolling_sequence_cost, sequence),
    name="minimize_cold_rolling_transition_cost",
)
program = builder.freeze()
```

This is the intended teaching point: the business scoring logic can stay in
clear Python while OptAgent owns permutation search, move evaluation, and
heuristic orchestration.

The notebook also ends with a compact complete-code cell. It repeats the same
pattern with a smaller table and comments around each step, so readers can see
the whole flow without jumping between sections.

## Run

Open and run:

```text
examples/cold_rolling/src/cold_rolling_model.ipynb
```
