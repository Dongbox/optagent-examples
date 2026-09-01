# OptAgent Examples

The maintained examples are grouped by the official Hexaly template labels:
`location/`, `network_design/`, `nonlinear/`, `packing/`, `routing/`,
`scheduling/`, and `simulation/`. They use the public `optagent` modeling and
solve interfaces.

| Label | Examples |
| --- | ---: |
| Location | 6 |
| Network Design | 1 |
| Nonlinear | 6 |
| Packing | 12 |
| Routing | 20 |
| Scheduling | 28 |
| Simulation | 3 |

CPIT is kept only under `packing/`, so the seven directories contain 76 unique
templates.

## Install

Install OptAgent from the approved distribution for your environment, then:

```bash
python -m pip install -r requirements-dev.txt
```

## Run

Open a notebook under one of the label directories, or run the tests from the
repository root:

```bash
python -m pytest -q
```

## Test

```bash
python -m pytest -q
```

Only small, public, reproducible data belongs in this repository.
