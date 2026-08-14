# Significant Feature Combination Mining

- generated_at: `2026-08-14T00:55:55.016054+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `5066`
- quality_scope: `exact_path`
- mined_combinations: `768`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSDAQ | top5_exception | 3d | 1 | 9 | 7 | 66.667 | 5.5935 | -24.5039 | 42.1788 | 55.556 | 33.333 | prob_clean >= 36.66 |
| 2 | KOSDAQ | top5_exception | 3d | 1 | 14 | 9 | 64.286 | 2.1645 | -24.5039 | 42.1788 | 64.286 | 42.857 | prob_clean >= 34.35 |
| 3 | KOSDAQ | top5_exception | 3d | 2 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | prob_clean >= 30.1<br>trend == DOWN |
| 4 | KOSDAQ | top5_exception | 3d | 3 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | alpha_score <= 80<br>prob_clean >= 30.1<br>trend == DOWN |
| 5 | KOSDAQ | top5_exception | 3d | 3 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | alpha_score <= 88.8<br>prob_clean >= 30.1<br>trend == DOWN |
| 6 | KOSPI | top5_exception | 3d | 2 | 29 | 12 | 62.069 | -0.3095 | -20.5279 | 15.6028 | 58.621 | 44.828 | alpha_score <= 65<br>decision == WATCHLIST_ONLY |
| 7 | KOSDAQ | top5_exception | 3d | 2 | 11 | 7 | 54.546 | 4.0299 | -14.0944 | 42.1788 | 81.818 | 54.546 | prob_clean >= 27.13<br>trend == DOWN |
| 8 | KOSDAQ | top5_exception | 3d | 3 | 11 | 7 | 54.546 | 4.0299 | -14.0944 | 42.1788 | 81.818 | 54.546 | alpha_score <= 80<br>prob_clean >= 27.13<br>trend == DOWN |
| 9 | KOSDAQ | top5_exception | 3d | 3 | 11 | 7 | 54.546 | 4.0299 | -14.0944 | 42.1788 | 81.818 | 54.546 | alpha_score <= 88.8<br>prob_clean >= 27.13<br>trend == DOWN |
| 10 | KOSDAQ | top5_exception | 3d | 2 | 13 | 7 | 53.846 | -1.7168 | -20.5255 | 16.0494 | 76.923 | 61.538 | decision_score <= 76.4<br>market_gate == RED |
| 11 | KOSDAQ | top5_exception | 3d | 3 | 15 | 7 | 53.333 | 2.7947 | -14.0944 | 42.1788 | 73.333 | 46.667 | priority_rank <= 4<br>prob_clean >= 25.35<br>trend == DOWN |
| 12 | KOSPI | top5_exception | 5d | 1 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | prob_clean >= 33.85 |
| 13 | KOSPI | top5_exception | 5d | 2 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | feature_quality == incomplete<br>prob_clean >= 33.85 |
| 14 | KOSPI | top5_exception | 5d | 2 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | feature_completeness <= 0.8<br>prob_clean >= 33.85 |
| 15 | KOSPI | top5_exception | 5d | 2 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | feature_origin == scanner_archive_outcome<br>prob_clean >= 33.85 |
| 16 | KOSDAQ | top5_exception | 3d | 3 | 29 | 12 | 51.724 | 1.7827 | -27.5218 | 42.1788 | 68.966 | 48.276 | alpha_score <= 71<br>priority_rank <= 4<br>trend == DOWN |
| 17 | KOSDAQ | top5_exception | 5d | 1 | 14 | 9 | 50.0 | 5.6177 | -27.9907 | 54.6089 | 64.286 | 42.857 | prob_clean >= 34.35 |
| 18 | KOSDAQ | top5_exception | 3d | 2 | 8 | 6 | 50.0 | 4.9813 | -14.0944 | 42.1788 | 75.0 | 50.0 | trend == DOWN<br>volume_ratio <= 1.2 |
| 19 | KOSDAQ | top5_exception | 3d | 3 | 12 | 8 | 50.0 | 1.766 | -15.4506 | 16.0494 | 66.667 | 41.667 | decision_score <= 76.4<br>priority_rank <= 4<br>trend == DOWN |
| 20 | KOSDAQ | top5_exception | 3d | 2 | 16 | 8 | 50.0 | 1.3372 | -20.5255 | 42.1788 | 75.0 | 50.0 | prob_clean >= 25.35<br>trend == DOWN |
| 21 | KOSDAQ | top5_exception | 3d | 3 | 16 | 8 | 50.0 | 1.3372 | -20.5255 | 42.1788 | 75.0 | 50.0 | alpha_score <= 80<br>prob_clean >= 25.35<br>trend == DOWN |
| 22 | KOSDAQ | top5_exception | 3d | 3 | 16 | 8 | 50.0 | 1.3372 | -20.5255 | 42.1788 | 75.0 | 50.0 | alpha_score <= 71<br>prob_clean >= 25.35<br>trend == DOWN |
| 23 | KOSDAQ | top5_exception | 3d | 3 | 16 | 8 | 50.0 | 1.3372 | -20.5255 | 42.1788 | 75.0 | 50.0 | alpha_score <= 88.8<br>prob_clean >= 25.35<br>trend == DOWN |
| 24 | KOSDAQ | top5_exception | 3d | 3 | 24 | 11 | 50.0 | 1.3203 | -27.5218 | 42.1788 | 70.833 | 50.0 | alpha_score <= 71<br>priority_rank <= 3<br>trend == DOWN |
| 25 | KOSDAQ | top5_exception | 3d | 3 | 10 | 6 | 50.0 | 0.215 | -14.0944 | 17.6367 | 90.0 | 60.0 | ml_prob <= 50<br>prob_clean >= 27.13<br>trend == DOWN |
| 26 | KOSDAQ | top5_exception | 3d | 3 | 10 | 6 | 50.0 | 0.215 | -14.0944 | 17.6367 | 90.0 | 60.0 | ml_prob <= 41.21<br>prob_clean >= 27.13<br>trend == DOWN |
| 27 | KOSDAQ | top5_exception | 3d | 3 | 10 | 6 | 50.0 | 0.215 | -14.0944 | 17.6367 | 90.0 | 60.0 | ml_prob <= 44.9<br>prob_clean >= 27.13<br>trend == DOWN |
| 28 | KOSPI | top5_exception | 3d | 2 | 8 | 5 | 50.0 | -1.9369 | -15.9015 | 5.6075 | 100.0 | 62.5 | decision_score >= 108<br>ml_prob <= 35.7 |
| 29 | KOSDAQ | top5_exception | 3d | 1 | 18 | 10 | 50.0 | -2.3 | -26.6898 | 26.0417 | 77.778 | 61.111 | decision_score >= 90 |
| 30 | KOSDAQ | top5_exception | 3d | 1 | 10 | 6 | 50.0 | -3.3887 | -26.6898 | 26.0417 | 70.0 | 60.0 | decision_score >= 97.5 |
| 31 | KOSPI | top5_exception | 3d | 1 | 49 | 14 | 48.98 | -2.0726 | -20.5279 | 17.7508 | 67.347 | 53.061 | decision == WATCHLIST_ONLY |
| 32 | KOSDAQ | top5_exception | 3d | 3 | 23 | 10 | 47.826 | 0.2567 | -27.5218 | 42.1788 | 73.913 | 56.522 | alpha_score <= 71<br>decision_score >= 68.562<br>trend == DOWN |
| 33 | KOSDAQ | top5_exception | 3d | 1 | 21 | 10 | 47.619 | -1.8396 | -26.6898 | 26.0417 | 76.191 | 57.143 | decision_score >= 88.92 |
| 34 | KOSDAQ | top5_exception | 3d | 3 | 32 | 13 | 46.875 | 0.184 | -27.5218 | 42.1788 | 68.75 | 46.875 | alpha_score <= 80<br>priority_rank <= 4<br>trend == DOWN |
| 35 | KOSPI | top5_exception | 3d | 1 | 15 | 9 | 46.667 | -2.0324 | -24.85 | 15.6028 | 66.667 | 33.333 | prob_clean >= 33.85 |
| 36 | KOSPI | top5_exception | 3d | 2 | 15 | 9 | 46.667 | -2.0324 | -24.85 | 15.6028 | 66.667 | 33.333 | feature_quality == incomplete<br>prob_clean >= 33.85 |
| 37 | KOSPI | top5_exception | 3d | 2 | 15 | 9 | 46.667 | -2.0324 | -24.85 | 15.6028 | 66.667 | 33.333 | feature_completeness <= 0.8<br>prob_clean >= 33.85 |
| 38 | KOSDAQ | top5_exception | 3d | 3 | 26 | 12 | 46.154 | 0.0696 | -27.5218 | 42.1788 | 69.231 | 50.0 | alpha_score <= 80<br>priority_rank <= 3<br>trend == DOWN |
| 39 | KOSDAQ | top5_exception | 3d | 3 | 26 | 10 | 46.154 | -0.3735 | -27.5218 | 42.1788 | 76.923 | 57.692 | alpha_score <= 71<br>decision_score >= 59.35<br>trend == DOWN |
| 40 | KOSDAQ | top5_exception | 3d | 3 | 26 | 10 | 46.154 | -0.3735 | -27.5218 | 42.1788 | 76.923 | 57.692 | alpha_score <= 71<br>decision_score >= 57<br>trend == DOWN |
| 41 | KOSDAQ | top5_exception | 3d | 3 | 22 | 11 | 45.454 | 1.8496 | -15.4506 | 42.1788 | 68.182 | 40.909 | alpha_score <= 62<br>priority_rank <= 4<br>trend == DOWN |
| 42 | KOSDAQ | top5_exception | 3d | 2 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | priority_rank <= 4<br>trend == DOWN |
| 43 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | priority_rank <= 4<br>selection_lane == 3d<br>trend == DOWN |
| 44 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | kr_universe_role == CORE_TREND<br>priority_rank <= 4<br>trend == DOWN |
| 45 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | core_trend_flag_bool == True<br>priority_rank <= 4<br>trend == DOWN |
| 46 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | alpha_score <= 88.8<br>priority_rank <= 4<br>trend == DOWN |
| 47 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | feature_completeness <= 0.9<br>priority_rank <= 4<br>trend == DOWN |
| 48 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | feature_quality == incomplete<br>priority_rank <= 4<br>trend == DOWN |
| 49 | KOSDAQ | top5_exception | 3d | 3 | 33 | 13 | 45.454 | -0.457 | -27.5218 | 42.1788 | 69.697 | 48.485 | feature_completeness <= 0.8<br>priority_rank <= 4<br>trend == DOWN |
| 50 | KOSPI | top5_exception | 5d | 2 | 11 | 7 | 45.454 | -2.7533 | -23.8484 | 7.4751 | 54.546 | 45.454 | expected_return_1d_pct <= -0.8285<br>feature_completeness <= 0.8 |
| 51 | KOSDAQ | top5_exception | 5d | 3 | 11 | 7 | 45.454 | -4.2416 | -28.5511 | 28.6582 | 72.727 | 45.454 | decision_score <= 76.4<br>priority_rank <= 4<br>trend == DOWN |
| 52 | KOSDAQ | top5_exception | 5d | 1 | 9 | 7 | 44.444 | 6.3269 | -26.0569 | 54.6089 | 55.556 | 33.333 | prob_clean >= 36.66 |
| 53 | KOSDAQ | top5_exception | 3d | 3 | 9 | 6 | 44.444 | 1.388 | -15.9341 | 16.0494 | 44.444 | 22.222 | ml_prob <= 26.9<br>priority_rank <= 4<br>trend == DOWN |
| 54 | KOSDAQ | top5_exception | 3d | 3 | 9 | 6 | 44.444 | 0.019 | -14.0944 | 17.6367 | 88.889 | 55.556 | ml_prob <= 36.2<br>prob_clean >= 27.13<br>trend == DOWN |
| 55 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>decision == WATCHLIST_ONLY<br>feature_completeness <= 0.8 |
| 56 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>decision == WATCHLIST_ONLY<br>feature_quality == incomplete |
| 57 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>decision == WATCHLIST_ONLY<br>feature_origin == scanner_archive_outcome |
| 58 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>decision == WATCHLIST_ONLY<br>kr_universe_role == CORE_TREND |
| 59 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>core_trend_flag_bool == True<br>decision == WATCHLIST_ONLY |
| 60 | KOSPI | top5_exception | 5d | 3 | 27 | 10 | 44.444 | -0.1952 | -19.9154 | 18.2979 | 55.556 | 44.444 | alpha_score <= 65<br>decision == WATCHLIST_ONLY<br>explosive_leader_flag_bool == False |
| 61 | KOSDAQ | top5_exception | 3d | 2 | 27 | 13 | 44.444 | -0.7095 | -27.5218 | 42.1788 | 70.37 | 51.852 | priority_rank <= 3<br>trend == DOWN |
| 62 | KOSDAQ | top5_exception | 3d | 2 | 34 | 12 | 44.118 | -0.3616 | -27.5218 | 42.1788 | 73.529 | 55.882 | alpha_score <= 71<br>trend == DOWN |
| 63 | KOSDAQ | top5_exception | 3d | 3 | 34 | 12 | 44.118 | -0.3616 | -27.5218 | 42.1788 | 73.529 | 55.882 | alpha_score <= 71<br>priority_rank <= 5<br>trend == DOWN |
| 64 | KOSDAQ | top5_exception | 3d | 1 | 34 | 19 | 44.118 | -3.6326 | -27.5218 | 42.1788 | 79.412 | 55.882 | priority_rank <= 1 |
| 65 | KOSDAQ | top5_exception | 3d | 3 | 14 | 8 | 42.857 | 0.1271 | -20.5255 | 42.1788 | 71.429 | 42.857 | alpha_score <= 62<br>prob_clean >= 25.35<br>trend == DOWN |
| 66 | KOSDAQ | top5_exception | 3d | 3 | 21 | 11 | 42.857 | -1.469 | -27.5218 | 42.1788 | 71.429 | 52.381 | alpha_score <= 80<br>decision_score >= 76.4<br>trend == DOWN |
| 67 | KOSDAQ | top5_exception | 3d | 3 | 26 | 11 | 42.308 | -1.5349 | -27.5218 | 42.1788 | 73.077 | 53.846 | alpha_score <= 80<br>decision_score >= 68.562<br>trend == DOWN |
| 68 | KOSDAQ | top5_exception | 3d | 2 | 19 | 10 | 42.105 | -2.0264 | -27.5218 | 42.1788 | 78.947 | 57.895 | prob_clean >= 21.3<br>trend == DOWN |
| 69 | KOSDAQ | top5_exception | 3d | 3 | 19 | 10 | 42.105 | -2.0264 | -27.5218 | 42.1788 | 78.947 | 57.895 | alpha_score <= 80<br>prob_clean >= 21.3<br>trend == DOWN |
| 70 | KOSDAQ | top5_exception | 3d | 3 | 19 | 10 | 42.105 | -2.0264 | -27.5218 | 42.1788 | 78.947 | 57.895 | alpha_score <= 71<br>prob_clean >= 21.3<br>trend == DOWN |
| 71 | KOSDAQ | top5_exception | 3d | 3 | 19 | 10 | 42.105 | -2.0264 | -27.5218 | 42.1788 | 78.947 | 57.895 | alpha_score <= 88.8<br>prob_clean >= 21.3<br>trend == DOWN |
| 72 | KOSPI | top5_exception | 3d | 2 | 19 | 10 | 42.105 | -2.1361 | -15.9015 | 17.5342 | 100.0 | 36.842 | decision_score >= 108<br>ml_prob <= 39.9 |
| 73 | KOSDAQ | top5_exception | 3d | 2 | 19 | 9 | 42.105 | -4.0372 | -27.5218 | 17.6367 | 73.684 | 57.895 | alpha_score >= 56<br>trend == DOWN |
| 74 | KOSDAQ | top5_exception | 3d | 1 | 12 | 8 | 41.667 | -3.1169 | -16.0688 | 7.0679 | 83.333 | 41.667 | alpha_score <= 43.2 |
| 75 | KOSDAQ | top5_exception | 3d | 2 | 12 | 8 | 41.667 | -3.1169 | -16.0688 | 7.0679 | 83.333 | 41.667 | alpha_score <= 43.2<br>priority_rank <= 4 |
| 76 | KOSPI | top5_exception | 5d | 2 | 29 | 12 | 41.379 | -0.885 | -19.9154 | 18.2979 | 58.621 | 44.828 | alpha_score <= 65<br>decision == WATCHLIST_ONLY |
| 77 | KOSDAQ | top5_exception | 3d | 3 | 29 | 11 | 41.379 | -1.9145 | -27.5218 | 42.1788 | 75.862 | 55.172 | alpha_score <= 80<br>decision_score >= 59.35<br>trend == DOWN |
| 78 | KOSDAQ | top5_exception | 3d | 3 | 29 | 11 | 41.379 | -1.9145 | -27.5218 | 42.1788 | 75.862 | 55.172 | alpha_score <= 80<br>decision_score >= 57<br>trend == DOWN |
| 79 | KOSDAQ | top5_exception | 3d | 2 | 34 | 13 | 41.176 | -0.8885 | -27.5218 | 42.1788 | 73.529 | 52.941 | decision_score <= 97.5<br>trend == DOWN |
| 80 | KOSDAQ | top5_exception | 3d | 1 | 39 | 13 | 41.026 | -2.7901 | -27.5218 | 42.1788 | 79.487 | 56.41 | decision_score >= 76.4 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 92, 'categorical': 51, 'total': 143}`
- predicates: `{'raw': 1425, 'unique': 1425, 'numeric': 1291, 'after_support_screen': 901, 'categorical': 134, 'duplicates': 0}`
- predicate support screen: `{'kept': 901, 'rejected_test_support': 522, 'rejected_train_support': 56}`
- result counts: `{'mined_combinations': 768, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_win': 384, 'test_bad_path': 384, 'test_stop5': 368, 'test_avg': 356, 'train_bad_path': 176, 'train_win': 118, 'train_stop5': 62, 'train_avg': 30, 'test_n': 1, 'test_days': 1}`
- `5d`: `{'test_win': 384, 'test_bad_path': 384, 'test_avg': 378, 'test_stop5': 364, 'train_bad_path': 176, 'train_win': 120, 'train_stop5': 59, 'train_avg': 30}`

### Beam Pruning
- `3d`: `{'attempted': 32768, 'rejected_test_n': 11946, 'expanded_survivors': 11790, 'pruned_by_beam': 11534, 'rejected_train_n': 9380, 'skipped_duplicate': 3768, 'skipped_feature_conflict': 2862, 'base_pool': 512, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256, 'rejected_test_days': 235, 'rejected_train_days': 4}`
- `5d`: `{'attempted': 32768, 'rejected_test_n': 12270, 'expanded_survivors': 11905, 'pruned_by_beam': 11649, 'rejected_train_n': 8537, 'skipped_duplicate': 3874, 'skipped_feature_conflict': 2829, 'base_pool': 512, 'parent_beam': 256, 'next_beam': 256, 'emitted': 256, 'rejected_test_days': 226}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=825 days=75 predicates=466 results=384 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=739 days=71 predicates=435 results=384 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
