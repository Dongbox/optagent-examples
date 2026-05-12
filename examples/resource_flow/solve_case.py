from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from optagent import CpSatSolver, ExactBackendName, MilpSolver
from optagent.heuristic import HeuristicConfig, HeuristicSolver
from optagent.solution.models import SolutionStatus, UnifiedSolution

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.resource_flow.case_loader import load_case
from examples.resource_flow.cp_builder import build_single_window_program
from examples.resource_flow.milp_builder import build_single_window_milp_program


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve the bundled resource_flow case through CP or MILP formulations.")
    parser.add_argument("--case", default="zj")
    parser.add_argument("--formulation", choices=["cp", "milp"], default="cp")
    parser.add_argument("--planning-period", type=int, default=3)
    parser.add_argument("--modeling-period", type=int, default=3)
    parser.add_argument("--window-index", type=int, default=0)
    parser.add_argument("--mode", choices=["exact", "heuristic", "hybrid"], default="exact")
    parser.add_argument(
        "--backend",
        choices=["auto", ExactBackendName.CP_SAT_NATIVE.value, ExactBackendName.HIGHS_NATIVE.value, ExactBackendName.MATHOPT_MP.value],
        default="auto",
    )
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
    built.program.solve_config["solver_log_output"] = True
    built.program.solve_config["solver_log_to_stdout"] = True
    if args.highs_profile_postsolve:
        built.program.solve_config["highs_profile_postsolve"] = True
    if preferred_backend and args.formulation == "cp":
        built.program.solve_config["preferred_backend"] = preferred_backend
    exact_time_limit_seconds = args.exact_time_limit_seconds
    if exact_time_limit_seconds is None:
        exact_time_limit_seconds = args.time_limit_seconds
    if exact_time_limit_seconds is not None:
        built.program.solve_config["time_limit_seconds"] = exact_time_limit_seconds
    if args.heuristic_time_limit_seconds is not None:
        built.program.solve_config["heuristic_time_limit_seconds"] = args.heuristic_time_limit_seconds
    if args.heuristic_max_candidate_moves is not None:
        built.program.solve_config["heuristic_max_candidate_moves"] = args.heuristic_max_candidate_moves
    if args.heuristic_max_scalar_variables is not None:
        built.program.solve_config["heuristic_max_scalar_variables"] = args.heuristic_max_scalar_variables
    if args.cp_workers is not None:
        built.program.solve_config["cp_num_search_workers"] = args.cp_workers
    if args.mathopt_solver_type:
        built.program.solve_config["mathopt_solver_type"] = args.mathopt_solver_type

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
        return CpSatSolver().solve(program).solution
    backend_name = None if args.backend == "auto" else args.backend
    return MilpSolver().solve(program, backend_name=backend_name).solution


def _build_heuristic_solution(result: Any, *, phase_name: str) -> UnifiedSolution:
    status = SolutionStatus.FEASIBLE if result.feasible else SolutionStatus.FALLBACK
    return UnifiedSolution(
        solver_name="heuristic",
        status=status,
        variable_values=dict(result.best_state.variable_values),
        objective_values=dict(result.best_objective_values),
        constraint_values=dict(result.best_constraint_values),
        feasible=result.feasible,
        dag_recheck_passed=True,
        metadata={
            "phase_name": phase_name,
            "strategy": result.strategy,
            "iterations_run": result.iterations_run,
            "termination_reason": result.termination_reason,
            "metrics": {
                "attempts": result.metrics.attempts,
                "accepted_moves": result.metrics.accepted_moves,
                "rejected_moves": result.metrics.rejected_moves,
                "improving_moves": result.metrics.improving_moves,
                "rollback_count": result.metrics.rollback_count,
            },
        },
    )


def _run_heuristic_phase(
    args: argparse.Namespace,
    program: Any,
    *,
    phase_name: str,
    strategy: str,
    budget_iterations: int,
    warm_start: dict[int, Any] | None,
    seed: int,
) -> UnifiedSolution:
    result = HeuristicSolver().solve(
        program,
        config=HeuristicConfig(
            seed=seed,
            max_iterations=max(1, budget_iterations),
            phase_budget=max(1, budget_iterations),
            strategy=strategy,
            restart_limit=1,
            warm_start=warm_start,
            time_limit_seconds=args.heuristic_time_limit_seconds,
            enable_lns=False,
            max_candidate_moves_per_iteration=args.heuristic_max_candidate_moves,
            max_scalar_variables_per_iteration=args.heuristic_max_scalar_variables,
        ),
    )
    return _build_heuristic_solution(result, phase_name=phase_name)


def _heuristic_solve(args: argparse.Namespace, program: Any) -> UnifiedSolution:
    seed_solution = _run_heuristic_phase(
        args,
        program,
        phase_name="seed",
        strategy="annealing",
        budget_iterations=args.seed_budget,
        warm_start=None,
        seed=0,
    )
    if args.intensify_budget <= 0:
        return seed_solution
    return _run_heuristic_phase(
        args,
        program,
        phase_name="intensify",
        strategy="tabu",
        budget_iterations=args.intensify_budget,
        warm_start=seed_solution.variable_values,
        seed=1,
    )


def _hybrid_solve(args: argparse.Namespace, program: Any) -> UnifiedSolution:
    heuristic_solution = _run_heuristic_phase(
        args,
        program,
        phase_name="seed",
        strategy="annealing",
        budget_iterations=args.seed_budget,
        warm_start=None,
        seed=0,
    )
    try:
        if args.formulation == "cp":
            exact_solution = CpSatSolver().solve(program, warm_start=heuristic_solution.variable_values).solution
        else:
            backend_name = None if args.backend == "auto" else args.backend
            exact_solution = MilpSolver().solve(
                program,
                warm_start=heuristic_solution.variable_values,
                backend_name=backend_name,
            ).solution
        exact_solution.metadata = {
            **exact_solution.metadata,
            "hybrid_seed_solver": heuristic_solution.solver_name,
            "hybrid_seed_status": heuristic_solution.status.value,
            "hybrid_seed_feasible": heuristic_solution.feasible,
        }
        return exact_solution
    except Exception as exc:
        heuristic_solution.metadata = {
            **heuristic_solution.metadata,
            "hybrid_exact_error": {"type": type(exc).__name__, "message": str(exc)},
        }
        return heuristic_solution


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
        elif args.mode == "heuristic":
            solution = _heuristic_solve(args, program)
        else:
            solution = _hybrid_solve(args, program)
        solve_seconds = perf_counter() - solve_start
        payload.update(
            {
                "solve_seconds": round(solve_seconds, 3),
                "solver_name": solution.solver_name,
                "status": solution.status.value,
                "feasible": solution.feasible,
                "objective_values": solution.objective_values,
                "solution_metadata": solution.metadata,
                "nonzero_variable_sample": _nonzero_sample(solution.variable_values, variable_node_ids),
            }
        )
    except Exception as exc:
        payload["error"] = {"type": type(exc).__name__, "message": str(exc)}
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
