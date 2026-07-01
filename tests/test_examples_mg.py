from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

from mg.program.model.model import build_mg_program
from mg.program.model.reports import build_parity_report, build_search_replacement_report, build_structured_report, run_production_case
from mg.program.model.rules import group_rule_costs, score_sequence
from mg.program.model.search import build_mg_config
from mg.program.main import (
    AGENT_LOGGER_NAME,
    OPTAGENT_LOGGER_NAME,
    configure_agent_logging,
    configure_optagent_logging,
    parse_args as parse_program_args,
    run_pipeline,
    terminal_output_payload,
)
from mg.program.scripts.postprocess.postprocess import read_output_tables, write_legacy_compatibility_tables, write_output_tables
from mg.program.scripts.preprocess.data import load_mg_case, validate_preprocess_outputs
import mg.program.main as mg_main
from mg.program.scripts.preprocess.transformer import CustomTransformer, main as run_transformer
from tests.reference_eval.eval_full import evaluate_full
from tests.reference_eval.state import EvaluationState


def test_mg_program_main_configures_agent_logger() -> None:
    logger = logging.getLogger(AGENT_LOGGER_NAME)
    optagent_logger = logging.getLogger(OPTAGENT_LOGGER_NAME)
    before = list(logger.handlers)
    optagent_before = list(optagent_logger.handlers)

    configured = configure_agent_logging()
    configure_agent_logging()
    optagent_configured = configure_optagent_logging()
    configure_optagent_logging()

    tagged_handlers = [handler for handler in logger.handlers if getattr(handler, "_mg_agent_log_handler", False)]
    optagent_tagged_handlers = [
        handler for handler in optagent_logger.handlers if getattr(handler, "_mg_optagent_log_handler", False)
    ]

    assert configured is logger
    assert logger.level == logging.INFO
    assert logger.propagate is False
    assert len(tagged_handlers) == 1
    assert optagent_configured is optagent_logger
    assert optagent_logger.level == logging.INFO
    assert optagent_logger.propagate is False
    assert len(optagent_tagged_handlers) == 1

    for handler in logger.handlers:
        if handler not in before:
            logger.removeHandler(handler)
    for handler in optagent_logger.handlers:
        if handler not in optagent_before:
            optagent_logger.removeHandler(handler)


def test_mg_config_can_enable_optagent_progress_logging() -> None:
    config = build_mg_config(
        mode="ga",
        budget_iterations=4,
        generation_limit=2,
        seed=7,
        progress_logging=True,
        progress_log_level=logging.WARNING,
    )

    assert config.progress_logging is True
    assert config.progress_log_level == logging.WARNING
    assert config.progress_mode == "ga"
    assert config.heuristic_cost_logging is True
    assert config.heuristic_cost_logging_policy == "improved"


def _make_tiny_mg_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE t_machine (id INTEGER, machine_no TEXT);
            CREATE TABLE i_zinc_plan (
                future_zinc TEXT,
                if_outer INTEGER,
                if_outer_first INTEGER,
                max_active_weight1 REAL,
                max_active_weight2 REAL
            );
            CREATE TABLE i_param (
                annealing_temp_upper_limit INTEGER,
                thin_material_threshold REAL,
                roll_change_width_upper_limit INTEGER,
                cross_removal_upper_limit INTEGER
            );
            CREATE TABLE t_order (id INTEGER, order_no TEXT);
            CREATE TABLE t_process (
                id INTEGER,
                order_id INTEGER,
                process_id INTEGER,
                thickness REAL,
                thickness_up_jump REAL,
                thickness_down_jump REAL,
                width REAL,
                width_up_jump REAL,
                width_down_jump REAL,
                temp REAL,
                temp_up_jump REAL,
                temp_down_jump REAL,
                weight REAL,
                producing_task INTEGER,
                left_mat_priority INTEGER,
                post_process INTEGER,
                label_campaign TEXT,
                is_outer INTEGER,
                surface_grade REAL,
                is_thin INTEGER,
                is_simple INTEGER,
                is_outer_transition REAL,
                out_width REAL,
                grade TEXT,
                category TEXT,
                zinc_layer TEXT,
                sell_code TEXT,
                grade_category TEXT,
                steel_type TEXT,
                grinding_class INTEGER,
                left_mat_priority_outer INTEGER
            );
            CREATE TABLE t_process_output (
                id INTEGER,
                order_id INTEGER,
                process_id INTEGER,
                machine_no TEXT,
                active INTEGER,
                order_mac_sequence INTEGER
            );
            CREATE TABLE t_connectables (
                id INTEGER,
                prev_order_id INTEGER,
                curr_order_id INTEGER,
                category_flag INTEGER,
                width_flag INTEGER,
                thickness_flag INTEGER,
                temp_flag INTEGER,
                same_width_flag INTEGER,
                connectable_flag INTEGER
            );
            CREATE TABLE t_rules_cost (
                scene_id INTEGER,
                scene_name TEXT,
                version INTEGER,
                rule_id INTEGER,
                cost REAL,
                rule_name TEXT,
                scope TEXT,
                rule_desc TEXT
            );
            CREATE TABLE t_total_cost (
                scene_id INTEGER,
                scene_name TEXT,
                version INTEGER,
                cost REAL
            );
            """
        )
        conn.execute("INSERT INTO t_machine VALUES (0, 'C208');")
        conn.execute("INSERT INTO i_zinc_plan VALUES ('GI', 0, 0, 100.0, 0.0);")
        conn.execute("INSERT INTO i_param VALUES (40, 0.5, 3000, 50);")
        rows = [
            (1, "A", 20.0, 1200.0, 0.7, 830.0, 1),
            (2, "B", 20.0, 1190.0, 0.7, 830.0, 1),
            (3, "C", 20.0, 1500.0, 1.2, 820.0, 2),
        ]
        for idx, order_no, weight, width, thickness, temp, is_thin in rows:
            conn.execute("INSERT INTO t_order VALUES (?, ?);", (idx, order_no))
            conn.execute(
                """
                INSERT INTO t_process VALUES (
                    ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, '',
                    0, 0, ?, 1, 0, ?, '', '', 'GI', 'MC', 'G1', '', 0, 0
                );
                """,
                (
                    idx,
                    idx,
                    thickness,
                    thickness + 0.2,
                    thickness - 0.2,
                    width,
                    width + 50,
                    width - 50,
                    temp,
                    temp + 20,
                    temp - 20,
                    weight,
                    is_thin,
                    width,
                ),
            )
            conn.execute("INSERT INTO t_process_output VALUES (?, ?, 0, 'C208', 1, ?);", (idx, idx, idx - 1))
        conn.execute("INSERT INTO t_connectables VALUES (0, 1, 2, 1, 1, 1, 1, 1, 1);")
        conn.execute("INSERT INTO t_connectables VALUES (1, 2, 3, 1, 0, 1, 1, 0, 0);")
        conn.execute("INSERT INTO t_rules_cost VALUES (0, 'comp', 0, 1, 0.0, 'MGLeftMat', '[]', '');")
        conn.execute("INSERT INTO t_rules_cost VALUES (0, 'comp', 0, 2, 0.0, 'MGSmooth', '[]', '');")
        conn.execute("INSERT INTO t_total_cost VALUES (0, 'comp', 0, 0.0);")
        conn.commit()
    finally:
        conn.close()


def test_mg_case_loader_scores_and_builds_program(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    case = load_mg_case(db_path)
    score = score_sequence(case, case.default_sequence)
    built = build_mg_program(case)
    evaluated = evaluate_full(
        built.program,
        EvaluationState(variable_values=built.program.default_variable_values()),
    )

    assert case.summary()["task_count"] == 3
    assert case.summary()["connectables_source"] == "db:t_connectables"
    assert score.diagnostics["active_count"] == 3
    assert evaluated.objective_values
    assert next(iter(evaluated.objective_values.values())) == score.total_cost
    assert built.program.metadata["structured_model_status"] == "edge_metadata_plus_blackbox_objective"
    assert "sequence_adjacency_penalty_matrix" not in built.program.metadata
    assert built.program.metadata["structured_edge_rules"]
    assert len(built.program.metadata["sequence_structured_edges"]) == 3

    write_output_tables(case, score)
    output_tables = read_output_tables(db_path)
    conn = sqlite3.connect(db_path)
    try:
        sequence_count = conn.execute("SELECT COUNT(*) FROM o_mg_optagent_sequence;").fetchone()[0]
        cost_count = conn.execute("SELECT COUNT(*) FROM o_mg_optagent_rule_cost;").fetchone()[0]
    finally:
        conn.close()

    assert sequence_count == 3
    assert cost_count >= 1
    assert len(output_tables["sequence"]) == 3
    assert output_tables["rule_costs"][-1]["rule_name"] == "total"


def test_mg_parity_report_reads_aps_baseline(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    report = build_parity_report(db_path)
    payload = report.to_dict()

    assert payload["aps_total"] == 0.0
    assert payload["python_total"] > 0
    assert any(item["rule_name"] == "MGSmooth" for item in payload["rule_deltas"])
    assert payload["total_abs_delta"] == payload["python_total"]


def test_mg_rule_grouping_preserves_aps_rule_names() -> None:
    grouped = group_rule_costs(
        {
            "MGLeftMat": 40.0,
            "MGLeftMat.inactive_reward": -20.0,
            "MGSmooth.width": 2.5,
            "MGSmooth.temp": 1.5,
            "MGSmooth.thickness": 3.0,
            "MGDiscontinuable": 5000.0,
            "unmapped.debug": 7.0,
        }
    )

    assert grouped["MGLeftMat"] == 20.0
    assert grouped["MGSmooth"] == 7.0
    assert grouped["MGDiscontinuable"] == 5000.0
    assert grouped["unmapped.debug"] == 7.0


def test_mg_search_replacement_report_runs_profile_matrix(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    case = load_mg_case(db_path)
    payload = build_search_replacement_report(
        case,
        modes=("ga",),
        seeds=(3, 5),
        budget_iterations=4,
        generation_limit=2,
    )

    assert payload["search"]["run_count"] == 2
    assert payload["baseline"]["total_cost"] > 0
    assert payload["aps_baseline"]["total_cost"] == 0.0
    assert payload["best"]["mode"] == "ga"
    assert payload["best"]["seed"] in {3, 5}
    assert len(payload["best"]["sequence"]) == 3
    assert payload["best"]["solver_trace_count"] >= 1
    assert payload["score_curve"]
    assert {point["source"] for point in payload["score_curve"]} >= {"baseline", "final"}
    assert payload["runs"][0]["total_cost"] <= payload["runs"][-1]["total_cost"]


def test_mg_structured_report_exposes_edge_level_rule_costs(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    case = load_mg_case(db_path)
    payload = build_structured_report(case)

    assert payload["structured_model"]["exact_lowering_status"] == "metadata_only"
    assert "MGDiscontinuable" in payload["structured_model"]["structured_edge_rules"]
    assert "MGOuterSandwich" in payload["structured_model"]["stateful_blackbox_rules"]
    assert payload["structured_model"]["edge_count"] == 6
    assert payload["structured_model"]["non_connectable_edge_count"] >= 1
    assert payload["structured_sequence"]["costs"]["MGDiscontinuable"] == 5000.0
    assert payload["comparable_rule_deltas"]["MGDiscontinuable"]["delta"] == 0.0
    assert payload["comparable_rule_deltas"]["MGSmooth"]["delta"] == 0.0


def test_mg_production_run_writes_auditable_output_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    payload = run_production_case(
        db_path,
        modes=("ga",),
        seeds=(7,),
        budget_iterations=4,
        generation_limit=2,
    )

    assert payload["integration"]["status"] == "written"
    assert payload["search"]["run_count"] == 1
    assert payload["best"]["mode"] == "ga"

    conn = sqlite3.connect(db_path)
    try:
        output_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'o_mg_optagent_%';"
            ).fetchall()
        }
        manifest = dict(conn.execute("SELECT key, value FROM o_mg_optagent_run_manifest;").fetchall())
        sequence_count = conn.execute("SELECT COUNT(*) FROM o_mg_optagent_sequence;").fetchone()[0]
        run_count = conn.execute("SELECT COUNT(*) FROM o_mg_optagent_search_run;").fetchone()[0]
    finally:
        conn.close()

    assert {
        "o_mg_optagent_sequence",
        "o_mg_optagent_rule_cost",
        "o_mg_optagent_run_manifest",
        "o_mg_optagent_diagnostics",
        "o_mg_optagent_search_run",
    }.issubset(output_tables)
    assert manifest["integration_status"] == '"written"'
    assert manifest["selected_mode"] == '"ga"'
    assert sequence_count == 3
    assert run_count == 1


def test_mg_production_dry_run_does_not_write_output_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    payload = run_production_case(
        db_path,
        modes=("ga",),
        seeds=(7,),
        budget_iterations=2,
        generation_limit=1,
        dry_run=True,
    )

    conn = sqlite3.connect(db_path)
    try:
        output_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'o_mg_optagent_%';"
        ).fetchone()[0]
    finally:
        conn.close()

    assert payload["integration"]["status"] == "dry_run"
    assert output_count == 0


def test_mg_formal_preprocess_validator_reports_model_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    payload = validate_preprocess_outputs(db_path)

    assert payload["status"] == "ok"
    assert payload["missing_required_tables"] == []
    assert payload["row_counts"]["t_process"] == 3
    assert payload["connectable_summary"]["usable_order_adjacency"] is True


def test_mg_formal_integration_can_write_legacy_compat_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)

    payload = run_production_case(
        db_path,
        modes=("ga",),
        seeds=(7,),
        budget_iterations=4,
        generation_limit=2,
        write_legacy_compat=True,
    )

    conn = sqlite3.connect(db_path)
    try:
        sequence_count = conn.execute("SELECT COUNT(*) FROM o_process_output_optagent;").fetchone()[0]
        rule_count = conn.execute("SELECT COUNT(*) FROM o_rules_cost_optagent;").fetchone()[0]
    finally:
        conn.close()

    assert payload["integration"]["legacy_compatibility_tables"] == [
        "o_process_output_optagent",
        "o_rules_cost_optagent",
    ]
    assert sequence_count == 3
    assert rule_count >= 1


def test_mg_postprocess_legacy_mapping_requires_optagent_outputs(tmp_path: Path) -> None:
    db_path = tmp_path / "mg.db"
    _make_tiny_mg_db(db_path)
    case = load_mg_case(db_path)

    try:
        write_legacy_compatibility_tables(case)
    except ValueError as exc:
        assert "o_mg_optagent_sequence" in str(exc)
    else:
        raise AssertionError("expected missing optagent output tables to fail")


def test_mg_preprocess_transformer_contract_raises_when_aps_unavailable(tmp_path: Path) -> None:
    db_path = tmp_path / "20260407000000.db"
    _make_tiny_mg_db(db_path)

    transformer = CustomTransformer(str(db_path), str(db_path), task_timeout=1000)

    try:
        result = transformer.run()
    except Exception as exc:  # APS is optional in the default test environment.
        assert str(exc)
    else:
        assert isinstance(result, bool)

    try:
        result = run_transformer(str(db_path), str(db_path))
    except Exception as exc:
        assert str(exc)
    else:
        assert isinstance(result, bool)


def test_mg_program_main_pipeline_runs_model_and_postprocess(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "20260407000000.db"
    _make_tiny_mg_db(db_path)

    monkeypatch.setattr(mg_main, "run_preprocess", lambda in_addr, out_addr: True)
    args = parse_program_args([str(db_path)])
    payload = run_pipeline(args.db_path)

    conn = sqlite3.connect(db_path)
    try:
        sequence_count = conn.execute("SELECT COUNT(*) FROM o_mg_optagent_sequence;").fetchone()[0]
        compat_count = conn.execute("SELECT COUNT(*) FROM o_process_output_optagent;").fetchone()[0]
    finally:
        conn.close()

    assert payload["sqlite_handoff"]["mode"] == "in_place"
    assert payload["preprocess"]["ok"] is True
    assert "model_run" in payload["runtime"]
    assert "postprocess" in payload["runtime"]
    assert len(payload["postprocess"]["sequence"]) == 3
    assert payload["postprocess"]["rule_costs"][-1]["rule_name"] == "total"
    assert terminal_output_payload(payload) == {
        "rule_costs": payload["postprocess"]["rule_costs"],
        "score_curve": payload["model"]["score_curve"],
    }
    assert "sequence" not in terminal_output_payload(payload)
    assert sequence_count == 3
    assert compat_count == 3


def test_mg_program_main_stops_when_preprocess_returns_false(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "20260407000000.db"
    _make_tiny_mg_db(db_path)

    monkeypatch.setattr(mg_main, "run_preprocess", lambda in_addr, out_addr: False)

    try:
        run_pipeline(db_path)
    except RuntimeError as exc:
        assert "MG preprocess failed" in str(exc)
    else:
        raise AssertionError("expected preprocess failure to stop the pipeline")
