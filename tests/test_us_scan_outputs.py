from modules.scanner_services import build_us_scan_outputs


def test_build_us_scan_outputs_accepts_phase25_trace_fields():
    outputs = build_us_scan_outputs(
        sym="NVDA",
        stock_name="NVIDIA",
        alpha_score=82,
        whale_score=71,
        real_trend="UP",
        prev_pct_change=1.25,
        consec_days=2,
        rs_tag="RS+",
        setup={
            "Volume Ratio": 1.7,
            "Volume Confirmed": True,
            "Entry Price": 100.0,
            "Target Price": 112.0,
            "Stop Loss": 96.0,
            "ATR Stop %": "-4%",
            "Max Hold Days": 3,
        },
        strategy_tag="BUY",
        surge_tag="Surge",
        wr=61,
        position="Rising",
        news_tag="AI",
        prob_5=58.2,
        prob_clean=55.1,
        decision_score=76.4,
        conviction_score=69.5,
        tier="T1",
        tier_sort=1,
        is_amex=False,
        tech_score=74,
        verdict_label="WATCHLIST",
        market_gate="GREEN",
        kospi_chg=0.0,
        phase25_variant="phase25_us_swing",
        phase25_prob=62.5,
        phase25_signal_direction="normal",
        phase25_raw_auc=0.61,
        phase25_oos_auc=0.59,
        phase25_oos_win_rate_pct=64.0,
        phase25_oos_avg_return_pct=3.2,
        model_trace_status="phase25_chosen",
    )

    assert outputs["res_data"]["phase25_signal_direction"] == "normal"
    assert outputs["res_data"]["phase25_oos_win_rate_pct"] == 64.0
    assert outputs["db_payload"]["phase25_signal_direction"] == "normal"
    assert outputs["db_payload"]["phase25_oos_avg_return_pct"] == 3.2
