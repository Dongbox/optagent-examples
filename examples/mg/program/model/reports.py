from __future__ import annotations

"""MG migration reports and SQLite production-output helpers.

This module intentionally owns parity, structured-edge, search-replacement, and
production-output reporting. The actual OptAgent model construction lives in
`model.py`; the actual search execution lives in `search.py`. Keeping these
diagnostic/reporting helpers here prevents the solver path from becoming a
second command-line application.
"""

from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .model import STATEFUL_BLACKBOX_RULES, STRUCTURED_EDGE_RULES, build_structured_edges
from .rules import group_rule_costs, score_sequence
from .search import DEFAULT_SEARCH_MODES, solve_mg_sequence
from mg.program.scripts.postprocess.postprocess import (
    write_legacy_compatibility_tables,
    write_production_output_tables,
    write_summary_json,
)
from mg.program.scripts.preprocess.data import (
    MGCase,
    MGParityReport,
    MGParityRuleDelta,
    load_mg_case,
)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ).fetchone()
    return row is not None


def _read_aps_rule_costs(db_path: str | Path) -> dict[str, float]:
    conn = sqlite3.connect(Path(db_path).expanduser().resolve())
    try:
        if not _table_exists(conn, "t_rules_cost"):
            return {}
        rows = conn.execute(
            "SELECT rule_name, SUM(COALESCE(cost, 0)) FROM t_rules_cost GROUP BY rule_name;"
        ).fetchall()
        return {str(rule_name): float(cost or 0.0) for rule_name, cost in rows}
    finally:
        conn.close()


def _read_aps_total_cost(db_path: str | Path) -> float | None:
    conn = sqlite3.connect(Path(db_path).expanduser().resolve())
    try:
        if not _table_exists(conn, "t_total_cost"):
            return None
        row = conn.execute("SELECT SUM(COALESCE(cost, 0)) FROM t_total_cost;").fetchone()
        if row is None or row[0] is None:
            return None
        return float(row[0])
    finally:
        conn.close()


def _delta(py_cost: float, aps_cost: float | None) -> tuple[float | None, float | None]:
    if aps_cost is None:
        return None, None
    abs_delta = round(py_cost - aps_cost, 6)
    rel_delta = None if abs(aps_cost) < 1e-12 else round(abs_delta / aps_cost, 6)
    return abs_delta, rel_delta


def build_parity_report(
    db_path: str | Path,
    *,
    machine_no: str | None = None,
    max_orders: int | None = None,
    case: MGCase | None = None,
) -> MGParityReport:
    """Compare Python scorer output against APS aggregate output tables."""

    effective_case = case or load_mg_case(db_path, machine_no=machine_no, max_orders=max_orders)
    score = score_sequence(effective_case, effective_case.default_sequence)
    python_grouped = group_rule_costs(score.breakdown)
    aps_rule_costs = _read_aps_rule_costs(db_path)
    aps_total = _read_aps_total_cost(db_path)

    rule_names = sorted(set(python_grouped) | set(aps_rule_costs))
    rule_deltas: list[MGParityRuleDelta] = []
    for rule_name in rule_names:
        py_cost = round(float(python_grouped.get(rule_name, 0.0)), 6)
        aps_cost = aps_rule_costs.get(rule_name)
        if aps_cost is not None:
            aps_cost = round(float(aps_cost), 6)
        abs_delta, rel_delta = _delta(py_cost, aps_cost)
        rule_deltas.append(
            MGParityRuleDelta(
                rule_name=rule_name,
                python_cost=py_cost,
                aps_cost=aps_cost,
                abs_delta=abs_delta,
                rel_delta=rel_delta,
            )
        )

    total_abs_delta, total_rel_delta = _delta(score.total_cost, aps_total)
    notes: list[str] = []
    if effective_case.source_summary.get("connectables_source") != "db:t_connectables":
        notes.append(
            "t_connectables was not usable as order-id adjacency data; parity uses fallback task-attribute connectability."
        )
    if max_orders is not None or effective_case.source_summary.get("loaded_with_max_orders") is not None:
        notes.append("Parity report is scoped by max_orders and does not represent the full database.")
    if not aps_rule_costs:
        notes.append("No APS t_rules_cost baseline was found.")
    if aps_total is None:
        notes.append("No APS t_total_cost baseline was found.")

    return MGParityReport(
        case_summary=effective_case.summary(),
        sequence_source="t_process_output active order_mac_sequence",
        python_total=score.total_cost,
        aps_total=round(aps_total, 6) if aps_total is not None else None,
        total_abs_delta=total_abs_delta,
        total_rel_delta=total_rel_delta,
        rule_deltas=rule_deltas,
        notes=notes,
    )


def summarize_parity_report(report: MGParityReport) -> dict[str, Any]:
    payload = report.to_dict()
    payload["largest_abs_rule_deltas"] = sorted(
        [
            item
            for item in payload["rule_deltas"]
            if item["abs_delta"] is not None
        ],
        key=lambda item: abs(float(item["abs_delta"])),
        reverse=True,
    )[:5]
    return payload


def build_search_replacement_report(
    case: MGCase,
    *,
    modes: Iterable[str] = DEFAULT_SEARCH_MODES,
    seeds: Iterable[int] = (11,),
    budget_iterations: int = 80,
    generation_limit: int = 8,
    use_constructive_default: bool = False,
    progress_logging: bool = False,
    progress_log_level: int | None = None,
    heuristic_cost_logging: bool = True,
    heuristic_cost_logging_policy: str = "improved",
) -> dict[str, Any]:
    """Build migration diagnostics around the actual OptAgent search result.

    The solve itself is delegated to `search.solve_mg_sequence(...)`. This
    wrapper adds APS baseline context so search quality can be compared against
    the legacy GA output without coupling the solving layer to SQLite reports.
    """

    payload = solve_mg_sequence(
        case,
        modes=modes,
        seeds=seeds,
        budget_iterations=budget_iterations,
        generation_limit=generation_limit,
        use_constructive_default=use_constructive_default,
        progress_logging=progress_logging,
        progress_log_level=progress_log_level,
        heuristic_cost_logging=heuristic_cost_logging,
        heuristic_cost_logging_policy=heuristic_cost_logging_policy,
    )
    parity_report = build_parity_report(case.db_path, case=case)
    aps_total = parity_report.aps_total
    payload["aps_baseline"] = {
        "sequence_source": parity_report.sequence_source,
        "total_cost": aps_total,
        "rule_costs": {
            item.rule_name: item.aps_cost
            for item in parity_report.rule_deltas
            if item.aps_cost is not None
        },
        "notes": list(parity_report.notes),
    }
    payload["best"]["delta_vs_aps_total"] = None if aps_total is None else round(payload["best"]["total_cost"] - aps_total, 6)
    return payload


def summarize_structured_sequence(case: MGCase, sequence: list[int]) -> dict[str, Any]:
    """Summarize the adjacent-edge subset of a selected active sequence."""

    costs: dict[str, float] = {
        "MGDiscontinuable": 0.0,
        "MGSmooth": 0.0,
        "MGChangeRoller": 0.0,
        "MGHardCamp": 0.0,
        "structured_edge_total": 0.0,
    }
    edges: list[dict[str, Any]] = []
    edge_matrix = build_structured_edges(case)
    for position in range(1, len(sequence)):
        edge_payload = dict(edge_matrix[sequence[position - 1]][sequence[position]])
        edge_costs = dict(edge_payload.get("costs", {}))
        edge_payload["position"] = position
        edges.append(edge_payload)
        costs["MGDiscontinuable"] += float(edge_costs.get("MGDiscontinuable", 0.0))
        costs["MGSmooth"] += (
            float(edge_costs.get("MGSmooth.width", 0.0))
            + float(edge_costs.get("MGSmooth.thickness", 0.0))
            + float(edge_costs.get("MGSmooth.temp", 0.0))
        )
        costs["MGChangeRoller"] += float(edge_costs.get("MGChangeRoller", 0.0)) + float(edge_costs.get("MGChangeRoller.simple_risk", 0.0))
        costs["MGHardCamp"] += float(edge_costs.get("MGHardCamp", 0.0))
        costs["structured_edge_total"] += float(edge_costs.get("structured_edge_total", 0.0))

    rounded_costs = {name: round(value, 6) for name, value in costs.items()}
    return {
        "edge_count": len(edges),
        "costs": rounded_costs,
        "top_edges": sorted(
            edges,
            key=lambda item: float(item["costs"]["structured_edge_total"]),
            reverse=True,
        )[:10],
    }


def build_structured_report(case: MGCase, *, sequence: list[int] | None = None) -> dict[str, Any]:
    """Compare DAG-visible edge metadata with grouped blackbox rule costs."""

    selected_sequence = list(case.default_sequence if sequence is None else sequence)
    blackbox = score_sequence(case, selected_sequence)
    grouped_blackbox = group_rule_costs(blackbox.breakdown)
    structured_sequence = summarize_structured_sequence(case, blackbox.active_sequence)
    edge_matrix = build_structured_edges(case)
    non_self_edges = max(0, len(case.tasks) * (len(case.tasks) - 1))
    non_connectable_edges = sum(
        1
        for row in edge_matrix
        for edge in row
        if not edge.get("disabled") and int(edge.get("connectable", 1)) == 0
    )
    structured_costs = structured_sequence["costs"]
    comparable = {
        rule: {
            "structured_cost": structured_costs.get(rule, 0.0),
            "blackbox_grouped_cost": grouped_blackbox.get(rule, 0.0),
            "delta": round(structured_costs.get(rule, 0.0) - grouped_blackbox.get(rule, 0.0), 6),
        }
        for rule in STRUCTURED_EDGE_RULES
    }

    return {
        "case": case.summary(),
        "structured_model": {
            "style": "sequence_edge_metadata_plus_blackbox_objective",
            "exact_lowering_status": "metadata_only",
            "structured_edge_rules": list(STRUCTURED_EDGE_RULES),
            "stateful_blackbox_rules": list(STATEFUL_BLACKBOX_RULES),
            "edge_count": non_self_edges,
            "non_connectable_edge_count": non_connectable_edges,
            "coverage_note": (
                "Stable adjacent-pair semantics are exposed as DAG-visible metadata; "
                "active-prefix and multi-edge campaign rules remain in the blackbox scorer."
            ),
        },
        "sequence": {
            "source": "active prefix of selected sequence",
            "selected_length": len(selected_sequence),
            "active_length": len(blackbox.active_sequence),
            "inactive_length": len(blackbox.inactive_sequence),
            "active_sequence_head": list(blackbox.active_sequence[:30]),
        },
        "structured_sequence": structured_sequence,
        "blackbox": {
            "total_cost": blackbox.total_cost,
            "grouped_rule_costs": grouped_blackbox,
            "diagnostics": blackbox.diagnostics,
        },
        "comparable_rule_deltas": comparable,
    }


def run_production_case(
    db_path: str | Path,
    *,
    machine_no: str | None = None,
    max_orders: int | None = None,
    modes: Iterable[str] = DEFAULT_SEARCH_MODES,
    seeds: Iterable[int] = (11,),
    budget_iterations: int = 80,
    generation_limit: int = 8,
    use_constructive_default: bool = False,
    output_db_path: str | Path | None = None,
    json_output: str | Path | None = None,
    dry_run: bool = False,
    write_legacy_compat: bool = False,
    progress_logging: bool = False,
    progress_log_level: int | None = None,
    heuristic_cost_logging: bool = True,
    heuristic_cost_logging_policy: str = "improved",
) -> dict[str, Any]:
    """Run the SQLite model phase and write auditable OptAgent output tables.

    This is the callable used by `program/main.py`. Its default behavior is the
    production path: load one SQLite case, solve it, and write `o_mg_optagent_*`
    tables back to that same database unless an explicit output path is passed
    by a migration test.
    """

    case = load_mg_case(db_path, machine_no=machine_no, max_orders=max_orders)
    report = build_search_replacement_report(
        case,
        modes=modes,
        seeds=seeds,
        budget_iterations=budget_iterations,
        generation_limit=generation_limit,
        use_constructive_default=use_constructive_default,
        progress_logging=progress_logging,
        progress_log_level=progress_log_level,
        heuristic_cost_logging=heuristic_cost_logging,
        heuristic_cost_logging_policy=heuristic_cost_logging_policy,
    )
    best_score = score_sequence(case, report["best"]["sequence"])
    structured = build_structured_report(case, sequence=report["best"]["sequence"])
    target_db_path = str(Path(output_db_path or case.db_path).expanduser().resolve())
    notes: list[str] = []
    if case.source_summary.get("connectables_source") != "db:t_connectables":
        notes.append("connectability used fallback task-attribute rules; production parity requires validating upstream t_connectables.")
    if max_orders is not None:
        notes.append("run was scoped by max_orders and does not represent the full database.")
    if dry_run:
        notes.append("dry_run=true; SQLite output tables were not written.")

    payload = {
        **report,
        "integration": {
            "status": "dry_run" if dry_run else "written",
            "dry_run": dry_run,
            "input_db_path": str(Path(db_path).expanduser().resolve()),
            "output_db_path": target_db_path,
            "output_tables": [
                "o_mg_optagent_sequence",
                "o_mg_optagent_rule_cost",
                "o_mg_optagent_run_manifest",
                "o_mg_optagent_diagnostics",
                "o_mg_optagent_search_run",
            ],
            "legacy_compatibility_tables": [
                "o_process_output_optagent",
                "o_rules_cost_optagent",
            ] if write_legacy_compat else [],
            "notes": notes,
        },
        "best_score": {
            "total_cost": best_score.total_cost,
            "breakdown": best_score.breakdown,
            "diagnostics": best_score.diagnostics,
        },
        "structured": {
            "structured_model": structured["structured_model"],
            "comparable_rule_deltas": structured["comparable_rule_deltas"],
        },
    }

    if not dry_run:
        # `o_mg_optagent_*` is the primary migration contract. Legacy-compatible
        # tables are optional and suffixed so validation does not overwrite
        # existing downstream output tables.
        write_production_output_tables(case, payload, output_db_path=target_db_path)
        if write_legacy_compat:
            write_legacy_compatibility_tables(case, output_db_path=target_db_path)
    if json_output:
        write_summary_json(payload, json_output)
    return payload
