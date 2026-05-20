# Hot-Dip Galvanizing OptAgent Example

This example demonstrates how OptAgent can cover a hot-dip galvanizing coil
sequencing problem with a compact and readable modeling declaration.

The main path is intentionally small:

```text
examples/mg/README.ipynb
examples/mg/src/hot_dip_galvanizing_model.ipynb
```

The notebook uses an inline public coil table instead of a SQLite handoff. That
keeps the example focused on solver capability: declare a sequence variable,
attach a business scoring function, and let OptAgent search for a lower-cost
galvanizing order.

## Business Problem

A CGL/HDG planner receives cold-rolled and hot-rolled feed coils that differ by
grade family, zinc layer, gauge, width, annealing temperature, surface/outer
panel requirements, and post-process route. The line should avoid unnecessary
campaign breaks and severe transitions.

The example objective includes:

- width, thickness, and annealing-temperature smoothness;
- zinc-layer campaign changes;
- grade-family changes;
- thin-gauge transitions;
- post-process route changes;
- outer-panel block breaks;
- width-up roll-change risk.

## Model Shape

The core declaration is deliberately short:

```python
builder = ModelBuilder(metadata={"case": "hot_dip_galvanizing_coil_sequence"})
sequence = builder.sequence_var(size=len(coils), default=incumbent_sequence)
builder.minimize(
    builder.external_call(galvanizing_sequence_cost, sequence),
    name="minimize_transition_and_campaign_cost",
)
program = builder.freeze()
```

This is the intended teaching point: the business scoring logic can stay in
clear Python while OptAgent owns permutation search, move evaluation, and
heuristic orchestration.

## Run

Open and run:

```text
examples/mg/src/hot_dip_galvanizing_model.ipynb
```

The older `program/` directory remains in place for compatibility with the
existing MG SQLite migration tests, but it is no longer the recommended reading
path for this example.
