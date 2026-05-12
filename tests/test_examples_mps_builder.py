from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from optagent import Orchestrator, SolutionStatus, load_strategy_preset


HAS_MP_BACKEND = importlib.util.find_spec("ortools") is not None or importlib.util.find_spec("highspy") is not None


MPS_FIXTURE = """\
NAME          tiny_resource_flow
ROWS
 N  OBJ
 L  cap
 G  demand
 E  link
COLUMNS
    x1        OBJ                 3  cap                 1
    x1        demand              1  link                1
    x2        OBJ                 2  cap                 1
    x2        demand              1  link               -1
    y1        OBJ                 5  link                1
RHS
    RHS1      cap                 4  demand              2
    RHS1      link                0
BOUNDS
 UP BND1      x1                  4
 UP BND1      x2                  4
 BV BND1      y1
ENDATA
"""


def test_parse_and_build_tiny_mps_model(tmp_path: Path) -> None:
    from examples.mps.mps_builder import build_program_from_mps, parse_mps

    mps_path = tmp_path / "tiny.mps"
    mps_path.write_text(MPS_FIXTURE, encoding="utf-8")

    parsed = parse_mps(mps_path)
    built = build_program_from_mps(mps_path)

    assert parsed.name == "tiny_resource_flow"
    assert parsed.objective_row == "OBJ"
    assert parsed.row_senses["cap"] == "L"
    assert parsed.variables["y1"].is_binary is True
    assert built.summary()["constraint_count"] == 3
    assert built.summary()["binary_variable_count"] == 1
    assert built.program.metadata["source_format"] == "mps"
    float_node_id = built.variable_node_ids["x1"]
    assert built.program.graph.nodes[float_node_id].metadata["family"] == "x"


@pytest.mark.skipif(not HAS_MP_BACKEND, reason="requires optional dependency 'ortools' or 'highspy'")
def test_tiny_mps_model_solves_through_external_preset(tmp_path: Path) -> None:
    from examples.mps.mps_builder import build_program_from_mps

    mps_path = tmp_path / "tiny.mps"
    mps_path.write_text(MPS_FIXTURE, encoding="utf-8")

    preset_path = tmp_path / "tiny_exact.json"
    preset_path.write_text(
        json.dumps(
            {
                "name": "tiny_exact",
                "description": "Exact preset for tiny imported MPS models.",
                "family": "exact",
                "objective": "quality",
                "tags": ["mps", "linear", "exact"],
                "requirements": ["highspy_or_ortools_mp"],
                "match": {
                    "problem_type": "general",
                    "has_linear": True,
                    "has_blackbox": False,
                    "has_scheduling": False,
                },
                "orchestrator_config": {
                    "total_budget_iterations": 40,
                    "phases": [
                        {
                            "name": "tiny_exact",
                            "solver": "milp",
                            "budget_iterations": 40,
                            "fallback_on_failure": False,
                            "fallback_on_stall": False,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    built = build_program_from_mps(mps_path)
    preset = load_strategy_preset(preset_path, program=built.program)
    result = Orchestrator().run(built.program, preset=preset)
    solution = result.final_solution

    assert solution.status in {SolutionStatus.OPTIMAL, SolutionStatus.FEASIBLE}
    assert solution.feasible is True
    assert solution.objective_values


def test_tiny_mps_model_solves_through_heuristic_preset(tmp_path: Path) -> None:
    from examples.mps.mps_builder import build_program_from_mps

    mps_path = tmp_path / "tiny.mps"
    mps_path.write_text(MPS_FIXTURE, encoding="utf-8")

    preset_path = tmp_path / "tiny_heuristic.json"
    preset_path.write_text(
        json.dumps(
            {
                "name": "tiny_heuristic",
                "description": "Heuristic preset for tiny imported MPS models.",
                "family": "heuristic",
                "objective": "balanced",
                "tags": ["mps", "linear", "heuristic"],
                "match": {
                    "problem_type": "general",
                    "has_linear": True,
                    "has_blackbox": False,
                    "has_scheduling": False
                },
                "orchestrator_config": {
                    "total_budget_iterations": 40,
                    "phases": [
                        {
                            "name": "seed",
                            "solver": "heuristic",
                            "budget_iterations": 15,
                            "strategy": "annealing",
                            "restart_limit": 1
                        },
                        {
                            "name": "intensify",
                            "solver": "heuristic",
                            "budget_iterations": 25,
                            "strategy": "tabu",
                            "restart_limit": 1
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    built = build_program_from_mps(mps_path)
    preset = load_strategy_preset(preset_path, program=built.program)
    result = Orchestrator().run(built.program, preset=preset)

    assert result.final_solution.objective_values
    assert result.solver_traces
