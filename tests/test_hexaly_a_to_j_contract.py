from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import optagent
from optagent.external import HxExternalArgumentValues


EXAMPLES = Path(__file__).parents[1] / "examples/hexaly"
NOTEBOOKS = tuple(sorted(EXAMPLES.glob("[a-j]*/*.ipynb")))


class _ModelEvaluated(Exception):
    pass


def _smallest_instance(notebook: Path) -> Path | None:
    directory = notebook.parent / "instances"
    if not directory.is_dir():
        return None
    candidates = [path for path in directory.iterdir() if path.is_file() and not path.name.startswith(".")]
    return min(candidates, key=lambda path: (path.stat().st_size, path.name), default=None)


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.parent.name)
def test_a_to_j_example_model_reaches_cpp_initial_evaluator(
    notebook: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _optagent_kernel import _evaluate_initial_model

    def evaluate(model: Any, **_kwargs: Any) -> None:
        external_functions = {
            name: {
                "kind": contract.kind,
                "function": lambda values, function=contract.function: function(HxExternalArgumentValues(values)),
            }
            for name, contract in model.external_functions.items()
        }
        result = _evaluate_initial_model(model.to_bytes(), external_functions)
        assert result["expression_count"] > 0
        assert result["unsupported_undefined_count"] == 0
        if notebook.parent.name == "hosaki_function":
            assert result["external_call_count"] == 1
        raise _ModelEvaluated

    monkeypatch.setattr(optagent, "solve", evaluate)
    namespace: dict[str, Any] = {"__name__": "notebook_contract"}
    document = json.loads(notebook.read_text(encoding="utf-8"))

    try:
        for cell in document["cells"]:
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if "INSTANCE_DIR" in source:
                continue
            exec(compile(source, str(notebook), "exec"), namespace)

        instance = _smallest_instance(notebook)
        arguments = (instance,) if instance is not None else ()
        namespace["main"](*arguments, time_limit=0.001)
    except _ModelEvaluated:
        return

    pytest.fail("example main() returned without sending its model through optagent.solve")
