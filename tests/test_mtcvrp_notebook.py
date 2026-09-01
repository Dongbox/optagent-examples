from __future__ import annotations

import json
from pathlib import Path
from typing import Any


NOTEBOOK = (
    Path(__file__).parents[1]
    / "examples/routing/multi_trip_capacitated_vehicle_routing_problem_mtcvrp"
    / "multi_trip_capacitated_vehicle_routing_problem_mtcvrp.ipynb"
)


def test_mtcvrp_reader_accepts_path_instance() -> None:
    document = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    implementation = next(
        "".join(cell["source"])
        for cell in document["cells"]
        if cell.get("cell_type") == "code"
        and "def read_input_multi_trip_vrp(filename):" in "".join(cell.get("source", []))
    )
    namespace: dict[str, Any] = {}
    exec(compile(implementation, str(NOTEBOOK), "exec"), namespace)

    instance = NOTEBOOK.parent / "instances/coordChrist100.dat"
    parsed = namespace["read_input_multi_trip_vrp"](instance)

    assert parsed[0] == 100
