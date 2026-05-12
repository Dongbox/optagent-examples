from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

PROGRAM_ROOT = Path(__file__).resolve().parent
EXAMPLES_ROOT = Path(__file__).resolve().parents[2]
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from mg.program.model.reports import run_production_case
from mg.program.scripts.postprocess.postprocess import run_postprocess
from mg.program.scripts.preprocess.transformer import main as run_preprocess


DEFAULT_DB_PATH = str(PROGRAM_ROOT / "data" / "20260407000000.db")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MG OptAgent pipeline against one SQLite database.")
    parser.add_argument(
        "db_path",
        nargs="?",
        default=os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite database used for preprocess input, model input, and output tables.",
    )
    return parser.parse_args(argv)


def run_pipeline(db_path: str | Path) -> dict[str, Any]:
    """Run preprocess, OptAgent model, and postprocess in one SQLite file."""

    sqlite_db_path = str(Path(db_path).expanduser().resolve())
    runtime: dict[str, float] = {}
    result: dict[str, Any] = {
        "program_root": str(PROGRAM_ROOT),
        "db_path": sqlite_db_path,
        "sqlite_handoff": {"mode": "in_place", "db_path": sqlite_db_path},
    }

    start = time.perf_counter()
    preprocess_ok = run_preprocess(sqlite_db_path, sqlite_db_path)
    result["preprocess"] = {"ok": preprocess_ok}
    runtime["preprocess"] = round(time.perf_counter() - start, 6)
    if not preprocess_ok:
        result["runtime"] = runtime
        raise RuntimeError(f"MG preprocess failed for {sqlite_db_path}; model and postprocess were not run.")

    start = time.perf_counter()
    result["model"] = run_production_case(sqlite_db_path, output_db_path=sqlite_db_path, write_legacy_compat=True)
    runtime["model_run"] = round(time.perf_counter() - start, 6)

    start = time.perf_counter()
    result["postprocess"] = run_postprocess(sqlite_db_path)
    runtime["postprocess"] = round(time.perf_counter() - start, 6)

    result["runtime"] = runtime
    return result


def main() -> None:
    payload = run_pipeline(parse_args().db_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
