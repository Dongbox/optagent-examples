# Flexible Resource-Constrained Project Scheduling Problem

This directory contains a notebook that models a flexible resource-constrained
project scheduling problem using OptAgent. The final cells solve the bundled
`pat1.fc` instance and print each task's selected resource, start time, and end
time when a feasible solution is found.

## Install

Install the OptAgent wheel for your Python version and platform together with
JupyterLab:

```bash
python -m pip install /path/to/optagent-VERSION-PYTHON_TAG-PLATFORM_TAG.whl jupyterlab
```

## Run

From the public examples repository root, enter this example directory and
start the notebook with:

```bash
cd examples/hexaly/flexible_resource_constrained_project_scheduling_problem
python -m jupyter lab flexible_resource_constrained_project_scheduling_problem.ipynb
```

Run the notebook cells in order. The final cell solves `instances/pat1.fc` with
a ten-second time limit. The model preserves the original time-indexed capacity
formulation; with the current OptAgent scheduling bootstrap, a short run may
finish without finding a feasible solution. The remaining Patterson instances
are available in `instances/` for additional experiments.
