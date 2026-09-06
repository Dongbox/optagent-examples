# Pooling

Install `optagent` and `jupyter`, open `pooling_problem.ipynb`, and run the
implementation cell followed by one of its `main(INSTANCE_DIR / ..., time_limit=10)`
instance calls.

Zero-capacity arcs are represented by a shared zero constant. Quality and cost
sums omit only terms proven zero from the instance's static bounds or coefficients;
all nonzero flows, proportion constraints, demands and quality limits remain.
Component-to-product flows through pools are shared across constraints and costs.
The native conditional linear worker can optimize a flow block with the current
mixing fractions fixed; the original nonlinear model certifies each proposal.
