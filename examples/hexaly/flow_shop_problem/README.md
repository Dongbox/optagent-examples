# Flow Shop Scheduling Problem

This directory contains a notebook that models a permutation flow shop
scheduling problem using OptAgent. The final cells solve the bundled
`tai20_5.txt` instance and print the makespan and job sequence.

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
cd examples/hexaly/flow_shop_problem
python -m jupyter lab flow_shop_problem.ipynb
```

Run the notebook cells in order. The final cell solves
`instances/tai20_5.txt` with a five-second time limit. The remaining Taillard
instances are available in `instances/` for larger experiments.
