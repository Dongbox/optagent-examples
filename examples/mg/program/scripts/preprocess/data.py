from __future__ import annotations

from dataclasses import dataclass, field
import sqlite3
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MGTask:
    index: int
    order_id: int
    order_no: str
    machine_no: str
    weight: float
    thickness: float
    thickness_up_jump: float
    thickness_down_jump: float
    width: float
    width_up_jump: float
    width_down_jump: float
    out_width: float
    temp: float
    temp_up_jump: float
    temp_down_jump: float
    post_process: int
    is_outer: int
    is_outer_transition: float
    is_thin: int
    is_simple: int
    grinding_class: int
    left_mat_priority: int
    left_mat_priority_outer: int
    surface_grade: float
    zinc_layer: str
    category: str
    grade: str
    grade_category: str
    sell_code: str


@dataclass(frozen=True)
class MGConnectableInfo:
    category_flag: int = 1
    width_flag: int = 1
    thickness_flag: int = 1
    temp_flag: int = 1
    same_width_flag: int = 1
    connectable_flag: int = 1


@dataclass(frozen=True)
class MGContextConfig:
    if_outer: int = 0
    max_active_weight1: float = 973.0
    max_active_weight2: float = 0.0
    if_outer_first: int = 0
    cross_removal_upper_limit: int = 50
    weight_delta: float = 20.0

    @property
    def active_weight_limit(self) -> float:
        return self.max_active_weight1 + self.max_active_weight2 + self.weight_delta


@dataclass(frozen=True)
class MGRuleWeights:
    left_mat: float = 20.0
    smooth_width: float = 0.5
    smooth_thickness: float = 1.0
    smooth_temp: float = 0.1
    discontinuable: float = 5000.0
    discontinuable_temp: float = 5000.0
    outer_sandwich: float = 1000.0
    hard_camp: float = 1.0
    outer_overwidth: float = 1.0
    outer_phase_violation: float = 10000.0
    thin_camp: float = 500.0
    post_process_camp: float = 400.0
    post_process_sandwich: float = 500.0
    change_roller: float = 200.0
    change_roller_simple: float = 100.0
    grinding_before_outer: float = 10.0


@dataclass
class MGCase:
    """Normalized in-memory view of the MG SQLite model contract."""

    db_path: str
    machine_no: str
    tasks: list[MGTask]
    connectables: dict[tuple[int, int], MGConnectableInfo]
    context: MGContextConfig
    rule_weights: MGRuleWeights
    default_sequence: list[int]
    source_summary: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        active_weight = sum(self.tasks[index].weight for index in self.default_sequence)
        return {
            "db_path": self.db_path,
            "machine_no": self.machine_no,
            "task_count": len(self.tasks),
            "connectable_edge_count": sum(1 for info in self.connectables.values() if info.connectable_flag),
            "default_sequence_length": len(self.default_sequence),
            "default_sequence_weight": round(active_weight, 3),
            "active_weight_limit": round(self.context.active_weight_limit, 3),
            **self.source_summary,
        }


@dataclass
class MGScore:
    total_cost: float
    active_sequence: list[int]
    inactive_sequence: list[int]
    breakdown: dict[str, float]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class MGParityRuleDelta:
    rule_name: str
    python_cost: float
    aps_cost: float | None
    abs_delta: float | None
    rel_delta: float | None


@dataclass
class MGParityReport:
    case_summary: dict[str, Any]
    sequence_source: str
    python_total: float
    aps_total: float | None
    total_abs_delta: float | None
    total_rel_delta: float | None
    rule_deltas: list[MGParityRuleDelta]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case_summary,
            "sequence_source": self.sequence_source,
            "python_total": self.python_total,
            "aps_total": self.aps_total,
            "total_abs_delta": self.total_abs_delta,
            "total_rel_delta": self.total_rel_delta,
            "rule_deltas": [
                {
                    "rule_name": item.rule_name,
                    "python_cost": item.python_cost,
                    "aps_cost": item.aps_cost,
                    "abs_delta": item.abs_delta,
                    "rel_delta": item.rel_delta,
                }
                for item in self.rule_deltas
            ],
            "notes": list(self.notes),
        }


STATIC_CONTEXT_DEFAULTS = {
    "if_outer": 0,
    "if_outer_first": 0,
    "max_active_weight1": 973.0,
    "max_active_weight2": 0.0,
    "cross_removal_upper_limit": 50,
}
REQUIRED_MODEL_TABLES = (
    "t_process",
    "t_order",
    "t_process_output",
    "t_connectables",
    "t_machine",
)
RECOMMENDED_INPUT_TABLES = (
    "i_zinc_plan",
    "i_param",
)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table});").fetchall()}


def _row_dicts(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    old_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.row_factory = old_factory


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(float(value))


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _load_context(conn: sqlite3.Connection) -> MGContextConfig:
    values = dict(STATIC_CONTEXT_DEFAULTS)
    if _table_exists(conn, "t_info"):
        rows = _row_dicts(conn, "SELECT * FROM t_info LIMIT 1;")
        if rows:
            values.update({key: rows[0].get(key, value) for key, value in values.items()})
    elif _table_exists(conn, "i_zinc_plan"):
        rows = _row_dicts(conn, "SELECT * FROM i_zinc_plan LIMIT 1;")
        if rows:
            values.update({key: rows[0].get(key, value) for key, value in values.items() if key in rows[0]})

    weight_delta = 20.0
    if _table_exists(conn, "i_param") and "cross_removal_upper_limit" in _columns(conn, "i_param"):
        rows = _row_dicts(conn, "SELECT * FROM i_param LIMIT 1;")
        if rows and rows[0].get("cross_removal_upper_limit") is not None:
            values["cross_removal_upper_limit"] = rows[0]["cross_removal_upper_limit"]

    return MGContextConfig(
        if_outer=_as_int(values.get("if_outer")),
        max_active_weight1=_as_float(values.get("max_active_weight1"), 973.0),
        max_active_weight2=_as_float(values.get("max_active_weight2")),
        if_outer_first=_as_int(values.get("if_outer_first")),
        cross_removal_upper_limit=_as_int(values.get("cross_removal_upper_limit"), 50),
        weight_delta=weight_delta,
    )


def _load_rule_weights(conn: sqlite3.Connection) -> MGRuleWeights:
    # Prefer aps.json-equivalent defaults. t_rules_cost in output DBs may be
    # post-run aggregate costs rather than rule parameters.
    return MGRuleWeights()


def _load_connectables(conn: sqlite3.Connection) -> dict[tuple[int, int], MGConnectableInfo]:
    if not _table_exists(conn, "t_connectables"):
        return {}
    rows = _row_dicts(conn, "SELECT * FROM t_connectables;")
    connectables: dict[tuple[int, int], MGConnectableInfo] = {}
    for row in rows:
        key = (_as_int(row.get("prev_order_id")), _as_int(row.get("curr_order_id")))
        connectables[key] = MGConnectableInfo(
            category_flag=_as_int(row.get("category_flag"), 1),
            width_flag=_as_int(row.get("width_flag"), 1),
            thickness_flag=_as_int(row.get("thickness_flag"), 1),
            temp_flag=_as_int(row.get("temp_flag"), 1),
            same_width_flag=_as_int(row.get("same_width_flag"), 1),
            connectable_flag=_as_int(row.get("connectable_flag"), 1),
        )
    return connectables


def _fallback_connectables(tasks: list[MGTask]) -> dict[tuple[int, int], MGConnectableInfo]:
    """Derive conservative adjacency when `t_connectables` has unusable IDs."""

    connectables: dict[tuple[int, int], MGConnectableInfo] = {}
    for prev in tasks:
        for curr in tasks:
            if prev.order_id == curr.order_id:
                continue
            width_flag = int(curr.width_down_jump <= prev.width <= curr.width_up_jump) if curr.width_up_jump or curr.width_down_jump else 1
            thickness_flag = (
                int(curr.thickness_down_jump <= prev.thickness <= curr.thickness_up_jump)
                if curr.thickness_up_jump or curr.thickness_down_jump
                else int(abs(prev.thickness - curr.thickness) <= 0.5)
            )
            temp_flag = (
                int(curr.temp_down_jump <= prev.temp <= curr.temp_up_jump)
                if curr.temp_up_jump or curr.temp_down_jump
                else int(abs(prev.temp - curr.temp) <= 3000)
            )
            category_flag = int((not prev.grade_category) or (not curr.grade_category) or prev.grade_category == curr.grade_category)
            same_width_flag = int(abs(prev.width - curr.width) <= 1e-9)
            connectables[(prev.order_id, curr.order_id)] = MGConnectableInfo(
                category_flag=category_flag,
                width_flag=width_flag,
                thickness_flag=thickness_flag,
                temp_flag=temp_flag,
                same_width_flag=same_width_flag,
                connectable_flag=int(width_flag and thickness_flag and temp_flag and category_flag),
            )
    return connectables


def _load_default_order_ids(conn: sqlite3.Connection, machine_no: str | None) -> list[int]:
    if not _table_exists(conn, "t_process_output"):
        return []
    where = "active=1"
    params: tuple[Any, ...] = ()
    if machine_no:
        where += " AND machine_no=?"
        params = (machine_no,)
    rows = _row_dicts(
        conn,
        f"""
        SELECT order_id
        FROM t_process_output
        WHERE {where}
        ORDER BY order_mac_sequence, id;
        """,
        params,
    )
    return [_as_int(row["order_id"]) for row in rows]


def _load_machine_no(conn: sqlite3.Connection, explicit_machine_no: str | None) -> str:
    if explicit_machine_no:
        return explicit_machine_no
    if _table_exists(conn, "t_machine"):
        rows = _row_dicts(conn, "SELECT machine_no FROM t_machine ORDER BY id LIMIT 1;")
        if rows:
            return _as_str(rows[0].get("machine_no"))
    rows = _row_dicts(
        conn,
        "SELECT machine_no FROM t_process_output WHERE machine_no IS NOT NULL GROUP BY machine_no ORDER BY COUNT(*) DESC LIMIT 1;",
    ) if _table_exists(conn, "t_process_output") else []
    return _as_str(rows[0].get("machine_no")) if rows else "MG"


def load_mg_case(
    db_path: str | Path,
    *,
    machine_no: str | None = None,
    max_orders: int | None = None,
) -> MGCase:
    """Load model-facing `t_*` tables produced by APS common preprocess."""

    path = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(path)
    try:
        effective_machine = _load_machine_no(conn, machine_no)
        task_rows = _row_dicts(
            conn,
            """
            SELECT
                p.*,
                o.order_no,
                COALESCE(po.machine_no, ?) AS machine_no
            FROM t_process p
            LEFT JOIN t_order o ON o.id = p.order_id
            LEFT JOIN t_process_output po ON po.order_id = p.order_id AND po.process_id = p.process_id
            GROUP BY p.order_id
            ORDER BY p.order_id;
            """,
            (effective_machine,),
        )
        default_order_ids = _load_default_order_ids(conn, effective_machine)
        context = _load_context(conn)
        rule_weights = _load_rule_weights(conn)
        connectables = _load_connectables(conn)
    finally:
        conn.close()

    if max_orders is not None and max_orders <= 0:
        raise ValueError("max_orders must be positive when provided")

    if max_orders is not None:
        preferred_order_ids = default_order_ids[:max_orders]
        if len(preferred_order_ids) < max_orders:
            seen = set(preferred_order_ids)
            for row in task_rows:
                order_id = row["order_id"]
                if order_id in seen:
                    continue
                preferred_order_ids.append(order_id)
                seen.add(order_id)
                if len(preferred_order_ids) >= max_orders:
                    break
        selected_order_ids = set(preferred_order_ids)
        task_rows = [row for row in task_rows if row["order_id"] in selected_order_ids]

    tasks: list[MGTask] = []
    for index, row in enumerate(task_rows):
        tasks.append(
            MGTask(
                index=index,
                order_id=_as_int(row.get("order_id")),
                order_no=_as_str(row.get("order_no")),
                machine_no=_as_str(row.get("machine_no") or effective_machine),
                weight=_as_float(row.get("weight")),
                thickness=_as_float(row.get("thickness")),
                thickness_up_jump=_as_float(row.get("thickness_up_jump")),
                thickness_down_jump=_as_float(row.get("thickness_down_jump")),
                width=_as_float(row.get("width")),
                width_up_jump=_as_float(row.get("width_up_jump")),
                width_down_jump=_as_float(row.get("width_down_jump")),
                out_width=_as_float(row.get("out_width")),
                temp=_as_float(row.get("temp")),
                temp_up_jump=_as_float(row.get("temp_up_jump")),
                temp_down_jump=_as_float(row.get("temp_down_jump")),
                post_process=_as_int(row.get("post_process")),
                is_outer=_as_int(row.get("is_outer")),
                is_outer_transition=_as_float(row.get("is_outer_transition")),
                is_thin=_as_int(row.get("is_thin")),
                is_simple=_as_int(row.get("is_simple")),
                grinding_class=_as_int(row.get("grinding_class")),
                left_mat_priority=_as_int(row.get("left_mat_priority")),
                left_mat_priority_outer=_as_int(row.get("left_mat_priority_outer")),
                surface_grade=_as_float(row.get("surface_grade")),
                zinc_layer=_as_str(row.get("zinc_layer")),
                category=_as_str(row.get("category")),
                grade=_as_str(row.get("grade")),
                grade_category=_as_str(row.get("grade_category")),
                sell_code=_as_str(row.get("sell_code")),
            )
        )

    distinct_connectable_orders = {
        order_id
        for edge in connectables
        for order_id in edge
    }
    connectables_source = "db:t_connectables"
    # Some real MG test DBs contain `t_connectables` rows whose order-id columns
    # are all zero. Treat those rows as unusable for adjacency and fall back to
    # task attributes while surfacing the source in reports.
    if len(distinct_connectable_orders) < max(2, min(len(tasks), 10)):
        connectables = _fallback_connectables(tasks)
        connectables_source = "fallback:task_attribute_rules"

    index_by_order_id = {task.order_id: task.index for task in tasks}
    default_sequence = [
        index_by_order_id[order_id]
        for order_id in default_order_ids
        if order_id in index_by_order_id
    ]
    default_sequence.extend(index for index in range(len(tasks)) if index not in set(default_sequence))

    return MGCase(
        db_path=str(path),
        machine_no=effective_machine,
        tasks=tasks,
        connectables=connectables,
        context=context,
        rule_weights=rule_weights,
        default_sequence=default_sequence,
        source_summary={
            "source_default_active_count": len(default_order_ids),
            "loaded_with_max_orders": max_orders,
            "connectables_source": connectables_source,
        },
    )


def validate_preprocess_outputs(db_path: str | Path) -> dict[str, Any]:
    """Validate that common preprocess produced the model tables we consume."""

    path = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(path)
    try:
        existing = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        missing_required = [table for table in REQUIRED_MODEL_TABLES if table not in existing]
        missing_recommended = [table for table in RECOMMENDED_INPUT_TABLES if table not in existing]
        row_counts = {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0])
            for table in REQUIRED_MODEL_TABLES
            if table in existing
        }
        connectable_summary: dict[str, Any] = {}
        if "t_connectables" in existing:
            row = conn.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT prev_order_id),
                    COUNT(DISTINCT curr_order_id),
                    MIN(prev_order_id),
                    MAX(prev_order_id),
                    MIN(curr_order_id),
                    MAX(curr_order_id)
                FROM t_connectables;
                """
            ).fetchone()
            connectable_summary = {
                "row_count": int(row[0] or 0),
                "distinct_prev_order_id": int(row[1] or 0),
                "distinct_curr_order_id": int(row[2] or 0),
                "min_prev_order_id": row[3],
                "max_prev_order_id": row[4],
                "min_curr_order_id": row[5],
                "max_curr_order_id": row[6],
                "usable_order_adjacency": bool((row[1] or 0) > 1 and (row[2] or 0) > 1),
            }
    finally:
        conn.close()

    status = "ok" if not missing_required else "missing_required_tables"
    notes: list[str] = []
    if missing_recommended:
        notes.append("recommended i_* configuration tables are missing; loader may fall back to defaults")
    if connectable_summary and not connectable_summary["usable_order_adjacency"]:
        notes.append("t_connectables does not expose usable order adjacency; model loader will use fallback connectability")
    return {
        "db_path": str(path),
        "status": status,
        "required_model_tables": list(REQUIRED_MODEL_TABLES),
        "missing_required_tables": missing_required,
        "recommended_input_tables": list(RECOMMENDED_INPUT_TABLES),
        "missing_recommended_tables": missing_recommended,
        "row_counts": row_counts,
        "connectable_summary": connectable_summary,
        "notes": notes,
    }
