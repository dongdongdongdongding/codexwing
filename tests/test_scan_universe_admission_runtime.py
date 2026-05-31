from modules.scan_universe_admission import _extract_feature_columns, build_scan_universe_admission_records


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
    assert "turnover" in features["feature_missing_keys"]
    assert features["kr_universe_role"] == "EXPLOSIVE_LEADER"
    assert features["scanner_timeframe_profile"] == "DAILY_PRIMARY_WITH_1H_REFRESH"
    assert features["flow_consensus_buying"] is True


def test_admission_records_include_full_result_interpretation():
    rows = [
        {
            "티커": "005930.KS",
            "종목명": "삼성전자",
            "Antigrav": 91,
            "Decision Score": 88.5,
            "AI확률": "55.0%",
            "정밀확률": "48.0%",
            "수급": "83.0점 당일+3일 순매수",
            "거래량": "✅ 2.40",
            "전일비": "+3.25%",
            "매수가(-2%)": "73,200",
            "leader_metrics": {
                "kr_turnover": 1234567890,
                "kr_foreign_flow": 100,
                "kr_institution_flow": 50,
                "kr_retail_flow": -150,
            },
            "flow": {
                "foreigner_3d": 200,
                "institution_3d": 80,
                "retail_3d": -280,
            },
        },
        {
            "티커": "000660.KS",
            "종목명": "SK하이닉스",
            "Antigrav": 80,
            "Decision Score": 78,
            "AI확률": "45.0%",
            "정밀확률": "42.0%",
            "수급": "55.0점 혼조",
            "거래량": "⚠️ 0.70",
            "전일비": "-1.20%",
            "매수가(-2%)": "120,000",
            "leader_metrics": {"kr_turnover": 987654321},
        },
    ]

    result = build_scan_universe_admission_records(rows, market="KOSPI", limit=1, include_near_miss=True)

    assert result["scored_count"] == 2
    assert len(result["all_records"]) == 2
    first = result["all_records"][0]
    interpretation = first["scan_result_interpretation"]
    assert interpretation["model_decision"] in {"운영 통과", "기준 미달"}
    assert interpretation["threshold_gap_pct_points"] is not None
    assert interpretation["drivers"]
    assert first["scan_universe_admission"]["feature_missing_keys"] == []
