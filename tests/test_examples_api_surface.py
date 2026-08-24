from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_examples_match_the_current_public_api_surface() -> None:
    examples = ROOT / "examples"
    assert (examples / "hexaly").is_dir()
    maintained = {
        path.name
        for path in examples.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and any(next(path.rglob(pattern), None) is not None for pattern in ("*.py", "*.md", "*.ipynb"))
    }
    assert maintained == {"hexaly"}

    source_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "examples").rglob("*.py")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.ipynb")),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for removed_api in (
        "PhaseConfig",
        "HeuristicStrategy",
        "TabuConfig",
        "solution.metadata",
        "parallel_workers=",
        "mutation_count=",
        "mutation_portfolio=",
        "search_width=",
        "duplicate_filter=",
        "local_improvement_strategy=",
        "local_improvement_top_k=",
        "algorithm=",
        "strategy=",
        "GaConfig",
        "CblsConfig",
    ):
        assert removed_api not in source
