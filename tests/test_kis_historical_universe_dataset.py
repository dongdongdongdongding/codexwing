from __future__ import annotations

import pandas as pd

from modules.kis_historical_universe_dataset import (
    InstrumentRecord,
    build_historical_rows_for_symbol,
    enrich_historical_rows_with_prefilter,
)
from modules.kis_model_features import flatten_kis_model_features


def _record() -> InstrumentRecord:
    return InstrumentRecord(
        symbol="000001.KS",
        local_symbol="000001",
        name="Test",
        market="KOSPI",
        listing_date="2025-01-01",
        official_sector="",
        official_industry="semiconductor manufacturing",
        industry_code="",
        region="서울",
        source="test",
    )


def test_historical_universe_uses_touch5_dd10_and_buy_premium_labels() -> None:
    dates = pd.bdate_range("2026-01-01", periods=10)
    frame = pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "High": [101, 102, 103, 104, 105, 108, 109, 110, 111, 112],
            "Low": [99, 100, 101, 102, 103, 96, 97, 98, 99, 100],
            "Close": [100, 101, 102, 103, 104, 106, 107, 108, 109, 110],
            "Volume": [1000] * 10,
        },
        index=dates,
    )

    rows = build_historical_rows_for_symbol(
        _record(),
        frame,
        min_base_date="2026-01-01",
        max_base_date="2026-01-02",
        target_pct=5.0,
        stop_pct=10.0,
        buy_premium_pct=2.0,
        min_prior_bars=1,
    )

    assert len(rows) == 2
    first = rows[0]
    assert first["snapshot_key"] == "KIS-HIST:2026-01-01:000001.KS"
    assert first["row_role"] == "historical_universe"
    assert first["max_high_return_5d_pct"] == 8.0
    assert first["min_low_return_5d_pct"] == -4.0
    assert first["target_hit_5d"] is True
    assert first["stop_hit_5d"] is False
    assert first["buy_premium_entry_price"] == 102.0
    assert first["buy_premium_max_high_return_5d_pct"] == 5.882353
    assert first["buy_premium_min_low_return_5d_pct"] == -5.882353
    assert first["buy_premium_target_hit_5d"] is True
    assert first["buy_premium_stop_hit_5d"] is False
    assert first["feature_snapshot"]["_feature_quality"]["is_dummy_data"] is False
    assert first["feature_snapshot"]["_kis_sidecar"]["feature_origin"] == "kis_historical_universe"


def test_historical_universe_conservatively_orders_same_day_target_and_stop() -> None:
    dates = pd.bdate_range("2026-01-01", periods=7)
    frame = pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104, 105, 106],
            "High": [100, 106, 102, 103, 104, 105, 106],
            "Low": [100, 89, 99, 100, 101, 102, 103],
            "Close": [100, 101, 102, 103, 104, 105, 106],
            "Volume": [1000] * 7,
        },
        index=dates,
    )

    rows = build_historical_rows_for_symbol(
        _record(),
        frame,
        min_base_date="2026-01-01",
        max_base_date="2026-01-01",
        target_pct=5.0,
        stop_pct=10.0,
        buy_premium_pct=0.0,
        min_prior_bars=1,
    )

    assert rows[0]["target_hit_1d"] is True
    assert rows[0]["stop_hit_1d"] is True
    assert rows[0]["target_before_stop_1d"] is False
    assert rows[0]["stop_before_target_1d"] is True
    assert rows[0]["first_touch_1d"] == "ambiguous_stop_first"


def test_historical_universe_prefilter_proxy_uses_real_daily_rank_features() -> None:
    rows = [
        {
            "ticker": "000001.KS",
            "stock_name": "Slow",
            "market": "KOSPI",
            "base_trade_date": "2026-01-02",
            "feature_origin": "kis_historical_universe_dataset_v1",
            "feature_snapshot": {"_feature_quality": {"is_dummy_data": False}},
            "entry_reference_price": 100.0,
            "day_return_pct": 1.0,
            "volume_ratio": 1.2,
            "turnover": 100_000_000.0,
        },
        {
            "ticker": "000002.KS",
            "stock_name": "Fast",
            "market": "KOSPI",
            "base_trade_date": "2026-01-02",
            "feature_origin": "kis_historical_universe_dataset_v1",
            "feature_snapshot": {"_feature_quality": {"is_dummy_data": False}},
            "entry_reference_price": 200.0,
            "day_return_pct": 8.0,
            "volume_ratio": 5.0,
            "turnover": 900_000_000.0,
        },
        {
            "ticker": "000003.KS",
            "stock_name": "Low",
            "market": "KOSPI",
            "base_trade_date": "2026-01-02",
            "feature_origin": "kis_historical_universe_dataset_v1",
            "feature_snapshot": {"_feature_quality": {"is_dummy_data": False}},
            "entry_reference_price": 50.0,
            "day_return_pct": -2.0,
            "volume_ratio": 0.7,
            "turnover": 20_000_000.0,
        },
    ]

    summary = enrich_historical_rows_with_prefilter(rows, rank_limit=2, max_candidates_per_market=2)

    assert summary["no_dummy_data"] is True
    assert summary["selected_total"] == 2
    assert "kis_operational_prefilter" not in rows[2]["feature_snapshot"]

    best = rows[1]["feature_snapshot"]["kis_operational_prefilter"]
    assert best["feature_origin"] == "kis_historical_prefilter_proxy"
    assert best["is_dummy_data"] is False
    assert best["historical_reconstruction"] is True
    assert best["rank"]["volume_rank"] == 1
    assert best["rank"]["fluctuation_rank"] == 1
    assert best["rank"]["volume_power_rank"] == 1
    assert best["quote"]["value_traded"] == 900_000_000.0
    assert best["flow"]["source_status"] == "historical_not_requested"

    flattened = flatten_kis_model_features(rows[1])
    assert flattened["kis_prefilter_present"] == 1.0
    assert flattened["kis_prefilter_rank_volume"] == 1.0
    assert flattened["kis_prefilter_rank_volume_power"] == 1.0
    assert flattened["kis_prefilter_quote_value_traded"] == 900_000_000.0
    assert flattened["kis_prefilter_flow_valid"] == 0.0
