from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from .schema import ResourceFlowCase, to_namespace


BUNDLED_CASE_DIR = Path(__file__).resolve().parent / "data"
BUNDLED_CASES = {
    ("zj", "cp", 3): BUNDLED_CASE_DIR / "zj_case_cp_sat_p3.json.gz",
    ("zj", "milp", 3): BUNDLED_CASE_DIR / "zj_case_mathopt_p3.json.gz",
}


def _decode_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode_jsonable(item) for item in value]
    if not isinstance(value, dict):
        return value
    marker = value.get("__type__")
    if marker == "tuple":
        return tuple(_decode_jsonable(item) for item in value["items"])
    if marker == "iso_date":
        return value["value"]
    if marker == "dict_items":
        return {
            _decode_jsonable(key): _decode_jsonable(item_value)
            for key, item_value in value["items"]
        }
    return {key: _decode_jsonable(item_value) for key, item_value in value.items()}


def load_case(
    *,
    case_name: str = "zj",
    formulation: str = "cp",
    planning_period: int = 3,
) -> ResourceFlowCase:
    bundle_path = BUNDLED_CASES.get((case_name, formulation, planning_period))
    if bundle_path is None or not bundle_path.exists():
        raise FileNotFoundError(
            f"No bundled resource_flow case is available for case={case_name!r}, formulation={formulation!r}, planning_period={planning_period}."
        )
    with gzip.open(bundle_path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)

    config_data = _decode_jsonable(payload["solver_config"])
    model_input_data = _decode_jsonable(payload["solver_model_input"])
    config = to_namespace(config_data)
    model_input = to_namespace(model_input_data)
    return ResourceFlowCase(
        case_name=case_name,
        formulation=formulation,
        planning_period=planning_period,
        config=config,
        model_input=model_input,
        processed_contract_count=int(payload["meta"]["processed_contract_count"]),
        filtered_contract_count=int(payload["meta"]["filtered_contract_count"]),
        source=f"bundled:{bundle_path.name}",
        metadata={
            "model_impl": payload["meta"].get("model_impl"),
        },
    )
