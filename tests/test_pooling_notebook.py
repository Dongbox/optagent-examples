from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

NOTEBOOK = Path(__file__).parents[1] / "examples/nonlinear/pooling_problem/pooling_problem.ipynb"


@pytest.mark.parametrize("direct", [True, False])
def test_zero_capacity_arcs_preserve_the_profit_and_constraints(direct) -> None:
    implementation = next(
        "".join(cell["source"])
        for cell in json.loads(NOTEBOOK.read_text())["cells"]
        if cell["cell_type"] == "code" and "def main(" in "".join(cell["source"])
    )
    namespace = {}
    exec(compile(implementation, str(NOTEBOOK), "exec"), namespace)
    data = SimpleNamespace(
        nbComponents=1,
        nbProducts=1,
        nbPools=1,
        nbAttributes=1,
        upperBoundComponentToProduct=[[10 if direct else 0]],
        upperBoundFractionComponentToPool=[[1]],
        upperBoundPoolToProduct=[[0 if direct else 10]],
        componentSupplies=[10],
        poolCapacities=[10],
        productCapacities=[10],
        demand=[0],
        componentQuality=[[1]],
        minTolerance=[[1]],
        maxTolerance=[[1]],
        costComponentToProduct=[[0]],
        costComponentToPool=[[0]],
        costPoolToProduct=[[0]],
        productPrices=[5],
        componentPrices=[1],
    )
    namespace["PoolingInstance"] = lambda _: data
    result = namespace["main"]("unused", time_limit=1)
    assert result.feasible
    assert result.objectives[0] == pytest.approx(40)
