# Dial-a-Ride Problem

This directory contains an OptAgent notebook for the dial-a-ride problem. It
keeps the original list-partition routing model, recursive load/time arrays,
pickup-before-delivery constraints, and lexicographic objectives. Route
positions use Hexaly-compatible `model.index(list, value)` syntax.

## Install and run

Install OptAgent and JupyterLab, then open the notebook from the public
examples repository root:

```bash
python -m pip install /path/to/optagent-VERSION-PYTHON_TAG-PLATFORM_TAG.whl jupyterlab
cd examples/routing/dial_a_ride_problem_darp
python -m jupyter lab dial_a_ride_problem_darp.ipynb
```

Run the cells in order using one of the bundled files under `instances/`.
