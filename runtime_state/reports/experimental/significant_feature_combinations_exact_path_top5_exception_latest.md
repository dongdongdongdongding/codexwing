# Significant Feature Combination Mining

- generated_at: `2026-06-29T07:04:58.718518+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4882`
- quality_scope: `exact_path`
- mined_combinations: `576`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSDAQ | top5_exception | 5d | 1 | 2 | 2 | 100.0 | 3.8535 | 3.212 | 4.4951 | 0.0 | 0.0 | ml_prob <= 23.3 |
| 2 | KOSDAQ | top5_exception | 3d | 3 | 6 | 6 | 83.333 | 3.3386 | -17.2662 | 20.6642 | 100.0 | 50.0 | alpha_score <= 53<br>priority_rank <= 1<br>selection_lane == 3d |
| 3 | KOSDAQ | top5_exception | 3d | 2 | 9 | 6 | 77.778 | 2.1005 | -17.2662 | 20.6642 | 88.889 | 44.444 | alpha_score <= 53<br>priority_rank <= 1 |
| 4 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 72.727 | 6.6581 | -25.5403 | 28.4932 | 54.546 | 18.182 | alpha_score <= 70.5<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 4 |
| 5 | KOSDAQ | top5_exception | 3d | 3 | 7 | 5 | 71.429 | 2.0591 | -17.2662 | 20.6642 | 85.714 | 42.857 | alpha_score <= 53<br>kr_universe_role == CORE_TREND<br>priority_rank <= 1 |
| 6 | KOSDAQ | top5_exception | 3d | 3 | 7 | 5 | 71.429 | 2.0591 | -17.2662 | 20.6642 | 85.714 | 42.857 | alpha_score <= 53<br>core_trend_flag_bool == True<br>priority_rank <= 1 |
| 7 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 1.9545 | -6.8182 | 20.6642 | 100.0 | 14.286 | alpha_score <= 42.35<br>priority_rank <= 10 |
| 8 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.777 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>decision_score <= 91 |
| 9 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.777 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>decision_score <= 90 |
| 10 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.494 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>feature_completeness <= 0.9 |
| 11 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.494 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>feature_quality == incomplete |
| 12 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.494 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>feature_completeness <= 0.8 |
| 13 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.494 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>kr_universe_role == CORE_TREND |
| 14 | KOSDAQ | top5_exception | 3d | 2 | 7 | 6 | 71.429 | 0.494 | -15.0606 | 20.6642 | 100.0 | 28.571 | alpha_score <= 42.35<br>core_trend_flag_bool == True |
| 15 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_score >= 105<br>decision == EXCEPTION_LEADER |
| 16 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_bucket == exception_leader<br>decision_score >= 105 |
| 17 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_score >= 105<br>exception_leader == True |
| 18 | KOSDAQ | top5_exception | 3d | 1 | 3 | 3 | 66.667 | 2.5535 | -15.9341 | 12.6338 | 0.0 | 0.0 | ml_prob <= 23.3 |
| 19 | KOSPI | top5_exception | 5d | 3 | 9 | 5 | 66.667 | 2.0731 | -14.6497 | 9.6426 | 66.667 | 44.444 | feature_quality == incomplete<br>kr_universe_role == EXPLOSIVE_LEADER<br>priority_rank <= 1 |
| 20 | KOSPI | top5_exception | 5d | 3 | 9 | 5 | 66.667 | 2.0731 | -14.6497 | 9.6426 | 66.667 | 44.444 | explosive_leader_flag_bool == True<br>feature_quality == incomplete<br>priority_rank <= 1 |
| 21 | KOSDAQ | top5_exception | 3d | 2 | 6 | 5 | 66.667 | 1.9954 | -6.8182 | 20.6642 | 100.0 | 16.667 | alpha_score <= 42.35<br>priority_rank <= 6.8 |
| 22 | KOSDAQ | top5_exception | 3d | 2 | 6 | 5 | 66.667 | 1.9954 | -6.8182 | 20.6642 | 100.0 | 16.667 | alpha_score <= 42.35<br>priority_rank <= 4 |
| 23 | KOSDAQ | top5_exception | 3d | 2 | 6 | 5 | 66.667 | 1.9954 | -6.8182 | 20.6642 | 100.0 | 16.667 | alpha_score <= 42.35<br>priority_rank <= 5 |
| 24 | KOSDAQ | top5_exception | 3d | 3 | 6 | 6 | 66.667 | 0.7668 | -6.8182 | 7.7586 | 100.0 | 16.667 | alpha_score <= 65<br>decision_score >= 79.8<br>prob_clean <= 24.975 |
| 25 | KOSPI | top5_exception | 5d | 3 | 6 | 4 | 66.667 | -0.533 | -25.5403 | 24.2188 | 50.0 | 16.667 | alpha_score <= 66<br>decision_bucket == watchlist<br>feature_origin == scanner_archive_outcome |
| 26 | KOSPI | top5_exception | 5d | 3 | 6 | 4 | 66.667 | -0.533 | -25.5403 | 24.2188 | 50.0 | 16.667 | alpha_score <= 66<br>exception_leader == False<br>feature_origin == scanner_archive_outcome |
| 27 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 99.55<br>decision == EXCEPTION_LEADER |
| 28 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 100<br>decision == EXCEPTION_LEADER |
| 29 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_bucket == exception_leader<br>decision_score >= 99.55 |
| 30 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_bucket == exception_leader<br>decision_score >= 100 |
| 31 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 99.55<br>exception_leader == True |
| 32 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 100<br>exception_leader == True |
| 33 | KOSDAQ | top5_exception | 3d | 2 | 11 | 7 | 63.636 | 1.7127 | -15.0606 | 20.6642 | 90.909 | 45.454 | alpha_score <= 53<br>prob_clean <= 24.975 |
| 34 | KOSPI | top5_exception | 3d | 2 | 8 | 6 | 62.5 | 3.3362 | -6.1602 | 18.0822 | 50.0 | 12.5 | alpha_score <= 66<br>decision_score >= 99.55 |
| 35 | KOSPI | top5_exception | 3d | 2 | 8 | 6 | 62.5 | 3.3362 | -6.1602 | 18.0822 | 50.0 | 12.5 | alpha_score <= 66<br>decision_score >= 100 |
| 36 | KOSPI | top5_exception | 3d | 3 | 8 | 6 | 62.5 | 3.3362 | -6.1602 | 18.0822 | 50.0 | 12.5 | alpha_score <= 66<br>decision_score >= 99.55<br>priority_rank >= 3 |
| 37 | KOSPI | top5_exception | 3d | 3 | 8 | 6 | 62.5 | 3.3362 | -6.1602 | 18.0822 | 50.0 | 12.5 | alpha_score <= 66<br>decision_score >= 100<br>priority_rank >= 3 |
| 38 | KOSDAQ | top5_exception | 3d | 1 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35 |
| 39 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 32.935 |
| 40 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 34.625 |
| 41 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 30.3 |
| 42 | KOSPI | top5_exception | 5d | 2 | 5 | 4 | 60.0 | 8.6036 | -6.5708 | 28.4932 | 40.0 | 20.0 | decision_score >= 105<br>ml_prob <= 32.7 |
| 43 | KOSPI | top5_exception | 3d | 1 | 5 | 4 | 60.0 | -0.3936 | -10.6122 | 10.7943 | 60.0 | 20.0 | trend == NEUTRAL |
| 44 | KOSPI | top5_exception | 3d | 2 | 5 | 4 | 60.0 | -0.3936 | -10.6122 | 10.7943 | 60.0 | 20.0 | feature_quality == incomplete<br>trend == NEUTRAL |
| 45 | KOSDAQ | top5_exception | 3d | 3 | 5 | 4 | 60.0 | -1.7384 | -6.8182 | 1.6313 | 100.0 | 0.0 | alpha_score <= 42.35<br>priority_rank <= 4<br>theme_source == stock_master |
| 46 | KOSDAQ | top5_exception | 5d | 2 | 5 | 4 | 60.0 | -2.4158 | -15.7978 | 8.2657 | 100.0 | 40.0 | alpha_score <= 42.35<br>decision_score <= 79.8 |
| 47 | KOSDAQ | top5_exception | 5d | 3 | 5 | 4 | 60.0 | -2.4158 | -15.7978 | 8.2657 | 100.0 | 40.0 | alpha_score <= 42.35<br>decision_score <= 79.8<br>prob_clean >= 20.185 |
| 48 | KOSPI | top5_exception | 5d | 3 | 31 | 7 | 58.064 | 5.0303 | -25.5403 | 52.1531 | 54.839 | 32.258 | alpha_score <= 70.5<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 25.5 |
| 49 | KOSDAQ | top5_exception | 3d | 1 | 7 | 5 | 57.143 | 0.4653 | -8.0429 | 12.0863 | 71.429 | 0.0 | expected_edge_score >= 8.076 |
| 50 | KOSDAQ | top5_exception | 3d | 2 | 7 | 5 | 57.143 | 0.4653 | -8.0429 | 12.0863 | 71.429 | 0.0 | alpha_score <= 84<br>expected_edge_score >= 8.076 |
| 51 | KOSPI | top5_exception | 5d | 3 | 7 | 4 | 57.143 | -0.894 | -19.2714 | 12.5691 | 85.714 | 71.429 | alpha_score >= 83<br>priority_rank >= 5<br>prob_clean >= 32.325 |
| 52 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 54.546 | -0.3584 | -14.6497 | 9.6426 | 72.727 | 45.454 | core_trend_flag_bool == False<br>feature_quality == incomplete<br>priority_rank <= 1 |
| 53 | KOSPI | top5_exception | 5d | 3 | 23 | 6 | 52.174 | 2.3942 | -25.5403 | 38.4365 | 60.87 | 39.13 | alpha_score <= 66<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 25.5 |
| 54 | KOSPI | top5_exception | 5d | 1 | 37 | 8 | 51.351 | 2.1174 | -19.2714 | 39.4197 | 72.973 | 43.243 | decision_score >= 105 |
| 55 | KOSPI | top5_exception | 3d | 2 | 37 | 10 | 51.351 | 1.6449 | -18.3014 | 21.2195 | 70.27 | 37.838 | decision_score >= 105<br>prob_clean <= 32.325 |
| 56 | KOSPI | top5_exception | 3d | 1 | 43 | 10 | 51.163 | 1.066 | -18.3014 | 21.2195 | 74.419 | 44.186 | decision_score >= 105 |
| 57 | KOSPI | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 8.0835 | -6.5708 | 28.4932 | 50.0 | 16.667 | alpha_score <= 66<br>decision_score >= 100<br>prob_clean <= 29.6 |
| 58 | KOSPI | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 8.0835 | -6.5708 | 28.4932 | 50.0 | 16.667 | alpha_score <= 66<br>decision_score >= 99.55<br>prob_clean <= 29.6 |
| 59 | KOSPI | top5_exception | 5d | 2 | 14 | 7 | 50.0 | 5.0773 | -11.588 | 28.4932 | 64.286 | 35.714 | alpha_score <= 70.5<br>decision_score >= 100 |
| 60 | KOSPI | top5_exception | 5d | 2 | 14 | 7 | 50.0 | 5.0773 | -11.588 | 28.4932 | 64.286 | 35.714 | alpha_score <= 70.5<br>decision_score >= 99.55 |
| 61 | KOSPI | top5_exception | 5d | 2 | 22 | 6 | 50.0 | 3.6496 | -19.2714 | 39.4197 | 63.636 | 40.909 | decision_score >= 105<br>decision == EXCEPTION_LEADER |
| 62 | KOSPI | top5_exception | 5d | 2 | 22 | 6 | 50.0 | 3.6496 | -19.2714 | 39.4197 | 63.636 | 40.909 | decision_bucket == exception_leader<br>decision_score >= 105 |
| 63 | KOSPI | top5_exception | 5d | 2 | 22 | 6 | 50.0 | 3.6496 | -19.2714 | 39.4197 | 63.636 | 40.909 | decision_score >= 105<br>exception_leader == True |
| 64 | KOSPI | top5_exception | 3d | 3 | 38 | 8 | 50.0 | 3.5438 | -26.947 | 29.9674 | 57.895 | 34.21 | decision == EXCEPTION_LEADER<br>ml_prob <= 42.2<br>prob_clean <= 25.5 |
| 65 | KOSPI | top5_exception | 3d | 3 | 38 | 8 | 50.0 | 3.5438 | -26.947 | 29.9674 | 57.895 | 34.21 | decision_bucket == exception_leader<br>ml_prob <= 42.2<br>prob_clean <= 25.5 |
| 66 | KOSPI | top5_exception | 3d | 3 | 38 | 8 | 50.0 | 3.5438 | -26.947 | 29.9674 | 57.895 | 34.21 | exception_leader == True<br>ml_prob <= 42.2<br>prob_clean <= 25.5 |
| 67 | KOSPI | top5_exception | 5d | 2 | 10 | 6 | 50.0 | 3.0528 | -15.493 | 28.4932 | 60.0 | 40.0 | decision == EXCEPTION_LEADER<br>ml_prob <= 32.7 |
| 68 | KOSPI | top5_exception | 5d | 2 | 10 | 6 | 50.0 | 3.0528 | -15.493 | 28.4932 | 60.0 | 40.0 | decision_bucket == exception_leader<br>ml_prob <= 32.7 |
| 69 | KOSPI | top5_exception | 5d | 2 | 10 | 6 | 50.0 | 3.0528 | -15.493 | 28.4932 | 60.0 | 40.0 | exception_leader == True<br>ml_prob <= 32.7 |
| 70 | KOSDAQ | top5_exception | 3d | 2 | 28 | 14 | 50.0 | 2.6456 | -20.9302 | 57.2505 | 89.286 | 50.0 | alpha_score <= 65<br>prob_clean <= 24.975 |
| 71 | KOSPI | top5_exception | 5d | 1 | 4 | 2 | 50.0 | 2.4822 | -5.1656 | 11.7886 | 75.0 | 25.0 | expected_return_3d_pct >= 0.83 |
| 72 | KOSPI | top5_exception | 5d | 1 | 4 | 2 | 50.0 | 2.4822 | -5.1656 | 11.7886 | 75.0 | 25.0 | expected_edge_score >= 6.4355 |
| 73 | KOSPI | top5_exception | 5d | 1 | 4 | 2 | 50.0 | 2.4822 | -5.1656 | 11.7886 | 75.0 | 25.0 | expected_return_1d_pct >= 0.45 |
| 74 | KOSPI | top5_exception | 5d | 1 | 4 | 3 | 50.0 | 2.1362 | -10.6395 | 11.1111 | 50.0 | 25.0 | trend == NEUTRAL |
| 75 | KOSPI | top5_exception | 3d | 1 | 4 | 2 | 50.0 | 0.2672 | -5.1795 | 5.8266 | 75.0 | 25.0 | expected_return_3d_pct >= 0.83 |
| 76 | KOSPI | top5_exception | 3d | 1 | 4 | 2 | 50.0 | 0.2672 | -5.1795 | 5.8266 | 75.0 | 25.0 | expected_edge_score >= 6.4355 |
| 77 | KOSPI | top5_exception | 3d | 1 | 4 | 2 | 50.0 | 0.2672 | -5.1795 | 5.8266 | 75.0 | 25.0 | expected_return_1d_pct >= 0.45 |
| 78 | KOSDAQ | top5_exception | 3d | 1 | 6 | 4 | 50.0 | -0.272 | -8.0429 | 12.0863 | 83.333 | 0.0 | expected_return_1d_pct >= 0.604 |
| 79 | KOSDAQ | top5_exception | 3d | 2 | 6 | 4 | 50.0 | -0.272 | -8.0429 | 12.0863 | 83.333 | 0.0 | alpha_score <= 84<br>expected_return_1d_pct >= 0.604 |
| 80 | KOSDAQ | top5_exception | 3d | 2 | 6 | 4 | 50.0 | -0.272 | -8.0429 | 12.0863 | 83.333 | 0.0 | alpha_score <= 92<br>expected_return_1d_pct >= 0.604 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 92, 'categorical': 51, 'total': 143}`
- predicates: `{'raw': 1399, 'unique': 1399, 'numeric': 1265, 'after_support_screen': 1246, 'categorical': 134, 'duplicates': 0}`
- predicate support screen: `{'kept': 1246, 'rejected_train_support': 91, 'rejected_test_support': 87}`
- result counts: `{'mined_combinations': 576, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_bad_path': 287, 'test_win': 276, 'test_stop5': 251, 'test_avg': 156, 'train_bad_path': 138, 'train_win': 80, 'train_stop5': 38, 'test_days': 5, 'test_n': 4, 'train_avg': 2}`
- `5d`: `{'test_bad_path': 287, 'test_win': 286, 'test_avg': 222, 'test_stop5': 208, 'train_bad_path': 143, 'train_win': 75, 'train_stop5': 39, 'test_n': 7, 'test_days': 7, 'train_avg': 1}`

### Beam Pruning
- `3d`: `{'attempted': 18432, 'rejected_test_n': 6857, 'rejected_train_n': 6745, 'expanded_survivors': 6110, 'pruned_by_beam': 5918, 'skipped_feature_conflict': 1874, 'skipped_duplicate': 1423, 'base_pool': 384, 'rejected_test_days': 276, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192, 'rejected_train_days': 25}`
- `5d`: `{'attempted': 18432, 'rejected_test_n': 7721, 'rejected_train_n': 6651, 'expanded_survivors': 5888, 'pruned_by_beam': 5696, 'skipped_feature_conflict': 1898, 'skipped_duplicate': 1343, 'rejected_test_days': 402, 'base_pool': 384, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192, 'rejected_train_days': 20}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=735 days=58 predicates=643 results=288 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=679 days=54 predicates=603 results=288 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
