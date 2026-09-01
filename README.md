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

## Test

```bash
python -m pytest -q
```

Only public, reproducible data belongs here.

## Test Ownership

- Core API and kernel behavior remains owned by the private OptAgent repository;
  this repository only tests the public example contract.
