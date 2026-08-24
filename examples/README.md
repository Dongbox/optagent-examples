# OptAgent Examples

The maintained examples are the Hexaly-compatible notebooks under `hexaly/`.
They use the public `optagent` modeling and solve interfaces.

## Install

Install OptAgent from the approved distribution for your environment, then:

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Open a notebook under `hexaly/`, or run the contract suite from the repository
root:

```bash
python -m pytest -q tests/test_hexaly_a_to_j_contract.py
```

## Test

```bash
python -m pytest -q
```

Only small, public, reproducible data belongs in this repository.
