# Flexible Resource-Constrained Project Scheduling with States

This directory contains an OptAgent notebook for FRCPSPS with resource states.
It preserves the interval decisions, resource partition, capacity constraints,
precedence constraints, and state-dependent transition delays. Interval
operations use the Hexaly-compatible `contains`, `start`, and `end` model APIs.

## Install and run

Install OptAgent and JupyterLab, then open the notebook from the public
examples repository root:

```bash
python -m pip install /path/to/optagent-VERSION-PYTHON_TAG-PLATFORM_TAG.whl jupyterlab
cd examples/scheduling/flexible_resource_constrained_project_scheduling_problem_with_states_frcpsps
python -m jupyter lab flexible_resource_constrained_project_scheduling_problem_with_states_frcpsps.ipynb
```

Run the cells in order using one of the bundled files under `instances/`.
