#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from optagent.benchmark_cli import parse_seeds, write_json_output
from steel.run_blackbox import solve_instance, steel_instances, summarize_run


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run repeatable steel blackbox experiments across one instance/mode combination.",
    )
    parser.add_argument("--instance", choices=tuple(steel_instances().keys()), default="bundled_head40")
    parser.add_argument("--mode", choices=("preset", "evolutionary", "tabu"), default="preset")
    parser.add_argument(
        "--seed",
        action="append",
        dest="seeds",
        help="Random seed. Repeat the flag or provide a comma-separated list. Default: 0.",
    )
    parser.add_argument("--budget-iterations", type=int, default=120)
    parser.add_argument("--generation-limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Print the full experiment payload as JSON.")
    parser.add_argument("--json-output", type=Path, help="Optional path to write the full experiment payload as JSON.")
    return parser


def _aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    best_objective = min(run["best_objective"] for run in runs)
    baseline_objective = runs[0]["baseline_objective"]
    improvements = [run["improvement"] for run in runs]
    return {
        "run_count": len(runs),
        "baseline_objective": baseline_objective,
        "best_objective": best_objective,
        "mean_best_objective": sum(run["best_objective"] for run in runs) / len(runs),
        "max_improvement": max(improvements),
        "mean_improvement": sum(improvements) / len(runs),
        "improved_run_count": sum(1 for run in runs if run["improved"]),
        "improved_rate": sum(1 for run in runs if run["improved"]) / len(runs),
    }


def _payload(
    *,
    instance_name: str,
    mode: str,
    seeds: tuple[int, ...],
    budget_iterations: int,
    generation_limit: int,
) -> dict[str, Any]:
    instance = steel_instances()[instance_name]
    runs = [
        summarize_run(
            solve_instance(
                instance=instance,
                mode=mode,
                budget_iterations=budget_iterations,
                generation_limit=generation_limit,
                seed=seed,
            )
        )
        for seed in seeds
    ]
    return {
        "instance": instance.name,
        "mode": mode,
        "seeds": list(seeds),
        "budget_iterations": budget_iterations,
        "generation_limit": generation_limit,
        "aggregate": _aggregate_runs(runs),
        "runs": runs,
    }


def _print_human_summary(payload: dict[str, Any]) -> None:
    aggregate = payload["aggregate"]
    print(f"instance: {payload['instance']}")
    print(f"mode: {payload['mode']}")
    print(f"seeds: {', '.join(str(seed) for seed in payload['seeds'])}")
    print(f"baseline_objective: {aggregate['baseline_objective']}")
    print(f"best_objective: {aggregate['best_objective']}")
    print(f"mean_best_objective: {aggregate['mean_best_objective']:.4f}")
    print(f"max_improvement: {aggregate['max_improvement']}")
    print(f"mean_improvement: {aggregate['mean_improvement']:.4f}")
    print(f"improved_rate: {aggregate['improved_rate']:.2f}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    seeds = parse_seeds(args.seeds)
    payload = _payload(
        instance_name=args.instance,
        mode=args.mode,
        seeds=seeds,
        budget_iterations=args.budget_iterations,
        generation_limit=args.generation_limit,
    )

    if args.json_output is not None:
        write_json_output(args.json_output, payload)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    _print_human_summary(payload)
    if args.json_output is not None:
        print(f"\nJSON written to: {args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
