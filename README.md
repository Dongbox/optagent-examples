# OptAgent Examples

This repository contains the maintained Hexaly-compatible OptAgent examples.
Each notebook under `examples/hexaly/` builds a model with the public
`optagent` API and sends it through the production solve route.

## Install

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Open a notebook under `examples/hexaly/`, or run the contract suite from the
repository root:

```bash
python -m pytest -q tests/test_hexaly_a_to_j_contract.py
```

## Test

```bash
python -m pytest -q
```

Only public, reproducible data belongs here.

## Test Ownership

- `tests/test_hexaly_a_to_j_contract.py` owns the notebook-to-public-solve and
  C++ initial-evaluator contract for the maintained A-J example set.
- Core API and kernel behavior remains owned by the private OptAgent repository;
  this repository only tests the public example contract.
