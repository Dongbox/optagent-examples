# Blackbox Examples

This directory contains examples where the objective or part of the model depends on Python-side blackbox logic.

## Supported modeling style

Typical primitives:

* `sequence_var(...)`
* `external_call(fn, ...)`
* blackbox objective with `minimize(...)`

## Supported solve forms

Primary solve path today:

* `PhaseConfig(..., solver=OrchestratorSolver.HEURISTIC, strategy=HeuristicStrategy.TABU)`
* `PhaseConfig(..., solver=OrchestratorSolver.HEURISTIC, heuristic_plan=HeuristicOrchestrationConfig(...))`

This category is important because exact backends are not the only intended execution mode in the current architecture.

## Included examples

* [routing_heuristic.py](../blackbox/routing_heuristic.py)
  Shows route ordering scored by a Python blackbox function and solved by the heuristic path.
* [steel_transition_sequence.py](../blackbox/steel_transition_sequence.py)
  Compatibility entrypoint for the steel coil direct-weld sequencing example. The canonical runnable version now lives at [../steel/steel_blackbox_sequence.py](../steel/steel_blackbox_sequence.py).
* [tsp_blackbox_small.py](../blackbox/tsp_blackbox_small.py)
  Shows a small TSP-style route scored entirely by a blackbox objective and solved by heuristic search.
* [tsp_evolutionary_small.py](../blackbox/tsp_evolutionary_small.py)
  Shows the same small TSP-style blackbox objective routed through the evolutionary heuristic path.
