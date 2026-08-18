# Job Shop Scheduling Problem

This directory contains a notebook that models the Job Shop Scheduling
Problem (JSSP) with OptAgent. Processing operations are interval variables,
each job follows its fixed machine order, and one full job-permutation list per
machine enforces disjunctive machine capacity.

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
cd examples/hexaly/job_shop_scheduling_problem_jssp
python -m jupyter lab job_shop_scheduling_problem_jssp.ipynb
```

Run the notebook cells in order. The final lines solve the bundled
`instances/ft06.txt` instance with a five-second time limit and print the
makespan plus the zero-based job sequence for every machine. Other bundled
Taillard-format instances can be selected by changing the filename.

The machine-capacity constraint deliberately retains the original Hexaly
formulation: a full job-order list plus dynamically indexed precedence between
adjacent intervals. The current OptAgent scheduling bootstrap does not treat
that arithmetic form as a first-class no-overlap declaration, so a short run
may report `NO_FEASIBLE_SOLUTION_FOUND`. The notebook reports that status
without replacing the original model or adding a custom schedule seed.
