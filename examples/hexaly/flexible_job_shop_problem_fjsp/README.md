# Flexible Job Shop Problem (FJSP)

This directory contains a notebook that models a flexible job shop scheduling
problem with OptAgent. The final cells solve the bundled `tiny.fjs` instance
and print each operation's selected machine, start time, and end time.

## Install

Install OptAgent from the approved distribution for your environment, then
install JupyterLab:

```bash
python -m pip install jupyterlab
```

## Run

From the public examples repository root, start the notebook with:

```bash
python -m jupyter lab examples/hexaly/flexible_job_shop_problem_fjsp/flexible_job_shop_problem_fjsp.ipynb
```

Run the notebook cells in order. The final cell solves `instances/tiny.fjs`
with a two-second time limit. The larger Brandimarte instances remain
available in `instances/` for longer experiments.
