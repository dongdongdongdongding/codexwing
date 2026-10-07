from datetime import datetime
import json
import os
from pathlib import Path
import subprocess

import pandas as pd
import pytest

from multi_agent.tools.refresh_verified_archive_daily import (
    SOURCE, completed_sessions, request_windows, plan_refresh, validate_identity,
    finalized_groups,
    verify_capture_receipt,
)
from multi_agent.tools.us_daily_panel_cache import file_sha


def fixture():
    days = pd.bdate_range("2026-07-13", periods=32)
    prices = pd.DataFrame({"date": days, "adj_open": 100., "adj_high": 140.,
                           "adj_low": 99., "adj_close": range(100, 132), "volume": 10.})
    row = {"id": 1, "run_id": "RUN-X", "ticker": "123456.KS", "market": "KOSPI",
           "market_type": "KR", "scan_mode": "SWING", "base_trade_date": "2026-07-13",
           "recommended_at": "2026-07-13T00:00:00Z", "entry_reference_price": 120.,
           "validation_excluded": True, "validation_excluded_reason": "FEATURE_MISSING",
           "feature_snapshot": {"scanner_feature": 5, "daily_outcome_basis": {
               "source": SOURCE, "kind": "adjusted_signal_close_to_close",
               "asof": "2026-07-13", "signal_date": "2026-07-13",
               "issued_reference_price": 120., "contract_pnl": False, "evidence_sha256": "original"}}}
    return row, prices, days


def test_30_session_maturity_and_idempotence_preserve_reference_exclusion_and_features():
    row, prices, days = fixture()
    first = plan_refresh([row], {"123456": prices.iloc[:30]}, days[:30], {"123456": "first"})
    pending = {**row, **first[0]["patch"]}
    assert pending.get("return_30d_pct") is None
    second = plan_refresh([pending], {"123456": prices}, days, {"123456": "second"})
    patch = second[0]["patch"]
    assert patch["return_30d_pct"] == 30.
    assert not set(patch) & {"entry_reference_price", "validation_excluded", "validation_excluded_reason"}
    assert patch["feature_snapshot"]["scanner_feature"] == 5
    mature = {**pending, **patch}
    # A new receipt with identical numerical observations is a true no-op.
    assert plan_refresh([mature], {"123456": prices}, days, {"123456": "new_receipt"}) == []
    changed = prices.copy(); changed.loc[30, "adj_close"] = 129
    revised = plan_refresh([mature], {"123456": changed}, days, {"123456": "revised"})
    assert revised[0]["patch"]["return_30d_pct"] == 29.
    assert revised[0]["basis"]["evidence_sha256"] == "revised"


def test_missing_session_or_duplicate_or_regressing_asof_never_plans_writes():
    row, prices, days = fixture()
    for bad in [prices.drop(5), pd.concat([prices, prices.iloc[:1]])]:
        with pytest.raises(ValueError):
            plan_refresh([row], {"123456": bad}, days, {"123456": "x"})
    row["feature_snapshot"]["daily_outcome_basis"]["asof"] = "2026-10-06"
    with pytest.raises(ValueError, match="regress"):
        plan_refresh([row], {"123456": prices}, days, {"123456": "x"})


@pytest.mark.parametrize("stamp,last", [
    ("2026-10-07T00:01:00+00:00", "2026-10-06"),
    ("2026-10-07T06:59:00+00:00", "2026-10-06"),
    ("2026-10-07T07:00:00+00:00", "2026-10-07"),
])
def test_current_day_is_not_completed_before_1600_korea(stamp, last):
    dates = pd.to_datetime(["2026-10-02", "2026-10-06", "2026-10-07", "2026-10-08"])
    result = completed_sessions(dates, datetime.fromisoformat(stamp))
    assert str(result[-1].date()) == last
    assert pd.Timestamp("2026-10-05") not in result  # never invent missing sessions


def test_windows_cover_long_history_once_without_provider_truncation():
    windows = list(request_windows("2026-01-01", "2026-10-06"))
    dates = [d for w in windows for d in pd.date_range(w["start_date"], w["end_date"])]
    assert dates == list(pd.date_range("2026-01-01", "2026-10-06"))
    assert all(len(pd.date_range(w["start_date"], w["end_date"])) <= 90 for w in windows)
    assert all(w["adjusted"] and w["market_div"] == "J" for w in windows)


def test_newest_provider_day_never_enters_labels_even_after_close():
    row, prices, days = fixture()
    groups, sessions = finalized_groups({"123456": prices}, days)
    assert sessions[-1] == days[-2]
    assert groups["123456"].date.max() == days[-2]
    # The later live day is only a rollover witness, not an outcome value.
    live = prices.iloc[[-1]].copy(); live["date"] = days[-1] + pd.Timedelta(days=1)
    all_prices = pd.concat([prices, live], ignore_index=True)
    groups, sessions = finalized_groups({"123456": all_prices}, days)
    assert sessions[-1] == days[-1]
    assert groups["123456"].date.max() == days[-1]
    # Every ticker must have rolled over before advancing the cohort as-of.
    groups, sessions = finalized_groups({"123456": all_prices, "654321": prices}, days)
    assert sessions[-1] == days[-2]


def test_original_identity_and_scanner_fallback_are_reverified(tmp_path):
    row, _, _ = fixture()
    original = json.loads(json.dumps(row))
    run = tmp_path / "runtime_state/shared_working/RUN-X"; run.mkdir(parents=True)
    outcome = run / "realized_outcomes.json"
    read = lambda p: json.loads(p.read_text())
    outcome.write_text(json.dumps({"outcomes": [row]}))
    assert validate_identity(row, original, tmp_path, read) == "realized_outcomes.json"
    with pytest.raises(ValueError, match="identity"):
        validate_identity({**row, "entry_reference_price": 100}, original, tmp_path, read)
    scanner = {"run_context": {"run_id": "RUN-X", "market": "KOSPI", "as_of_date": "2026-07-13"},
               "candidates": [{"ticker": row["ticker"], "feature_snapshot": {
                   "scan_mode": "SWING", "entry_reference_price": 120.}}]}
    (run / "scanner_handoff.json").write_text(json.dumps(scanner))
    outcome.write_text(json.dumps({"outcomes": [{**row, "entry_reference_price": 99}]}))
    with pytest.raises(ValueError, match="contradictory"):
        validate_identity(row, original, tmp_path, read)
    outcome.write_text('{"outcomes": []}')
    assert validate_identity(row, original, tmp_path, read) == "scanner_handoff.json"
    row["feature_snapshot"]["daily_outcome_basis"]["source"] = "unadjusted"
    with pytest.raises(ValueError, match="basis"):
        validate_identity(row, original, tmp_path, read)


def test_capture_replay_rejects_missing_or_modified_receipt_members(tmp_path):
    for name in ["request.json", "kis_123456.json"]:
        (tmp_path / name).write_text('{}')
    receipt = {p.name: file_sha(p) for p in tmp_path.glob('*.json')}
    (tmp_path / 'receipt.json').write_text(json.dumps(receipt))
    read = lambda p: json.loads(p.read_text())
    verify_capture_receipt(tmp_path, ['123456'], read)
    with pytest.raises(ValueError, match='receipt'):
        verify_capture_receipt(tmp_path, ['123456', '654321'], read)
    (tmp_path / 'kis_123456.json').write_text('{"changed": true}')
    with pytest.raises(ValueError, match='receipt'):
        verify_capture_receipt(tmp_path, ['123456'], read)


@pytest.mark.parametrize('dry_run', ['0', '1'])
def test_real_daily_block_runs_verified_refresh_before_export_with_same_apply_policy(dry_run):
    script = (Path(__file__).resolve().parents[1] / 'multi_agent/tools/run_daily_ops.sh').read_text()
    block = script.split('echo "[STEP] refresh_issued_outcomes"', 1)[1].split(
        'echo "[STEP] export_scan_archive_learning_dataset"', 1)[0]
    out = subprocess.run(['/bin/bash', '-c',
        'set -euo pipefail\nrun_optional() { printf "%s\\n" "$*"; }\n' + block],
        env={**os.environ, 'DRY_RUN': dry_run}, capture_output=True, text=True, check=True).stdout
    line = next(x for x in out.splitlines() if x.startswith('refresh_verified_archive_daily python3'))
    assert ('--apply' in line) == (dry_run == '0')
    assert out.index('refresh_issued_outcomes python3') < out.index(line)
