from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from steel import steel_dag_path, steel_sequence_external


def test_sequence_graph_ir_model_scoring_matches_domain_semantics() -> None:
    instance = steel_sequence_external.load_steel_instances()["toy"]
    model = steel_sequence_external.build_sequence_external_model(instance)

    assert model.default_sequence == list(range(len(instance.coils)))
    assert model.penalty_matrix == steel_sequence_external.build_penalty_matrix(instance.coils)
    assert "sequence_adjacency_penalty_matrix" not in model.program.metadata
    assert len(model.program.objective_ids) == 1
    objective = model.program.graph.nodes[model.program.objective_ids[0]]
    transition = model.program.graph.nodes[objective.inputs[0]]
    assert transition.kind.value == "sequence_transition_sum"


def test_sequence_graph_ir_runs_ga_and_alns_on_toy() -> None:
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
    assert payload["modeling"] == "sequence_graph_ir_objective"
    assert set(rows) == {"ga", "alns"}
    for row in rows.values():
        assert sorted(row["sequence"]) == list(range(len(instance.coils)))
        assert row["objective"] == steel_sequence_external.analyze_sequence(row["sequence"], instance.coils)["transition_count"]
        assert row["metadata"]["strategy"] == row["strategy"]


def test_dag_path_model_encodes_default_path() -> None:
    instance = steel_dag_path.load_steel_instances()["toy"]
    model = steel_dag_path.build_dag_path_model(instance)
    selected_edges = steel_dag_path.selected_edges_from_sequence(
        model.default_sequence,
        depot_index=model.depot_index,
    )
    decoded = steel_dag_path.decode_sequence_from_edges(
        selected_edges=selected_edges,
        coil_count=model.coil_count,
        depot_index=model.depot_index,
    )

    assert decoded == model.default_sequence == list(range(len(instance.coils)))
    assert "sequence_adjacency_penalty_matrix" not in model.program.metadata
    assert len(model.edge_node_ids) == model.coil_count * (model.coil_count + 1)
    assert len(model.program.objective_ids) == 1


def test_dag_path_runs_ga_and_alns_on_toy() -> None:
    instance = steel_dag_path.load_steel_instances()["toy"]
    payload = steel_dag_path.solve_dag_path(
        instance=instance,
        seed=5,
        max_iterations=4,
        population_size=4,
        time_limit_s=5.0,
        trace_limit=4,
    )

    rows = {row["strategy"]: row for row in payload["strategies"]}
    assert payload["modeling"] == "dag_path"
    assert set(rows) == {"ga", "alns"}
    for row in rows.values():
        assert sorted(row["sequence"]) == list(range(len(instance.coils)))
        assert row["objective"] == steel_dag_path.analyze_sequence(row["sequence"], instance.coils)["transition_count"]
        assert row["metadata"]["strategy"] == row["strategy"]
