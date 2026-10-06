import json
from pathlib import Path

from modules.pipeline_status import kr_producer_status, session_status
from multi_agent.tools.run_primary_market_session_ops import mark_session_state, SESSION_SPECS
from datetime import datetime, timezone


def write(root, name, value):
    path = root / "runtime_state" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_real_scheduler_schema_is_consumed_and_failure_exposed(tmp_path):
    state = {}
    spec = next(s for s in SESSION_SPECS if s.session_id == "kr_regular_close")
    mark_session_state(state, spec=spec, now_utc=datetime(2026, 10, 6, tzinfo=timezone.utc),
                       report={"status": "failed", "report_path": "/old/repo/batch.json"})
    state["runs"]["2026-10-07::kr_regular_close"] = {
        "session_id": spec.session_id, "recorded_at": "2099-01-01", "status": "ok", "dry_run": True}
    write(tmp_path, "long_term/ops/primary_market_session_state.json", state)
    write(tmp_path, "reports/ops/batch.json", {"commands": [{"name": "primary_daily_ops", "returncode": 9,
          "stdout_tail": "[OK] scan\n[FAILED] vintage_manifest(rc=1)"}]})
    result = session_status(tmp_path)
    assert result["session_error"] is None
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["id"] == spec.session_id
    assert result["sessions"][0]["status"] == "failed"
    assert result["sessions"][0]["failures"][0]["details"] == ["[FAILED] vintage_manifest(rc=1)"]


def test_absent_or_bad_evidence_never_reports_healthy(tmp_path):
    assert session_status(tmp_path)["session_error"]
    assert all(r["status"] == "error" for r in kr_producer_status(tmp_path))
    write(tmp_path, "reports/experimental/kr_swing_candidate_latest.json", [])
    assert kr_producer_status(tmp_path, lane="kospi_swing")[0]["status"] == "error"


def test_empty_run_is_distinct_from_missing_or_stale_run(tmp_path):
    write(tmp_path, "reports/experimental/kr_swing_candidate_latest.json", {
        "as_of": "2026-10-06", "picks": [], "gate": {"KOSPI": {
            "gate": "ABSTAIN", "fire": False, "gate_kind": "mkt_weakness",
            "gate_mkt_ret5": 2.4999, "gate_threshold": 0.5071}}})
    status = kr_producer_status(tmp_path, lane="kospi_swing", daily_date="2026-10-06")[0]
    assert status["status"] == "abstain" and "2.4999" in status["reason"]
    assert kr_producer_status(tmp_path, lane="kospi_swing", daily_date="2026-10-07")[0]["status"] == "stale"
    write(tmp_path, "reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json",
          {"trade_date": "20261006", "scored_rows": 216, "picks": []})
    status = kr_producer_status(tmp_path, lane="kosdaq_intraday", daily_date="2026-10-06")[0]
    assert status["status"] == "no_candidates" and status["scored_rows"] == 216


def test_current_session_wins_over_old_session(tmp_path):
    write(tmp_path, "long_term/ops/primary_market_session_state.json", {"runs": {
        "2026-10-05::kr_regular_close": {"recorded_at": "2026-10-05T10:00:00", "status": "ok"},
        "2026-10-06::kr_regular_close": {"recorded_at": "2026-10-06T10:00:00", "status": "failed"}}})
    assert session_status(tmp_path)["sessions"][0]["status"] == "failed"
