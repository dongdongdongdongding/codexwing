# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T12:50:49+00:00`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_buy_premium_exact_sanity_v4_20260401_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob` topn=`2` prob_threshold=`0.65` tail_threshold=`0.0`
- compound_filter: depth=`2` single_limit=`80` candidate_limit=`3000`
- base: status=`blocked` blockers=`['active_days_lt_20', 'min_low_5d_lt_neg10']` n=`58` days=`16` hit5=`84.4828` avg5=`11.02878` min_low=`-22.529631`
- filters_tested: `4179`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- candidate_frontier: total=`4179` sample=`0` low_safe=`838` hit_low_safe=`838` sample_low_safe=`0` sample_hit_low_safe=`0`
- candidate_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[1, 2, 3, 4, 5]` holdout_folds=`[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]` selection_candidates=`3234` holdout_evaluated=`3234` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`40` days=`11` hit5=`80.0` avg5=`8.288982` min_low=`-23.60242`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout_frontier: total=`3101` sample=`0` low_safe=`167` hit_low_safe=`156` sample_low_safe=`0` sample_hit_low_safe=`0`
- holdout_frontier_best_sample: status=`None` rule=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` blockers=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top2_prob_p0p65_tail0_compound2_099f7109e9 | 12 | 3 | 6 | 100.0 | 33.846508 | -7.614241 | 4.601458 |
| 2 | shadow_ready | top2_prob_p0p65_tail0_compound2_6b8d4c59be | 12 | 3 | 6 | 100.0 | 33.846508 | -7.614241 | 4.601458 |
| 3 | shadow_ready | top2_prob_p0p65_tail0_compound2_6598600824 | 12 | 3 | 6 | 100.0 | 27.618672 | -5.82776 | 4.601458 |
| 4 | shadow_ready | top2_prob_p0p65_tail0_compound2_a8fcb40e96 | 12 | 3 | 6 | 100.0 | 27.618672 | -5.82776 | 4.601458 |
| 5 | shadow_ready | top2_prob_p0p65_tail0_compound2_e55aea330b | 12 | 3 | 6 | 100.0 | 29.182525 | -7.271967 | 4.601458 |
| 6 | shadow_ready | top2_prob_p0p65_tail0_compound2_23683d867e | 12 | 3 | 6 | 100.0 | 29.182525 | -7.271967 | 4.601458 |
| 7 | shadow_ready | top2_prob_p0p65_tail0_compound2_e25586e76e | 12 | 3 | 6 | 100.0 | 29.182525 | -7.271967 | 4.601458 |
| 8 | shadow_ready | top2_prob_p0p65_tail0_compound2_982ce83b90 | 12 | 3 | 6 | 100.0 | 29.182525 | -7.271967 | 4.601458 |
| 9 | shadow_ready | top2_prob_p0p65_tail0_compound2_40a1d3cc38 | 16 | 3 | 8 | 100.0 | 26.640686 | -6.559247 | 4.601458 |
| 10 | shadow_ready | top2_prob_p0p65_tail0_compound2_9dfe04d546 | 16 | 3 | 8 | 100.0 | 26.640686 | -6.559247 | 4.601458 |
| 11 | shadow_ready | top2_prob_p0p65_tail0_compound2_652eeb5afd | 18 | 4 | 9 | 100.0 | 24.555227 | -6.559247 | 4.601458 |
| 12 | shadow_ready | top2_prob_p0p65_tail0_compound2_ae62f8271d | 16 | 3 | 8 | 100.0 | 23.84035 | -7.271967 | 4.601458 |
| 13 | shadow_ready | top2_prob_p0p65_tail0_compound2_9a7b7a680a | 16 | 3 | 8 | 100.0 | 23.84035 | -7.271967 | 4.601458 |
| 14 | shadow_ready | top2_prob_p0p65_tail0_compound2_36e99d0a00 | 16 | 3 | 8 | 100.0 | 20.792673 | -4.963962 | 4.601458 |
| 15 | shadow_ready | top2_prob_p0p65_tail0_compound2_22642feee5 | 16 | 3 | 8 | 100.0 | 20.792673 | -4.963962 | 4.601458 |
| 16 | shadow_ready | top2_prob_p0p65_tail0_compound2_1434e678ca | 18 | 4 | 9 | 100.0 | 19.356994 | -4.963962 | 4.601458 |
| 17 | shadow_ready | top2_prob_p0p65_tail0_compound2_0cb7653f67 | 26 | 8 | 13 | 100.0 | 21.318466 | -9.057457 | 4.601458 |
| 18 | shadow_ready | top2_prob_p0p65_tail0_compound2_0c8da329ab | 26 | 8 | 13 | 100.0 | 21.318466 | -9.057457 | 4.601458 |
| 19 | shadow_ready | top2_prob_p0p65_tail0_compound2_db2ef5cdf2 | 16 | 3 | 8 | 100.0 | 22.254633 | -7.271967 | 4.601458 |
| 20 | shadow_ready | top2_prob_p0p65_tail0_compound2_9c801b1313 | 16 | 3 | 8 | 100.0 | 22.254633 | -7.271967 | 4.601458 |
| 21 | shadow_ready | top2_prob_p0p65_tail0_compound2_36c6a8cf2f | 12 | 3 | 6 | 100.0 | 18.82263 | -4.963962 | 4.601458 |
| 22 | shadow_ready | top2_prob_p0p65_tail0_compound2_cd3ad12c87 | 12 | 3 | 6 | 100.0 | 18.82263 | -4.963962 | 4.601458 |
| 23 | shadow_ready | top2_prob_p0p65_tail0_close_failure_prior_market_avg_mfe_5d_pct_ge_15p5431 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 24 | shadow_ready | top2_prob_p0p65_tail0_close_failure_prior_market_avg_mae_5d_pct_ge_neg9p8844 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 25 | shadow_ready | top2_prob_p0p65_tail0_compound2_4f27853814 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 26 | shadow_ready | top2_prob_p0p65_tail0_compound2_678560b5a6 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 27 | shadow_ready | top2_prob_p0p65_tail0_compound2_caf066fd61 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 28 | shadow_ready | top2_prob_p0p65_tail0_compound2_ce7559ed4d | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 29 | shadow_ready | top2_prob_p0p65_tail0_compound2_0d06e371de | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 30 | shadow_ready | top2_prob_p0p65_tail0_compound2_e74cbf10a6 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 31 | shadow_ready | top2_prob_p0p65_tail0_compound2_4c52abd984 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 32 | shadow_ready | top2_prob_p0p65_tail0_compound2_9e6f79cb40 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 33 | shadow_ready | top2_prob_p0p65_tail0_compound2_c2a03b9c4a | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 34 | shadow_ready | top2_prob_p0p65_tail0_compound2_d0e3231ab6 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 35 | shadow_ready | top2_prob_p0p65_tail0_compound2_9fc9bbd2a8 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 36 | shadow_ready | top2_prob_p0p65_tail0_compound2_61e0ca924b | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 37 | shadow_ready | top2_prob_p0p65_tail0_compound2_a8b6cb7eec | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 38 | shadow_ready | top2_prob_p0p65_tail0_compound2_8d25dfc93a | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 39 | shadow_ready | top2_prob_p0p65_tail0_compound2_44ef45fb0d | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 40 | shadow_ready | top2_prob_p0p65_tail0_compound2_776e8aa827 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 41 | shadow_ready | top2_prob_p0p65_tail0_compound2_19f0048d82 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 42 | shadow_ready | top2_prob_p0p65_tail0_compound2_83a327b9db | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 43 | shadow_ready | top2_prob_p0p65_tail0_compound2_93d3becbf8 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 44 | shadow_ready | top2_prob_p0p65_tail0_compound2_68c37b5a79 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 45 | shadow_ready | top2_prob_p0p65_tail0_compound2_b2c75ea929 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 46 | shadow_ready | top2_prob_p0p65_tail0_compound2_d0b3c5727d | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 47 | shadow_ready | top2_prob_p0p65_tail0_compound2_864a9e8140 | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 48 | shadow_ready | top2_prob_p0p65_tail0_compound2_cf9dc646cd | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 49 | shadow_ready | top2_prob_p0p65_tail0_compound2_973964c73b | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
| 50 | shadow_ready | top2_prob_p0p65_tail0_compound2_38c260339f | 16 | 3 | 8 | 100.0 | 18.2082 | -4.963962 | 4.601458 |
