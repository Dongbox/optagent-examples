# Job Shop Scheduling Problem with Intensity

This directory contains a notebook that models a Job Shop Scheduling Problem
with time-varying machine intensity using OptAgent. Operations are interval
variables, each job follows its fixed machine order, and each machine has a
full job-order list. An operation accumulates its machine's intensity over its
active integer time range until its processing requirement is met.

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
cd examples/hexaly/job_shop_scheduling_problem_with_intensity
python -m jupyter lab job_shop_scheduling_problem_with_intensity.ipynb
```

Run the notebook cells in order. The final lines solve the bundled
`instances/i01_ft06.txt` instance with a five-second time limit and print the
makespan plus the zero-based job sequence for every machine.

The conversion deliberately keeps the original dynamically indexed machine
precedence and intensity-sum formulation. The current OptAgent scheduling
bootstrap does not treat these arithmetic expressions as first-class
scheduling declarations, so a short run may report
`NO_FEASIBLE_SOLUTION_FOUND`. The notebook reports that status without adding
a custom schedule seed or replacing the original constraints.
