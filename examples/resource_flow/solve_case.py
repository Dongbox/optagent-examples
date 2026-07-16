from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from optagent import CpSatConfig, GaConfig, MilpConfig, UnifiedSolution, solve, solve_cpsat, solve_milp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.resource_flow.case_loader import load_case
from examples.resource_flow.cp_builder import build_single_window_program
from examples.resource_flow.milp_builder import build_single_window_milp_program
from examples._common import solution_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve the bundled resource_flow case through CP or MILP formulations."
    )
    parser.add_argument("--case", default="zj")
    parser.add_argument("--formulation", choices=["cp", "milp"], default="cp")
    parser.add_argument("--planning-period", type=int, default=3)
    parser.add_argument("--modeling-period", type=int, default=3)
    parser.add_argument("--window-index", type=int, default=0)
    parser.add_argument("--mode", choices=["exact", "ga"], default="exact")
    parser.add_argument("--backend", choices=["auto", "optx", "mathopt_mp"], default="auto")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--time-limit-seconds", type=float)
    parser.add_argument("--exact-time-limit-seconds", type=float)
    parser.add_argument("--heuristic-total-budget", type=int, default=2)
    parser.add_argument("--seed-budget", type=int, default=1)
    parser.add_argument("--intensify-budget", type=int, default=1)
    parser.add_argument("--refine-budget", type=int, default=1)
    parser.add_argument("--heuristic-time-limit-seconds", type=float, default=1.0)
    parser.add_argument("--heuristic-max-candidate-moves", type=int, default=1)
    parser.add_argument("--heuristic-max-scalar-variables", type=int, default=1)
    parser.add_argument("--cp-workers", type=int)
    parser.add_argument("--mathopt-solver-type")
    parser.add_argument("--highs-profile-postsolve", action="store_true")
    return parser.parse_args()


def _build_program(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, int], Any]:
    case = load_case(case_name=args.case, formulation=args.formulation, planning_period=args.planning_period)
    preferred_backend = None if args.backend == "auto" else args.backend

    build_start = perf_counter()
    if args.formulation == "cp":
        built = build_single_window_program(
            case.config,
            case.model_input,
            modeling_period=args.modeling_period,
            k=args.window_index,
        )
    else:
        built = build_single_window_milp_program(
            case.config,
            case.model_input,
            modeling_period=args.modeling_period,
            k=args.window_index,
            preferred_backend=preferred_backend,
        )
    build_seconds = perf_counter() - build_start
    exact_time_limit_seconds = args.exact_time_limit_seconds
    if exact_time_limit_seconds is None:
        exact_time_limit_seconds = args.time_limit_seconds

    payload = {
        "case": case.case_name,
        "formulation": args.formulation,
        "planning_period": args.planning_period,
        "modeling_period": args.modeling_period,
        "window_index": args.window_index,
        "mode": args.mode,
        "backend": args.backend,
        "exact_time_limit_seconds": exact_time_limit_seconds,
        "heuristic_total_budget": args.heuristic_total_budget,
        "seed_budget": args.seed_budget,
        "intensify_budget": args.intensify_budget,
        "refine_budget": args.refine_budget,
        "heuristic_time_limit_seconds": args.heuristic_time_limit_seconds,
        "heuristic_max_candidate_moves": args.heuristic_max_candidate_moves,
        "heuristic_max_scalar_variables": args.heuristic_max_scalar_variables,
        "cp_workers": args.cp_workers,
        "mathopt_solver_type": args.mathopt_solver_type,
        "highs_profile_postsolve": args.highs_profile_postsolve,
        "bundle_source": case.source,
        "case_summary": case.summary(),
        "build_seconds": round(build_seconds, 3),
        "model_summary": built.summary(),
    }
    return payload, built.variable_node_ids, built.program


def _nonzero_sample(variable_values: dict[int, Any], variable_node_ids: dict[str, int]) -> dict[str, Any]:
    nonzero: dict[str, Any] = {}
    for name, node_id in variable_node_ids.items():
        value = variable_values.get(node_id)
        if isinstance(value, bool):
            if value:
                nonzero[name] = value
            continue
        if isinstance(value, (int, float)) and abs(float(value)) > 1e-9:
            nonzero[name] = value
    return dict(list(sorted(nonzero.items()))[:25])


def _exact_solve(args: argparse.Namespace, program: Any) -> Any:
    if args.formulation == "cp":
        return solve_cpsat(
            program,
            config=CpSatConfig(
                time_limit_s=args.exact_time_limit_seconds or args.time_limit_seconds,
                workers=args.cp_workers,
                log_to_stdout=False,
            ),
        )
    backend_name = "optx" if args.backend == "auto" else args.backend
    return solve_milp(
        program,
        config=MilpConfig(
            backend=backend_name,
            time_limit_s=args.exact_time_limit_seconds or args.time_limit_seconds,
        ),
    )


def _ga_solve(args: argparse.Namespace, program: Any) -> UnifiedSolution:
    iterations = max(1, args.heuristic_total_budget or args.seed_budget + args.intensify_budget)
    return solve(
        program,
        strategy=GaConfig(
            max_iterations=iterations,
            population_size=6,
        ),
        max_iterations=iterations,
        time_limit_s=args.heuristic_time_limit_seconds or 1.0,
        seed=0,
        trace_output="summary",
    )


def main() -> None:
    args = parse_args()
    payload, variable_node_ids, program = _build_program(args)
    if args.summary_only:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return
    try:
        solve_start = perf_counter()
        if args.mode == "exact":
            solution = _exact_solve(args, program)
        else:
            solution = _ga_solve(args, program)
        solve_seconds = perf_counter() - solve_start
        payload.update(
            {
                "solve_seconds": round(solve_seconds, 3),
                "solver_name": solution.solver_name,
                "status": solution.status.value,
                "feasible": solution.feasible,
                "objective_values": solution.objective_values,
                "solution_metadata": solution_metadata(solution),
                "nonzero_variable_sample": _nonzero_sample(solution.variable_values, variable_node_ids),
            }
        )
    except Exception as exc:
        payload["error"] = {"type": type(exc).__name__, "message": str(exc)}
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
