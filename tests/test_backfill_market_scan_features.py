from multi_agent.tools.backfill_market_scan_features import _shared_feature_row


def test_shared_feature_row_preserves_runtime_numeric_and_flow_fields():
    row = _shared_feature_row(
        {
            "ticker": "000004.KS",
            "score": 81.4,
            "reasons": ["전략: exception_leader"],
            "theme_context": {
                "primary_theme": "전력기기",
                "theme_source": "dynamic",
                "theme_inference_status": "resolved",
            },
            "feature_snapshot": {
                "stock_name": "표시행",
                "antigrav": 84,
                "prob_5": "53.5%",
                "prob_clean": "49.2%",
                "whale": "67점 축적",
                "volume": "✅ 2.35",
                "day_return_pct": "+3.8%",
                "entry_reference_price": "12,300",
                "real_trend": "UP",
                "position": "상승초입",
                "leader_metrics": {
                    "kr_foreign_flow": -120.5,
                    "kr_institution_flow": 310.25,
                    "kr_retail_flow": -189.75,
                    "kr_volume_ratio": 2.35,
                    "kr_flow_consensus_buying": True,
                },
            },
        }
    )

    assert row["stock_name"] == "표시행"
    assert row["alpha_score"] == 84
    assert row["tech_score"] == 84
    assert row["ml_prob"] == 53.5
    assert row["prob_clean"] == 49.2
    assert row["whale_score"] == 67
    assert row["volume_ratio"] == 2.35
    assert row["day_return_pct"] == 3.8
    assert row["entry_reference_price"] == 12300.0
    assert row["foreigner_1d"] == -120.5
    assert row["institution_1d"] == 310.25
    assert row["retail_1d"] == -189.75
    assert row["whale_flow_1d"] == 189.75
    assert row["flow_window"] == "1d/3d/10d"
    assert row["flow_consensus_buying"] is True
    assert row["primary_theme"] == "전력기기"
    assert row["strategy"] == "exception_leader"
