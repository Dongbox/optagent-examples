from __future__ import annotations

from dataclasses import dataclass, is_dataclass, replace
from types import SimpleNamespace
from typing import Any

from optagent import ModelBuilder

UTILIZATION_COEFF_SCALE = 1_000_000


@dataclass
class BuiltResourceFlowProgram:
    program: Any
    variable_node_ids: dict[str, int]
    metadata: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            **self.metadata,
            "variable_count": len(self.program.variable_ids),
            "constraint_count": len(self.program.constraint_ids),
            "objective_count": len(self.program.objective_ids),
        }


def _get_global_t(step: int, k: int, t: int) -> int:
    return step * k + t


def _sum_expr(builder: ModelBuilder, exprs: list[Any]) -> Any:
    if not exprs:
        return builder.const(0)
    if len(exprs) == 1:
        return exprs[0]
    return builder.sum(*exprs)


def _weight_scale(config: Any) -> int:
    weight_decimals = getattr(config, "weight_decimals", None)
    if weight_decimals is None:
        weight_decimals = 2 if getattr(config, "model_impl", "cp_sat") == "cp_sat" else 3
    return 10 ** int(weight_decimals)


def _get_active_A_m_due(
    config: Any,
    model_input: Any,
    modeling_period: int,
    k: int,
) -> list[tuple[str, str, int]]:
    active_pairs: list[tuple[str, str, int]] = []
    for d, m in model_input.A_m_due:
        local_t_d_m_due = model_input.t_d_m_due[(d, m)] - config.step * k
        if 1 <= local_t_d_m_due <= modeling_period:
            active_pairs.append((d, m, local_t_d_m_due))
    return active_pairs


def _get_active_A_ready(
    config: Any,
    model_input: Any,
    modeling_period: int,
    k: int,
) -> list[tuple[str, str, int, int]]:
    active_items: list[tuple[str, str, int, int]] = []
    for d, m, global_t in model_input.A_ready:
        local_t = global_t - config.step * k
        if not 1 <= local_t <= modeling_period:
            continue
        weight = config.contract_ready_weights.get(model_input.t_d_m_due[(d, m)] - global_t, 0)
        if weight <= 0:
            continue
        active_items.append((d, m, local_t, int(weight)))
    return active_items


def _get_contract_machine_capacity(
    config: Any,
    model_input: Any,
    d: str,
    m: str,
    global_t: int,
) -> int:
    if m == "m_source":
        return max(config.m_source_capacity.values())
    camp_label = model_input.camp_d_m[(d, m)]
    return int(config.capacity[(m, camp_label, global_t)])


def _get_machine_max_capacity(config: Any, m: str, global_t: int) -> int:
    return max(
        (cap for (_m, _, _t), cap in config.capacity.items() if _m == m and _t == global_t),
        default=0,
    )


def _get_inventory_upper_bound(config: Any, model_input: Any) -> int:
    candidates: list[int] = [0]
    candidates.extend(int(value) for value in config.m_source_capacity.values())
    candidates.extend(int(value) for value in config.capacity.values())
    candidates.extend(int(high) for _, (_, high) in config.I_range.items() if high != -1)
    candidates.extend(int(max(low, high)) for low, high in config.I_expect.values() if low != -1 or high != -1)
    candidates.extend(int(value) for value in model_input.I_m_0.values())
    candidates.extend(int(value) for value in model_input.I_d_m_0.values())
    candidates.extend(int(value) for value in model_input.I_d_m_0_excess.values())
    candidates.extend(int(value) for value in model_input.Q_d.values())
    candidates.extend(int(value) for value in model_input.owe_d_m.values())
    candidates.extend(int(value) for value in model_input.x_t0.values())
    return max(candidates)


def _get_cp_sat_utilization_coeff(
    config: Any,
    model_input: Any,
    d: str,
    m: str,
    global_t: int,
) -> int:
    a_d_m_t = model_input.a_d_m_t[(d, m, global_t)]
    weight_scale = _weight_scale(config)
    coeff = 100 * UTILIZATION_COEFF_SCALE * a_d_m_t / 1000 / weight_scale
    return round(coeff)


def build_single_window_program(
    config: Any,
    model_input: Any,
    *,
    modeling_period: int,
    k: int = 0,
    p: int = 1,
) -> BuiltResourceFlowProgram:
    builder = ModelBuilder(
        metadata={
            "problem_family": "resource_flow",
            "formulation": "cp",
            "window_index": k,
            "modeling_period": modeling_period,
            "contracts": len(model_input.D),
            "machines": len(config.m_real),
        },
        solve_config={"preferred_backend": "cp_sat_native"},
    )
    vars_by_name: dict[str, Any] = {}

    def int_var(name: str, lb: int, ub: int) -> Any:
        default = lb if lb == ub else min(max(0, lb), ub)
        expr = builder.int_var(default=default, lb=lb, ub=ub, name=name)
        vars_by_name[name] = expr
        return expr

    def bool_var(name: str) -> Any:
        expr = builder.bool_var(default=False, name=name)
        vars_by_name[name] = expr
        return expr

    M_ids = model_input.M_ids
    D_ids = model_input.D_ids
    inventory_ub = _get_inventory_upper_bound(config, model_input)

    for (m, n) in config.m_logistics:
        if (m, n) not in model_input.D_m_n:
            continue
        for d in model_input.D_m_n[(m, n)]:
            for t in range(1, modeling_period + 1):
                global_t = _get_global_t(config.step, k, t)
                ub = min(model_input.Q_d[d], _get_contract_machine_capacity(config, model_input, d, m, global_t))
                min_batch = min(20 * _weight_scale(config), model_input.Q_d[d])
                x = int_var(f"x_d{D_ids[d]}_m{M_ids[m]}_n{M_ids[n]}_t{t}", 0, ub)
                if 0 < min_batch <= ub:
                    builder.constraint(
                        builder.or_(x == 0, x >= min_batch),
                        name=f"{x.builder.graph.nodes[x.node_id].metadata['name']}_domain",
                    )

    for m in config.m_real:
        for t in range(modeling_period + 1):
            int_var(f"I_m{M_ids[m]}_t{t}", 0, inventory_ub)
            int_var(f"delta_I_range_m{M_ids[m]}_t{t}", 0, inventory_ub)
            int_var(f"delta_I_expect_m{M_ids[m]}_t{t}", 0, inventory_ub)
            if t > 0:
                global_t = _get_global_t(config.step, k, t)
                max_capacity = _get_machine_max_capacity(config, m, global_t)
                int_var(f"O_m{M_ids[m]}_t{t}", 0, max_capacity)
                int_var(f"u_m{M_ids[m]}_t{t}", 0, 100)
                bool_var(f"z_m{M_ids[m]}_t{t}")
            for d in model_input.D_m[m]:
                int_var(f"I_d{D_ids[d]}_m{M_ids[m]}_t{t}", 0, inventory_ub)
                if t > 0:
                    int_var(
                        f"O_d{D_ids[d]}_m{M_ids[m]}_t{t}",
                        0,
                        _get_contract_machine_capacity(config, model_input, d, m, global_t),
                    )
                    int_var(f"C_d{D_ids[d]}_m{M_ids[m]}_t{t}", 0, inventory_ub)

    for d in model_input.D:
        for t in range(modeling_period + 1):
            int_var(f"R_d{D_ids[d]}_t{t}", 0, model_input.Q_d[d])

    for d, m, _ in _get_active_A_m_due(config, model_input, modeling_period, k):
        int_var(f"R_m_due_d{D_ids[d]}_m{M_ids[m]}", 0, model_input.owe_d_m[(d, m)])

    for d, m, t, _ in _get_active_A_ready(config, model_input, modeling_period, k):
        int_var(f"I_d_eff_d{D_ids[d]}_m{M_ids[m]}_t{t}", 0, inventory_ub)

    for cost_name in (
        "cost_inventory",
        "cost_utilization",
        "cost_contract",
        "cost_contract_base",
        "cost_contract_m_due",
        "cost_contract_ready",
        "cost_I_range",
        "cost_I_expect",
    ):
        int_var(cost_name, 0, 10**12)

    for m in config.m_real:
        m_id = M_ids[m]
        for t in range(modeling_period + 1):
            i_m_t = vars_by_name[f"I_m{m_id}_t{t}"]
            i_range = vars_by_name[f"delta_I_range_m{m_id}_t{t}"]
            i_expect = vars_by_name[f"delta_I_expect_m{m_id}_t{t}"]

            if t == 0:
                builder.constraint(i_m_t == max(model_input.I_m_0.get(m, 0), 0), name=f"init_I_m_{m}_{t}")
                for d in model_input.D_m[m]:
                    builder.constraint(
                        vars_by_name[f"I_d{D_ids[d]}_m{m_id}_t{t}"] == max(model_input.I_d_m_0.get((d, m), 0), 0),
                        name=f"init_I_d_{d}_{m}_{t}",
                    )
            else:
                consumption_by_contract: dict[str, Any] = {}
                for d in model_input.D_m[m]:
                    o_expr = vars_by_name[f"O_d{D_ids[d]}_m{m_id}_t{t}"]
                    c_expr = vars_by_name[f"C_d{D_ids[d]}_m{m_id}_t{t}"]
                    builder.constraint(c_expr == ((o_expr * 1000) // config.m_yield[m]), name=f"cons_{d}_{m}_{t}")
                    consumption_by_contract[d] = c_expr

                inflow_by_contract: dict[str, Any] = {}
                if t == 1:
                    for d in model_input.D_m[m]:
                        inflow_by_contract[d] = builder.const(
                            sum(
                                model_input.x_t0.get((d, i, mm), 0)
                                for (i, mm) in model_input.E_d[d]
                                if mm == m
                            )
                        )
                else:
                    for d in model_input.D_m[m]:
                        inflow_by_contract[d] = _sum_expr(
                            builder,
                            [
                                vars_by_name[f"x_d{D_ids[d]}_m{M_ids[i]}_n{M_ids[mm]}_t{t-1}"]
                                for (i, mm) in model_input.E_d[d]
                                if mm == m
                            ],
                        )

                total_consumption = _sum_expr(builder, list(consumption_by_contract.values()))
                total_inflow = _sum_expr(builder, list(inflow_by_contract.values()))
                prev_i_m_t = vars_by_name[f"I_m{m_id}_t{t - 1}"]
                if t == 1:
                    builder.constraint(i_m_t == prev_i_m_t + total_inflow - total_consumption, name=f"I_m_bal_{m}_{t}")
                else:
                    builder.constraint(i_m_t == prev_i_m_t + total_inflow - total_consumption, name=f"I_m_bal_{m}_{t}")

                for d in model_input.D_m[m]:
                    builder.constraint(
                        vars_by_name[f"I_d{D_ids[d]}_m{m_id}_t{t}"]
                        == vars_by_name[f"I_d{D_ids[d]}_m{m_id}_t{t - 1}"] + inflow_by_contract[d] - consumption_by_contract[d],
                        name=f"I_d_bal_{d}_{m}_{t}",
                    )

            global_t = _get_global_t(config.step, k, t)
            range_lb, range_ub = config.I_range[(m, global_t)]
            expect_lb, expect_ub = config.I_expect[m]
            builder.constraint(i_range == builder.max(0, i_m_t - range_ub, range_lb - i_m_t), name=f"range_dev_{m}_{t}")
            builder.constraint(i_expect == builder.max(0, i_m_t - expect_ub, expect_lb - i_m_t), name=f"expect_dev_{m}_{t}")

    for m in config.m_real:
        m_id = M_ids[m]
        for t in range(1, modeling_period + 1):
            global_t = _get_global_t(config.step, k, t)
            out_by_contract = {
                d: _sum_expr(
                    builder,
                    [
                        vars_by_name[f"x_d{D_ids[d]}_m{M_ids[mm]}_n{M_ids[j]}_t{t}"]
                        for (mm, j) in model_input.E_d[d]
                        if mm == m
                    ],
                )
                for d in model_input.D_m[m]
            }
            total_output = _sum_expr(builder, list(out_by_contract.values()))
            builder.constraint(vars_by_name[f"O_m{m_id}_t{t}"] == total_output, name=f"O_m_def_{m}_{t}")
            for d, out_expr in out_by_contract.items():
                builder.constraint(vars_by_name[f"O_d{D_ids[d]}_m{m_id}_t{t}"] == out_expr, name=f"O_d_def_{d}_{m}_{t}")

            max_capacity = _get_machine_max_capacity(config, m, global_t)
            if max_capacity == 0:
                builder.constraint(vars_by_name[f"O_m{m_id}_t{t}"] == 0, name=f"stop_output_{m}_{t}")
                builder.constraint(vars_by_name[f"u_m{m_id}_t{t}"] == 100, name=f"stop_util_{m}_{t}")
            else:
                util_sum = _sum_expr(
                    builder,
                    [
                        vars_by_name[f"O_d{D_ids[d]}_m{m_id}_t{t}"]
                        * _get_cp_sat_utilization_coeff(config, model_input, d, m, global_t)
                        for d in model_input.D_m[m]
                    ],
                )
                builder.constraint(vars_by_name[f"u_m{m_id}_t{t}"] == (util_sum // UTILIZATION_COEFF_SCALE), name=f"util_{m}_{t}")
            builder.constraint(
                vars_by_name[f"z_m{m_id}_t{t}"] == (vars_by_name[f"u_m{m_id}_t{t}"] <= config.capacity_utilization_standard - 1),
                name=f"util_flag_{m}_{t}",
            )

    for d in model_input.D:
        d_id = D_ids[d]
        builder.constraint(vars_by_name[f"R_d{d_id}_t0"] == model_input.Q_d[d], name=f"R_init_{d}")
        for t in range(1, modeling_period + 1):
            production_d = _sum_expr(
                builder,
                [
                    vars_by_name[f"O_d{d_id}_m{M_ids[m]}_t{t}"]
                    for (m, n) in model_input.E_d[d]
                    if n == "m_sink"
                ],
            )
            builder.constraint(
                vars_by_name[f"R_d{d_id}_t{t}"] == builder.max(0, vars_by_name[f"R_d{d_id}_t{t - 1}"] - production_d),
                name=f"R_roll_{d}_{t}",
            )

        source_total = _sum_expr(
            builder,
            [
                vars_by_name[f"x_d{d_id}_m{M_ids[m]}_n{M_ids[n]}_t{t}"]
                for (m, n) in model_input.E_d[d]
                if m == "m_source"
                for t in range(1, modeling_period + 1)
            ],
        )
        builder.constraint(source_total <= model_input.owe_d_m[(d, "m_source")], name=f"source_total_{d}")

        for (m, _) in model_input.E_d[d]:
            if m == "m_source":
                continue
            m_id = M_ids[m]
            machine_total = _sum_expr(
                builder,
                [vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"] for t in range(1, modeling_period + 1)],
            )
            rhs = round(model_input.owe_d_m[(d, m)] * (1 + model_input.overprod_d_m[(d, m)] / 100))
            builder.constraint(machine_total <= rhs, name=f"machine_total_{d}_{m}")

    for t in range(1, modeling_period + 1):
        source_day = _sum_expr(
            builder,
            [
                vars_by_name[f"x_d{D_ids[d]}_m{M_ids[m]}_n{M_ids[n]}_t{t}"]
                for d in model_input.D
                for (m, n) in model_input.E_d[d]
                if m == "m_source"
            ],
        )
        builder.constraint(
            source_day <= config.m_source_capacity[_get_global_t(config.step, k, t)],
            name=f"source_day_{t}",
        )

    key_range_terms = [
        vars_by_name[f"delta_I_range_m{M_ids[m]}_t{t}"]
        for m in config.m_real_key
        for t in range(modeling_period + 1)
    ]
    common_range_terms = [
        vars_by_name[f"delta_I_range_m{M_ids[m]}_t{t}"]
        for m in set(config.m_real) - set(config.m_real_key)
        for t in range(modeling_period + 1)
    ]
    key_expect_terms = [
        vars_by_name[f"delta_I_expect_m{M_ids[m]}_t{t}"]
        for m in config.m_real_key
        for t in range(modeling_period + 1)
    ]
    common_expect_terms = [
        vars_by_name[f"delta_I_expect_m{M_ids[m]}_t{t}"]
        for m in set(config.m_real) - set(config.m_real_key)
        for t in range(modeling_period + 1)
    ]

    n1 = max(len(config.m_real_key) * (modeling_period + 1), 1)
    n2 = max((len(config.m_real) - len(config.m_real_key)) * (modeling_period + 1), 1)
    range_exprs = []
    expect_exprs = []
    if key_range_terms:
        range_exprs.append((_sum_expr(builder, key_range_terms) // n1) * config.cost_coeff_inv_range_key)
    if common_range_terms:
        range_exprs.append((_sum_expr(builder, common_range_terms) // n2) * config.cost_coeff_inv_range_common)
    if key_expect_terms:
        expect_exprs.append((_sum_expr(builder, key_expect_terms) // n1) * config.cost_coeff_inv_expect_key)
    if common_expect_terms:
        expect_exprs.append((_sum_expr(builder, common_expect_terms) // n2) * config.cost_coeff_inv_expect_common)

    builder.constraint(vars_by_name["cost_I_range"] == _sum_expr(builder, range_exprs), name="cost_I_range_def")
    builder.constraint(vars_by_name["cost_I_expect"] == _sum_expr(builder, expect_exprs), name="cost_I_expect_def")
    builder.constraint(
        vars_by_name["cost_inventory"]
        == vars_by_name["cost_I_range"] * config.cost_coeff_inv_range
        + vars_by_name["cost_I_expect"] * config.cost_coeff_inv_expect,
        name="cost_inventory_def",
    )

    low_util_indicator = _sum_expr(
        builder,
        [vars_by_name[f"z_m{M_ids[m]}_t{t}"] for m in config.m_real for t in range(1, modeling_period + 1)],
    )
    low_util_gap = _sum_expr(
        builder,
        [
            100 - vars_by_name[f"u_m{M_ids[m]}_t{t}"]
            for m in config.m_real
            for t in range(1, modeling_period + 1)
        ],
    )
    builder.constraint(
        vars_by_name["cost_utilization"]
        == ((low_util_indicator * config.cost_coeff_mu1 + low_util_gap * config.cost_coeff_mu2) // modeling_period),
        name="cost_utilization_def",
    )

    base_terms = []
    for d in model_input.D:
        if model_input.Q_d[d] == 0:
            continue
        d_id = D_ids[d]
        for t in range(1, modeling_period + 1):
            base_terms.append(vars_by_name[f"R_d{d_id}_t{t}"] * (model_input.e_d[d] * model_input.P_t[(d, t)]))
    contract_norm = max(round(len(model_input.D) / 10), 1)
    builder.constraint(
        vars_by_name["cost_contract_base"] == (_sum_expr(builder, base_terms) // (100 * contract_norm)),
        name="cost_contract_base_def",
    )

    active_due = _get_active_A_m_due(config, model_input, modeling_period, k)
    due_terms = []
    for d, m, local_due in active_due:
        d_id = D_ids[d]
        m_id = M_ids[m]
        produced_until_due = _sum_expr(
            builder,
            [vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"] for t in range(1, local_due + 1)],
        )
        shortfall = vars_by_name[f"R_m_due_d{d_id}_m{m_id}"]
        builder.constraint(
            shortfall == builder.max(0, model_input.owe_d_m[(d, m)] - produced_until_due),
            name=f"cost_contract_due_shortfall_{d}_{m}",
        )
        due_terms.append(shortfall)
    builder.constraint(
        vars_by_name["cost_contract_m_due"]
        == (_sum_expr(builder, due_terms) // max(len(due_terms), 1)),
        name="cost_contract_m_due_def",
    )

    active_ready = _get_active_A_ready(config, model_input, modeling_period, k)
    ready_norm = sum(weight for _, _, _, weight in active_ready)
    ready_terms = []
    for d, m, t, weight in active_ready:
        d_id = D_ids[d]
        m_id = M_ids[m]
        eff_inv = vars_by_name[f"I_d_eff_d{d_id}_m{m_id}_t{t}"]
        builder.constraint(
            eff_inv == builder.max(0, vars_by_name[f"I_d{d_id}_m{m_id}_t{t}"] - model_input.I_d_m_0_excess.get((d, m), 0)),
            name=f"ready_eff_{d}_{m}_{t}",
        )
        ready_terms.append(eff_inv * weight)
    builder.constraint(
        vars_by_name["cost_contract_ready"] == (_sum_expr(builder, ready_terms) // max(ready_norm, 1)),
        name="cost_contract_ready_def",
    )

    builder.constraint(
        vars_by_name["cost_contract"]
        == vars_by_name["cost_contract_base"]
        + vars_by_name["cost_contract_m_due"] * int(config.cost_coeff_contract_m_due)
        + vars_by_name["cost_contract_ready"] * int(config.cost_coeff_contract_ready),
        name="cost_contract_def",
    )

    builder.minimize(
        vars_by_name["cost_inventory"] * config.cost_coeff_inventory
        + vars_by_name["cost_utilization"] * config.cost_coeff_utility
        + vars_by_name["cost_contract"] * config.cost_coeff_contract,
        name="resource_flow_objective",
    )

    program = builder.freeze()
    return BuiltResourceFlowProgram(
        program=program,
        variable_node_ids={name: expr.node_id for name, expr in vars_by_name.items()},
        metadata={
            "problem_family": "resource_flow",
            "formulation": "cp",
            "window_index": k,
            "modeling_period": modeling_period,
        },
    )


def roll_variable_name(var_name: str, step: int) -> str | None:
    marker = "_t"
    if marker not in var_name:
        return var_name
    prefix, suffix = var_name.rsplit(marker, 1)
    if not suffix.isdigit():
        return var_name
    prev_t = int(suffix)
    if prev_t < step:
        return None
    return f"{prefix}_t{prev_t - step}"


def roll_named_warm_start(previous_solution: dict[str, int | bool], step: int) -> dict[str, int | bool]:
    rolled: dict[str, int | bool] = {}
    for var_name, value in previous_solution.items():
        rolled_name = roll_variable_name(var_name, step)
        if rolled_name is not None:
            rolled[rolled_name] = value
    return rolled


def advance_window_input(config: Any, prev_input: Any, prev_solution: dict[str, int | bool]) -> Any:
    step = config.step

    def _weight(value: int | bool) -> int:
        return int(value)

    D = prev_input.D
    Q_d = {d: _weight(prev_solution[f"R_d{prev_input.D_ids[d]}_t{step}"]) for d in D}
    I_m_0 = {
        m: _weight(prev_solution[f"I_m{prev_input.M_ids[m]}_t{step}"])
        for m in config.m_real
    }
    I_d_m_0 = {
        (d, m): _weight(prev_solution[f"I_d{prev_input.D_ids[d]}_m{prev_input.M_ids[m]}_t{step}"])
        for (d, m) in prev_input.I_d_m_0
    }
    x_t0: dict[tuple[str, str, str], int] = {}
    for (m, n), ds in prev_input.D_m_n.items():
        for d in ds:
            value = _weight(prev_solution[f"x_d{prev_input.D_ids[d]}_m{prev_input.M_ids[m]}_n{prev_input.M_ids[n]}_t{step}"])
            if value > 0:
                x_t0[(d, m, n)] = value

    P_t = {}
    max_prev_t = max(key[1] for key in prev_input.P_t.keys())
    for d in D:
        for t in range(1, max_prev_t + 1 - step):
            P_t[(d, t)] = prev_input.P_t[(d, t + step)]

    owe_d_m: dict[tuple[str, str], int] = {}
    for d in D:
        d_id = prev_input.D_ids[d]
        for m in {edge[0] for edge in prev_input.E_d[d]}:
            m_id = prev_input.M_ids[m]
            provided_qty = 0
            for n in {edge[1] for edge in prev_input.E_d[d] if edge[0] == m}:
                n_id = prev_input.M_ids[n]
                for t in range(1, step + 1):
                    provided_qty += _weight(prev_solution[f"x_d{d_id}_m{m_id}_n{n_id}_t{t}"])
            owe_d_m[(d, m)] = max(prev_input.owe_d_m[(d, m)] - provided_qty, 0)

    I_d_m_0_excess = {}
    for (d, m), overprod_percent in prev_input.overprod_d_m.items():
        if m == "m_source":
            continue
        allowed_consumption_qty = owe_d_m.get((d, m), 0) * (1 + overprod_percent / 100) * 1000 / config.m_yield[m]
        I_d_m_0_excess[(d, m)] = max(I_d_m_0.get((d, m), 0) - allowed_consumption_qty, 0)

    t_d_m_due = {
        (d, m): due
        for (d, m), due in prev_input.t_d_m_due.items()
    }
    A_m_due = sorted(
        [
            (d, m)
            for (d, m), m_due in t_d_m_due.items()
            if owe_d_m.get((d, m), 0) > 0 and 1 <= m_due <= config.planning_period
        ],
        key=lambda item: (t_d_m_due[item], item[0], item[1]),
    )

    A_ready = []
    for d, m in A_m_due:
        m_due = t_d_m_due[(d, m)]
        start_t = max(1, m_due - config.contract_ready_window)
        for t in range(start_t, m_due + 1):
            if t > config.planning_period:
                continue
            if config.contract_ready_weights.get(m_due - t, 0) <= 0:
                continue
            A_ready.append((d, m, t))
    A_ready.sort(key=lambda item: (item[2], t_d_m_due[(item[0], item[1])], item[0], item[1]))

    updates = {
        "I_d_m_0": I_d_m_0,
        "I_d_m_0_excess": I_d_m_0_excess,
        "I_m_0": I_m_0,
        "Q_d": Q_d,
        "x_t0": x_t0,
        "owe_d_m": owe_d_m,
        "t_d_m_due": t_d_m_due,
        "A_m_due": A_m_due,
        "A_ready": A_ready,
        "P_t": P_t,
    }
    if is_dataclass(prev_input):
        return replace(prev_input, **updates)
    next_input = SimpleNamespace(**vars(prev_input))
    for key, value in updates.items():
        setattr(next_input, key, value)
    return next_input
