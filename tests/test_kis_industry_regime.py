from modules.kis_industry_regime import (
    KIS_STOCK_INDUSTRY_INDEX_MAPPING_WARNING,
    build_kis_industry_regime_overlay,
    resolve_kis_market_index_code,
    resolve_kis_stock_industry_index_code,
)


def test_kis_industry_regime_overlay_scores_positive_index_momentum():
    bars = []
    for idx in range(22):
        close = 1000 + idx * 5
        bars.append(
            {
                "stck_bsop_date": f"202605{idx + 1:02d}",
                "bstp_nmix_oprc": str(close - 2),
                "bstp_nmix_hgpr": str(close + 5),
                "bstp_nmix_lwpr": str(close - 5),
                "bstp_nmix_prpr": str(close),
                "acml_vol": str(100000 + idx),
            }
        )

    overlay = build_kis_industry_regime_overlay(
        index_code="1001",
        industry_name="KOSDAQ",
        market="KOSDAQ",
        price_payload={"output": {"bstp_nmix_prpr": "1110", "bstp_nmix_prdy_ctrt": "1.2"}},
        daily_bars_payload={"output2": bars},
    )

    assert overlay["source_ok"] is True
    assert overlay["bar_count"] == 22
    assert overlay["return_5d_pct"] > 0
    assert overlay["trend"] in {"positive", "strong_positive"}
    assert overlay["confidence"] >= 0.8


def test_kis_industry_regime_overlay_keeps_missing_payload_as_warning_not_dummy():
    overlay = build_kis_industry_regime_overlay(index_code="1001")

    assert overlay["source_ok"] is False
    assert overlay["no_dummy_data"] is True
    assert "kis_industry_price_missing" in overlay["warnings"]
    assert "kis_industry_daily_bars_missing" in overlay["warnings"]


def test_kis_market_index_code_resolver_allows_only_verified_market_indices():
    kospi = resolve_kis_market_index_code("유가증권")
    kosdaq = resolve_kis_market_index_code("KSQ")
    unsupported = resolve_kis_market_index_code("UNKNOWN")

    assert kospi["mapping_verified"] is True
    assert kospi["index_code"] == "0001"
    assert kosdaq["mapping_verified"] is True
    assert kosdaq["index_code"] == "1001"
    assert unsupported["mapping_verified"] is False
    assert unsupported["index_code"] is None
    assert unsupported["no_dummy_data"] is True


def test_kis_stock_industry_index_mapping_is_blocked_without_official_index_code():
    mapping = resolve_kis_stock_industry_index_code(
        {
            "ticker": "005930",
            "market_name": "유가증권",
            "sector_name": "반도체",
            "standard_industry_code": "C261",
        }
    )

    assert mapping["mapping_verified"] is False
    assert mapping["mapping_status"] == "unmapped_unverified"
    assert mapping["index_code"] is None
    assert mapping["market_index_code"] == "0001"
    assert KIS_STOCK_INDUSTRY_INDEX_MAPPING_WARNING in mapping["warnings"]
    assert mapping["no_dummy_data"] is True
