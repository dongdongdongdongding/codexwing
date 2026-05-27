# Significant Feature Combination Mining

- generated_at: `2026-05-27T11:32:49.734804+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4298`
- mined_combinations: `1920`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | top5_exception | 3d | 2 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome |
| 2 | KOSPI | top5_exception | 3d | 3 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 37.045 |
| 3 | KOSPI | top5_exception | 3d | 3 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome<br>prob_clean <= 34.5 |
| 4 | KOSPI | top5_exception | 3d | 4 | 8 | 5 | 75.0 | 2.0912 | -22.0867 | 15.1825 | 87.5 | 75.0 | decision_score >= 113<br>feature_origin == scanner_archive_outcome<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 5 | KOSPI | top5_exception | 3d | 2 | 12 | 5 | 75.0 | 1.546 | -22.0867 | 15.1825 | 75.0 | 50.0 | decision_score >= 113<br>prob_clean >= 22.51 |
| 6 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 7 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 8 | KOSPI | top5_exception | 3d | 3 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 9 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 10 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>feature_completeness >= 0.4<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 11 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 12 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 13 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>feature_completeness >= 0.5<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 14 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 15 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 16 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 17 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score <= 100<br>decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 18 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8<br>trend == UP |
| 19 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 20 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score <= 100<br>decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 21 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8<br>trend == UP |
| 22 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score <= 100<br>core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 23 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8<br>trend == UP |
| 24 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score >= 67<br>decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 32.8 |
| 25 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score >= 67<br>decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 32.8 |
| 26 | KOSPI | top5_exception | 3d | 4 | 11 | 5 | 72.727 | 3.4714 | -7.4334 | 15.1825 | 72.727 | 63.636 | alpha_score >= 67<br>core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 27 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False |
| 28 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND |
| 29 | KOSPI | top5_exception | 3d | 2 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113 |
| 30 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 34.5 |
| 31 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 34.5 |
| 32 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 34.5 |
| 33 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>prob_clean <= 37.045 |
| 34 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>prob_clean <= 37.045 |
| 35 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>prob_clean <= 37.045 |
| 36 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>priority_rank <= 10 |
| 37 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>priority_rank <= 10 |
| 38 | KOSPI | top5_exception | 3d | 3 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>priority_rank <= 10 |
| 39 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 40 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 41 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 42 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>explosive_leader_flag_bool == False<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 43 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | decision_score >= 113<br>kr_universe_role == CORE_TREND<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 44 | KOSPI | top5_exception | 3d | 4 | 13 | 5 | 69.231 | 1.6643 | -22.0867 | 15.1825 | 76.923 | 61.538 | core_trend_flag_bool == True<br>decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 45 | KOSPI | top5_exception | 3d | 3 | 9 | 5 | 66.667 | 4.186 | -7.4334 | 15.1825 | 77.778 | 66.667 | decision_score >= 113<br>ml_prob <= 36.7<br>prob_clean <= 37.045 |
| 46 | KOSPI | top5_exception | 3d | 3 | 9 | 5 | 66.667 | 4.186 | -7.4334 | 15.1825 | 77.778 | 66.667 | decision_score >= 113<br>ml_prob <= 36.7<br>prob_clean <= 34.5 |
| 47 | KOSPI | top5_exception | 3d | 2 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8 |
| 48 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 49 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 50 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 51 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>prob_clean <= 32.8<br>trend == UP |
| 52 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score >= 67<br>decision_score >= 113<br>prob_clean <= 32.8 |
| 53 | KOSPI | top5_exception | 3d | 3 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 32.8 |
| 54 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score <= 100<br>decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 55 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8<br>trend == UP |
| 56 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score <= 100<br>decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 57 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8<br>trend == UP |
| 58 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 32.8<br>trend == UP |
| 59 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score >= 67<br>decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 32.8 |
| 60 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score >= 67<br>decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 32.8 |
| 61 | KOSPI | top5_exception | 3d | 4 | 12 | 5 | 66.667 | 3.1392 | -7.4334 | 15.1825 | 75.0 | 66.667 | alpha_score >= 67<br>decision_score >= 113<br>prob_clean <= 32.8<br>trend == UP |
| 62 | KOSPI | top5_exception | 3d | 1 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113 |
| 63 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5 |
| 64 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 37.045 |
| 65 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10 |
| 66 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4 |
| 67 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5 |
| 68 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445 |
| 69 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score <= 100<br>decision_score >= 113 |
| 70 | KOSPI | top5_exception | 3d | 2 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>trend == UP |
| 71 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 21.445<br>prob_clean <= 37.045 |
| 72 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>priority_rank <= 10<br>prob_clean <= 37.045 |
| 73 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 34.5 |
| 74 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 20.275<br>prob_clean <= 37.045 |
| 75 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 18.9<br>prob_clean <= 37.045 |
| 76 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>ml_prob >= 20.275<br>prob_clean <= 34.5 |
| 77 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.4<br>prob_clean <= 34.5 |
| 78 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>feature_completeness >= 0.5<br>prob_clean <= 34.5 |
| 79 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | alpha_score <= 100<br>decision_score >= 113<br>prob_clean <= 34.5 |
| 80 | KOSPI | top5_exception | 3d | 3 | 15 | 5 | 66.667 | 1.7887 | -22.0867 | 15.1825 | 80.0 | 60.0 | decision_score >= 113<br>prob_clean <= 34.5<br>trend == UP |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 68, 'categorical': 50, 'total': 118}`
- predicates: `{'raw': 479, 'unique': 479, 'numeric': 395, 'after_support_screen': 376, 'categorical': 84, 'duplicates': 0}`
- predicate support screen: `{'kept': 376, 'rejected_train_support': 56, 'rejected_test_support': 54}`
- result counts: `{'mined_combinations': 1920, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `1d`: `{'test_win': 640, 'test_bad_path': 640, 'test_stop5': 625, 'test_avg': 611, 'train_win': 152, 'train_bad_path': 122, 'train_stop5': 20, 'test_days': 5, 'train_avg': 4, 'test_n': 3}`
- `3d`: `{'test_bad_path': 640, 'test_stop5': 626, 'test_win': 614, 'test_avg': 501, 'train_bad_path': 107, 'train_win': 28, 'train_stop5': 19, 'test_days': 5, 'test_n': 4}`
- `5d`: `{'test_win': 640, 'test_bad_path': 640, 'test_stop5': 632, 'test_avg': 594, 'train_bad_path': 104, 'train_stop5': 17, 'test_days': 9, 'test_n': 7, 'train_win': 4}`

### Beam Pruning
- `1d`: `{'attempted': 76800, 'rejected_train_n': 38756, 'rejected_test_n': 20090, 'expanded_survivors': 19842, 'pruned_by_beam': 19362, 'skipped_feature_conflict': 9804, 'skipped_duplicate': 4864, 'base_pool': 960, 'rejected_test_days': 753, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480, 'rejected_train_days': 121}`
- `3d`: `{'attempted': 76800, 'rejected_train_n': 40944, 'rejected_test_n': 20472, 'expanded_survivors': 18473, 'pruned_by_beam': 17993, 'skipped_feature_conflict': 9214, 'skipped_duplicate': 4371, 'base_pool': 960, 'rejected_test_days': 750, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480, 'rejected_train_days': 150}`
- `5d`: `{'attempted': 76800, 'rejected_train_n': 42067, 'rejected_test_n': 21472, 'expanded_survivors': 17049, 'pruned_by_beam': 16569, 'skipped_feature_conflict': 9126, 'skipped_duplicate': 4595, 'base_pool': 960, 'rejected_test_days': 753, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480, 'rejected_train_days': 66}`

### Scope Diagnostics
- `KOSPI` `top5_exception` rows=508 days=39 predicates=165 results=960 safe=0 skip=-
- `KOSDAQ` `top5_exception` rows=531 days=39 predicates=211 results=960 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
