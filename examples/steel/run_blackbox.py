from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from optagent import Orchestrator
from optagent.ir.eval_full import evaluate_full

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import print_solution
from steel.blackbox_model import build_program
from steel.solve_profiles import build_blackbox_config, choose_blackbox_preset_mode
from steel.steel_domain import SteelCoilInstance, analyze_sequence, load_steel_instances


def steel_instances() -> dict[str, SteelCoilInstance]:
    return load_steel_instances()


def solve_instance(
    *,
    instance: SteelCoilInstance,
    mode: str,
    budget_iterations: int,
    generation_limit: int,
    seed: int,
) -> dict[str, Any]:
    baseline_sequence = list(range(len(instance.coils)))
    baseline = analyze_sequence(baseline_sequence, instance.coils)
    program, sequence_node_id = build_program(instance)

    orchestrator = Orchestrator()
    effective_mode = mode
    preset_policy = "explicit_mode"
    if mode == "preset":
        default_eval = evaluate_full(program, program.default_state())
        default_objective = int(next(iter(default_eval.objective_values.values()), 10**9))
        effective_mode, preset_policy = choose_blackbox_preset_mode(objective=default_objective)
    result = orchestrator.run(
        program,
        config=build_blackbox_config(
            mode=effective_mode,
            budget_iterations=budget_iterations,
            generation_limit=generation_limit,
            seed=seed,
        ),
    )

    best_sequence = list(result.final_solution.variable_values[sequence_node_id])
    best = analyze_sequence(best_sequence, instance.coils)
    
    # 计算变异策略成功率
    mutation_stats = {}
    if hasattr(result, 'mutation_successes') and hasattr(result, 'mutation_trials'):
        for strategy in result.mutation_successes:
            successes = result.mutation_successes[strategy]
            trials = result.mutation_trials[strategy]
            if trials > 0:
                mutation_stats[strategy] = {
                    "successes": successes,
                    "trials": trials,
                    "success_rate": successes / trials
                }
    
    return {
        "instance": instance.name,
        "coil_count": len(instance.coils),
        "model_style": "blackbox_sequence",
        "solve_style": "heuristic" if mode != "preset" else "preset",
        "mode": mode,
        "seed": seed,
        "budget_iterations": budget_iterations,
        "generation_limit": generation_limit,
        "sequence_head": best_sequence[:20],
        "baseline": baseline,
        "best": best,
        "selected_preset": result.selected_preset_name,
        "selected_preset_source": result.selected_preset_source,
        "generation_trace_count": len(result.evolutionary_generation_traces),
        "solver_trace_count": len(result.solver_traces),
        "solution": result.final_solution,
        "mutation_stats": mutation_stats,
        "effective_mode": effective_mode,
        "preset_policy": preset_policy,
        "seed_sequence_head": [],
        "seed_diagnostics": None,
    }


def summarize_run(solved: dict[str, Any]) -> dict[str, Any]:
    baseline_objective = int(solved["baseline"]["transition_count"])
    best_objective = int(solved["best"]["transition_count"])
    improvement = baseline_objective - best_objective
    return {
        "instance": solved["instance"],
        "coil_count": solved["coil_count"],
        "model_style": solved["model_style"],
        "solve_style": solved["solve_style"],
        "mode": solved["mode"],
        "seed": solved["seed"],
        "budget_iterations": solved["budget_iterations"],
        "generation_limit": solved["generation_limit"],
        "sequence_head": solved["sequence_head"],
        "baseline_objective": baseline_objective,
        "best_objective": best_objective,
        "improvement": improvement,
        "improvement_ratio": (improvement / baseline_objective) if baseline_objective else 0.0,
        "improved": improvement > 0,
        "transition_count": int(solved["best"]["transition_count"]),
        "direct_weld_ratio": solved["best"]["direct_weld_ratio"],
        "selected_preset": solved["selected_preset"],
        "selected_preset_source": solved["selected_preset_source"],
        "generation_trace_count": solved["generation_trace_count"],
        "solver_trace_count": solved["solver_trace_count"],
        "diagnostics": solved["best"],
        "baseline": solved["baseline"],
        "best": solved["best"],
        "mutation_stats": solved.get("mutation_stats", {}),
        "effective_mode": solved.get("effective_mode", solved["mode"]),
        "preset_policy": solved.get("preset_policy"),
        "seed_sequence_head": solved.get("seed_sequence_head", []),
        "seed_diagnostics": solved.get("seed_diagnostics"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Steel coil sequencing as a blackbox sequence optimization problem.")
    parser.add_argument("--instance", choices=tuple(steel_instances().keys()), default="toy")
    parser.add_argument("--mode", choices=("preset", "evolutionary", "tabu"), default="preset")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--budget-iterations", type=int, default=120)
    parser.add_argument("--generation-limit", type=int, default=12)
    args = parser.parse_args()

    instance = steel_instances()[args.instance]
    solved = solve_instance(
        instance=instance,
        mode=args.mode,
        budget_iterations=args.budget_iterations,
        generation_limit=args.generation_limit,
        seed=args.seed,
    )
    print_solution(
        "steel transition sequencing solved in the current optagent framework",
        solved.pop("solution"),
        extra=summarize_run(solved),
    )


if __name__ == "__main__":
    main()
