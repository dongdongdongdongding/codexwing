# Loss Exclusion Guard Mining

- generated_at: `2026-05-27T01:46:42.885174+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `4203`
- guard_count: `50213`
- production_candidate_count: `0`
- shadow_candidate_count: `2104`
- guard_levels: `{'coverage_fail': 23844, 'sample_fail': 14602, 'diagnostic': 9663, 'shadow_candidate': 2104}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 71.429 | 34.587 | -2.9134 | 6.1642 | 9.0776 | -16.5752 | 23.81 | 11.279 | conviction_score >= 64.225<br>whale_score <= 74.95 |
| 2 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3684 | 36.842 | 71.429 | 34.587 | -2.9134 | 6.1642 | 9.0776 | -16.5752 | 23.81 | 11.279 | alpha_score >= 68.75<br>conviction_score >= 64.225<br>whale_score <= 74.95 |
| 3 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3509 | 36.842 | 70.0 | 33.158 | -2.9134 | 5.9849 | 8.8983 | -16.5752 | 21.667 | 10.088 | conviction_score >= 64.225<br>priority_rank >= 12.1<br>whale_score <= 74.95 |
| 4 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3509 | 36.842 | 70.0 | 33.158 | -2.9134 | 5.9849 | 8.8983 | -16.5752 | 21.667 | 10.088 | conviction_score >= 64.225<br>core_trend_flag_bool == False<br>whale_score <= 74.95 |
| 5 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3509 | 36.842 | 70.0 | 33.158 | -2.9134 | 5.9849 | 8.8983 | -16.5752 | 21.667 | 10.088 | conviction_score >= 64.225<br>kr_universe_role == EXPLOSIVE_LEADER<br>whale_score <= 74.95 |
| 6 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3509 | 36.842 | 70.0 | 33.158 | -2.9134 | 5.9849 | 8.8983 | -16.5752 | 21.667 | 10.088 | conviction_score >= 64.225<br>explosive_leader_flag_bool == True<br>whale_score <= 74.95 |
| 7 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3509 | 36.842 | 70.0 | 33.158 | -2.9134 | 4.9435 | 7.8569 | -16.5752 | 21.667 | 10.088 | conviction_score >= 64.225<br>selection_lane == 1d<br>whale_score <= 74.95 |
| 8 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4386 | 36.842 | 68.0 | 31.158 | -2.9134 | 4.0011 | 6.9145 | -15.0342 | 22.667 | 15.088 | conviction_score >= 64.225<br>kr_universe_role == EXPLOSIVE_LEADER<br>volume_ratio <= 0.7175 |
| 9 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4386 | 36.842 | 68.0 | 31.158 | -2.9134 | 4.0011 | 6.9145 | -15.0342 | 22.667 | 15.088 | conviction_score >= 64.225<br>explosive_leader_flag_bool == True<br>volume_ratio <= 0.7175 |
| 10 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4386 | 36.842 | 68.0 | 31.158 | -2.9134 | 3.168 | 6.0814 | -15.0342 | 22.667 | 15.088 | conviction_score >= 64.225<br>selection_lane == 1d<br>volume_ratio <= 0.7175 |
| 11 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4211 | 36.842 | 70.833 | 33.991 | -2.9134 | 3.9074 | 6.8208 | -21.2895 | 16.667 | 14.255 | conviction_score >= 64.225<br>priority_rank >= 12.1<br>volume_ratio <= 0.7175 |
| 12 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.3623 | 31.884 | 64.0 | 32.116 | -0.8034 | 3.3309 | 4.1343 | -10.6927 | 25.565 | 21.333 | tech_score >= 85<br>volume_ratio <= 0.93 |
| 13 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 66.667 | 29.825 | -2.9134 | 3.2774 | 6.1908 | -21.2895 | 22.223 | 16.57 | conviction_score >= 64.225<br>volume_ratio <= 0.7175 |
| 14 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 66.667 | 29.825 | -2.9134 | 3.2774 | 6.1908 | -21.2895 | 22.223 | 16.57 | conviction_score >= 64.225<br>volume_ratio <= 0.7915 |
| 15 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4737 | 36.842 | 66.667 | 29.825 | -2.9134 | 3.2774 | 6.1908 | -21.2895 | 22.223 | 16.57 | alpha_score >= 68.75<br>conviction_score >= 64.225<br>volume_ratio <= 0.7175 |
| 16 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4386 | 36.842 | 68.0 | 31.158 | -2.9134 | 3.6133 | 6.5267 | -21.2895 | 18.667 | 15.088 | conviction_score >= 64.225<br>tech_score <= 40<br>volume_ratio <= 0.7175 |
| 17 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 65.385 | 28.543 | -2.9134 | 3.0992 | 6.0126 | -21.2895 | 20.513 | 15.857 | conviction_score >= 64.225<br>volume_ratio <= 0.8 |
| 18 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 3.5891 | 6.5025 | -21.2895 | 21.506 | 18.959 | conviction_score >= 64.225<br>decision_score >= 91 |
| 19 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.4561 | 36.842 | 65.385 | 28.543 | -2.9134 | 3.0284 | 5.9418 | -21.2895 | 20.513 | 15.857 | conviction_score >= 64.225<br>decision_score >= 98.395<br>volume_ratio <= 0.7175 |
| 20 | shadow_candidate | KOSDAQ | exception_leader | 3d | 3 | 0.3684 | 36.842 | 66.667 | 29.825 | -2.9134 | 1.4701 | 4.3835 | -21.2895 | 23.81 | 16.04 | conviction_score >= 64.225<br>priority_rank <= 2<br>volume_ratio <= 0.7175 |
| 21 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 57.143 | 20.301 | -2.9134 | 4.0331 | 6.9465 | -18.3432 | 28.572 | 16.04 | conviction_score >= 59.395<br>prob_clean >= 31.975 |
| 22 | shadow_candidate | KOSDAQ | exception_leader | 1d | 2 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | priority_rank >= 6.9<br>tech_score >= 85 |
| 23 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | alpha_score >= 68.75<br>priority_rank >= 6.9<br>tech_score >= 85 |
| 24 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | decision_score >= 98.395<br>priority_rank >= 6.9<br>tech_score >= 85 |
| 25 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | core_trend_flag_bool == False<br>priority_rank >= 6.9<br>tech_score >= 85 |
| 26 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | kr_universe_role == EXPLOSIVE_LEADER<br>priority_rank >= 6.9<br>tech_score >= 85 |
| 27 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.8672 | 3.7328 | -10.7239 | 28.571 | 15.536 | explosive_leader_flag_bool == True<br>priority_rank >= 6.9<br>tech_score >= 85 |
| 28 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 65.0 | 28.158 | -2.9134 | 3.9867 | 6.9001 | -21.2895 | 11.667 | 15.088 | conviction_score >= 59.395<br>whale_score <= 70 |
| 29 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.3875 | 46.25 | 74.194 | 27.944 | -0.8656 | 2.9038 | 3.7694 | -10.7239 | 27.419 | 13.347 | decision_score >= 98.395<br>priority_rank >= 9<br>tech_score >= 85 |
| 30 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 62.963 | 26.121 | -2.9134 | 2.8723 | 5.7857 | -21.2895 | 18.519 | 12.866 | alpha_score >= 68.75<br>volume_ratio <= 0.8 |
| 31 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 56.522 | 19.68 | -2.9134 | 3.3364 | 6.2498 | -18.3432 | 27.537 | 13.349 | conviction_score >= 64.225<br>prob_clean >= 31.975 |
| 32 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.4692 | 5.3826 | -21.2895 | 21.667 | 20.088 | volume_confirmed == False<br>volume_ratio <= 1 |
| 33 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.375 | 46.25 | 73.333 | 27.083 | -0.8656 | 2.9234 | 3.789 | -11.5587 | 26.667 | 12.917 | alpha_score <= 40.95<br>priority_rank >= 9<br>tech_score >= 85 |
| 34 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 75.0 | 28.75 | -0.8656 | 2.4178 | 3.2834 | -11.5587 | 28.571 | 8.393 | priority_rank >= 9<br>tech_score >= 85<br>theme_inference_status == blank |
| 35 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.9392 | 5.8526 | -21.2895 | 21.667 | 15.088 | alpha_score >= 68.75<br>volume_ratio <= 0.9 |
| 36 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.375 | 46.25 | 73.333 | 27.083 | -0.8656 | 2.6485 | 3.5141 | -11.5587 | 26.667 | 12.917 | conviction_score <= 45.55<br>priority_rank >= 9<br>tech_score >= 85 |
| 37 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4058 | 31.884 | 57.143 | 25.259 | -0.8034 | 2.4268 | 3.2302 | -10.6927 | 23.136 | 19.047 | alpha_score >= 84<br>volume_ratio <= 0.93 |
| 38 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 57.143 | 20.301 | -2.9134 | 3.126 | 6.0394 | -21.2895 | 20.238 | 17.231 | conviction_score >= 59.395<br>decision_score >= 91 |
| 39 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5088 | 36.842 | 62.069 | 25.227 | -2.9134 | 2.8492 | 5.7626 | -21.2895 | 14.943 | 10.95 | priority_rank >= 12.1<br>tech_score <= 54.5 |
| 40 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.5322 | 5.4456 | -21.2895 | 16.667 | 15.088 | conviction_score >= 64.225<br>tech_score <= 40 |
| 41 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3893 | 26.718 | 50.98 | 24.262 | -4.0214 | 0.2141 | 4.2355 | -30.1013 | 19.473 | 18.126 | conviction_score >= 66.375<br>volume_ratio <= 0.741 |
| 42 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 1.8369 | 4.7503 | -21.2895 | 18.28 | 12.507 | alpha_score >= 68.75<br>volume_ratio <= 0.7175 |
| 43 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 1.8369 | 4.7503 | -21.2895 | 18.28 | 12.507 | alpha_score >= 68.75<br>volume_ratio <= 0.7915 |
| 44 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.3768 | 31.884 | 53.846 | 21.962 | -0.8034 | 1.8353 | 2.6387 | -10.6927 | 23.411 | 29.487 | kr_universe_role == TRANSITIONAL<br>volume_ratio <= 0.93 |
| 45 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3586 | 39.394 | 61.972 | 22.578 | -0.8851 | 1.5397 | 2.4248 | -12.2503 | 28.823 | 23.367 | priority_rank >= 10<br>regime_volatility_20d <= 2.22 |
| 46 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3586 | 39.394 | 61.972 | 22.578 | -0.8851 | 1.5397 | 2.4248 | -12.2503 | 28.823 | 23.367 | priority_rank >= 10<br>regime_volatility_20d <= 2.4 |
| 47 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 60.87 | 24.028 | -2.9134 | 2.3915 | 5.3049 | -21.2895 | 18.841 | 13.349 | conviction_score >= 59.395<br>volume_ratio <= 0.7175 |
| 48 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 60.87 | 24.028 | -2.9134 | 2.3915 | 5.3049 | -21.2895 | 18.841 | 13.349 | conviction_score >= 59.395<br>volume_ratio <= 0.7915 |
| 49 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 71.429 | 25.179 | -0.8656 | 1.5356 | 2.4012 | -12.9528 | 28.571 | 19.107 | alpha_score <= 51.5<br>core_trend_flag_bool == False<br>priority_rank >= 6.9 |
| 50 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 71.429 | 25.179 | -0.8656 | 1.5356 | 2.4012 | -12.9528 | 28.571 | 19.107 | alpha_score <= 51.5<br>kr_universe_role == EXPLOSIVE_LEADER<br>priority_rank >= 6.9 |
| 51 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.35 | 46.25 | 71.429 | 25.179 | -0.8656 | 1.5356 | 2.4012 | -12.9528 | 28.571 | 19.107 | alpha_score <= 51.5<br>explosive_leader_flag_bool == True<br>priority_rank >= 6.9 |
| 52 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4203 | 31.884 | 55.172 | 23.288 | -0.8034 | 2.0646 | 2.868 | -10.6927 | 21.289 | 22.988 | tech_score >= 92.75<br>volume_ratio <= 0.93 |
| 53 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4203 | 31.884 | 55.172 | 23.288 | -0.8034 | 2.0646 | 2.868 | -10.6927 | 21.289 | 22.988 | tech_score >= 95<br>volume_ratio <= 0.93 |
| 54 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 59.259 | 22.417 | -2.9134 | 3.4714 | 6.3848 | -21.2895 | 14.815 | 12.866 | conviction_score >= 59.395<br>priority_rank >= 12.1 |
| 55 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 57.143 | 20.301 | -2.9134 | 2.9863 | 5.8997 | -15.0342 | 19.048 | 16.04 | selection_lane == 1d<br>volume_ratio <= 0.9 |
| 56 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 63.636 | 26.794 | -2.9134 | 2.0421 | 4.9555 | -20.2828 | 16.667 | 7.815 | volume_ratio <= 0.7175<br>whale_score <= 74.95 |
| 57 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 63.636 | 26.794 | -2.9134 | 2.0421 | 4.9555 | -20.2828 | 16.667 | 7.815 | volume_ratio <= 0.7915<br>whale_score <= 74.95 |
| 58 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.3623 | 31.884 | 56.0 | 24.116 | -0.8034 | 2.4506 | 3.254 | -10.6927 | 21.565 | 17.333 | conviction_score >= 68.8<br>volume_ratio <= 0.8 |
| 59 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.3623 | 31.884 | 56.0 | 24.116 | -0.8034 | 2.4506 | 3.254 | -10.6927 | 21.565 | 17.333 | conviction_score >= 68.8<br>volume_ratio <= 0.8575 |
| 60 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.3623 | 31.884 | 56.0 | 24.116 | -0.8034 | 2.4506 | 3.254 | -10.6927 | 21.565 | 17.333 | conviction_score >= 68.8<br>volume_ratio <= 0.79 |
| 61 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 64.286 | 27.444 | -2.9134 | 2.1146 | 5.028 | -21.2895 | 13.096 | 6.517 | priority_rank >= 12.1<br>volume_ratio <= 0.7175 |
| 62 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 64.286 | 27.444 | -2.9134 | 2.1146 | 5.028 | -21.2895 | 13.096 | 6.517 | priority_rank >= 12.1<br>volume_ratio <= 0.7915 |
| 63 | shadow_candidate | KOSDAQ | exception_leader | 1d | 2 | 0.4 | 46.25 | 71.875 | 25.625 | -0.8656 | 2.4519 | 3.3175 | -11.5587 | 25.0 | 10.625 | priority_rank >= 9<br>tech_score >= 85 |
| 64 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.4 | 46.25 | 71.875 | 25.625 | -0.8656 | 2.4519 | 3.3175 | -11.5587 | 25.0 | 10.625 | core_trend_flag_bool == False<br>priority_rank >= 9<br>tech_score >= 85 |
| 65 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.4 | 46.25 | 71.875 | 25.625 | -0.8656 | 2.4519 | 3.3175 | -11.5587 | 25.0 | 10.625 | kr_universe_role == EXPLOSIVE_LEADER<br>priority_rank >= 9<br>tech_score >= 85 |
| 66 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.4 | 46.25 | 71.875 | 25.625 | -0.8656 | 2.4519 | 3.3175 | -11.5587 | 25.0 | 10.625 | explosive_leader_flag_bool == True<br>priority_rank >= 9<br>tech_score >= 85 |
| 67 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4122 | 26.718 | 50.0 | 23.282 | -4.0214 | 0.3691 | 4.3905 | -30.1013 | 13.373 | 21.177 | priority_rank >= 10<br>volume_ratio <= 0.741 |
| 68 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5088 | 36.842 | 55.172 | 18.33 | -2.9134 | 3.0892 | 6.0026 | -18.3432 | 18.391 | 14.398 | conviction_score >= 59.395<br>core_trend_flag_bool == False |
| 69 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 64.0 | 27.158 | -2.9134 | 2.6367 | 5.5501 | -21.2895 | 10.667 | 7.088 | priority_rank >= 12.1<br>volume_ratio <= 0.8 |
| 70 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4348 | 31.884 | 56.667 | 24.783 | -0.8034 | 2.3024 | 3.1058 | -10.6927 | 19.565 | 13.333 | tech_score >= 85<br>volume_ratio <= 0.8 |
| 71 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4348 | 31.884 | 56.667 | 24.783 | -0.8034 | 2.3024 | 3.1058 | -10.6927 | 19.565 | 13.333 | tech_score >= 85<br>volume_ratio <= 0.8575 |
| 72 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4638 | 31.884 | 56.25 | 24.366 | -0.8034 | 2.5033 | 3.3067 | -10.4034 | 19.565 | 11.458 | decision == WATCHLIST_ONLY<br>volume_ratio <= 0.8 |
| 73 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4638 | 31.884 | 56.25 | 24.366 | -0.8034 | 2.5033 | 3.3067 | -10.4034 | 19.565 | 11.458 | decision == WATCHLIST_ONLY<br>volume_ratio <= 0.8575 |
| 74 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5614 | 36.842 | 59.375 | 22.533 | -2.9134 | 2.622 | 5.5354 | -21.2895 | 13.542 | 10.088 | conviction_score >= 64.225<br>priority_rank >= 12.1 |
| 75 | shadow_candidate | KOSDAQ | exception_leader | 1d | 3 | 0.3875 | 46.25 | 70.968 | 24.718 | -0.8656 | 2.4832 | 3.3488 | -11.5587 | 24.194 | 10.121 | alpha_score <= 32<br>priority_rank >= 9<br>tech_score >= 85 |
| 76 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 55.882 | 19.04 | -2.9134 | 2.2789 | 5.1923 | -21.2895 | 16.667 | 14.5 | conviction_score >= 64.225<br>decision_score >= 98.395 |
| 77 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4493 | 31.884 | 54.839 | 22.955 | -0.8034 | 2.1757 | 2.9791 | -10.6927 | 21.178 | 13.978 | tech_score >= 85<br>volume_ratio <= 0.79 |
| 78 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.374 | 26.718 | 48.98 | 22.262 | -4.0214 | 0.0103 | 4.0317 | -30.1013 | 17.152 | 17.246 | conviction_score >= 66.375<br>volume_ratio <= 0.8 |
| 79 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.374 | 26.718 | 48.98 | 22.262 | -4.0214 | 0.0103 | 4.0317 | -30.1013 | 17.152 | 17.246 | conviction_score >= 66.375<br>volume_ratio <= 0.87 |
| 80 | shadow_candidate | KOSDAQ | top5 | 1d | 2 | 0.4783 | 31.884 | 54.546 | 22.662 | -0.8034 | 2.3782 | 3.1816 | -10.4034 | 21.08 | 12.121 | decision == WATCHLIST_ONLY<br>volume_ratio <= 0.79 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=34.587 avg_delta=9.0776 :: conviction_score >= 64.225 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=34.587 avg_delta=9.0776 :: alpha_score >= 68.75 / conviction_score >= 64.225 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=33.158 avg_delta=8.8983 :: conviction_score >= 64.225 / priority_rank >= 12.1 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=33.158 avg_delta=8.8983 :: conviction_score >= 64.225 / core_trend_flag_bool == False / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=33.158 avg_delta=8.8983 :: conviction_score >= 64.225 / kr_universe_role == EXPLOSIVE_LEADER / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=33.158 avg_delta=8.8983 :: conviction_score >= 64.225 / explosive_leader_flag_bool == True / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=33.158 avg_delta=7.8569 :: conviction_score >= 64.225 / selection_lane == 1d / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=31.158 avg_delta=6.9145 :: conviction_score >= 64.225 / kr_universe_role == EXPLOSIVE_LEADER / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=31.158 avg_delta=6.9145 :: conviction_score >= 64.225 / explosive_leader_flag_bool == True / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=31.158 avg_delta=6.0814 :: conviction_score >= 64.225 / selection_lane == 1d / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4211 win_delta=33.991 avg_delta=6.8208 :: conviction_score >= 64.225 / priority_rank >= 12.1 / volume_ratio <= 0.7175
- `KOSDAQ` `top5` `1d` level=shadow_candidate retain=0.3623 win_delta=32.116 avg_delta=4.1343 :: tech_score >= 85 / volume_ratio <= 0.93
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=29.825 avg_delta=6.1908 :: conviction_score >= 64.225 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=29.825 avg_delta=6.1908 :: conviction_score >= 64.225 / volume_ratio <= 0.7915
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=29.825 avg_delta=6.1908 :: alpha_score >= 68.75 / conviction_score >= 64.225 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=31.158 avg_delta=6.5267 :: conviction_score >= 64.225 / tech_score <= 40 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4561 win_delta=28.543 avg_delta=6.0126 :: conviction_score >= 64.225 / volume_ratio <= 0.8
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5439 win_delta=24.448 avg_delta=6.5025 :: conviction_score >= 64.225 / decision_score >= 91
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4561 win_delta=28.543 avg_delta=5.9418 :: conviction_score >= 64.225 / decision_score >= 98.395 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=29.825 avg_delta=4.3835 :: conviction_score >= 64.225 / priority_rank <= 2 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=20.301 avg_delta=6.9465 :: conviction_score >= 59.395 / prob_clean >= 31.975
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: alpha_score >= 68.75 / priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: decision_score >= 98.395 / priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: core_trend_flag_bool == False / priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: kr_universe_role == EXPLOSIVE_LEADER / priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.35 win_delta=28.75 avg_delta=3.7328 :: explosive_leader_flag_bool == True / priority_rank >= 6.9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=28.158 avg_delta=6.9001 :: conviction_score >= 59.395 / whale_score <= 70
- `KOSDAQ` `exception_leader` `1d` level=shadow_candidate retain=0.3875 win_delta=27.944 avg_delta=3.7694 :: decision_score >= 98.395 / priority_rank >= 9 / tech_score >= 85
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=26.121 avg_delta=5.7857 :: alpha_score >= 68.75 / volume_ratio <= 0.8

## Diagnostics

- `KOSPI` `top5` rows=395 days=39 cut=2026-05-11 predicates=164 levels={'coverage_fail': 4735, 'diagnostic': 1438, 'sample_fail': 1248, 'shadow_candidate': 307}
- `KOSPI` `exception_leader` rows=60 days=12 cut=2026-04-16 predicates=0 levels={}
- `KOSPI` `top5_exception` rows=455 days=39 cut=2026-05-11 predicates=179 levels={'coverage_fail': 5015, 'diagnostic': 1744, 'sample_fail': 931, 'shadow_candidate': 392}
- `KOSPI` `ranked_top20` rows=981 days=39 cut=2026-05-11 predicates=222 levels={'coverage_fail': 4778, 'sample_fail': 1787, 'diagnostic': 1505, 'shadow_candidate': 275}
- `KOSDAQ` `top5` rows=284 days=39 cut=2026-05-11 predicates=196 levels={'coverage_fail': 2154, 'sample_fail': 2056, 'diagnostic': 1344, 'shadow_candidate': 264}
- `KOSDAQ` `exception_leader` rows=219 days=27 cut=2026-05-13 predicates=105 levels={'coverage_fail': 1637, 'sample_fail': 1316, 'diagnostic': 1110, 'shadow_candidate': 495}
- `KOSDAQ` `top5_exception` rows=503 days=39 cut=2026-05-11 predicates=220 levels={'sample_fail': 3651, 'coverage_fail': 2371, 'diagnostic': 1565, 'shadow_candidate': 226}
- `KOSDAQ` `ranked_top20` rows=835 days=39 cut=2026-05-11 predicates=251 levels={'sample_fail': 3613, 'coverage_fail': 3154, 'diagnostic': 957, 'shadow_candidate': 145}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
