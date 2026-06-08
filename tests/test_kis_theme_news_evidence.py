from modules.kis_theme_news_evidence import build_kis_theme_news_evidence, format_kis_theme_news_summary


def _kis_sidecar():
    return {
        "feature_origin": "kis_openapi_sidecar",
        "contract_version": "kis_operational_adapter_v1",
        "coverage": {"news_titles": True, "stock_info": True},
        "rank_contract": {"checked": True, "volume_rank": 4, "volume_power_rank": 9},
        "vi_contract": {"checked": True, "triggered": True},
        "news_contract": {
            "source": "kis_openapi",
            "source_status": "ok",
            "checked": True,
            "news_count": 2,
            "rows": [
                {"dorg": "KIS", "data_dt": "20260608", "data_tm": "091500", "hts_pbnt_titl_cntt": "AI 반도체 공급 계약 수주"},
                {"dorg": "KIS", "data_dt": "20260608", "data_tm": "092000", "title": "신규 정책 지원 기대"},
            ],
        },
        "stock_info_contract": {
            "checked": True,
            "sector_name": "반도체",
            "standard_industry_code": "C261",
            "market_name": "KOSPI",
            "stock_type": "주권",
        },
        "model_candidate_features": {
            "kis_news_title_count": 2,
            "kis_stock_sector_name": "반도체",
            "kis_stock_standard_industry_code": "C261",
        },
    }


def test_build_kis_theme_news_evidence_combines_real_sidecar_prefilter_and_theme():
    row = {
        "ticker": "005930.KS",
        "market": "KOSPI",
        "feature_snapshot": {
            "theme_context": {"primary_theme": "AI반도체", "theme_source": "theme_master"},
            "kis_sidecar": _kis_sidecar(),
            "kis_operational_prefilter": {
                "feature_origin": "kis_openapi_prefilter",
                "sources": ["volume_rank", "vi_status"],
                "selection_score": 122.5,
                "rank": {"volume_rank": 4},
                "vi_triggered": True,
                "quote_ok": True,
                "flow_ok": True,
            },
        },
    }

    evidence = build_kis_theme_news_evidence(row)

    assert evidence["contract_version"] == "kis_theme_news_evidence_v1"
    assert evidence["kis_backed"] is True
    assert evidence["no_dummy_data"] is True
    assert evidence["theme"]["primary_theme"] == "AI반도체"
    assert evidence["theme"]["kis_sector_name"] == "반도체"
    assert evidence["news"]["news_count"] == 2
    assert "contract_order" in evidence["news"]["positive_tags"]
    assert evidence["market_action"]["vi_triggered"] is True
    assert evidence["evidence_strength_level"] == "strong"

    summary = format_kis_theme_news_summary(evidence)
    assert "뉴스 2건" in summary
    assert "AI 반도체 공급 계약 수주" in summary


def test_format_kis_theme_news_summary_does_not_label_local_theme_as_kis_backed():
    evidence = build_kis_theme_news_evidence({"ticker": "005930.KS", "theme_context": {"primary_theme": "반도체"}})

    assert evidence["available"] is True
    assert evidence["kis_backed"] is False
    assert format_kis_theme_news_summary(evidence) == ""
