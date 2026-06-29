# Significant Feature Combination Mining

- generated_at: `2026-06-29T07:07:05.628399+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4882`
- quality_scope: `exact_path`
- mined_combinations: `768`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 75.0 | 6.4408 | -8.347 | 28.4932 | 58.333 | 33.333 | alpha_score <= 74<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 3 |
| 2 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 72.727 | 6.6581 | -25.5403 | 28.4932 | 54.546 | 18.182 | alpha_score <= 70.5<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 4 |
| 3 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 72.727 | 6.1676 | -25.5403 | 28.4932 | 45.454 | 18.182 | alpha_score <= 66<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 5 |
| 4 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 72.727 | 6.1676 | -25.5403 | 28.4932 | 45.454 | 18.182 | alpha_score <= 66<br>feature_quality == incomplete<br>priority_rank <= 5 |
| 5 | KOSPI | top5_exception | 5d | 3 | 17 | 6 | 70.588 | 5.5352 | -25.5403 | 28.4932 | 58.823 | 29.412 | alpha_score <= 74<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 4 |
| 6 | KOSPI | top5_exception | 5d | 3 | 10 | 5 | 70.0 | 2.2007 | -25.5403 | 24.2188 | 50.0 | 20.0 | alpha_score <= 70.5<br>decision_bucket == watchlist<br>feature_origin == scanner_archive_outcome |
| 7 | KOSPI | top5_exception | 5d | 3 | 10 | 5 | 70.0 | 2.2007 | -25.5403 | 24.2188 | 50.0 | 20.0 | alpha_score <= 70.5<br>exception_leader == False<br>feature_origin == scanner_archive_outcome |
| 8 | KOSPI | top5_exception | 5d | 3 | 10 | 5 | 70.0 | 2.2007 | -25.5403 | 24.2188 | 50.0 | 20.0 | alpha_score <= 70.5<br>decision_bucket == watchlist<br>feature_quality == incomplete |
| 9 | KOSPI | top5_exception | 5d | 3 | 10 | 5 | 70.0 | 2.2007 | -25.5403 | 24.2188 | 50.0 | 20.0 | alpha_score <= 70.5<br>exception_leader == False<br>feature_quality == incomplete |
| 10 | KOSPI | top5_exception | 3d | 3 | 23 | 8 | 69.565 | 5.5451 | -13.0798 | 21.2195 | 60.87 | 30.435 | decision_score >= 105<br>decision == EXCEPTION_LEADER<br>prob_clean <= 32.325 |
| 11 | KOSPI | top5_exception | 3d | 3 | 23 | 8 | 69.565 | 5.5451 | -13.0798 | 21.2195 | 60.87 | 30.435 | decision_bucket == exception_leader<br>decision_score >= 105<br>prob_clean <= 32.325 |
| 12 | KOSPI | top5_exception | 3d | 3 | 23 | 8 | 69.565 | 5.5451 | -13.0798 | 21.2195 | 60.87 | 30.435 | decision_score >= 105<br>exception_leader == True<br>prob_clean <= 32.325 |
| 13 | KOSPI | top5_exception | 5d | 3 | 23 | 6 | 69.565 | 5.0172 | -25.5403 | 28.4932 | 52.174 | 26.087 | alpha_score <= 74<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 5 |
| 14 | KOSPI | top5_exception | 5d | 3 | 16 | 5 | 68.75 | 5.6139 | -25.5403 | 28.4932 | 50.0 | 18.75 | alpha_score <= 70.5<br>feature_origin == scanner_archive_outcome<br>priority_rank <= 5 |
| 15 | KOSPI | top5_exception | 3d | 3 | 25 | 8 | 68.0 | 4.7985 | -13.0798 | 21.2195 | 64.0 | 36.0 | decision_score >= 105<br>decision == EXCEPTION_LEADER<br>prob_clean <= 34.6 |
| 16 | KOSPI | top5_exception | 3d | 3 | 25 | 8 | 68.0 | 4.7985 | -13.0798 | 21.2195 | 64.0 | 36.0 | decision_bucket == exception_leader<br>decision_score >= 105<br>prob_clean <= 34.6 |
| 17 | KOSPI | top5_exception | 3d | 3 | 25 | 8 | 68.0 | 4.7985 | -13.0798 | 21.2195 | 64.0 | 36.0 | decision_score >= 105<br>exception_leader == True<br>prob_clean <= 34.6 |
| 18 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_score >= 99.55<br>decision == EXCEPTION_LEADER<br>prob_clean <= 32.325 |
| 19 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_score >= 100<br>decision == EXCEPTION_LEADER<br>prob_clean <= 32.325 |
| 20 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_bucket == exception_leader<br>decision_score >= 99.55<br>prob_clean <= 32.325 |
| 21 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_bucket == exception_leader<br>decision_score >= 100<br>prob_clean <= 32.325 |
| 22 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_score >= 99.55<br>exception_leader == True<br>prob_clean <= 32.325 |
| 23 | KOSPI | top5_exception | 3d | 3 | 24 | 8 | 66.667 | 5.3096 | -13.0798 | 21.2195 | 62.5 | 29.167 | decision_score >= 100<br>exception_leader == True<br>prob_clean <= 32.325 |
| 24 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_score >= 99.55<br>decision == EXCEPTION_LEADER |
| 25 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_score >= 100<br>decision == EXCEPTION_LEADER |
| 26 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_bucket == exception_leader<br>decision_score >= 99.55 |
| 27 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_bucket == exception_leader<br>decision_score >= 100 |
| 28 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_score >= 99.55<br>exception_leader == True |
| 29 | KOSPI | top5_exception | 3d | 3 | 21 | 8 | 66.667 | 4.9284 | -7.1097 | 21.2195 | 61.905 | 28.571 | alpha_score <= 83<br>decision_score >= 100<br>exception_leader == True |
| 30 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_score >= 105<br>decision == EXCEPTION_LEADER |
| 31 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_bucket == exception_leader<br>decision_score >= 105 |
| 32 | KOSPI | top5_exception | 3d | 2 | 27 | 8 | 66.667 | 4.3874 | -13.0798 | 21.2195 | 66.667 | 40.741 | decision_score >= 105<br>exception_leader == True |
| 33 | KOSPI | top5_exception | 5d | 3 | 15 | 6 | 66.667 | 2.7381 | -25.5403 | 24.2188 | 60.0 | 33.333 | alpha_score <= 74<br>decision_bucket == watchlist<br>feature_origin == scanner_archive_outcome |
| 34 | KOSPI | top5_exception | 5d | 3 | 15 | 6 | 66.667 | 2.7381 | -25.5403 | 24.2188 | 60.0 | 33.333 | alpha_score <= 74<br>exception_leader == False<br>feature_origin == scanner_archive_outcome |
| 35 | KOSPI | top5_exception | 5d | 3 | 15 | 6 | 66.667 | 2.7381 | -25.5403 | 24.2188 | 60.0 | 33.333 | alpha_score <= 74<br>decision_bucket == watchlist<br>feature_quality == incomplete |
| 36 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_score >= 99.55<br>decision == EXCEPTION_LEADER<br>prob_clean <= 34.6 |
| 37 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_score >= 100<br>decision == EXCEPTION_LEADER<br>prob_clean <= 34.6 |
| 38 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_bucket == exception_leader<br>decision_score >= 99.55<br>prob_clean <= 34.6 |
| 39 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_bucket == exception_leader<br>decision_score >= 100<br>prob_clean <= 34.6 |
| 40 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_score >= 99.55<br>exception_leader == True<br>prob_clean <= 34.6 |
| 41 | KOSPI | top5_exception | 3d | 3 | 26 | 8 | 65.385 | 4.6098 | -13.0798 | 21.2195 | 65.385 | 34.615 | decision_score >= 100<br>exception_leader == True<br>prob_clean <= 34.6 |
| 42 | KOSPI | top5_exception | 3d | 2 | 26 | 8 | 65.385 | 3.6226 | -13.0798 | 21.2195 | 73.077 | 42.308 | decision_score >= 105<br>priority_rank >= 5 |
| 43 | KOSPI | top5_exception | 3d | 3 | 20 | 8 | 65.0 | 4.6296 | -5.8132 | 21.2195 | 60.0 | 30.0 | alpha_score <= 74<br>decision_score >= 99.55<br>feature_origin == scanner_archive_outcome |
| 44 | KOSPI | top5_exception | 3d | 3 | 20 | 8 | 65.0 | 4.6296 | -5.8132 | 21.2195 | 60.0 | 30.0 | alpha_score <= 74<br>decision_score >= 100<br>feature_origin == scanner_archive_outcome |
| 45 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 99.55<br>decision == EXCEPTION_LEADER |
| 46 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 100<br>decision == EXCEPTION_LEADER |
| 47 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_bucket == exception_leader<br>decision_score >= 99.55 |
| 48 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_bucket == exception_leader<br>decision_score >= 100 |
| 49 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 99.55<br>exception_leader == True |
| 50 | KOSPI | top5_exception | 3d | 2 | 28 | 8 | 64.286 | 4.2269 | -13.0798 | 21.2195 | 67.857 | 39.286 | decision_score >= 100<br>exception_leader == True |
| 51 | KOSPI | top5_exception | 3d | 2 | 22 | 9 | 63.636 | 4.3991 | -7.1097 | 21.2195 | 59.091 | 36.364 | alpha_score <= 74<br>decision_score >= 105 |
| 52 | KOSDAQ | top5_exception | 3d | 2 | 11 | 7 | 63.636 | 1.7127 | -15.0606 | 20.6642 | 90.909 | 45.454 | alpha_score <= 53<br>prob_clean <= 24.975 |
| 53 | KOSPI | top5_exception | 5d | 3 | 16 | 6 | 62.5 | 5.2277 | -11.588 | 28.4932 | 56.25 | 25.0 | alpha_score <= 74<br>decision_score >= 100<br>feature_origin == scanner_archive_outcome |
| 54 | KOSPI | top5_exception | 5d | 3 | 16 | 6 | 62.5 | 5.2277 | -11.588 | 28.4932 | 56.25 | 25.0 | alpha_score <= 74<br>decision_score >= 99.55<br>feature_origin == scanner_archive_outcome |
| 55 | KOSDAQ | top5_exception | 3d | 1 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35 |
| 56 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean >= 20.185 |
| 57 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 32.935 |
| 58 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 34.625 |
| 59 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 30.3 |
| 60 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>decision_score <= 98.05 |
| 61 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>prob_clean <= 36.815 |
| 62 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>decision_score >= 57 |
| 63 | KOSDAQ | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>explosive_leader_flag_bool == False |
| 64 | KOSDAQ | top5_exception | 3d | 3 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>decision_score <= 98.05<br>prob_clean >= 20.185 |
| 65 | KOSDAQ | top5_exception | 3d | 3 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>decision_score >= 57<br>prob_clean >= 20.185 |
| 66 | KOSDAQ | top5_exception | 3d | 3 | 8 | 7 | 62.5 | -0.1724 | -15.0606 | 20.6642 | 100.0 | 25.0 | alpha_score <= 42.35<br>explosive_leader_flag_bool == False<br>prob_clean >= 20.185 |
| 67 | KOSPI | top5_exception | 5d | 2 | 18 | 7 | 61.111 | 5.4264 | -11.588 | 28.4932 | 55.556 | 33.333 | alpha_score <= 74<br>decision_score >= 105 |
| 68 | KOSPI | top5_exception | 5d | 2 | 20 | 7 | 60.0 | 5.294 | -11.588 | 28.4932 | 55.0 | 30.0 | alpha_score <= 83<br>decision_score >= 105 |
| 69 | KOSPI | top5_exception | 3d | 2 | 25 | 9 | 60.0 | 4.0726 | -7.1097 | 21.2195 | 60.0 | 36.0 | alpha_score <= 83<br>decision_score >= 105 |
| 70 | KOSPI | top5_exception | 3d | 3 | 25 | 9 | 60.0 | 4.0726 | -7.1097 | 21.2195 | 60.0 | 36.0 | alpha_score <= 83<br>decision_score >= 105<br>prob_clean <= 34.6 |
| 71 | KOSPI | top5_exception | 3d | 3 | 24 | 9 | 58.333 | 4.1834 | -7.1097 | 21.2195 | 58.333 | 33.333 | alpha_score <= 83<br>decision_score >= 105<br>prob_clean <= 32.325 |
| 72 | KOSDAQ | top5_exception | 3d | 2 | 18 | 12 | 55.556 | 1.39 | -20.9302 | 46.0651 | 94.444 | 50.0 | alpha_score <= 58<br>prob_clean <= 24.975 |
| 73 | KOSDAQ | top5_exception | 3d | 3 | 9 | 6 | 55.556 | -1.6996 | -21.8301 | 12.0863 | 77.778 | 0.0 | alpha_score <= 84<br>expected_edge_score >= 4.91<br>ml_prob <= 50 |
| 74 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 54.546 | -0.3584 | -14.6497 | 9.6426 | 72.727 | 45.454 | core_trend_flag_bool == False<br>feature_quality == incomplete<br>priority_rank <= 1 |
| 75 | KOSDAQ | top5_exception | 3d | 3 | 11 | 6 | 54.546 | -1.8066 | -21.8301 | 12.0863 | 81.818 | 9.091 | alpha_score <= 84<br>decision_score >= 79.8<br>expected_edge_score >= 4.91 |
| 76 | KOSDAQ | top5_exception | 3d | 2 | 13 | 6 | 53.846 | -2.1385 | -21.8301 | 12.0863 | 84.615 | 15.385 | alpha_score <= 84<br>expected_edge_score >= 4.91 |
| 77 | KOSPI | top5_exception | 5d | 3 | 17 | 6 | 52.941 | 4.4336 | -11.588 | 28.4932 | 58.823 | 29.412 | alpha_score <= 96<br>decision_score >= 105<br>decision == EXCEPTION_LEADER |
| 78 | KOSPI | top5_exception | 5d | 3 | 17 | 6 | 52.941 | 4.4336 | -11.588 | 28.4932 | 58.823 | 29.412 | alpha_score <= 96<br>decision_bucket == exception_leader<br>decision_score >= 105 |
| 79 | KOSPI | top5_exception | 5d | 3 | 17 | 6 | 52.941 | 4.4336 | -11.588 | 28.4932 | 58.823 | 29.412 | alpha_score <= 96<br>decision_score >= 105<br>exception_leader == True |
| 80 | KOSPI | top5_exception | 3d | 2 | 17 | 9 | 52.941 | 3.0945 | -7.1097 | 18.0822 | 64.706 | 35.294 | alpha_score <= 70.5<br>decision_score >= 99.55 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 92, 'categorical': 51, 'total': 143}`
- predicates: `{'raw': 1369, 'unique': 1369, 'numeric': 1238, 'after_support_screen': 1149, 'categorical': 131, 'duplicates': 0}`
- predicate support screen: `{'kept': 1149, 'rejected_train_support': 137, 'rejected_test_support': 118}`
- result counts: `{'mined_combinations': 768, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_win': 384, 'test_bad_path': 384, 'test_stop5': 366, 'test_avg': 221, 'train_bad_path': 220, 'train_win': 131, 'train_stop5': 72, 'train_avg': 18, 'test_days': 3, 'test_n': 2}`
- `5d`: `{'test_bad_path': 384, 'test_win': 375, 'test_stop5': 359, 'test_avg': 300, 'train_bad_path': 236, 'train_win': 113, 'train_stop5': 68, 'test_days': 4, 'test_n': 2}`

### Beam Pruning
- `3d`: `{'attempted': 32768, 'expanded_survivors': 12095, 'pruned_by_beam': 11839, 'rejected_test_n': 11613, 'rejected_train_n': 10590, 'skipped_duplicate': 3275, 'skipped_feature_conflict': 3184, 'base_pool': 512, 'rejected_test_days': 293, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256, 'rejected_train_days': 9}`
- `5d`: `{'attempted': 32768, 'rejected_test_n': 12523, 'expanded_survivors': 11745, 'pruned_by_beam': 11489, 'rejected_train_n': 10499, 'skipped_feature_conflict': 3214, 'skipped_duplicate': 3118, 'rejected_test_days': 565, 'base_pool': 512, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=735 days=58 predicates=617 results=384 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=679 days=54 predicates=532 results=384 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
