from __future__ import annotations

import pandas as pd

from multi_agent.tools import augment_kis_historical_proxy_with_sidecar_cache as tool


def test_augment_market_proxy_joins_exact_ticker_date_only() -> None:
    proxy = pd.DataFrame(
        [
            {
                "ticker": "000001.KS",
                "market": "KOSPI",
                "base_trade_date": "2026-05-01",
                "kis_whale_score": None,
                "buy_premium_target_hit_5d": True,
            },
            {
                "ticker": "000001.KS",
                "market": "KOSPI",
                "base_trade_date": "2026-05-02",
                "kis_whale_score": None,
                "buy_premium_target_hit_5d": False,
            },
        ]
    )
    sidecar = pd.DataFrame(
        [
            {
                "ticker": "000001",
                "market": "KOSPI",
                "base_trade_date": "2026-05-01",
                "kis_whale_score": 88.0,
                "kis_foreigner_1d": 1000.0,
                "buy_premium_target_hit_5d": False,
            }
        ]
    )

    augmented, summary = tool.augment_market_proxy(proxy, sidecar, market="KOSPI", generated_at="2026-06-13T00:00:00+00:00")

    assert summary["matched_rows"] == 1
    assert summary["matched_days"] == 1
    assert augmented.loc[0, "kis_whale_score"] == 88.0
    assert augmented.loc[0, "kis_foreigner_1d"] == 1000.0
    assert pd.isna(augmented.loc[1, "kis_whale_score"])
    assert augmented.loc[0, "buy_premium_target_hit_5d"] == True
    assert augmented.loc[0, "kis_sidecar_cache_augmented"] == 1
    assert augmented.loc[1, "kis_sidecar_cache_augmented"] == 0
    assert augmented.loc[0, "kis_sidecar_cache_leakage_policy"] == "exact_ticker_date_only_no_forward_fill"


def test_augment_market_proxy_prefers_duplicate_with_more_real_features() -> None:
    proxy = pd.DataFrame(
        [
            {
                "ticker": "A000123",
                "market": "KOSDAQ",
                "trade_date": "2026-05-03",
                "kis_whale_score": None,
                "kis_stock_sector_name": None,
            }
        ]
    )
    sidecar = pd.DataFrame(
        [
            {
                "ticker": "000123.KQ",
                "market": "KOSDAQ",
                "trade_date": "2026-05-03",
                "kis_whale_score": None,
                "kis_stock_sector_name": "",
            },
            {
                "ticker": "000123",
                "market": "KOSDAQ",
                "trade_date": "2026-05-03",
                "kis_whale_score": 42.0,
                "kis_stock_sector_name": "2차전지",
            },
        ]
    )

    augmented, summary = tool.augment_market_proxy(proxy, sidecar, market="KOSDAQ")

    assert summary["sidecar_dedupe"]["duplicate_key_rows_removed"] == 1
    assert augmented.loc[0, "kis_whale_score"] == 42.0
    assert augmented.loc[0, "kis_stock_sector_name"] == "2차전지"


def test_parse_market_path_requires_explicit_market() -> None:
    market, path = tool._parse_market_path("KOSPI=/tmp/cache.pkl")

    assert market == "KOSPI"
    assert str(path) == "/tmp/cache.pkl"


def test_build_report_can_write_matched_only_cache(tmp_path) -> None:
    proxy_path = tmp_path / "proxy.pkl"
    sidecar_path = tmp_path / "sidecar.pkl"
    output_path = tmp_path / "augmented.pkl"
    matched_only_path = tmp_path / "matched_only.pkl"
    pd.DataFrame(
        [
            {"ticker": "000001.KS", "market": "KOSPI", "base_trade_date": "2026-05-01", "kis_whale_score": None},
            {"ticker": "000002.KS", "market": "KOSPI", "base_trade_date": "2026-05-01", "kis_whale_score": None},
        ]
    ).to_pickle(proxy_path)
    pd.DataFrame(
        [{"ticker": "000001", "market": "KOSPI", "base_trade_date": "2026-05-01", "kis_whale_score": 11.0}]
    ).to_pickle(sidecar_path)

    report = tool.build_report(
        sidecar_cache=sidecar_path,
        proxy_caches={"KOSPI": proxy_path},
        output_caches={"KOSPI": output_path},
        matched_only_output_caches={"KOSPI": matched_only_path},
    )
    matched_only = pd.read_pickle(matched_only_path)

    assert report["markets"][0]["matched_rows"] == 1
    assert len(pd.read_pickle(output_path)) == 2
    assert len(matched_only) == 1
    assert matched_only.iloc[0]["ticker"] == "000001.KS"
