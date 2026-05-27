# Significant Feature Combination Mining

- generated_at: `2026-05-27T11:54:26.837043+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4220`
- quality_scope: `exact_path`
- mined_combinations: `768`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | top5_exception | 3d | 2 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome |
| 2 | KOSPI | top5_exception | 3d | 3 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 37.045 |
| 3 | KOSPI | top5_exception | 3d | 3 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 34.5 |
| 4 | KOSPI | top5_exception | 3d | 2 | 12 | 5 | 75.0 | 1.546 | -22.0867 | 15.1825 | 75.0 | 50.0 | decision_score >= 113<br>prob_clean >= 22.51 |
| 5 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 6 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 7 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 8 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False |
| 9 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND |
| 10 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113 |
| 11 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 34.5 |
| 12 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 34.5 |
| 13 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 34.5 |
| 14 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 37.045 |
| 15 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 37.045 |
| 16 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 37.045 |
| 17 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>priority_rank <= 10 |
| 18 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>priority_rank <= 10 |
| 19 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>priority_rank <= 10 |
| 20 | KOSPI | top5_exception | 3d | 3 | 9 | 5 | 66.667 | 4.186 | -7.4334 | 15.1825 | 77.778 | 66.667 | decision_score >= 113<br>ml_prob <= 36.7<br>prob_clean <= 37.045 |
| 21 | KOSPI | top5_exception | 3d | 3 | 9 | 5 | 66.667 | 4.186 | -7.4334 | 15.1825 | 77.778 | 66.667 | decision_score >= 113<br>ml_prob <= 36.7<br>prob_clean <= 34.5 |
| 22 | KOSPI | top5_exception | 3d | 2 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8 |
| 23 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 24 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 25 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 26 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8<br>trend == UP |
| 27 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score >= 67<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 28 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 32.8 |
| 29 | KOSPI | top5_exception | 3d | 1 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113 |
| 30 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5 |
| 31 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045 |
| 32 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10 |
| 33 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4 |
| 34 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5 |
| 35 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445 |
| 36 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 37 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 38 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 34.5 |
| 39 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 20.275<br>prob_clean <= 37.045 |
| 40 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 37.045 |
| 41 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 20.275<br>prob_clean <= 34.5 |
| 42 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 34.5 |
| 43 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 34.5 |
| 44 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 34.5 |
| 45 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5<br>trend == UP |
| 46 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 37.045 |
| 47 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 37.045 |
| 48 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 37.045 |
| 49 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045<br>trend == UP |
| 50 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score >= 67<br>decision_score >= 113<br>prob_clean <= 34.5 |
| 51 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score >= 67<br>decision_score >= 113<br>prob_clean <= 37.045 |
| 52 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 0.5378 | -22.0867 | 10.2167 | 75.0 | 58.333 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>theme_inference_status == inferred |
| 53 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 0.5378 | -22.0867 | 10.2167 | 75.0 | 58.333 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>theme_inference_status == inferred |
| 54 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 0.5378 | -22.0867 | 10.2167 | 75.0 | 58.333 | core_trend_flag_bool == True<br>decision_score >= 113<br>theme_inference_status == inferred |
| 55 | KOSPI | top5_exception | 3d | 2 | 14 | 5 | 64.286 | 0.832 | -22.0867 | 10.2167 | 78.571 | 57.143 | decision_score >= 113<br>theme_inference_status == inferred |
| 56 | KOSPI | top5_exception | 3d | 1 | 10 | 6 | 60.0 | 3.7308 | -3.6133 | 17.2005 | 70.0 | 40.0 | ml_prob <= 27.655 |
| 57 | KOSPI | top5_exception | 3d | 2 | 10 | 5 | 60.0 | 2.1061 | -7.4334 | 10.2167 | 70.0 | 70.0 | decision_score >= 113<br>prob_clean <= 29.7 |
| 58 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 54.546 | 0.4321 | -9.901 | 14.3535 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 59 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 54.546 | 0.4321 | -9.901 | 14.3535 | 72.727 | 63.636 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 60 | KOSPI | top5_exception | 5d | 3 | 11 | 5 | 54.546 | 0.4321 | -9.901 | 14.3535 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 61 | KOSPI | top5_exception | 5d | 2 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False |
| 62 | KOSPI | top5_exception | 5d | 2 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND |
| 63 | KOSPI | top5_exception | 5d | 2 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113 |
| 64 | KOSPI | top5_exception | 5d | 3 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>priority_rank <= 10 |
| 65 | KOSPI | top5_exception | 5d | 3 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>priority_rank <= 10 |
| 66 | KOSPI | top5_exception | 5d | 3 | 13 | 5 | 53.846 | -0.1034 | -13.1436 | 14.3535 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>priority_rank <= 10 |
| 67 | KOSPI | top5_exception | 5d | 1 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113 |
| 68 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10 |
| 69 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5 |
| 70 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045 |
| 71 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445 |
| 72 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4 |
| 73 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5 |
| 74 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 75 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 76 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 34.5 |
| 77 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 20.275<br>prob_clean <= 34.5 |
| 78 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | alpha_score <= 100<br>decision_score >= 113<br>priority_rank <= 10 |
| 79 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>trend == UP |
| 80 | KOSPI | top5_exception | 5d | 2 | 10 | 5 | 50.0 | 0.0734 | -9.901 | 14.3535 | 70.0 | 70.0 | decision_score >= 113<br>prob_clean <= 29.7 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 68, 'categorical': 50, 'total': 118}`
- predicates: `{'raw': 479, 'unique': 479, 'numeric': 395, 'after_support_screen': 376, 'categorical': 84, 'duplicates': 0}`
- predicate support screen: `{'kept': 376, 'rejected_train_support': 58, 'rejected_test_support': 54}`
- result counts: `{'mined_combinations': 768, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_bad_path': 384, 'test_stop5': 383, 'test_win': 377, 'test_avg': 312, 'train_bad_path': 80, 'train_stop5': 18, 'train_win': 13, 'test_days': 4, 'test_n': 3}`
- `5d`: `{'test_win': 384, 'test_bad_path': 384, 'test_stop5': 381, 'test_avg': 357, 'train_bad_path': 76, 'train_stop5': 12, 'test_days': 8, 'test_n': 6}`

### Beam Pruning
- `3d`: `{'attempted': 32768, 'rejected_train_n': 13911, 'expanded_survivors': 10930, 'pruned_by_beam': 10674, 'rejected_test_n': 7555, 'skipped_feature_conflict': 3213, 'skipped_duplicate': 2520, 'base_pool': 512, 'rejected_test_days': 478, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256, 'rejected_train_days': 78}`
- `5d`: `{'attempted': 32768, 'rejected_train_n': 14608, 'expanded_survivors': 9810, 'pruned_by_beam': 9554, 'rejected_test_n': 8064, 'skipped_feature_conflict': 3290, 'skipped_duplicate': 2690, 'base_pool': 512, 'rejected_test_days': 457, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256, 'rejected_train_days': 29}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=508 days=39 predicates=165 results=384 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=530 days=39 predicates=211 results=384 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
