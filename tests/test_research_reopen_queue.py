import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from multi_agent.tools import research_reopen_queue as queue


def setup_queue(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(queue, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(queue, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(queue, "OUT", tmp_path / "report.json")
    monkeypatch.setattr(queue, "QUEUE", {k: v for k, v in queue.QUEUE.items()
                                       if k.startswith("live_meta")})
    path = tmp_path / "runtime_state/reports/experimental" / queue.META_LEDGERS[0][0]
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(r) for r in rows))
    queue.STATE.write_text(json.dumps({"live_meta_calibration": "2026-07-30"}))
    calls = []
    monkeypatch.setattr(queue.subprocess, "run", lambda *a, **kw:
                        calls.append(a[0]) or SimpleNamespace(returncode=0))
    return path, calls


def test_independent_second_stage_preserves_history_and_deduplicates(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 0, "mkt_state": "NORMAL", "hold_days": 5}] * 200)
    report = queue.run_queue()
    full = report["items"][1]
    assert full["ready"] and full["ticketed"]
    assert len(calls) == 1 and "2차" in calls[0][2]
    state = json.loads(queue.STATE.read_text())
    assert state["live_meta_calibration"] == "2026-07-30"
    assert state["live_meta_calibration_full"]
    assert full["evidence"]["promotion_allowed"] is False
    assert full["evidence"]["h10_tp5_probability_verified"] is False
    assert full["evidence"]["ledgers"][0]["contracts"]
    queue.run_queue()
    assert len(calls) == 1


def test_unknown_regime_is_not_non_risk_off(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 2, "mkt_state": "RISK_OFF"}] * 200 +
        [{"exit_t5_h5": 2}, {"exit_t5_h5": 2, "mkt_state": "INVALID"}])
    full = queue.run_queue()["items"][1]
    assert full["have"] == 202 and not full["ready"]
    assert not calls


def test_finite_outcomes_and_contracts_are_reported(tmp_path, monkeypatch):
    path, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": n, "mkt_state": "NORMAL"} for n in
         [None, True, False, float("nan"), float("inf"), -float("inf"), "5", 0, -2]])
    with path.open("a") as f:
        f.write('\n[1,2]\ninvalid\n')
    out = queue.run_queue()["items"][1]
    assert out["have"] == 2 and not out["ready"]
    evidence = out["evidence"]
    assert evidence["known_non_risk_off"] == 2
    assert evidence["ledgers"][0]["malformed_rows"] == 2
    assert len(evidence["ledgers"][0]["sha256"]) == 64
    assert not calls


def test_no_tickets_does_not_consume_stage(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "RISK_ON"}] * 200)
    full = queue.run_queue(no_tickets=True)["items"][1]
    assert full["ready"] and not full["ticketed"] and not calls
    queue.run_queue()
    assert len(calls) == 1


def test_failed_creation_is_retryable(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "NORMAL"}] * 200)
    monkeypatch.setattr(queue.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=1))
    full = queue.run_queue()["items"][1]
    assert full["ready"] and not full["ticketed"]
    assert "live_meta_calibration_full" not in json.loads(queue.STATE.read_text())


def test_199_with_regime_is_not_ready(tmp_path, monkeypatch):
    _, calls = setup_queue(tmp_path, monkeypatch,
        [{"exit_t5_h5": 1, "mkt_state": "NORMAL"}] * 199)
    assert not queue.run_queue()["items"][1]["ready"]
    assert not calls


def ext_cache(tmp_path, monkeypatch, n=6, days=120):
    monkeypatch.setattr(queue, "CACHE", tmp_path)
    d = tmp_path / "intraday_ext"
    d.mkdir()
    dates = pd.bdate_range("2025-01-01 19:59", periods=days, normalize=False)
    for i in range(n):
        pd.DataFrame({"close": 1}, index=dates).to_parquet(d / f"{i:06d}.parquet")
    return d


def test_ext_census_includes_files_beyond_first_five(tmp_path, monkeypatch):
    d = ext_cache(tmp_path, monkeypatch)
    pd.DataFrame({"close": [1]}, index=pd.to_datetime(["2025-10-01 19:59"])).to_parquet(d / "000005.parquet")
    out = queue._ext_evidence()
    assert out["days"] == 121 and out["symbols"] == 6
    assert out["progress"] == 6 / 300 and not out["ready"]
    assert not out["promotion_allowed"]


def test_ext_both_axes_required_and_historical_ticket_preserved(tmp_path, monkeypatch):
    ext_cache(tmp_path, monkeypatch, n=300, days=120)
    monkeypatch.setattr(queue, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(queue, "OUT", tmp_path / "report.json")
    monkeypatch.setattr(queue, "QUEUE", {"ext_session_transfer": queue.QUEUE["ext_session_transfer"]})
    queue.STATE.write_text(json.dumps({"ext_session_transfer": "2026-08-24"}))
    def unexpected(*a, **kw):
        raise AssertionError("old ticket must not be reissued")
    monkeypatch.setattr(queue.subprocess, "run", unexpected)
    item = queue.run_queue()["items"][0]
    assert item["ready"] and item["have"] == item["need"] == 1
    assert json.loads(queue.STATE.read_text())["ext_session_transfer"] == "2026-08-24"
    for f in (tmp_path / "intraday_ext").glob("*.parquet"):
        frame = pd.read_parquet(f).iloc[:119]
        frame.to_parquet(f)
    out = queue._ext_evidence()
    assert out["symbols"] == 300 and out["days"] == 119 and not out["ready"]


def test_ext_empty_invalid_and_current_day_not_counted(tmp_path, monkeypatch):
    d = ext_cache(tmp_path, monkeypatch, n=1, days=1)
    pd.DataFrame({"close": []}, index=pd.DatetimeIndex([])).to_parquet(d / "000001.parquet")
    pd.DataFrame({"close": [1]}).to_parquet(d / "000002.parquet")
    pd.DataFrame({"close": [1, 1, 1]}, index=pd.to_datetime([
        "2026-10-07 08:00Z", "2026-10-08 08:00Z", "2026-10-06 23:00Z"])
    ).to_parquet(d / "000003.parquet")
    out = queue._ext_evidence(datetime(2026, 10, 7, 0, tzinfo=timezone.utc))
    assert out["symbols"] == 1 and out["days"] == 1
    assert out["file_errors"] == [{"file": "000002.parquet", "error": "ValueError"}]
    assert not out["ready"]
    out = queue._ext_evidence(datetime(2026, 10, 7, 11, tzinfo=timezone.utc))
    assert out["symbols"] == 2 and out["days"] == 2


def test_ext_changed_snapshot_not_ready(tmp_path, monkeypatch):
    d = ext_cache(tmp_path, monkeypatch, n=1, days=120)
    original = pd.read_parquet
    def replace_while_reading(path, **kwargs):
        result = original(path, **kwargs)
        path.touch()
        return result
    monkeypatch.setattr(pd, "read_parquet", replace_while_reading)
    out = queue._ext_evidence()
    assert not out["snapshot_stable"] and not out["ready"]
