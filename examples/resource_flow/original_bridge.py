from __future__ import annotations

from dataclasses import dataclass, replace
import importlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import types
from typing import Any


DEFAULT_APS_PRE_DECISION_ROOT = Path("/Users/dongbox/work/aps-pre-decision")
APS_PRE_DECISION_ROOT = Path(os.environ.get("APS_PRE_DECISION_ROOT", str(DEFAULT_APS_PRE_DECISION_ROOT)))
ZJ_DATA_PATH = APS_PRE_DECISION_ROOT / "test_data" / "物流平衡" / "zj" / "合同清单2026.1.23.xlsx"
ZJ_CONFIG_DIR = APS_PRE_DECISION_ROOT / "app_lib" / "apps" / "resource_flow_optimizer" / "V2" / "test_config_dict" / "zj"


@dataclass
class ExternalCaseBundle:
    raw_config: Any
    solver_config: Any
    raw_model_input: Any
    solver_model_input: Any
    processed_contract_count: int
    filtered_contract_count: int
    source: str


def _aps_pre_decision_available() -> bool:
    return APS_PRE_DECISION_ROOT.exists()


def _install_stub_packages() -> None:
    for name, path in [
        ("app_lib", APS_PRE_DECISION_ROOT / "app_lib"),
        ("app_lib.apps", APS_PRE_DECISION_ROOT / "app_lib" / "apps"),
        ("app_lib.apps.resource_flow_optimizer", APS_PRE_DECISION_ROOT / "app_lib" / "apps" / "resource_flow_optimizer"),
        ("app_lib.apps.resource_flow_optimizer.V2", APS_PRE_DECISION_ROOT / "app_lib" / "apps" / "resource_flow_optimizer" / "V2"),
        ("algorithm_lib", APS_PRE_DECISION_ROOT / "algorithm_lib"),
        ("algorithm_lib.algorithms", APS_PRE_DECISION_ROOT / "algorithm_lib" / "algorithms"),
        ("algorithm_lib.algorithms.optimization", APS_PRE_DECISION_ROOT / "algorithm_lib" / "algorithms" / "optimization"),
        ("algorithm_lib.algorithms.optimization.cp_sat", APS_PRE_DECISION_ROOT / "algorithm_lib" / "algorithms" / "optimization" / "cp_sat"),
    ]:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    if str(APS_PRE_DECISION_ROOT) not in sys.path:
        sys.path.append(str(APS_PRE_DECISION_ROOT))


def _load_json(name: str) -> Any:
    return json.loads((ZJ_CONFIG_DIR / name).read_text(encoding="utf-8"))


def _parse_backlog_key(key_str: str) -> tuple[int, str]:
    day, priority = key_str.split("|")
    return int(day), priority


def _modules() -> dict[str, Any]:
    if not _aps_pre_decision_available():
        raise RuntimeError(
            "Original aps-pre-decision bridge is unavailable. "
            "Set APS_PRE_DECISION_ROOT to a valid checkout if you need the original preprocess or CP-SAT builder."
        )
    _install_stub_packages()
    return {
        "config": importlib.import_module("app_lib.apps.resource_flow_optimizer.V2.config"),
        "preprocess": importlib.import_module("app_lib.apps.resource_flow_optimizer.V2.preprocess"),
        "builder": importlib.import_module("app_lib.apps.resource_flow_optimizer.V2.model_builder.cp_sat"),
        "weight_utils": importlib.import_module("app_lib.apps.resource_flow_optimizer.V2.weight_utils"),
    }


def load_external_zj_case(*, planning_period: int = 3, model_impl: str = "cp_sat") -> ExternalCaseBundle:
    import pandas as pd

    modules = _modules()
    ResourceFlowConfig = modules["config"].ResourceFlowConfig
    preprocess_module = modules["preprocess"]
    preprocess = preprocess_module.preprocess

    def _resolve_column(frame: pd.DataFrame, target: str) -> Any:
        if target in frame.columns:
            return target
        for column in frame.columns:
            if str(column).strip() == target:
                return column
        raise KeyError(target)

    def _bridge_integrate_contract_procedure(contract_df: pd.DataFrame, backlog_idx_range: list[int]) -> pd.DataFrame:
        grouped = contract_df.copy()
        grouped["sub_backlog"] = grouped[preprocess_module.ContractRequiredColumns().backlog].apply(
            lambda value: "".join([str(value)[i - 1] for i in backlog_idx_range])
        )
        group_cols = [
            preprocess_module.ContractRequiredColumns().contract_no,
            preprocess_module.ContractRequiredColumns().contract_due,
            "sub_backlog",
        ]
        sum_cols = [
            column
            for column in list(
                set(preprocess_module.PROCESS_OWE_COLUMNS.values()).union(set(preprocess_module.PROCESS_INV_COLUMNS.values()))
            )
            if column in grouped.columns
        ]

        rows: list[pd.Series] = []
        for keys, frame in grouped.groupby(group_cols, dropna=False, sort=False):
            merged = preprocess_module._merge_contract_procedures_group(frame, sum_cols).copy()
            for column, item_value in zip(group_cols, keys):
                merged[column] = item_value
            rows.append(merged)
        return pd.DataFrame(rows).reset_index(drop=True)

    def _bridge_reset_contract_no(contract_df: pd.DataFrame) -> pd.DataFrame:
        contract_df = contract_df.copy()
        contract_no_name = preprocess_module.ContractRequiredColumns().contract_no
        due_name = preprocess_module.ContractRequiredColumns().contract_due
        if contract_no_name not in [str(column).strip() for column in contract_df.columns]:
            contract_df[contract_no_name] = contract_df.index.to_series().map(contract_df_original[contract_no_name])
        if due_name not in [str(column).strip() for column in contract_df.columns]:
            contract_df[due_name] = contract_df.index.to_series().map(contract_df_original[due_name])
        contract_no_col = _resolve_column(contract_df, contract_no_name)
        process_tag_col = _resolve_column(contract_df, preprocess_module.ContractRequiredColumns().process_tag)
        ordered = contract_df.sort_values(by=[contract_no_col, process_tag_col], kind="stable").copy()
        ordered["tmp_process_id"] = ordered.groupby(contract_no_col).cumcount()
        ordered["new_contract_no"] = ordered[contract_no_col].astype(str) + "_" + ordered["tmp_process_id"].astype(int).astype(str)
        ordered.drop(columns=["tmp_process_id"], inplace=True)
        return ordered

    preprocess_module._integrate_contract_procedure = _bridge_integrate_contract_procedure
    preprocess_module._reset_contract_no = _bridge_reset_contract_no

    contract_df = pd.read_excel(ZJ_DATA_PATH)
    contract_df_original = contract_df.copy()
    backlog_dict = {_parse_backlog_key(key): value for key, value in _load_json("backlog_dict.json").items()}
    m_logistics = [(origin, target) for origin, targets in _load_json("m_logistics.json").items() for target in targets]
    camp_capacity = _load_json("camp_capacity.json")
    capacity = {
        (machine, camp_label, day): cap
        for machine, machine_camps in camp_capacity.items()
        for camp_label, cap in machine_camps.items()
        for day in range(1, planning_period + 2)
    }
    i_range = {
        (machine, day): (low, high)
        for machine, (low, high) in _load_json("machine_I_range.json").items()
        for day in range(0, planning_period + 2)
    }
    raw_config = ResourceFlowConfig(
        model_impl=model_impl,
        t0_date="2026-01-23",
        m_real=list(camp_capacity.keys()),
        m_logistics=m_logistics,
        m_real_key=["D202"],
        m_line=_load_json("machine_line.json"),
        I_range=i_range,
        I_expect=_load_json("machine_I_expect.json"),
        capacity=capacity,
        m_source_capacity={day: 30900 for day in range(1, planning_period + 2)},
        planning_period=planning_period,
        backlog_dict=backlog_dict,
        m_yield={machine: int(yield_percent * 1000) for machine, yield_percent in _load_json("machine_yield.json").items()},
        time_limit=600,
        step=1,
        window_period=3,
    )

    class _Logger:
        def info(self, *_args: Any, **_kwargs: Any) -> None:
            return

        def error(self, *_args: Any, **_kwargs: Any) -> None:
            return

    raw_model_input, _processed_df, filtered_out_df = preprocess(raw_input_data=contract_df, config=raw_config, logger=_Logger())

    solver_config = raw_config
    solver_model_input = raw_model_input
    if model_impl == "cp_sat":
        solver_config = scale_cp_sat_config(raw_config, modules["weight_utils"])
        solver_model_input = scale_cp_sat_model_input(raw_model_input, raw_config, modules["weight_utils"])

    return ExternalCaseBundle(
        raw_config=raw_config,
        solver_config=solver_config,
        raw_model_input=raw_model_input,
        solver_model_input=solver_model_input,
        processed_contract_count=len(solver_model_input.D),
        filtered_contract_count=len(filtered_out_df),
        source=f"external:{APS_PRE_DECISION_ROOT}",
    )


def scale_cp_sat_config(config: Any, weight_utils: Any | None = None) -> Any:
    modules = _modules() if weight_utils is None else None
    weight_utils = weight_utils or modules["weight_utils"]
    scale_weight = weight_utils.scale_weight

    def scale_optional(value: float | int) -> int:
        return -1 if value == -1 else scale_weight(value, config=config)

    scaled_i_range = {key: (scale_optional(bounds[0]), scale_optional(bounds[1])) for key, bounds in config.I_range.items()}
    scaled_i_expect = {key: (scale_optional(bounds[0]), scale_optional(bounds[1])) for key, bounds in config.I_expect.items()}
    scaled_capacity = {key: scale_weight(value, config=config) for key, value in config.capacity.items()}
    scaled_m_source_capacity = {key: scale_weight(value, config=config) for key, value in config.m_source_capacity.items()}
    scaled_initial_hint = None
    initial_hint = getattr(config, "initial_hint", None)
    if initial_hint:
        scaled_initial_hint = {
            var_name: scale_weight(value, config=config)
            if var_name.startswith(("x_d", "I_m", "I_d", "O_m", "O_d", "R_d", "C_d", "delta_I_range_", "delta_I_expect_"))
            else value
            for var_name, value in initial_hint.items()
        }
    utility_scale = weight_utils.get_weight_scale(config)
    utility_coeff = config.cost_coeff_utility
    scaled_cost_coeff_utility = utility_coeff if utility_coeff >= utility_scale and utility_coeff % utility_scale == 0 else utility_coeff * utility_scale

    if hasattr(config, "model_copy"):
        return config.model_copy(
            deep=True,
            update={
                "I_range": scaled_i_range,
                "I_expect": scaled_i_expect,
                "capacity": scaled_capacity,
                "m_source_capacity": scaled_m_source_capacity,
                "initial_hint": scaled_initial_hint,
                "cost_coeff_utility": scaled_cost_coeff_utility,
            },
        )
    copied = dict(vars(config))
    copied.update(
        {
            "I_range": scaled_i_range,
            "I_expect": scaled_i_expect,
            "capacity": scaled_capacity,
            "m_source_capacity": scaled_m_source_capacity,
            "initial_hint": scaled_initial_hint,
            "cost_coeff_utility": scaled_cost_coeff_utility,
        }
    )
    return SimpleNamespace(**copied)


def scale_cp_sat_model_input(model_input: Any, config: Any, weight_utils: Any | None = None) -> Any:
    modules = _modules() if weight_utils is None else None
    weight_utils = weight_utils or modules["weight_utils"]
    scale_weight = weight_utils.scale_weight
    updates = {
        "I_d_m_0": {key: scale_weight(value, config=config) for key, value in model_input.I_d_m_0.items()},
        "I_d_m_0_excess": {key: scale_weight(value, config=config) for key, value in model_input.I_d_m_0_excess.items()},
        "I_m_0": {key: scale_weight(value, config=config) for key, value in model_input.I_m_0.items()},
        "Q_d": {key: scale_weight(value, config=config) for key, value in model_input.Q_d.items()},
        "x_t0": {key: scale_weight(value, config=config) for key, value in model_input.x_t0.items()},
        "owe_d_m": {key: scale_weight(value, config=config) for key, value in model_input.owe_d_m.items()},
    }
    if hasattr(model_input, "__dataclass_fields__"):
        return replace(model_input, **updates)
    copied = dict(vars(model_input))
    copied.update(updates)
    return SimpleNamespace(**copied)


def build_original_cp_sat_model(
    config: Any,
    model_input: Any,
    *,
    modeling_period: int,
    k: int = 0,
) -> tuple[dict[str, str], dict[str, Any], Any, dict[str, int]]:
    modules = _modules()
    build_model = modules["builder"].build_model
    return build_model(config=config, model_input=model_input, modeling_period=modeling_period, k=k)
