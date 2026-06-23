from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from optagent import AlnsConfig, GaConfig, ModelBuilder, solve


DATA_PATH = Path(__file__).with_name("data") / "steel_coils.json"
EPS = 1e-6


@dataclass(frozen=True)
class SteelCoilInstance:
    name: str
    coils: list[list[float]]


@dataclass(frozen=True)
class DagPathModel:
    program: Any
    depot_index: int
    coil_count: int
    edge_node_ids: dict[tuple[int, int], int]
    default_sequence: list[int]
    penalty_matrix: list[list[int]]


def load_steel_instances() -> dict[str, SteelCoilInstance]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    bundled = payload["bundled"]
    return {
        "toy": SteelCoilInstance(name="toy_5", coils=payload["toy"]),
        "bundled_head40": SteelCoilInstance(name="bundled_head40", coils=bundled[:40]),
        "bundled": SteelCoilInstance(name=f"bundled_{len(bundled)}", coils=bundled),
    }


def can_weld(left: list[float], right: list[float]) -> bool:
    left_thick, left_thick_up, left_thick_down, left_width, left_width_down, left_width_up, left_temp, left_temp_up, left_temp_down = left
    right_thick, right_thick_up, right_thick_down, right_width, right_width_down, right_width_up, right_temp, right_temp_up, right_temp_down = right
    return (
        right_thick_down - EPS <= left_thick <= right_thick_up + EPS
        and right_width_down - EPS <= left_width <= right_width_up + EPS
        and right_temp_down - EPS <= left_temp <= right_temp_up + EPS
        and left_thick_down - EPS <= right_thick <= left_thick_up + EPS
        and left_width_down - EPS <= right_width <= left_width_up + EPS
        and left_temp_down - EPS <= right_temp <= left_temp_up + EPS
    )


def build_penalty_matrix(coils: list[list[float]]) -> list[list[int]]:
    return [
        [0 if left == right or can_weld(coils[left], coils[right]) else 1 for right in range(len(coils))]
        for left in range(len(coils))
    ]


def transition_count(sequence: list[int], coils: list[list[float]]) -> int:
    return sum(0 if can_weld(coils[sequence[index - 1]], coils[sequence[index]]) else 1 for index in range(1, len(sequence)))


def analyze_sequence(sequence: list[int], coils: list[list[float]]) -> dict[str, Any]:
    penalties = [0 if can_weld(coils[sequence[index - 1]], coils[sequence[index]]) else 1 for index in range(1, len(sequence))]
    breaks = [
        {"prev": sequence[index - 1], "curr": sequence[index], "position": index}
        for index in range(1, len(sequence))
        if penalties[index - 1] > 0
    ]
    pair_count = max(0, len(sequence) - 1)
    direct_weld_count = pair_count - len(breaks)
    return {
        "transition_count": len(breaks),
        "break_positions": [item["position"] for item in breaks],
        "edge_penalties": penalties,
        "direct_weld_count": direct_weld_count,
        "pair_count": pair_count,
        "direct_weld_ratio": direct_weld_count / pair_count if pair_count else 1.0,
        "first_breaks": breaks[:10],
    }


def selected_edges_from_sequence(sequence: list[int], *, depot_index: int) -> list[tuple[int, int]]:
    if not sequence:
        return [(depot_index, depot_index)]
    edges = [(depot_index, sequence[0])]
    edges.extend((sequence[index - 1], sequence[index]) for index in range(1, len(sequence)))
    edges.append((sequence[-1], depot_index))
    return edges


def order_defaults_from_sequence(sequence: list[int], *, coil_count: int, depot_index: int) -> dict[int, int]:
    order = {depot_index: 0}
    for index, coil_id in enumerate(sequence, start=1):
        order[coil_id] = index
    for node in range(coil_count):
        order.setdefault(node, min(coil_count, node + 1))
    return order


def decode_sequence_from_edges(*, selected_edges: list[tuple[int, int]], coil_count: int, depot_index: int) -> list[int]:
    successor = {left: right for left, right in selected_edges}
    sequence: list[int] = []
    current = successor[depot_index]
    visited: set[int] = set()
    while current != depot_index:
        if current in visited:
            raise ValueError("selected edges contain a cycle before returning to depot")
        visited.add(current)
        sequence.append(current)
        current = successor[current]
    if len(sequence) != coil_count:
        raise ValueError(f"decoded path length {len(sequence)} does not match expected coil_count={coil_count}")
    return sequence


def build_dag_path_model(instance: SteelCoilInstance) -> DagPathModel:
    penalty_matrix = build_penalty_matrix(instance.coils)
    default_sequence = list(range(len(instance.coils)))
    builder = ModelBuilder(
        metadata={
            "case": f"steel_dag_path_{instance.name}",
            "model_style": "dag_path",
            "sequence_path_linear": True,
            "sequence_break_window": 24,
        }
    )
    coil_count = len(instance.coils)
    depot = coil_count
    nodes = range(coil_count + 1)
    actual_nodes = range(coil_count)
    default_edges = set(selected_edges_from_sequence(default_sequence, depot_index=depot))
    order_defaults = order_defaults_from_sequence(default_sequence, coil_count=coil_count, depot_index=depot)

    edges = {
        (left, right): builder.int_var(
            default=1 if (left, right) in default_edges else 0,
            lb=0,
            ub=1,
            name=f"x_{left}_{right}",
        )
        for left in nodes
        for right in nodes
        if left != right
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
    return DagPathModel(
        program=builder.freeze(),
        depot_index=depot,
        coil_count=coil_count,
        edge_node_ids={edge: expr.node_id for edge, expr in edges.items()},
        default_sequence=default_sequence,
        penalty_matrix=penalty_matrix,
    )


def selected_edges_from_solution(edge_node_ids: dict[tuple[int, int], int], variable_values: dict[int, Any]) -> list[tuple[int, int]]:
    return [
        edge
        for edge, node_id in edge_node_ids.items()
        if int(round(float(variable_values.get(node_id, 0)))) > 0
    ]


def metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "strategy",
        "execution_graph_strategy",
        "termination_reason",
        "iterations",
        "attempted_moves",
        "accepted_moves",
        "domain_best_sequence_penalty",
        "ga_generation_count",
        "ga_mutation_portfolio",
        "alns_iterations",
        "alns_candidates_evaluated",
        "alns_candidates_accepted",
        "alns_acceptance_model",
    )
    return {key: metadata[key] for key in keys if key in metadata}


def summarize_solution(*, model: DagPathModel, instance: SteelCoilInstance, solution: Any, strategy_name: str, elapsed_seconds: float) -> dict[str, Any]:
    selected_edges = selected_edges_from_solution(model.edge_node_ids, solution.variable_values)
    sequence = decode_sequence_from_edges(
        selected_edges=selected_edges,
        coil_count=model.coil_count,
        depot_index=model.depot_index,
    )
    diagnostics = analyze_sequence(sequence, instance.coils)
    return {
        "strategy": strategy_name,
        "solver_name": solution.solver_name,
        "status": solution.status.value,
        "feasible": solution.feasible,
        "elapsed_seconds": elapsed_seconds,
        "sequence_head": sequence[:20],
        "sequence": sequence,
        "selected_edges_head": selected_edges[:20],
        "objective": int(diagnostics["transition_count"]),
        "direct_weld_ratio": float(diagnostics["direct_weld_ratio"]),
        "diagnostics": diagnostics,
        "metadata": metadata_summary(solution.metadata),
    }


def solve_dag_path(
    *,
    instance: SteelCoilInstance,
    seed: int = 11,
    max_iterations: int = 80,
    population_size: int = 8,
    time_limit_s: float = 30.0,
    trace_limit: int = 8,
) -> dict[str, Any]:
    model = build_dag_path_model(instance)
    default = analyze_sequence(model.default_sequence, instance.coils)

    started = time.monotonic()
    ga_solution = solve(
        model.program,
        strategy=GaConfig(
            max_iterations=max_iterations,
            population_size=population_size,
            mutation_count=max(1, population_size // 4),
            search_width=population_size,
            parallel_workers=1,
            duplicate_filter=True,
            mutation_portfolio=("random_reset", "random_swap"),
            local_improvement_strategy="tabu",
            local_improvement_top_k=1,
        ),
        seed=seed,
        time_limit_s=time_limit_s,
        trace_output="summary",
        trace_limit=trace_limit,
    )
    ga_row = summarize_solution(
        model=model,
        instance=instance,
        solution=ga_solution,
        strategy_name="ga",
        elapsed_seconds=time.monotonic() - started,
    )

    started = time.monotonic()
    alns_solution = solve(
        model.program,
        strategy=AlnsConfig(
            max_iterations=max_iterations,
            destroy_count=2,
            repair_operators=("greedy",),
            acceptance="not_worse",
        ),
        seed=seed,
        time_limit_s=time_limit_s,
        trace_output="summary",
        trace_limit=trace_limit,
    )
    alns_row = summarize_solution(
        model=model,
        instance=instance,
        solution=alns_solution,
        strategy_name="alns",
        elapsed_seconds=time.monotonic() - started,
    )

    rows = [ga_row, alns_row]
    best = min(rows, key=lambda row: (row["objective"], row["elapsed_seconds"]))
    return {
        "modeling": "dag_path",
        "instance": instance.name,
        "coil_count": len(instance.coils),
        "seed": seed,
        "max_iterations": max_iterations,
        "population_size": population_size,
        "time_limit_s": time_limit_s,
        "model": {
            "default_sequence_head": model.default_sequence[:20],
            "default_objective": int(default["transition_count"]),
            "edge_variable_count": len(model.edge_node_ids),
            "depot_index": model.depot_index,
            "graph_node_count": len(model.program.graph.nodes),
            "objective_ids": list(model.program.objective_ids),
        },
        "strategies": rows,
        "best_strategy": best["strategy"],
        "best_objective": best["objective"],
        "best_sequence_head": best["sequence_head"],
    }


def print_summary(payload: dict[str, Any]) -> None:
    print(f"instance: {payload['instance']}")
    print(f"modeling: {payload['modeling']}")
    print(f"default_objective: {payload['model']['default_objective']}")
    for row in payload["strategies"]:
        print(f"{row['strategy']}: objective={row['objective']} elapsed={row['elapsed_seconds']:.4f}s")
    print(f"best_strategy: {payload['best_strategy']}")
    print(f"best_objective: {payload['best_objective']}")


def main() -> int:
    instances = load_steel_instances()
    parser = argparse.ArgumentParser(description="Solve the steel DAG path model with GA and ALNS.")
    parser.add_argument("--instance", choices=tuple(instances), default="toy")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--max-iterations", type=int, default=80)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--time-limit-s", type=float, default=30.0)
    parser.add_argument("--trace-limit", type=int, default=8)
    parser.add_argument("--summary", action="store_true", help="Print a compact text summary instead of JSON.")
    args = parser.parse_args()

    instance = instances[args.instance]
    payload = solve_dag_path(
        instance=instance,
        seed=args.seed,
        max_iterations=args.max_iterations,
        population_size=args.population_size,
        time_limit_s=args.time_limit_s,
        trace_limit=args.trace_limit,
    )
    if args.summary:
        print_summary(payload)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
