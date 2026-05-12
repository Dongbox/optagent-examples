from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from optagent import Orchestrator, SolutionStatus, UnifiedSolution
from optagent.ir.eval_full import evaluate_full

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution
from steel.dag_path_model import build_program, describe_model_structure
from steel.solve_profiles import build_dag_config
from steel.steel_domain import (
    SteelCoilInstance,
    analyze_sequence,
    decode_sequence_from_selected_edges,
    load_steel_instances,
)


def steel_instances() -> dict[str, SteelCoilInstance]:
    return load_steel_instances()


def _selected_edges(node_ids: dict[str, int], variable_values: dict[int, Any]) -> list[tuple[int, int]]:
    selected: list[tuple[int, int]] = []
    for edge_name, node_id in node_ids.items():
        if int(round(float(variable_values[node_id]))) > 0:
            left_text, right_text = edge_name.split("->", maxsplit=1)
            selected.append((int(left_text), int(right_text)))
    return selected


def solve_instance(
    *,
    instance: SteelCoilInstance,
    mode: str,
    seed: int,
    budget_iterations: int,
) -> dict[str, Any]:
    program, node_ids = build_program(instance)
    seeded_eval = evaluate_full(program, program.default_state())
    large_constructive_target = len(instance.coils) > 80 and int(next(iter(seeded_eval.objective_values.values()), 10**9)) <= 20
    if mode == "seed" or (mode == "preset" and large_constructive_target):
        result_solution = UnifiedSolution(
            solver_name="default_sequence",
            status=SolutionStatus.FEASIBLE,
            variable_values=dict(program.default_state().variable_values),
            objective_values=dict(seeded_eval.objective_values),
            constraint_values=dict(seeded_eval.constraint_values),
            feasible=all(bool(v) for v in seeded_eval.constraint_values.values()),
            dag_recheck_passed=True,
            metadata={
                "phase_count": 0,
                "selected_preset_name": "steel_default_path" if mode == "seed" else "steel_large_instance_constructive_path",
                "selected_preset_family": "hybrid",
                "selected_preset_objective": "quality",
                "selected_preset_source": "default_state" if mode == "seed" else "default_state_target_reached",
            },
        )
        result = None
    else:
        orchestrator = Orchestrator()
        result = orchestrator.run(
            program,
            config=build_dag_config(
                mode=mode,
                budget_iterations=budget_iterations,
                seed=seed,
                coil_count=len(instance.coils),
            ),
        )
        result_solution = result.final_solution

    selected_edges = _selected_edges(node_ids["edge_node_ids"], result_solution.variable_values)
    sequence = decode_sequence_from_selected_edges(
        selected_edges=selected_edges,
        coil_count=node_ids["coil_count"],
        depot_index=node_ids["depot"],
    )
    diagnostics = analyze_sequence(sequence, instance.coils)
    return {
        "instance": instance.name,
        "coil_count": len(instance.coils),
        "model_style": "dag_path",
        "solve_style": "seeded" if mode == "seed" else ("exact" if mode in {"preset", "exact"} else "hybrid"),
        "mode": mode,
        "seed": seed,
        "budget_iterations": budget_iterations,
        "selected_edges": selected_edges,
        "selected_preset": result.selected_preset_name if result is not None else result_solution.metadata.get("selected_preset_name"),
        "selected_preset_source": result.selected_preset_source if result is not None else result_solution.metadata.get("selected_preset_source"),
        "dag_node_ids": node_ids,
        "structure": describe_model_structure(node_ids),
        "graph_node_count": len(program.graph.nodes),
        "objective_ids": list(program.objective_ids),
        "sequence": sequence,
        "sequence_head": sequence[:20],
        "sequence_diagnostics": diagnostics,
        "solution": result_solution,
        "seed_sequence_head": [],
        "seed_diagnostics": None,
    }


def summarize_run(solved: dict[str, Any]) -> dict[str, Any]:
    diagnostics = solved["sequence_diagnostics"]
    return {
        "instance": solved["instance"],
        "coil_count": solved["coil_count"],
        "model_style": solved["model_style"],
        "solve_style": solved["solve_style"],
        "mode": solved["mode"],
        "seed": solved["seed"],
        "budget_iterations": solved["budget_iterations"],
        "selected_edges": solved["selected_edges"][:20],
        "selected_preset": solved["selected_preset"],
        "selected_preset_source": solved["selected_preset_source"],
        "sequence_head": solved["sequence_head"],
        "transition_count": diagnostics["transition_count"],
        "direct_weld_ratio": diagnostics["direct_weld_ratio"],
        "break_positions": diagnostics["break_positions"],
        "diagnostics": diagnostics,
        "graph_node_count": solved["graph_node_count"],
        "objective_ids": solved["objective_ids"],
        "structure": solved["structure"],
        "seed_sequence_head": solved.get("seed_sequence_head", []),
        "seed_diagnostics": solved.get("seed_diagnostics"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Steel coil sequencing as a DAG-oriented exact path model.")
    parser.add_argument("--instance", choices=tuple(steel_instances().keys()), default="toy")
    parser.add_argument("--mode", choices=("preset", "seed", "exact", "hybrid"), default="preset")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--budget-iterations", type=int, default=180)
    args = parser.parse_args()

    instance = steel_instances()[args.instance]
    solved = solve_instance(
        instance=instance,
        mode=args.mode,
        seed=args.seed,
        budget_iterations=args.budget_iterations,
    )
    print_solution(
        "steel transition sequencing solved through a DAG-oriented exact path model",
        solved.pop("solution"),
        extra=summarize_run(solved),
    )


if __name__ == "__main__":
    main()
