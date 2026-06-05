from multi_agent.tools.run_kis_operational_kr_scan import _prefilter_market_payload


def test_prefilter_market_payload_compacts_kis_features_without_dummy_values():
    prefilter = {
        "contract_version": "kis_operational_prefilter_v1",
        "generated_at": "2026-06-05T09:35:00",
        "artifacts": {"json": "runtime_state/reports/validation/kis_operational_prefilter.json"},
        "markets": {
            "KOSPI": {
                "seed_count": 2,
                "vi_seed_count": 1,
                "quote_fetch_count": 2,
                "flow_fetch_count": 1,
                "selected_count": 1,
                "rejected_count": 1,
                "endpoint_summary": [{"name": "KOSPI:volume_rank", "ok": True, "row_count": 2}],
                "selected_tickers": ["005930.KS"],
                "selected": [
                    {
                        "market": "KOSPI",
                        "ticker": "005930.KS",
                        "code": "005930",
                        "name": "삼성전자",
                        "sources": ["volume_rank", "vi_status"],
                        "rank": {"volume_rank": 1},
                        "rank_raw": {"volume_rank": {"large": "raw payload should not be copied"}},
                        "selection_score": 122.5,
                        "score_components": {"value_traded": 20.0, "vi_triggered": 8.0},
                        "vi_triggered": True,
                        "quote_ok": True,
                        "value_traded": 123456789000,
                        "prev_volume_ratio": 155.2,
                        "quote": {"source_status": "ok", "current_price": 81200, "per": 15.1, "pbr": 1.2},
                        "flow_ok": True,
                        "flow": {
                            "flow_source": "kis_openapi",
                            "valid": True,
                            "whale_score": 71.0,
                            "foreigner_1d": 10,
                            "institution_1d": 20,
                            "retail_1d": -30,
                        },
                    }
                ],
                "rejected_sample": [],
            }
        },
        "warnings": [],
    }

    payload = _prefilter_market_payload(prefilter, "KOSPI")
    candidate = payload["selected"][0]

    assert payload["kis_only"] is True
    assert payload["is_dummy_data"] is False
    assert candidate["feature_origin"] == "kis_openapi_prefilter"
    assert candidate["is_dummy_data"] is False
    assert candidate["rank"] == {"volume_rank": 1}
    assert "rank_raw" not in candidate
    assert candidate["quote"]["value_traded"] == 123456789000
    assert candidate["quote"]["prev_volume_ratio"] == 155.2
    assert candidate["quote"]["per"] == 15.1
    assert candidate["flow"]["flow_source"] == "kis_openapi"
    assert candidate["score_components"]["vi_triggered"] == 8.0
