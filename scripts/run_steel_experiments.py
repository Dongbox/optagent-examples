#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from blackbox.steel_sequence_external import load_steel_instances, solve_sequence_external


def parse_csv_or_repeat(values: list[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            normalized = part.strip()
            if normalized:
                items.append(normalized)
    return tuple(items)


def parse_seeds(values: list[str] | None) -> tuple[int, ...]:
    raw = parse_csv_or_repeat(values)
    return tuple(int(item) for item in raw) if raw else (0,)


def write_json_output(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    instances = load_steel_instances()
    parser = argparse.ArgumentParser(
        description="Run repeatable steel sequence graph IR GA evaluations across one instance.",
    )
    parser.add_argument("--instance", choices=tuple(instances), default="bundled_head40")
    parser.add_argument(
        "--seed",
        action="append",
        dest="seeds",
        help="Random seed. Repeat the flag or provide a comma-separated list. Default: 0.",
    )
    parser.add_argument("--max-iterations", type=int, default=120)
    parser.add_argument("--population-size", type=int, default=12)
    parser.add_argument("--time-limit-s", type=float, default=30.0)
    parser.add_argument("--json", action="store_true", help="Print the full experiment payload as JSON.")
    parser.add_argument("--json-output", type=Path, help="Optional path to write the full experiment payload as JSON.")
    return parser


def _payload(
    *,
    instance_name: str,
    seeds: tuple[int, ...],
    max_iterations: int,
    population_size: int,
    time_limit_s: float,
) -> dict[str, object]:
    instance = load_steel_instances()[instance_name]
    runs = [
        solve_sequence_external(
            instance=instance,
            seed=seed,
            max_iterations=max_iterations,
            population_size=population_size,
            time_limit_s=time_limit_s,
        )
        for seed in seeds
    ]
    best_objective = min(run["best_objective"] for run in runs)
    best_counts = {
        strategy: sum(1 for run in runs if run["best_strategy"] == strategy)
        for strategy in sorted({run["best_strategy"] for run in runs})
    }
    return {
        "instance": instance.name,
        "seeds": list(seeds),
        "max_iterations": max_iterations,
        "population_size": population_size,
        "time_limit_s": time_limit_s,
        "aggregate": {
            "run_count": len(runs),
            "best_objective": best_objective,
            "mean_best_objective": sum(run["best_objective"] for run in runs) / len(runs),
            "best_strategy_counts": best_counts,
        },
        "runs": runs,
    }


def _print_human_summary(payload: dict[str, object]) -> None:
    aggregate = payload["aggregate"]
    assert isinstance(aggregate, dict)
    print(f"instance: {payload['instance']}")
    print(f"seeds: {', '.join(str(seed) for seed in payload['seeds'])}")
    print(f"best_objective: {aggregate['best_objective']}")
    print(f"mean_best_objective: {aggregate['mean_best_objective']:.4f}")
    print(f"best_strategy_counts: {aggregate['best_strategy_counts']}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = _payload(
        instance_name=args.instance,
        seeds=parse_seeds(args.seeds),
        max_iterations=args.max_iterations,
        population_size=args.population_size,
        time_limit_s=args.time_limit_s,
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
