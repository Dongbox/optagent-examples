# Hosaki Function

This directory contains a notebook that models the box-constrained Hosaki
function with OptAgent. The objective remains a Python external function of
two floating-point decision variables, matching the original Hexaly model.

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
cd examples/hexaly/hosaki_function
python -m jupyter lab hosaki_function.ipynb
```

Run the notebook cells in order. No instance file is required. The final cell
solves the model with a one-second wall-clock limit and prints the objective,
`x1`, and `x2` values.

The original Hexaly example enables surrogate modeling and limits the number
of external-function evaluations. OptAgent does not currently expose matching
options, so this conversion preserves the external objective and uses the
public solve time limit instead.
