# KIS Touch5 Drawdown Filter Research

- version: `kis_touch5_drawdown_filter_research_v1`
- status: `no_production_gate_pass_candidate`
- validation_mode: `research_sweep_only_walk_forward_predictions`
- deployment_ready: `False`
- generated_at: `2026-06-13T12:06:38+00:00`
- prepared_cache: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl`
- market: `KOSDAQ`
- selection: score_mode=`prob_tail_margin` topn=`3` prob_threshold=`0.5` tail_threshold=`0.0`
- compound_filter: depth=`2` single_limit=`80` candidate_limit=`3000`
- base: status=`blocked` blockers=`['active_days_lt_20', 'min_low_5d_lt_neg10']` n=`82` days=`13` hit5=`73.1707` avg5=`5.138529` min_low=`-21.915669`
- filters_tested: `4098`
- production_ready_count: `0`
- best_filter: `{}`
- best: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- holdout: status=`no_holdout_gate_pass` validation=`selection_fixed_rule_holdout_walk_forward_predictions` selection_folds=`[2, 3, 4, 5, 6]` holdout_folds=`[7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` selection_candidates=`3958` holdout_evaluated=`3958` gate_pass_count=`0` deployment_ready=`False`
- selection_best_holdout: status=`blocked` n=`52` days=`7` hit5=`63.4615` avg5=`4.200313` min_low=`-31.118999`
- best_holdout_gate_pass: status=`None` n=`None` days=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None`
- rolling_prior: status=`skipped_by_operator` validation=`None` min_prior_folds=`None` evaluated_steps=`None` selected=`None` deployment_ready=`False`
- rolling_prior_aggregate: status=`None` n=`None` days=`None` runs=`None` hit5=`None` avg5=`None` min_low=`None` expected_net=`None` blockers=`None`

| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_537872383d | 16 | 3 | 6 | 100.0 | 24.050376 | -9.786204 | 4.601458 |
| 2 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_3232921bc0 | 18 | 3 | 6 | 100.0 | 22.21043 | -9.786204 | 4.601458 |
| 3 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_f5e94e3e56 | 18 | 3 | 6 | 100.0 | 22.21043 | -9.786204 | 4.601458 |
| 4 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_d5c04c95f0 | 19 | 4 | 7 | 100.0 | 21.485966 | -9.786204 | 4.601458 |
| 5 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_1a2ac065ed | 19 | 4 | 7 | 100.0 | 21.485966 | -9.786204 | 4.601458 |
| 6 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_70017fe6de | 15 | 3 | 5 | 100.0 | 14.170073 | -5.062696 | 4.601458 |
| 7 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_398aff7c94 | 15 | 3 | 5 | 100.0 | 14.170073 | -5.062696 | 4.601458 |
| 8 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_364b55afb5 | 15 | 3 | 5 | 100.0 | 14.170073 | -5.062696 | 4.601458 |
| 9 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_435ecbe89b | 15 | 3 | 5 | 100.0 | 14.170073 | -5.062696 | 4.601458 |
| 10 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_e60a9319ee | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 11 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_57ab8182d3 | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 12 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_d5836cccbe | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 13 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_d85086c27f | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 14 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_8b7a5a023b | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 15 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_225b46f402 | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 16 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_ece733fab6 | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 17 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_42a3d99a9b | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 18 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_78cf7f033c | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 19 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_4b065aaf0e | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 20 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_cf967abb9c | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 21 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_c322092e62 | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 22 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_333a14fdfd | 18 | 4 | 6 | 100.0 | 13.402796 | -5.062696 | 4.601458 |
| 23 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_f729a45a32 | 39 | 7 | 13 | 100.0 | 12.052509 | -6.060289 | 4.601458 |
| 24 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_9779618d5e | 39 | 7 | 13 | 100.0 | 12.052509 | -6.060289 | 4.601458 |
| 25 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_9db5752cbc | 21 | 5 | 7 | 100.0 | 13.473955 | -6.060289 | 4.601458 |
| 26 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_9595c8fd2f | 21 | 5 | 7 | 100.0 | 13.473955 | -6.060289 | 4.601458 |
| 27 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_f8093e17f0 | 21 | 5 | 7 | 100.0 | 13.473955 | -6.060289 | 4.601458 |
| 28 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_c02d9486e1 | 18 | 4 | 6 | 100.0 | 14.125212 | -6.060289 | 4.601458 |
| 29 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_4334c42e8b | 18 | 4 | 6 | 100.0 | 14.125212 | -6.060289 | 4.601458 |
| 30 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_8fdb143095 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 31 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_74b99eb639 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 32 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_54952e2222 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 33 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_1c95ebc823 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 34 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_e698a8cbdd | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 35 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_742fe6a807 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 36 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_0bb9d86161 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 37 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_69dbe991bf | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 38 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_ae5b50d5a8 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 39 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_944ac958a6 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 40 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_8671fcec53 | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 41 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_1c1c32e64f | 39 | 7 | 13 | 100.0 | 11.585255 | -6.060289 | 4.601458 |
| 42 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_38ff8afa2e | 30 | 6 | 10 | 100.0 | 12.441152 | -6.060289 | 4.601458 |
| 43 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_f2fab8d80d | 30 | 6 | 10 | 100.0 | 12.441152 | -6.060289 | 4.601458 |
| 44 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_4b6352807e | 31 | 7 | 11 | 100.0 | 16.132203 | -9.786204 | 4.601458 |
| 45 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_403e6ecbfd | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
| 46 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_2b80f8d269 | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
| 47 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_d207ea4cfa | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
| 48 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_da34c8076b | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
| 49 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_99267ca008 | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
| 50 | shadow_ready | top3_prob_tail_margin_p0p5_tail0_compound2_d2f139e00e | 30 | 6 | 10 | 100.0 | 12.051447 | -6.060289 | 4.601458 |
