from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from optagent import GaConfig, MilpConfig, solve, solve_milp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import solution_metadata
from mps.mps_builder import build_program_from_mps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an OptAgent model from an MPS window and solve it with current direct APIs."
    )
    parser.add_argument("--window", type=int, choices=range(6), help="Window index in examples/mps/window_<idx>.mps")
    parser.add_argument("--mps-file", type=Path, help="Explicit MPS file path. Overrides --window when provided.")
    parser.add_argument(
        "--mode",
        choices=["exact", "heuristic"],
        default="exact",
        help="exact uses solve_milp; heuristic uses solve(...) with GaConfig for smoke-scale MPS experiments.",
    )
    parser.add_argument(
        "--backend",
        choices=["optx", "mathopt_mp"],
        default="optx",
        help="MP backend for exact mode. optx is the internal backend; mathopt_mp demonstrates the external adapter.",
    )
    parser.add_argument(
        "--summary-only", action="store_true", help="Build the program and print model summary without solving."
    )
    parser.add_argument("--time-limit-s", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=11)
    return parser.parse_args()


def resolve_mps_path(args: argparse.Namespace) -> Path:
    if args.mps_file is not None:
        return args.mps_file.resolve()
    if args.window is None:
        raise SystemExit("one of --window or --mps-file is required")
    return Path(__file__).with_name(f"window_{args.window}.mps")


def _nonzero_sample(variable_values: dict[int, Any], variable_node_ids: dict[str, int]) -> dict[str, Any]:
    nonzero: dict[str, Any] = {}
    for name, node_id in variable_node_ids.items():
        value = variable_values.get(node_id)
        if isinstance(value, bool):
            if value:
                nonzero[name] = value
        elif isinstance(value, (int, float)) and abs(float(value)) > 1e-9:
            nonzero[name] = value
    return dict(list(sorted(nonzero.items()))[:25])


def main() -> None:
    args = parse_args()
    mps_path = resolve_mps_path(args)

    build_start = perf_counter()
    built = build_program_from_mps(mps_path, preferred_backend=args.backend if args.mode == "exact" else None)
    build_seconds = perf_counter() - build_start

    payload: dict[str, Any] = {
        "title": "optagent mps window",
        "mps_path": str(mps_path),
        "mode": args.mode,
        "backend": args.backend,
        "build_seconds": round(build_seconds, 3),
        "model_summary": built.summary(),
    }
    if args.summary_only:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    solve_start = perf_counter()
    if args.mode == "exact":
        solution = solve_milp(
            built.program,
            config=MilpConfig(
                backend=args.backend,
                time_limit_s=args.time_limit_s,
            ),
        )
    else:
        solution = solve(
            built.program,
            strategy=GaConfig(
                max_iterations=40,
                population_size=8,
            ),
            seed=args.seed,
            time_limit_s=args.time_limit_s,
            trace_output="summary",
        )
    solve_seconds = perf_counter() - solve_start

    payload.update(
        {
            "solve_seconds": round(solve_seconds, 3),
            "solver_name": solution.solver_name,
            "status": solution.status.value,
            "feasible": solution.feasible,
            "objective_values": solution.objective_values,
            "solution_metadata": solution_metadata(solution),
            "nonzero_variable_sample": _nonzero_sample(solution.variable_values, built.variable_node_ids),
        }
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
