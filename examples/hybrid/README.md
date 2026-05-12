# Hybrid Examples

This directory contains examples that keep linear planning and scheduling semantics in the same DAG, then solve them through orchestrated multi-phase runs instead of forcing one isolated backend from the start.

## Supported modeling style

Typical primitives:

* `int_var(...)` for quantities, slack, and penalty terms
* `sequence_var(...)`
* `interval_var(...)`
* `interval_length(...)` / `interval_end(...)`
* `no_overlap(...)`
* linear coupling constraints across scalar and interval expressions

## Supported solve forms

Primary solve path today:

* `OrchestratorConfig(..., phases=[...])`
* alternating or sequential combinations of:
  * `PhaseConfig(..., solver=OrchestratorSolver.HEURISTIC)`
  * `PhaseConfig(..., solver=OrchestratorSolver.CP_SAT)`
  * `PhaseConfig(..., solver=OrchestratorSolver.MILP)`
* `execution_mode=ExecutionMode.ALTERNATING`

This category is where the current architecture is most visible: one DAG model can carry mixed semantics, and the orchestrator decides whether to seed with heuristic, route to an exact family, or fall back when lowering is not available.

## Included examples

* [hybrid_production_planning_small.py](../hybrid/hybrid_production_planning_small.py)
  Shows a small production planning problem where local output is coupled to interval lengths on a shared line, while outsourcing and tardiness stay in the linear part of the DAG. The solve path alternates heuristic seeding and CP-SAT exact refinement.
