# Inventory Routing Problem

This directory contains a notebook that models the Inventory Routing Problem
(IRP) with OptAgent. It combines one customer-sequence list per planning
period with continuous delivery quantities, recursive inventories, stockout
and vehicle-capacity constraints, and inventory plus transportation costs.

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
cd examples/hexaly/inventory_routing_problem_irp
python -m jupyter lab inventory_routing_problem_irp.ipynb
```

Run the notebook cells in order. The final lines solve the bundled
`instances/abs1n5.dat` instance with a five-second time limit. Other bundled
Archetti instances can be selected by changing the instance filename.

To preserve the original Hexaly model, the conversion does not add custom
initial delivery quantities or routes. With the natural zero-delivery and
empty-route defaults, the current OptAgent search may report
`NO_FEASIBLE_SOLUTION_FOUND` on this coupled list/continuous model within a
short time limit; the notebook reports that status without changing the model.
