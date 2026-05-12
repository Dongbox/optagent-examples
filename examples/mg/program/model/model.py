from __future__ import annotations

"""Build the OptAgent program for the MG model phase.

The migrated MG model is intentionally kept as a sequence blackbox: OptAgent
owns sequence exploration, while MG rule semantics stay in `rules.py`. This
file only declares the optimization variable, attaches useful sequence-edge
metadata, and wires the blackbox scorer into the objective.
"""

from dataclasses import dataclass
from typing import Any

from optagent import ModelBuilder
from optagent.heuristic.sequence_adjacency import greedy_construct_sequence

from .rules import _connectable, build_penalty_matrix, score_sequence_external
from examples.mg.program.scripts.preprocess.data import MGCase


STRUCTURED_EDGE_RULES = (
    "MGDiscontinuable",
    "MGSmooth",
    "MGChangeRoller",
    "MGHardCamp",
)
STATEFUL_BLACKBOX_RULES = (
    "MGLeftMat",
    "MGOuterSandwich",
    "MGThinCamp",
    "MGPostProcessCamp",
    "MGGrindingBeforeOuter",
)


def _structured_edge_total(case: MGCase, prev_index: int, curr_index: int) -> tuple[float, dict[str, Any]]:
    """Return DAG-visible adjacent-edge costs used for diagnostics/metadata.

    The authoritative objective remains the blackbox scorer because several MG
    rules depend on active-prefix and multi-edge state. These edge costs expose
    the stable adjacent-pair subset for analysis and future exact lowering.
    """

    prev = case.tasks[prev_index]
    curr = case.tasks[curr_index]
    info = _connectable(case, prev, curr)
    width_delta = prev.width - curr.width
    roller_flag = prev.width < curr.width and info.same_width_flag == 0
    if info.connectable_flag:
        discontinuable_cost = 0.0
    elif info.temp_flag == 0 and info.width_flag and info.thickness_flag and info.category_flag:
        discontinuable_cost = case.rule_weights.discontinuable_temp
    else:
        discontinuable_cost = case.rule_weights.discontinuable

    smooth_width_cost = (
        width_delta * case.rule_weights.smooth_width
        if roller_flag
        else abs(width_delta) * case.rule_weights.smooth_width
    )
    smooth_thickness_cost = abs(prev.thickness - curr.thickness) * case.rule_weights.smooth_thickness
    smooth_temp_cost = abs(prev.temp - curr.temp) * case.rule_weights.smooth_temp
    change_roller_cost = case.rule_weights.change_roller if roller_flag else 0.0
    simple_risk_cost = case.rule_weights.change_roller_simple if roller_flag and curr.is_simple == 0 else 0.0
    hard_camp_cost = case.rule_weights.hard_camp if curr.zinc_layer and prev.zinc_layer and curr.zinc_layer != prev.zinc_layer else 0.0
    total = discontinuable_cost + smooth_width_cost + smooth_thickness_cost + smooth_temp_cost + change_roller_cost + simple_risk_cost + hard_camp_cost
    return total, {
        "prev_index": prev.index,
        "curr_index": curr.index,
        "prev_order_id": prev.order_id,
        "curr_order_id": curr.order_id,
        "connectable": int(info.connectable_flag),
        "same_width": int(info.same_width_flag),
        "category_flag": int(info.category_flag),
        "width_flag": int(info.width_flag),
        "thickness_flag": int(info.thickness_flag),
        "temp_flag": int(info.temp_flag),
        "costs": {
            "MGDiscontinuable": round(float(discontinuable_cost), 6),
            "MGSmooth.width": round(float(smooth_width_cost), 6),
            "MGSmooth.thickness": round(float(smooth_thickness_cost), 6),
            "MGSmooth.temp": round(float(smooth_temp_cost), 6),
            "MGChangeRoller": round(float(change_roller_cost), 6),
            "MGChangeRoller.simple_risk": round(float(simple_risk_cost), 6),
            "MGHardCamp": round(float(hard_camp_cost), 6),
            "structured_edge_total": round(float(total), 6),
        },
    }


def build_structured_edges(case: MGCase) -> list[list[dict[str, Any]]]:
    """Build all pairwise edge metadata for the sequence variable.

    OptAgent currently still optimizes the authoritative blackbox objective.
    The matrix is kept in program metadata so reports, explainability tooling,
    and future exact/path lowerings can inspect the stable adjacent-pair subset.
    """

    matrix: list[list[dict[str, Any]]] = []
    for prev in case.tasks:
        row: list[dict[str, Any]] = []
        for curr in case.tasks:
            if prev.index == curr.index:
                row.append(
                    {
                        "prev_index": prev.index,
                        "curr_index": curr.index,
                        "disabled": True,
                        "costs": {"structured_edge_total": 0.0},
                    }
                )
                continue
            _, edge = _structured_edge_total(case, prev.index, curr.index)
            row.append(edge)
        matrix.append(row)
    return matrix


def structured_edge_cost_matrix(case: MGCase) -> list[list[float]]:
    """Return the numeric edge-cost view consumed by sequence heuristics."""

    return [
        [float(edge["costs"]["structured_edge_total"]) for edge in row]
        for row in build_structured_edges(case)
    ]


@dataclass
class BuiltMGProgram:
    program: Any
    sequence_node_id: int
    metadata: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            **self.metadata,
            "variable_count": len(self.program.variable_ids),
            "constraint_count": len(self.program.constraint_ids),
            "objective_count": len(self.program.objective_ids),
        }


def build_mg_program(case: MGCase, *, use_constructive_default: bool = False) -> BuiltMGProgram:
    """Build the OptAgent sequence model that replaces the APS GA model phase."""

    penalty_matrix = build_penalty_matrix(case)
    structured_edges = build_structured_edges(case)
    # Production runs normally start from APS/preprocess output in
    # `case.default_sequence`. The constructive default is kept for migration
    # experiments where there is no trustworthy warm start.
    default_sequence = (
        greedy_construct_sequence(penalty_matrix)
        if use_constructive_default
        else list(case.default_sequence)
    )
    builder = ModelBuilder(
        metadata={
            "problem_family": "mg",
            "model_style": "blackbox_sequence",
            "machine_no": case.machine_no,
            "task_count": len(case.tasks),
            "sequence_adjacency_penalty_matrix": penalty_matrix,
            "sequence_structured_edge_cost_matrix": structured_edge_cost_matrix(case),
            "sequence_structured_edges": structured_edges,
            "structured_edge_rules": list(STRUCTURED_EDGE_RULES),
            "stateful_blackbox_rules": list(STATEFUL_BLACKBOX_RULES),
            "sequence_path_linear": False,
            "structured_model_status": "edge_metadata_plus_blackbox_objective",
            "sequence_break_window": 24,
        },
        solve_config={
            "heuristic_time_limit_seconds": 5.0,
            "heuristic_max_candidate_moves": 64,
            "heuristic_max_scalar_variables": 0,
        },
    )
    sequence = builder.sequence_var(
        size=len(case.tasks),
        default=default_sequence,
        name="mg_order_sequence",
    )
    case_const = builder.const(case)
    # The sequence variable is passed into an external scorer so every candidate
    # evaluated by OptAgent is scored with the latest sequence value.
    builder.minimize(
        builder.external_call(
            score_sequence_external,
            sequence,
            case_const,
            name="mg_rule_score",
            cache=False,
        ),
        name="mg_rule_cost",
    )
    program = builder.freeze()
    return BuiltMGProgram(
        program=program,
        sequence_node_id=sequence.node_id,
        metadata={
            "task_count": len(case.tasks),
            "default_sequence_head": default_sequence[:20],
            "constructive_default": use_constructive_default,
            "structured_edge_rule_count": len(STRUCTURED_EDGE_RULES),
            "stateful_blackbox_rule_count": len(STATEFUL_BLACKBOX_RULES),
        },
    )
