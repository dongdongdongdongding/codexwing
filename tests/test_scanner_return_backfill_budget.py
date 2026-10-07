from copy import deepcopy
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from modules import db_manager
from multi_agent.tools import backfill_scanner_full_returns as m
from multi_agent.tools import repair_issued_outcomes as repair


def row(i, ticker="005930.KS"):
    return {"id": i, "run_id": f"RUN-{i}", "ticker": ticker,
            "recommended_at": "2026-09-01T00:00:00Z", "return_3d_pct": None}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    data = {"rows": [], "index": {}, "calls": [], "plans": [], "result": {"return_3d_pct": 4.0}}
    monkeypatch.setattr(db_manager, "DBManager", lambda: SimpleNamespace(client=object()))
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "_build_outcome_index", lambda *a: data["index"])
    monkeypatch.setattr(m, "_fetch_scanner_rows_missing_returns", lambda *a, **k: deepcopy(data["rows"]))
    def fetch(ticker, date):
        data["calls"].append((ticker,date))
        return pd.DataFrame({"Close": [100.]}) if data["result"] else None
    monkeypatch.setattr(m, "_fetch_history_close", fetch)
    monkeypatch.setattr(m, "_compute_returns_from_history", lambda *a: dict(data["result"]))
    def audit(plan, *args, **kwargs):
        data["plans"].append(deepcopy(plan))
        return {"changes": len(plan)}
    monkeypatch.setattr(repair, "audit_and_apply", audit)
    def run(**kwargs):
        return m.run_backfill(shared_dir=tmp_path, limit_runs=1, dry_run=kwargs.pop("dry_run", False),
            market_filter=None, resume_path=tmp_path/"cursor.json", progress_path=tmp_path/"progress.json", **kwargs)
    data["run"] = run
    return data


def test_one_source_capture_serves_duplicate_rows_but_not_different_dates(setup):
    d=setup;d["rows"]=[row(1),row(2),{**row(3),"recommended_at":"2026-09-02T00:00:00Z"}]
    r=d["run"]()
    assert r["coverage_complete"] and r["updated"]==3
    assert r["history_requests"]==2 and r["history_cache_hits"]==1
    assert len(d["calls"])==2
    assert [p["patch"] for p in d["plans"][0]]==[{"return_3d_pct":4.}]*3


def test_no_history_request_for_dedicated_lane(setup):
    d=setup;d["rows"]=[{**row(1),"run_id":"SWING-CAND-20260901"}]
    r=d["run"]()
    assert r["skipped_dedicated_refresh"]==1 and r["rows_processed"]==1
    assert d["calls"]==[] and d["plans"]==[]


def test_request_budget_reuses_cached_sources_then_resumes_next_unvisited_row(setup,tmp_path):
    d=setup;d["rows"]=[row(1),row(2),row(3,"000660.KS")]
    r=d["run"](max_history_requests=1)
    assert r["status"]=="partial" and r["rows_unvisited"]==1
    assert r["rows_processed"]==2 and r["resume_last_id"]==2
    assert r["budget_reason"]=="history_request_limit"
    assert json.loads((tmp_path/"cursor.json").read_text())["last_id"]==2
    r=d["run"](max_rows=1)
    assert d["plans"][-1][0]["before"]["id"]==3
    assert r["resume_last_id"]==3
    r=d["run"](max_rows=1)
    assert d["plans"][-1][0]["before"]["id"]==1  # revisit immature/failed old rows


def test_failed_response_cached_only_for_current_invocation(setup):
    d=setup;d["rows"]=[row(1),row(2)];d["result"]={}
    r=d["run"]()
    assert r["history_fetch_failed"]==2 and len(d["calls"])==1
    assert r["status"]=="degraded" and r["degraded_reasons"]==["history_unavailable"]
    d["result"]={"return_3d_pct":4.}
    r=d["run"]()
    assert r["updated"]==2 and len(d["calls"])==2


def test_dry_run_never_advances_resume_state(setup,tmp_path):
    d=setup;d["rows"]=[row(1),row(2)]
    d["run"](dry_run=True,max_rows=1)
    assert not (tmp_path/"cursor.json").exists()
    progress=json.loads((tmp_path/"progress.json").read_text())
    assert progress["phase"]=="finished" and progress["summary"]["rows_unvisited"]==1
    assert progress["dry_run"] is True


def test_cas_failure_cannot_advance_cursor_even_after_partial_writes(setup,tmp_path,monkeypatch):
    d=setup;d["rows"]=[row(1),row(2)]
    d["run"](max_rows=1)
    original=(tmp_path/"cursor.json").read_bytes()
    def fail(*a,**kw):raise RuntimeError("compare-and-set conflict")
    monkeypatch.setattr(repair,"audit_and_apply",fail)
    with pytest.raises(RuntimeError):d["run"](max_rows=1)
    assert (tmp_path/"cursor.json").read_bytes()==original


def test_conflicting_source_basis_still_cannot_patch_after_cache_reuse(setup):
    d=setup;d["rows"]=[row(1),{**row(2),"return_3d_pct":-9.,"return_5d_pct":None}]
    d["result"]={"return_3d_pct":4.,"return_5d_pct":5.}
    r=d["run"]()
    assert r["updated"]==1 and r["incompatible_daily_basis_by_field"]=={"return_3d_pct":1}
    assert r["history_requests"]==1
    assert r["status"]=="degraded" and r["degraded_reasons"]==["incompatible_daily_basis"]


def test_cursor_scope_mismatch_fails_before_io(setup,tmp_path):
    d=setup;(tmp_path/"cursor.json").write_text(json.dumps({"scope":{},"last_id":1}))
    with pytest.raises(ValueError,match="cursor"):d["run"]()
    assert d["calls"]==[]


def test_budget_on_empty_index_still_attempts_history(setup):
    d=setup;d["rows"]=[row(1),row(2)]
    r=d["run"](max_rows=1)
    assert r["status"]=="partial" and r["updated"]==1


def test_second_fallback_budget_does_not_count_unvisited_index_match(setup):
    d=setup;d["rows"]=[row(1),row(2,"000660.KS")];d["index"]={("RUN-2","000660.KS"): {}}
    r=d["run"](max_history_requests=1)
    assert r["rows_processed"]==1 and r["matched_outcome_index"]==0
    assert r["matched_yfinance_fallback"]==1


def test_planning_clock_stops_before_next_row_without_dropping_finished_plan(setup,monkeypatch):
    d=setup;d["rows"]=[row(1),row(2,"000660.KS")];clock=[0.]
    monkeypatch.setattr(m.time,"monotonic",lambda:clock[0])
    original=m._fetch_history_close
    def slow(*args):
        result=original(*args);clock[0]+=11.;return result
    monkeypatch.setattr(m,"_fetch_history_close",slow)
    r=d["run"](max_planning_seconds=10)
    assert r["budget_reason"]=="planning_time_limit"
    assert r["updated"]==1 and r["rows_unvisited"]==1


def test_cli_partial_is_nonzero_and_dry_run_does_not_advance_cursor(setup,tmp_path,monkeypatch):
    d=setup;d["rows"]=[row(1),row(2)]
    monkeypatch.setattr(m.sys,"argv",["backfill","--max-rows","1","--dry-run","--shared-dir",str(tmp_path)])
    assert m.main()==2
    assert not list(tmp_path.rglob("scanner_return_backfill_cursor_*.json"))
    receipt=json.loads(next(tmp_path.rglob("scanner_returns/*.json")).read_text())
    assert receipt["summary"]["status"]=="partial"


def test_cli_failure_receipt_and_unchanged_cursor(setup,tmp_path,monkeypatch):
    d=setup;d["rows"]=[row(1)]
    def fail(*a,**k):raise RuntimeError("CAS failed")
    monkeypatch.setattr(repair,"audit_and_apply",fail)
    monkeypatch.setattr(m.sys,"argv",["backfill","--max-rows","1","--shared-dir",str(tmp_path)])
    with pytest.raises(RuntimeError):m.main()
    assert not list(tmp_path.rglob("scanner_return_backfill_cursor_*.json"))
    receipt=json.loads(next(tmp_path.rglob("scanner_returns/*.json")).read_text())
    assert receipt["phase"]=="failed" and receipt["error_type"]=="RuntimeError"


def test_cli_global_lock_prevents_overlapping_market_writers(setup,tmp_path,monkeypatch):
    import fcntl
    p=tmp_path/"runtime_state/long_term/ops/scanner_return_backfill.lock";p.parent.mkdir(parents=True)
    with p.open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        monkeypatch.setattr(m.sys,"argv",["backfill","--market","KOSPI","--max-rows","1"])
        assert m.main()==2
        assert setup["calls"]==[]
