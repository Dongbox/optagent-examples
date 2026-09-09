# OptAgent Examples

This repository contains runnable examples of the public OptAgent Python API.
Each notebook under `examples/<label>/` builds a model with the public
`optagent` API and sends it through the production solve route.

## Install

Install the matching OptAgent package and configure its license following the
[installation guide](https://optagent.pages.dev/start/installation/), then install
the notebook tools and example dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Start JupyterLab from the example directory so relative instance paths resolve.
For example, from the repository root:

```bash
cd examples/packing/knapsack_problem
python -m jupyterlab knapsack_problem.ipynb
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

## Documentation

Browse the [example catalog](https://optagent.pages.dev/examples/) to read notebooks
without starting a Python kernel. The documentation site renders these notebooks
without executing them and offers a complete example ZIP with instance files.
Notebook prose should describe this implementation's OptAgent APIs. Preserve
problem/data attribution and copyright notices; do not present another solver's
benchmark results as OptAgent results. Add verified outputs separately when ready.

## Test Ownership

- Core API and kernel behavior remains owned by the private OptAgent repository;
  this repository only tests the public example contract.
