# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `production_gate_pass_research_candidate_found`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T09:11:00+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSPI`
- base: status=`shadow_risk_review` blockers=`['min_low_5d_lt_neg10']` n=`58` days=`15` hit5=`79.3103` avg5=`34.754917` min_low=`-10.87344`
- filters_tested: `1107`
- production_ready_count: `6`
- best_filter: `{'type': 'single_feature_threshold', 'feature': 'close_failure_prior_kis_sector_failure_rate_pct', 'op': 'le', 'threshold': 46.666667, 'pool_rows': 3811}`
- best: status=`production_ready` n=`54` days=`15` hit5=`98.1481` avg5=`24.676158` min_low=`-9.230497` expected_net=`4.331054`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3, 4, 5]` holdout_folds=`[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`811` holdout_evaluated=`811` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`shadow_ready` n=`23` days=`7` hit5=`100.0` avg5=`39.699864` min_low=`-5.551964`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- rolling_prior: status=`rolling_prior_blocked` validation=`rolling_prior_oos_next_fold_walk_forward_predictions` min_prior_folds=`5` evaluated_steps=`15` selected=`2` deployment_ready=`False`
- rolling_prior_aggregate: status=`blocked` n=`2` days=`1` runs=`2` hit5=`100.0` avg5=`47.674132` min_low=`-3.191402` expected_net=`4.601458` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`

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
