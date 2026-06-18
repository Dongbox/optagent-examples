from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from optagent import CpSatConfig, solve_cpsat

from .cp_builder import advance_window_input, build_single_window_program, roll_named_warm_start


@dataclass
class RollingWindowStep:
    window_index: int
    modeling_period: int
    named_values: dict[str, Any]
    objective_values: dict[int, Any]
    summary: dict[str, Any]


@dataclass
class RollingWindowResult:
    steps: list[RollingWindowStep]


def run_rolling_cp_sat(config: Any, model_input: Any) -> RollingWindowResult:
    steps: list[RollingWindowStep] = []
    current_input = model_input
    previous_named_values: dict[str, Any] = {}

    if config.step == 0 or config.window_period == 0:
        solve_times = 1
    else:
        solve_times = max(((config.planning_period + 1 - config.window_period) + config.step - 1) // config.step + 1, 1)

    for k in range(solve_times):
        modeling_period = (
            config.planning_period + 1
            if config.step == 0 or config.window_period == 0
            else min(config.window_period, config.planning_period - k * config.step + 1)
        )
        built = build_single_window_program(config, current_input, modeling_period=modeling_period, k=k)
        named_hint = previous_named_values if k == 0 else roll_named_warm_start(previous_named_values, config.step)
        warm_start = {
            built.variable_node_ids[name]: value
            for name, value in named_hint.items()
            if name in built.variable_node_ids
        }
        solution = solve_cpsat(
            built.program,
            warm_start=warm_start or None,
            config=CpSatConfig(time_limit_s=10.0, workers=1),
        )
        named_values = {
            name: solution.variable_values[node_id]
            for name, node_id in built.variable_node_ids.items()
        }
        steps.append(
            RollingWindowStep(
                window_index=k,
                modeling_period=modeling_period,
                named_values=named_values,
                objective_values=dict(solution.objective_values),
                summary=built.summary(),
            )
        )
        previous_named_values = named_values
        if k + 1 < solve_times:
            current_input = advance_window_input(config, current_input, named_values)

    return RollingWindowResult(steps=steps)
