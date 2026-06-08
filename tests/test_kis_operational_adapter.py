from __future__ import annotations

import pandas as pd

from modules.kis_operational_adapter import (
    build_kis_sidecar_snapshot,
    kis_replacement_roadmap,
    normalize_kis_daily_bars,
    normalize_kis_financial_ratio,
    normalize_kis_flow_for_whale_contract,
    normalize_kis_minute_bars,
    normalize_kis_news_titles,
    normalize_kis_quote_for_operational_fields,
    normalize_kis_rank_membership,
    normalize_kis_stock_info,
    normalize_kis_vi_status,
)


def test_normalize_kis_daily_bars_matches_ohlcv_contract():
    payload = {
        "output2": [
            {
                "stck_bsop_date": "20260603",
                "stck_oprc": "1000",
                "stck_hgpr": "1100",
                "stck_lwpr": "990",
                "stck_clpr": "1080",
                "acml_vol": "10000",
            },
            {
                "stck_bsop_date": "20260602",
                "stck_oprc": "900",
                "stck_hgpr": "1010",
                "stck_lwpr": "880",
                "stck_clpr": "1000",
                "acml_vol": "8000",
            },
        ]
    }

    frame = normalize_kis_daily_bars("005930.KS", payload)

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert frame.index[0].strftime("%Y%m%d") == "20260602"
    assert float(frame["Close"].iloc[-1]) == 1080.0


def test_normalize_kis_minute_bars_resolves_datetime_and_ohlcv():
    payload = {
        "output2": [
            {
                "stck_bsop_date": "20260603",
                "stck_cntg_hour": "090100",
                "stck_prpr": "1010",
                "stck_oprc": "1005",
                "stck_hgpr": "1015",
                "stck_lwpr": "1000",
                "cntg_vol": "1200",
            }
        ]
    }

    frame = normalize_kis_minute_bars("005930.KS", payload)

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert frame.index[0].strftime("%Y%m%d%H%M%S") == "20260603090100"
    assert float(frame["Volume"].iloc[0]) == 1200.0


def test_quote_and_flow_normalize_to_operational_contracts():
    quote = normalize_kis_quote_for_operational_fields(
        {
            "ticker": "005930",
            "source_status": "ok",
            "last_price": "76500",
            "day_change_pct": "1.25",
            "volume": "1234567",
            "value_traded": "90000000000",
            "prev_volume_ratio": "180.5",
            "per": "12.3",
            "pbr": "1.1",
            "status_warning": None,
        }
    )
    flow = normalize_kis_flow_for_whale_contract(
        {
            "source_status": "ok",
            "flow_unit": "KRW",
            "foreigner_1d": 100,
            "institution_1d": 50,
            "retail_1d": -150,
            "foreigner_3d": 200,
            "institution_3d": 100,
            "retail_3d": -300,
            "foreigner_10d": 300,
            "institution_10d": 200,
            "retail_10d": -500,
        }
    )

    assert quote["current_price"] == 76500.0
    assert quote["volume_ratio"] == 180.5
    assert flow["valid"] is True
    assert flow["flow_source"] == "kis_openapi"
    assert flow["whale_score"] > 50
    assert flow["whale_flow_1d"] == 150


def test_rank_vi_and_news_contracts_track_checked_state_without_fabrication():
    rank = normalize_kis_rank_membership(
        "005930.KS",
        volume_rank_payload={
            "output": [
                {"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "2"},
                {"mksc_shrn_iscd": "000660", "hts_kor_isnm": "SK하이닉스", "data_rank": "1"},
            ]
        },
        fluctuation_rank_payload={"output": []},
        volume_power_rank_payload={"output": []},
    )
    vi = normalize_kis_vi_status("005930.KS", {"output": []})
    news = normalize_kis_news_titles({"output": []}, symbol="005930.KS")

    assert rank["checked"] is True
    assert rank["volume_rank"] == 2
    assert rank["fluctuation_rank"] is None
    assert vi["checked"] is True
    assert vi["triggered"] is False
    assert news["checked"] is True
    assert news["news_count"] == 0
    assert news["source_scope"] == "empty"


def test_normalize_kis_news_titles_filters_mixed_kis_rows_to_candidate_symbol():
    news = normalize_kis_news_titles(
        {
            "output": [
                {
                    "iscd1": "005930",
                    "kor_isnm1": "삼성전자",
                    "hts_pbnt_titl_cntt": "삼성전자 AI 반도체 공급 계약",
                },
                {
                    "iscd1": "000660",
                    "kor_isnm1": "SK하이닉스",
                    "hts_pbnt_titl_cntt": "SK하이닉스 HBM 공급",
                },
            ]
        },
        symbol="005930.KS",
        stock_name="삼성전자",
    )

    assert news["checked"] is True
    assert news["raw_news_count"] == 2
    assert news["news_count"] == 1
    assert news["rows_filtered_out_count"] == 1
    assert news["rows"][0]["iscd1"] == "005930"
    assert news["source_scope"] == "symbol_specific"
    assert news["promotion_blocked"] is False
    assert news["source_scope_metadata"]["evidence"]["raw_news_count"] == 2


def test_stock_info_and_financial_ratio_contracts_preserve_real_fields():
    stock = normalize_kis_stock_info(
        "005930.KS",
        {
            "output": {
                "pdno": "005930",
                "prdt_name": "삼성전자",
                "mket_id_cd": "STK",
                "mket_id_cd_name": "유가증권",
                "scty_dvsn_name": "주권",
                "lstg_dt": "19750611",
                "bstp_kor_isnm": "전기전자",
                "prdt_sale_stat_cd": "00",
            }
        },
    )
    financial = normalize_kis_financial_ratio(
        "005930.KS",
        {
            "output": [
                {
                    "stac_yymm": "202512",
                    "grs": "3.4",
                    "bsop_prfi_inrt": "18.2",
                    "ntin_inrt": "13.1",
                    "roe_val": "9.8",
                    "eps": "5500",
                    "bps": "52000",
                    "per": "14.2",
                    "pbr": "1.3",
                    "lblt_rate": "28.7",
                    "crnt_rate": "262.0",
                    "rsrv_rate": "5300.1",
                }
            ]
        },
    )

    assert stock["checked"] is True
    assert stock["source_status"] == "ok"
    assert stock["product_name"] == "삼성전자"
    assert stock["listed_date"] == "19750611"
    assert financial["checked"] is True
    assert financial["statement_period"] == "202512"
    assert financial["roe"] == 9.8
    assert financial["debt_ratio"] == 28.7


def test_sidecar_snapshot_marks_production_replacement_only_when_all_gates_present():
    daily = pd.DataFrame(
        {
            "Open": [100.0] * 55,
            "High": [105.0] * 55,
            "Low": [99.0] * 55,
            "Close": list(range(100, 155)),
            "Volume": [1000.0] * 55,
        },
        index=pd.date_range("2026-04-01", periods=55, freq="D"),
    )
    minute = pd.DataFrame(
        {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5], "Volume": [500.0]},
        index=pd.date_range("2026-06-03 09:00", periods=1, freq="min"),
    )
    snapshot = build_kis_sidecar_snapshot(
        "005930.KS",
        market="KOSPI",
        quote_snapshot={"ticker": "005930", "source_status": "ok", "last_price": 155, "volume": 1000},
        daily_bars=daily,
        minute_bars=minute,
        investor_flow={
            "source_status": "ok",
            "foreigner_1d": 10,
            "institution_1d": 20,
            "retail_1d": -30,
        },
        rank_membership={"volume_rank": 5},
        vi_status={"checked": True, "triggered": False},
        news_titles=[{"title": "one", "mksc_shrn_iscd": "005930"}, {"title": "two", "mksc_shrn_iscd": "005930"}],
        news_titles_checked=True,
        news_title_count=40,
        stock_info={
            "checked": True,
            "source_status": "ok",
            "product_name": "삼성전자",
            "market_name": "유가증권",
            "stock_type": "주권",
            "listed_date": "19750611",
            "status_code": "00",
        },
        financial_ratio={
            "checked": True,
            "source_status": "ok",
            "statement_period": "202512",
            "roe": 9.8,
            "debt_ratio": 28.7,
            "current_ratio": 262.0,
        },
    )

    assert snapshot["feature_origin"] == "kis_openapi_sidecar"
    assert snapshot["coverage"]["daily_ohlcv_50d"] is True
    assert snapshot["replacement_readiness"]["production_replacement_ready"] is True
    assert snapshot["model_candidate_features"]["kis_daily_return_5d_pct"] is not None
    assert snapshot["model_candidate_features"]["kis_daily_ma20"] is not None
    assert snapshot["model_candidate_features"]["kis_daily_prior_20d_high"] is not None
    assert snapshot["daily_ohlcv_summary"]["latest_close"] == 154.0
    assert snapshot["coverage"]["vi_status"] is True
    assert snapshot["coverage"]["news_titles"] is True
    assert snapshot["news_contract"]["news_count"] == 40
    assert snapshot["news_contract"]["source_scope"] == "symbol_specific"
    assert snapshot["news_contract"]["promotion_blocked"] is False
    assert len(snapshot["news_contract"]["rows"]) == 2
    assert snapshot["news_contract"]["rows_stored_count"] == 2
    assert snapshot["news_contract"]["rows_truncated"] is True
    assert snapshot["model_candidate_features"]["kis_news_title_count"] == 40
    assert snapshot["coverage"]["stock_info"] is True
    assert snapshot["coverage"]["financial_ratio"] is True
    assert snapshot["stock_info_contract"]["listed_date"] == "19750611"
    assert snapshot["financial_ratio_contract"]["roe"] == 9.8
    assert snapshot["model_candidate_features"]["kis_financial_debt_ratio"] == 28.7


def test_sidecar_snapshot_blocks_production_ready_for_ambiguous_news_scope():
    snapshot = build_kis_sidecar_snapshot(
        "005930.KS",
        quote_snapshot={"ticker": "005930", "source_status": "ok", "last_price": 155, "volume": 1000},
        news_titles=[{"title": "AI 반도체 공급 계약 수주"}],
        news_titles_checked=True,
        stock_info={"checked": True, "source_status": "ok", "product_name": "삼성전자"},
    )

    assert snapshot["news_contract"]["source_scope"] == "ambiguous"
    assert snapshot["news_contract"]["promotion_blocked"] is True
    assert snapshot["replacement_readiness"]["production_replacement_ready"] is False
    assert snapshot["model_candidate_features"]["kis_news_promotion_blocked"] is True
    assert "KIS_NEWS_SCOPE_AMBIGUOUS" in snapshot["warnings"]


def test_kis_replacement_roadmap_keeps_source_adapter_promotion_order():
    roadmap = kis_replacement_roadmap()
    phase_names = [phase["name"] for phase in roadmap["phases"]]
    assert phase_names[:4] == ["contract_adapter", "sidecar_archive", "deep_analysis_source_contract", "dual_run_parity"]
    assert "KIS daily MA/range/return features for Top Deep readiness and chase-risk checks" in roadmap["high_value_kis_features"]
    assert "same-day minute bars for intraday volume curve and VWAP features" in roadmap["high_value_kis_features"]
