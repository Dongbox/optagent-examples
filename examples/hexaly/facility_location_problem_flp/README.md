# Facility Location Problem (FLP)

This directory contains a notebook that models the OR-LIB P-Median facility
location problem with OptAgent and runs the model on the bundled `pmed1.in`
instance.

## Install

Install OptAgent from the approved distribution for your environment, then
install JupyterLab:

```bash
python -m pip install jupyterlab
```

## Run

From the public examples repository root, start the notebook with:

```bash
python -m jupyter lab examples/hexaly/facility_location_problem_flp/facility_location_problem_flp.ipynb
```

Run the notebook cells in order. The final cell solves `instances/pmed1.in`
and prints the total cost, selected facility indices, and solution status.
