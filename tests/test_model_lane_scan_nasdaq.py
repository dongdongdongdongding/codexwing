from __future__ import annotations

import sys
import types

from modules.model_lane_scan import model_lane_for, run_model_lane_scan


def test_nasdaq_swing_uses_session_edge_lane():
    assert model_lane_for("NASDAQ", "SWING") == "nasdaq_session_edge"


def test_nasdaq_session_edge_routes_to_live_scan_lane(monkeypatch, tmp_path):
    fake_nas = types.ModuleType("report_nasdaq_session_edge_shadow")
    fake_nas.DEFAULT_OUT_DIR = tmp_path
    fake_nas.DEFAULT_LEDGER = tmp_path / "ledger.jsonl"
    fake_nas.DEFAULT_MODEL_BUNDLE = tmp_path / "model.pkl"
    fake_nas.DEFAULT_RAW_OHLCV_DIR = tmp_path / "raw"
    fake_nas.DEFAULT_CACHE_DIR = tmp_path / "cache"

    observed = {}

    def run_model(args):
        observed["args"] = args
        return {
            "score_date": "2026-06-26",
            "session_blocked": False,
            "market_session": "nasdaq_regular_close",
            "session_contract": {
                "market_session": "nasdaq_regular_close",
                "source_price_kind": "yfinance_5m_prepost",
                "sample_limit_warning": "fixture",
            },
            "capital_status": "operator_enabled_live_scan",
            "promotion_note": "fixture trace",
            "picks": [
                {
                    "ticker": "HOOD",
                    "stock_name": "Robinhood",
                    "market": "NASDAQ",
                    "p": 0.74,
                    "score": 0.98,
                    "entry_reference_price": 98.7,
                    "day_change": 5.9,
                }
            ],
        }

    fake_nas.run_model = run_model

    fake_swing = types.ModuleType("report_swing_ensemble")

    def route_live(picks, run_id, recommended_at, *, bucket, decision, lane):
        observed["route"] = {
            "picks": picks,
            "run_id": run_id,
            "recommended_at": recommended_at,
            "bucket": bucket,
            "decision": decision,
            "lane": lane,
        }
        return len(picks)

    fake_swing._route_live = route_live

    monkeypatch.setitem(sys.modules, "report_nasdaq_session_edge_shadow", fake_nas)
    monkeypatch.setitem(sys.modules, "report_swing_ensemble", fake_swing)
    monkeypatch.setenv("AG_NASDAQ_SESSION_EDGE_NO_FETCH", "0")

    result = run_model_lane_scan("NASDAQ", "SWING", route=True)

    assert result["error"] is None
    assert result["bucket"] == "nasdaq_session_edge"
    assert result["run_id"] == "NASDAQ-SESSION-EDGE-20260626"
    assert result["routed"] == 1
    assert result["picks"][0]["ticker"] == "HOOD"
    assert observed["args"].market_session == "nasdaq_regular_close"
    assert observed["args"].no_fetch is False
    assert observed["route"]["bucket"] == "nasdaq_session_edge"
    assert observed["route"]["decision"] == "NASDAQ_SESSION_EDGE_BUY"
    assert observed["route"]["lane"] == "NASDAQ_SESSION_EDGE"
