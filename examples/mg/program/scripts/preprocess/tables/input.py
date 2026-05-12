# 导入通用预处理
from aps.preprocess.tables import (
    iProcess,
    iLeftedMat,
    iTables,
    iScheduledOrders,
    iTableBase,
)
from aps.orm import ObjectColumn, FloatColumn, IntColumn


class iTables(iTables):
    WIDTH_LIMIT = "i_width_limit"
    WIDTH_LIMIT_2 = "i_width_limit2"
    PARAM = "i_param"
    CATEGORY_LIST = "i_category_list"
    OUTER_PANELS_TRANSITION = "i_outer_panels_transition"
    CATEGORY_CONNECTION = "i_category_connection"
    THICK_LIMIT = "i_thick_limit"
    ZINC_PLAN = "i_zinc_plan"



class iScheduledOrdersCustom(iScheduledOrders):
    post_process = IntColumn()
    label_campaign = ObjectColumn()
    surface_grade = IntColumn()
    is_outer_transition = IntColumn()
    out_width = FloatColumn()
    grade = ObjectColumn()
    category = ObjectColumn()
    zinc_layer = ObjectColumn()
    sell_code = ObjectColumn()
    grade_category = ObjectColumn()
    steel_type = ObjectColumn()


class iProcessCustom(iProcess):
    post_process = IntColumn()
    label_campaign = ObjectColumn()
    is_outer = IntColumn()
    surface_grade = IntColumn()
    is_outer_transition = IntColumn()
    out_width = FloatColumn()
    grade = ObjectColumn()
    category = ObjectColumn()
    zinc_layer = ObjectColumn()
    sell_code = ObjectColumn()
    grade_category = ObjectColumn()
    steel_type = ObjectColumn()
    zinc_thick = FloatColumn()



class iLeftedMatCustom(iLeftedMat):
    post_process = IntColumn()
    label_campaign = ObjectColumn()
    surface_grade = IntColumn()
    is_outer_transition = IntColumn()
    left_mat_priority_outer = IntColumn()
    out_width = FloatColumn()
    grade = ObjectColumn()
    category = ObjectColumn()
    zinc_layer = ObjectColumn()
    sell_code = ObjectColumn()
    grade_category = ObjectColumn()
    steel_type = ObjectColumn()
    zinc_thick = FloatColumn()


class iWidthLimit(iTableBase):
    class Meta:
        table_name = iTables.WIDTH_LIMIT

    entry_thickness_lower_bound = FloatColumn()
    entry_thickness_upper_bound = FloatColumn()
    is_outer_or_high_surface = IntColumn()
    width_change_limit = FloatColumn()


class iWidthLimit2(iTableBase):
    class Meta:
        table_name = iTables.WIDTH_LIMIT_2

    narrow_to_wide_threshold = FloatColumn()
    width_change_upper_limit = FloatColumn()


class iParam(iTableBase):
    class Meta:
        table_name = iTables.PARAM

    annealing_temp_upper_limit = FloatColumn()
    thin_material_threshold = FloatColumn()
    roll_change_width_upper_limit = FloatColumn()
    cross_removal_upper_limit = IntColumn()
    spetial_temp_upper_limit = FloatColumn()


class iCategoryList(iTableBase):
    class Meta:
        table_name = iTables.CATEGORY_LIST

    transition_grade = ObjectColumn()
    grinding_cat = ObjectColumn()




class iOuterPanelsTransition(iTableBase):
    class Meta:
        table_name = iTables.OUTER_PANELS_TRANSITION

    exit_thickness_lower_limit = FloatColumn()
    exit_thickness_upper_limit = FloatColumn()
    width_lower_limit = FloatColumn()
    width_upper_limit = FloatColumn()


class iCategoryLimit(iTableBase):
    class Meta:
        table_name = iTables.CATEGORY_CONNECTION

    prev_grade_category = ObjectColumn()
    next_grade_category = ObjectColumn()


class iThickLimit(iTableBase):
    class Meta:
        table_name = iTables.THICK_LIMIT

    thickness_lower_bound = FloatColumn()
    thickness_upper_bound = FloatColumn()
    thickness_tolerance = FloatColumn()
    is_cq_dq_ddq_eddq_non_outer = IntColumn()
    is_cq_dq_ddq = IntColumn()
    is_special_cat = IntColumn()



class iZincPlan(iTableBase):
    class Meta:
        table_name = iTables.ZINC_PLAN
    if_outer = IntColumn()
    max_active_weight1 = FloatColumn()
    max_active_weight2 = FloatColumn()
    if_outer_first = IntColumn()

