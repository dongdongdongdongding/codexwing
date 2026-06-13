# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `production_gate_pass_research_candidate_found`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T13:29:34+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSPI`
- selection: score_mode=`prob` topn=`1` prob_threshold=`None` tail_threshold=`0.85`
- compound_filter: depth=`1` single_limit=`60` candidate_limit=`0`
- base: status=`shadow_risk_review` blockers=`['min_low_5d_lt_neg10']` n=`58` days=`15` hit5=`79.3103` avg5=`34.754917` min_low=`-10.87344`
- filters_tested: `1107`
- production_ready_count: `6`
- best_filter: `{'type': 'single_feature_threshold', 'feature': 'close_failure_prior_kis_sector_failure_rate_pct', 'op': 'le', 'threshold': 46.666667, 'pool_rows': 3811}`
- best: status=`production_ready` n=`54` days=`15` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` expected_net=`4.331054`
- candidate_frontier: total=`1107` sample=`199` low_safe=`286` hit_low_safe=`173` sample_low_safe=`7` sample_hit_low_safe=`6`
- candidate_frontier_best_sample: status=`production_ready` rule=`top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667` n=`54` days=`15` runs=`54` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` blockers=`[]`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3]` holdout_folds=`[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`706` holdout_evaluated=`706` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`shadow_risk_review` n=`40` days=`12` hit5=`87.5` avg5=`32.224954` min_low=`-10.87344`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`696` sample=`0` low_safe=`171` hit_low_safe=`135` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667 | 54 | 15 | 54 | 98.1481 | 24.676158 | -9.230497 | 4.331054 |
| 2 | production_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p69809 | 58 | 15 | 58 | 81.0345 | 35.016288 | -9.230497 | 1.832218 |
| 3 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_2p71383 | 58 | 15 | 58 | 81.0345 | 35.016288 | -9.230497 | 1.832218 |
| 4 | production_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p53492 | 55 | 15 | 55 | 80.0 | 30.595452 | -9.230497 | 1.681166 |
| 5 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_avg_close_5d_pct_le_2p55419 | 54 | 15 | 54 | 79.6296 | 30.826482 | -9.230497 | 1.627083 |
| 6 | production_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_touch5_n_le_702 | 57 | 15 | 57 | 77.193 | 35.051254 | -9.337 | 1.271303 |
| 7 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_ge_55p471 | 15 | 3 | 15 | 100.0 | 75.177243 | -7.120743 | 4.601458 |
| 8 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_neg0p342036 | 15 | 3 | 15 | 100.0 | 75.177243 | -7.120743 | 4.601458 |
| 9 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p1637 | 15 | 3 | 15 | 100.0 | 75.177243 | -7.120743 | 4.601458 |
| 10 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p3346 | 17 | 4 | 17 | 100.0 | 71.941583 | -7.120743 | 4.601458 |
| 11 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_risk_score_ge_54p176 | 17 | 4 | 17 | 100.0 | 71.941583 | -7.120743 | 4.601458 |
| 12 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_failure_rate_pct_ge_51p6225 | 25 | 5 | 25 | 100.0 | 64.374971 | -7.120743 | 4.601458 |
| 13 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_0p515842 | 25 | 5 | 25 | 100.0 | 64.374971 | -7.120743 | 4.601458 |
| 14 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p4322 | 25 | 5 | 25 | 100.0 | 64.374971 | -7.120743 | 4.601458 |
| 15 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p04538 | 25 | 5 | 25 | 100.0 | 64.374971 | -7.120743 | 4.601458 |
| 16 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg9p00484 | 25 | 5 | 25 | 100.0 | 64.374971 | -7.120743 | 4.601458 |
| 17 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_3824 | 38 | 10 | 38 | 100.0 | 53.704093 | -7.120743 | 4.601458 |
| 18 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_3848 | 38 | 10 | 38 | 100.0 | 53.704093 | -7.120743 | 4.601458 |
| 19 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p7241 | 30 | 6 | 30 | 100.0 | 54.553038 | -7.120743 | 4.601458 |
| 20 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mae_5d_pct_le_neg8p74539 | 30 | 6 | 30 | 100.0 | 54.553038 | -7.120743 | 4.601458 |
| 21 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_close_5d_pct_le_2p14332 | 31 | 7 | 31 | 100.0 | 53.114015 | -7.120743 | 4.601458 |
| 22 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_avg_mfe_5d_pct_le_14p7284 | 40 | 9 | 40 | 100.0 | 51.198935 | -7.120743 | 4.601458 |
| 23 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_13636 | 8 | 4 | 8 | 100.0 | 50.520546 | -3.900022 | 4.601458 |
| 24 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_13715 | 8 | 4 | 8 | 100.0 | 50.520546 | -3.900022 | 4.601458 |
| 25 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_mfe_5d_pct_ge_24p4162 | 45 | 9 | 45 | 100.0 | 49.413499 | -9.506833 | 4.601458 |
| 26 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_4p84699 | 46 | 10 | 46 | 100.0 | 42.971678 | -7.120743 | 4.601458 |
| 27 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_7p7009 | 46 | 10 | 46 | 100.0 | 41.673451 | -8.05775 | 4.601458 |
| 28 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_7349 | 24 | 8 | 24 | 100.0 | 40.032125 | -5.551964 | 4.601458 |
| 29 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_7428 | 24 | 8 | 24 | 100.0 | 40.032125 | -5.551964 | 4.601458 |
| 30 | shadow_ready | top1_prob_tail0p85_kis_daily_return_20d_pct_le_neg16p8 | 38 | 10 | 38 | 97.3684 | 52.914705 | -7.579406 | 4.217206 |
| 31 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_stop5_rate_pct_ge_68p4199 | 19 | 5 | 19 | 100.0 | 40.817938 | -5.551964 | 4.601458 |
| 32 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_8908 | 21 | 6 | 21 | 100.0 | 38.94041 | -5.551964 | 4.601458 |
| 33 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_8987 | 21 | 6 | 21 | 100.0 | 38.94041 | -5.551964 | 4.601458 |
| 34 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_2p38762 | 48 | 12 | 48 | 97.9167 | 42.031675 | -7.120743 | 4.297266 |
| 35 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_3p01151 | 48 | 12 | 48 | 97.9167 | 42.031675 | -7.120743 | 4.297266 |
| 36 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_3p4694 | 48 | 12 | 48 | 97.9167 | 42.031675 | -7.120743 | 4.297266 |
| 37 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_4p11085 | 47 | 11 | 47 | 97.8723 | 42.714406 | -7.120743 | 4.290783 |
| 38 | shadow_ready | top1_prob_tail0p85_close_failure_prior_market_clean_defense_rate_pct_le_23p6267 | 11 | 4 | 11 | 100.0 | 35.379405 | -5.551964 | 4.601458 |
| 39 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_5p3402 | 51 | 14 | 51 | 98.0392 | 40.679581 | -8.188031 | 4.315153 |
| 40 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_6p11527 | 51 | 14 | 51 | 98.0392 | 40.679581 | -8.188031 | 4.315153 |
| 41 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_7p94329 | 50 | 13 | 50 | 98.0 | 41.294306 | -8.188031 | 4.309429 |
| 42 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_sector_avg_close_5d_pct_ge_1p14759 | 54 | 14 | 54 | 98.1481 | 39.445677 | -8.188031 | 4.331054 |
| 43 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_11786 | 13 | 5 | 13 | 100.0 | 33.183172 | -5.551964 | 4.601458 |
| 44 | shadow_ready | top1_prob_tail0p85_close_failure_prior_kis_theme_touch5_n_ge_11865 | 13 | 5 | 13 | 100.0 | 33.183172 | -5.551964 | 4.601458 |
| 45 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_0p401005 | 57 | 14 | 57 | 98.2456 | 38.060278 | -8.188031 | 4.34529 |
| 46 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_1p67203 | 57 | 14 | 57 | 98.2456 | 38.060278 | -8.188031 | 4.34529 |
| 47 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_2p94384 | 57 | 14 | 57 | 98.2456 | 38.060278 | -8.188031 | 4.34529 |
| 48 | shadow_ready | top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_2p06939 | 47 | 14 | 47 | 97.8723 | 36.276297 | -8.567368 | 4.290783 |
| 49 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_4p58927 | 52 | 14 | 52 | 96.1538 | 39.774732 | -8.578431 | 4.039857 |
| 50 | shadow_ready | top1_prob_tail0p85_close_failure_prior_ticker_avg_close_5d_pct_ge_9p73027 | 48 | 11 | 48 | 95.8333 | 43.999319 | -9.506833 | 3.993059 |
