# Group Seat Reservation Knapsack Problem

This directory contains a notebook that models a group seat reservation
knapsack problem using OptAgent. The final cells solve the bundled
`G20N10_30_0.txt` instance and print the utilization and allocated seat ranges
for selected requests.

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
cd examples/hexaly/group_seat_reservation_knapsack_problem_gsr_kp
python -m jupyter lab group_seat_reservation_knapsack_problem_gsr_kp.ipynb
```

Run the notebook cells in order. The final cell solves
`instances/G20N10_30_0.txt` with a five-second time limit. Other bundled
instances are available in `instances/` for additional experiments. Optional
intervals start absent in the current OptAgent search, so a short run may keep
the feasible empty allocation with utilization zero.
