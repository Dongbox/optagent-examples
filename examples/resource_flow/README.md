# Resource Flow Examples

This directory contains the self-contained OptAgent `resource_flow` example extracted from the original `/Users/dongbox/work/aps-pre-decision` project.

Included pieces:

* [case_loader.py](/Users/dongbox/work/optagent/examples/resource_flow/case_loader.py)
  Loads bundled `zj` case snapshots through a shared schema.
* [schema.py](/Users/dongbox/work/optagent/examples/resource_flow/schema.py)
  Defines the shared case container used by both formulations.
* [cp_builder.py](/Users/dongbox/work/optagent/examples/resource_flow/cp_builder.py)
  Single-window CP-style formulation with CP-SAT oriented constraints.
* [milp_builder.py](/Users/dongbox/work/optagent/examples/resource_flow/milp_builder.py)
  Single-window algebraic MILP formulation for `milp` family backends such as `mathopt_mp` and `highs_native`.
* [solve_case.py](/Users/dongbox/work/optagent/examples/resource_flow/solve_case.py)
  Unified entrypoint for the bundled case across formulations and solve modes.
* [rolling.py](/Users/dongbox/work/optagent/examples/resource_flow/rolling.py)
  Workflow-layer rolling-window runner for the CP formulation with warm-start shifting and state carry-over.
* [original_bridge.py](/Users/dongbox/work/optagent/examples/resource_flow/original_bridge.py)
  Optional external-project bridge for migration and original CP-SAT builder comparison. It is no longer part of the default bundled runtime path.
* [compare_original.py](/Users/dongbox/work/optagent/examples/resource_flow/compare_original.py)
  Migration-time comparison script for the bundled CP case against the original external CP-SAT builder.

Run from the repository root:

```bash
PYTHONPATH=src python examples/resource_flow/solve_case.py --formulation cp --summary-only
PYTHONPATH=src python examples/resource_flow/solve_case.py --formulation milp --summary-only
PYTHONPATH=src python examples/resource_flow/solve_case.py --formulation cp --mode hybrid
PYTHONPATH=src python examples/resource_flow/solve_case.py --formulation milp --mode exact --backend highs_native
PYTHONPATH=src python examples/resource_flow/compare_original.py --planning-period 3 --modeling-period 3
```

Default bundled behavior is self-contained for the shipped `planning_period=3` `zj` case. No files from `aps-pre-decision` are required for `case_loader.py`, `cp_builder.py`, `milp_builder.py`, or `solve_case.py`.

The migration-only `compare_original.py` path still needs an `aps-pre-decision` checkout reachable through `APS_PRE_DECISION_ROOT` or the default local path.

Current scope:

* shared bundled case schema
* single-window `cp` formulation
* single-window `milp` formulation
* unified solve entrypoint for exact / heuristic / hybrid modes
* CP rolling-window workflow shell
* optional original-model comparison bridge

Current limitations:

* the bundled real-case snapshots currently cover `planning_period=3` only
* `solve_case.py` can enter large-instance exact solve paths, but full bundled `zj` solve times are backend- and budget-dependent
* original-model comparison still targets the `aps-pre-decision` layout and is not a generic package loader
* the rolling shell currently lives at the example/workflow layer, not in the core `Orchestrator`
