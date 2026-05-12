from aps.preprocess import GeneratorResult, Generator
from aps.orm import Table
import numpy as np
import pandas as pd

from .tables import iTables, tTables




class tProcessGenerator(Generator):
    params_defined = [
        tTables.PROCESS,
        iTables.WIDTH_LIMIT,
        iTables.PARAM,
        iTables.CATEGORY_LIST,
        iTables.THICK_LIMIT,
    ]
    table_name = tTables.PROCESS

    def _apply_width_limits(self, t_process_data, width_limit_data):
        """按厚度区间与外板/高表面条件，计算宽度上下限。"""
        # 初始化宽度上下限列
        t_process_data["width_up_jump"] = 0.0
        t_process_data["width_down_jump"] = 0.0

        if width_limit_data.empty:
            return t_process_data

        # 遍历 i_width_limit 中的每条记录，根据厚度范围和条件匹配
        for _, limit_row in width_limit_data.iterrows():
            thickness_lower = limit_row.get("entry_thickness_lower_bound", 0)
            thickness_upper = limit_row.get("entry_thickness_upper_bound", float("inf"))
            width_change_limit = limit_row.get("width_change_limit", 0)
            is_outer_or_high_surface = limit_row.get("is_outer_or_high_surface", 0)

            # 判断是否为 外板 产品且表面等级>=3000
            is_0350_high_surface = (
                (t_process_data["is_outer"] == 1)
                & (t_process_data["surface_grade"] >= 3000)
            )

            # 判断是否为其他产品（非0350或表面等级<3000）
            is_other_product = ~is_0350_high_surface

            # 根据厚度范围匹配
            thickness_mask = (t_process_data["thickness"] >= thickness_lower) & (
                t_process_data["thickness"] < thickness_upper
                if thickness_upper != float("inf")
                else True
            )

            # 外板产品且表面等级>=3000：使用 is_outer_or_high_surface=1 的记录
            if is_0350_high_surface.any():
                mask_0350 = (
                    thickness_mask
                    & is_0350_high_surface
                    & (is_outer_or_high_surface == 1)
                )
                t_process_data.loc[mask_0350, "width_up_jump"] = (
                    t_process_data.loc[mask_0350, "width"] + width_change_limit
                )
                t_process_data.loc[mask_0350, "width_down_jump"] = (
                    t_process_data.loc[mask_0350, "width"] - width_change_limit
                )

            # 其他产品：使用 is_outer_or_high_surface=0 的记录
            if is_other_product.any():
                mask_other = thickness_mask & is_other_product & (is_outer_or_high_surface == 0)
                t_process_data.loc[mask_other, "width_up_jump"] = (
                    t_process_data.loc[mask_other, "width"] + width_change_limit
                )
                t_process_data.loc[mask_other, "width_down_jump"] = (
                    t_process_data.loc[mask_other, "width"] - width_change_limit
                )

        return t_process_data

    def _apply_temp_limits(self, t_process_data, param_data, category_list_data):
        """按参数温度幅度与过渡牌号规则，计算温度上下限。"""
        if not param_data.empty:
            temp_limit = param_data.iloc[0].get("annealing_temp_upper_limit", 40)
        else:
            temp_limit = 40  # 默认值


        # 获取 i_category_list 中的过渡牌号列表
        transition_grades = set()
        if not category_list_data.empty:
            transition_grades = {
                g for g in category_list_data["transition_grade"].dropna().tolist() if str(g).strip()
            }

        # 初始化温度上下限列
        t_process_data["temp_up_jump"] = t_process_data["temp"] + temp_limit
        t_process_data["temp_down_jump"] = t_process_data["temp"] - temp_limit

        # 当 grade 属于过渡牌号时，没有温度限制
        # temp_up_jump = maxint, temp_down_jump = 0
        if transition_grades:
            grade_series = t_process_data["grade"].fillna("").astype(str)
            mask_transition = grade_series.str.startswith(tuple(transition_grades))
            t_process_data.loc[mask_transition, "temp_up_jump"] = 10000
            t_process_data.loc[mask_transition, "temp_down_jump"] = 0

        return t_process_data

    def _apply_thickness_limits(self, t_process_data, thick_limit_data):
        """根据钢种分组与厚度区间，生成厚度上下限列。"""
        t_process_data["thickness_up_jump"] = t_process_data["thickness"]
        t_process_data["thickness_down_jump"] = t_process_data["thickness"]

        if thick_limit_data.empty:
            return t_process_data

        grade_category = t_process_data["grade_category"].fillna("")
        steel_type = t_process_data["steel_type"].fillna("")

        # CQ/DQ/DDQ/EDDQ 非外板用途钢种（使用 is_cq_dq_ddq = 1 的界限）
        is_special_1 = grade_category.isin(["CQ", "DQ", "DDQ", "EDDQ"]) & (t_process_data["is_outer"] == 0)
        # CQ/DQ/DDQ 级钢种（使用 is_cq_dq_ddq_eddq_non_outer = 1 的界限）
        is_special_2 = grade_category.isin(["CQ", "DQ", "DDQ"]) & (~is_special_1)
        # 软钢/磷化钢特殊规则（使用 is_special_cat = 1 的界限）
        is_special_steel_type = steel_type.isin(["软钢", "磷化钢"])
        # 其他钢种（默认界限）

        def apply_thickness_limits(mask, subset):
            if subset.empty:
                return
            max_upper = subset["thickness_upper_bound"].max()
            for _, limit_row in subset.iterrows():
                lower = limit_row.get("thickness_lower_bound", 0.0)
                upper = limit_row.get("thickness_upper_bound", max_upper)
                tol = limit_row.get("thickness_tolerance", 0.0)
                # 最后一个区间采用闭区间，避免上界漏匹配
                if upper == max_upper:
                    thickness_mask = (t_process_data["thickness"] >= lower) & (
                        t_process_data["thickness"] <= upper
                    )
                else:
                    thickness_mask = (t_process_data["thickness"] >= lower) & (
                        t_process_data["thickness"] < upper
                    )
                # 仅对指定钢种组(mask)且处于该厚度区间的订单应用容差
                final_mask = mask & thickness_mask
                if final_mask.any():
                    # 上下限 = 实际厚度 ± 容差
                    t_process_data.loc[final_mask, "thickness_up_jump"] = (
                        t_process_data.loc[final_mask, "thickness"] + tol
                    )
                    t_process_data.loc[final_mask, "thickness_down_jump"] = (
                        t_process_data.loc[final_mask, "thickness"] - tol
                    )

        subset_special_1 = thick_limit_data[thick_limit_data["is_cq_dq_ddq"] == 1]
        subset_special_2 = thick_limit_data[
            thick_limit_data["is_cq_dq_ddq_eddq_non_outer"] == 1
        ]
        subset_default = thick_limit_data[
            (thick_limit_data["is_cq_dq_ddq"] == 0)
            & (thick_limit_data["is_cq_dq_ddq_eddq_non_outer"] == 0)
            & (thick_limit_data["is_special_cat"] == 0)
        ]
        subset_special_steel_type = thick_limit_data[
            thick_limit_data["is_special_cat"] == 1
        ]

        apply_thickness_limits(pd.Series(True, index=t_process_data.index), subset_default)
        apply_thickness_limits(is_special_1, subset_special_1)
        apply_thickness_limits(is_special_2, subset_special_2)
        apply_thickness_limits(is_special_steel_type, subset_special_steel_type)
        

        # 统一厚度上下限小数位，避免浮点误差
        t_process_data["thickness_up_jump"] = t_process_data["thickness_up_jump"].round(1)
        t_process_data["thickness_down_jump"] = t_process_data["thickness_down_jump"].round(1)

        return t_process_data

    def execute(
        self,
        t_process: Table,
        i_width_limit: Table,
        i_param: Table,
        i_category_list: Table,
        i_thick_limit: Table,
    ) -> GeneratorResult:
        """
        生成 width_up_jump 和 width_down_jump

        """

        t_process_data = t_process.df.copy()
        param_data = i_param.df.copy()  
        t_process_data["surface_grade"] = t_process_data["surface_grade"].astype(int)

        # i_process 中参与排产的订单默认不是留料；若上游未显式带出该列，这里兜底补 0。
        if "left_mat_priority_outer" not in t_process_data.columns:
            t_process_data["left_mat_priority_outer"] = 0
        else:
            t_process_data["left_mat_priority_outer"] = (
                t_process_data["left_mat_priority_outer"].fillna(0).astype(int)
            )

    
        # is_thin 含义：
        # 1 = 薄规格或HSLA（厚度<=0.5 或 grade_category 为 HSLA）
        # 0 = 非薄规格但属于 CQ/DQ
        # 2 = 其他（既非薄规格/HSLA，也非 CQ/DQ）
        is_thin_condition = (t_process_data["thickness"] <= 0.5) | (t_process_data["grade_category"] == "HSLA")
        is_cq_dq_condition = t_process_data["grade_category"].isin(["CQ", "DQ"])
        t_process_data["is_thin"] = np.where(
            is_thin_condition,
            1,
            np.where(
                is_cq_dq_condition,
                0,
                2
            )
        )

        # is_simple: 表面等级<=3000 且后处理=0
        t_process_data["is_simple"] = (
            (t_process_data["surface_grade"] <= 3000) &
            (t_process_data["post_process"] == 0)
        ).astype(int)

        # grinding_class 取值逻辑：
        # 1) 读取 i_category_list.grinding_cat，按行顺序编号：第1行=0，之后依次+1
        # 2) grade_category 命中 grinding_cat 时取对应编号
        # 3) 未命中时取“最后一行编号 + 10”
        #    例如 grinding_cat 前两行是 DDQ、IF-HSS，则 DDQ=0、IF-HSS=1，其他=11
        category_list_data = i_category_list.df
        if not category_list_data.empty and "grinding_cat" in category_list_data.columns:
            grinding_cats = category_list_data["grinding_cat"].dropna().tolist()
        else:
            grinding_cats = []

        grinding_map = {cat: idx for idx, cat in enumerate(grinding_cats)}
        default_grinding_class = (len(grinding_cats) - 1 + 10) if grinding_cats else 10
        t_process_data["grinding_class"] = (
            t_process_data["grade_category"]
            .map(grinding_map)
            .fillna(default_grinding_class)
            .astype(int)
        )



        # 1:生成 width_up_jump 和 width_down_jump
        # 获取 i_width_limit 中的参数
        width_limit_data = i_width_limit.df.copy()
        t_process_data = self._apply_width_limits(t_process_data, width_limit_data)
        
        
        # 2:生成 temp_up_jump 和 temp_down_jump
        # 从 i_param 中获取 annealing_temp_upper_limit 作为温度变化限制
        t_process_data = self._apply_temp_limits(t_process_data, param_data, category_list_data)


        # 3:生成 thickness_up_jump 和 thickness_down_jump
        thick_limit_data = i_thick_limit.df.copy()
        t_process_data = self._apply_thickness_limits(t_process_data, thick_limit_data)

        # 重置 t_process_data 的索引
        t_process_data.reset_index(drop=True, inplace=True)



        self.shared.set("process_data", t_process_data)
        
        
        return GeneratorResult(tTables.PROCESS, t_process_data)
        

class tConnectablesGenerator(Generator):
    params_defined = [tTables.PROCESS, iTables.WIDTH_LIMIT_2, iTables.CATEGORY_CONNECTION, iTables.PARAM]
    table_name = tTables.CONNECTABLES

    @staticmethod
    def _calc_category_flag(cat_prev_ok: np.ndarray, cat_next_ok_slice: np.ndarray) -> np.ndarray:
        """品种可接：prev 属于允许前级集合 且 next 属于允许后级集合。"""
        # 对应原 _check_category 的双向集合约束逻辑
        return cat_prev_ok[:, None] & cat_next_ok_slice[None, :]

    @staticmethod
    def _calc_width_flag(
        prev_width: np.ndarray,
        prev_width_down: np.ndarray,
        prev_width_up: np.ndarray,
        next_width: np.ndarray,
        next_width_down: np.ndarray,
        next_width_up: np.ndarray,
        narrow_to_wide_threshold: float,
        width_change_upper_limit: float,
    ) -> np.ndarray:
        """入口宽度跳变约束 + 窄宽跃迁限制。"""
        # 对应原 _check_width：双向区间判断 + 窄料变宽限制
        prev_in_next = (prev_width[:, None] >= next_width_down[None, :]) & (
            prev_width[:, None] <= next_width_up[None, :]
        )
        next_in_prev = (next_width[None, :] >= prev_width_down[:, None]) & (
            next_width[None, :] <= prev_width_up[:, None]
        )
        narrow_to_wide = (prev_width[:, None] < next_width[None, :]) & (
            prev_width[:, None] < narrow_to_wide_threshold
        ) & ((next_width[None, :] - prev_width[:, None]) > width_change_upper_limit)
        return prev_in_next & next_in_prev & (~narrow_to_wide)

    @staticmethod
    def _calc_thickness_flag(
        prev_thickness: np.ndarray,
        prev_thickness_down: np.ndarray,
        prev_thickness_up: np.ndarray,
        next_thickness: np.ndarray,
        next_thickness_down: np.ndarray,
        next_thickness_up: np.ndarray,
    ) -> np.ndarray:
        """厚度跳变约束：根据厚度升降方向选择对应上下限。"""
        # 对应原 _check_thickness：厚料落在薄料上下限内
        prev_le = prev_thickness[:, None] <= next_thickness[None, :]
        next_in_prev = (next_thickness[None, :] >= prev_thickness_down[:, None]) & (
            next_thickness[None, :] <= prev_thickness_up[:, None]
        )
        prev_in_next = (prev_thickness[:, None] >= next_thickness_down[None, :]) & (
            prev_thickness[:, None] <= next_thickness_up[None, :]
        )
        return np.where(prev_le, next_in_prev, prev_in_next)

    @staticmethod
    def _calc_temp_flag(
        prev_thickness: np.ndarray,
        prev_temp: np.ndarray,
        prev_temp_down: np.ndarray,
        prev_temp_up: np.ndarray,
        next_thickness: np.ndarray,
        next_temp: np.ndarray,
        next_temp_down: np.ndarray,
        next_temp_up: np.ndarray,
        special_temp_upper_limit: float,
    ) -> np.ndarray:
        """温度双向落入区间；若任一任务 temp_down_jump 为 0，则视为可接。"""
        prev_in_next = (prev_temp[:, None] >= next_temp_down[None, :]) & (
            prev_temp[:, None] <= next_temp_up[None, :]
        )
        next_in_prev = (next_temp[None, :] >= prev_temp_down[:, None]) & (
            next_temp[None, :] <= prev_temp_up[:, None]
        )
        # 前后其中一卷是温度过度卷都可接
        zero_ok = (prev_temp_down[:, None] == 0) | (next_temp_down[None, :] == 0)
        # 特殊规则：一卷厚度小温度高、另一卷厚度大温度低，温差在阈值内可接
        thickness_small_temp_high = (prev_thickness[:, None] < next_thickness[None, :]) & (
            prev_temp[:, None] > next_temp[None, :]
        )
        thickness_large_temp_low = (prev_thickness[:, None] > next_thickness[None, :]) & (
            prev_temp[:, None] < next_temp[None, :]
        )
        special_ok = (
            (np.abs(prev_temp[:, None] - next_temp[None, :]) <= special_temp_upper_limit)
            & (thickness_small_temp_high | thickness_large_temp_low)
        )
        return (prev_in_next & next_in_prev) | zero_ok | special_ok

    @staticmethod
    def _calc_same_width_flag(
        prev_width: np.ndarray,
        prev_post_process: np.ndarray,
        prev_sell_code: np.ndarray,
        prev_out_width: np.ndarray,
        next_width: np.ndarray,
        next_post_process: np.ndarray,
        next_sell_code: np.ndarray,
        next_out_width: np.ndarray,
    ) -> np.ndarray:
        """
        同宽规则：
        1) 后卷后处理不为 0：入口宽度差 <= 15mm
        2) 后卷后处理为 0：入口宽度差 <= 20mm
        3) 对于剩下的不是同宽的前后卷，后卷后处理为 0 且后卷 sell_code 为 MC：
        宽的合同用出口宽度(out_width)，窄的合同用入口宽度(width)，差 <= 20mm
        """
        # 计算入口宽度差
        abs_width = np.abs(prev_width[:, None] - next_width[None, :])

        # 条件 1: 后卷后处理不为 0，入口宽度差 <= 15mm
        pp_not_0 = next_post_process[None, :] != 0
        same_width_1 = pp_not_0 & (abs_width <= 15)

        # 条件 2: 后卷后处理为 0，入口宽度差 <= 20mm
        pp_0 = next_post_process[None, :] == 0
        same_width_2 = pp_0 & (abs_width <= 20)

        # 条件 3: 剩下的不是同宽的前后卷，后卷后处理为 0 且后卷 sell_code 为 MC
        next_mc = pp_0 & (next_sell_code[None, :] == "MC")
        wider = np.maximum(prev_out_width[:, None], next_out_width[None, :])
        narrower = np.minimum(prev_width[:, None], next_width[None, :])
        same_width_3 = next_mc & (np.abs(wider - narrower) <= 20)

        # 合并所有同宽条件
        same_width = same_width_1 | same_width_2 | same_width_3

        return same_width.astype(int)

    def execute(self, t_process: Table, i_width_limit_2: Table, i_category_connection: Table, i_param: Table) -> GeneratorResult:
        """
        生成接续表 t_connectables
        """
        import pandas as pd
        
        t_process_data = self.shared.get("process_data")
        
        if t_process_data is None or t_process_data.empty:
            t_process_data = t_process.df.copy()
        
        width_limit_2_data = i_width_limit_2.df
        if not width_limit_2_data.empty:
            narrow_to_wide_threshold = width_limit_2_data.iloc[0].get("narrow_to_wide_threshold", 1000)
            width_change_upper_limit = width_limit_2_data.iloc[0].get("width_change_upper_limit", 200)
        else:
            narrow_to_wide_threshold = 1000
            width_change_upper_limit = 200
        
        category_limit_data = i_category_connection.df.copy()
        param_data = i_param.df.copy()
        if not param_data.empty:
            special_temp_upper_limit = param_data.iloc[0].get("spetial_temp_upper_limit", 50)
        else:
            special_temp_upper_limit = 50

        # 向量化计算，分块避免 O(n^2) Python 循环。
        # 下方的 *_flag 计算与原 _check_category/_check_width/_check_thickness/_check_temp/_check_same_width 规则保持一致。
        order_no = t_process_data["order_no"].to_numpy()
        width = t_process_data["width"].to_numpy()
        width_down = t_process_data["width_down_jump"].to_numpy()
        width_up = t_process_data["width_up_jump"].to_numpy()
        thickness = t_process_data["thickness"].to_numpy()
        thickness_down = t_process_data["thickness_down_jump"].to_numpy()
        thickness_up = t_process_data["thickness_up_jump"].to_numpy()
        temp = t_process_data["temp"].to_numpy()
        temp_down = t_process_data["temp_down_jump"].to_numpy()
        temp_up = t_process_data["temp_up_jump"].to_numpy()
        post_process = t_process_data["post_process"].to_numpy()
        sell_code = t_process_data["sell_code"].fillna("").to_numpy()
        out_width = t_process_data["out_width"].to_numpy()
        out_width = np.where(np.isnan(out_width), width, out_width)
        grade_category = t_process_data["grade_category"].fillna("").to_numpy()

        n = len(t_process_data)
        if n == 0:
            return GeneratorResult(self.table_name, pd.DataFrame())

        if category_limit_data.empty:
            cat_prev_ok = np.ones(n, dtype=bool)
            cat_next_ok = np.ones(n, dtype=bool)
        else:
            prev_grades = set(category_limit_data["prev_grade_category"].dropna().tolist())
            next_grades = set(category_limit_data["next_grade_category"].dropna().tolist())
            cat_prev_ok = np.isin(grade_category, list(next_grades))
            cat_next_ok = np.isin(grade_category, list(prev_grades))

        records = []
        block = 2000
        for j0 in range(0, n, block):
            j1 = min(n, j0 + block)
            b = j1 - j0

            next_width = width[j0:j1]
            next_width_down = width_down[j0:j1]
            next_width_up = width_up[j0:j1]
            next_thickness = thickness[j0:j1]
            next_thickness_down = thickness_down[j0:j1]
            next_thickness_up = thickness_up[j0:j1]
            next_temp = temp[j0:j1]
            next_temp_down = temp_down[j0:j1]
            next_temp_up = temp_up[j0:j1]
            next_post_process = post_process[j0:j1]
            next_sell_code = sell_code[j0:j1]
            next_out_width = out_width[j0:j1]

            category_flag = self._calc_category_flag(cat_prev_ok, cat_next_ok[j0:j1])
            width_flag = self._calc_width_flag(
                width,
                width_down,
                width_up,
                next_width,
                next_width_down,
                next_width_up,
                narrow_to_wide_threshold,
                width_change_upper_limit,
            )
            thickness_flag = self._calc_thickness_flag(
                thickness,
                thickness_down,
                thickness_up,
                next_thickness,
                next_thickness_down,
                next_thickness_up,
            )
            temp_flag = self._calc_temp_flag(
                thickness,
                temp,
                temp_down,
                temp_up,
                next_thickness,
                next_temp,
                next_temp_down,
                next_temp_up,
                special_temp_upper_limit,
            )
            same_width_flag = self._calc_same_width_flag(
                width,
                post_process,
                sell_code,
                out_width,
                next_width,
                next_post_process,
                next_sell_code,
                next_out_width,
            )

            connectable_flag = category_flag & width_flag & thickness_flag & temp_flag

            # 过滤对角线
            mask = np.ones((n, b), dtype=bool)
            diag_idx = np.arange(j0, j1)
            mask[diag_idx, diag_idx - j0] = False

            mask_flat = mask.ravel()
            prev_order_no = np.repeat(order_no, b)[mask_flat]
            curr_order_no = np.tile(order_no[j0:j1], n)[mask_flat]

            records.append(
                pd.DataFrame({
                    "prev_order_no": prev_order_no,
                    "curr_order_no": curr_order_no,
                    "category_flag": category_flag.ravel()[mask_flat].astype(int),
                    "width_flag": width_flag.ravel()[mask_flat].astype(int),
                    "thickness_flag": thickness_flag.ravel()[mask_flat].astype(int),
                    "temp_flag": temp_flag.ravel()[mask_flat].astype(int),
                    "same_width_flag": same_width_flag.ravel()[mask_flat].astype(int),
                    "connectable_flag": connectable_flag.ravel()[mask_flat].astype(int),
                })
            )

        i_connectable_data = pd.concat(records, ignore_index=True)
        
        return GeneratorResult(self.table_name, i_connectable_data)
    

class tInfoGenerator(Generator):
    params_defined = [iTables.ZINC_PLAN, iTables.PARAM]
    table_name = tTables.INFO

    def execute(self, i_zinc_plan: Table, i_param: Table) -> GeneratorResult:

        zinc_plan_data = i_zinc_plan.df.copy()
        param_data = i_param.df.copy()
        info_data = zinc_plan_data[["if_outer", 'max_active_weight1', 'max_active_weight2', 'if_outer_first']].copy()
        info_data['cross_removal_upper_limit'] = param_data["cross_removal_upper_limit"]
       

        return GeneratorResult(tTables.INFO, info_data)
        
