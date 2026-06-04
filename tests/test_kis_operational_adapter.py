from __future__ import annotations

import pandas as pd

from modules.kis_operational_adapter import (
    build_kis_sidecar_snapshot,
    kis_replacement_roadmap,
    normalize_kis_daily_bars,
    normalize_kis_flow_for_whale_contract,
    normalize_kis_minute_bars,
    normalize_kis_news_titles,
    normalize_kis_quote_for_operational_fields,
    normalize_kis_rank_membership,
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
    news = normalize_kis_news_titles({"output": []})

    assert rank["checked"] is True
    assert rank["volume_rank"] == 2
    assert rank["fluctuation_rank"] is None
    assert vi["checked"] is True
    assert vi["triggered"] is False
    assert news["checked"] is True
    assert news["news_count"] == 0


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
        news_titles=[{"title": "one"}, {"title": "two"}],
        news_titles_checked=True,
        news_title_count=40,
    )

    assert snapshot["feature_origin"] == "kis_openapi_sidecar"
    assert snapshot["coverage"]["daily_ohlcv_50d"] is True
    assert snapshot["replacement_readiness"]["production_replacement_ready"] is True
    assert snapshot["model_candidate_features"]["kis_daily_return_5d_pct"] is not None
    assert snapshot["coverage"]["vi_status"] is True
    assert snapshot["coverage"]["news_titles"] is True
    assert snapshot["news_contract"]["news_count"] == 40
    assert len(snapshot["news_contract"]["rows"]) == 2
    assert snapshot["news_contract"]["rows_stored_count"] == 2
    assert snapshot["news_contract"]["rows_truncated"] is True
    assert snapshot["model_candidate_features"]["kis_news_title_count"] == 40


def test_kis_replacement_roadmap_keeps_source_adapter_promotion_order():
    roadmap = kis_replacement_roadmap()
    phase_names = [phase["name"] for phase in roadmap["phases"]]
    assert phase_names[:3] == ["contract_adapter", "sidecar_archive", "dual_run_parity"]
    assert "same-day minute bars for intraday volume curve and VWAP features" in roadmap["high_value_kis_features"]
