from pandas import DataFrame

from aps.preprocess import Validator
from aps.preprocess.tables import Table

from .tables import iTables


class iProcessGradeCatVaild(Validator):
    """验证任务表中的grade_category列是否存在空值"""
    params_defined = [iTables.PROCESS]
    table_name = "任务表"

    def execute(self, i_process: Table) -> DataFrame:
        
        i_process_data = i_process.df.copy()
        self.is_column_empty(i_process_data, "grade_category")

        return self.to_dataframe()
