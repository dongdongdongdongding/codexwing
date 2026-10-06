import json
import pandas as pd
import pytest

from modules.model_lane_contract import model_lane_contract, pick_signal_date
from multi_agent.tools import report_kr_swing_candidate as R
from web.backend import services as S


def test_rerun_routes_frozen_price_score_and_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "LEDGER", tmp_path / "ledger.jsonl")
    pick = {"date": "2026-10-01", "ticker": "A", "market": "KOSDAQ", "close": 100,
            "p": .75, "contract_tp": .05, "contract_h": 10}
    first = R.record_daily_picks({"as_of": pick["date"], "picks": [pick]}, "first")
    before = R.LEDGER.read_bytes()
    second = R.record_daily_picks({"as_of": pick["date"], "picks": [
        {**pick, "close": 123, "p": .9}, {**pick, "ticker": "B"}]}, "rerun")
    assert second == first
    assert second[0]["close"] == 100 and second[0]["contract_h"] == 10
    assert R.LEDGER.read_bytes() == before


def test_db_does_not_overwrite_a_newer_or_same_session_ledger(monkeypatch):
    recorded = {"lane": "kospi_swing", "scan_date": "2026-10-01", "code": "A", "entry": 12270,
                "contract_h": 10, "prob": 75.57}
    uploaded = {**recorded, "entry": 12320, "contract_h": 5}
    monkeypatch.setattr(S, "_a_picks_ledger", lambda: [recorded.copy()])
    monkeypatch.setattr(S, "_kr_scan_picks", lambda: [uploaded.copy()])
    assert S.a_picks()[0]["entry"] == 12270
    assert S.a_picks()[0]["contract_h"] == 10
    uploaded["scan_date"] = "2026-10-02"
    assert S.a_picks()[0]["entry"] == 12320


def test_signal_date_is_not_midnight_upload_date():
    assert pick_signal_date({}, "SWING-CAND-20261001", "2026-10-02T01:00:00Z") == "2026-10-01"
    assert pick_signal_date({"signal_date": "2026-10-05"}, "any", "2026-10-06") == "2026-10-05"


def test_persisted_deep_report_preserves_per_pick_contract(monkeypatch):
    from modules import db_manager, top_deep_report
    from multi_agent.tools.report_swing_ensemble import _route_live
    captured = []
    class DB:
        def upsert_scan_result(self, payload, **kwargs):
            return True
    monkeypatch.setattr(db_manager, "DBManager", DB)
    def persist(rows):
        captured.extend(rows)
        return {"rows_upserted": len(rows)}
    monkeypatch.setattr(top_deep_report, "upsert_reports_to_supabase", persist)
    _route_live([{"ticker": "002990.KS", "market": "KOSPI", "p": .75, "entry_reference_price": 100,
                  "date": "2026-10-01", "contract_h": 10, "contract_tp": .07, "model_label": "t5_5"}],
                "SWING-CAND-20261001", "2026-10-02T01:00:00Z", bucket="swing_candidate")
    row = captured[0]
    ci = row["candidate_interpretation"]
    assert row["trade_plan"]["target_price"] == 107
    assert ci["hold_days"] == 10 and ci["contract_h"] == 10
    assert ci["contract_tp"] == .07 and ci["signal_date"] == "2026-10-01"
    assert "10거래일" in ci["hold_note"] and "t5_5" in ci["model_prob_label"]
    assert "ft_5_5" not in ci["model_prob_label"]


def test_empty_nasdaq_admission_still_records_run_and_resolves(tmp_path, monkeypatch):
    from multi_agent.tools import report_nasdaq_session_tape as N
    monkeypatch.setattr(N, "_features", lambda: ["univ_frac250"])
    monkeypatch.setattr(N, "_latest_panel", lambda: "fixture")
    monkeypatch.setattr(N.pd, "read_parquet", lambda *a, **k: pd.DataFrame({
        "symbol": ["TEST"], "date": [pd.Timestamp("2026-10-01")], "close": [100],
        "liq20": [1], "feature_ready": [True], "fwd_high_ret_20d": [None], "univ_frac250": [0.1]}))
    monkeypatch.setattr(N, "_admit", lambda p: p.assign(tradable=False))
    monkeypatch.setattr(N, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(N, "REPORT_JSON", tmp_path / "report.json")
    monkeypatch.setattr(N, "REPORT_MD", tmp_path / "report.md")
    monkeypatch.setattr(N, "resolve_pending", lambda today: {"resolved": 3})
    N.main()
    report = json.loads(N.REPORT_JSON.read_text())
    assert report["status"] == "no_candidates" and report["picks"] == []
    assert report["forward_summary"]["resolved"] == 3
