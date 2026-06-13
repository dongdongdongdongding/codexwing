# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T13:18:51+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSPI`
- selection: score_mode=`prob_plus_tail` topn=`2` prob_threshold=`0.8` tail_threshold=`0.85`
- compound_filter: depth=`1` single_limit=`60` candidate_limit=`0`
- base: status=`shadow_ready` blockers=`['active_days_lt_15']` n=`93` days=`14` hit5=`87.0968` avg5=`15.093948` min_low=`-8.919727`
- filters_tested: `1066`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`1066` sample=`0` low_safe=`724` hit_low_safe=`667` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3, 4, 5]` holdout_folds=`[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`715` holdout_evaluated=`715` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`shadow_risk_review` n=`36` days=`6` hit5=`88.8889` avg5=`32.236433` min_low=`-10.089127`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`697` sample=`0` low_safe=`612` hit_low_safe=`591` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`rolling_prior_shadow_ready` validation=`rolling_prior_oos_next_fold_walk_forward_predictions` min_prior_folds=`5` evaluated_steps=`15` selected=`34` deployment_ready=`False`
- rolling_prior_aggregate: status=`shadow_risk_review` n=`34` days=`5` runs=`21` hit5=`94.1176` avg5=`21.329321` min_low=`-17.463325` expected_net=`3.742542` blockers=`['active_days_lt_15', 'min_low_5d_lt_neg10']`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_30p6796 | 63 | 8 | 36 | 100.0 | 38.376499 | -8.42246 | 4.601458 |
| 2 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p36554 | 18 | 3 | 9 | 100.0 | 33.408735 | -4.011814 | 4.601458 |
| 3 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p31215 | 18 | 3 | 9 | 100.0 | 33.408735 | -4.011814 | 4.601458 |
| 4 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_close_location_pct_ge_11p7647 | 79 | 11 | 42 | 100.0 | 27.316639 | -7.289003 | 4.601458 |
| 5 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_4p84699 | 66 | 9 | 37 | 100.0 | 28.496989 | -7.120743 | 4.601458 |
| 6 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_close_location_pct_ge_16p1232 | 79 | 11 | 42 | 100.0 | 27.133704 | -8.252071 | 4.601458 |
| 7 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_sector_avg_mfe_5d_pct_ge_19p9763 | 64 | 8 | 36 | 100.0 | 25.495237 | -6.888232 | 4.601458 |
| 8 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_failure_rate_pct_ge_54p08 | 34 | 4 | 17 | 100.0 | 24.287617 | -4.641544 | 4.601458 |
| 9 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_neg0p032468 | 34 | 4 | 17 | 100.0 | 24.287617 | -4.641544 | 4.601458 |
| 10 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p3346 | 34 | 4 | 17 | 100.0 | 24.287617 | -4.641544 | 4.601458 |
| 11 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_risk_score_ge_54p176 | 34 | 4 | 17 | 100.0 | 24.287617 | -4.641544 | 4.601458 |
| 12 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_23p9252 | 72 | 8 | 36 | 100.0 | 26.394867 | -9.506833 | 4.601458 |
| 13 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_failure_rate_pct_ge_51p6225 | 50 | 5 | 25 | 100.0 | 25.733837 | -7.289003 | 4.601458 |
| 14 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_0p515842 | 50 | 5 | 25 | 100.0 | 25.733837 | -7.289003 | 4.601458 |
| 15 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p4322 | 50 | 5 | 25 | 100.0 | 25.733837 | -7.289003 | 4.601458 |
| 16 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p04538 | 50 | 5 | 25 | 100.0 | 25.733837 | -7.289003 | 4.601458 |
| 17 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p00484 | 50 | 5 | 25 | 100.0 | 25.733837 | -7.289003 | 4.601458 |
| 18 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p2249 | 30 | 3 | 15 | 100.0 | 23.869393 | -4.641544 | 4.601458 |
| 19 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_risk_score_ge_55p568 | 30 | 3 | 15 | 100.0 | 23.869393 | -4.641544 | 4.601458 |
| 20 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_failure_rate_pct_ge_48p4733 | 55 | 8 | 29 | 100.0 | 24.147002 | -8.188031 | 4.601458 |
| 21 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_failure_rate_pct_ge_48p3476 | 55 | 8 | 29 | 100.0 | 24.147002 | -8.188031 | 4.601458 |
| 22 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_1p2621 | 39 | 8 | 22 | 100.0 | 21.553978 | -5.847023 | 4.601458 |
| 23 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_failure_rate_pct_ge_45p8069 | 59 | 9 | 31 | 100.0 | 23.212245 | -8.188031 | 4.601458 |
| 24 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_failure_rate_pct_ge_45p7538 | 59 | 9 | 31 | 100.0 | 23.212245 | -8.188031 | 4.601458 |
| 25 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_1p29874 | 40 | 8 | 23 | 100.0 | 21.191919 | -5.847023 | 4.601458 |
| 26 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_2p14332 | 61 | 7 | 31 | 100.0 | 22.481581 | -7.289003 | 4.601458 |
| 27 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_6p85473 | 66 | 9 | 37 | 98.4848 | 28.363277 | -7.120743 | 4.380217 |
| 28 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p7241 | 60 | 6 | 30 | 100.0 | 22.690553 | -7.289003 | 4.601458 |
| 29 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg8p74539 | 60 | 6 | 30 | 100.0 | 22.690553 | -7.289003 | 4.601458 |
| 30 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_0p594656 | 35 | 7 | 20 | 100.0 | 20.883084 | -5.847023 | 4.601458 |
| 31 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_0p641681 | 35 | 7 | 20 | 100.0 | 20.883084 | -5.847023 | 4.601458 |
| 32 | shadow_risk_review | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_19p7838 | 56 | 8 | 36 | 96.4286 | 44.951317 | -10.089127 | 4.079982 |
| 33 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_touch5_n_ge_6017 | 59 | 9 | 30 | 100.0 | 20.521125 | -7.289003 | 4.601458 |
| 34 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_6071 | 59 | 9 | 30 | 100.0 | 20.521125 | -7.289003 | 4.601458 |
| 35 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_1p52857 | 82 | 13 | 45 | 98.7805 | 24.439405 | -8.252071 | 4.423393 |
| 36 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_touch5_n_ge_3824 | 75 | 10 | 38 | 100.0 | 19.135575 | -7.289003 | 4.601458 |
| 37 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_3848 | 75 | 10 | 38 | 100.0 | 19.135575 | -7.289003 | 4.601458 |
| 38 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_close_location_pct_ge_20p3453 | 79 | 11 | 42 | 100.0 | 19.173985 | -8.252071 | 4.601458 |
| 39 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_close_location_pct_ge_26p4706 | 79 | 11 | 42 | 100.0 | 19.014492 | -8.252071 | 4.601458 |
| 40 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_close_location_pct_ge_31p5488 | 79 | 11 | 42 | 100.0 | 19.014492 | -8.252071 | 4.601458 |
| 41 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p7284 | 77 | 9 | 40 | 100.0 | 18.732078 | -7.289003 | 4.601458 |
| 42 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_prev_volume_ratio_le_0p6166 | 74 | 9 | 37 | 100.0 | 18.650795 | -7.289003 | 4.601458 |
| 43 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_volume_ratio_20d_le_0p6166 | 74 | 9 | 37 | 100.0 | 18.650795 | -7.289003 | 4.601458 |
| 44 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_neg1p51036 | 31 | 4 | 17 | 100.0 | 21.233774 | -5.847023 | 4.601458 |
| 45 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_neg1p50405 | 31 | 4 | 17 | 100.0 | 21.233774 | -5.847023 | 4.601458 |
| 46 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_sector_stop5_rate_pct_le_65p5172 | 75 | 10 | 38 | 100.0 | 20.172011 | -9.506833 | 4.601458 |
| 47 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_theme_failure_rate_pct_ge_51p4421 | 33 | 5 | 18 | 100.0 | 22.675086 | -8.188031 | 4.601458 |
| 48 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_close_failure_prior_kis_theme_failure_rate_pct_ge_51p2742 | 33 | 5 | 18 | 100.0 | 22.675086 | -8.188031 | 4.601458 |
| 49 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_prev_volume_ratio_le_0p6533 | 74 | 9 | 37 | 100.0 | 17.683407 | -7.289003 | 4.601458 |
| 50 | shadow_ready | top2_prob_plus_tail_p0p8_tail0p85_kis_daily_volume_ratio_20d_le_0p6533 | 74 | 9 | 37 | 100.0 | 17.683407 | -7.289003 | 4.601458 |
