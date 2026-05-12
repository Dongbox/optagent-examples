from __future__ import annotations

import time
from typing import Any

from optagent import Orchestrator
from optagent.heuristic.sequence_adjacency import greedy_construct_sequence

from steel.blackbox_model import build_program as build_blackbox_program
from steel.dag_path_model import build_program as build_dag_program
from steel.solve_profiles import (
    build_blackbox_config,
    build_dag_config,
    choose_blackbox_preset_mode,
)
from steel.steel_domain import SteelCoilInstance, analyze_sequence, build_penalty_matrix


def build_start_sequences(instance: SteelCoilInstance, *, seed: int) -> dict[str, list[int]]:
    import random

    penalty_matrix = build_penalty_matrix(instance.coils)
    identity = list(range(len(instance.coils)))
    constructive = greedy_construct_sequence(penalty_matrix)
    shuffled = list(identity)
    random.Random(seed).shuffle(shuffled)
    return {
        "identity": identity,
        "constructive": constructive,
        f"random_{seed}": shuffled,
    }


def perturb_sequence(sequence: list[int], *, swap_count: int, seed: int) -> list[int]:
    import random

    updated = list(sequence)
    if len(updated) < 2 or swap_count <= 0:
        return updated
    rng = random.Random(seed)
    for _ in range(swap_count):
        left, right = rng.sample(range(len(updated)), k=2)
        updated[left], updated[right] = updated[right], updated[left]
    return updated


def _mutation_stats(result: Any) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for strategy, successes in getattr(result, "mutation_successes", {}).items():
        trials = int(getattr(result, "mutation_trials", {}).get(strategy, 0))
        if trials <= 0:
            continue
        stats[strategy] = {
            "successes": int(successes),
            "trials": trials,
            "success_rate": float(successes) / float(trials),
        }
    return stats


def _solver_metrics(result: Any) -> dict[str, int]:
    metrics = {
        "accepted_moves": 0,
        "rejected_moves": 0,
        "attempts": 0,
    }
    for trace in getattr(result, "solver_traces", []):
        trace_metrics = getattr(trace, "metrics", {})
        for key in metrics:
            metrics[key] += int(trace_metrics.get(key, 0))
    return metrics


def _row(
    *,
    phase: str,
    route: str,
    start_policy: str,
    initial_sequence: list[int],
    final_sequence: list[int],
    instance: SteelCoilInstance,
    elapsed_seconds: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial = analyze_sequence(initial_sequence, instance.coils)
    final = analyze_sequence(final_sequence, instance.coils)
    return {
        "phase": phase,
        "route": route,
        "start_policy": start_policy,
        "coil_count": len(instance.coils),
        "initial_objective": int(initial["transition_count"]),
        "final_objective": int(final["transition_count"]),
        "improvement_delta": int(initial["transition_count"]) - int(final["transition_count"]),
        "improvement_rate": (
            (int(initial["transition_count"]) - int(final["transition_count"])) / float(initial["transition_count"])
            if int(initial["transition_count"]) > 0
            else 0.0
        ),
        "search_changed_sequence": list(initial_sequence) != list(final_sequence),
        "elapsed_seconds": elapsed_seconds,
        "initial_direct_weld_ratio": float(initial["direct_weld_ratio"]),
        "final_direct_weld_ratio": float(final["direct_weld_ratio"]),
        "initial_break_count": len(initial["break_positions"]),
        "final_break_count": len(final["break_positions"]),
        "initial_sequence_head": list(initial_sequence[:20]),
        "final_sequence_head": list(final_sequence[:20]),
        "metadata": metadata or {},
    }


def run_blackbox_route(
    *,
    instance: SteelCoilInstance,
    route: str,
    initial_sequence: list[int],
    start_policy: str,
    budget_iterations: int,
    generation_limit: int,
    search_seed: int,
    phase: str,
) -> dict[str, Any]:
    started = time.monotonic()
    if route == "blackbox_seed_only":
        return _row(
            phase=phase,
            route=route,
            start_policy=start_policy,
            initial_sequence=initial_sequence,
            final_sequence=initial_sequence,
            instance=instance,
            elapsed_seconds=time.monotonic() - started,
            metadata={"mode": "no_search", "family": "baseline"},
        )

    mode_map = {
        "blackbox_tabu": "tabu",
        "blackbox_evolutionary": "evolutionary",
        "blackbox_preset": "preset",
    }
    program, sequence_node_id = build_blackbox_program(instance, default_sequence=list(initial_sequence))
    effective_mode = mode_map[route]
    preset_policy = None
    if route == "blackbox_preset":
        initial_objective = analyze_sequence(initial_sequence, instance.coils)["transition_count"]
        effective_mode, preset_policy = choose_blackbox_preset_mode(objective=int(initial_objective))
        if effective_mode == "fast_polish":
            preset_policy = "initial_seed_target_reached_fast_polish"
        elif effective_mode == "targeted_polish":
            preset_policy = "initial_seed_midband_targeted_polish"
    result = Orchestrator().run(
        program,
        config=build_blackbox_config(
            mode=effective_mode,
            budget_iterations=budget_iterations,
            generation_limit=generation_limit,
            seed=search_seed,
        ),
    )
    final_sequence = list(result.final_solution.variable_values[sequence_node_id])
    metadata = {
        "mode": effective_mode,
        "family": "ga" if route in {"blackbox_evolutionary", "blackbox_preset"} else "local_search",
        "solver_trace_count": len(result.solver_traces),
        "generation_trace_count": len(result.evolutionary_generation_traces),
        "mutation_stats": _mutation_stats(result),
        "solver_metrics": _solver_metrics(result),
    }
    if preset_policy is not None:
        metadata["preset_policy"] = preset_policy
    return _row(
        phase=phase,
        route=route,
        start_policy=start_policy,
        initial_sequence=initial_sequence,
        final_sequence=final_sequence,
        instance=instance,
        elapsed_seconds=time.monotonic() - started,
        metadata=metadata,
    )


def run_dag_route(
    *,
    instance: SteelCoilInstance,
    route: str,
    initial_sequence: list[int],
    start_policy: str,
    budget_iterations: int,
    search_seed: int,
    phase: str,
) -> dict[str, Any]:
    started = time.monotonic()
    if route == "dag_seed":
        return _row(
            phase=phase,
            route=route,
            start_policy=start_policy,
            initial_sequence=initial_sequence,
            final_sequence=initial_sequence,
            instance=instance,
            elapsed_seconds=time.monotonic() - started,
            metadata={"mode": "seed", "family": "baseline"},
        )

    program, node_ids = build_dag_program(instance, initial_sequence=list(initial_sequence))
    initial_objective = analyze_sequence(initial_sequence, instance.coils)["transition_count"]
    if len(instance.coils) > 80 and int(initial_objective) <= 20:
        return _row(
            phase=phase,
            route=route,
            start_policy=start_policy,
            initial_sequence=initial_sequence,
            final_sequence=initial_sequence,
            instance=instance,
            elapsed_seconds=time.monotonic() - started,
            metadata={
                "mode": "preset",
                "family": "dag_policy",
                "selected_preset": "steel_large_instance_constructive_path",
                "selected_preset_source": "initial_seed_target_reached",
                "solver_trace_count": 0,
            },
        )

    result = Orchestrator().run(
        program,
        config=build_dag_config(
            mode="preset",
            budget_iterations=budget_iterations,
            seed=search_seed,
            coil_count=node_ids["coil_count"],
        ),
    )
    selected_edges = [
        tuple(int(part) for part in edge_name.split("->", maxsplit=1))
        for edge_name, node_id in node_ids["edge_node_ids"].items()
        if int(round(float(result.final_solution.variable_values[node_id]))) > 0
    ]
    from steel.steel_domain import decode_sequence_from_selected_edges

    final_sequence = decode_sequence_from_selected_edges(
        selected_edges=selected_edges,
        coil_count=node_ids["coil_count"],
        depot_index=node_ids["depot"],
    )
    return _row(
        phase=phase,
        route=route,
        start_policy=start_policy,
        initial_sequence=initial_sequence,
        final_sequence=final_sequence,
        instance=instance,
        elapsed_seconds=time.monotonic() - started,
        metadata={
            "mode": "preset",
            "family": "dag_policy",
            "selected_preset": result.selected_preset_name,
            "selected_preset_source": result.selected_preset_source,
            "solver_trace_count": len(result.solver_traces),
        },
    )


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["phase"], row["route"])
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for (phase, route), items in sorted(grouped.items()):
        summary.append(
            {
                "phase": phase,
                "route": route,
                "run_count": len(items),
                "mean_initial_objective": sum(item["initial_objective"] for item in items) / len(items),
                "mean_final_objective": sum(item["final_objective"] for item in items) / len(items),
                "mean_improvement_delta": sum(item["improvement_delta"] for item in items) / len(items),
                "best_final_objective": min(item["final_objective"] for item in items),
                "improved_run_count": sum(1 for item in items if item["improvement_delta"] > 0),
            }
        )
    return summary


def build_attribution_payload(
    *,
    instance: SteelCoilInstance,
    search_seed: int,
    budget_iterations: int,
    generation_limit: int,
    perturb_swap_counts: tuple[int, ...],
) -> dict[str, Any]:
    start_sequences = build_start_sequences(instance, seed=search_seed)
    rows: list[dict[str, Any]] = []

    for start_policy in ("identity", "constructive", f"random_{search_seed}"):
        rows.append(
            run_blackbox_route(
                instance=instance,
                route="blackbox_seed_only",
                initial_sequence=start_sequences[start_policy],
                start_policy=start_policy,
                budget_iterations=budget_iterations,
                generation_limit=generation_limit,
                search_seed=search_seed,
                phase="seed_only",
            )
        )

    for start_policy in ("identity", "constructive"):
        start_sequence = start_sequences[start_policy]
        for route in ("blackbox_tabu", "blackbox_evolutionary", "blackbox_preset"):
            rows.append(
                run_blackbox_route(
                    instance=instance,
                    route=route,
                    initial_sequence=start_sequence,
                    start_policy=start_policy,
                    budget_iterations=budget_iterations,
                    generation_limit=generation_limit,
                    search_seed=search_seed,
                    phase="same_seed_search",
                )
            )
    for route in ("dag_seed", "dag_preset"):
        rows.append(
            run_dag_route(
                instance=instance,
                route=route,
                initial_sequence=start_sequences["constructive"],
                start_policy="constructive",
                budget_iterations=budget_iterations,
                search_seed=search_seed,
                phase="same_seed_search",
            )
        )

    constructive = start_sequences["constructive"]
    skipped_routes: list[dict[str, Any]] = []
    for swap_count in perturb_swap_counts:
        perturbed_policy = f"constructive_swaps_{swap_count}"
        perturbed = perturb_sequence(constructive, swap_count=swap_count, seed=search_seed + swap_count)
        perturbed_objective = analyze_sequence(perturbed, instance.coils)["transition_count"]
        rows.append(
            run_blackbox_route(
                instance=instance,
                route="blackbox_seed_only",
                initial_sequence=perturbed,
                start_policy=perturbed_policy,
                budget_iterations=budget_iterations,
                generation_limit=generation_limit,
                search_seed=search_seed,
                phase="perturbation_recovery",
            )
        )
        route_list = ["blackbox_tabu", "blackbox_evolutionary", "blackbox_preset"]
        if len(instance.coils) <= 80 or int(perturbed_objective) <= 20:
            route_list.append("dag_preset")
        else:
            skipped_routes.append(
                {
                    "phase": "perturbation_recovery",
                    "route": "dag_preset",
                    "start_policy": perturbed_policy,
                    "reason": "skipped_for_large_instance_bad_start",
                    "initial_objective": int(perturbed_objective),
                }
            )
        for route in route_list:
            if route == "dag_preset":
                rows.append(
                    run_dag_route(
                        instance=instance,
                        route=route,
                        initial_sequence=perturbed,
                        start_policy=perturbed_policy,
                        budget_iterations=budget_iterations,
                        search_seed=search_seed,
                        phase="perturbation_recovery",
                    )
                )
                continue
            rows.append(
                run_blackbox_route(
                    instance=instance,
                    route=route,
                    initial_sequence=perturbed,
                    start_policy=perturbed_policy,
                    budget_iterations=budget_iterations,
                    generation_limit=generation_limit,
                    search_seed=search_seed,
                    phase="perturbation_recovery",
                )
            )

    return {
        "instance": instance.name,
        "coil_count": len(instance.coils),
        "search_seed": search_seed,
        "budget_iterations": budget_iterations,
        "generation_limit": generation_limit,
        "perturb_swap_counts": list(perturb_swap_counts),
        "phase_plan": [
            {
                "phase": "phase_1_seed_baselines",
                "goal": "Measure how much quality comes from the initial sequence alone.",
                "rows": ["blackbox_seed_only"],
            },
            {
                "phase": "phase_2_same_seed_search",
                "goal": "Hold the starting sequence fixed and compare local search, GA, preset policy, and DAG policy.",
                "rows": ["blackbox_tabu", "blackbox_evolutionary", "blackbox_preset", "dag_seed", "dag_preset"],
            },
            {
                "phase": "phase_3_perturbation_recovery",
                "goal": "Damage a strong constructive sequence and test whether each search route can recover it.",
                "rows": ["blackbox_tabu", "blackbox_evolutionary", "blackbox_preset", "dag_preset_optional"],
            },
        ],
        "rows": rows,
        "aggregate": aggregate_rows(rows),
        "skipped_routes": skipped_routes,
    }
