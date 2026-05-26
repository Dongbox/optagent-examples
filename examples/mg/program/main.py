from __future__ import annotations

import argparse
import json
import logging
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
AGENT_LOGGER_NAME = "Agent"
OPTAGENT_LOGGER_NAME = "OptAgent"
_MG_AGENT_LOG_HANDLER = "_mg_agent_log_handler"
_MG_OPTAGENT_LOG_HANDLER = "_mg_optagent_log_handler"


def configure_agent_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the APS Transformer logger for direct main.py execution."""

    logger = logging.getLogger(AGENT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, _MG_AGENT_LOG_HANDLER, False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        setattr(handler, _MG_AGENT_LOG_HANDLER, True)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
    for handler in logger.handlers:
        if getattr(handler, _MG_AGENT_LOG_HANDLER, False):
            handler.setLevel(level)
    return logger


def configure_optagent_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the OptAgent progress logger for direct main.py execution."""

    logger = logging.getLogger(OPTAGENT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, _MG_OPTAGENT_LOG_HANDLER, False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        setattr(handler, _MG_OPTAGENT_LOG_HANDLER, True)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
    for handler in logger.handlers:
        if getattr(handler, _MG_OPTAGENT_LOG_HANDLER, False):
            handler.setLevel(level)
    return logger


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def _env_log_level(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().upper()
    if normalized.isdigit():
        return int(normalized)
    return int(getattr(logging, normalized, default))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MG OptAgent pipeline against one SQLite database.")
    parser.add_argument(
        "db_path",
        nargs="?",
        default=os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite database used for preprocess input, model input, and output tables.",
    )
    return parser.parse_args(argv)


def run_pipeline(
    db_path: str | Path,
    *,
    progress_logging: bool = False,
    progress_log_level: int = logging.INFO,
    heuristic_cost_logging: bool = True,
    heuristic_cost_logging_policy: str = "improved",
) -> dict[str, Any]:
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
    result["model"] = run_production_case(
        sqlite_db_path,
        output_db_path=sqlite_db_path,
        write_legacy_compat=True,
        progress_logging=progress_logging,
        progress_log_level=progress_log_level,
        heuristic_cost_logging=heuristic_cost_logging,
        heuristic_cost_logging_policy=heuristic_cost_logging_policy,
    )
    runtime["model_run"] = round(time.perf_counter() - start, 6)

    start = time.perf_counter()
    result["postprocess"] = run_postprocess(sqlite_db_path)
    runtime["postprocess"] = round(time.perf_counter() - start, 6)

    result["runtime"] = runtime
    return result


def terminal_output_payload(pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """Return the concise terminal payload expected by MG operators."""

    postprocess = pipeline_result["postprocess"]
    return {
        "rule_costs": postprocess["rule_costs"],
        "score_curve": pipeline_result["model"]["score_curve"],
    }


def main() -> None:
    progress_logging = _env_bool("OPTAGENT_PROGRESS_LOGGING", default=True)
    progress_log_level = _env_log_level("OPTAGENT_PROGRESS_LOG_LEVEL", default=logging.INFO)
    heuristic_cost_logging = _env_bool("OPTAGENT_HEURISTIC_COST_LOGGING", default=True)
    heuristic_cost_logging_policy = os.environ.get("OPTAGENT_HEURISTIC_COST_LOGGING_POLICY", "improved")
    configure_agent_logging()
    if progress_logging:
        configure_optagent_logging(progress_log_level)
    payload = run_pipeline(
        parse_args().db_path,
        progress_logging=progress_logging,
        progress_log_level=progress_log_level,
        heuristic_cost_logging=heuristic_cost_logging,
        heuristic_cost_logging_policy=heuristic_cost_logging_policy,
    )
    print(json.dumps(terminal_output_payload(payload), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
