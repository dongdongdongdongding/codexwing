from modules.kis_theme_valuechain import (
    VALUECHAIN_CONFIDENCE_FLOOR,
    build_kis_theme_valuechain_payload,
    extract_kis_ticker_category_record,
    kis_theme_valuechain_path,
    normalize_verified_valuechain_edge,
)


def _scan_row(ticker="005930.KS", market="KOSPI", stock_name="삼성전자"):
    code = ticker.split(".")[0]
    return {
        "ticker": ticker,
        "market": market,
        "base_trade_date": "2026-06-08",
        "stock_name": stock_name,
        "feature_snapshot": {
            "theme_context": {"primary_theme": "AI반도체", "theme_source": "theme_master"},
            "kis_sidecar": {
                "feature_origin": "kis_openapi_sidecar",
                "coverage": {"news_titles": True, "stock_info": True, "financial_ratio": True},
                "rank_contract": {"checked": True, "volume_rank": 4, "fluctuation_rank": 8, "volume_power_rank": 9},
                "vi_contract": {"checked": True, "triggered": True},
                "news_contract": {
                    "source": "kis_openapi",
                    "source_status": "ok",
                    "checked": True,
                    "news_count": 1,
                    "rows": [
                        {
                            "mksc_shrn_iscd": code,
                            "data_dt": "20260608",
                            "hts_pbnt_titl_cntt": "AI 반도체 공급 계약 수주",
                        }
                    ],
                },
                "stock_info_contract": {
                    "checked": True,
                    "ticker": code,
                    "product_name": stock_name,
                    "sector_name": "반도체",
                    "standard_industry_code": "C261",
                    "market_name": market,
                    "stock_type": "주권",
                },
                "financial_ratio_contract": {
                    "per": 11.2,
                    "pbr": 0.92,
                    "roe": 14.1,
                    "debt_ratio": 42.0,
                    "revenue_growth_rate": 13.5,
                },
                "model_candidate_features": {
                    "kis_value_traded": 123400000000,
                    "kis_day_change_pct": 2.7,
                    "kis_rank_volume": 4,
                    "kis_rank_fluctuation": 8,
                    "kis_rank_volume_power": 9,
                    "kis_vi_triggered": True,
                },
            },
        },
    }


def test_extract_kis_ticker_category_record_preserves_real_kis_sidecar_fields():
    record = extract_kis_ticker_category_record(_scan_row())

    assert record["ticker"] == "005930.KS"
    assert record["market"] == "KOSPI"
    assert record["market_scope"] == "KOSPI"
    assert record["stock_name"] == "삼성전자"
    assert record["primary_theme"] == "AI반도체"
    assert record["sector_name"] == "반도체"
    assert record["standard_industry_code"] == "C261"
    assert record["per"] == 11.2
    assert record["pbr"] == 0.92
    assert record["roe"] == 14.1
    assert record["volume_rank"] == 4
    assert record["vi_triggered"] is True
    assert record["news_count"] == 1
    assert record["no_dummy_data"] is True


def test_normalize_verified_valuechain_edge_requires_official_95pct_evidence():
    edge = normalize_verified_valuechain_edge(
        {
            "from_symbol": "095610.KQ",
            "to_symbol": "005930.KS",
            "relationship": "equipment_supplier_to_customer",
            "confidence": 0.99,
            "source_type": "exchange_disclosure",
            "source_urls": ["https://kind.krx.co.kr/external/2025/02/06/000180/20250206000436/70012.htm"],
            "evidence_text": "KIND disclosure states a semiconductor equipment supply contract with Samsung Electronics.",
        }
    )

    assert edge["production_valuechain"] is True
    assert edge["confidence"] >= VALUECHAIN_CONFIDENCE_FLOOR
    assert edge["source"] == "ticker:095610.KQ"
    assert edge["target"] == "ticker:005930.KS"
    assert edge["blocked_reasons"] == []


def test_single_source_url_string_is_preserved_for_verified_valuechain_edge():
    edge = normalize_verified_valuechain_edge(
        {
            "from_symbol": "095610.KQ",
            "to_symbol": "005930.KS",
            "relationship": "equipment_supplier_to_customer",
            "source_type": "exchange_disclosure",
            "source_url": "https://kind.krx.co.kr/external/2025/02/06/000180/20250206000436/70012.htm",
            "evidence_text": "KIND disclosure states a semiconductor equipment supply contract with Samsung Electronics.",
        }
    )

    assert edge["production_valuechain"] is True
    assert edge["source_urls"] == ["https://kind.krx.co.kr/external/2025/02/06/000180/20250206000436/70012.htm"]


def test_news_or_web_search_only_edge_is_blocked_below_production_threshold():
    edge = normalize_verified_valuechain_edge(
        {
            "from_symbol": "095610.KQ",
            "to_symbol": "005930.KS",
            "relationship": "rumored_supplier",
            "confidence": 0.99,
            "source_type": "news",
            "source_urls": ["https://example.com/news"],
            "evidence_text": "A news article says the companies may be connected.",
        }
    )

    assert edge["production_valuechain"] is False
    assert edge["confidence"] < VALUECHAIN_CONFIDENCE_FLOOR
    assert "valuechain_source_type_not_95pct_trusted" in edge["blocked_reasons"]
    assert "valuechain_confidence_below_95pct" in edge["blocked_reasons"]


def test_build_kis_theme_valuechain_payload_filters_market_and_counts_verified_edges():
    payload = build_kis_theme_valuechain_payload(
        [
            _scan_row("005930.KS", "KOSPI", "삼성전자"),
            _scan_row("086520.KQ", "KOSDAQ", "에코프로"),
        ],
        market="KOSPI",
        verified_valuechain_sources=[
            {
                "from_symbol": "095610.KQ",
                "to_symbol": "005930.KS",
                "relationship": "equipment_supplier_to_customer",
                "confidence": 0.99,
                "source_type": "exchange_disclosure",
                "source_urls": ["https://kind.krx.co.kr/external/2025/02/06/000180/20250206000436/70012.htm"],
                "evidence_text": "KIND disclosure states a semiconductor equipment supply contract with Samsung Electronics.",
            },
            {
                "from_symbol": "086520.KQ",
                "to_symbol": "005930.KS",
                "relationship": "media_only_peer",
                "confidence": 0.96,
                "source_type": "web_search",
                "source_urls": ["https://example.com/search-result"],
                "evidence_text": "Search result without official confirmation.",
            },
        ],
    )

    assert payload["market_scope"] == "KOSPI"
    assert payload["summary"]["ticker_category_records"] == 1
    assert payload["summary"]["verified_valuechain_edges"] == 1
    assert payload["summary"]["blocked_valuechain_edges"] == 1
    assert any(edge["edge_kind"] == "verified_valuechain" for edge in payload["edges"])
    assert payload["theme_daily_state"][0]["theme_name"] == "AI반도체"


def test_kis_theme_valuechain_path_keeps_kospi_and_kosdaq_separate():
    assert kis_theme_valuechain_path("KR").name == "KR.json"
    assert kis_theme_valuechain_path("KOSPI").name == "KOSPI.json"
    assert kis_theme_valuechain_path("KOSDAQ").name == "KOSDAQ.json"
