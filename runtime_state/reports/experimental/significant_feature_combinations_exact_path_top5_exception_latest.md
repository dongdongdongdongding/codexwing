# Significant Feature Combination Mining

- generated_at: `2026-08-14T00:53:47.260080+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `5066`
- quality_scope: `exact_path`
- mined_combinations: `576`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | top5_exception | 5d | 2 | 6 | 6 | 83.333 | 5.1118 | -16.0514 | 23.2143 | 66.667 | 50.0 | prob_clean >= 21.6<br>trend == NEUTRAL |
| 2 | KOSPI | top5_exception | 5d | 3 | 6 | 6 | 83.333 | 5.1118 | -16.0514 | 23.2143 | 66.667 | 50.0 | alpha_score <= 100<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 3 | KOSPI | top5_exception | 5d | 3 | 6 | 6 | 83.333 | 5.1118 | -16.0514 | 23.2143 | 66.667 | 50.0 | feature_completeness >= 0.5<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 4 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 5.317 | -16.0514 | 23.2143 | 60.0 | 60.0 | priority_rank >= 2<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 5 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 4.5569 | -16.0514 | 23.2143 | 80.0 | 60.0 | decision_score >= 74.3<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 6 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 4.5569 | -16.0514 | 23.2143 | 80.0 | 60.0 | decision_score >= 65.96<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 7 | KOSPI | top5_exception | 5d | 2 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | prob_clean >= 24.2<br>trend == NEUTRAL |
| 8 | KOSPI | top5_exception | 5d | 2 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | prob_clean >= 26.5<br>trend == NEUTRAL |
| 9 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | alpha_score <= 100<br>prob_clean >= 24.2<br>trend == NEUTRAL |
| 10 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | alpha_score <= 100<br>prob_clean >= 26.5<br>trend == NEUTRAL |
| 11 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | feature_completeness >= 0.5<br>prob_clean >= 24.2<br>trend == NEUTRAL |
| 12 | KOSPI | top5_exception | 5d | 3 | 5 | 5 | 80.0 | 1.4914 | -16.0514 | 9.6639 | 80.0 | 60.0 | feature_completeness >= 0.5<br>prob_clean >= 26.5<br>trend == NEUTRAL |
| 13 | KOSPI | top5_exception | 3d | 3 | 5 | 5 | 80.0 | -0.7155 | -24.7994 | 7.8233 | 60.0 | 60.0 | priority_rank >= 2<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 14 | KOSPI | top5_exception | 5d | 1 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | trend == NEUTRAL |
| 15 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | alpha_score <= 100<br>trend == NEUTRAL |
| 16 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | feature_completeness >= 0.5<br>trend == NEUTRAL |
| 17 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | feature_origin == scanner_archive_outcome<br>trend == NEUTRAL |
| 18 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | feature_quality == incomplete<br>trend == NEUTRAL |
| 19 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | decision_score <= 108<br>trend == NEUTRAL |
| 20 | KOSPI | top5_exception | 5d | 2 | 8 | 7 | 75.0 | 3.0506 | -16.0514 | 23.2143 | 62.5 | 37.5 | feature_completeness <= 0.8<br>trend == NEUTRAL |
| 21 | KOSPI | top5_exception | 5d | 2 | 7 | 6 | 71.429 | 2.9027 | -16.0514 | 23.2143 | 57.143 | 42.857 | priority_rank >= 2<br>trend == NEUTRAL |
| 22 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.9027 | -16.0514 | 23.2143 | 57.143 | 42.857 | alpha_score <= 100<br>priority_rank >= 2<br>trend == NEUTRAL |
| 23 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.9027 | -16.0514 | 23.2143 | 57.143 | 42.857 | feature_completeness >= 0.5<br>priority_rank >= 2<br>trend == NEUTRAL |
| 24 | KOSPI | top5_exception | 5d | 2 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | decision_score >= 74.3<br>trend == NEUTRAL |
| 25 | KOSPI | top5_exception | 5d | 2 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | decision_score >= 65.96<br>trend == NEUTRAL |
| 26 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | alpha_score <= 100<br>decision_score >= 74.3<br>trend == NEUTRAL |
| 27 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | decision_score >= 74.3<br>feature_quality == incomplete<br>trend == NEUTRAL |
| 28 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | alpha_score <= 100<br>decision_score >= 65.96<br>trend == NEUTRAL |
| 29 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | decision_score >= 74.3<br>feature_completeness <= 0.8<br>trend == NEUTRAL |
| 30 | KOSPI | top5_exception | 5d | 3 | 7 | 6 | 71.429 | 2.3597 | -16.0514 | 23.2143 | 71.429 | 42.857 | decision_score >= 65.96<br>feature_completeness >= 0.5<br>trend == NEUTRAL |
| 31 | KOSPI | top5_exception | 3d | 2 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | priority_rank >= 2<br>trend == NEUTRAL |
| 32 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | alpha_score <= 100<br>priority_rank >= 2<br>trend == NEUTRAL |
| 33 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | feature_completeness >= 0.5<br>priority_rank >= 2<br>trend == NEUTRAL |
| 34 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | feature_quality == incomplete<br>priority_rank >= 2<br>trend == NEUTRAL |
| 35 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | decision_score <= 108<br>priority_rank >= 2<br>trend == NEUTRAL |
| 36 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 71.429 | -0.7353 | -24.7994 | 9.0426 | 57.143 | 42.857 | feature_completeness <= 0.8<br>priority_rank >= 2<br>trend == NEUTRAL |
| 37 | KOSDAQ | top5_exception | 3d | 2 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | trend == DOWN<br>volume_ratio <= 0.98 |
| 38 | KOSDAQ | top5_exception | 3d | 3 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | alpha_score <= 80<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 39 | KOSDAQ | top5_exception | 3d | 3 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | feature_completeness <= 0.9<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 40 | KOSDAQ | top5_exception | 3d | 3 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | feature_quality == incomplete<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 41 | KOSDAQ | top5_exception | 3d | 3 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | feature_completeness <= 0.8<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 42 | KOSDAQ | top5_exception | 3d | 3 | 6 | 5 | 66.667 | 10.3478 | -5.2988 | 42.1788 | 66.667 | 33.333 | priority_rank <= 5<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 43 | KOSDAQ | top5_exception | 3d | 1 | 9 | 7 | 66.667 | 5.5935 | -24.5039 | 42.1788 | 55.556 | 33.333 | prob_clean >= 36.66 |
| 44 | KOSPI | top5_exception | 5d | 3 | 6 | 5 | 66.667 | 2.072 | -16.0514 | 23.2143 | 66.667 | 50.0 | decision_score >= 65.96<br>priority_rank >= 2<br>trend == NEUTRAL |
| 45 | KOSPI | top5_exception | 5d | 3 | 6 | 5 | 66.667 | 2.072 | -16.0514 | 23.2143 | 66.667 | 50.0 | decision_score >= 74.3<br>priority_rank >= 2<br>trend == NEUTRAL |
| 46 | KOSPI | top5_exception | 3d | 2 | 6 | 6 | 66.667 | -0.7755 | -24.7994 | 7.8233 | 66.667 | 50.0 | prob_clean >= 21.6<br>trend == NEUTRAL |
| 47 | KOSPI | top5_exception | 3d | 3 | 6 | 5 | 66.667 | -2.1618 | -24.7994 | 9.0426 | 66.667 | 50.0 | decision_score >= 65.96<br>priority_rank >= 2<br>trend == NEUTRAL |
| 48 | KOSPI | top5_exception | 3d | 3 | 6 | 5 | 66.667 | -2.1618 | -24.7994 | 9.0426 | 66.667 | 50.0 | decision_score >= 74.3<br>priority_rank >= 2<br>trend == NEUTRAL |
| 49 | KOSDAQ | top5_exception | 3d | 2 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | prob_clean >= 30.1<br>trend == DOWN |
| 50 | KOSDAQ | top5_exception | 3d | 3 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | alpha_score <= 80<br>prob_clean >= 30.1<br>trend == DOWN |
| 51 | KOSDAQ | top5_exception | 3d | 3 | 8 | 5 | 62.5 | 6.4697 | -7.8125 | 42.1788 | 75.0 | 37.5 | alpha_score <= 88.8<br>prob_clean >= 30.1<br>trend == DOWN |
| 52 | KOSPI | top5_exception | 3d | 1 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | trend == NEUTRAL |
| 53 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | alpha_score <= 100<br>trend == NEUTRAL |
| 54 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | feature_quality == incomplete<br>trend == NEUTRAL |
| 55 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | decision_score <= 108<br>trend == NEUTRAL |
| 56 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | feature_completeness >= 0.5<br>trend == NEUTRAL |
| 57 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | feature_completeness <= 0.8<br>trend == NEUTRAL |
| 58 | KOSPI | top5_exception | 3d | 2 | 8 | 7 | 62.5 | -0.7778 | -24.7994 | 9.0426 | 62.5 | 37.5 | feature_origin == scanner_archive_outcome<br>trend == NEUTRAL |
| 59 | KOSDAQ | top5_exception | 3d | 1 | 5 | 5 | 60.0 | 0.8819 | -15.9341 | 12.6338 | 60.0 | 40.0 | ml_prob <= 22.1 |
| 60 | KOSPI | top5_exception | 3d | 2 | 5 | 5 | 60.0 | -1.8949 | -24.7994 | 7.8233 | 80.0 | 60.0 | prob_clean >= 24.2<br>trend == NEUTRAL |
| 61 | KOSPI | top5_exception | 3d | 2 | 5 | 5 | 60.0 | -1.8949 | -24.7994 | 7.8233 | 80.0 | 60.0 | prob_clean >= 26.5<br>trend == NEUTRAL |
| 62 | KOSPI | top5_exception | 3d | 3 | 5 | 5 | 60.0 | -2.4953 | -24.7994 | 7.3529 | 80.0 | 60.0 | decision_score >= 74.3<br>prob_clean >= 21.6<br>trend == NEUTRAL |
| 63 | KOSPI | top5_exception | 3d | 2 | 7 | 6 | 57.143 | -2.0066 | -24.7994 | 9.0426 | 71.429 | 42.857 | decision_score >= 74.3<br>trend == NEUTRAL |
| 64 | KOSPI | top5_exception | 3d | 2 | 7 | 6 | 57.143 | -2.0066 | -24.7994 | 9.0426 | 71.429 | 42.857 | decision_score >= 65.96<br>trend == NEUTRAL |
| 65 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 57.143 | -2.0066 | -24.7994 | 9.0426 | 71.429 | 42.857 | alpha_score <= 100<br>decision_score >= 74.3<br>trend == NEUTRAL |
| 66 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 57.143 | -2.0066 | -24.7994 | 9.0426 | 71.429 | 42.857 | decision_score >= 74.3<br>feature_quality == incomplete<br>trend == NEUTRAL |
| 67 | KOSPI | top5_exception | 3d | 3 | 7 | 6 | 57.143 | -2.0066 | -24.7994 | 9.0426 | 71.429 | 42.857 | decision_score >= 74.3<br>feature_completeness <= 0.8<br>trend == NEUTRAL |
| 68 | KOSPI | top5_exception | 5d | 1 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | prob_clean >= 33.85 |
| 69 | KOSPI | top5_exception | 5d | 2 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | feature_quality == incomplete<br>prob_clean >= 33.85 |
| 70 | KOSPI | top5_exception | 5d | 2 | 15 | 9 | 53.333 | 0.6964 | -21.1774 | 18.2979 | 66.667 | 33.333 | feature_completeness <= 0.8<br>prob_clean >= 33.85 |
| 71 | KOSDAQ | top5_exception | 3d | 3 | 29 | 12 | 51.724 | 1.7827 | -27.5218 | 42.1788 | 68.966 | 48.276 | alpha_score <= 71<br>priority_rank <= 4<br>trend == DOWN |
| 72 | KOSDAQ | top5_exception | 5d | 2 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | trend == DOWN<br>volume_ratio <= 0.98 |
| 73 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | alpha_score <= 80<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 74 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | alpha_score <= 71<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 75 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | alpha_score <= 62<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 76 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | alpha_score <= 56<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 77 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | feature_completeness <= 0.9<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 78 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | feature_quality == incomplete<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 79 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | feature_completeness <= 0.8<br>trend == DOWN<br>volume_ratio <= 0.98 |
| 80 | KOSDAQ | top5_exception | 5d | 3 | 6 | 5 | 50.0 | 2.3852 | -26.1645 | 54.6089 | 66.667 | 33.333 | alpha_score <= 52<br>trend == DOWN<br>volume_ratio <= 0.98 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 92, 'categorical': 51, 'total': 143}`
- predicates: `{'raw': 1436, 'unique': 1436, 'numeric': 1296, 'after_support_screen': 1062, 'categorical': 140, 'duplicates': 0}`
- predicate support screen: `{'kept': 1062, 'rejected_test_support': 373, 'rejected_train_support': 20}`
- result counts: `{'mined_combinations': 576, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `3d`: `{'test_bad_path': 288, 'test_win': 281, 'test_stop5': 279, 'test_avg': 264, 'train_bad_path': 114, 'train_win': 80, 'train_stop5': 44, 'train_avg': 15}`
- `5d`: `{'test_bad_path': 288, 'test_stop5': 280, 'test_win': 259, 'test_avg': 237, 'train_bad_path': 107, 'train_win': 85, 'train_stop5': 40, 'train_avg': 14, 'test_days': 3}`

### Beam Pruning
- `3d`: `{'attempted': 18432, 'expanded_survivors': 7427, 'pruned_by_beam': 7235, 'rejected_test_n': 5514, 'rejected_train_n': 4737, 'skipped_duplicate': 2419, 'skipped_feature_conflict': 1763, 'base_pool': 384, 'rejected_test_days': 222, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192}`
- `5d`: `{'attempted': 18432, 'expanded_survivors': 7310, 'pruned_by_beam': 7118, 'rejected_test_n': 5798, 'rejected_train_n': 4670, 'skipped_duplicate': 2246, 'skipped_feature_conflict': 1754, 'base_pool': 384, 'rejected_test_days': 296, 'parent_beam': 192, 'next_beam': 192, 'emitted': 192}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=825 days=75 predicates=532 results=288 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=739 days=71 predicates=530 results=288 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
