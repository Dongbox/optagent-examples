from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from steel.dag_path_model import build_program
from steel.run_dag import main, solve_instance, steel_instances, summarize_run

__all__ = [
    "build_program",
    "main",
    "solve_instance",
    "steel_instances",
    "summarize_run",
]


if __name__ == "__main__":
    main()
