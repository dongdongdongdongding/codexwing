# Significant Feature Combination Mining

- generated_at: `2026-05-27T01:27:18.810318+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4203`
- mined_combinations: `60`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSDAQ | ranked_top20 | 5d | 1 | 7 | 4 | 42.857 | -5.4405 | -27.3349 | 8.9947 | 85.714 | 42.857 | expected_return_1d_pct <= -0.88 |
| 2 | KOSDAQ | ranked_top20 | 5d | 3 | 8 | 5 | 37.5 | -3.7469 | -17.2391 | 16.4962 | 75.0 | 50.0 | decision_score <= 76<br>ml_prob <= 44.63<br>whale_score <= 62 |
| 3 | KOSDAQ | ranked_top20 | 5d | 1 | 8 | 4 | 37.5 | -5.5014 | -27.3349 | 8.9947 | 87.5 | 50.0 | expected_edge_score <= -11.5375 |
| 4 | KOSDAQ | ranked_top20 | 5d | 1 | 8 | 4 | 37.5 | -5.5014 | -27.3349 | 8.9947 | 87.5 | 50.0 | expected_return_3d_pct <= -1.4625 |
| 5 | KOSDAQ | ranked_top20 | 5d | 3 | 12 | 6 | 33.333 | -5.0204 | -19.1582 | 16.4962 | 75.0 | 50.0 | decision_score <= 83.3<br>ml_prob <= 44.63<br>whale_score <= 62 |
| 6 | KOSDAQ | ranked_top20 | 5d | 3 | 9 | 5 | 33.333 | -5.9005 | -23.1293 | 16.4962 | 77.778 | 44.444 | decision_score <= 76<br>ml_prob <= 49.2<br>whale_score <= 62 |
| 7 | KOSDAQ | ranked_top20 | 5d | 1 | 95 | 6 | 32.632 | -4.0671 | -46.3097 | 34.4353 | 80.0 | 46.316 | alpha_score <= 66 |
| 8 | KOSDAQ | ranked_top20 | 5d | 1 | 62 | 6 | 32.258 | -4.6077 | -27.3349 | 34.4353 | 83.871 | 46.774 | decision == EXCEPTION_LEADER |
| 9 | KOSDAQ | ranked_top20 | 5d | 1 | 62 | 6 | 32.258 | -4.6077 | -27.3349 | 34.4353 | 83.871 | 46.774 | decision_bucket == exception_leader |
| 10 | KOSDAQ | ranked_top20 | 5d | 1 | 62 | 6 | 32.258 | -4.6077 | -27.3349 | 34.4353 | 83.871 | 46.774 | exception_leader == True |
| 11 | KOSDAQ | ranked_top20 | 5d | 1 | 39 | 6 | 30.769 | -4.265 | -27.3349 | 20.3463 | 79.487 | 48.718 | alpha_score <= 53.85 |
| 12 | KOSDAQ | ranked_top20 | 5d | 3 | 13 | 6 | 30.769 | -6.4134 | -23.1293 | 16.4962 | 76.923 | 46.154 | decision_score <= 83.3<br>ml_prob <= 49.2<br>whale_score <= 62 |
| 13 | KOSDAQ | ranked_top20 | 5d | 2 | 41 | 6 | 29.268 | -6.4902 | -25.9487 | 20.3463 | 80.488 | 48.78 | conviction_score <= 66.3<br>whale_score <= 70 |
| 14 | KOSDAQ | ranked_top20 | 5d | 2 | 34 | 6 | 26.471 | -6.9056 | -25.9487 | 16.4962 | 79.412 | 41.176 | alpha_score <= 72<br>whale_score <= 62 |
| 15 | KOSDAQ | ranked_top20 | 5d | 2 | 19 | 6 | 26.316 | -7.9919 | -25.9487 | 16.4962 | 78.947 | 52.632 | ml_prob <= 44.63<br>whale_score <= 62 |
| 16 | KOSDAQ | ranked_top20 | 5d | 3 | 19 | 6 | 26.316 | -7.9919 | -25.9487 | 16.4962 | 78.947 | 52.632 | alpha_score <= 87<br>ml_prob <= 44.63<br>whale_score <= 62 |
| 17 | KOSDAQ | ranked_top20 | 5d | 2 | 23 | 6 | 26.087 | -6.5104 | -24.4872 | 16.4962 | 82.609 | 39.13 | decision_score <= 76<br>whale_score <= 62 |
| 18 | KOSDAQ | ranked_top20 | 5d | 1 | 12 | 6 | 25.0 | -9.7395 | -46.3097 | 8.9947 | 91.667 | 41.667 | expected_edge_score <= -7.4675 |
| 19 | KOSDAQ | ranked_top20 | 5d | 1 | 12 | 6 | 25.0 | -9.7395 | -46.3097 | 8.9947 | 91.667 | 41.667 | expected_return_3d_pct <= -0.9125 |
| 20 | KOSDAQ | ranked_top20 | 5d | 1 | 12 | 6 | 25.0 | -9.7395 | -46.3097 | 8.9947 | 91.667 | 41.667 | expected_return_1d_pct <= -0.53 |
| 21 | KOSDAQ | ranked_top20 | 5d | 1 | 78 | 6 | 24.359 | -7.1086 | -25.9487 | 27.4744 | 85.897 | 46.154 | whale_score <= 74.5 |
| 22 | KOSDAQ | ranked_top20 | 5d | 1 | 37 | 6 | 24.324 | -7.6797 | -25.9487 | 16.4962 | 81.081 | 45.946 | whale_score <= 62 |
| 23 | KOSDAQ | ranked_top20 | 5d | 2 | 37 | 6 | 24.324 | -7.6797 | -25.9487 | 16.4962 | 81.081 | 45.946 | alpha_score <= 87<br>whale_score <= 62 |
| 24 | KOSDAQ | ranked_top20 | 5d | 1 | 79 | 6 | 24.051 | -5.5327 | -46.3097 | 27.4744 | 84.81 | 48.101 | decision_score <= 76 |
| 25 | KOSDAQ | ranked_top20 | 5d | 2 | 21 | 6 | 23.809 | -8.7505 | -25.9487 | 16.4962 | 80.952 | 52.381 | ml_prob <= 49.2<br>whale_score <= 62 |
| 26 | KOSDAQ | ranked_top20 | 5d | 2 | 21 | 6 | 23.809 | -8.7505 | -25.9487 | 16.4962 | 80.952 | 52.381 | ml_prob <= 50<br>whale_score <= 62 |
| 27 | KOSDAQ | ranked_top20 | 5d | 3 | 21 | 6 | 23.809 | -8.7505 | -25.9487 | 16.4962 | 80.952 | 52.381 | alpha_score <= 87<br>ml_prob <= 49.2<br>whale_score <= 62 |
| 28 | KOSDAQ | ranked_top20 | 5d | 3 | 21 | 6 | 23.809 | -8.7505 | -25.9487 | 16.4962 | 80.952 | 52.381 | alpha_score <= 87<br>ml_prob <= 50<br>whale_score <= 62 |
| 29 | KOSDAQ | ranked_top20 | 5d | 2 | 13 | 5 | 23.077 | -6.2363 | -23.1293 | 27.4744 | 84.615 | 38.462 | decision_score <= 72<br>theme_inference_status == blank |
| 30 | KOSDAQ | ranked_top20 | 5d | 2 | 13 | 5 | 23.077 | -6.2363 | -23.1293 | 27.4744 | 84.615 | 38.462 | decision_score <= 76<br>theme_inference_status == blank |
| 31 | KOSDAQ | ranked_top20 | 5d | 2 | 41 | 6 | 21.951 | -7.8958 | -25.9487 | 16.4962 | 82.927 | 46.342 | alpha_score <= 72<br>whale_score <= 69 |
| 32 | KOSDAQ | ranked_top20 | 5d | 1 | 61 | 6 | 21.311 | -7.9663 | -25.9487 | 20.3463 | 86.885 | 50.82 | whale_score <= 70 |
| 33 | KOSDAQ | ranked_top20 | 5d | 1 | 43 | 6 | 20.93 | -5.9219 | -23.1293 | 14.6138 | 88.372 | 51.163 | decision_score <= 62 |
| 34 | KOSDAQ | ranked_top20 | 5d | 1 | 73 | 6 | 20.548 | -6.1017 | -46.3097 | 27.4744 | 86.301 | 50.685 | decision_score <= 72 |
| 35 | KOSDAQ | ranked_top20 | 5d | 2 | 20 | 6 | 20.0 | -7.5716 | -24.4872 | 16.4962 | 85.0 | 40.0 | decision_score <= 72<br>whale_score <= 62 |
| 36 | KOSDAQ | ranked_top20 | 5d | 3 | 20 | 6 | 20.0 | -7.5716 | -24.4872 | 16.4962 | 85.0 | 40.0 | alpha_score <= 87<br>decision_score <= 72<br>whale_score <= 62 |
| 37 | KOSDAQ | ranked_top20 | 5d | 3 | 20 | 6 | 20.0 | -8.2335 | -22.4502 | 20.3463 | 95.0 | 65.0 | alpha_score <= 87<br>priority_rank <= 4<br>whale_score <= 70 |
| 38 | KOSDAQ | ranked_top20 | 5d | 1 | 46 | 6 | 19.565 | -8.8455 | -25.9487 | 16.4962 | 84.783 | 50.0 | whale_score <= 69 |
| 39 | KOSDAQ | ranked_top20 | 5d | 2 | 21 | 6 | 19.048 | -8.869 | -22.4502 | 20.3463 | 95.238 | 61.905 | priority_rank <= 4<br>whale_score <= 70 |
| 40 | KOSDAQ | ranked_top20 | 5d | 2 | 27 | 6 | 18.518 | -7.1182 | -46.3097 | 13.8511 | 85.185 | 51.852 | decision_score <= 72<br>priority_rank <= 4 |
| 41 | KOSDAQ | ranked_top20 | 5d | 2 | 22 | 5 | 18.182 | -8.8586 | -24.4872 | 11.1111 | 86.364 | 54.546 | kr_universe_role == TRANSITIONAL<br>whale_score <= 62 |
| 42 | KOSDAQ | ranked_top20 | 5d | 2 | 17 | 5 | 17.647 | -8.105 | -24.4872 | 11.1111 | 88.235 | 47.059 | tier == ⚡T3<br>whale_score <= 62 |
| 43 | KOSDAQ | ranked_top20 | 5d | 1 | 18 | 5 | 16.667 | -10.693 | -23.1481 | 16.7081 | 83.333 | 44.444 | decision_score >= 96.07 |
| 44 | KOSDAQ | ranked_top20 | 5d | 2 | 25 | 6 | 16.0 | -8.1889 | -24.4872 | 16.4962 | 88.0 | 44.0 | decision_score <= 72<br>whale_score <= 69 |
| 45 | KOSDAQ | ranked_top20 | 5d | 3 | 25 | 6 | 16.0 | -8.1889 | -24.4872 | 16.4962 | 88.0 | 44.0 | alpha_score <= 87<br>decision_score <= 72<br>whale_score <= 69 |
| 46 | KOSDAQ | ranked_top20 | 5d | 2 | 34 | 6 | 14.706 | -8.1336 | -24.4872 | 16.4962 | 91.177 | 50.0 | decision_score <= 72<br>whale_score <= 70 |
| 47 | KOSDAQ | ranked_top20 | 5d | 3 | 34 | 6 | 14.706 | -8.1336 | -24.4872 | 16.4962 | 91.177 | 50.0 | alpha_score <= 87<br>decision_score <= 72<br>whale_score <= 70 |
| 48 | KOSDAQ | ranked_top20 | 5d | 3 | 21 | 5 | 14.286 | -8.5762 | -24.4872 | 11.1111 | 90.476 | 47.619 | decision_score <= 72<br>tier == ⚡T3<br>whale_score <= 69 |
| 49 | KOSDAQ | ranked_top20 | 5d | 3 | 14 | 5 | 14.286 | -10.5244 | -19.1582 | 4.7561 | 92.857 | 71.429 | ml_prob <= 44.63<br>volume_ratio <= 1.29<br>whale_score <= 62 |
| 50 | KOSDAQ | ranked_top20 | 5d | 2 | 22 | 5 | 13.636 | -8.6852 | -24.4872 | 11.1111 | 90.909 | 50.0 | tier == ⚡T3<br>whale_score <= 69 |
| 51 | KOSDAQ | ranked_top20 | 5d | 3 | 22 | 5 | 13.636 | -8.6852 | -24.4872 | 11.1111 | 90.909 | 50.0 | alpha_score <= 87<br>tier == ⚡T3<br>whale_score <= 69 |
| 52 | KOSDAQ | ranked_top20 | 5d | 3 | 30 | 5 | 13.333 | -9.0596 | -24.4872 | 14.6138 | 93.333 | 56.667 | decision_score <= 72<br>volume_ratio <= 1.29<br>whale_score <= 70 |
| 53 | KOSDAQ | ranked_top20 | 5d | 2 | 32 | 5 | 12.5 | -10.7483 | -24.4872 | 11.1111 | 87.5 | 56.25 | volume_ratio <= 1.09<br>whale_score <= 69 |
| 54 | KOSDAQ | ranked_top20 | 5d | 3 | 32 | 5 | 12.5 | -10.7483 | -24.4872 | 11.1111 | 87.5 | 56.25 | alpha_score <= 87<br>volume_ratio <= 1.09<br>whale_score <= 69 |
| 55 | KOSDAQ | ranked_top20 | 5d | 3 | 16 | 5 | 12.5 | -11.2035 | -23.1293 | 4.7561 | 93.75 | 68.75 | ml_prob <= 49.2<br>volume_ratio <= 1.29<br>whale_score <= 62 |
| 56 | KOSDAQ | ranked_top20 | 5d | 3 | 8 | 5 | 12.5 | -11.7126 | -23.1293 | 16.4962 | 87.5 | 37.5 | decision_score <= 72<br>ml_prob <= 49.2<br>whale_score <= 69 |
| 57 | KOSDAQ | ranked_top20 | 5d | 2 | 14 | 5 | 7.143 | -11.854 | -22.4502 | 0.6504 | 100.0 | 64.286 | priority_rank <= 4<br>whale_score <= 69 |
| 58 | KOSDAQ | ranked_top20 | 5d | 3 | 18 | 5 | 5.556 | -13.9686 | -23.1481 | 4.6569 | 94.444 | 66.667 | ml_prob <= 49.2<br>volume_ratio <= 1.09<br>whale_score <= 69 |
| 59 | KOSDAQ | ranked_top20 | 5d | 3 | 18 | 5 | 5.556 | -13.9686 | -23.1481 | 4.6569 | 94.444 | 66.667 | ml_prob <= 50<br>volume_ratio <= 1.09<br>whale_score <= 69 |
| 60 | KOSDAQ | ranked_top20 | 5d | 1 | 11 | 3 | 0.0 | -13.8863 | -27.3349 | -1.494 | 100.0 | 72.727 | ml_prob <= 31.6 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `1`
- candidate features: `{'numeric': 34, 'categorical': 25, 'total': 59}`
- predicates: `{'raw': 293, 'unique': 293, 'after_support_screen': 260, 'numeric': 246, 'categorical': 47, 'duplicates': 0}`
- predicate support screen: `{'kept': 260, 'rejected_test_support': 31, 'rejected_train_support': 7}`
- result counts: `{'mined_combinations': 60, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 1}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `5d`: `{'test_win': 60, 'test_avg': 60, 'test_bad_path': 60, 'test_stop5': 60, 'train_bad_path': 18, 'test_days': 4, 'train_win': 4, 'test_n': 1}`

### Beam Pruning
- `5d`: `{'attempted': 1600, 'rejected_train_n': 778, 'rejected_test_n': 664, 'expanded_survivors': 282, 'pruned_by_beam': 242, 'skipped_feature_conflict': 206, 'base_pool': 80, 'skipped_duplicate': 57, 'parent_beam': 40, 'next_beam': 40, 'emitted': 40, 'rejected_test_days': 38, 'rejected_train_days': 9}`

### Scope Diagnostics
- `KOSDAQ` `ranked_top20` rows=835 days=39 predicates=260 results=60 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
