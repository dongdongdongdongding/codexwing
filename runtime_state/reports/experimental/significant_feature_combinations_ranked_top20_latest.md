# Significant Feature Combination Mining

- generated_at: `2026-05-27T11:40:54.962898+00:00`
- report_version: `significant_feature_combo_mining_v2`
- input_rows: `4298`
- mined_combinations: `1920`
- production_safe_count: `0`

## Top Validated Combinations

| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | ranked_top20 | 5d | 4 | 8 | 5 | 87.5 | 8.4669 | -11.206 | 27.6342 | 87.5 | 75.0 | conviction_score <= 68.775<br>decision_score >= 70.1<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 2 | KOSPI | ranked_top20 | 3d | 1 | 7 | 2 | 85.714 | 3.1377 | -8.9849 | 10.2167 | 100.0 | 42.857 | ml_prob <= 24.5 |
| 3 | KOSDAQ | ranked_top20 | 5d | 4 | 9 | 5 | 66.667 | 5.6219 | -19.1176 | 32.4143 | 88.889 | 77.778 | alpha_score <= 62<br>priority_rank <= 3<br>selection_lane == 3d<br>theme_source == stock_master |
| 4 | KOSPI | ranked_top20 | 1d | 2 | 8 | 6 | 62.5 | -0.2329 | -7.717 | 5.0325 | 50.0 | 12.5 | expected_edge_score >= 3.7625<br>kr_universe_role == EXPLOSIVE_LEADER |
| 5 | KOSPI | ranked_top20 | 1d | 2 | 8 | 6 | 62.5 | -0.2329 | -7.717 | 5.0325 | 50.0 | 12.5 | expected_edge_score >= 3.7625<br>explosive_leader_flag_bool == True |
| 6 | KOSPI | ranked_top20 | 1d | 2 | 8 | 6 | 62.5 | -0.2329 | -7.717 | 5.0325 | 50.0 | 12.5 | expected_return_1d_pct >= 0.2675<br>kr_universe_role == EXPLOSIVE_LEADER |
| 7 | KOSPI | ranked_top20 | 1d | 2 | 8 | 6 | 62.5 | -0.2329 | -7.717 | 5.0325 | 50.0 | 12.5 | expected_return_1d_pct >= 0.2675<br>explosive_leader_flag_bool == True |
| 8 | KOSPI | ranked_top20 | 1d | 2 | 13 | 5 | 61.538 | 0.9044 | -19.1554 | 12.6479 | 84.615 | 30.769 | core_trend_flag_bool == False<br>expected_edge_score <= -14.1835 |
| 9 | KOSPI | ranked_top20 | 1d | 3 | 10 | 7 | 60.0 | 1.4468 | -7.0 | 6.7651 | 80.0 | 40.0 | conviction_score <= 68.775<br>expected_return_3d_pct >= 0.071<br>prob_clean >= 29.5 |
| 10 | KOSDAQ | ranked_top20 | 1d | 3 | 10 | 5 | 60.0 | 1.2574 | -6.1279 | 18.5495 | 50.0 | 40.0 | expected_return_3d_pct <= -0.9325<br>priority_rank <= 6<br>volume_ratio <= 1.26 |
| 11 | KOSDAQ | ranked_top20 | 1d | 4 | 10 | 5 | 60.0 | 1.2574 | -6.1279 | 18.5495 | 50.0 | 40.0 | alpha_score >= 49<br>expected_return_3d_pct <= -0.9325<br>priority_rank <= 6<br>volume_ratio <= 1.26 |
| 12 | KOSDAQ | ranked_top20 | 5d | 4 | 10 | 6 | 60.0 | 0.1887 | -46.3097 | 32.4143 | 100.0 | 90.0 | alpha_score <= 62<br>ml_prob <= 50<br>priority_rank <= 3<br>theme_source == stock_master |
| 13 | KOSDAQ | ranked_top20 | 5d | 4 | 10 | 6 | 60.0 | 0.1887 | -46.3097 | 32.4143 | 100.0 | 90.0 | alpha_score <= 62<br>ml_prob <= 49.9<br>priority_rank <= 3<br>theme_source == stock_master |
| 14 | KOSPI | ranked_top20 | 1d | 4 | 10 | 6 | 60.0 | -1.5759 | -14.0921 | 5.3678 | 80.0 | 70.0 | conviction_score <= 71.5<br>expected_edge_score >= -3.325<br>ml_prob <= 40.49<br>prob_clean >= 29.5 |
| 15 | KOSPI | ranked_top20 | 1d | 4 | 10 | 6 | 60.0 | -1.5759 | -14.0921 | 5.3678 | 80.0 | 70.0 | conviction_score <= 71.5<br>expected_return_1d_pct >= -0.235<br>ml_prob <= 40.49<br>prob_clean >= 29.5 |
| 16 | KOSPI | ranked_top20 | 5d | 4 | 29 | 8 | 58.621 | 0.3612 | -17.8016 | 27.6342 | 82.759 | 65.517 | conviction_score <= 68.775<br>priority_rank <= 11<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 17 | KOSPI | ranked_top20 | 1d | 2 | 12 | 5 | 58.333 | 0.5183 | -19.1554 | 12.6479 | 91.667 | 33.333 | core_trend_flag_bool == False<br>expected_return_3d_pct <= -1.898 |
| 18 | KOSPI | ranked_top20 | 1d | 2 | 21 | 11 | 57.143 | 0.2508 | -14.986 | 17.3134 | 47.619 | 23.809 | kr_universe_role == EXPLOSIVE_LEADER<br>priority_rank <= 2 |
| 19 | KOSPI | ranked_top20 | 1d | 2 | 21 | 11 | 57.143 | 0.2508 | -14.986 | 17.3134 | 47.619 | 23.809 | explosive_leader_flag_bool == True<br>priority_rank <= 2 |
| 20 | KOSPI | ranked_top20 | 5d | 4 | 28 | 8 | 57.143 | 0.2001 | -17.8016 | 27.6342 | 85.714 | 67.857 | conviction_score <= 68.775<br>priority_rank <= 10<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 21 | KOSPI | ranked_top20 | 1d | 1 | 14 | 5 | 57.143 | 0.0872 | -19.1554 | 12.6479 | 92.857 | 35.714 | expected_return_1d_pct <= -1.179 |
| 22 | KOSPI | ranked_top20 | 1d | 2 | 14 | 5 | 57.143 | 0.0872 | -19.1554 | 12.6479 | 92.857 | 35.714 | decision_score <= 70.1<br>expected_return_1d_pct <= -1.179 |
| 23 | KOSPI | ranked_top20 | 1d | 2 | 14 | 5 | 57.143 | 0.0872 | -19.1554 | 12.6479 | 92.857 | 35.714 | decision_score <= 80<br>expected_return_1d_pct <= -1.179 |
| 24 | KOSPI | ranked_top20 | 1d | 2 | 14 | 5 | 57.143 | 0.0872 | -19.1554 | 12.6479 | 92.857 | 35.714 | decision_score <= 87<br>expected_return_1d_pct <= -1.179 |
| 25 | KOSPI | ranked_top20 | 1d | 3 | 14 | 5 | 57.143 | 0.0872 | -19.1554 | 12.6479 | 92.857 | 35.714 | decision_score <= 70.1<br>expected_return_1d_pct <= -1.179<br>theme_routing_path == core_only |
| 26 | KOSPI | ranked_top20 | 5d | 4 | 30 | 8 | 56.667 | -0.3613 | -21.3141 | 27.6342 | 83.333 | 66.667 | conviction_score <= 68.775<br>priority_rank <= 13<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 27 | KOSPI | ranked_top20 | 5d | 4 | 23 | 8 | 56.522 | -0.4744 | -17.8016 | 27.6342 | 82.609 | 65.217 | conviction_score <= 68.775<br>expected_return_3d_pct >= -0.85<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 28 | KOSPI | ranked_top20 | 1d | 2 | 18 | 7 | 55.556 | 0.3256 | -19.1554 | 12.6479 | 88.889 | 33.333 | decision_score <= 70.1<br>expected_edge_score <= -14.1835 |
| 29 | KOSPI | ranked_top20 | 1d | 2 | 18 | 7 | 55.556 | 0.3256 | -19.1554 | 12.6479 | 88.889 | 33.333 | decision_score <= 80<br>expected_edge_score <= -14.1835 |
| 30 | KOSPI | ranked_top20 | 1d | 2 | 18 | 7 | 55.556 | 0.3256 | -19.1554 | 12.6479 | 88.889 | 33.333 | decision_score <= 87<br>expected_edge_score <= -14.1835 |
| 31 | KOSPI | ranked_top20 | 1d | 3 | 18 | 7 | 55.556 | 0.3256 | -19.1554 | 12.6479 | 88.889 | 33.333 | decision_score <= 70.1<br>expected_edge_score <= -14.1835<br>theme_routing_path == core_only |
| 32 | KOSPI | ranked_top20 | 1d | 4 | 9 | 6 | 55.556 | -2.3474 | -14.0921 | 4.4467 | 77.778 | 66.667 | conviction_score <= 71.5<br>expected_return_3d_pct >= -0.365<br>ml_prob <= 40.49<br>prob_clean >= 29.5 |
| 33 | KOSPI | ranked_top20 | 1d | 2 | 20 | 8 | 55.0 | 1.4027 | -10.2941 | 12.6479 | 70.0 | 25.0 | conviction_score <= 66.325<br>ml_prob <= 28.6 |
| 34 | KOSPI | ranked_top20 | 5d | 3 | 31 | 8 | 54.839 | -0.8781 | -21.3141 | 27.6342 | 83.871 | 67.742 | conviction_score <= 68.775<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 35 | KOSPI | ranked_top20 | 1d | 4 | 11 | 6 | 54.546 | 0.7884 | -11.659 | 6.7734 | 81.818 | 63.636 | conviction_score <= 68.775<br>decision_score >= 70.1<br>expected_edge_score >= -3.325<br>prob_clean >= 29.5 |
| 36 | KOSPI | ranked_top20 | 1d | 4 | 11 | 6 | 54.546 | 0.7884 | -11.659 | 6.7734 | 81.818 | 63.636 | conviction_score <= 68.775<br>decision_score >= 70.1<br>expected_return_1d_pct >= -0.235<br>prob_clean >= 29.5 |
| 37 | KOSDAQ | ranked_top20 | 5d | 4 | 11 | 6 | 54.546 | -0.8992 | -46.3097 | 32.4143 | 90.909 | 72.727 | alpha_score <= 62<br>priority_rank <= 3<br>prob_clean <= 36.2<br>theme_source == stock_master |
| 38 | KOSPI | ranked_top20 | 1d | 3 | 11 | 7 | 54.546 | -0.9507 | -19.3443 | 15.0943 | 63.636 | 45.454 | alpha_score <= 83<br>phase25_prob <= 38.3<br>prob_clean >= 29.5 |
| 39 | KOSPI | ranked_top20 | 5d | 4 | 24 | 8 | 54.167 | -0.78 | -17.8016 | 27.6342 | 83.333 | 66.667 | conviction_score <= 68.775<br>expected_edge_score >= -7.1405<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 40 | KOSDAQ | ranked_top20 | 3d | 3 | 13 | 6 | 53.846 | 2.8239 | -10.8604 | 43.6396 | 69.231 | 61.538 | kr_universe_role == EXPLOSIVE_LEADER<br>theme_inference_status == inferred<br>whale_score <= 75 |
| 41 | KOSDAQ | ranked_top20 | 3d | 3 | 13 | 6 | 53.846 | 2.8239 | -10.8604 | 43.6396 | 69.231 | 61.538 | explosive_leader_flag_bool == True<br>theme_inference_status == inferred<br>whale_score <= 75 |
| 42 | KOSDAQ | ranked_top20 | 1d | 2 | 15 | 8 | 53.333 | 0.7789 | -7.7055 | 18.5495 | 60.0 | 40.0 | expected_return_3d_pct <= -0.9325<br>volume_ratio <= 1.26 |
| 43 | KOSDAQ | ranked_top20 | 1d | 2 | 15 | 8 | 53.333 | 0.7789 | -7.7055 | 18.5495 | 60.0 | 40.0 | expected_return_3d_pct <= -0.9325<br>volume_ratio <= 1.2 |
| 44 | KOSPI | ranked_top20 | 1d | 3 | 15 | 7 | 53.333 | -0.0136 | -14.986 | 6.7651 | 80.0 | 33.333 | conviction_score <= 71.5<br>expected_return_3d_pct >= 0.071<br>prob_clean >= 29.5 |
| 45 | KOSPI | ranked_top20 | 1d | 3 | 15 | 7 | 53.333 | -0.0136 | -14.986 | 6.7651 | 80.0 | 33.333 | conviction_score <= 71.5<br>expected_edge_score >= 0.2015<br>prob_clean >= 29.5 |
| 46 | KOSPI | ranked_top20 | 1d | 3 | 15 | 7 | 53.333 | -0.0136 | -14.986 | 6.7651 | 80.0 | 33.333 | conviction_score <= 71.5<br>expected_return_1d_pct >= 0.0105<br>prob_clean >= 29.5 |
| 47 | KOSPI | ranked_top20 | 1d | 2 | 36 | 9 | 52.778 | 0.9344 | -19.3443 | 17.9962 | 72.222 | 38.889 | kosdaq_chg <= 1.86<br>phase25_prob <= 38.3 |
| 48 | KOSPI | ranked_top20 | 1d | 1 | 19 | 8 | 52.632 | 0.3022 | -19.1554 | 12.6479 | 89.474 | 36.842 | expected_edge_score <= -14.1835 |
| 49 | KOSPI | ranked_top20 | 1d | 2 | 23 | 10 | 52.174 | -0.4276 | -13.5214 | 6.3315 | 69.565 | 43.478 | conviction_score <= 66.325<br>expected_return_3d_pct >= -0.365 |
| 50 | KOSDAQ | ranked_top20 | 5d | 2 | 23 | 7 | 52.174 | -1.1887 | -46.3097 | 32.4143 | 82.609 | 69.565 | alpha_score <= 62<br>priority_rank <= 3 |
| 51 | KOSPI | ranked_top20 | 5d | 4 | 23 | 8 | 52.174 | -1.7686 | -21.3141 | 27.6342 | 86.957 | 69.565 | conviction_score <= 68.775<br>explosive_leader_flag_bool == False<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 52 | KOSPI | ranked_top20 | 5d | 4 | 25 | 8 | 52.0 | -0.9852 | -17.8016 | 27.6342 | 84.0 | 68.0 | conviction_score <= 68.775<br>expected_return_1d_pct >= -0.5105<br>prob_clean >= 29.5<br>theme_routing_path == core_only |
| 53 | KOSDAQ | ranked_top20 | 3d | 2 | 27 | 7 | 51.852 | 1.5847 | -19.2781 | 43.6396 | 66.667 | 55.556 | theme_source == stock_master<br>volume_ratio >= 2 |
| 54 | KOSPI | ranked_top20 | 1d | 1 | 31 | 10 | 51.613 | 1.3166 | -10.2941 | 17.9962 | 67.742 | 29.032 | ml_prob <= 28.6 |
| 55 | KOSPI | ranked_top20 | 1d | 3 | 33 | 9 | 51.515 | -0.398 | -13.5214 | 6.7734 | 72.727 | 45.454 | conviction_score <= 68.775<br>expected_edge_score >= -3.325<br>prob_clean >= 29.5 |
| 56 | KOSPI | ranked_top20 | 1d | 3 | 33 | 9 | 51.515 | -0.398 | -13.5214 | 6.7734 | 72.727 | 45.454 | conviction_score <= 68.775<br>expected_return_1d_pct >= -0.235<br>prob_clean >= 29.5 |
| 57 | KOSPI | ranked_top20 | 1d | 4 | 33 | 9 | 51.515 | -0.398 | -13.5214 | 6.7734 | 72.727 | 45.454 | conviction_score <= 68.775<br>expected_edge_score >= -3.325<br>ml_prob >= 18.9<br>prob_clean >= 29.5 |
| 58 | KOSPI | ranked_top20 | 1d | 4 | 33 | 9 | 51.515 | -0.398 | -13.5214 | 6.7734 | 72.727 | 45.454 | conviction_score <= 68.775<br>expected_return_1d_pct >= -0.235<br>ml_prob >= 18.9<br>prob_clean >= 29.5 |
| 59 | KOSDAQ | ranked_top20 | 3d | 3 | 14 | 6 | 50.0 | 1.8325 | -12.9434 | 43.6396 | 71.429 | 64.286 | kr_universe_role == EXPLOSIVE_LEADER<br>prob_clean >= 23.6<br>whale_score <= 75 |
| 60 | KOSDAQ | ranked_top20 | 3d | 3 | 14 | 6 | 50.0 | 1.8325 | -12.9434 | 43.6396 | 71.429 | 64.286 | explosive_leader_flag_bool == True<br>prob_clean >= 23.6<br>whale_score <= 75 |
| 61 | KOSPI | ranked_top20 | 3d | 1 | 8 | 4 | 50.0 | 1.4352 | -7.0175 | 18.1604 | 62.5 | 37.5 | phase25_prob <= 23.4 |
| 62 | KOSDAQ | ranked_top20 | 3d | 3 | 26 | 7 | 50.0 | 0.8719 | -19.2781 | 43.6396 | 65.385 | 53.846 | feature_completeness >= 0.6<br>theme_source == stock_master<br>volume_ratio >= 2 |
| 63 | KOSDAQ | ranked_top20 | 3d | 4 | 26 | 7 | 50.0 | 0.8719 | -19.2781 | 43.6396 | 65.385 | 53.846 | feature_completeness >= 0.6<br>ml_prob >= 20.2<br>theme_source == stock_master<br>volume_ratio >= 2 |
| 64 | KOSPI | ranked_top20 | 1d | 1 | 28 | 9 | 50.0 | 0.3842 | -8.5179 | 11.0714 | 64.286 | 35.714 | expected_return_3d_pct >= 0.6175 |
| 65 | KOSPI | ranked_top20 | 3d | 3 | 14 | 10 | 50.0 | 0.2101 | -12.659 | 20.0898 | 71.429 | 35.714 | expected_edge_score >= -3.325<br>prob_clean >= 29.5<br>tech_score >= 85 |
| 66 | KOSPI | ranked_top20 | 3d | 3 | 14 | 10 | 50.0 | 0.2101 | -12.659 | 20.0898 | 71.429 | 35.714 | expected_return_1d_pct >= -0.235<br>prob_clean >= 29.5<br>tech_score >= 85 |
| 67 | KOSPI | ranked_top20 | 1d | 1 | 6 | 3 | 50.0 | 0.0934 | -4.0261 | 3.6315 | 66.667 | 33.333 | priority_rank >= 20 |
| 68 | KOSPI | ranked_top20 | 1d | 2 | 16 | 7 | 50.0 | -0.4295 | -19.1554 | 12.6479 | 93.75 | 31.25 | decision_score <= 70.1<br>expected_return_3d_pct <= -1.898 |
| 69 | KOSPI | ranked_top20 | 1d | 2 | 16 | 7 | 50.0 | -0.4295 | -19.1554 | 12.6479 | 93.75 | 31.25 | decision_score <= 80<br>expected_return_3d_pct <= -1.898 |
| 70 | KOSPI | ranked_top20 | 1d | 2 | 16 | 7 | 50.0 | -0.4295 | -19.1554 | 12.6479 | 93.75 | 31.25 | decision_score <= 87<br>expected_return_3d_pct <= -1.898 |
| 71 | KOSPI | ranked_top20 | 1d | 3 | 16 | 7 | 50.0 | -0.4295 | -19.1554 | 12.6479 | 93.75 | 31.25 | decision_score <= 70.1<br>expected_return_3d_pct <= -1.898<br>theme_routing_path == core_only |
| 72 | KOSPI | ranked_top20 | 1d | 3 | 30 | 9 | 50.0 | -0.4951 | -13.5214 | 6.7734 | 73.333 | 43.333 | conviction_score <= 68.775<br>expected_return_3d_pct >= -0.365<br>prob_clean >= 29.5 |
| 73 | KOSPI | ranked_top20 | 1d | 4 | 30 | 9 | 50.0 | -0.4951 | -13.5214 | 6.7734 | 73.333 | 43.333 | conviction_score <= 68.775<br>expected_return_3d_pct >= -0.365<br>ml_prob >= 20.4<br>prob_clean >= 29.5 |
| 74 | KOSPI | ranked_top20 | 1d | 4 | 30 | 9 | 50.0 | -0.4951 | -13.5214 | 6.7734 | 73.333 | 43.333 | conviction_score <= 68.775<br>expected_return_3d_pct >= -0.365<br>priority_rank <= 13<br>prob_clean >= 29.5 |
| 75 | KOSPI | ranked_top20 | 3d | 4 | 24 | 9 | 50.0 | -0.9662 | -13.9423 | 9.2037 | 70.833 | 41.667 | decision_bucket == watchlist<br>decision_score <= 80<br>priority_rank <= 13<br>prob_clean >= 32.68 |
| 76 | KOSDAQ | ranked_top20 | 5d | 1 | 6 | 3 | 50.0 | -1.4356 | -17.2391 | 8.9947 | 83.333 | 50.0 | expected_return_1d_pct <= -0.8915 |
| 77 | KOSDAQ | ranked_top20 | 3d | 1 | 8 | 5 | 50.0 | -1.4386 | -12.9434 | 20.1189 | 87.5 | 87.5 | tech_score >= 100 |
| 78 | KOSPI | ranked_top20 | 1d | 4 | 10 | 7 | 50.0 | -1.4803 | -14.986 | 6.7734 | 70.0 | 40.0 | conviction_score <= 71.5<br>decision_score >= 80<br>expected_return_3d_pct >= -0.365<br>prob_clean >= 29.5 |
| 79 | KOSPI | ranked_top20 | 1d | 4 | 10 | 7 | 50.0 | -1.4803 | -14.986 | 6.7734 | 70.0 | 40.0 | conviction_score <= 71.5<br>decision_score >= 80<br>expected_edge_score >= -3.325<br>prob_clean >= 29.5 |
| 80 | KOSPI | ranked_top20 | 1d | 4 | 10 | 7 | 50.0 | -1.4803 | -14.986 | 6.7734 | 70.0 | 40.0 | conviction_score <= 71.5<br>decision_score >= 80<br>expected_return_1d_pct >= -0.235<br>prob_clean >= 29.5 |

## Production Safe Candidates

- None found under current holdout gate.

## Search Diagnostics

- scopes evaluated: `2`
- candidate features: `{'numeric': 80, 'categorical': 50, 'total': 130}`
- predicates: `{'raw': 542, 'unique': 542, 'after_support_screen': 481, 'numeric': 448, 'categorical': 94, 'duplicates': 0}`
- predicate support screen: `{'kept': 481, 'rejected_test_support': 49, 'rejected_train_support': 21}`
- result counts: `{'mined_combinations': 1920, 'production_safe': 0}`
- exact exhaustive: `{'enabled_scopes': 0, 'disabled_scopes': {'disabled': 2}, 'checked_combinations': 0, 'production_safe_combinations': 0}`

### Gate Rejections
- `1d`: `{'test_win': 640, 'test_bad_path': 640, 'test_stop5': 615, 'test_avg': 600, 'train_win': 201, 'train_bad_path': 163, 'train_stop5': 50, 'test_days': 9, 'train_avg': 7, 'test_n': 4}`
- `3d`: `{'test_bad_path': 640, 'test_win': 639, 'test_stop5': 634, 'test_avg': 583, 'train_bad_path': 163, 'train_win': 73, 'train_stop5': 50, 'test_days': 12, 'test_n': 6}`
- `5d`: `{'test_bad_path': 640, 'test_stop5': 640, 'test_win': 639, 'test_avg': 625, 'train_bad_path': 134, 'train_win': 52, 'train_stop5': 48, 'test_days': 10, 'test_n': 6}`

### Beam Pruning
- `1d`: `{'attempted': 76800, 'rejected_train_n': 33654, 'expanded_survivors': 22263, 'pruned_by_beam': 21783, 'rejected_test_n': 21079, 'skipped_feature_conflict': 10214, 'skipped_duplicate': 4587, 'rejected_test_days': 1362, 'base_pool': 960, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480, 'rejected_train_days': 238}`
- `3d`: `{'attempted': 76800, 'rejected_train_n': 35940, 'expanded_survivors': 20848, 'pruned_by_beam': 20368, 'rejected_test_n': 18968, 'skipped_feature_conflict': 9025, 'skipped_duplicate': 4349, 'rejected_test_days': 1395, 'rejected_train_days': 1197, 'base_pool': 960, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480}`
- `5d`: `{'attempted': 76800, 'rejected_train_n': 38042, 'rejected_test_n': 19910, 'expanded_survivors': 19057, 'pruned_by_beam': 18577, 'skipped_feature_conflict': 9375, 'skipped_duplicate': 4137, 'rejected_test_days': 1321, 'base_pool': 960, 'rejected_train_days': 552, 'parent_beam': 480, 'next_beam': 480, 'emitted': 480}`

### Scope Diagnostics
- `KOSPI` `ranked_top20` rows=1082 days=39 predicates=220 results=960 safe=0 skip=-
- `KOSDAQ` `ranked_top20` rows=901 days=39 predicates=261 results=960 safe=0 skip=-

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.
- Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.
- Outcome and future-path columns are excluded from predicates to avoid leakage.
- Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.
