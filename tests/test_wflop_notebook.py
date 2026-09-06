from __future__ import annotations

import json
from pathlib import Path

import pytest

from optagent import OptModel

NOTEBOOK = (
    Path(__file__).parents[1]
    / "examples/network_design/wind_farm_layout_optimization_problem_wflop"
    / "wind_farm_layout_optimization_problem_wflop.ipynb"
)


@pytest.mark.parametrize("zero_wake", [False, True])
def test_sparse_wake_aggregate_matches_expanded_energy(monkeypatch, zero_wake) -> None:
    implementation = next(
        "".join(cell["source"])
        for cell in json.loads(NOTEBOOK.read_text())["cells"]
        if cell["cell_type"] == "code" and "def main(" in "".join(cell["source"])
    )
    namespace = {}
    exec(compile(implementation, str(NOTEBOOK), "exec"), namespace)
    data = {
        "radius": 1,
        "disc_delta": 1,
        "min_distance": 0,
        "nb_turbines": 2,
        "degrees": [0, 90],
        "dyn_coeff": 1,
        "turbine_diameter": 1,
        "thrust_coeff": 0.5,
        "inflow_speed": 10,
        "min_speed": 0,
        "optimal_speed": 10,
        "max_speed": 20,
        "turbine_nominal_power": 100,
        "probabilities": [0.4, 0.6],
    }
    namespace["read_data"] = lambda _: data
    namespace["build_discretization"] = lambda *args: ([0, 1, 2], [0, 0, 0])
    namespace["wake_loss"] = (
        lambda a, b, angle, *args: 0
        if zero_wake or a == b or (a[0] == 1 and angle == 0)
        else 0.01 * (1 + b[0] + angle / 90)
    )
    original_bool = OptModel.bool
    selected = [True, False, True]

    def fixed_bool(self, *args, **kwargs):
        value = original_bool(self, *args, default=selected[int(kwargs["name"].split("_")[-1])], **kwargs)
        self.constraint(value == selected[int(kwargs["name"].split("_")[-1])])
        return value

    monkeypatch.setattr(OptModel, "bool", fixed_bool)
    result = namespace["main"]("unused", time_limit=1)
    expected = 0.0
    for location in range(3):
        for angle, probability in zip(data["degrees"], data["probabilities"]):
            loss = sum(
                (0.01 * (1 + other + angle / 90)) ** 2
                for other in range(3)
                if not zero_wake and not (location == 1 and angle == 0) and other != location and selected[other]
            )
            speed = 10 * (selected[location] - loss**0.5)
            power = 100 * (speed / 10) ** 3 if 0 <= speed < 10 else 100 if 10 <= speed < 20 else 0
            expected += 8760 * probability * power
    assert result.feasible
    assert result.objectives[0] == pytest.approx(expected)
