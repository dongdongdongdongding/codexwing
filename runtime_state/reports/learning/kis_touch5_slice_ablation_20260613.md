# KIS Touch5 Slice Ablation

- version: `kis_touch5_slice_ablation_v2`
- generated_at: `2026-06-13T14:06:02+00:00`
- dummy_data_used: `False`
- decision: `slice_ablation_blocks_production_replacement`
- production_replacement_ready: `False`
- recommended_action: `keep KIS model in shadow and continue actual sidecar backfill/forward tracking`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`
- feature_axis: `['all_features', 'all_minus_close_failure_prior', 'all_minus_theme_news', 'all_minus_kis_flow', 'close_failure_prior_only', 'kis_price_rank_quote_only', 'kis_flow_only', 'kis_static_financial_only', 'theme_news_only', 'scanner_technical_only']`

## Market Summary
| market | ok | production_ready | shadow | period_pass/periods | ablation_pass/ablations | dominant_prior |
|---|---:|---:|---:|---:|---:|---|
| KOSPI | 10 | 0 | 3 | 3/4 | 0/6 | False |
| KOSDAQ | 10 | 0 | 2 | 1/4 | 0/6 | False |

## Slice Feature Matrix
| market | mode | complete | periods_pass | full_feature_pass | best_feature | hit5 | min_low |
|---|---|---:|---:|---:|---|---:|---:|
| KOSPI | focused_partial | False | 3/4 | 0/7 | all_features | 100.0 | -8.188031 |
| KOSDAQ | focused_partial | False | 1/4 | 0/7 | all_features | 88.2353 | -9.837985 |

### Feature Winners
#### KOSPI
- config=`all_features` slice=`2026-05..2026-06` gate=`shadow_ready` n=`8` days=`3` hit5=`100.0` avg5=`8.426101` min_low=`-8.188031` outcome_pass=`True` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
- config=`all_minus_close_failure_prior` slice=`actual_available_full` gate=`blocked` n=`5` days=`3` hit5=`60.0` avg5=`3.040068` min_low=`-13.305564` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
- config=`all_minus_theme_news` slice=`actual_available_full` gate=`blocked` n=`5` days=`2` hit5=`60.0` avg5=`4.962856` min_low=`-8.737024` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
- config=`all_minus_kis_flow` slice=`actual_available_full` gate=`blocked` n=`3` days=`1` hit5=`33.3333` avg5=`1.622779` min_low=`-8.737024` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
- config=`close_failure_prior_only` slice=`actual_available_full` gate=`blocked` n=`1` days=`1` hit5=`0.0` avg5=`-11.849118` min_low=`-14.863855` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
- config=`kis_price_rank_quote_only` slice=`actual_available_full` gate=`blocked` n=`2` days=`2` hit5=`50.0` avg5=`-5.087658` min_low=`-23.585434` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
- config=`scanner_technical_only` slice=`actual_available_full` gate=`blocked` n=`11` days=`6` hit5=`9.0909` avg5=`-12.571841` min_low=`-24.61343` outcome_pass=`False` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
#### KOSDAQ
- config=`all_features` slice=`2026-05` gate=`shadow_ready` n=`17` days=`3` hit5=`88.2353` avg5=`9.402924` min_low=`-9.837985` outcome_pass=`True` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
- config=`all_minus_close_failure_prior` slice=`actual_available_full` gate=`blocked` n=`1` days=`1` hit5=`0.0` avg5=`-2.995802` min_low=`-3.570812` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
- config=`all_minus_theme_news` slice=`actual_available_full` gate=`blocked` n=`2` days=`1` hit5=`0.0` avg5=`-2.552118` min_low=`-7.128514` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
- config=`all_minus_kis_flow` slice=`actual_available_full` gate=`blocked` n=`3` days=`1` hit5=`0.0` avg5=`-4.770998` min_low=`-14.334666` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
- config=`close_failure_prior_only` slice=`actual_available_full` gate=`blocked` n=`3` days=`1` hit5=`66.6667` avg5=`-5.931222` min_low=`-14.578702` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
- config=`kis_price_rank_quote_only` slice=`actual_available_full` gate=`blocked` n=`2` days=`1` hit5=`0.0` avg5=`-3.076093` min_low=`-4.351985` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
- config=`scanner_technical_only` slice=`actual_available_full` gate=`blocked` n=`2` days=`2` hit5=`50.0` avg5=`-6.814654` min_low=`-11.803161` outcome_pass=`False` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`

## Best Results
### KOSPI
1. slice=`2026-05..2026-06` config=`all_features` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`shadow_ready` n=`8` days=`3` hit5=`100.0` avg5=`8.426101` min_low=`-8.188031` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
2. slice=`2026-05` config=`all_features` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`shadow_ready` n=`25` days=`6` hit5=`96.0` avg5=`5.862451` min_low=`-8.188031` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
3. slice=`2026-04..2026-05` config=`all_features` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`shadow_ready` n=`25` days=`6` hit5=`88.0` avg5=`4.54865` min_low=`-8.737024` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
4. slice=`actual_available_full` config=`all_minus_close_failure_prior` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`blocked` n=`5` days=`3` hit5=`60.0` avg5=`3.040068` min_low=`-13.305564` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
5. slice=`actual_available_full` config=`all_features` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`blocked` n=`6` days=`3` hit5=`66.6667` avg5=`5.792931` min_low=`-8.737024` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
6. slice=`actual_available_full` config=`all_minus_theme_news` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`blocked` n=`5` days=`2` hit5=`60.0` avg5=`4.962856` min_low=`-8.737024` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
7. slice=`actual_available_full` config=`scanner_technical_only` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`blocked` n=`11` days=`6` hit5=`9.0909` avg5=`-12.571841` min_low=`-24.61343` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
8. slice=`actual_available_full` config=`all_minus_kis_flow` rule=`top2_prob_plus_tail_p0p8_tail0p85` status=`blocked` n=`3` days=`1` hit5=`33.3333` avg5=`1.622779` min_low=`-8.737024` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
### KOSDAQ
1. slice=`2026-05` config=`all_features` rule=`top3_ev_tail0p9` status=`shadow_ready` n=`17` days=`3` hit5=`88.2353` avg5=`9.402924` min_low=`-9.837985` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
2. slice=`2026-04..2026-05` config=`all_features` rule=`top3_ev_tail0p9` status=`shadow_risk_review` n=`18` days=`3` hit5=`83.3333` avg5=`9.761324` min_low=`-13.338014` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'min_low_5d_lt_neg10']`
3. slice=`actual_available_full` config=`scanner_technical_only` rule=`top3_ev_tail0p9` status=`blocked` n=`2` days=`2` hit5=`50.0` avg5=`-6.814654` min_low=`-11.803161` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. slice=`actual_available_full` config=`close_failure_prior_only` rule=`top3_ev_tail0p9` status=`blocked` n=`3` days=`1` hit5=`66.6667` avg5=`-5.931222` min_low=`-14.578702` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. slice=`2026-05..2026-06` config=`all_features` rule=`top3_ev_tail0p9` status=`blocked` n=`2` days=`1` hit5=`0.0` avg5=`-2.552118` min_low=`-7.128514` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
6. slice=`actual_available_full` config=`all_minus_theme_news` rule=`top3_ev_tail0p9` status=`blocked` n=`2` days=`1` hit5=`0.0` avg5=`-2.552118` min_low=`-7.128514` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
7. slice=`actual_available_full` config=`kis_price_rank_quote_only` rule=`top3_ev_tail0p9` status=`blocked` n=`2` days=`1` hit5=`0.0` avg5=`-3.076093` min_low=`-4.351985` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
8. slice=`actual_available_full` config=`all_features` rule=`top3_ev_tail0p9` status=`blocked` n=`1` days=`1` hit5=`0.0` avg5=`-2.995802` min_low=`-3.570812` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
