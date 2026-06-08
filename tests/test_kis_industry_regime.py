from modules.kis_industry_regime import build_kis_industry_regime_overlay


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
