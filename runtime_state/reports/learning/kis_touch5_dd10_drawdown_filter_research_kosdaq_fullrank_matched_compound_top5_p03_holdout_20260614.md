# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-14T04:18:49+00:00`
- prepared_cache: `runtime_state/reports/learning/kis_historical_universe_fullrank_sidecar_cache_augmented_matched_only_kosdaq_20260101_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob_plus_tail` topn=`5` prob_threshold=`0.3` tail_threshold=`0.0`
- compound_filter: depth=`2` single_limit=`80` candidate_limit=`3000`
- base: status=`blocked` blockers=`['active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']` n=`52` days=`11` hit5=`53.8462` avg5=`-0.481049` min_low=`-30.923396`
- filters_tested: `4329`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`4329` sample=`0` low_safe=`39` hit_low_safe=`0` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[2, 3, 4, 5, 6]` holdout_folds=`[7, 8, 9, 10, 11, 12, 13, 14, 15, 16]` selection_candidates=`4289` holdout_evaluated=`600` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`26` days=`6` hit5=`30.7692` avg5=`-8.086069` min_low=`-28.540083`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`600` sample=`0` low_safe=`0` hit_low_safe=`0` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_1eee64e57e | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 2 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_08535d8ecb | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 3 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_571f54aaa0 | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 4 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_e9388470dd | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 5 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_c0dbb0d057 | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 6 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_ede7aac7ed | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 7 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_169f98563a | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 8 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_09fdce415d | 30 | 6 | 6 | 73.3333 | 4.161918 | -10.170965 | 0.707731 |
| 9 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d97fb6b8b2 | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 10 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_1347c33684 | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 11 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_aac22303ea | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 12 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_0585439f82 | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 13 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_9066a57122 | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 14 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_57309aab5b | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 15 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_ff5cd0cc68 | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 16 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_73755d9ceb | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 17 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_a0bbb2706e | 25 | 5 | 5 | 72.0 | 5.065275 | -10.170965 | 0.51305 |
| 18 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_touch5_n_le_59067 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 19 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_clean_defense_rate_pct_ge_42p1691 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 20 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_stop5_rate_pct_le_49p6622 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 21 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_avg_mfe_5d_pct_ge_16p8683 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 22 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_4be67364eb | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 23 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_8404baffbb | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 24 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_1689eed0f0 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 25 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_16b8044cef | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 26 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_4214eda820 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 27 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_4f1ed7ed92 | 35 | 7 | 7 | 77.1429 | 5.200231 | -12.593206 | 1.263988 |
| 28 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_touch5_n_le_57212 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 29 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_failure_rate_pct_le_29p5963 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 30 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_stop5_rate_pct_le_48p9251 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 31 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_stop5_rate_pct_le_49p4829 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 32 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_avg_close_5d_pct_ge_5p92247 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 33 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_avg_mfe_5d_pct_ge_16p8827 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 34 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_avg_mae_5d_pct_ge_neg6p21513 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 35 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_avg_mae_5d_pct_ge_neg6p17973 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 36 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_risk_score_le_27p5641 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 37 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_c756bdcdf7 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 38 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_61f220e33c | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 39 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_fea43c31a5 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 40 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_bbb4faf79d | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 41 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_6a4185d2b9 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 42 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_f7dafc758d | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 43 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_cdd8476a9f | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 44 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_688b48a6cf | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 45 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_0d59efc198 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 46 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_f3a4c1611a | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 47 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_b5d815f62d | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 48 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d997277d34 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 49 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d208fe468c | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 50 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_64eb30846a | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 51 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_3780c15228 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 52 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_0ce8812532 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 53 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_8a50e10741 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 54 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_fc4b9e5f2d | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 55 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_f81b4ec36e | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 56 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_e51fbedb1a | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 57 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_467d7aaa00 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 58 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_db6a1da595 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 59 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_98cbcc4da9 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 60 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d537308cb4 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 61 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_6e5b29cbdb | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 62 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_1d05ef2a23 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 63 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_88ab9c896f | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 64 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_78662fde04 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 65 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_50fa94d401 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 66 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_bc0f229fbe | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 67 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_7c13df2169 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 68 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_c0f9038c3a | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 69 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_e7b9557abf | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 70 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_44cbc488f7 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 71 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_7e7f7e6a2c | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 72 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_2b3f848a59 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 73 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_7559e7f3c6 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 74 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_b51a0fdea4 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 75 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_50c479ab85 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 76 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d10026988b | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 77 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_47cb826e82 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 78 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_2cd3466d40 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 79 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_372278845e | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 80 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_b6730d51d3 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 81 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_94dd4f1ed1 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 82 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_f314da1794 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 83 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_14f0be501b | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 84 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d8dc75103d | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 85 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_58a815f6c4 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 86 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_34fe76c017 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 87 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_6b35cf40aa | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 88 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_eb46a16452 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 89 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_2466b645c9 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 90 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_566bfce552 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 91 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_1ab9b6e852 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 92 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_c1ca7296f2 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 93 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_7eba80ca60 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 94 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_830bff4760 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 95 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_0ab6bf85b6 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 96 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_6cc55fd010 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 97 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_f9aa6270d2 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 98 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d3d78ead42 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 99 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_9378a3fa8f | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
| 100 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_c9bd239ec6 | 25 | 5 | 5 | 76.0 | 6.340629 | -12.593206 | 1.097108 |
