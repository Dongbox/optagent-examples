from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from examples.mg.program.model.rules import group_rule_costs, score_sequence
from examples.mg.program.scripts.preprocess.data import MGCase, MGScore, load_mg_case


def summarize_solution(case: MGCase, sequence: list[int], *, solver_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    score = score_sequence(case, sequence)
    active_orders = [case.tasks[index] for index in score.active_sequence]
    return {
        "case": case.summary(),
        "score": {
            "total_cost": score.total_cost,
            "breakdown": score.breakdown,
            "diagnostics": score.diagnostics,
        },
        "active_sequence": [
            {
                "position": position,
                "task_index": task.index,
                "order_id": task.order_id,
                "order_no": task.order_no,
                "weight": task.weight,
                "width": task.width,
                "thickness": task.thickness,
                "temp": task.temp,
            }
            for position, task in enumerate(active_orders)
        ],
        "sequence_head": list(sequence[:30]),
        "solver": solver_metadata or {},
    }


def write_summary_json(payload: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_output_tables(case: MGCase, score: MGScore, *, output_db_path: str | Path | None = None) -> None:
    """Write the primary OptAgent sequence and rule-cost output tables."""

    db_path = Path(output_db_path or case.db_path).expanduser().resolve()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS o_mg_optagent_sequence;")
        conn.execute("DROP TABLE IF EXISTS o_mg_optagent_rule_cost;")
        conn.execute(
            """
            CREATE TABLE o_mg_optagent_sequence (
                position INTEGER,
                task_index INTEGER,
                order_id INTEGER,
                order_no TEXT,
                active INTEGER,
                arranged_weight REAL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE o_mg_optagent_rule_cost (
                rule_name TEXT,
                cost REAL
            );
            """
        )
        arranged_weight = 0.0
        for position, task_index in enumerate(score.active_sequence):
            task = case.tasks[task_index]
            arranged_weight += task.weight
            conn.execute(
                "INSERT INTO o_mg_optagent_sequence VALUES (?, ?, ?, ?, ?, ?);",
                (position, task.index, task.order_id, task.order_no, 1, arranged_weight),
            )
        for position, task_index in enumerate(score.inactive_sequence, start=len(score.active_sequence)):
            task = case.tasks[task_index]
            conn.execute(
                "INSERT INTO o_mg_optagent_sequence VALUES (?, ?, ?, ?, ?, ?);",
                (position, task.index, task.order_id, task.order_no, 0, arranged_weight),
            )
        for name, cost in score.breakdown.items():
            conn.execute("INSERT INTO o_mg_optagent_rule_cost VALUES (?, ?);", (name, float(cost)))
        conn.execute("INSERT INTO o_mg_optagent_rule_cost VALUES (?, ?);", ("total", float(score.total_cost)))
        conn.commit()
    finally:
        conn.close()


def write_production_output_tables(
    case: MGCase,
    payload: dict[str, Any],
    *,
    output_db_path: str | Path | None = None,
) -> None:
    """Write production outputs plus manifest/diagnostics/search audit tables."""

    best = payload["best"]
    sequence = [int(index) for index in best["sequence"]]
    score = score_sequence(case, sequence)
    db_path = Path(output_db_path or case.db_path).expanduser().resolve()
    write_output_tables(case, score, output_db_path=db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS o_mg_optagent_run_manifest;")
        conn.execute("DROP TABLE IF EXISTS o_mg_optagent_diagnostics;")
        conn.execute("DROP TABLE IF EXISTS o_mg_optagent_search_run;")
        conn.execute(
            """
            CREATE TABLE o_mg_optagent_run_manifest (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE o_mg_optagent_diagnostics (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE o_mg_optagent_search_run (
                rank INTEGER,
                mode TEXT,
                seed INTEGER,
                total_cost REAL,
                improvement_vs_baseline REAL,
                feasible INTEGER,
                status TEXT,
                runtime_seconds REAL,
                active_count INTEGER,
                inactive_count INTEGER,
                solver_trace_count INTEGER,
                generation_trace_count INTEGER,
                sequence_json TEXT,
                grouped_rule_costs_json TEXT
            );
            """
        )

        manifest = {
            "integration_status": payload["integration"]["status"],
            "dry_run": payload["integration"]["dry_run"],
            "output_db_path": str(db_path),
            "machine_no": case.machine_no,
            "task_count": len(case.tasks),
            "connectables_source": case.source_summary.get("connectables_source"),
            "selected_mode": best["mode"],
            "selected_seed": best["seed"],
            "best_total_cost": best["total_cost"],
            "baseline_total_cost": payload["baseline"]["total_cost"],
            "aps_total_cost": payload["aps_baseline"]["total_cost"],
            "delta_vs_aps_total": best.get("delta_vs_aps_total"),
            "run_count": payload["search"]["run_count"],
            "budget_iterations": payload["search"]["budget_iterations"],
            "generation_limit": payload["search"]["generation_limit"],
        }
        for key, value in manifest.items():
            conn.execute(
                "INSERT INTO o_mg_optagent_run_manifest VALUES (?, ?);",
                (key, json.dumps(value, ensure_ascii=False)),
            )

        diagnostics = {
            "score_diagnostics": score.diagnostics,
            "grouped_rule_costs": group_rule_costs(score.breakdown),
            "aps_notes": payload["aps_baseline"].get("notes", []),
            "production_notes": payload["integration"].get("notes", []),
        }
        for key, value in diagnostics.items():
            conn.execute(
                "INSERT INTO o_mg_optagent_diagnostics VALUES (?, ?);",
                (key, json.dumps(value, ensure_ascii=False)),
            )

        for rank, run in enumerate(payload["runs"], start=1):
            conn.execute(
                """
                INSERT INTO o_mg_optagent_search_run VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rank,
                    run["mode"],
                    int(run["seed"]),
                    float(run["total_cost"]),
                    float(run["improvement_vs_baseline"]),
                    int(bool(run["feasible"])),
                    run["status"],
                    float(run["runtime_seconds"]),
                    int(run["active_count"]),
                    int(run["inactive_count"]),
                    int(run["solver_trace_count"]),
                    int(run["generation_trace_count"]),
                    json.dumps(run["sequence"], ensure_ascii=False),
                    json.dumps(run["grouped_rule_costs"], ensure_ascii=False),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def write_legacy_compatibility_tables(
    case: MGCase,
    *,
    output_db_path: str | Path | None = None,
    sequence_table: str = "o_process_output_optagent",
    rule_cost_table: str = "o_rules_cost_optagent",
) -> None:
    """Map OptAgent outputs to suffixed compatibility tables for old consumers."""

    db_path = Path(output_db_path or case.db_path).expanduser().resolve()
    conn = sqlite3.connect(db_path)
    try:
        sequence_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='o_mg_optagent_sequence';"
        ).fetchone()
        rule_cost_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='o_mg_optagent_rule_cost';"
        ).fetchone()
        if sequence_exists is None or rule_cost_exists is None:
            raise ValueError("o_mg_optagent_sequence and o_mg_optagent_rule_cost must exist before compatibility mapping")

        conn.execute(f"DROP TABLE IF EXISTS {sequence_table};")
        conn.execute(f"DROP TABLE IF EXISTS {rule_cost_table};")
        conn.execute(
            f"""
            CREATE TABLE {sequence_table} (
                order_id INTEGER,
                process_id INTEGER,
                machine_no TEXT,
                active INTEGER,
                order_mac_sequence INTEGER,
                source_table TEXT
            );
            """
        )
        conn.execute(
            f"""
            CREATE TABLE {rule_cost_table} (
                rule_name TEXT,
                cost REAL,
                source_table TEXT
            );
            """
        )
        conn.execute(
            f"""
            INSERT INTO {sequence_table}
            SELECT order_id, 0, ?, active, position, 'o_mg_optagent_sequence'
            FROM o_mg_optagent_sequence
            ORDER BY position;
            """,
            (case.machine_no,),
        )
        conn.execute(
            f"""
            INSERT INTO {rule_cost_table}
            SELECT rule_name, cost, 'o_mg_optagent_rule_cost'
            FROM o_mg_optagent_rule_cost
            ORDER BY rule_name;
            """
        )
        conn.commit()
    finally:
        conn.close()


def run_postprocess(
    db_path: str,
    *,
    machine_no: str | None = None,
    sequence_table: str = "o_process_output_optagent",
    rule_cost_table: str = "o_rules_cost_optagent",
) -> dict[str, str]:
    case = load_mg_case(db_path, machine_no=machine_no)
    write_legacy_compatibility_tables(
        case,
        output_db_path=db_path,
        sequence_table=sequence_table,
        rule_cost_table=rule_cost_table,
    )
    return {
        "status": "written",
        "db_path": str(Path(db_path).expanduser().resolve()),
        "sequence_table": sequence_table,
        "rule_cost_table": rule_cost_table,
    }
