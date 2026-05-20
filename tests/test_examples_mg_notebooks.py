from __future__ import annotations

import json
from pathlib import Path


MG_ROOT = Path(__file__).resolve().parents[1] / "examples" / "mg"


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
