from __future__ import annotations

from typing import Any

from optagent import ModelBuilder
from optagent.heuristic.sequence_adjacency import greedy_construct_sequence

from steel.steel_domain import SteelCoilInstance, build_penalty_matrix, transition_count


def build_program(instance: SteelCoilInstance, *, default_sequence: list[int] | None = None) -> tuple[Any, int]:
    penalty_matrix = build_penalty_matrix(instance.coils)
    effective_sequence = default_sequence if default_sequence is not None else greedy_construct_sequence(penalty_matrix)
    builder = ModelBuilder(
        metadata={
            "case": f"steel_transition_sequence_{instance.name}",
            "model_style": "blackbox_sequence",
            "sequence_adjacency_penalty_matrix": penalty_matrix,
            "sequence_break_window": 24,
        }
    )
    sequence = builder.sequence_var(
        size=len(instance.coils),
        default=effective_sequence,
        name="coil_sequence",
    )
    coils = builder.const(instance.coils)
    builder.minimize(
        builder.external_call(transition_count, sequence, coils, name="steel_transition_count"),
        name="transition_count",
    )
    return builder.freeze(), sequence.node_id
