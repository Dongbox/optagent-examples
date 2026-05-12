"""MILP resource-flow model builder aligned with the original MathOpt model.

This file keeps the original business modeling logic from:
`aps-pre-decision/.../model_builder/mathopt.py`
while expressing the model through OptAgent `ModelBuilder`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from optagent import ModelBuilder


# 通用整数变量的取值上界
MAX_INT = int(1e10)
# 物料流量、库存等重量相关变量的取值上界
MAX_WEIGHT_INT = int(50000)
# 对 max(expr_1, expr_2, ...) 做精确线性化时使用的 Big-M
MAX_SELECTOR_BIG_M = int(1e6)
UTILIZATION_SCALE = 100
YIELD_SCALE = 1000
PREPROCESS_UTILIZATION_SCALE = 1000
MIN_BATCH_QTY = 20
EPSILON = 1e-6


@dataclass
class BuiltResourceFlowMilpProgram:
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
    """
    将滚动规划子周期中的 t 映射为全局周期索引，用于 config 查表。
    """
    return step * k + t


def _get_active_A_m_due(
    config: Any,
    model_input: Any,
    modeling_period: int,
    k: int,
) -> list[tuple[str, str, int]]:
    """
    获取当前求解轮次内需要纳入机组交期完成度惩罚的合同-机组组合。

    返回值中的第三个元素为映射到当前建模周期内的机组交期天数。
    """
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
    """
    获取当前求解轮次内需要纳入临期可生产库存滞留惩罚的合同-机组-时间组合。

    返回值第四个元素为对应的分段惩罚权重。
    """
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


def _sum_expr(builder: ModelBuilder, exprs: list[Any]) -> Any:
    """
    将表达式列表累加为一个 OptAgent 表达式，空列表时返回 0。
    """
    if not exprs:
        return builder.const(0.0)
    if len(exprs) == 1:
        return exprs[0]
    return builder.sum(*exprs)


def _get_contract_machine_capacity(
    config: Any,
    model_input: Any,
    d: str,
    m: str,
    global_t: int,
) -> float:
    """
    获取合同 d 在机组 m、第 global_t 天对应集批标签的日产能。
    """
    if m == "m_source":
        # m_source 为虚拟供料节点，不对应集批标签，实际供料量由上游供料约束单独控制。
        return float(MAX_WEIGHT_INT)
    camp_label = model_input.camp_d_m[(d, m)]
    return float(config.capacity[(m, camp_label, global_t)])


def _get_machine_max_capacity(config: Any, m: str, global_t: int) -> float:
    """
    获取机组 m 在第 global_t 天所有集批标签中的最大日产能。

    该值仅用于：
    1. 机组总产出变量 O_m_t 的上界；
    2. 判断该机组在当天是否为整日停机。
    """
    return float(
        max(
            (cap for (_m, _, _t), cap in config.capacity.items() if _m == m and _t == global_t),
            default=0,
        )
    )


def _get_mathopt_utilization_coeff(model_input: Any, d: str, m: str, global_t: int) -> float:
    """
    将预处理口径的 a_d_m_t 转回利用率约束所需的真实业务系数。

    预处理阶段保存的是：
        a_d_m_t = 1000 / C_(m, camp_d_m, t)

    建模公式需要的是：
        u_m_t = 100 * Σ((1 / C_(m, camp_d_m, t)) * O_d_m_t)

    因此这里先除回预处理阶段的放大倍率，再乘上 100，
    得到可直接作用在 O_d_m_t 上的线性系数：
        coeff = 100 * a_d_m_t / PREPROCESS_UTILIZATION_SCALE
    """
    return UTILIZATION_SCALE * float(model_input.a_d_m_t[(d, m, global_t)]) / PREPROCESS_UTILIZATION_SCALE


def build_single_window_milp_program(
    config: Any,
    model_input: Any,
    *,
    modeling_period: int,
    k: int = 0,
    preferred_backend: str | None = None,
) -> BuiltResourceFlowMilpProgram:
    """
    构建物流平衡模型（变量、约束、目标函数）。

    k: 滚动规划求解轮次（从 0 开始）
    """
    solve_config: dict[str, Any] = {}
    if preferred_backend:
        solve_config["preferred_backend"] = preferred_backend
    builder = ModelBuilder(
        metadata={
            "problem_family": "resource_flow",
            "formulation": "milp",
            "window_index": k,
            "modeling_period": modeling_period,
            "contracts": len(model_input.D),
            "machines": len(config.m_real),
        },
        solve_config=solve_config,
    )
    vars_by_name: dict[str, Any] = {}
    m_ids = model_input.M_ids
    d_ids = model_input.D_ids
    active_A_ready = _get_active_A_ready(config, model_input, modeling_period, k)

    def float_var(name: str, lb: float, ub: float) -> Any:
        expr = builder.float_var(default=float(lb), lb=float(lb), ub=float(ub), name=name)
        vars_by_name[name] = expr
        return expr

    def binary_var(name: str) -> Any:
        expr = builder.bool_var(default=False, name=name)
        vars_by_name[name] = expr
        return expr

    def add_max_constraints(target: Any, exprs: list[Any], selector_base_name: str) -> None:
        """
        通过 selector binary + Big-M 做 target = max(exprs) 的精确线性化。
        """
        selectors = [binary_var(f"{selector_base_name}_sel{i}") for i in range(len(exprs))]
        builder.constraint(_sum_expr(builder, selectors) == 1, name=f"{selector_base_name}_pick_one")
        for index, expr in enumerate(exprs):
            builder.constraint(target >= expr, name=f"{selector_base_name}_lb_{index}")
            builder.constraint(target <= expr + MAX_SELECTOR_BIG_M * (1 - selectors[index]), name=f"{selector_base_name}_ub_{index}")

    # ============= 主决策变量 x_(d,m,n,t) =============
    for (m, n) in config.m_logistics:
        if (m, n) not in model_input.D_m_n:
            continue
        for d in model_input.D_m_n[(m, n)]:
            for t in range(1, modeling_period + 1):
                global_t = _get_global_t(config.step, k, t)
                positive_ub = min(model_input.Q_d[d], _get_contract_machine_capacity(config, model_input, d, m, global_t))
                positive_lb = min(MIN_BATCH_QTY, positive_ub)
                x_name = f"x_d{d_ids[d]}_m{m_ids[m]}_n{m_ids[n]}_t{t}"
                x_var = float_var(x_name, 0.0, max(0.0, float(positive_ub)))
                if positive_ub <= EPSILON:
                    continue
                # 用二元变量 y 约束：x = 0 或 x >= positive_lb
                y_var = binary_var(f"y_{x_name}")
                builder.constraint(x_var <= positive_ub * y_var, name=f"{x_name}_batch_ub")
                builder.constraint(x_var >= positive_lb * y_var, name=f"{x_name}_batch_lb")

    # ============= 状态（辅助）变量 =============
    # 机组总库存 I_(m,t)
    # 合同库存状态 I_(m,t)^d
    # 库存偏移量 delta_I_range_(m,t) / delta_I_expect_(m,t)
    # 机组日产出 O_(m,t)
    # 合同机组日产出 O_(m,t)^d
    # 机组产能利用率 u_(m,t)
    # 低利用率指示变量 z_(m,t) - 当日产能利用率低于标准值时取 1，达标取 0
    for m in config.m_real:
        m_id = m_ids[m]
        for t in range(modeling_period + 1):
            float_var(f"I_m{m_id}_t{t}", 0.0, MAX_WEIGHT_INT)
            float_var(f"delta_I_range_m{m_id}_t{t}", 0.0, MAX_WEIGHT_INT)
            float_var(f"delta_I_expect_m{m_id}_t{t}", 0.0, MAX_WEIGHT_INT)
            for d in model_input.D_m[m]:
                float_var(f"I_d{d_ids[d]}_m{m_id}_t{t}", 0.0, MAX_WEIGHT_INT)
            if t == 0:
                continue
            global_t = _get_global_t(config.step, k, t)
            float_var(f"O_m{m_id}_t{t}", 0.0, _get_machine_max_capacity(config, m, global_t))
            float_var(f"u_m{m_id}_t{t}", 0.0, UTILIZATION_SCALE)
            binary_var(f"z_m{m_id}_t{t}")
            for d in model_input.D_m[m]:
                float_var(
                    f"O_d{d_ids[d]}_m{m_id}_t{t}",
                    0.0,
                    _get_contract_machine_capacity(config, model_input, d, m, global_t),
                )
                float_var(f"C_d{d_ids[d]}_m{m_id}_t{t}", 0.0, MAX_WEIGHT_INT)

    # 合同剩余交付需求量 R_(d,t)
    for d in model_input.D:
        d_id = d_ids[d]
        for t in range(modeling_period + 1):
            float_var(f"R_d{d_id}_t{t}", 0.0, max(0.0, float(model_input.Q_d[d])))

    # 合同机组交期未完成量 R_(d,m)^m_due
    for d, m, _ in _get_active_A_m_due(config, model_input, modeling_period, k):
        float_var(
            f"R_m_due_d{d_ids[d]}_m{m_ids[m]}",
            0.0,
            max(0.0, float(model_input.owe_d_m[(d, m)])),
        )

    # 临期合同有效滞留库存 I_(m,t)^(d,eff)
    for d, m, t, _ in active_A_ready:
        float_var(f"I_d_eff_d{d_ids[d]}_m{m_ids[m]}_t{t}", 0.0, MAX_WEIGHT_INT)

    # ============= 目标函数（辅助）变量 =============
    cost_inventory = float_var("cost_inventory", 0.0, MAX_INT)
    cost_utilization = float_var("cost_utilization", 0.0, MAX_INT)
    cost_contract = float_var("cost_contract", 0.0, MAX_INT)
    cost_contract_base = float_var("cost_contract_base", 0.0, MAX_INT)
    cost_contract_m_due = float_var("cost_contract_m_due", 0.0, MAX_INT)
    cost_contract_ready = float_var("cost_contract_ready", 0.0, MAX_INT)
    cost_i_range = float_var("cost_I_range", 0.0, MAX_INT)
    cost_i_expect = float_var("cost_I_expect", 0.0, MAX_INT)

    # ================ 约束定义 ================
    # 1. 库存相关约束 / 平衡推演
    for m in config.m_real:
        m_id = m_ids[m]
        yield_value = float(config.m_yield[m])
        m_contract_list = model_input.D_m[m]
        for t in range(modeling_period + 1):
            i_m_t = vars_by_name[f"I_m{m_id}_t{t}"]
            delta_range_t = vars_by_name[f"delta_I_range_m{m_id}_t{t}"]
            delta_expect_t = vars_by_name[f"delta_I_expect_m{m_id}_t{t}"]
            global_t = _get_global_t(config.step, k, t)

            if t == 0:
                # 初始库存由输入数据直接给定
                builder.constraint(i_m_t == max(model_input.I_m_0.get(m, 0), 0.0), name=f"init_I_m_{m}_{t}")
                for d in m_contract_list:
                    d_id = d_ids[d]
                    builder.constraint(
                        vars_by_name[f"I_d{d_id}_m{m_id}_t0"] == max(model_input.I_d_m_0.get((d, m), 0), 0.0),
                        name=f"init_I_d_{d}_{m}_{t}",
                    )
            else:
                machine_consumption_terms: list[Any] = []
                machine_inflow_terms: list[Any] = []
                machine_inflow_t0 = 0.0
                i_m_prev_t = vars_by_name[f"I_m{m_id}_t{t-1}"]
                for d in m_contract_list:
                    d_id = d_ids[d]
                    o_d_m_t = vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"]
                    c_d_m_t = vars_by_name[f"C_d{d_id}_m{m_id}_t{t}"]
                    i_d_m_t = vars_by_name[f"I_d{d_id}_m{m_id}_t{t}"]
                    i_d_m_prev_t = vars_by_name[f"I_d{d_id}_m{m_id}_t{t-1}"]

                    # 合同当日生产消耗材料量
                    builder.constraint(yield_value * c_d_m_t == YIELD_SCALE * o_d_m_t, name=f"cons_{d}_{m}_{t}")
                    machine_consumption_terms.append(c_d_m_t)

                    inflow_d_terms: list[Any] = []
                    inflow_d_t0 = 0.0
                    for (i, mm) in model_input.E_d[d]:
                        if mm != m:
                            continue
                        if t == 1:
                            # t=1 的入库量来自外部传入的 t0 初始流量
                            inflow_d_t0 += model_input.x_t0.get((d, i, mm), 0)
                        else:
                            inflow_var = vars_by_name[f"x_d{d_id}_m{m_ids[i]}_n{m_ids[mm]}_t{t - 1}"]
                            inflow_d_terms.append(inflow_var)
                            machine_inflow_terms.append(inflow_var)

                    # 合同级库存动态平衡
                    if t == 1:
                        builder.constraint(i_d_m_t - i_d_m_prev_t + c_d_m_t == inflow_d_t0, name=f"I_d_bal_{d}_{m}_{t}")
                        machine_inflow_t0 += inflow_d_t0
                    else:
                        builder.constraint(
                            i_d_m_t - i_d_m_prev_t - _sum_expr(builder, inflow_d_terms) + c_d_m_t == 0,
                            name=f"I_d_bal_{d}_{m}_{t}",
                        )

                # 机组级库存动态平衡
                if t == 1:
                    builder.constraint(
                        i_m_t - i_m_prev_t + _sum_expr(builder, machine_consumption_terms) == machine_inflow_t0,
                        name=f"I_m_bal_{m}_{t}",
                    )
                else:
                    builder.constraint(
                        i_m_t - i_m_prev_t - _sum_expr(builder, machine_inflow_terms) + _sum_expr(builder, machine_consumption_terms) == 0,
                        name=f"I_m_bal_{m}_{t}",
                    )

            # 机组总库存偏移量
            range_lb, range_ub = config.I_range[(m, global_t)]
            expect_lb, expect_ub = config.I_expect[m]
            # delta_I_range_m_t = max(0, I_m_t - I_m_t_ub, I_m_t_lb - I_m_t)
            add_max_constraints(
                delta_range_t,
                [i_m_t - range_ub, range_lb - i_m_t, builder.const(0.0)],
                f"selector_delta_I_range_m{m_id}_t{t}",
            )
            # delta_I_expect_m_t = max(0, I_m_t - I_expect_ub, I_expect_lb - I_m_t)
            add_max_constraints(
                delta_expect_t,
                [i_m_t - expect_ub, expect_lb - i_m_t, builder.const(0.0)],
                f"selector_delta_I_expect_m{m_id}_t{t}",
            )

    # 2. 产出与利用率约束
    for m in config.m_real:
        m_id = m_ids[m]
        for t in range(1, modeling_period + 1):
            global_t = _get_global_t(config.step, k, t)
            o_m_t = vars_by_name[f"O_m{m_id}_t{t}"]
            u_m_t = vars_by_name[f"u_m{m_id}_t{t}"]
            z_m_t = vars_by_name[f"z_m{m_id}_t{t}"]
            machine_outflow_terms: list[Any] = []
            for d in model_input.D_m[m]:
                d_id = d_ids[d]
                o_d_m_t = vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"]
                x_terms = [
                    vars_by_name[f"x_d{d_id}_m{m_id}_n{m_ids[j]}_t{t}"]
                    for (mm, j) in model_input.E_d[d]
                    if mm == m
                ]
                builder.constraint(o_d_m_t == _sum_expr(builder, x_terms), name=f"O_d_def_{d}_{m}_{t}")
                machine_outflow_terms.append(o_d_m_t)

            builder.constraint(o_m_t == _sum_expr(builder, machine_outflow_terms), name=f"O_m_def_{m}_{t}")
            max_capacity_t = _get_machine_max_capacity(config, m, global_t)
            if max_capacity_t == 0:
                # 整日停机时，要求产出为 0，利用率记为 100
                builder.constraint(o_m_t == 0, name=f"stop_output_{m}_{t}")
                builder.constraint(u_m_t == UTILIZATION_SCALE, name=f"stop_util_{m}_{t}")
            else:
                utilization_terms = [
                    _get_mathopt_utilization_coeff(model_input, d, m, global_t) * vars_by_name[f"O_d{d_ids[d]}_m{m_id}_t{t}"]
                    for d in model_input.D_m[m]
                ]
                builder.constraint(u_m_t == _sum_expr(builder, utilization_terms), name=f"util_{m}_{t}")
            # 用 z_m_t 表示利用率是否低于标准值
            builder.constraint(
                u_m_t <= float(config.capacity_utilization_standard) - EPSILON + UTILIZATION_SCALE * (1 - z_m_t),
                name=f"util_flag_ub_{m}_{t}",
            )
            builder.constraint(
                u_m_t >= float(config.capacity_utilization_standard) - UTILIZATION_SCALE * z_m_t,
                name=f"util_flag_lb_{m}_{t}",
            )

    # 3. 合同剩余量 / 来源供料 / 机组累计产出上界
    for d in model_input.D:
        d_id = d_ids[d]
        for t in range(modeling_period + 1):
            if t == 0:
                builder.constraint(vars_by_name[f"R_d{d_id}_t{t}"] == max(0.0, float(model_input.Q_d[d])), name=f"R_init_{d}")
                continue
            production_d_terms = [
                vars_by_name[f"O_d{d_id}_m{m_ids[m]}_t{t}"]
                for (m, n) in model_input.E_d[d]
                if n == "m_sink"
            ]
            builder.constraint(
                vars_by_name[f"R_d{d_id}_t{t}"] >= vars_by_name[f"R_d{d_id}_t{t - 1}"] - _sum_expr(builder, production_d_terms),
                name=f"R_roll_{d}_{t}",
            )

        d_inflow_source_terms = [
            vars_by_name[f"x_d{d_id}_m{m_ids[m]}_n{m_ids[n]}_t{t}"]
            for (m, n) in model_input.E_d[d]
            if m == "m_source"
            for t in range(1, modeling_period + 1)
        ]
        builder.constraint(
            _sum_expr(builder, d_inflow_source_terms) <= model_input.owe_d_m[(d, "m_source")],
            name=f"source_total_{d}",
        )

        for (m, _) in model_input.E_d[d]:
            if m == "m_source":
                continue
            m_id = m_ids[m]
            builder.constraint(
                _sum_expr(
                    builder,
                    [vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"] for t in range(1, modeling_period + 1)],
                )
                <= round(model_input.owe_d_m[(d, m)] * (1 + model_input.overprod_d_m[(d, m)] / 100)),
                name=f"machine_total_{d}_{m}",
            )

    # 4. 每日总供料约束
    for t in range(1, modeling_period + 1):
        global_t = _get_global_t(config.step, k, t)
        inflow_source_terms = [
            vars_by_name[f"x_d{d_ids[d]}_m{m_ids[m]}_n{m_ids[n]}_t{t}"]
            for d in model_input.D
            for (m, n) in model_input.E_d[d]
            if m == "m_source"
        ]
        builder.constraint(
            _sum_expr(builder, inflow_source_terms) <= float(config.m_source_capacity[global_t]),
            name=f"source_day_{t}",
        )

    key_machines = list(config.m_real_key)
    common_machines = [m for m in config.m_real if m not in set(key_machines)]
    n_key = len(key_machines) * (modeling_period + 1)
    n_common = len(common_machines) * (modeling_period + 1)

    # 5. 库存成本
    cost_i_range_terms: list[Any] = []
    if n_key > 0:
        avg_key_range = float_var("avg_delta_I_range_key", 0.0, MAX_INT)
        key_range_sum = _sum_expr(
            builder,
            [vars_by_name[f"delta_I_range_m{m_ids[m]}_t{t}"] for m in key_machines for t in range(modeling_period + 1)],
        )
        builder.constraint(float(n_key) * avg_key_range == key_range_sum, name="avg_delta_I_range_key_def")
        cost_i_range_terms.append(int(config.cost_coeff_inv_range_key) * avg_key_range)
    if n_common > 0:
        avg_common_range = float_var("avg_delta_I_range_common", 0.0, MAX_INT)
        common_range_sum = _sum_expr(
            builder,
            [vars_by_name[f"delta_I_range_m{m_ids[m]}_t{t}"] for m in common_machines for t in range(modeling_period + 1)],
        )
        builder.constraint(float(n_common) * avg_common_range == common_range_sum, name="avg_delta_I_range_common_def")
        cost_i_range_terms.append(int(config.cost_coeff_inv_range_common) * avg_common_range)
    builder.constraint(cost_i_range == _sum_expr(builder, cost_i_range_terms), name="cost_I_range_def")

    cost_i_expect_terms: list[Any] = []
    if n_key > 0:
        avg_key_expect = float_var("avg_delta_I_expect_key", 0.0, MAX_INT)
        key_expect_sum = _sum_expr(
            builder,
            [vars_by_name[f"delta_I_expect_m{m_ids[m]}_t{t}"] for m in key_machines for t in range(modeling_period + 1)],
        )
        builder.constraint(float(n_key) * avg_key_expect == key_expect_sum, name="avg_delta_I_expect_key_def")
        cost_i_expect_terms.append(int(config.cost_coeff_inv_expect_key) * avg_key_expect)
    if n_common > 0:
        avg_common_expect = float_var("avg_delta_I_expect_common", 0.0, MAX_INT)
        common_expect_sum = _sum_expr(
            builder,
            [vars_by_name[f"delta_I_expect_m{m_ids[m]}_t{t}"] for m in common_machines for t in range(modeling_period + 1)],
        )
        builder.constraint(float(n_common) * avg_common_expect == common_expect_sum, name="avg_delta_I_expect_common_def")
        cost_i_expect_terms.append(int(config.cost_coeff_inv_expect_common) * avg_common_expect)
    builder.constraint(cost_i_expect == _sum_expr(builder, cost_i_expect_terms), name="cost_I_expect_def")
    builder.constraint(
        cost_inventory == int(config.cost_coeff_inv_range) * cost_i_range + int(config.cost_coeff_inv_expect) * cost_i_expect,
        name="cost_inventory_def",
    )

    # 6. 产能利用率成本
    low_utilization_indicator_terms = [
        vars_by_name[f"z_m{m_ids[m]}_t{t}"]
        for m in config.m_real
        for t in range(1, modeling_period + 1)
    ]
    low_utilization_value_terms = [
        UTILIZATION_SCALE - vars_by_name[f"u_m{m_ids[m]}_t{t}"]
        for m in config.m_real
        for t in range(1, modeling_period + 1)
    ]
    utilization_numerator = int(config.cost_coeff_mu1) * _sum_expr(builder, low_utilization_indicator_terms) + int(config.cost_coeff_mu2) * _sum_expr(builder, low_utilization_value_terms)
    builder.constraint(float(modeling_period) * cost_utilization == utilization_numerator, name="cost_utilization_def")

    # 7. 合同交付成本：基础延期成本
    d_cost_terms: list[Any] = []
    for d in model_input.D:
        if model_input.Q_d[d] <= 0:
            continue
        d_id = d_ids[d]
        for t in range(1, modeling_period + 1):
            d_cost_terms.append(int(model_input.e_d[d] * model_input.P_t[(d, t)]) * vars_by_name[f"R_d{d_id}_t{t}"])
    contract_norm = max(round(len(model_input.D) / 10), 1)
    if d_cost_terms:
        builder.constraint(100.0 * contract_norm * cost_contract_base == _sum_expr(builder, d_cost_terms), name="cost_contract_base_def")
    else:
        builder.constraint(cost_contract_base == 0, name="cost_contract_base_zero")

    # 8. 合同交付成本：机组交期未完成量
    active_A_m_due = _get_active_A_m_due(config, model_input, modeling_period, k)
    m_due_cost_terms: list[Any] = []
    for d, m, local_t_d_m_due in active_A_m_due:
        d_id = d_ids[d]
        m_id = m_ids[m]
        r_m_due = vars_by_name[f"R_m_due_d{d_id}_m{m_id}"]
        produced_until_due_terms = [vars_by_name[f"O_d{d_id}_m{m_id}_t{t}"] for t in range(1, local_t_d_m_due + 1)]
        builder.constraint(
            r_m_due >= float(model_input.owe_d_m[(d, m)]) - _sum_expr(builder, produced_until_due_terms),
            name=f"cost_contract_due_shortfall_{d}_{m}",
        )
        m_due_cost_terms.append(r_m_due)
    if m_due_cost_terms:
        builder.constraint(float(len(m_due_cost_terms)) * cost_contract_m_due == _sum_expr(builder, m_due_cost_terms), name="cost_contract_m_due_def")
    else:
        builder.constraint(cost_contract_m_due == 0, name="cost_contract_m_due_zero")

    # 9. 合同交付成本：临期可生产库存滞留
    ready_norm = sum(weight for _, _, _, weight in active_A_ready)
    if ready_norm > 0:
        for d, m, t, _ in active_A_ready:
            d_id = d_ids[d]
            m_id = m_ids[m]
            add_max_constraints(
                vars_by_name[f"I_d_eff_d{d_id}_m{m_id}_t{t}"],
                [
                    vars_by_name[f"I_d{d_id}_m{m_id}_t{t}"] - float(model_input.I_d_m_0_excess.get((d, m), 0)),
                    builder.const(0.0),
                ],
                f"selector_I_d_eff_d{d_id}_m{m_id}_t{t}",
            )
        ready_cost_terms = [
            weight * vars_by_name[f"I_d_eff_d{d_ids[d]}_m{m_ids[m]}_t{t}"]
            for d, m, t, weight in active_A_ready
        ]
        builder.constraint(float(ready_norm) * cost_contract_ready == _sum_expr(builder, ready_cost_terms), name="cost_contract_ready_def")
    else:
        builder.constraint(cost_contract_ready == 0, name="cost_contract_ready_zero")

    # 10. 合同总成本
    builder.constraint(
        cost_contract
        == cost_contract_base
        + int(config.cost_coeff_contract_m_due) * cost_contract_m_due
        + int(config.cost_coeff_contract_ready) * cost_contract_ready,
        name="cost_contract_def",
    )

    # 11. 总目标函数
    builder.minimize(
        int(config.cost_coeff_inventory) * cost_inventory
        + int(config.cost_coeff_utility) * cost_utilization
        + int(config.cost_coeff_contract) * cost_contract,
        name="resource_flow_milp_objective",
    )

    program = builder.freeze()
    return BuiltResourceFlowMilpProgram(
        program=program,
        variable_node_ids={name: expr.node_id for name, expr in vars_by_name.items()},
        metadata={
            "problem_family": "resource_flow",
            "formulation": "milp",
            "window_index": k,
            "modeling_period": modeling_period,
        },
    )
