from __future__ import annotations

import pandas as pd

from multi_agent.tools import augment_kis_historical_proxy_with_static_sidecar_master as tool


def test_build_static_master_ignores_unknown_and_drops_conflicts() -> None:
    sidecar = pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "market": "KOSPI",
                "kis_stock_type": "UNKNOWN",
                "kis_stock_par_value": 500.0,
                "kis_stock_listed_shares": 1000.0,
            },
            {
                "ticker": "000001",
                "market": "KOSPI",
                "kis_stock_type": "101",
                "kis_stock_par_value": 500.0,
                "kis_stock_listed_shares": 1000.0,
            },
            {
                "ticker": "000002.KS",
                "market": "KOSPI",
                "kis_stock_type": "101",
                "kis_stock_par_value": 500.0,
                "kis_stock_listed_shares": 1000.0,
            },
            {
                "ticker": "000002.KS",
                "market": "KOSPI",
                "kis_stock_type": "101",
                "kis_stock_par_value": 500.0,
                "kis_stock_listed_shares": 2000.0,
            },
        ]
    )

    master, summary = tool.build_static_master(sidecar)
    keyed = master.set_index("__join_ticker")

    assert keyed.loc["000001", "kis_stock_type"] == "101"
    assert keyed.loc["000001", "kis_stock_listed_shares"] == 1000.0
    assert "kis_stock_listed_shares" not in keyed.loc["000002"].dropna().index
    assert summary["conflict_count"] == 1
    assert summary["no_dummy_data"] is True


def test_static_master_augmentation_fills_missing_only() -> None:
    proxy = pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "market": "KOSPI",
                "base_trade_date": "2026-01-02",
                "kis_stock_sector_name": "instrument-sector",
                "kis_stock_standard_industry_code": None,
            },
            {
                "ticker": "000002.KS",
                "market": "KOSPI",
                "base_trade_date": "2026-01-02",
                "kis_stock_sector_name": None,
                "kis_stock_standard_industry_code": None,
            },
        ]
    )
    master = pd.DataFrame(
        [
            {
                "__join_market": "KOSPI",
                "__join_ticker": "000001",
                "__static_feature_count": 2,
                "kis_stock_sector_name": "sidecar-sector",
                "kis_stock_standard_industry_code": "032902",
            }
        ]
    )

    augmented, summary = tool.augment_market_proxy_with_static_master(
        proxy,
        master,
        market="KOSPI",
        generated_at="2026-06-13T00:00:00+00:00",
    )

    assert augmented.loc[0, "kis_stock_sector_name"] == "instrument-sector"
    assert augmented.loc[0, "kis_stock_standard_industry_code"] == "032902"
    assert pd.isna(augmented.loc[1, "kis_stock_standard_industry_code"])
    assert augmented.loc[0, "kis_static_sidecar_master_augmented"] == 1
    assert augmented.loc[1, "kis_static_sidecar_master_augmented"] == 0
    assert summary["augmented_rows"] == 1
    assert summary["feature_fill_counts_top"][0]["feature"] == "kis_stock_standard_industry_code"
