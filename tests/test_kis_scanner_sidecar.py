from __future__ import annotations

import pandas as pd

from modules.scanner_services import _build_optional_kis_sidecar, build_kr_scan_outputs


def _daily_frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Open": [100.0] * 55,
            "High": [105.0] * 55,
            "Low": [99.0] * 55,
            "Close": list(range(100, 155)),
            "Volume": [1000.0] * 55,
        },
        index=pd.date_range("2026-04-01", periods=55, freq="D"),
    )
    frame.attrs["source_provider"] = "kis_openapi"
    return frame


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
        daily_bars_source="kis_openapi",
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
        daily_bars_source="kis_openapi",
    )

    sidecar = output["db_payload"]["leader_metrics"]["kis_sidecar"]
    assert output["db_payload"]["decision_score"] == 83
    assert sidecar["model_candidate_features"]["kis_daily_return_5d_pct"] is not None
    assert output["db_payload"]["feature_snapshot"]["kis_sidecar"]["feature_origin"] == "kis_openapi_sidecar"


def test_optional_kis_sidecar_does_not_label_unknown_daily_source_as_kis(monkeypatch):
    monkeypatch.setenv("AG_ENABLE_KIS_SIDECAR", "1")
    monkeypatch.setenv("AG_KIS_SIDECAR_FETCH_QUOTE", "0")
    frame = _daily_frame()
    frame.attrs["source_provider"] = "finance_data_reader"

    sidecar = _build_optional_kis_sidecar(
        "005930.KS",
        market="KOSPI",
        daily_bars=frame,
        whale_data=_kis_flow(),
    )

    assert sidecar["coverage"]["daily_ohlcv"] is False
    assert "kis_daily_sidecar_skipped_unverified_source:finance_data_reader" in sidecar["warnings"]


def test_optional_kis_sidecar_persists_live_rank_news_stock_and_financial_contracts(monkeypatch):
    class FakeKISClient:
        def quote_snapshot(self, symbol):
            return {"ticker": symbol, "source_status": "ok", "last_price": 75500, "per": 14.0, "pbr": 1.2}

        def volume_rank(self, *, market="ALL"):
            return {"output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "4"}]}

        def fluctuation_rank(self, *, market="ALL"):
            return {"output": []}

        def volume_power_rank(self, *, market="ALL"):
            return {"output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "9"}]}

        def vi_status(self, *, market="ALL", trade_date):
            return {"output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자"}]}

        def news_titles(self, *, symbol="", trade_date="", hour=""):
            code = str(symbol or "005930").split(".")[0]
            return {
                "output": [
                    {"title": "one", "mksc_shrn_iscd": code},
                    {"title": "two", "mksc_shrn_iscd": code},
                    {"title": "three", "mksc_shrn_iscd": code},
                ]
            }

        def stock_info(self, symbol):
            return {
                "output": {
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "mket_id_cd_name": "유가증권",
                    "scty_dvsn_name": "주권",
                    "lstg_dt": "19750611",
                }
            }

        def financial_ratio(self, symbol):
            return {"output": [{"stac_yymm": "202512", "roe_val": "9.8", "lblt_rate": "28.7"}]}

    monkeypatch.setattr("modules.kis_openapi.KISOpenAPIClient", FakeKISClient)
    monkeypatch.setenv("AG_ENABLE_KIS_SIDECAR", "1")
    monkeypatch.setenv("AG_KIS_SIDECAR_NEWS_MAX_ROWS", "2")
    monkeypatch.setenv("AG_KIS_SIDECAR_FETCH_MINUTE", "0")

    sidecar = _build_optional_kis_sidecar(
        "005930.KS",
        market="KOSPI",
        daily_bars=_daily_frame(),
        daily_bars_source="kis_openapi",
        whale_data=_kis_flow(),
    )

    features = sidecar["model_candidate_features"]
    assert sidecar["rank_contract"]["volume_rank"] == 4
    assert sidecar["rank_contract"]["volume_power_rank"] == 9
    assert sidecar["vi_contract"]["triggered"] is True
    assert sidecar["news_contract"]["news_count"] == 3
    assert sidecar["news_contract"]["rows_stored_count"] == 2
    assert sidecar["news_contract"]["source_scope"] == "symbol_specific"
    assert sidecar["stock_info_contract"]["listed_date"] == "19750611"
    assert sidecar["financial_ratio_contract"]["roe"] == 9.8
    assert features["kis_rank_volume"] == 4
    assert features["kis_news_title_count"] == 3
    assert features["kis_stock_listed_date"] == "19750611"
    assert features["kis_financial_debt_ratio"] == 28.7
