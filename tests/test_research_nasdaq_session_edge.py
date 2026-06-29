from __future__ import annotations

import pandas as pd

from multi_agent.tools.research_nasdaq_session_edge import (
    _condition_specs,
    add_ranks_and_alpha,
    aggregate_symbol_sessions,
    metric_block,
    search_edges,
)


def _intraday_fixture() -> pd.DataFrame:
    idx = pd.to_datetime(
        [
            "2026-06-02 04:00",
            "2026-06-02 09:25",
            "2026-06-02 09:30",
            "2026-06-02 10:25",
            "2026-06-02 15:55",
            "2026-06-02 16:00",
            "2026-06-02 19:55",
        ]
    ).tz_localize("America/New_York")
    return pd.DataFrame(
        {
            "Open": [101, 104, 105, 106, 108, 108, 109],
            "High": [102, 105, 106, 107, 109, 109, 110],
            "Low": [100, 103, 104, 105, 107, 107, 108],
            "Close": [102, 105, 106, 107, 108, 109, 110],
            "Volume": [1000, 2000, 3000, 4000, 5000, 2000, 3000],
        },
        index=idx,
    )


def _raw_daily_fixture() -> pd.DataFrame:
    dates = pd.bdate_range("2026-06-02", periods=6)
    return pd.DataFrame(
        {
            "date": dates,
            "open": [105, 109, 110, 111, 112, 113],
            "high": [111, 112, 113, 114, 116, 117],
            "low": [104, 108, 109, 110, 111, 112],
            "close": [108, 110, 111, 112, 115, 116],
            "volume": [1000] * 6,
        }
    )


def test_aggregate_symbol_sessions_creates_distinct_session_entries():
    date = pd.Timestamp("2026-06-02")
    rows = aggregate_symbol_sessions(
        "NVDA",
        _intraday_fixture(),
        daily_rows={
            ("NVDA", date): {
                "symbol": "NVDA",
                "date": date,
                "name": "NVIDIA",
                "prev_daily_close": 100.0,
                "liq20": 1_000_000_000.0,
                "liq60": 900_000_000.0,
                "ret_5d": 5.0,
                "ret_20d": 10.0,
                "ret_60d": 20.0,
                "atr_pct": 3.0,
                "vol_ratio": 1.5,
                "rsi14": 60.0,
                "ma60_slope": 1.0,
                "ma200_slope": 1.0,
                "dist_hi20": 0.0,
                "dist_hi120": 0.0,
            }
        },
        raw_daily=_raw_daily_fixture(),
    )

    by_mode = {row["session_mode"]: row for row in rows}

    assert set(by_mode) == {"premarket", "regular_open", "regular_close", "afterhours"}
    assert by_mode["premarket"]["entry_price"] == 105.0
    assert by_mode["regular_open"]["entry_price"] == 107.0
    assert by_mode["regular_close"]["entry_price"] == 108.0
    assert by_mode["afterhours"]["entry_price"] == 110.0
    assert round(by_mode["premarket"]["session_ret"], 6) == 5.0
    assert by_mode["afterhours"]["session_ret"] > 0.0
    assert by_mode["premarket"]["touch5_3d"] == 1.0


def test_session_search_surfaces_recent_shadow_candidate_without_production_promotion():
    dates = pd.bdate_range("2026-06-02", periods=40)
    rows = []
    for date in dates:
        for idx in range(3):
            rows.append(
                {
                    "date": date,
                    "symbol": f"SYM{idx}",
                    "name": f"Symbol {idx}",
                    "session_mode": "premarket",
                    "entry_price": 100.0,
                    "prev_daily_close": 95.0,
                    "session_ret": 5.0 if idx == 0 else -1.0,
                    "anchor_ret": 5.0 if idx == 0 else -1.0,
                    "session_range_pct": 1.0,
                    "session_close_loc": 0.9 if idx == 0 else 0.2,
                    "session_volume": 1000.0,
                    "session_dollar_volume": 2_000_000.0 if idx == 0 else 100_000.0,
                    "session_volume_share_regular": 0.4,
                    "session_bars": 10,
                    "liq20": 1_000_000_000.0,
                    "liq60": 1_000_000_000.0,
                    "ret_5d": 5.0,
                    "ret_20d": 10.0,
                    "ret_60d": 15.0,
                    "atr_pct": 3.0,
                    "vol_ratio": 1.5,
                    "rsi14": 60.0,
                    "ma60_slope": 1.0,
                    "ma200_slope": 1.0,
                    "dist_hi20": 0.0,
                    "dist_hi120": 0.0,
                    "fwd_close_ret_3d": 2.0 if idx == 0 else -1.0,
                    "fwd_close_ret_5d": 3.0 if idx == 0 else -2.0,
                    "fwd_high_ret_3d": 6.0 if idx == 0 else 1.0,
                    "fwd_high_ret_5d": 7.0 if idx == 0 else 2.0,
                    "fwd_low_ret_3d": -1.0,
                    "fwd_low_ret_5d": -2.0,
                    "touch5_3d": 1.0 if idx == 0 else 0.0,
                    "touch5_5d": 1.0 if idx == 0 else 0.0,
                    "dd5_3d": 0.0,
                    "dd5_5d": 0.0,
                    "ft_5_5": 1.0 if idx == 0 else 0.0,
                    "same_day_touch_stop_ambiguous": 0.0,
                }
            )
    panel = add_ranks_and_alpha(pd.DataFrame(rows))
    results = search_edges(panel, topn_values=[1])

    assert results
    top = results[0]
    assert top["session_mode"] == "premarket"
    assert top["recent_shadow_ready"] is True
    assert top["promotion_ready"] is False
    assert any("n_below_min" in reason for reason in top["promotion_blocking_reasons"])

    metrics = metric_block(panel[panel["symbol"].eq("SYM0")])
    assert metrics["ret5_pos_rate"] == 1.0
    assert metrics["touch3"] == 1.0


def test_condition_specs_include_regular_close_shadow_edge_families():
    specs = {name: (mode, dict(items)) for name, mode, items in _condition_specs()}

    assert specs["regular_close_strength_liq_trend"][0] == "regular_close"
    assert specs["regular_close_strength_liq_trend"][1]["r_liq20"] == 0.75
    assert specs["regular_close_core_close_ma200"][1]["r_session_close_loc"] == 0.65
    assert specs["regular_close_core_ma200"][1]["r_ma200_slope"] == 0.65
