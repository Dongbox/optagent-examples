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
class SequenceExternalModel:
    program: Any
    sequence_node_id: int
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


def build_sequence_external_model(instance: SteelCoilInstance) -> SequenceExternalModel:
    penalty_matrix = build_penalty_matrix(instance.coils)
    default_sequence = list(range(len(instance.coils)))
    builder = ModelBuilder(
        metadata={
            "case": f"steel_sequence_external_{instance.name}",
            "model_style": "sequence_graph_ir_objective",
            "sequence_break_window": 24,
        }
    )
    coil_sequence = builder.sequence_var(
        size=len(instance.coils),
        default=default_sequence,
        name="coil_sequence",
    )
    builder.constraint(builder.sequence_contains(coil_sequence, 0), name="contains_first_coil")
    builder.minimize(
        builder.sequence_transition_sum(
            coil_sequence,
            penalty_matrix,
            include_return_edge=False,
            cost_semantics="penalty",
        ),
        name="transition_count",
    )
    return SequenceExternalModel(
        program=builder.freeze(),
        sequence_node_id=coil_sequence.node_id,
        default_sequence=default_sequence,
        penalty_matrix=penalty_matrix,
    )


def metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "strategy",
        "execution_graph_strategy",
        "termination_reason",
        "iterations",
        "attempted_moves",
        "accepted_moves",
        "domain_best_sequence_penalty",
        "external_batch_count",
        "external_rows_requested",
        "ga_generation_count",
        "ga_mutation_portfolio",
        "ga_tabu_improvement_count",
        "alns_iterations",
        "alns_candidates_evaluated",
        "alns_candidates_accepted",
        "alns_acceptance_model",
    )
    return {key: metadata[key] for key in keys if key in metadata}


def summarize_solution(
    *,
    model: SequenceExternalModel,
    instance: SteelCoilInstance,
    solution: Any,
    strategy_name: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    sequence = [int(item) for item in solution.variable_values[model.sequence_node_id]]
    diagnostics = analyze_sequence(sequence, instance.coils)
    return {
        "strategy": strategy_name,
        "solver_name": solution.solver_name,
        "status": solution.status.value,
        "feasible": solution.feasible,
        "elapsed_seconds": elapsed_seconds,
        "sequence_head": sequence[:20],
        "sequence": sequence,
        "objective": int(diagnostics["transition_count"]),
        "direct_weld_ratio": float(diagnostics["direct_weld_ratio"]),
        "diagnostics": diagnostics,
        "metadata": metadata_summary(solution.metadata),
    }


def solve_sequence_external(
    *,
    instance: SteelCoilInstance,
    seed: int = 11,
    max_iterations: int = 120,
    population_size: int = 12,
    time_limit_s: float = 30.0,
    trace_limit: int = 8,
) -> dict[str, Any]:
    model = build_sequence_external_model(instance)
    default = analyze_sequence(model.default_sequence, instance.coils)

    started = time.monotonic()
    ga_solution = solve(
        model.program,
        strategy=GaConfig(
            max_iterations=max_iterations,
            population_size=population_size,
            mutation_count=max(1, population_size // 3),
            search_width=population_size,
            parallel_workers=1,
            duplicate_filter=True,
            mutation_portfolio=(
                "sequence_two_opt",
                "sequence_block_move",
                "ruin_and_repair",
                "random_swap",
            ),
            local_improvement_strategy="lns",
            local_improvement_top_k=2,
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
            destroy_count=3,
            repair_operators=("greedy", "beam"),
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
        "modeling": "sequence_graph_ir_objective",
        "instance": instance.name,
        "coil_count": len(instance.coils),
        "seed": seed,
        "max_iterations": max_iterations,
        "population_size": population_size,
        "time_limit_s": time_limit_s,
        "model": {
            "default_sequence_head": model.default_sequence[:20],
            "default_objective": int(default["transition_count"]),
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
    parser = argparse.ArgumentParser(description="Solve the steel sequence graph IR model with GA and ALNS.")
    parser.add_argument("--instance", choices=tuple(instances), default="toy")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--max-iterations", type=int, default=120)
    parser.add_argument("--population-size", type=int, default=12)
    parser.add_argument("--time-limit-s", type=float, default=30.0)
    parser.add_argument("--trace-limit", type=int, default=8)
    parser.add_argument("--summary", action="store_true", help="Print a compact text summary instead of JSON.")
    args = parser.parse_args()

    instance = instances[args.instance]
    payload = solve_sequence_external(
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
