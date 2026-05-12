# 导入通用预处理
from unicodedata import category
from aps.orm import ObjectColumn, FloatColumn, IntColumn, ReferenceKey
from aps.preprocess.tables import tTableBase, tTables, tProcess, tMachineRollChange


class tTables(tTables):
    CONNECTABLES = "t_connectables"
    INFO = "t_info"



# 声明已有表扩展字段
class tProcessCustom(tProcess):
    post_process = IntColumn()
    label_campaign = ObjectColumn()
    is_outer = IntColumn()
    surface_grade = IntColumn()
    is_thin = IntColumn()
    is_simple = IntColumn()
    is_outer_transition = IntColumn()
    out_width = FloatColumn()
    width_up_jump = FloatColumn()
    width_down_jump = FloatColumn()
    temp_up_jump = FloatColumn()
    temp_down_jump = FloatColumn()
    grade = ObjectColumn()
    category = ObjectColumn()
    zinc_layer = ObjectColumn()
    sell_code = ObjectColumn()
    grade_category = ObjectColumn()
    steel_type = ObjectColumn()
    zinc_thick = FloatColumn()
    grinding_class = IntColumn()
    left_mat_priority_outer = IntColumn()

   


class tConnectables(tTableBase):
    class Meta:
        table_name = tTables.CONNECTABLES

    prev_order_id = IntColumn(ref_key=ReferenceKey(tTables.ORDER, "order_no", "prev_order_no"))
    curr_order_id = IntColumn(ref_key=ReferenceKey(tTables.ORDER, "order_no", "curr_order_no"))
    category_flag = IntColumn()
    width_flag = IntColumn()
    thickness_flag = IntColumn()
    temp_flag = IntColumn()
    same_width_flag = IntColumn()
    connectable_flag = IntColumn()


class tInfo(tTableBase):
    class Meta:
        table_name = tTables.INFO

    if_outer = IntColumn()
    max_active_weight1 = FloatColumn()
    max_active_weight2 = FloatColumn()
    if_outer_first = IntColumn()
    cross_removal_upper_limit = IntColumn()



# class tCampaignConfig(tTableBase):
#     class Meta:
#         table_name = tTables.CAMPAIGN_CONFIG

#     campaign_level_name = ObjectColumn()
#     hard_or_flexible = IntColumn()

# class tMachineRollChangeCustom(tMachineRollChange):
#     cum_weight_up = IntColumn()
#     cum_weight_down = IntColumn()
