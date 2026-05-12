from __future__ import annotations

import json
from typing import Any

from optagent import UnifiedSolution


def print_solution(title: str, solution: UnifiedSolution, *, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "title": title,
        "solver_name": solution.solver_name,
        "status": solution.status.value,
        "feasible": solution.feasible,
        "objective_values": solution.objective_values,
        "metadata": solution.metadata,
        "variables": solution.variable_values,
    }
    if extra:
        payload["extra"] = extra
    print(json.dumps(payload, indent=2, ensure_ascii=True))
