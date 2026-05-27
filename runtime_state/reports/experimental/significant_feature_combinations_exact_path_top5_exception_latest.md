# Significant Feature Combination Mining

- generated_at: `2026-05-27T11:52:02.195161+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4220`
- quality_scope: `exact_path`
- mined_combinations: `576`
- production_safe_count: `1`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | top5_exception | 5d | 2 | 5 | 4 | 80.0 | 7.9019 | -3.2595 | 17.5781 | 20.0 | 0.0 | alpha_score <= 67<br>ml_prob <= 30.45 |
| 2 | KOSPI | top5_exception | 3d | 1 | 4 | 2 | 100.0 | 6.9372 | 1.9462 | 10.2167 | 100.0 | 50.0 | ml_prob <= 23.85 |
| 3 | KOSPI | top5_exception | 3d | 3 | 9 | 4 | 77.778 | 4.0346 | -3.512 | 15.1825 | 66.667 | 55.556 | alpha_score <= 99<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 4 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 75.0 | 1.546 | -22.0867 | 15.1825 | 75.0 | 50.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean >= 22.51 |
| 5 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 75.0 | 1.546 | -22.0867 | 15.1825 | 75.0 | 50.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean >= 22.51 |
| 6 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 7 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 8 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 9 | KOSPI | top5_exception | 3d | 3 | 10 | 4 | 70.0 | 0.6729 | -22.0867 | 15.1825 | 80.0 | 50.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean >= 25.525 |
| 10 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False |
| 11 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND |
| 12 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113 |
| 13 | KOSPI | top5_exception | 3d | 2 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8 |
| 14 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 32.8 |
| 15 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 32.8 |
| 16 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 17 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 18 | KOSPI | top5_exception | 3d | 1 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113 |
| 19 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5 |
| 20 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045 |
| 21 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7 |
| 22 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10 |
| 23 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4 |
| 24 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5 |
| 25 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 34.5 |
| 26 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 27 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>priority_rank <= 7 |
| 28 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>priority_rank <= 7 |
| 29 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 37.045 |
| 30 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 34.5 |
| 31 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>priority_rank <= 10 |
| 32 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>priority_rank <= 10 |
| 33 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 34 | KOSPI | top5_exception | 3d | 3 | 14 | 5 | 64.286 | 1.1867 | -22.0867 | 15.1825 | 78.571 | 57.143 | decision_score >= 113<br>ml_prob >= 23.85<br>prob_clean <= 37.045 |
| 35 | KOSPI | top5_exception | 3d | 2 | 14 | 5 | 64.286 | 0.832 | -22.0867 | 10.2167 | 78.571 | 57.143 | decision_score >= 113<br>theme_inference_status == inferred |
| 36 | KOSPI | top5_exception | 3d | 3 | 14 | 5 | 64.286 | 0.832 | -22.0867 | 10.2167 | 78.571 | 57.143 | decision_score >= 113<br>prob_clean <= 37.045<br>theme_inference_status == inferred |
| 37 | KOSPI | top5_exception | 3d | 3 | 14 | 5 | 64.286 | 0.832 | -22.0867 | 10.2167 | 78.571 | 57.143 | decision_score >= 113<br>prob_clean <= 34.5<br>theme_inference_status == inferred |
| 38 | KOSPI | top5_exception | 3d | 1 | 10 | 6 | 60.0 | 3.7308 | -3.6133 | 17.2005 | 70.0 | 40.0 | ml_prob <= 27.655 |
| 39 | KOSPI | top5_exception | 3d | 3 | 10 | 4 | 60.0 | 2.822 | -7.4334 | 15.1825 | 80.0 | 70.0 | alpha_score >= 78<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 40 | KOSPI | top5_exception | 5d | 1 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113 |
| 41 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7 |
| 42 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10 |
| 43 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5 |
| 44 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045 |
| 45 | KOSPI | top5_exception | 5d | 2 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445 |
| 46 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 34.5 |
| 47 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 34.5 |
| 48 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 37.045 |
| 49 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>priority_rank <= 7 |
| 50 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>priority_rank <= 7 |
| 51 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 52 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 53 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 34.5 |
| 54 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>priority_rank <= 10 |
| 55 | KOSPI | top5_exception | 5d | 3 | 15 | 5 | 53.333 | 0.5513 | -13.1436 | 16.821 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>priority_rank <= 10 |
| 56 | KOSPI | top5_exception | 5d | 3 | 10 | 4 | 50.0 | 0.7648 | -13.1436 | 16.821 | 80.0 | 50.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean >= 25.525 |
| 57 | KOSPI | top5_exception | 5d | 2 | 14 | 5 | 50.0 | 0.4027 | -13.1436 | 16.821 | 78.571 | 57.143 | decision_score >= 113<br>ml_prob >= 23.85 |
| 58 | KOSPI | top5_exception | 5d | 3 | 14 | 5 | 50.0 | 0.4027 | -13.1436 | 16.821 | 78.571 | 57.143 | decision_score >= 113<br>ml_prob >= 23.85<br>prob_clean <= 37.045 |
| 59 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 50.0 | -0.1257 | -13.1436 | 16.821 | 75.0 | 50.0 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean >= 22.51 |
| 60 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 50.0 | -0.1257 | -13.1436 | 16.821 | 75.0 | 50.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean >= 22.51 |
| 61 | KOSPI | top5_exception | 5d | 2 | 12 | 5 | 50.0 | -0.2045 | -9.901 | 14.3535 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8 |
| 62 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 50.0 | -0.2045 | -9.901 | 14.3535 | 75.0 | 66.667 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 32.8 |
| 63 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 50.0 | -0.2045 | -9.901 | 14.3535 | 75.0 | 66.667 | decision_score >= 113<br>priority_rank <= 7<br>prob_clean <= 32.8 |
| 64 | KOSPI | top5_exception | 5d | 3 | 12 | 5 | 50.0 | -0.2045 | -9.901 | 14.3535 | 75.0 | 66.667 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 32.8 |
| 65 | KOSDAQ | top5_exception | 5d | 1 | 4 | 3 | 50.0 | -0.5231 | -13.8914 | 13.3901 | 75.0 | 75.0 | alpha_score <= 36.5 |
| 66 | KOSPI | top5_exception | 3d | 1 | 48 | 9 | 47.917 | 0.5343 | -20.6854 | 33.4586 | 77.083 | 45.833 | conviction_score <= 65.06 |
| 67 | KOSPI | top5_exception | 5d | 3 | 11 | 7 | 45.454 | 2.3707 | -20.1285 | 54.4834 | 63.636 | 36.364 | alpha_score <= 67<br>decision_score <= 95.525<br>ml_prob <= 36.7 |
| 68 | KOSPI | top5_exception | 3d | 1 | 29 | 8 | 44.828 | -0.4119 | -22.0867 | 17.2005 | 86.207 | 72.414 | feature_origin == scanner_archive_outcome |
| 69 | KOSPI | top5_exception | 3d | 3 | 9 | 6 | 44.444 | -2.3288 | -16.3543 | 13.67 | 66.667 | 22.222 | alpha_score >= 83<br>ml_prob >= 36.7<br>prob_clean >= 37.045 |
| 70 | KOSDAQ | top5_exception | 3d | 2 | 18 | 7 | 44.444 | -3.5217 | -30.1013 | 10.745 | 66.667 | 38.889 | alpha_score <= 70<br>phase25_prob <= 50 |
| 71 | KOSPI | top5_exception | 5d | 2 | 14 | 7 | 42.857 | 1.5969 | -20.1285 | 54.4834 | 64.286 | 42.857 | alpha_score <= 67<br>ml_prob <= 36.7 |
| 72 | KOSPI | top5_exception | 3d | 1 | 17 | 8 | 41.176 | 0.0985 | -16.3543 | 28.1513 | 58.823 | 29.412 | expected_return_3d_pct >= 0.76 |
| 73 | KOSPI | top5_exception | 3d | 2 | 17 | 8 | 41.176 | 0.0985 | -16.3543 | 28.1513 | 58.823 | 29.412 | alpha_score <= 99<br>expected_return_3d_pct >= 0.76 |
| 74 | KOSPI | top5_exception | 3d | 2 | 17 | 8 | 41.176 | 0.0985 | -16.3543 | 28.1513 | 58.823 | 29.412 | expected_return_3d_pct >= 0.76<br>ml_prob >= 23.85 |
| 75 | KOSPI | top5_exception | 3d | 2 | 17 | 8 | 41.176 | 0.0985 | -16.3543 | 28.1513 | 58.823 | 29.412 | expected_return_3d_pct >= 0.76<br>ml_prob >= 21.445 |
| 76 | KOSPI | top5_exception | 3d | 1 | 57 | 10 | 40.351 | -0.8021 | -22.0867 | 28.1513 | 80.702 | 54.386 | decision_score >= 95.525 |
| 77 | KOSPI | top5_exception | 5d | 1 | 10 | 6 | 40.0 | -1.2245 | -11.615 | 17.5781 | 70.0 | 40.0 | ml_prob <= 27.655 |
| 78 | KOSPI | top5_exception | 3d | 1 | 5 | 1 | 40.0 | -2.7384 | -7.8947 | 4.7872 | 100.0 | 100.0 | decision == EXCEPTION_LEADER |
| 79 | KOSPI | top5_exception | 3d | 1 | 5 | 1 | 40.0 | -2.7384 | -7.8947 | 4.7872 | 100.0 | 100.0 | decision_bucket == exception_leader |
| 80 | KOSPI | top5_exception | 3d | 1 | 5 | 1 | 40.0 | -2.7384 | -7.8947 | 4.7872 | 100.0 | 100.0 | exception_leader == True |

## Production Safe Candidates

- `KOSPI` `top5_exception` `5d` win=80.0 avg=7.9019 bad=20.0 stop=0.0 :: alpha_score <= 67 / ml_prob <= 30.45

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 68, 'categorical': 50, 'total': 118}`
- predicates: `{'raw': 501, 'unique': 501, 'numeric': 413, 'after_support_screen': 403, 'categorical': 88, 'duplicates': 0}`
- predicate support screen: `{'kept': 403, 'rejected_train_support': 55, 'rejected_test_support': 50}`
- result counts: `{'mined_combinations': 576, 'production_safe': 1}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_bad_path': 288, 'test_stop5': 286, 'test_win': 280, 'test_avg': 243, 'train_bad_path': 52, 'train_stop5': 10, 'test_days': 8, 'train_win': 4, 'test_n': 3}`
- `5d`: `{'test_win': 287, 'test_bad_path': 287, 'test_stop5': 284, 'test_avg': 260, 'train_bad_path': 50, 'train_stop5': 9, 'test_days': 7, 'test_n': 2}`

### Beam Pruning
- `3d`: `{'attempted': 18432, 'rejected_train_n': 7150, 'expanded_survivors': 6064, 'pruned_by_beam': 5872, 'rejected_test_n': 4426, 'skipped_feature_conflict': 2189, 'skipped_duplicate': 1271, 'rejected_test_days': 425, 'base_pool': 384, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192, 'rejected_train_days': 69}`
- `5d`: `{'attempted': 18432, 'rejected_train_n': 7425, 'expanded_survivors': 5794, 'pruned_by_beam': 5602, 'rejected_test_n': 4117, 'skipped_feature_conflict': 2220, 'skipped_duplicate': 1375, 'rejected_test_days': 425, 'base_pool': 384, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192, 'rejected_train_days': 48}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=508 days=39 predicates=171 results=288 safe=1 skip=-
- `KOSDAQ` `top5_exception` rows=530 days=39 predicates=232 results=288 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
