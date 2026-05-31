from modules.scan_universe_admission import _extract_feature_columns


def test_runtime_feature_extractor_reads_display_and_nested_scan_fields():
    row = {
        "티커": "005930.KS",
        "Antigrav": 91,
        "Decision Score": 88.5,
        "AI확률": "55.0%",
        "정밀확률": "48.0%",
        "수급": "83.0점 당일+3일 순매수",
        "거래량": "✅ 2.40",
        "전일비": "+3.25%",
        "매수가(-2%)": "73,200",
        "feature_snapshot": {
            "kr_universe_role": "EXPLOSIVE_LEADER",
            "scanner_timeframe_profile": "DAILY_PRIMARY_WITH_1H_REFRESH",
        },
        "leader_metrics": {
            "kr_flow_consensus_buying": True,
            "kr_retail_dominant": False,
        },
    }

    features = _extract_feature_columns(row, market="KOSPI")

    assert features["alpha_score"] == 91.0
    assert features["tech_score"] == 91.0
    assert features["ml_prob"] == 55.0
    assert features["prob_clean"] == 48.0
    assert features["whale_score"] == 83.0
    assert features["volume_ratio"] == 2.4
    assert features["day_return_pct"] == 3.25
    assert features["entry_reference_price"] == 73200.0
    assert features["kr_universe_role"] == "EXPLOSIVE_LEADER"
    assert features["scanner_timeframe_profile"] == "DAILY_PRIMARY_WITH_1H_REFRESH"
    assert features["flow_consensus_buying"] is True
