from __future__ import annotations

import pandas as pd

from modules.scanner_services import _build_optional_kis_sidecar, build_kr_scan_outputs


def _daily_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0] * 55,
            "High": [105.0] * 55,
            "Low": [99.0] * 55,
            "Close": list(range(100, 155)),
            "Volume": [1000.0] * 55,
        },
        index=pd.date_range("2026-04-01", periods=55, freq="D"),
    )


def _kis_flow() -> dict:
    return {
        "flow_source": "kis_openapi",
        "foreigner_1d": 10,
        "institution_1d": 20,
        "retail_1d": -30,
        "foreigner_3d": 40,
        "institution_3d": 50,
        "retail_3d": -90,
        "foreigner_10d": 100,
        "institution_10d": 120,
        "retail_10d": -220,
    }


def test_optional_kis_sidecar_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AG_ENABLE_KIS_SIDECAR", raising=False)

    assert _build_optional_kis_sidecar("005930.KS", market="KOSPI") == {}


def test_optional_kis_sidecar_uses_active_kis_provider_and_flow(monkeypatch):
    monkeypatch.setenv("AG_ENABLE_KIS_SIDECAR", "1")
    monkeypatch.setenv("AG_KR_MARKET_DATA_PROVIDER", "kis_first")
    monkeypatch.setenv("AG_KIS_SIDECAR_FETCH_QUOTE", "0")

    sidecar = _build_optional_kis_sidecar(
        "005930.KS",
        market="KOSPI",
        daily_bars=_daily_frame(),
        whale_data=_kis_flow(),
    )

    assert sidecar["feature_origin"] == "kis_openapi_sidecar"
    assert sidecar["coverage"]["daily_ohlcv_50d"] is True
    assert sidecar["coverage"]["investor_flow"] is True
    assert sidecar["replacement_readiness"]["production_replacement_ready"] is False


def test_kr_scan_outputs_embed_kis_sidecar_without_decision_change(monkeypatch):
    monkeypatch.setenv("AG_ENABLE_KIS_SIDECAR", "1")
    monkeypatch.setenv("AG_KR_MARKET_DATA_PROVIDER", "kis_first")
    monkeypatch.setenv("AG_KIS_SIDECAR_FETCH_QUOTE", "0")

    output = build_kr_scan_outputs(
        sym="005930.KS",
        stock_name="Samsung",
        alpha_score=82,
        whale_score=70,
        whale_trend="flow",
        real_trend="UP",
        prev_pct_change=1.2,
        consec_days=1,
        setup={
            "Entry Price": 10000,
            "Target Price": 11500,
            "Stop Loss": 9000,
            "ATR Stop %": "-10%",
            "Max Hold Days": 5,
            "Volume Ratio": 2.0,
            "Volume Confirmed": True,
        },
        news_tag="-",
        strategy_tag="Momentum",
        surge_tag="-",
        wr=80,
        position="Rising",
        prob_5=70,
        prob_clean=68,
        decision_score=83,
        conviction_score=72,
        tier="T1",
        tier_sort=1,
        tech_score=75,
        fund_ok=True,
        m_type="KOSPI",
        verdict_label="Buy",
        market_gate="GREEN",
        kospi_chg=0.4,
        whale_data=_kis_flow(),
        daily_bars=_daily_frame(),
    )

    sidecar = output["db_payload"]["leader_metrics"]["kis_sidecar"]
    assert output["db_payload"]["decision_score"] == 83
    assert sidecar["model_candidate_features"]["kis_daily_return_5d_pct"] is not None
    assert output["db_payload"]["feature_snapshot"]["kis_sidecar"]["feature_origin"] == "kis_openapi_sidecar"
