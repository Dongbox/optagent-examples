from __future__ import annotations

import json
from typing import Any

from optagent import UnifiedSolution


def solution_metadata(solution: UnifiedSolution) -> dict[str, Any]:
    metadata = dict(solution.diagnostics)
    metadata.update(
        {
            "algorithm": solution.result.algorithm,
            "iterations": solution.result.iterations,
            "wall_time_seconds": solution.result.wall_time_seconds,
            "termination_reason": solution.result.termination_reason,
            "termination_policy": solution.result.termination_policy,
            "restarts": solution.result.restarts,
        }
    )
    return metadata


def print_solution(title: str, solution: UnifiedSolution, *, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "title": title,
        "solver_name": solution.solver_name,
        "status": solution.status.value,
        "feasible": solution.feasible,
        "objective_values": solution.objective_values,
        "metadata": solution_metadata(solution),
        "variables": solution.variable_values,
    }
    if extra:
        payload["extra"] = extra
    print(json.dumps(payload, indent=2, ensure_ascii=True))
