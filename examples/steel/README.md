# Steel Examples

This directory hosts the shared domain layer for the steel coil sequencing problem and will become the landing area for both steel example styles:

* blackbox sequence optimization
* DAG-oriented sequence modeling

Current phase status:

* `steel_domain.py` defines the shared instance loader, welding rule, objective, and diagnostics.
* `blackbox_model.py` owns the blackbox steel sequence model definition.
* `dag_path_model.py` owns the DAG-oriented exact-path steel model definition.
* `solve_profiles.py` owns the steel example's default heuristic / exact / hybrid solve profiles.
* `run_blackbox.py` and `run_dag.py` own CLI entrypoints and summary shaping.
* `steel_blackbox_sequence.py` and `steel_dag_sequence.py` remain compatibility-facing thin wrappers.
* [../blackbox/steel_transition_sequence.py](/Users/dongbox/work/optagent/examples/blackbox/steel_transition_sequence.py) remains as a compatibility wrapper.
* the steel entrypoints now use steel-specific preset logic built on top of the shared sequence machinery:
  * shared internal seed: compatibility path merge + break-repair polish
  * blackbox default:
    * if the internal seed already reaches the `<=8` quality target, only run a short final polish
    * if the internal seed lands in the `9-16` mid band, run a targeted polish route before falling back to the heavier preset
    * otherwise fall back to a stronger seeded multi-island memetic + tabu path
  * DAG default:
    * small instances: exact-oriented
    * larger instances: seeded DAG path incumbent

Shared concepts exposed here:

* `SteelCoilInstance`
* `load_steel_instances()`
* `can_weld(...)`
* `transition_count(...)`
* `analyze_sequence(...)`
* `build_compatibility_matrix(...)`
* `build_penalty_matrix(...)`

Instance names currently available:

* `toy`
* `bundled_head40`
* `bundled`

Recommended commands:

```bash
PYTHONPATH=src .venv/bin/python examples/steel/steel_blackbox_sequence.py --instance toy --mode preset
PYTHONPATH=src .venv/bin/python examples/steel/steel_dag_sequence.py --instance toy --mode preset
PYTHONPATH=src .venv/bin/python examples/steel/steel_dag_sequence.py --instance bundled_head40 --mode exact
PYTHONPATH=src .venv/bin/python examples/steel/steel_dag_sequence.py --instance bundled --mode preset
PYTHONPATH=src .venv/bin/python examples/steel/steel_dag_sequence.py --instance bundled --mode seed
PYTHONPATH=src .venv/bin/python examples/steel/steel_blackbox_sequence.py --instance bundled_head40 --mode tabu --budget-iterations 200
PYTHONPATH=src .venv/bin/python scripts/run_steel_experiments.py --instance bundled_head40 --mode preset --seed 0 --seed 1 --json-output evals/steel/bundled_head40-preset.json
PYTHONPATH=src .venv/bin/python scripts/run_steel_search_attribution.py --instance bundled --search-seed 11 --json-output evals/steel/bundled-search-attribution.json
```

Search attribution workflow:

* `scripts/run_steel_search_attribution.py` is the recommended entrypoint when you need to separate:
  * seed-only quality
  * same-seed search improvement
  * perturbation recovery strength
* The attribution script explicitly keeps GA routes in the matrix:
  * `blackbox_evolutionary`
  * `blackbox_preset`
* The output is intended to answer:
  * how much quality comes from the initial constructive sequence
  * how much additional improvement comes from tabu / GA / DAG policy
