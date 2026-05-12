from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from steel.search_attribution import build_attribution_payload, build_start_sequences, perturb_sequence
from steel.steel_domain import load_steel_instances


def test_build_start_sequences_exposes_identity_constructive_and_random() -> None:
    instance = load_steel_instances()["toy"]
    starts = build_start_sequences(instance, seed=7)

    assert set(starts) == {"identity", "constructive", "random_7"}
    for sequence in starts.values():
        assert sorted(sequence) == list(range(len(instance.coils)))


def test_perturb_sequence_preserves_permutation_and_changes_order() -> None:
    sequence = [0, 1, 2, 3, 4]
    perturbed = perturb_sequence(sequence, swap_count=3, seed=11)

    assert sorted(perturbed) == sequence
    assert perturbed != sequence


def test_search_attribution_payload_contains_ga_and_perturbation_sections() -> None:
    instance = load_steel_instances()["toy"]
    payload = build_attribution_payload(
        instance=instance,
        search_seed=5,
        budget_iterations=24,
        generation_limit=4,
        perturb_swap_counts=(2,),
    )

    routes = {(row["phase"], row["route"]) for row in payload["rows"]}

    assert payload["phase_plan"][1]["phase"] == "phase_2_same_seed_search"
    assert ("same_seed_search", "blackbox_evolutionary") in routes
    assert ("same_seed_search", "blackbox_preset") in routes
    assert ("same_seed_search", "dag_preset") in routes
    assert ("perturbation_recovery", "blackbox_evolutionary") in routes
    assert ("perturbation_recovery", "dag_preset") in routes

    constructive_rows = [
        row
        for row in payload["rows"]
        if row["phase"] == "seed_only" and row["start_policy"] == "constructive"
    ]
    assert constructive_rows
    constructive = constructive_rows[0]
    assert constructive["initial_objective"] == constructive["final_objective"]
    assert constructive["search_changed_sequence"] is False
