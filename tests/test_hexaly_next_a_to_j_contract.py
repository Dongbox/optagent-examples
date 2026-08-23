from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
from typing import Any

import pytest

import optagent_next
from optagent.runtime.external import HxExternalArgumentValues


EXAMPLES = Path(__file__).parents[1] / "examples/hexaly_next"
NOTEBOOKS = tuple(sorted(EXAMPLES.glob("[a-j]*/*.ipynb")))


class _ModelEvaluated(Exception):
    pass


class _ModelCaptured(Exception):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model


def _smallest_instance(notebook: Path) -> Path | None:
    directory = notebook.parent / "instances"
    if not directory.is_dir():
        return None
    candidates = [path for path in directory.iterdir() if path.is_file() and not path.name.startswith(".")]
    return min(candidates, key=lambda path: (path.stat().st_size, path.name), default=None)


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.parent.name)
def test_a_to_j_example_model_reaches_cpp_initial_evaluator(
    notebook: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _optagent_kernel import _evaluate_next_initial_model

    def evaluate(model: Any, **_kwargs: Any) -> None:
        external_functions = {
            name: {
                "kind": contract.kind,
                "function": lambda values, function=contract.function: function(HxExternalArgumentValues(values)),
            }
            for name, contract in model.external_functions.items()
        }
        result = _evaluate_next_initial_model(model.to_bytes(), external_functions)
        assert result["expression_count"] > 0
        assert result["unsupported_undefined_count"] == 0
        if notebook.parent.name == "hosaki_function":
            assert result["external_call_count"] == 1
        raise _ModelEvaluated

    monkeypatch.setattr(optagent_next, "solve", evaluate)
    namespace: dict[str, Any] = {"__name__": "notebook_contract"}
    document = json.loads(notebook.read_text(encoding="utf-8"))

    try:
        for cell in document["cells"]:
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if "INSTANCE_DIR" in source:
                continue
            exec(compile(source, str(notebook), "exec"), namespace)

        instance = _smallest_instance(notebook)
        arguments = (instance,) if instance is not None else ()
        namespace["main"](*arguments, time_limit=0.001)
    except _ModelEvaluated:
        return

    pytest.fail("example main() returned without sending its model through optagent_next.solve")


def _capture_notebook_model(notebook: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    def capture(model: Any, **_kwargs: Any) -> None:
        raise _ModelCaptured(model)

    monkeypatch.setattr(optagent_next, "solve", capture)
    namespace: dict[str, Any] = {"__name__": "notebook_search_diagnostic"}
    document = json.loads(notebook.read_text(encoding="utf-8"))
    try:
        for cell in document["cells"]:
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if "INSTANCE_DIR" in source:
                continue
            exec(compile(source, str(notebook), "exec"), namespace)
        instance = _smallest_instance(notebook)
        arguments = (instance,) if instance is not None else ()
        namespace["main"](*arguments, time_limit=0.001)
    except _ModelCaptured as captured:
        return captured.model
    pytest.fail(f"{notebook.parent.name} did not submit a model to optagent_next.solve")


def _external_bindings(model: Any) -> dict[str, dict[str, Any]]:
    from optagent.runtime.external import HxExternalArgumentValues

    return {
        name: {
            "kind": contract.kind,
            "function": lambda values, function=contract.function: function(HxExternalArgumentValues(values)),
        }
        for name, contract in model.external_functions.items()
    }


def _run_search_probe(
    payload: bytes,
    configuration: tuple[str, str, int, int, int, bool],
    external_functions: dict[str, dict[str, Any]],
    queue: Any,
) -> None:
    from _optagent_kernel import _diagnose_next_search

    (
        worker_mode,
        construction_mode,
        worker_threads,
        construction_evaluation_limit,
        target_seed_count,
        require_diversity,
    ) = configuration
    try:
        response = _diagnose_next_search(
            payload,
            0.08,
            worker_mode,
            construction_mode,
            worker_threads,
            64,
            construction_evaluation_limit,
            target_seed_count,
            require_diversity,
            1,
            external_functions,
        )
        queue.put(
            {
                "feasible": bool(response["feasible"]),
                "objectives": list(response["objectives"]),
                "diagnostics": dict(response["diagnostics"]),
            }
        )
    except BaseException as error:
        queue.put({"error": f"{type(error).__name__}: {error}"})


def _isolated_search_probe(
    payload: bytes,
    configuration: tuple[str, str, int, int, int, bool],
    external_functions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    process = context.Process(
        target=_run_search_probe,
        args=(payload, configuration, external_functions or {}, queue),
    )
    process.start()
    process.join(timeout=2.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=1.0)
        return {"timeout": True, "exitcode": process.exitcode}
    if queue.empty():
        return {"error": "probe exited without a result", "exitcode": process.exitcode}
    return dict(queue.get())


@pytest.mark.skipif(
    os.environ.get("OPTAGENT_NEXT_RUN_SEARCH_DIAGNOSTICS") != "1",
    reason="set OPTAGENT_NEXT_RUN_SEARCH_DIAGNOSTICS=1 to run the 31-example search matrix",
)
def test_a_to_j_worker_and_streaming_search_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configurations = (
        ("default_only", "vns", "default_only", 1, 2, 1, False),
        ("streaming_current", "vns", "streaming", 1, 2, 1, False),
        ("default_only", "ga", "default_only", 1, 2, 1, False),
        ("streaming_current", "ga", "streaming", 1, 2, 1, False),
        ("default_only", "portfolio", "default_only", 2, 2, 1, False),
        ("streaming_current", "portfolio", "streaming", 2, 2, 1, False),
        ("blocking_diverse", "portfolio", "blocking", 2, 16, 4, True),
        ("streaming_diverse", "portfolio", "streaming", 2, 16, 4, True),
    )
    selected_examples = {name for name in os.environ.get("OPTAGENT_NEXT_DIAGNOSTIC_EXAMPLES", "").split(",") if name}
    notebooks = tuple(
        notebook for notebook in NOTEBOOKS if not selected_examples or notebook.parent.name in selected_examples
    )
    rows: list[dict[str, Any]] = []
    for notebook in notebooks:
        model = _capture_notebook_model(notebook, monkeypatch)
        if model.external_functions:
            probe = _isolated_search_probe(
                model.to_bytes(),
                ("vns", "streaming", 1, 2, 1, False),
                _external_bindings(model),
            )
            rows.append(
                {
                    "example": notebook.parent.name,
                    "worker_mode": "vns",
                    "construction_mode": "streaming_current",
                    "external_function_probe": True,
                    **probe,
                }
            )
            continue
        for (
            construction_label,
            worker_mode,
            construction_mode,
            worker_threads,
            construction_evaluation_limit,
            target_seed_count,
            require_diversity,
        ) in configurations:
            probe = _isolated_search_probe(
                model.to_bytes(),
                (
                    worker_mode,
                    construction_mode,
                    worker_threads,
                    construction_evaluation_limit,
                    target_seed_count,
                    require_diversity,
                ),
            )
            rows.append(
                {
                    "example": notebook.parent.name,
                    "worker_mode": worker_mode,
                    "construction_mode": construction_label,
                    **probe,
                }
            )

    report_path = Path(os.environ.get("OPTAGENT_NEXT_DIAGNOSTIC_REPORT", "/tmp/hexaly_next_search.json"))
    report_path.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")

    completed = [row for row in rows if "diagnostics" in row]
    assert completed
    timeouts = [row for row in rows if row.get("timeout")]
    assert not timeouts, f"worker search exceeded the hard probe timeout; report={report_path}"
    errors = [row for row in rows if "error" in row]
    assert not errors, f"worker search probes failed; report={report_path}"
    assert all(not row["diagnostics"]["termination_reason"].startswith("worker_failed") for row in completed)
    for row in completed:
        diagnostics = row["diagnostics"]
        publications = diagnostics["seed_publications"]
        signatures = [publication["signature"] for publication in publications]
        assert len(signatures) == len(set(signatures)), (
            f"construction published a duplicate seed; row={row}; report={report_path}"
        )
        assert [publication["publication_ns"] for publication in publications] == sorted(
            publication["publication_ns"] for publication in publications
        )
        assert (
            diagnostics["search_evaluations_lost_to_construction"]
            == diagnostics["construction"]["budgeted_evaluations"]
        )
        for acceptance in diagnostics["seed_acceptances"]:
            publication = next(item for item in publications if item["signature"] == acceptance["signature"])
            assert acceptance["acceptance_ns"] >= publication["publication_ns"]

    paired: dict[tuple[str, str], dict[str, Any]] = {}
    for row in completed:
        if row["construction_mode"] not in {"blocking_diverse", "streaming_diverse"}:
            continue
        paired[(row["example"], row["construction_mode"])] = row
    for example in {key[0] for key in paired}:
        blocking = paired.get((example, "blocking_diverse"))
        streaming = paired.get((example, "streaming_diverse"))
        if blocking is None or streaming is None:
            continue
        blocking_diagnostics = blocking["diagnostics"]
        streaming_diagnostics = streaming["diagnostics"]
        assert [item["signature"] for item in blocking_diagnostics["seed_publications"]] == [
            item["signature"] for item in streaming_diagnostics["seed_publications"]
        ], f"blocking/streaming used different seed sequences for {example}; report={report_path}"
        assert (
            blocking_diagnostics["construction"]["budgeted_evaluations"]
            == streaming_diagnostics["construction"]["budgeted_evaluations"]
        ), f"blocking/streaming used different construction budgets for {example}; report={report_path}"
    for worker_mode in ("vns", "ga"):
        relevant = [row for row in completed if row["worker_mode"] == worker_mode]
        if not relevant:
            continue
        assert any(row["diagnostics"]["evaluated"] > 0 for row in relevant), (
            f"{worker_mode} did not evaluate a candidate on any a-to-j example; report={report_path}"
        )
        assert any(row["diagnostics"]["final_better_than_initial"] for row in relevant), (
            f"{worker_mode} did not improve any a-to-j example; report={report_path}"
        )
