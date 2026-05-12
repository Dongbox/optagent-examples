from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.resource_flow.case_loader import load_case
from examples.resource_flow.cp_builder import build_single_window_program
from examples.resource_flow.original_bridge import build_original_cp_sat_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare the bundled resource_flow CP formulation against the original aps-pre-decision CP-SAT builder."
    )
    parser.add_argument("--planning-period", type=int, default=3)
    parser.add_argument("--modeling-period", type=int, default=3)
    parser.add_argument("--window-index", type=int, default=0)
    args = parser.parse_args()

    payload = {
        "case": "zj",
        "planning_period": args.planning_period,
        "modeling_period": args.modeling_period,
        "window_index": args.window_index,
    }
    try:
        case = load_case(case_name="zj", formulation="cp", planning_period=args.planning_period)
        built = build_single_window_program(
            case.config,
            case.model_input,
            modeling_period=args.modeling_period,
            k=args.window_index,
        )
        original_var_types, _, original_constraints, original_objective = build_original_cp_sat_model(
            case.config,
            case.model_input,
            modeling_period=args.modeling_period,
            k=args.window_index,
        )

        payload.update(
            {
                "bundle_source": case.source,
                "processed_contracts": case.processed_contract_count,
                "filtered_contracts": case.filtered_contract_count,
                "optagent": built.summary(),
                "original": {
                    "variable_count": len(original_var_types),
                    "linear_constraints": len(original_constraints.linear),
                    "logical_constraints": len(original_constraints.logical),
                    "arithmetic_constraints": len(original_constraints.arithmetic),
                    "min_max_constraints": len(original_constraints.min_max),
                    "all_different_constraints": len(original_constraints.all_different),
                    "abs_equality_constraints": len(original_constraints.abs_equality),
                    "objective_terms": len(original_objective),
                },
            }
        )
    except Exception as exc:
        payload["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
