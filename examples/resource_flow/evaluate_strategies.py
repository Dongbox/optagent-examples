from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOLVE_CASE = REPO_ROOT / "examples" / "resource_flow" / "solve_case.py"


@dataclass
class StrategyRun:
    name: str
    formulation: str
    mode: str
    backend: str
    exact_time_limit_seconds: float | None
    wall_timeout_seconds: float
    heuristic_total_budget: int | None = None
    seed_budget: int | None = None
    intensify_budget: int | None = None
    refine_budget: int | None = None
    heuristic_time_limit_seconds: float | None = None
    heuristic_max_candidate_moves: int | None = None
    heuristic_max_scalar_variables: int | None = None
    cp_workers: int | None = None
    mathopt_solver_type: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate resource_flow strategy combinations through solve_case.py.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals") / f"resource_flow_strategy_eval_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
    )
    return parser.parse_args()


def _matrix() -> list[StrategyRun]:
    return [
        StrategyRun("cp_exact_auto", "cp", "exact", "auto", 30.0, 90.0, cp_workers=8),
        StrategyRun(
            "cp_ga_auto",
            "cp",
            "ga",
            "auto",
            None,
            30.0,
            heuristic_total_budget=1,
            seed_budget=1,
            intensify_budget=0,
            heuristic_time_limit_seconds=1.0,
            heuristic_max_candidate_moves=1,
            heuristic_max_scalar_variables=1,
            cp_workers=8,
        ),
        StrategyRun(
            "cp_alns_auto",
            "cp",
            "alns",
            "auto",
            10.0,
            45.0,
            heuristic_total_budget=1,
            seed_budget=1,
            refine_budget=1,
            heuristic_time_limit_seconds=1.0,
            heuristic_max_candidate_moves=1,
            heuristic_max_scalar_variables=1,
            cp_workers=8,
        ),
        StrategyRun("milp_exact_optx", "milp", "exact", "optx", 5.0, 45.0),
        StrategyRun("milp_exact_mathopt", "milp", "exact", "mathopt_mp", 30.0, 60.0, mathopt_solver_type="GSCIP"),
        StrategyRun(
            "milp_ga_auto",
            "milp",
            "ga",
            "auto",
            None,
            30.0,
            heuristic_total_budget=1,
            seed_budget=1,
            intensify_budget=0,
            heuristic_time_limit_seconds=1.0,
            heuristic_max_candidate_moves=1,
            heuristic_max_scalar_variables=1,
        ),
        StrategyRun(
            "milp_alns_optx",
            "milp",
            "alns",
            "optx",
            5.0,
            45.0,
            heuristic_total_budget=1,
            seed_budget=1,
            refine_budget=1,
            heuristic_time_limit_seconds=1.0,
            heuristic_max_candidate_moves=1,
            heuristic_max_scalar_variables=1,
        ),
        StrategyRun(
            "milp_alns_mathopt",
            "milp",
            "alns",
            "mathopt_mp",
            5.0,
            45.0,
            heuristic_total_budget=1,
            seed_budget=1,
            refine_budget=1,
            heuristic_time_limit_seconds=1.0,
            heuristic_max_candidate_moves=1,
            heuristic_max_scalar_variables=1,
            mathopt_solver_type="GSCIP",
        ),
    ]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _command(run: StrategyRun) -> list[str]:
    cmd = [
        sys.executable,
        str(SOLVE_CASE),
        "--formulation",
        run.formulation,
        "--mode",
        run.mode,
        "--backend",
        run.backend,
    ]
    if run.exact_time_limit_seconds is not None:
        cmd.extend(["--exact-time-limit-seconds", str(run.exact_time_limit_seconds)])
    if run.heuristic_total_budget is not None:
        cmd.extend(["--heuristic-total-budget", str(run.heuristic_total_budget)])
    if run.seed_budget is not None:
        cmd.extend(["--seed-budget", str(run.seed_budget)])
    if run.intensify_budget is not None:
        cmd.extend(["--intensify-budget", str(run.intensify_budget)])
    if run.refine_budget is not None:
        cmd.extend(["--refine-budget", str(run.refine_budget)])
    if run.heuristic_time_limit_seconds is not None:
        cmd.extend(["--heuristic-time-limit-seconds", str(run.heuristic_time_limit_seconds)])
    if run.heuristic_max_candidate_moves is not None:
        cmd.extend(["--heuristic-max-candidate-moves", str(run.heuristic_max_candidate_moves)])
    if run.heuristic_max_scalar_variables is not None:
        cmd.extend(["--heuristic-max-scalar-variables", str(run.heuristic_max_scalar_variables)])
    if run.cp_workers is not None:
        cmd.extend(["--cp-workers", str(run.cp_workers)])
    if run.mathopt_solver_type is not None:
        cmd.extend(["--mathopt-solver-type", run.mathopt_solver_type])
    return cmd


def _summarize_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "feasible": payload.get("feasible"),
        "solver_name": payload.get("solver_name"),
        "objective_values": payload.get("objective_values"),
        "error": payload.get("error"),
    }


def _run_one(run: StrategyRun) -> dict[str, Any]:
    started_at = _utc_now()
    command = _command(run)
    wall_start = perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            capture_output=True,
            text=True,
            timeout=run.wall_timeout_seconds,
            check=False,
        )
        wall_seconds = perf_counter() - wall_start
    except subprocess.TimeoutExpired as exc:
        return {
            "run": asdict(run),
            "started_at": started_at,
            "finished_at": _utc_now(),
            "command": command,
            "returncode": None,
            "wall_seconds": round(perf_counter() - wall_start, 3),
            "completed": False,
            "timed_out": True,
            "stdout": exc.stdout[-4000:] if exc.stdout else "",
            "stderr": exc.stderr[-4000:] if exc.stderr else "",
            "payload": None,
            "summary": {"error": {"type": "TimeoutExpired", "message": f"wall timeout after {run.wall_timeout_seconds}s"}},
        }

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    payload = None
    parse_error = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            parse_error = {"type": "JSONDecodeError", "message": str(exc)}
    summary = _summarize_result(payload) if payload is not None else {"error": parse_error}
    ok = proc.returncode == 0 and payload is not None and payload.get("error") is None
    return {
        "run": asdict(run),
        "started_at": started_at,
        "finished_at": _utc_now(),
        "command": command,
        "returncode": proc.returncode,
        "wall_seconds": round(wall_seconds, 3),
        "completed": True,
        "timed_out": False,
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
        "payload": payload,
        "summary": summary,
        "ok": ok,
    }


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    runs = _matrix()
    results = [_run_one(run) for run in runs]
    ok_count = sum(1 for item in results if item.get("ok"))
    timeout_count = sum(1 for item in results if item.get("timed_out"))
    error_count = len(results) - ok_count - timeout_count

    report = {
        "generated_at": _utc_now(),
        "python_executable": sys.executable,
        "solve_case": str(SOLVE_CASE),
        "results": results,
        "aggregate": {
            "total": len(results),
            "ok": ok_count,
            "timeout": timeout_count,
            "error": error_count,
        },
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "aggregate": report["aggregate"]}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
