#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from optagent.benchmark_cli import write_json_output
from steel.search_attribution import build_attribution_payload
from steel.steel_domain import load_steel_instances


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run steel seed-vs-search attribution experiments.",
    )
    parser.add_argument("--instance", choices=tuple(load_steel_instances().keys()), default="bundled")
    parser.add_argument("--search-seed", type=int, default=11)
    parser.add_argument("--budget-iterations", type=int, default=120)
    parser.add_argument("--generation-limit", type=int, default=12)
    parser.add_argument(
        "--perturb-swaps",
        default="12,24",
        help="Comma-separated swap counts for constructive perturbation recovery experiments.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full payload as JSON.")
    parser.add_argument("--json-output", type=Path, help="Optional path to write the full payload as JSON.")
    return parser


def _parse_perturb_swaps(value: str) -> tuple[int, ...]:
    items = []
    for part in value.split(","):
        text = part.strip()
        if not text:
            continue
        items.append(max(0, int(text)))
    return tuple(items) or (12, 24)


def _print_human_summary(payload: dict[str, object]) -> None:
    print(f"instance: {payload['instance']}")
    print(f"coil_count: {payload['coil_count']}")
    print(f"search_seed: {payload['search_seed']}")
    print(f"budget_iterations: {payload['budget_iterations']}")
    print(f"generation_limit: {payload['generation_limit']}")
    print("aggregate:")
    for row in payload["aggregate"]:
        print(
            "  "
            f"{row['phase']} | {row['route']} | "
            f"mean_initial={row['mean_initial_objective']:.2f} | "
            f"mean_final={row['mean_final_objective']:.2f} | "
            f"mean_delta={row['mean_improvement_delta']:.2f} | "
            f"best_final={row['best_final_objective']}"
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = build_attribution_payload(
        instance=load_steel_instances()[args.instance],
        search_seed=args.search_seed,
        budget_iterations=args.budget_iterations,
        generation_limit=args.generation_limit,
        perturb_swap_counts=_parse_perturb_swaps(args.perturb_swaps),
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
