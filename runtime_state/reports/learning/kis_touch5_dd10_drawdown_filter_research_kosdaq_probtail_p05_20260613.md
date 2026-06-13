# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T11:25:29+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob_tail_margin` topn=`3` prob_threshold=`0.5` tail_threshold=`0.0`
- base: status=`blocked` blockers=`['active_days_lt_20', 'min_low_5d_lt_neg10']` n=`83` days=`14` hit5=`75.9036` avg5=`6.54185` min_low=`-21.915669`
- filters_tested: `1120`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[2, 3, 4, 5, 6]` holdout_folds=`[7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`947` holdout_evaluated=`80` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`53` days=`8` hit5=`62.2642` avg5=`3.885862` min_low=`-31.118999`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_4767 | 39 | 6 | 13 | 100.0 | 10.122487 | -7.8413 | 4.601458 |
| 2 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_4243 | 33 | 5 | 11 | 100.0 | 9.581557 | -7.8413 | 4.601458 |
| 3 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_3719 | 30 | 4 | 10 | 100.0 | 9.440125 | -7.8413 | 4.601458 |
| 4 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_8765 | 57 | 9 | 19 | 98.2456 | 10.577195 | -9.401261 | 4.34529 |
| 5 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_6787 | 48 | 8 | 16 | 97.9167 | 10.275807 | -9.401261 | 4.297266 |
| 6 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_touch5_n_le_6106 | 42 | 7 | 14 | 97.619 | 9.982995 | -9.401261 | 4.253797 |
| 7 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_risk_score_le_55p9755 | 27 | 4 | 9 | 96.2963 | 11.726945 | -9.401261 | 4.060664 |
| 8 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_avg_close_5d_pct_ge_2p14245 | 18 | 3 | 6 | 94.4444 | 11.562394 | -9.401261 | 3.790259 |
| 9 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_avg_close_5d_pct_ge_2p54247 | 18 | 3 | 6 | 94.4444 | 11.562394 | -9.401261 | 3.790259 |
| 10 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_avg_mfe_5d_pct_le_15p3467 | 34 | 6 | 12 | 97.0588 | 9.393419 | -11.604404 | 4.172 |
| 11 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_sector_touch5_n_le_13 | 58 | 10 | 20 | 84.4828 | 5.939729 | -9.402705 | 2.335721 |
| 12 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_clean_defense_rate_pct_le_15p4814 | 13 | 4 | 5 | 92.3077 | 12.534666 | -11.604404 | 3.47827 |
| 13 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_stop5_rate_pct_ge_80p0206 | 13 | 4 | 5 | 92.3077 | 12.534666 | -11.604404 | 3.47827 |
| 14 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_feature_coverage_score_le_0p052632 | 60 | 10 | 20 | 95.0 | 11.483108 | -13.881985 | 3.871385 |
| 15 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_feature_coverage_score_le_0p263158 | 60 | 10 | 20 | 95.0 | 11.483108 | -13.881985 | 3.871385 |
| 16 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_feature_coverage_score_le_0p736842 | 60 | 10 | 20 | 95.0 | 11.483108 | -13.881985 | 3.871385 |
| 17 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_865 | 60 | 10 | 20 | 95.0 | 11.483108 | -13.881985 | 3.871385 |
| 18 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_theme_touch5_n_ge_884 | 60 | 10 | 20 | 95.0 | 11.483108 | -13.881985 | 3.871385 |
| 19 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_3824 | 51 | 9 | 17 | 94.1176 | 11.382001 | -13.881985 | 3.742542 |
| 20 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_6017 | 39 | 8 | 13 | 92.3077 | 12.51482 | -13.881985 | 3.47827 |
| 21 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_theme_touch5_n_ge_6071 | 39 | 8 | 13 | 92.3077 | 12.51482 | -13.881985 | 3.47827 |
| 22 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_clean_defense_rate_pct_le_15p9422 | 28 | 6 | 10 | 92.8571 | 11.168281 | -14.285185 | 3.55849 |
| 23 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_sector_clean_defense_rate_pct_le_5p81037 | 57 | 9 | 19 | 71.9298 | 4.066357 | -10.170965 | 0.5028 |
| 24 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_8044 | 30 | 6 | 10 | 90.0 | 13.526092 | -13.881985 | 3.141312 |
| 25 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_theme_touch5_n_ge_8123 | 30 | 6 | 10 | 90.0 | 13.526092 | -13.881985 | 3.141312 |
| 26 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_8908 | 27 | 5 | 9 | 88.8889 | 13.807227 | -13.881985 | 2.979075 |
| 27 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_theme_touch5_n_ge_8987 | 27 | 5 | 9 | 88.8889 | 13.807227 | -13.881985 | 2.979075 |
| 28 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_touch5_n_ge_13636 | 18 | 3 | 6 | 88.8889 | 14.983372 | -13.881985 | 2.979075 |
| 29 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_kis_theme_touch5_n_ge_13715 | 18 | 3 | 6 | 88.8889 | 14.983372 | -13.881985 | 2.979075 |
| 30 | shadow_risk_review | top3_prob_tail_margin_p0p5_tail0_close_failure_prior_market_clean_defense_rate_pct_le_15p5073 | 22 | 5 | 8 | 90.9091 | 10.852679 | -14.285185 | 3.274054 |
