from __future__ import annotations

from pathlib import Path

import pytest

from optagent import GaConfig, MilpConfig, SolutionStatus, SolveOptions, solve, solve_milp
from optagent.exact import exact_backend_registry


OPTX_AVAILABLE = exact_backend_registry()["optx"].backend.is_available()


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


@pytest.mark.skipif(not OPTX_AVAILABLE, reason="requires native OptX backend with embedded HiGHS support")
def test_tiny_mps_model_solves_through_internal_exact_backend(tmp_path: Path) -> None:
    from examples.mps.mps_builder import build_program_from_mps

    mps_path = tmp_path / "tiny.mps"
    mps_path.write_text(MPS_FIXTURE, encoding="utf-8")

    built = build_program_from_mps(mps_path)
    solution = solve_milp(built.program, config=MilpConfig(backend="optx", time_limit_s=10.0))

    assert solution.status in {SolutionStatus.OPTIMAL, SolutionStatus.FEASIBLE}
    assert solution.feasible is True
    assert solution.objective_values


def test_tiny_mps_model_solves_through_declared_strategy(tmp_path: Path) -> None:
    from examples.mps.mps_builder import build_program_from_mps

    mps_path = tmp_path / "tiny.mps"
    mps_path.write_text(MPS_FIXTURE, encoding="utf-8")

    built = build_program_from_mps(mps_path)
    solution = solve(
        built.program,
        options=SolveOptions(
            strategy=GaConfig(
                max_iterations=20,
                population_size=4,
                mutation_portfolio=("random_reset", "random_swap"),
            ),
            max_iterations=20,
            time_limit_s=5.0,
            log_level="off",
            trace_output="summary",
        ),
    )

    assert solution.objective_values
    assert solution.metadata["strategy"] == "ga"
