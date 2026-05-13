from modules.entry_readiness import build_entry_readiness_analysis


def test_entry_readiness_blocks_extreme_overheat():
    analysis = build_entry_readiness_analysis(
        candidate={"decision_score": 92.0, "prob_clean": 78.0, "real_trend": "UP", "volume_ratio": 3.2},
        price={
            "current_price": 100000.0,
            "return_5d_pct": 31.0,
            "return_20d_pct": 74.0,
            "return_60d_pct": 166.0,
            "pct_from_52w_high": -1.8,
            "volume_ratio_20d": 3.4,
            "ma5": 88000.0,
            "ma20": 72000.0,
            "prior_20d_high": 99000.0,
            "gap_up_after_long_bullish": True,
            "gap_up_pct": 4.1,
            "close_location_pct": 82.0,
        },
        prediction={"expected_edge_score": 6.0},
        trade_plan={"entry_policy": "open/reference", "target_tp_pct": 20.0, "stop_sl_pct": -5.0, "hold_days": 5},
        news={"sentiment_score": 0.4},
        loss_risk_score=38.0,
    )

    assert analysis["quality"]["grade"] in {"A", "B+"}
    assert analysis["upside"]["chase_risk_level"] == "신규 진입 금지"
    assert analysis["final_buy_judgment"]["action"] == "매수 금지"
    assert any(row["code"] == "RET_60D_GT_150" and row["triggered"] for row in analysis["upside"]["filters"])
    assert analysis["entry_strategy"]["mode"] == "blocked"
    assert "신규 매수 금지" in analysis["entry_strategy"]["primary_condition"]
    assert analysis["risk_management"]["stop_price"] is not None


def test_entry_readiness_allows_valid_pullback_conditionally():
    analysis = build_entry_readiness_analysis(
        candidate={"relative_rank_score": 78.0, "prob_clean": 74.0, "real_trend": "UP", "volume_ratio": 1.5},
        price={
            "current_price": 100.0,
            "return_5d_pct": 4.0,
            "return_20d_pct": 13.0,
            "return_60d_pct": 32.0,
            "pct_from_52w_high": -18.0,
            "volume_ratio_20d": 1.6,
            "ma5": 99.0,
            "ma20": 96.0,
            "prior_20d_high": 101.0,
            "gap_up_pct": 0.6,
            "close_location_pct": 72.0,
        },
        prediction={"expected_edge_score": 4.0},
        trade_plan={"entry_policy": "-2% limit", "target_tp_pct": 10.0, "stop_sl_pct": -10.0, "hold_days": 5},
        news={"sentiment_score": 0.2},
        loss_risk_score=30.0,
    )

    assert analysis["upside"]["chase_risk_level"] == "낮음"
    assert analysis["timing"]["timing_label"] in {"양호", "조건부 양호"}
    assert analysis["final_buy_judgment"]["action"] in {"즉시 매수 가능", "조건부 매수 가능"}
    assert analysis["entry_strategy"]["mode"] == "entry_allowed"
    assert analysis["entry_strategy"]["pullback_support_price"] == 99.0
    assert analysis["risk_management"]["data_source"] == "support_resistance_stop_from_price_snapshot"


def test_entry_readiness_marks_missing_data_without_faking_fundamentals():
    analysis = build_entry_readiness_analysis(
        candidate={},
        price={},
        prediction={},
        trade_plan={},
        news={},
        loss_risk_score=None,
    )

    assert analysis["quality"]["source_status"] == "not_connected"
    assert analysis["quality"]["grade"] in {"C", "D"}
    assert any("미연결" in warning for warning in analysis["warnings"])
    assert analysis["data_coverage"]["coverage_pct"] == 0.0
    assert analysis["entry_strategy"]["data_source"] == "price_snapshot_ma_volume_return"
