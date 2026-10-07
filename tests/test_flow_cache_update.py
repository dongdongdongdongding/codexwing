from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from multi_agent.tools import update_flow_cache as flow
from multi_agent.tools import run_primary_market_session_ops as ops

NOW = datetime(2026, 10, 7, 2, tzinfo=timezone.utc)


def payload(*days, value="10"):
    return {"rt_cd": "0", "output2": [
        {"stck_bsop_date": day, **{source: value for source in flow.FIELDS.values()}}
        for day in days]}


def setup_cache(tmp_path):
    old = pd.DataFrame([
        {"code": code, "date": pd.Timestamp(day), **{f: 10 for f in flow.FIELDS}}
        for code, day in [("005930", "2026-10-06"), ("000660", "2026-10-02")]])
    old.to_parquet(tmp_path / "flow.parquet", index=False)
    pd.DataFrame({"code": ["005930", "000660"], "date": pd.to_datetime(["2026-10-06"] * 2),
                  "liq": [100, 90]}).to_parquet(tmp_path / "px_long.parquet", index=False)
    audit = tmp_path / "audit"
    audit.mkdir()
    return old, audit


class Client:
    def __init__(self, responses):
        self.responses = responses

    def investor_trading_daily(self, code, **kwargs):
        response = self.responses[code]
        if isinstance(response, Exception):
            raise response
        return response


def test_per_symbol_holes_preserve_history_and_repeat_noop(tmp_path):
    old, audit = setup_cache(tmp_path)
    before = flow.sha(tmp_path / "flow.parquet")
    client = Client({c: payload("20261007", "20261006", "20261002") for c in old.code})
    r = flow.collect(tmp_path, audit, client, now=NOW, apply=True)
    assert r["status"] == "ok" and r["added_rows"] == 2 and r["committed"]
    assert flow.sha(audit / "flow.before.parquet") == before
    after = pd.read_parquet(tmp_path / "flow.parquet")
    pd.testing.assert_frame_equal(after.iloc[:len(old)], old)
    assert after.date.max() == pd.Timestamp("2026-10-06")
    assert all(x["excluded_current_or_future_rows"] == 1 for x in r["symbols"])
    second = tmp_path / "second"
    second.mkdir()
    repeat = flow.collect(tmp_path, second, client, now=NOW, apply=True)
    assert repeat["added_rows"] == 0 and not repeat["committed"]
    assert repeat["cache_before_sha256"] == repeat["cache_after_sha256"]


def test_partial_api_failure_never_reports_current(tmp_path):
    old, audit = setup_cache(tmp_path)
    r = flow.collect(tmp_path, audit, Client({"005930": payload("20261006"),
        "000660": TimeoutError("secret must not enter receipt")}), now=NOW, apply=True)
    assert r["status"] == "degraded" and r["error_symbols"] == 1 and r["stale_symbols"] == 1
    assert r["cache_before_sha256"] == r["cache_after_sha256"]
    assert "secret" not in json.dumps(r)
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "flow.parquet"), old)


@pytest.mark.parametrize("value", [None, "", "NaN", "1.2", True, "1,2", "1e3", str(2**64)])
def test_malformed_amount_not_zero_filled(value):
    with pytest.raises(ValueError):
        flow.parse_rows(payload("20261006", value=value), "005930", pd.Timestamp("2026-10-07"))


def test_signed_and_comma_amount_preserved():
    p = payload("20261006")
    p["output2"][0]["frgn_ntby_tr_pbmn"] = "-12,345"
    rows, _ = flow.parse_rows(p, "005930", pd.Timestamp("2026-10-07"))
    assert rows[0]["frgn_val"] == -12345


@pytest.mark.parametrize("bad", [{"rt_cd": "1", "output2": []}, {"rt_cd": "0"},
                               {"rt_cd": "0", "output2": {}}])
def test_failed_or_malformed_envelope(bad):
    with pytest.raises(ValueError):
        flow.parse_rows(bad, "005930", pd.Timestamp("2026-10-07"))


def test_empty_and_conflict_visible_without_historical_overwrite(tmp_path):
    old, audit = setup_cache(tmp_path)
    r = flow.collect(tmp_path, audit, Client({"005930": payload("20261006", value="999"),
        "000660": payload()}), now=NOW, apply=True)
    assert r["status"] == "degraded" and r["empty_symbols"] == r["overlap_conflicts"] == 1
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "flow.parquet"), old)


def test_concurrent_source_change_refuses_commit(tmp_path):
    old, audit = setup_cache(tmp_path)

    class ChangingClient:
        def investor_trading_daily(self, code, **kwargs):
            (tmp_path / "flow.parquet").write_bytes(b"other writer")
            return payload("20261006")

    with pytest.raises(RuntimeError, match="cache_changed_during_collection"):
        flow.collect(tmp_path, audit, ChangingClient(), now=NOW, apply=True)
    assert (tmp_path / "flow.parquet").read_bytes() == b"other writer"


def test_no_apply_retains_cache(tmp_path):
    old, audit = setup_cache(tmp_path)
    r = flow.collect(tmp_path, audit, Client({c: payload("20261006") for c in old.code}), now=NOW)
    assert r["added_rows"] == 1 and not r["committed"]
    assert r["cache_before_sha256"] == r["cache_after_sha256"]


def test_batch_attaches_own_receipt_beyond_stdout_tail(tmp_path, monkeypatch):
    monkeypatch.setattr(ops, "PROJECT_ROOT", tmp_path)

    def run(argv, **kwargs):
        flow.write_json(Path(kwargs["env"]["FLOW_RECEIPT_PATH"]), {
            "status": "degraded", "cache_latest": "2026-10-06", "stale_symbols": 2,
            "symbols": ["details stay in durable receipt"]})
        return SimpleNamespace(returncode=9, stdout="x" * 10000, stderr="")

    monkeypatch.setattr(ops.subprocess, "run", run)
    result = ops._run_command({"name": "primary_daily_ops", "argv": ["bash"]}, dry_run=False)
    artifact = result["step_artifacts"]["flow_update"]
    assert artifact["status"] == "degraded" and artifact["stale_symbols"] == 2
    assert artifact["sha256"] == flow.sha(Path(artifact["path"]))
    assert "symbols" not in artifact


def test_main_api_failure_returns_nonzero_and_durable_receipt(tmp_path, monkeypatch):
    setup_cache(tmp_path)
    from modules import kis_openapi
    monkeypatch.setattr(kis_openapi, "KISOpenAPIClient", lambda **kw: Client({
        "005930": TimeoutError(), "000660": TimeoutError()}))
    monkeypatch.setattr(flow, "legacy_writers", lambda: [])
    report = tmp_path / "receipt.json"
    monkeypatch.setattr("sys.argv", ["update_flow_cache.py", "--cache", str(tmp_path), "--report", str(report)])
    assert flow.main() == 2
    assert json.loads(report.read_text())["error_symbols"] == 2
