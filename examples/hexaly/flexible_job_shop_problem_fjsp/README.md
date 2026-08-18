# Flexible Job Shop Problem (FJSP)

This directory contains a notebook that models a flexible job shop scheduling
problem with OptAgent. The final cells solve the bundled `tiny.fjs` instance
and print each operation's selected machine, start time, and end time.

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
cd examples/hexaly/flexible_job_shop_problem_fjsp
python -m jupyter lab flexible_job_shop_problem_fjsp.ipynb
```

Run the notebook cells in order. The final cell solves `instances/tiny.fjs`
with a two-second time limit. The larger Brandimarte instances remain
available in `instances/` for longer experiments.
