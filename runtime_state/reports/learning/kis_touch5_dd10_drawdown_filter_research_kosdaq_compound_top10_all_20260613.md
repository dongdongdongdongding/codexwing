# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T12:34:11+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob_plus_tail` topn=`10` prob_threshold=`None` tail_threshold=`0.0`
- compound_filter: depth=`2` single_limit=`80` candidate_limit=`3000`
- base: status=`blocked` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']` n=`364` days=`19` hit5=`52.4725` avg5=`0.352228` min_low=`-38.310759`
- filters_tested: `4014`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`4014` sample=`0` low_safe=`230` hit_low_safe=`210` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[2, 3, 4, 5, 6]` holdout_folds=`[7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`3956` holdout_evaluated=`3956` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`90` days=`5` hit5=`88.8889` avg5=`12.65128` min_low=`-19.786096`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`3920` sample=`0` low_safe=`0` hit_low_safe=`0` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top10_prob_plus_tail_tail0_compound2_fbd9f7eaf7 | 50 | 4 | 5 | 98.0 | 9.545147 | -9.401261 | 4.309429 |
| 2 | shadow_ready | top10_prob_plus_tail_tail0_compound2_3b0ed7b5ec | 50 | 4 | 5 | 98.0 | 9.545147 | -9.401261 | 4.309429 |
| 3 | shadow_ready | top10_prob_plus_tail_tail0_compound2_04cf9be635 | 50 | 4 | 5 | 98.0 | 9.545147 | -9.401261 | 4.309429 |
| 4 | shadow_ready | top10_prob_plus_tail_tail0_compound2_d0ad73b946 | 50 | 4 | 5 | 98.0 | 9.545147 | -9.401261 | 4.309429 |
| 5 | shadow_ready | top10_prob_plus_tail_tail0_compound2_f075faf14e | 100 | 5 | 10 | 96.0 | 9.697969 | -9.222948 | 4.0174 |
| 6 | shadow_ready | top10_prob_plus_tail_tail0_compound2_bf2c6032c1 | 110 | 6 | 11 | 95.4545 | 9.322853 | -9.401261 | 3.937749 |
| 7 | shadow_ready | top10_prob_plus_tail_tail0_compound2_3df695d632 | 70 | 3 | 7 | 94.2857 | 9.288513 | -9.222948 | 3.767087 |
| 8 | shadow_ready | top10_prob_plus_tail_tail0_compound2_2ba212617d | 52 | 3 | 7 | 94.2308 | 6.088875 | -8.648617 | 3.759071 |
| 9 | shadow_ready | top10_prob_plus_tail_tail0_compound2_742ed361a2 | 60 | 4 | 6 | 93.3333 | 9.352644 | -8.769063 | 3.628023 |
| 10 | shadow_ready | top10_prob_plus_tail_tail0_compound2_9d43407c85 | 70 | 5 | 7 | 92.8571 | 8.812508 | -9.401261 | 3.55849 |
| 11 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_2ef6c0d4bd | 100 | 6 | 10 | 97.0 | 14.158901 | -11.146595 | 4.163414 |
| 12 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_a21418d932 | 100 | 6 | 10 | 97.0 | 14.158901 | -11.146595 | 4.163414 |
| 13 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_cf01bdd4f3 | 100 | 6 | 10 | 97.0 | 14.158901 | -11.146595 | 4.163414 |
| 14 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_77b8af9544 | 100 | 6 | 10 | 97.0 | 14.158901 | -11.146595 | 4.163414 |
| 15 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_d4bbee2416 | 100 | 6 | 10 | 97.0 | 13.934039 | -11.146595 | 4.163414 |
| 16 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_005bcc0ef8 | 100 | 6 | 10 | 97.0 | 13.934039 | -11.146595 | 4.163414 |
| 17 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_1ad5db4944 | 90 | 5 | 9 | 96.6667 | 14.349606 | -11.146595 | 4.114748 |
| 18 | shadow_ready | top10_prob_plus_tail_tail0_compound2_f46f15c53c | 52 | 3 | 7 | 92.3077 | 4.989087 | -8.7875 | 3.47827 |
| 19 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_3808e60c47 | 91 | 5 | 10 | 96.7033 | 11.625993 | -11.146595 | 4.120092 |
| 20 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_4a247bfa7a | 80 | 4 | 8 | 96.25 | 14.746032 | -11.146595 | 4.053903 |
| 21 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_07855739ba | 82 | 4 | 10 | 96.3415 | 11.880962 | -11.146595 | 4.067264 |
| 22 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_647afe8d05 | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 23 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_4555116b45 | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 24 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_1f54dea044 | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 25 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_f1d3888803 | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 26 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_d979631718 | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 27 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_025d193fff | 60 | 3 | 6 | 95.0 | 16.572495 | -11.146595 | 3.871385 |
| 28 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_5a8c29b14c | 60 | 3 | 6 | 95.0 | 11.678404 | -11.146595 | 3.871385 |
| 29 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_f7e74688e4 | 60 | 3 | 6 | 95.0 | 11.678404 | -11.146595 | 3.871385 |
| 30 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_f6f9f9a2ee | 50 | 3 | 5 | 94.0 | 3.636404 | -10.742564 | 3.725371 |
| 31 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_b90bad6b11 | 52 | 3 | 7 | 94.2308 | 8.657076 | -11.146595 | 3.759071 |
| 32 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_03e3adc5bf | 50 | 3 | 5 | 92.0 | 6.202488 | -10.675381 | 3.433341 |
| 33 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_38cfb4953e | 50 | 3 | 5 | 94.0 | 8.100842 | -11.146595 | 3.725371 |
| 34 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_bbd5f06d6e | 50 | 3 | 5 | 90.0 | 4.925901 | -10.344592 | 3.141312 |
| 35 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_966ca4f3dd | 91 | 5 | 10 | 91.2088 | 6.621543 | -10.891685 | 3.317815 |
| 36 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_7d142428bd | 90 | 5 | 9 | 91.1111 | 7.0709 | -10.891685 | 3.303549 |
| 37 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_37f933cccc | 50 | 3 | 5 | 88.0 | 4.493756 | -10.178777 | 2.849283 |
| 38 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_1b54da6f24 | 50 | 3 | 5 | 90.0 | 8.75747 | -10.742564 | 3.141312 |
| 39 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_02b4cfc3fa | 82 | 4 | 10 | 90.2439 | 6.859113 | -10.891685 | 3.176925 |
| 40 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_2b08d683e1 | 90 | 5 | 9 | 88.8889 | 8.808079 | -10.742564 | 2.979075 |
| 41 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_a755951e27 | 80 | 4 | 8 | 90.0 | 6.754297 | -10.891685 | 3.141312 |
| 42 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_5e91af0366 | 80 | 4 | 8 | 87.5 | 8.829032 | -10.742564 | 2.776276 |
| 43 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_6acd277bf9 | 60 | 3 | 6 | 88.3333 | 5.880668 | -10.891685 | 2.89795 |
| 44 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_373b5ef527 | 60 | 3 | 6 | 88.3333 | 5.880668 | -10.891685 | 2.89795 |
| 45 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_e3500402eb | 60 | 3 | 6 | 86.6667 | 9.48896 | -10.742564 | 2.654602 |
| 46 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_1cd42db518 | 60 | 3 | 6 | 86.6667 | 9.48896 | -10.742564 | 2.654602 |
| 47 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_9f2780315c | 60 | 3 | 6 | 86.6667 | 6.481145 | -10.891685 | 2.654602 |
| 48 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_5d93763594 | 60 | 3 | 6 | 86.6667 | 6.481145 | -10.891685 | 2.654602 |
| 49 | shadow_risk_review | top10_prob_plus_tail_tail0_compound2_aacc968471 | 50 | 3 | 5 | 82.0 | 2.718644 | -10.058162 | 1.973196 |
| 50 | shadow_ready | top10_prob_plus_tail_tail0_compound2_ff48ea613b | 52 | 3 | 7 | 80.7692 | 4.412321 | -8.245349 | 1.793481 |
