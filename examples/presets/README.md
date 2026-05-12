# Preset-Driven Examples

This directory contains both explicit built-in preset examples and automatic preset selection examples.

These examples complement the existing explicit-orchestration examples:

* explicit examples show the raw orchestration API shape
* preset-driven examples show the user-facing preset flow without hand-writing orchestration wiring

Primary usage:

* explicit preset examples define one `SELECTED_PRESET = BuiltInStrategyPreset....`
* `Orchestrator().run(program, preset=SELECTED_PRESET)` accepts the enum member directly
* nearby comments list other reasonable built-in alternatives for that example
* external preset files should prefer `preset = load_strategy_preset(path, program=program)` and `Orchestrator().run(program, preset=preset)`
* automatic preset examples call `Orchestrator().run(program)` directly

Advanced inspect API:

* if you want to inspect the preset structure before running, use `get_strategy_preset(program, SELECTED_PRESET)` and then `print(preset)`

Included examples:

* [scheduling_memetic_quality_preset.py](../presets/scheduling_memetic_quality_preset.py)
  Uses the stage-1 scheduling memetic quality preset with repair plus local improvement.
* [scheduling_evolutionary_repair_preset.py](../presets/scheduling_evolutionary_repair_preset.py)
  Uses the built-in scheduling evolutionary repair preset on a small two-machine job shop.
* [scheduling_evolutionary_repair_large_preset.py](../presets/scheduling_evolutionary_repair_large_preset.py)
  Uses the same preset on a larger two-machine flow-shop-style scheduling model.
* [routing_blackbox_preset.py](../presets/routing_blackbox_preset.py)
  Uses an explicit built-in routing preset enum for a blackbox route objective.
* [hybrid_production_preset.py](../presets/hybrid_production_preset.py)
  Uses an explicit built-in hybrid-capable preset enum for a mixed planning-and-scheduling DAG.
* [routing_blackbox_auto_preset.py](../presets/routing_blackbox_auto_preset.py)
  Lets `Orchestrator().run(program)` auto-select the preset and exposes the selected preset in the result metadata.
