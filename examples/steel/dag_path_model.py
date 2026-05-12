from __future__ import annotations

from typing import Any

from optagent import ModelBuilder
from optagent.heuristic.sequence_adjacency import greedy_construct_sequence

from steel.steel_domain import (
    SteelCoilInstance,
    build_penalty_matrix,
    order_defaults_from_sequence,
    selected_edges_from_sequence,
)


def build_program(instance: SteelCoilInstance, *, initial_sequence: list[int] | None = None) -> tuple[Any, dict[str, Any]]:
    penalty_matrix = build_penalty_matrix(instance.coils)
    effective_sequence = initial_sequence if initial_sequence is not None else greedy_construct_sequence(penalty_matrix)
    builder = ModelBuilder(
        metadata={
            "case": f"steel_dag_sequence_{instance.name}",
            "style": "dag_exact_path",
            "model_style": "dag_path",
            "sequence_path_linear": True,
            "sequence_adjacency_penalty_matrix": penalty_matrix,
            "sequence_break_window": 24,
        }
    )
    coil_count = len(instance.coils)
    depot = coil_count
    nodes = range(coil_count + 1)
    actual_nodes = range(coil_count)
    selected_edges = set(
        selected_edges_from_sequence(effective_sequence, depot_index=depot)
    )
    order_defaults = order_defaults_from_sequence(effective_sequence, coil_count=coil_count, depot_index=depot)

    edges = {
        (i, j): builder.int_var(default=1 if (i, j) in selected_edges else 0, lb=0, ub=1, name=f"x_{i}_{j}")
        for i in nodes
        for j in nodes
        if i != j
    }
    order = {
        node: builder.int_var(default=order_defaults[node], lb=0, ub=coil_count, name=f"u_{node}")
        for node in nodes
    }

    for node in nodes:
        outgoing = [edges[(node, other)] for other in nodes if other != node]
        incoming = [edges[(other, node)] for other in nodes if other != node]
        builder.constraint(builder.sum(*outgoing) == 1, name=f"leave_{node}")
        builder.constraint(builder.sum(*incoming) == 1, name=f"enter_{node}")

    builder.constraint(order[depot] == 0, name="anchor_depot")
    for node in actual_nodes:
        builder.constraint(order[node] >= 1, name=f"lower_u_{node}")
        builder.constraint(order[node] <= coil_count, name=f"upper_u_{node}")

    for left in actual_nodes:
        for right in actual_nodes:
            if left == right:
                continue
            builder.constraint(
                order[left] - order[right] + ((coil_count + 1) * edges[(left, right)]) <= coil_count,
                name=f"mtz_{left}_{right}",
            )

    objective_terms = [
        edges[(left, right)] * penalty_matrix[left][right]
        for left in actual_nodes
        for right in actual_nodes
        if left != right
    ]
    builder.minimize(builder.sum(*objective_terms), name="transition_count")
    return builder.freeze(), {
        "depot": depot,
        "coil_count": coil_count,
        "penalty_matrix": penalty_matrix,
        "edge_node_ids": {f"{left}->{right}": edge.node_id for (left, right), edge in edges.items()},
        "order_node_ids": {str(node): expr.node_id for node, expr in order.items()},
    }


def describe_model_structure(node_ids: dict[str, Any]) -> dict[str, int]:
    edge_count = len(node_ids["edge_node_ids"])
    order_count = len(node_ids["order_node_ids"])
    return {
        "coil_count": int(node_ids["coil_count"]),
        "edge_variable_count": edge_count,
        "order_variable_count": order_count,
        "depot_index": int(node_ids["depot"]),
    }
