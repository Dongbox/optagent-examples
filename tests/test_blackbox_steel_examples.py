from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from blackbox import steel_sequence_external


def test_sequence_external_model_scoring_matches_domain_semantics() -> None:
    instance = steel_sequence_external.load_steel_instances()["toy"]
    model = steel_sequence_external.build_sequence_external_model(instance)

    assert model.default_sequence == list(range(len(instance.coils)))
    assert model.penalty_matrix == steel_sequence_external.build_penalty_matrix(instance.coils)
    assert model.program.metadata["model_style"] == "sequence_external_callback"
    assert len(model.program.objective_ids) == 1
    objective = model.program.graph.nodes[model.program.objective_ids[0]]
    transition = model.program.graph.nodes[objective.inputs[0]]
    assert transition.kind.value == "external_call"


def test_sequence_external_callback_runs_ga_on_toy() -> None:
    instance = steel_sequence_external.load_steel_instances()["toy"]
    payload = steel_sequence_external.solve_sequence_external(
        instance=instance,
        seed=5,
        max_iterations=4,
        population_size=4,
        time_limit_s=5.0,
        trace_limit=4,
    )

    rows = {row["strategy"]: row for row in payload["strategies"]}
    assert payload["modeling"] == "sequence_external_callback"
    assert set(rows) == {"ga"}
    for row in rows.values():
        assert sorted(row["sequence"]) == list(range(len(instance.coils)))
        assert row["objective"] == steel_sequence_external.analyze_sequence(row["sequence"], instance.coils)["transition_count"]
        assert row["metadata"]["strategy"] == row["strategy"]
