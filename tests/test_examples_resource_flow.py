from __future__ import annotations

import importlib.util
from types import SimpleNamespace

from optagent import CpSatSolver, MilpSolver, SolutionStatus

from examples.resource_flow.case_loader import load_case
from examples.resource_flow.cp_builder import advance_window_input, build_single_window_program, roll_named_warm_start
from examples.resource_flow.milp_builder import build_single_window_milp_program
from examples.resource_flow.rolling import run_rolling_cp_sat


HAS_MP_BACKEND = importlib.util.find_spec("ortools") is not None or importlib.util.find_spec("highspy") is not None


def _tiny_case() -> tuple[SimpleNamespace, SimpleNamespace]:
    config = SimpleNamespace(
        model_impl="cp_sat",
        weight_decimals=0,
        step=1,
        planning_period=1,
        window_period=1,
        m_real=["M1"],
        m_logistics=[("m_source", "M1"), ("M1", "m_sink")],
        m_real_key=["M1"],
        m_line={"M1": "L1"},
        m_yield={"M1": 1000},
        I_range={("M1", 0): (0, 100), ("M1", 1): (0, 100)},
        I_expect={"M1": (0, 100)},
        capacity={("M1", "default", 1): 100, ("M1", "default", 2): 100},
        m_source_capacity={1: 100, 2: 100},
        capacity_utilization_standard=90,
        cost_coeff_inventory=1,
        cost_coeff_utility=1,
        cost_coeff_contract=10,
        cost_coeff_contract_m_due=100,
        cost_coeff_contract_ready=100,
        contract_ready_window=1,
        contract_ready_weights={0: 100, 1: 10},
        cost_coeff_inv_range=10,
        cost_coeff_inv_expect=1,
        cost_coeff_inv_range_key=2,
        cost_coeff_inv_range_common=1,
        cost_coeff_inv_expect_key=2,
        cost_coeff_inv_expect_common=1,
        cost_coeff_mu1=100,
        cost_coeff_mu2=1,
    )
    model_input = SimpleNamespace(
        D=["D1"],
        M_all=["M1", "m_source", "m_sink"],
        M_ids={"M1": 0, "m_source": 1, "m_sink": 2},
        D_ids={"D1": 0},
        I_d_m_0={("D1", "M1"): 0},
        I_m_0={"M1": 0},
        Q_d={"D1": 40},
        x_t0={},
        camp_d_m={("D1", "M1"): "default"},
        a_d_m_t={("D1", "M1", 1): 10.0, ("D1", "M1", 2): 10.0},
        owe_d_m={("D1", "m_source"): 40, ("D1", "M1"): 40},
        overprod_d_m={("D1", "M1"): 0},
        D_m_n={("m_source", "M1"): ["D1"], ("M1", "m_sink"): ["D1"]},
        D_m={"M1": ["D1"]},
        E_d={"D1": [("m_source", "M1"), ("M1", "m_sink")]},
        e_d={"D1": 100},
        P_t={("D1", 1): 1, ("D1", 2): 2},
        t_d_due={"D1": 1},
        t_d_lb={"D1": 1},
        t_d_m_lb={("D1", "M1"): 1},
        t_d_m_due={("D1", "M1"): 1},
        A_m_due=[("D1", "M1")],
        A_ready=[("D1", "M1", 1)],
        I_d_m_0_excess={("D1", "M1"): 0},
    )
    return config, model_input


def _tiny_rolling_case() -> tuple[SimpleNamespace, SimpleNamespace]:
    config, model_input = _tiny_case()
    config.planning_period = 2
    config.window_period = 1
    config.I_range = {("M1", 0): (0, 100), ("M1", 1): (0, 100), ("M1", 2): (0, 100), ("M1", 3): (0, 100)}
    config.capacity = {("M1", "default", 1): 100, ("M1", "default", 2): 100, ("M1", "default", 3): 100, ("M1", "default", 4): 100}
    config.m_source_capacity = {1: 100, 2: 100, 3: 100, 4: 100}
    model_input.a_d_m_t = {("D1", "M1", 1): 10.0, ("D1", "M1", 2): 10.0, ("D1", "M1", 3): 10.0, ("D1", "M1", 4): 10.0}
    model_input.P_t = {("D1", 1): 1, ("D1", 2): 2, ("D1", 3): 3, ("D1", 4): 4}
    model_input.t_d_due = {"D1": 2}
    model_input.t_d_m_due = {("D1", "M1"): 2}
    model_input.A_ready = [("D1", "M1", 1), ("D1", "M1", 2)]
    return config, model_input


def test_resource_flow_single_window_program_solves() -> None:
    config, model_input = _tiny_case()
    built = build_single_window_program(config, model_input, modeling_period=1)

    assert len(built.variable_node_ids) > 0
    assert len(built.program.constraint_ids) > 0

    result = CpSatSolver().solve(built.program)

    assert result.solution.status in {SolutionStatus.OPTIMAL, SolutionStatus.FEASIBLE}
    assert result.solution.feasible is True
    named_values = {
        name: result.solution.variable_values[node_id]
        for name, node_id in built.variable_node_ids.items()
    }
    assert named_values["x_d0_m1_n0_t1"] == 20
    assert named_values["x_d0_m0_n2_t1"] == 0
    assert named_values["O_m0_t1"] == 0
    assert named_values["R_d0_t1"] == 40


def test_resource_flow_bundled_zj_case_loads_without_external_project() -> None:
    cp_case = load_case(case_name="zj", formulation="cp", planning_period=3)
    milp_case = load_case(case_name="zj", formulation="milp", planning_period=3)

    assert cp_case.source.startswith("bundled:")
    assert cp_case.processed_contract_count == len(cp_case.model_input.D)
    assert cp_case.filtered_contract_count >= 0
    assert cp_case.config.model_impl == "cp_sat"
    assert cp_case.config.planning_period == 3

    assert milp_case.source.startswith("bundled:")
    assert milp_case.processed_contract_count == len(milp_case.model_input.D)
    assert milp_case.filtered_contract_count >= 0
    assert milp_case.config.model_impl == "mathopt"
    assert milp_case.config.planning_period == 3


def test_resource_flow_single_window_milp_program_builds() -> None:
    config, model_input = _tiny_case()
    built = build_single_window_milp_program(config, model_input, modeling_period=1)

    assert len(built.variable_node_ids) > 0
    assert len(built.program.constraint_ids) > 0
    assert built.summary()["formulation"] == "milp"


def test_resource_flow_bundled_milp_case_builds_summary() -> None:
    case = load_case(case_name="zj", formulation="milp", planning_period=3)
    built = build_single_window_milp_program(case.config, case.model_input, modeling_period=3)

    assert built.summary()["variable_count"] > 0
    assert built.summary()["constraint_count"] > 0


def test_resource_flow_single_window_milp_program_solves_when_backend_available() -> None:
    if not HAS_MP_BACKEND:
        return
    config, model_input = _tiny_case()
    built = build_single_window_milp_program(config, model_input, modeling_period=1)

    result = MilpSolver().solve(built.program)

    assert result.solution.status in {SolutionStatus.OPTIMAL, SolutionStatus.FEASIBLE}
    assert result.solution.feasible is True


def test_resource_flow_rolling_helpers_shift_state_and_warm_start() -> None:
    config, model_input = _tiny_case()
    previous_solution = {
        "R_d0_t1": 0,
        "I_m0_t1": 0,
        "I_d0_m0_t1": 0,
        "x_d0_m1_n0_t1": 40,
        "x_d0_m0_n2_t1": 40,
        "cost_inventory": 0,
    }

    rolled_hint = roll_named_warm_start(previous_solution, step=1)
    assert rolled_hint["cost_inventory"] == 0
    assert "R_d0_t0" in rolled_hint
    assert "x_d0_m1_n0_t0" in rolled_hint

    next_input = advance_window_input(config, model_input, previous_solution)
    assert next_input.Q_d["D1"] == 0
    assert next_input.I_m_0["M1"] == 0
    assert next_input.x_t0[("D1", "m_source", "M1")] == 40


def test_resource_flow_rolling_runner_carries_inventory_between_windows() -> None:
    config, model_input = _tiny_rolling_case()

    result = run_rolling_cp_sat(config, model_input)

    assert len(result.steps) == 3
    assert result.steps[0].named_values["x_d0_m1_n0_t1"] == 20
    assert result.steps[0].named_values["x_d0_m0_n2_t1"] == 0
    assert result.steps[1].named_values["x_d0_m0_n2_t1"] == 20
