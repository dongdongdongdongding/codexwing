import json
import os
from pathlib import Path
import subprocess

import pandas as pd
import pytest

from multi_agent.tools.refresh_issued_outcomes import plan_refresh
from multi_agent.tools.repair_issued_outcomes import audit_and_apply


def sample():
    days = pd.bdate_range("2026-08-24", periods=7)
    prices = pd.DataFrame({"code":"123456", "date":days,
                           "adj_close":[100.,101.,102.,103.,104.,105.,106.],
                           "adj_high":[101.,102.,103.,104.,106.,106.,107.]})
    row = {"id":1,"run_id":"SWING-CAND-20260824","ticker":"123456.KS",
           "base_trade_date":"2026-08-24","entry_reference_price":99.,
           "validation_excluded":True,"validation_excluded_reason":"FEATURE_MISSING"}
    issued = {(row["run_id"],row["ticker"]):{"date":"2026-08-24","close":99.}}
    return row,issued,prices,days


def test_refresh_matures_labels_without_changing_issued_reference_or_exclusions():
    row,issued,prices,days = sample()
    plan,_,errors = plan_refresh([row],issued,prices.iloc[:3],days[:3])
    assert not errors
    assert plan[0]["patch"].get("return_5d_pct") is None
    before = {**row,**plan[0]["patch"]}
    plan,_,errors = plan_refresh([before],issued,prices,days)
    assert not errors
    assert plan[0]["patch"]["return_5d_pct"] == 5.
    assert plan[0]["patch"]["hit_5pct_within_5d"] is True
    assert "entry_reference_price" not in plan[0]["patch"]
    assert "validation_excluded" not in plan[0]["patch"]
    assert "validation_excluded_reason" not in plan[0]["patch"]
    refreshed = {**before,**plan[0]["patch"]}
    assert plan_refresh([refreshed],issued,prices,days)[0] == []


def test_missing_ticker_session_and_changed_issued_reference_are_reported():
    row,issued,prices,days = sample()
    plan,_,errors = plan_refresh([row],issued,prices.drop(2),days)
    assert not plan and errors[0]["id"] == 1
    plan,_,errors = plan_refresh([{**row,"entry_reference_price":100}],issued,prices,days)
    assert not plan and errors[0]["reason"] == "issued_reference_mismatch"


def test_unissued_rows_and_missing_signal_day_price_are_not_fabricated():
    row,issued,prices,days = sample()
    plan,counts,errors = plan_refresh([{**row,"ticker":"OTHER"}],issued,prices,days)
    assert not plan and not errors and counts["not_in_issued_ledger"] == 1
    plan,counts,errors = plan_refresh([row],issued,prices,days[:0])
    assert not plan and not errors and counts["waiting_signal_day_price"] == 1


def test_suspended_session_keeps_daily_valuation_but_not_fictitious_high_label():
    row,issued,prices,days = sample()
    prices["volume"] = 10
    prices.loc[1,["volume","adj_high"]] = 0
    plan,_,errors = plan_refresh([row],issued,prices,days)
    assert not errors
    patch = plan[0]["patch"]
    assert patch["return_1d_pct"] == 1.
    assert patch.get("hit_5pct_within_5d") is None
    assert patch["feature_snapshot"]["daily_outcome_basis"]["nontrading_sessions"] == [str(days[1].date())]
    assert patch["feature_snapshot"]["daily_outcome_basis"]["valuation_only"] is True


def test_verified_backup_precedes_write_and_source_change_blocks_write(tmp_path):
    item = {"before":{"id":1,"entry_reference_price":99},"patch":{"return_1d_pct":1.}}
    class Client:
        def table(self,*args):
            raise AssertionError("source guard should stop before any DB write")
    def changed():
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert json.loads(files[0].read_text())["plan"] == [item]
        raise RuntimeError("source changed")
    with pytest.raises(RuntimeError,match="source changed"):
        audit_and_apply([item],tmp_path,{},Client(),True,changed)


def test_compare_and_set_conflict_is_audited_and_stops_following_rows(tmp_path):
    class Query:
        def __init__(self):
            self.writes = 0
        def table(self,*a): return self
        def update(self,*a): return self
        def eq(self,*a): return self
        def is_(self,*a): return self
        def execute(self):
            self.writes += 1
            return type("Response",(),{"data":[]})()
    client = Query()
    items = [{"before":{"id":n},"patch":{"return_1d_pct":1.}} for n in [1,2]]
    with pytest.raises(RuntimeError,match="compare-and-set"):
        audit_and_apply(items,tmp_path,{},client,True)
    assert client.writes == 1
    logs = [json.loads(s) for s in (tmp_path/"audit.jsonl").read_text().splitlines()]
    assert logs[-1]["state"] == "conflict"


@pytest.mark.parametrize("dry_run",["0","1"])
def test_real_daily_step_preserves_dry_run_on_system_bash(dry_run):
    script = (Path(__file__).resolve().parents[1]/"multi_agent/tools/run_daily_ops.sh").read_text()
    block = script.split('echo "[STEP] refresh_issued_outcomes"',1)[1].split(
        'echo "[STEP] export_scan_archive_learning_dataset"',1)[0]
    result = subprocess.run(["/bin/bash","-c",'set -euo pipefail\nrun_optional() { printf "%s\\n" "$@"; }\n'+block],
                            env={**os.environ,"DRY_RUN":dry_run},capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert ("--apply" in result.stdout.splitlines()) == (dry_run == "0")
