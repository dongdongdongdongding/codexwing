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

    # 2026-09-02 은퇴 이후: 스캔은 돌되 **라우팅은 거부**된다.
    # 이 테스트는 원래 「정상 라우팅」을 지켰다. 결정이 뒤집혔고, 같은 자리에서
    # **은퇴가 라우팅 층에서도 집행되는지**를 지킨다 — 은퇴를 선언해 놓고 라우터가
    # 그대로 발행하면 은퇴가 아니다(랭킹섀도 보드가 킬 선언 뒤 1,304행을 더 찍은 그 병).
    assert result["error"] == "lane_retired: nasdaq_session_edge"
    assert result.get("routed") in (0, None), "은퇴 레인이 라우팅되면 안 된다"

    # 스캔조차 안 부른다 — 은퇴 판정이 모델 실행 **앞**에 선다.
    # 관측만 남기려면 스캔을 돌려야 하지만, 이 레인은 42거래일간 0픽이라 돌릴 이유가 없다.
    assert "args" not in observed, "은퇴 레인의 모델이 실행됐다"
    assert "route" not in observed, "은퇴 레인이 _route_live 까지 도달했다"
