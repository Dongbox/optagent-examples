# MG OptAgent Migration Example

This directory contains the first OptAgent migration scaffold for an APS-compatible MG scheduling project.

The implementation is intentionally a sequence-blackbox model, organized to mirror the original MG `program/` layout:

- `program/scripts/preprocess/data.py` loads the MG SQLite contract from `i_*` and `t_*` tables.
- `program/scripts/preprocess/data.py` defines the shared MG case, task, score, and parity dataclasses.
- `program/scripts/preprocess/transformer.py` keeps the original APS `Transformer`-style `CustomTransformer` and `main(in_addr, out_addr)` contract.
- `program/scripts/preprocess/tables/`, `generators.py`, and `validators.py` carry the MG project-specific APS preprocess extensions used by the common transformer.
- `program/scripts/preprocess/data.py` validates that the original common preprocess has generated required model tables.
- `program/model/rules.py` reimplements the main MG rule-cost semantics in Python for scoring and diagnostics.
- `program/model/model.py` builds an OptAgent `sequence_var(...)` model with `external_call(...)` scoring.
- `program/model/search.py` defines tabu, polish, and evolutionary heuristic configurations.
- `program/model/search.py` runs the actual OptAgent sequence search.
- `program/model/reports.py` contains parity, structured-edge, search-replacement, and SQLite production-output reporting helpers.
- `program/main.py` is the formal replacement for the APS model phase.
- `program/scripts/postprocess/postprocess.py` creates JSON summaries and SQLite output tables.
- `program/scripts/postprocess/postprocess.py` maps OptAgent outputs to compatibility tables for downstream postprocess flows.
- `program/main.py` is the top-level pipeline entrypoint, mirroring the original MG `program/main.py` flow.

Run from the repository root:

```bash
PYTHONPATH=. python examples/mg/program/main.py examples/mg/program/data/20260407000000.db
```

The production entrypoint accepts one SQLite path. Preprocess input, model
input, OptAgent output, compatibility output, and postprocess output are written
in that same SQLite file. APS preprocessing failures are fatal; the model and
postprocess stages do not run after a failed preprocess.

Migration-time parity and diagnostic reports are available as Python APIs in
`program/model/reports.py`:

- `build_parity_report(...)`
- `build_search_replacement_report(...)`
- `build_structured_report(...)`
- `run_production_case(...)`

These helpers are separated from `program/model/search.py` so actual model
construction and search execution remain focused on solving.

Production output tables:

- `o_mg_optagent_sequence`: active and inactive order sequence selected by OptAgent.
- `o_mg_optagent_rule_cost`: detailed Python rule costs plus `total`.
- `o_mg_optagent_run_manifest`: selected mode/seed, baseline cost, best cost, APS comparison, budget, and source caveats.
- `o_mg_optagent_diagnostics`: score diagnostics, grouped rule costs, APS notes, and production notes as JSON values.
- `o_mg_optagent_search_run`: every profile/seed candidate run with ranking, cost, sequence JSON, and trace counts.

Formal integration data flow:

```text
program/scripts/preprocess/
  original common preprocess generates i_* and t_* tables
  transformer.py keeps the APS Transformer-style entrypoint
  tables/generators/validators keep the MG custom APS preprocess extensions

program/model/
  program/main.py runs the OptAgent model phase in place of APS Agent.run()
  input: SQLite i_* / t_* tables
  output: o_mg_optagent_* tables

program/scripts/postprocess/
  original postprocess can continue
  postprocess.py can map outputs to o_process_output_optagent and o_rules_cost_optagent

program/main.py
  orchestrates preprocess, OptAgent model, and postprocess stages
```

Current scope:

- SQLite case loading from the existing MG table contract.
- Warm-start/default sequence from `t_process_output`.
- Active-prefix behavior based on `MGContext` cumulative weight semantics.
- Rule-cost breakdown for the main MG C++ rule families.
- APS parity report over grouped rule names: `MGLeftMat`, `MGSmooth`, `MGHardCamp`, `MGDiscontinuable`, `MGOuterSandwich`, `MGThinCamp`, `MGPostProcessCamp`, `MGChangeRoller`, and `MGGrindingBeforeOuter`.
- Structured edge metadata for stable adjacent-pair semantics: `MGDiscontinuable`, `MGSmooth`, `MGChangeRoller`, and `MGHardCamp`.
- OptAgent heuristic search over the sequence, including tabu, polish, and evolutionary profile matrices with multiple seeds.

Current limitations:

- The model is blackbox-scored; individual rules are not yet lowered into structured DAG constraints.
- Optional active/inactive behavior is represented inside the scorer as an active prefix over a full permutation.
- APS custom C++ mutation hooks are replaced by OptAgent sequence heuristics and evolutionary mutation portfolios rather than copied directly.
- `t_rules_cost` and `t_total_cost` are treated as APS output aggregates, not rule parameter sources.
- Some supplied MG SQLite snapshots may have `t_connectables.prev_order_id` and `curr_order_id` values that are not usable as order adjacency data, so parity falls back to task-attribute connectability and reports that caveat.
- Phase 2 focuses on auditable rule deltas and known semantic gaps, not zero-delta production parity certification.
- Phase 3 search replacement uses the current blackbox Python scorer as the objective. Search quality is therefore only as production-ready as the Phase 2 rule parity inputs.
- Phase 4 exposes structured edge metadata but still keeps the blackbox objective authoritative. Current OptAgent exact lowering does not support standalone sequence path optimization without interval/no-overlap structure.
- `MGChangeRoller.simple` is only partly represented in edge metadata because the full rule needs follower-window state.
- Phase 5 provides an integration runner and SQLite output contract, but production cutover still requires validating upstream `t_connectables` generation and full-size regression cases.
- The supplied `aps-2.0.5-py3-none-any.whl` declares `Python >=3.6.8, <=3.10.12`. Formal runs should use an APS-compatible Python/dependency stack. The example keeps APS preprocessing failures fatal.
