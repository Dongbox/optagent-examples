from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_examples_match_the_current_public_api_surface() -> None:
    assert not (ROOT / "examples/presets").exists()

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
    ):
        assert removed_api not in source
