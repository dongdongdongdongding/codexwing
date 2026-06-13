# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T12:26:59+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob_plus_tail` topn=`5` prob_threshold=`0.3` tail_threshold=`0.0`
- compound_filter: depth=`2` single_limit=`80` candidate_limit=`3000`
- base: status=`blocked` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']` n=`144` days=`16` hit5=`68.0556` avg5=`5.931853` min_low=`-33.704825`
- filters_tested: `3949`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`3949` sample=`0` low_safe=`535` hit_low_safe=`524` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[2, 3, 4, 5, 6]` holdout_folds=`[7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`3976` holdout_evaluated=`3976` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`61` days=`8` hit5=`62.2951` avg5=`3.397096` min_low=`-23.62384`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`3968` sample=`0` low_safe=`0` hit_low_safe=`0` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_742ed361a2 | 30 | 4 | 6 | 100.0 | 13.094836 | -7.544717 | 4.601458 |
| 2 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_341682c301 | 30 | 4 | 6 | 100.0 | 13.094836 | -7.544717 | 4.601458 |
| 3 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_f075faf14e | 50 | 5 | 10 | 100.0 | 11.731332 | -9.222948 | 4.601458 |
| 4 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_24c8072aec | 40 | 4 | 8 | 100.0 | 11.50683 | -9.222948 | 4.601458 |
| 5 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_6c2b1cf1e9 | 30 | 3 | 6 | 100.0 | 10.430842 | -7.614241 | 4.601458 |
| 6 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_15c75bc84f | 30 | 3 | 6 | 100.0 | 10.430842 | -7.614241 | 4.601458 |
| 7 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_3df695d632 | 35 | 3 | 7 | 100.0 | 10.939777 | -9.222948 | 4.601458 |
| 8 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_bf2c6032c1 | 55 | 6 | 11 | 98.1818 | 11.326617 | -9.401261 | 4.335974 |
| 9 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_e194cdf6e7 | 45 | 5 | 9 | 97.7778 | 8.51292 | -7.544717 | 4.276984 |
| 10 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_18b2a8aa5e | 45 | 5 | 9 | 97.7778 | 8.51292 | -7.544717 | 4.276984 |
| 11 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_ea50308026 | 95 | 9 | 19 | 96.8421 | 10.217856 | -9.571134 | 4.140359 |
| 12 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_1e8f5708e1 | 40 | 4 | 8 | 97.5 | 8.467618 | -7.011985 | 4.236422 |
| 13 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_d203fcee3e | 40 | 4 | 8 | 97.5 | 8.467618 | -7.011985 | 4.236422 |
| 14 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_9d43407c85 | 35 | 5 | 7 | 97.1429 | 12.264068 | -9.401261 | 4.18428 |
| 15 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_fcd2b6be20 | 35 | 5 | 7 | 97.1429 | 12.264068 | -9.401261 | 4.18428 |
| 16 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_d857ade925 | 80 | 8 | 16 | 96.25 | 9.819985 | -9.571134 | 4.053903 |
| 17 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_ca64e3bd5f | 30 | 3 | 6 | 96.6667 | 8.409876 | -7.011985 | 4.114748 |
| 18 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_f88df2e4d2 | 30 | 3 | 6 | 96.6667 | 8.409876 | -7.011985 | 4.114748 |
| 19 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_2b08f75872 | 95 | 9 | 19 | 95.7895 | 10.020127 | -10.00878 | 3.986664 |
| 20 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_e30b65ffd1 | 30 | 3 | 6 | 96.6667 | 10.086258 | -10.00878 | 4.114748 |
| 21 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_3d64ef69cc | 30 | 3 | 6 | 96.6667 | 10.086258 | -10.00878 | 4.114748 |
| 22 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_1ae20879fb | 70 | 7 | 14 | 95.7143 | 10.145842 | -9.571134 | 3.975683 |
| 23 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_0e815ca375 | 45 | 5 | 9 | 95.5556 | 10.337148 | -8.496732 | 3.952511 |
| 24 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_45db4b70b0 | 45 | 5 | 9 | 95.5556 | 10.337148 | -8.496732 | 3.952511 |
| 25 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_9aff9e40c1 | 65 | 6 | 13 | 95.3846 | 11.232694 | -9.571134 | 3.927542 |
| 26 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_5ed8109383 | 65 | 6 | 13 | 95.3846 | 10.439575 | -9.571134 | 3.927542 |
| 27 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_a92e91044a | 65 | 6 | 13 | 95.3846 | 10.119554 | -9.571134 | 3.927542 |
| 28 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_d9863564b3 | 65 | 6 | 13 | 95.3846 | 9.989605 | -9.571134 | 3.927542 |
| 29 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_close_failure_prior_market_touch5_n_le_4767 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 30 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_d74d418af8 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 31 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_3fc3edbdcb | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 32 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_fa07faa3bc | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 33 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_cfdf14fee2 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 34 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_0d99ab0f92 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 35 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_16dd69b259 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 36 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_151607c901 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 37 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_de2409f710 | 65 | 6 | 13 | 95.3846 | 9.971384 | -9.571134 | 3.927542 |
| 38 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_5f2b4e2d5d | 45 | 4 | 9 | 95.5556 | 9.149218 | -8.496732 | 3.952511 |
| 39 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_1e87d87c4c | 45 | 4 | 9 | 95.5556 | 9.149218 | -8.496732 | 3.952511 |
| 40 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_ddd47d6b23 | 80 | 8 | 16 | 95.0 | 9.585182 | -10.00878 | 3.871385 |
| 41 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_52e59d4d68 | 46 | 5 | 10 | 95.6522 | 5.649075 | -7.544717 | 3.966616 |
| 42 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_d157d15546 | 46 | 5 | 10 | 95.6522 | 5.649075 | -7.544717 | 3.966616 |
| 43 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_2042381e94 | 40 | 4 | 8 | 95.0 | 9.321214 | -8.496732 | 3.871385 |
| 44 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_7fec53b550 | 40 | 4 | 8 | 95.0 | 9.321214 | -8.496732 | 3.871385 |
| 45 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_8f2c6df577 | 42 | 4 | 10 | 95.2381 | 5.762123 | -7.011985 | 3.906151 |
| 46 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_6cee7b41c8 | 42 | 4 | 10 | 95.2381 | 5.762123 | -7.011985 | 3.906151 |
| 47 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_56376780a9 | 45 | 5 | 9 | 97.7778 | 4.56226 | -10.324821 | 4.276984 |
| 48 | shadow_risk_review | top5_prob_plus_tail_p0p3_tail0_compound2_d67323f7bc | 45 | 5 | 9 | 97.7778 | 4.56226 | -10.324821 | 4.276984 |
| 49 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_600ef6de7a | 70 | 7 | 14 | 94.2857 | 10.894148 | -9.571134 | 3.767087 |
| 50 | shadow_ready | top5_prob_plus_tail_p0p3_tail0_compound2_7d24a9ef74 | 55 | 5 | 11 | 94.5455 | 11.230191 | -9.571134 | 3.805021 |
