from __future__ import annotations

import json
from pathlib import Path


MG_ROOT = Path(__file__).resolve().parents[1] / "examples" / "mg"
COLD_ROLLING_ROOT = Path(__file__).resolve().parents[1] / "examples" / "cold_rolling"


def _notebook_text(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["nbformat"] == 4
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in payload.get("cells", [])
    )


def test_hot_dip_galvanizing_notebook_package_is_present() -> None:
    notebooks = [
        MG_ROOT / "README.ipynb",
        MG_ROOT / "src" / "hot_dip_galvanizing_model.ipynb",
    ]

    for notebook in notebooks:
        assert notebook.exists(), notebook

    assert not (MG_ROOT / "src" / "data").exists()


def test_hot_dip_galvanizing_notebooks_use_business_language() -> None:
    readme_text = _notebook_text(MG_ROOT / "README.ipynb")
    modeling_text = _notebook_text(MG_ROOT / "src" / "hot_dip_galvanizing_model.ipynb")

    assert "热镀锌" in readme_text
    assert "冷轧" in readme_text
    assert "热轧" in readme_text
    assert "业务痛点" in readme_text
    assert "求解器能做到什么" in readme_text
    assert "OptAgent 能做得更好的地方" in readme_text
    assert "锌层 campaign" in readme_text
    assert "退火温度跳变" in readme_text
    assert "外板质量窗口" in readme_text
    assert "订单表、材料表、机组表和初始计划表" in readme_text
    assert "锌层" in modeling_text
    assert "退火温度" in modeling_text
    assert "sequence_var" in modeling_text
    assert "external_call" in modeling_text
    assert "order_table = [" in modeling_text
    assert "material_table = [" in modeling_text
    assert "line_table = [" in modeling_text
    assert "incumbent_plan_table = [" in modeling_text
    assert "import pandas as pd" in modeling_text
    assert "pd.DataFrame(line_table)" in modeling_text
    assert "pd.DataFrame(material_table)" in modeling_text
    assert "pd.DataFrame(order_table)" in modeling_text
    assert "model_input_df" in modeling_text
    assert "SQLite" in readme_text


def test_cold_rolling_notebooks_use_business_language() -> None:
    notebooks = [
        COLD_ROLLING_ROOT / "README.ipynb",
        COLD_ROLLING_ROOT / "src" / "cold_rolling_model.ipynb",
    ]

    for notebook in notebooks:
        assert notebook.exists(), notebook

    readme_text = _notebook_text(COLD_ROLLING_ROOT / "README.ipynb")
    modeling_text = _notebook_text(COLD_ROLLING_ROOT / "src" / "cold_rolling_model.ipynb")

    assert "冷轧" in readme_text
    assert "通用冷轧" in readme_text
    assert "业务需求" in readme_text
    assert "求解器能做到什么" in readme_text
    assert "OptAgent 能做得更好的地方" in readme_text
    assert "不绑定某一条实际机组" in readme_text
    assert "厚度和压下率跳变" in readme_text
    assert "表面质量窗口" in readme_text
    assert "订单表、材料表和产能类型表" in readme_text
    assert "due_position_risk" in readme_text
    assert "需求声明位置对照" in readme_text
    assert "完整代码示例" in readme_text
    assert "入口厚度" in modeling_text
    assert "目标厚度" in modeling_text
    assert "压下率" in modeling_text
    assert "surface_grade" in modeling_text
    assert "oiling_route" in modeling_text
    assert "due_priority" in modeling_text
    assert "target_position" in modeling_text
    assert "due_bucket_spread" in modeling_text
    assert "due_position_risk" in modeling_text
    assert "requirement_mapping" in modeling_text
    assert "business_requirement" in modeling_text
    assert "declared_in_table" in modeling_text
    assert "交期压力和工艺平稳性相互冲突" in modeling_text
    assert "sequence_var" in modeling_text
    assert "external_call" in modeling_text
    assert "order_table = [" in modeling_text
    assert "material_table = [" in modeling_text
    assert "capacity_table = [" in modeling_text
    assert "baseline_sequence" in modeling_text
    assert "完整代码示例" in modeling_text
    assert "class DemoCoil" in modeling_text
    assert "demo_sequence_cost" in modeling_text
    assert "incumbent_plan_table" not in modeling_text
    assert "初始计划表" not in modeling_text
    assert "pain_point_mapping" not in modeling_text
    assert "痛点" not in readme_text
    assert "痛点" not in modeling_text
    assert "import pandas as pd" in modeling_text
    assert "pd.DataFrame(capacity_table)" in modeling_text
    assert "pd.DataFrame(material_table)" in modeling_text
    assert "pd.DataFrame(order_table)" in modeling_text
    assert "model_input_df" in modeling_text
