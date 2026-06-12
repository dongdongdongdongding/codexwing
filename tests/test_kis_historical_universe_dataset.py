from __future__ import annotations

import pandas as pd

from modules.kis_historical_universe_dataset import InstrumentRecord, build_historical_rows_for_symbol


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
