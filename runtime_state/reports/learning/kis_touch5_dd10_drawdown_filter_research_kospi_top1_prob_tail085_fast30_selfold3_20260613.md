# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `production_gate_pass_research_candidate_found`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T13:44:48+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSPI`
- selection: score_mode=`prob` topn=`1` prob_threshold=`None` tail_threshold=`0.85`
- compound_filter: depth=`1` single_limit=`60` candidate_limit=`0`
- base: status=`shadow_risk_review` blockers=`['min_low_5d_lt_neg10']` n=`58` days=`15` hit5=`79.3103` avg5=`34.754917` min_low=`-10.87344`
- filters_tested: `463`
- production_ready_count: `6`
- best_filter: `{'type': 'single_feature_threshold', 'feature': 'close_failure_prior_kis_sector_failure_rate_pct', 'op': 'le', 'threshold': 46.666667, 'pool_rows': 3811}`
- best: status=`production_ready` n=`54` days=`15` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` expected_net=`4.331054`
- candidate_frontier: total=`463` sample=`98` low_safe=`84` hit_low_safe=`49` sample_low_safe=`6` sample_hit_low_safe=`6`
- candidate_frontier_best_sample: status=`production_ready` rule=`top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667` n=`54` days=`15` runs=`54` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` blockers=`[]`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3]` holdout_folds=`[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`327` holdout_evaluated=`120` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`shadow_risk_review` n=`41` days=`12` hit5=`92.6829` avg5=`32.906426` min_low=`-10.87344`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`120` sample=`0` low_safe=`26` hit_low_safe=`23` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`rolling_prior_shadow_ready` validation=`rolling_prior_oos_next_fold_walk_forward_predictions` min_prior_folds=`3` evaluated_steps=`17` selected=`22` deployment_ready=`False`
- rolling_prior_aggregate: status=`shadow_ready` n=`22` days=`7` runs=`22` hit5=`86.3636` avg5=`33.261526` min_low=`-9.469258` expected_net=`2.610345` blockers=`['n_lt_30', 'active_days_lt_15']`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667 | 54 | 15 | 54 | 98.1481 | 24.676158 | -9.230497 | 4.331054 |
| 2 | production_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p69809 | 58 | 15 | 58 | 81.0345 | 35.016288 | -9.230497 | 1.832218 |
| 3 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_2p71383 | 58 | 15 | 58 | 81.0345 | 35.016288 | -9.230497 | 1.832218 |
| 4 | production_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p53492 | 55 | 15 | 55 | 80.0 | 30.595452 | -9.230497 | 1.681166 |
| 5 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_2p55419 | 54 | 15 | 54 | 79.6296 | 30.826482 | -9.230497 | 1.627083 |
| 6 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_touch5_n_le_702 | 57 | 15 | 57 | 77.193 | 35.051254 | -9.337 | 1.271303 |
| 7 | shadow_ready | top1_prob_tail0p85_kis_daily_return_20d_pct_le_neg16p8 | 38 | 10 | 38 | 97.3684 | 52.914705 | -7.579406 | 4.217206 |
| 8 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p06939 | 47 | 14 | 47 | 97.8723 | 36.276297 | -8.567368 | 4.290783 |
| 9 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_39p0728 | 48 | 12 | 48 | 97.9167 | 22.706816 | -8.05775 | 4.297266 |
| 10 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_neg2p37094 | 21 | 6 | 21 | 95.2381 | 34.823482 | -7.120743 | 3.906151 |
| 11 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_42p5558 | 49 | 13 | 49 | 95.9184 | 26.035957 | -9.230497 | 4.005485 |
| 12 | shadow_ready | top1_prob_tail0p85_kis_daily_return_5d_pct_le_neg6p4953 | 46 | 10 | 46 | 95.6522 | 24.565802 | -8.028976 | 3.966616 |
| 13 | shadow_ready | top1_prob_tail0p85_kis_daily_return_5d_pct_le_neg5p7432 | 47 | 11 | 47 | 93.617 | 34.611852 | -9.119927 | 3.669447 |
| 14 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_35p7895 | 48 | 12 | 48 | 95.8333 | 20.338735 | -10.280626 | 3.993059 |
| 15 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_53p6585 | 58 | 15 | 58 | 94.8276 | 36.709404 | -10.87344 | 3.846212 |
| 16 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_23p0769 | 46 | 10 | 46 | 97.8261 | 1.95354 | -10.160866 | 4.284037 |
| 17 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_32p8571 | 48 | 12 | 48 | 93.75 | 17.550615 | -10.280626 | 3.688867 |
| 18 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_stop5_rate_pct_ge_67p6301 | 49 | 13 | 49 | 91.8367 | 41.745181 | -10.87344 | 3.409497 |
| 19 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_stop5_rate_pct_ge_68p227 | 49 | 13 | 49 | 91.8367 | 41.745181 | -10.87344 | 3.409497 |
| 20 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_stop5_rate_pct_ge_67p6471 | 49 | 13 | 49 | 91.8367 | 41.745181 | -10.87344 | 3.409497 |
| 21 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_clean_defense_rate_pct_le_26p474 | 49 | 13 | 49 | 91.8367 | 41.745181 | -10.87344 | 3.409497 |
| 22 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_clean_defense_rate_pct_le_26p5837 | 49 | 13 | 49 | 91.8367 | 41.745181 | -10.87344 | 3.409497 |
| 23 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_clean_defense_rate_pct_le_22p7407 | 49 | 13 | 49 | 91.8367 | 41.066155 | -10.87344 | 3.409497 |
| 24 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_clean_defense_rate_pct_le_22p6831 | 49 | 13 | 49 | 91.8367 | 41.066155 | -10.87344 | 3.409497 |
| 25 | shadow_risk_review | top1_prob_tail0p85_kis_prev_volume_ratio_le_0p63445 | 49 | 12 | 49 | 93.8776 | 24.924416 | -10.87344 | 3.707498 |
| 26 | shadow_risk_review | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p63445 | 49 | 12 | 49 | 93.8776 | 24.924416 | -10.87344 | 3.707498 |
| 27 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_29p5405 | 47 | 11 | 47 | 93.617 | 8.056103 | -10.280626 | 3.669447 |
| 28 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_clean_defense_rate_pct_le_21p5696 | 49 | 13 | 49 | 89.7959 | 40.593549 | -10.87344 | 3.111511 |
| 29 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg1p9499 | 57 | 14 | 57 | 94.7368 | 11.039011 | -10.87344 | 3.832954 |
| 30 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg1p2005 | 57 | 14 | 57 | 94.7368 | 11.039011 | -10.87344 | 3.832954 |
| 31 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_neg1p51036 | 29 | 9 | 29 | 89.6552 | 36.97146 | -10.769805 | 3.090966 |
| 32 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_neg1p50405 | 29 | 9 | 29 | 89.6552 | 36.97146 | -10.769805 | 3.090966 |
| 33 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg0p3018 | 55 | 14 | 55 | 94.5455 | 9.789378 | -10.87344 | 3.805021 |
| 34 | shadow_risk_review | top1_prob_tail0p85_kis_prev_volume_ratio_le_0p5185 | 49 | 12 | 49 | 91.8367 | 21.455454 | -10.87344 | 3.409497 |
| 35 | shadow_risk_review | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p5185 | 49 | 12 | 49 | 91.8367 | 21.455454 | -10.87344 | 3.409497 |
| 36 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg10p6547 | 58 | 15 | 58 | 93.1034 | 7.874679 | -10.87344 | 3.594454 |
| 37 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg5p6298 | 57 | 14 | 57 | 92.9825 | 8.825487 | -10.87344 | 3.576801 |
| 38 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg4p0299 | 57 | 14 | 57 | 92.9825 | 8.658243 | -10.87344 | 3.576801 |
| 39 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg6p96228 | 57 | 14 | 57 | 92.9825 | 8.422287 | -10.87344 | 3.576801 |
| 40 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_sector_touch5_n_ge_473 | 30 | 9 | 30 | 93.3333 | 9.70723 | -10.87344 | 3.628023 |
| 41 | shadow_risk_review | top1_prob_tail0p85_kis_prev_volume_ratio_le_0p57268 | 49 | 12 | 49 | 91.8367 | 23.589567 | -11.211566 | 3.409497 |
| 42 | shadow_risk_review | top1_prob_tail0p85_kis_daily_volume_ratio_20d_le_0p57268 | 49 | 12 | 49 | 91.8367 | 23.589567 | -11.211566 | 3.409497 |
| 43 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_stop5_rate_pct_ge_68p2692 | 42 | 12 | 42 | 88.0952 | 31.212892 | -10.87344 | 2.863184 |
| 44 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_stop5_rate_pct_ge_70p2912 | 42 | 12 | 42 | 88.0952 | 30.420696 | -10.87344 | 2.863184 |
| 45 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_theme_stop5_rate_pct_ge_70p5833 | 42 | 12 | 42 | 88.0952 | 30.420696 | -10.87344 | 2.863184 |
| 46 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_stop5_rate_pct_ge_70p3807 | 42 | 12 | 42 | 88.0952 | 30.420696 | -10.87344 | 2.863184 |
| 47 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_kis_theme_stop5_rate_pct_ge_70p7462 | 42 | 12 | 42 | 88.0952 | 30.420696 | -10.87344 | 2.863184 |
| 48 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg9p6259 | 58 | 15 | 58 | 91.3793 | 6.279054 | -10.87344 | 3.34271 |
| 49 | shadow_risk_review | top1_prob_tail0p85_kis_daily_return_20d_pct_ge_neg8p6822 | 58 | 15 | 58 | 91.3793 | 6.279054 | -10.87344 | 3.34271 |
| 50 | shadow_risk_review | top1_prob_tail0p85_close_failure_prior_ticker_failure_rate_pct_le_35p4839 | 57 | 14 | 57 | 84.2105 | 36.000495 | -10.663142 | 2.295961 |
