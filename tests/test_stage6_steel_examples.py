from __future__ import annotations

from pathlib import Path
import sys

from optagent import BuiltInStrategyPreset, Orchestrator
from optagent.heuristic.sequence_adjacency import greedy_construct_sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from steel.steel_blackbox_sequence import build_program as build_blackbox_program
from steel.steel_dag_sequence import build_program as build_dag_program
from steel.solve_profiles import choose_blackbox_preset_mode
from steel.steel_domain import (
    build_penalty_matrix,
    build_internal_seed,
    decode_sequence_from_selected_edges,
    load_steel_instances,
    selected_edges_from_sequence,
    transition_count,
)


def test_steel_dag_oriented_scoring_matches_blackbox_semantics() -> None:
    instance = load_steel_instances()["toy"]
    sequence = [0, 1, 2, 3, 4]
    blackbox_program, _ = build_blackbox_program(instance)
    dag_program, dag_node_ids = build_dag_program(instance)

    blackbox_score = transition_count(sequence, instance.coils)
    penalty_matrix = dag_node_ids["penalty_matrix"]
    dag_score = sum(penalty_matrix[sequence[index - 1]][sequence[index]] for index in range(1, len(sequence)))

    assert blackbox_score == dag_score == 3
    assert penalty_matrix == build_penalty_matrix(instance.coils)
    assert len(blackbox_program.objective_ids) == 1
    assert len(dag_program.objective_ids) == 1


def test_steel_dag_exact_preset_solves_toy_optimally() -> None:
    instance = load_steel_instances()["toy"]
    dag_program, dag_node_ids = build_dag_program(instance)

    result = Orchestrator().run(dag_program, preset=BuiltInStrategyPreset.SEQUENCE_EXACT)
    selected_edges = [
        tuple(int(part) for part in edge_name.split("->", maxsplit=1))
        for edge_name, node_id in dag_node_ids["edge_node_ids"].items()
        if int(round(float(result.final_solution.variable_values[node_id]))) > 0
    ]
    sequence = decode_sequence_from_selected_edges(
        selected_edges=selected_edges,
        coil_count=dag_node_ids["coil_count"],
        depot_index=dag_node_ids["depot"],
    )

    assert transition_count(sequence, instance.coils) == 3
    assert result.selected_preset_name == "sequence_exact"


def test_steel_seed_builder_finds_valid_toy_sequence() -> None:
    instance = load_steel_instances()["toy"]
    seed = build_internal_seed(instance)
    assert sorted(seed.sequence) == list(range(len(instance.coils)))
    assert seed.objective == 3


def test_steel_internal_seed_hits_bundled_target() -> None:
    instance = load_steel_instances()["bundled"]
    seed = build_internal_seed(instance)

    assert sorted(seed.sequence) == list(range(len(instance.coils)))
    assert seed.source == "internal_seed"
    assert seed.objective <= 20


def test_src_constructive_sequence_hits_bundled_target() -> None:
    instance = load_steel_instances()["bundled"]
    sequence = greedy_construct_sequence(build_penalty_matrix(instance.coils))

    assert sorted(sequence) == list(range(len(instance.coils)))
    assert transition_count(sequence, instance.coils) <= 20


def test_blackbox_preset_policy_uses_three_stage_thresholds() -> None:
    assert choose_blackbox_preset_mode(objective=8) == (
        "fast_polish",
        "internal_constructive_target_reached_fast_polish",
    )
    assert choose_blackbox_preset_mode(objective=14) == (
        "targeted_polish",
        "internal_constructive_midband_targeted_polish",
    )
    assert choose_blackbox_preset_mode(objective=17) == (
        "preset",
        "no_internal_seed_default_preset",
    )


def test_steel_dag_program_can_encode_seed_sequence_as_defaults() -> None:
    instance = load_steel_instances()["toy"]
    sequence = [0, 1, 2, 3, 4]
    program, dag_node_ids = build_dag_program(instance, initial_sequence=sequence)

    selected_edges = [
        tuple(int(part) for part in edge_name.split("->", maxsplit=1))
        for edge_name, node_id in dag_node_ids["edge_node_ids"].items()
        if int(round(float(program.default_state().variable_values[node_id]))) > 0
    ]
    decoded = decode_sequence_from_selected_edges(
        selected_edges=selected_edges,
        coil_count=dag_node_ids["coil_count"],
        depot_index=dag_node_ids["depot"],
    )

    assert decoded == sequence
    assert set(selected_edges) == set(selected_edges_from_sequence(sequence, depot_index=dag_node_ids["depot"]))
