# OptAgent Examples

This repository contains the maintained Hexaly-compatible OptAgent examples.
Each notebook under `examples/<label>/` builds a model with the public
`optagent` API and sends it through the production solve route.

## Install

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Open a notebook under `examples/<label>/`, or run the tests from the
repository root:

```bash
python -m pytest -q
```

## Modeling conventions

Use `OptModel()` and omit optional `name` arguments in ordinary examples.
Keep Python references to decision and objective expressions, then read `.value`
after checking `solution.feasible`. Read `solution.objectives` in declaration
order. Names and model identifiers are optional metadata, not result lookup keys;
retain them when an example, its result handling, or its test fixtures actually
uses them. The wind-farm fixture, for example, uses location names to assign
fixed decision values.

## Test

```bash
python -m pytest -q
```

Only public, reproducible data belongs here.

## Test Ownership

- Core API and kernel behavior remains owned by the private OptAgent repository;
  this repository only tests the public example contract.
