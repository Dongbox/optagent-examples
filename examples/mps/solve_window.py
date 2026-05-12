from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from optagent import ExactBackendName, Orchestrator, load_strategy_preset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mps.mps_builder import build_program_from_mps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OptAgent models from MPS windows and solve them through heuristic, hybrid, or exact OptAgent presets.")
    parser.add_argument("--window", type=int, choices=range(6), help="Window index in examples/mps/window_<idx>.mps")
    parser.add_argument("--mps-file", type=Path, help="Explicit MPS file path. Overrides --window when provided.")
    parser.add_argument(
        "--mode",
        choices=["heuristic", "hybrid", "exact"],
        default="heuristic",
        help="Solve mode. Defaults to heuristic to exercise the OptAgent heuristic path.",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", ExactBackendName.MATHOPT_MP.value, ExactBackendName.HIGHS_NATIVE.value],
        default="auto",
        help="Concrete MP backend override for exact-capable modes. Default routes through the milp family registry.",
    )
    parser.add_argument(
        "--preset",
        type=Path,
        help="Explicit external preset file. When omitted, a built-in examples/mps preset is selected from --mode.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Build the OptAgent program and print model summary without calling the solver.",
    )
    return parser.parse_args()


def resolve_mps_path(args: argparse.Namespace) -> Path:
    if args.mps_file is not None:
        return args.mps_file.resolve()
    if args.window is None:
        raise SystemExit("one of --window or --mps-file is required")
    return Path(__file__).with_name(f"window_{args.window}.mps")


def main() -> None:
    args = parse_args()
    mps_path = resolve_mps_path(args)
    preferred_backend = None if args.backend == "auto" else args.backend

    build_start = perf_counter()
    built = build_program_from_mps(mps_path, preferred_backend=preferred_backend)
    build_seconds = perf_counter() - build_start

    payload: dict[str, Any] = {
        "title": "optagent mps window",
        "mps_path": str(mps_path),
        "mode": args.mode,
        "build_seconds": round(build_seconds, 3),
        "model_summary": built.summary(),
        "requested_backend": args.backend,
    }
    if args.summary_only:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    preset_path = args.preset or _default_preset_path(args.mode)
    preset = load_strategy_preset(preset_path, program=built.program)
    solve_start = perf_counter()
    result = Orchestrator().run(built.program, preset=preset)
    solve_seconds = perf_counter() - solve_start
    solution = result.final_solution

    nonzero_variables = {
        name: value
        for name, value in solution.variable_values.items()
        if isinstance(value, (int, float)) and abs(float(value)) > 1e-9
    }
    sample_nonzero = dict(list(sorted(nonzero_variables.items()))[:25])

    payload.update(
        {
            "solve_seconds": round(solve_seconds, 3),
            "selected_preset": result.selected_preset_name,
            "selected_preset_source": result.selected_preset_source,
            "preset_path": str(preset_path),
            "solver_name": solution.solver_name,
            "status": solution.status.value,
            "feasible": solution.feasible,
            "objective_values": solution.objective_values,
            "solution_metadata": solution.metadata,
            "nonzero_variable_count": len(nonzero_variables),
            "nonzero_variable_sample": sample_nonzero,
        }
    )
def _default_preset_path(mode: str) -> Path:
    if mode == "exact":
        return Path(__file__).with_name("resource_flow_exact_preset.json")
    if mode == "hybrid":
        return Path(__file__).with_name("resource_flow_hybrid_preset.json")
    return Path(__file__).with_name("resource_flow_heuristic_preset.json")


if __name__ == "__main__":
    main()
