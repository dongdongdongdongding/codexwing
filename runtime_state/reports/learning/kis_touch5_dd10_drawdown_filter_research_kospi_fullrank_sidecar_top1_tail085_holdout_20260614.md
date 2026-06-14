# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-14T04:15:08+00:00`
- prepared_cache: `runtime_state/reports/learning/kis_historical_universe_fullrank_sidecar_cache_augmented_prepared_kospi_20260101_20260610.pkl`
- market: `KOSPI`
- selection: score_mode=`prob` topn=`1` prob_threshold=`None` tail_threshold=`0.85`
- compound_filter: depth=`1` single_limit=`60` candidate_limit=`0`
- base: status=`blocked` blockers=`['n_lt_30', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']` n=`17` days=`17` hit5=`17.6471` avg5=`-0.877676` min_low=`-6.232202`
- filters_tested: `1295`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`1295` sample=`0` low_safe=`898` hit_low_safe=`10` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3]` holdout_folds=`[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`784` holdout_evaluated=`180` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`170` sample=`0` low_safe=`142` hit_low_safe=`0` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_23373 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 2 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_21p5847 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 3 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_21p6409 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 4 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_56p2688 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 5 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_56p454 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 6 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_33p8944 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 7 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p4928 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 8 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p68066 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 9 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_12p7703 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 10 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_12p9445 | 1 | 1 | 1 | 100.0 | 16.243365 | -3.05742 | 4.601458 |
| 11 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_23796 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 12 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_21p8608 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 13 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_55p5542 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 14 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_34p2705 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 15 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_34p6573 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 16 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_6p02526 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 17 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p5687 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 18 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_13p7611 | 3 | 3 | 3 | 66.6667 | 6.227265 | -6.232202 | -0.26569 |
| 19 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_23585 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 20 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_55p9254 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 21 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_6p08088 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 22 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_6p10562 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 23 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p532 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 24 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p73623 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 25 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p70145 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 26 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_13p3159 | 2 | 2 | 2 | 50.0 | 6.734489 | -6.232202 | -2.699271 |
| 27 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p601 | 4 | 4 | 4 | 50.0 | 4.180252 | -6.232202 | -2.699271 |
| 28 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_24018 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 29 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_22p1709 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 30 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_22p6208 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 31 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_55p1662 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 32 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p81945 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 33 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p77419 | 4 | 4 | 4 | 50.0 | 3.868025 | -6.232202 | -2.699271 |
| 34 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_touch5_n_ge_7 | 7 | 7 | 7 | 42.8571 | 1.56089 | -6.012922 | -3.742239 |
| 35 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_24283 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 36 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_23p1641 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 37 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_54p8048 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 38 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_34p9874 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 39 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_5p93557 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 40 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p87428 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 41 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_14p2886 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 42 | blocked | top1_prob_tail0p85_close_failure_prior_market_risk_score_le_14p8745 | 5 | 5 | 5 | 40.0 | 2.285961 | -6.232202 | -4.159417 |
| 43 | blocked | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p38026 | 10 | 10 | 10 | 40.0 | -0.276223 | -8.86297 | -4.159417 |
| 44 | blocked | top1_prob_tail0p85_volume_ratio_le_0p380293 | 10 | 10 | 10 | 40.0 | -0.276223 | -8.86297 | -4.159417 |
| 45 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_touch5_n_ge_5 | 8 | 8 | 8 | 37.5 | 1.120681 | -6.012922 | -4.524453 |
| 46 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_clean_defense_rate_pct_le_87p5 | 11 | 11 | 11 | 36.3636 | 0.542633 | -6.012922 | -4.690384 |
| 47 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_5p68865 | 11 | 11 | 11 | 36.3636 | 0.542633 | -6.012922 | -4.690384 |
| 48 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_5p8742 | 11 | 11 | 11 | 36.3636 | 0.542633 | -6.012922 | -4.690384 |
| 49 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_6p12227 | 11 | 11 | 11 | 36.3636 | 0.542633 | -6.012922 | -4.690384 |
| 50 | blocked | top1_prob_tail0p85_kis_prev_volume_ratio_le_70p8804 | 11 | 11 | 11 | 36.3636 | 0.354685 | -6.106206 | -4.690384 |
| 51 | blocked | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_1p07572 | 11 | 11 | 11 | 36.3636 | -0.015129 | -6.232202 | -4.690384 |
| 52 | blocked | top1_prob_tail0p85_volume_ratio_le_1p07571 | 11 | 11 | 11 | 36.3636 | -0.015129 | -6.232202 | -4.690384 |
| 53 | blocked | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p704451 | 11 | 11 | 11 | 36.3636 | -0.105251 | -7.603329 | -4.690384 |
| 54 | blocked | top1_prob_tail0p85_volume_ratio_le_0p704448 | 11 | 11 | 11 | 36.3636 | -0.105251 | -7.603329 | -4.690384 |
| 55 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_5p60655 | 11 | 11 | 11 | 36.3636 | 0.249013 | -9.001302 | -4.690384 |
| 56 | blocked | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p438998 | 11 | 11 | 11 | 36.3636 | -0.69914 | -8.86297 | -4.690384 |
| 57 | blocked | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p530039 | 11 | 11 | 11 | 36.3636 | -0.69914 | -8.86297 | -4.690384 |
| 58 | blocked | top1_prob_tail0p85_volume_ratio_le_0p438998 | 11 | 11 | 11 | 36.3636 | -0.69914 | -8.86297 | -4.690384 |
| 59 | blocked | top1_prob_tail0p85_volume_ratio_le_0p530047 | 11 | 11 | 11 | 36.3636 | -0.69914 | -8.86297 | -4.690384 |
| 60 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p602 | 6 | 6 | 6 | 33.3333 | 1.575946 | -6.232202 | -5.132852 |
| 61 | blocked | top1_prob_tail0p85_close_failure_prior_market_touch5_n_le_24538 | 6 | 6 | 6 | 33.3333 | 1.229028 | -6.232202 | -5.132852 |
| 62 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_35p3167 | 6 | 6 | 6 | 33.3333 | 1.229028 | -6.232202 | -5.132852 |
| 63 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_5p82182 | 6 | 6 | 6 | 33.3333 | 1.229028 | -6.232202 | -5.132852 |
| 64 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_stop5_rate_pct_ge_16p6667 | 6 | 6 | 6 | 33.3333 | -0.331072 | -6.012922 | -5.132852 |
| 65 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_touch5_n_ge_10 | 6 | 6 | 6 | 33.3333 | -0.886189 | -6.012922 | -5.132852 |
| 66 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_stop5_rate_pct_ge_22p2222 | 6 | 6 | 6 | 33.3333 | -0.914451 | -7.603329 | -5.132852 |
| 67 | blocked | top1_prob_tail0p85_kis_daily_close_location_pct_le_7p09416 | 10 | 10 | 10 | 30.0 | -0.588776 | -8.939847 | -5.619563 |
| 68 | blocked | top1_prob_tail0p85_close_failure_prior_kis_sector_touch5_n_ge_2521 | 3 | 3 | 3 | 33.3333 | -4.937585 | -10.309102 | -5.132852 |
| 69 | blocked | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_2521 | 3 | 3 | 3 | 33.3333 | -4.937585 | -10.309102 | -5.132852 |
| 70 | blocked | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_2521 | 3 | 3 | 3 | 33.3333 | -4.937585 | -10.309102 | -5.132852 |
| 71 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p604 | 7 | 7 | 7 | 28.5714 | 1.421763 | -6.232202 | -5.828159 |
| 72 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p6098 | 7 | 7 | 7 | 28.5714 | 1.421763 | -6.232202 | -5.828159 |
| 73 | blocked | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_le_23p3771 | 7 | 7 | 7 | 28.5714 | 0.77334 | -6.232202 | -5.828159 |
| 74 | blocked | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_ge_54p3948 | 7 | 7 | 7 | 28.5714 | 0.77334 | -6.232202 | -5.828159 |
| 75 | blocked | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_le_35p8076 | 7 | 7 | 7 | 28.5714 | 0.77334 | -6.232202 | -5.828159 |
| 76 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_ge_neg4p94067 | 7 | 7 | 7 | 28.5714 | 0.77334 | -6.232202 | -5.828159 |
| 77 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_5p78986 | 7 | 7 | 7 | 28.5714 | 0.668821 | -6.232202 | -5.828159 |
| 78 | blocked | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_ge_5p79853 | 7 | 7 | 7 | 28.5714 | 0.668821 | -6.232202 | -5.828159 |
| 79 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_8p63202 | 11 | 11 | 11 | 27.2727 | 0.519392 | -6.012922 | -6.017788 |
| 80 | blocked | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_9p46203 | 11 | 11 | 11 | 27.2727 | 0.519392 | -6.012922 | -6.017788 |
