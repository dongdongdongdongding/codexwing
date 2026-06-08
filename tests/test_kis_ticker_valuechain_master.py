from modules.kis_ticker_valuechain_master import build_ticker_valuechain_master


def _official_edge():
    return {
        "from_symbol": "095610.KQ",
        "to_symbol": "005930.KS",
        "relationship": "semiconductor_equipment_supplier_to_customer",
        "confidence": 0.99,
        "source_type": "exchange_disclosure",
        "source_urls": ["https://kind.krx.co.kr/external/2025/02/06/000180/20250206000436/70012.htm"],
        "source_title": "KIND 공급계약",
        "evidence_text": "KIND disclosure reports semiconductor manufacturing equipment supply contract with Samsung Electronics.",
        "evidence_collected_at": "2026-06-08T00:00:00+09:00",
    }


def test_build_ticker_valuechain_master_creates_static_profiles_from_official_edges():
    payload = build_ticker_valuechain_master(
        [_official_edge()],
        ticker_metadata_records=[
            {"ticker": "095610.KQ", "stock_name": "테스", "market_scope": "KOSDAQ", "primary_theme": "반도체"},
            {"ticker": "005930.KS", "stock_name": "삼성전자", "market_scope": "KOSPI", "primary_theme": "반도체"},
        ],
    )

    assert payload["version"] == "kis_ticker_valuechain_master_v1"
    assert payload["summary"]["ticker_profiles"] == 2
    assert payload["summary"]["verified_edges"] == 1
    assert payload["summary"]["blocked_edges"] == 0
    profiles = {row["ticker"]: row for row in payload["ticker_profiles"]}
    assert profiles["095610.KQ"]["stock_name"] == "테스"
    assert profiles["095610.KQ"]["downstream_symbols"] == ["005930.KS"]
    assert "equipment_supplier" in profiles["095610.KQ"]["valuechain_roles"]
    assert profiles["005930.KS"]["upstream_symbols"] == ["095610.KQ"]
    assert "customer" in profiles["005930.KS"]["valuechain_roles"]
    assert profiles["005930.KS"]["durability"] == "static_until_official_evidence_changes"


def test_build_ticker_valuechain_master_blocks_news_only_edges_from_profiles():
    payload = build_ticker_valuechain_master(
        [
            {
                **_official_edge(),
                "source_type": "news",
                "source_urls": ["https://example.com/news"],
            }
        ]
    )

    assert payload["summary"]["ticker_profiles"] == 0
    assert payload["summary"]["verified_edges"] == 0
    assert payload["summary"]["blocked_edges"] == 1
