# Loss Exclusion Guard Mining

- generated_at: `2026-05-27T01:51:21.900813+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `4203`
- guard_count: `525`
- production_candidate_count: `0`
- shadow_candidate_count: `114`
- guard_levels: `{'sample_fail': 199, 'shadow_candidate': 114, 'coverage_fail': 108, 'diagnostic': 104}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 71.429 | 34.587 | -2.9134 | 6.1642 | 9.0776 | -16.5752 | 23.81 | 11.279 | conviction_score >= 64.225<br>whale_score <= 74.95 |
| 2 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 66.667 | 29.825 | -2.9134 | 3.2774 | 6.1908 | -21.2895 | 22.223 | 16.57 | conviction_score >= 64.225<br>volume_ratio <= 0.7175 |
| 3 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 66.667 | 29.825 | -2.9134 | 3.2774 | 6.1908 | -21.2895 | 22.223 | 16.57 | conviction_score >= 64.225<br>volume_ratio <= 0.7915 |
| 4 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 65.385 | 28.543 | -2.9134 | 3.0992 | 6.0126 | -21.2895 | 20.513 | 15.857 | conviction_score >= 64.225<br>volume_ratio <= 0.8 |
| 5 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 3.5891 | 6.5025 | -21.2895 | 21.506 | 18.959 | conviction_score >= 64.225<br>decision_score >= 91 |
| 6 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 57.143 | 20.301 | -2.9134 | 4.0331 | 6.9465 | -18.3432 | 28.572 | 16.04 | conviction_score >= 59.395<br>prob_clean >= 31.975 |
| 7 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 65.0 | 28.158 | -2.9134 | 3.9867 | 6.9001 | -21.2895 | 11.667 | 15.088 | conviction_score >= 59.395<br>whale_score <= 70 |
| 8 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 62.963 | 26.121 | -2.9134 | 2.8723 | 5.7857 | -21.2895 | 18.519 | 12.866 | alpha_score >= 68.75<br>volume_ratio <= 0.8 |
| 9 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 56.522 | 19.68 | -2.9134 | 3.3364 | 6.2498 | -18.3432 | 27.537 | 13.349 | conviction_score >= 64.225<br>prob_clean >= 31.975 |
| 10 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.9392 | 5.8526 | -21.2895 | 21.667 | 15.088 | alpha_score >= 68.75<br>volume_ratio <= 0.9 |
| 11 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 57.143 | 20.301 | -2.9134 | 3.126 | 6.0394 | -21.2895 | 20.238 | 17.231 | conviction_score >= 59.395<br>decision_score >= 91 |
| 12 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5088 | 36.842 | 62.069 | 25.227 | -2.9134 | 2.8492 | 5.7626 | -21.2895 | 14.943 | 10.95 | priority_rank >= 12.1<br>tech_score <= 54.5 |
| 13 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.5322 | 5.4456 | -21.2895 | 16.667 | 15.088 | conviction_score >= 64.225<br>tech_score <= 40 |
| 14 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 1.8369 | 4.7503 | -21.2895 | 18.28 | 12.507 | alpha_score >= 68.75<br>volume_ratio <= 0.7175 |
| 15 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 61.29 | 24.448 | -2.9134 | 1.8369 | 4.7503 | -21.2895 | 18.28 | 12.507 | alpha_score >= 68.75<br>volume_ratio <= 0.7915 |
| 16 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 60.87 | 24.028 | -2.9134 | 2.3915 | 5.3049 | -21.2895 | 18.841 | 13.349 | conviction_score >= 59.395<br>volume_ratio <= 0.7175 |
| 17 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4035 | 36.842 | 60.87 | 24.028 | -2.9134 | 2.3915 | 5.3049 | -21.2895 | 18.841 | 13.349 | conviction_score >= 59.395<br>volume_ratio <= 0.7915 |
| 18 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 59.259 | 22.417 | -2.9134 | 3.4714 | 6.3848 | -21.2895 | 14.815 | 12.866 | conviction_score >= 59.395<br>priority_rank >= 12.1 |
| 19 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 63.636 | 26.794 | -2.9134 | 2.0421 | 4.9555 | -20.2828 | 16.667 | 7.815 | volume_ratio <= 0.7175<br>whale_score <= 74.95 |
| 20 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 63.636 | 26.794 | -2.9134 | 2.0421 | 4.9555 | -20.2828 | 16.667 | 7.815 | volume_ratio <= 0.7915<br>whale_score <= 74.95 |
| 21 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 64.286 | 27.444 | -2.9134 | 2.1146 | 5.028 | -21.2895 | 13.096 | 6.517 | priority_rank >= 12.1<br>volume_ratio <= 0.7175 |
| 22 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 64.286 | 27.444 | -2.9134 | 2.1146 | 5.028 | -21.2895 | 13.096 | 6.517 | priority_rank >= 12.1<br>volume_ratio <= 0.7915 |
| 23 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 64.0 | 27.158 | -2.9134 | 2.6367 | 5.5501 | -21.2895 | 10.667 | 7.088 | priority_rank >= 12.1<br>volume_ratio <= 0.8 |
| 24 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5614 | 36.842 | 59.375 | 22.533 | -2.9134 | 2.622 | 5.5354 | -21.2895 | 13.542 | 10.088 | conviction_score >= 64.225<br>priority_rank >= 12.1 |
| 25 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 55.882 | 19.04 | -2.9134 | 2.2789 | 5.1923 | -21.2895 | 16.667 | 14.5 | conviction_score >= 64.225<br>decision_score >= 98.395 |
| 26 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 64.0 | 27.158 | -2.9134 | 1.2476 | 4.161 | -21.2895 | 10.667 | 11.088 | volume_ratio <= 0.7175<br>whale_score <= 70 |
| 27 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 64.0 | 27.158 | -2.9134 | 1.2476 | 4.161 | -21.2895 | 10.667 | 11.088 | volume_ratio <= 0.7915<br>whale_score <= 70 |
| 28 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 59.091 | 22.249 | -2.9134 | 2.1406 | 5.054 | -21.2895 | 16.667 | 12.361 | conviction_score >= 59.395<br>volume_ratio <= 0.8 |
| 29 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 61.905 | 25.063 | -2.9134 | 2.02 | 4.9334 | -20.2828 | 14.286 | 6.517 | volume_ratio <= 0.8<br>whale_score <= 74.95 |
| 30 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.1393 | 5.0527 | -21.2895 | 11.667 | 15.088 | volume_ratio <= 0.9<br>whale_score <= 57.5 |
| 31 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4211 | 36.842 | 58.333 | 21.491 | -2.9134 | 1.6012 | 4.5146 | -21.2895 | 16.667 | 10.088 | conviction_score >= 59.395<br>volume_ratio <= 0.6 |
| 32 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 54.546 | 17.704 | -2.9134 | 3.6621 | 6.5755 | -18.3432 | 16.667 | 7.815 | priority_rank >= 12.1<br>prob_clean >= 31.975 |
| 33 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 60.0 | 23.158 | -2.9134 | 2.9547 | 5.8681 | -21.1454 | 14.667 | -0.912 | priority_rank >= 12.1<br>whale_score <= 74.95 |
| 34 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4211 | 36.842 | 62.5 | 25.658 | -2.9134 | 1.1952 | 4.1086 | -21.2895 | 8.334 | 10.088 | volume_ratio <= 0.8<br>whale_score <= 70 |
| 35 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 57.143 | 20.301 | -2.9134 | 1.3876 | 4.301 | -21.2895 | 14.286 | 16.04 | conviction_score <= 45.55<br>volume_ratio <= 0.9 |
| 36 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 58.064 | 21.222 | -2.9134 | 2.0985 | 5.0119 | -21.2895 | 11.828 | 6.056 | priority_rank >= 12.1<br>tech_score <= 40 |
| 37 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 53.846 | 17.004 | -2.9134 | 0.8863 | 3.7997 | -21.2895 | 16.667 | 19.703 | prob_clean >= 33.7<br>tech_score <= 54.5 |
| 38 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 54.546 | 17.704 | -2.9134 | 1.2612 | 4.1746 | -21.2895 | 16.667 | 16.906 | theme_inference_status == blank<br>volume_ratio <= 0.9 |
| 39 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 52.381 | 15.539 | -2.9134 | 1.0777 | 3.9911 | -21.2346 | 19.048 | 20.802 | prob_clean >= 31.975<br>tech_score <= 54.5 |
| 40 | shadow_candidate | KOSDAQ | exception_leader | 3d | 1 | 0.3509 | 36.842 | 50.0 | 13.158 | -2.9134 | 2.8306 | 5.744 | -21.2346 | 16.667 | 20.088 | loss_risk_score <= 30.7196 |
| 41 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 54.546 | 17.704 | -2.9134 | 0.4581 | 3.3715 | -21.2895 | 16.667 | 16.906 | prob_clean >= 33.7<br>volume_ratio <= 0.8 |
| 42 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 48.0 | 11.158 | -2.9134 | 2.6896 | 5.603 | -17.8527 | 18.667 | 15.088 | decision_score >= 88<br>prob_clean >= 31.975 |
| 43 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 48.0 | 11.158 | -2.9134 | 2.6896 | 5.603 | -17.8527 | 18.667 | 15.088 | decision_score >= 91<br>prob_clean >= 31.975 |
| 44 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 51.613 | 14.771 | -2.9134 | 1.7339 | 4.6473 | -21.2895 | 15.054 | 12.507 | conviction_score >= 59.395<br>decision_score >= 98.395 |
| 45 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4211 | 36.842 | 58.333 | 21.491 | -2.9134 | 1.42 | 4.3334 | -20.2828 | 12.5 | 1.755 | tech_score <= 54.5<br>whale_score <= 74.95 |
| 46 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4912 | 36.842 | 57.143 | 20.301 | -2.9134 | 2.5368 | 5.4502 | -21.1454 | 13.096 | -4.198 | alpha_score >= 68.75<br>whale_score <= 74.95 |
| 47 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 53.846 | 17.004 | -2.9134 | 1.6339 | 4.5473 | -21.2895 | 12.821 | 12.011 | conviction_score >= 59.395<br>tech_score <= 40 |
| 48 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 52.381 | 15.539 | -2.9134 | 1.5082 | 4.4216 | -21.2895 | 14.286 | 16.04 | decision_score >= 98.395<br>volume_ratio <= 0.9 |
| 49 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4211 | 36.842 | 58.333 | 21.491 | -2.9134 | 0.9519 | 3.8653 | -20.2828 | 12.5 | 1.755 | volume_ratio <= 0.6<br>whale_score <= 74.95 |
| 50 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 53.846 | 17.004 | -2.9134 | -0.405 | 2.5084 | -21.2895 | 16.667 | 15.857 | prob_clean >= 33.7<br>volume_ratio <= 0.7175 |
| 51 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4561 | 36.842 | 53.846 | 17.004 | -2.9134 | -0.405 | 2.5084 | -21.2895 | 16.667 | 15.857 | prob_clean >= 33.7<br>volume_ratio <= 0.7915 |
| 52 | shadow_candidate | KOSDAQ | exception_leader | 3d | 1 | 0.4035 | 36.842 | 52.174 | 15.332 | -2.9134 | 0.8778 | 3.7912 | -21.2895 | 14.493 | 17.697 | volume_ratio <= 0.9 |
| 53 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 52.381 | 15.539 | -2.9134 | 0.0323 | 2.9457 | -21.2346 | 19.048 | 16.04 | prob_clean >= 31.975<br>volume_ratio <= 0.7175 |
| 54 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 52.381 | 15.539 | -2.9134 | 0.0323 | 2.9457 | -21.2346 | 19.048 | 16.04 | prob_clean >= 31.975<br>volume_ratio <= 0.7915 |
| 55 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4737 | 36.842 | 59.259 | 22.417 | -2.9134 | 0.7535 | 3.6669 | -21.2895 | 7.408 | 5.458 | tech_score <= 54.5<br>whale_score <= 70 |
| 56 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 58.064 | 21.222 | -2.9134 | 1.0773 | 3.9907 | -21.2895 | 8.603 | 2.83 | priority_rank >= 12.1<br>volume_ratio <= 0.6 |
| 57 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3509 | 36.842 | 55.0 | 18.158 | -2.9134 | 3.3839 | 6.2973 | -21.1454 | 16.667 | -9.912 | prob_clean >= 33.7<br>whale_score <= 74.95 |
| 58 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | 0.2455 | 3.1589 | -21.2895 | 10.785 | 14.5 | decision_score >= 88<br>tech_score <= 54.5 |
| 59 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | 0.2455 | 3.1589 | -21.2895 | 10.785 | 14.5 | decision_score >= 91<br>tech_score <= 54.5 |
| 60 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 56.667 | 19.825 | -2.9134 | 1.2685 | 4.1819 | -21.2895 | 6.667 | 5.088 | priority_rank >= 12.1<br>whale_score <= 70 |
| 61 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5789 | 36.842 | 54.546 | 17.704 | -2.9134 | -0.4114 | 2.502 | -21.2895 | 9.091 | 13.876 | tech_score <= 54.5<br>volume_ratio <= 0.7175 |
| 62 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5789 | 36.842 | 54.546 | 17.704 | -2.9134 | -0.4114 | 2.502 | -21.2895 | 9.091 | 13.876 | tech_score <= 54.5<br>volume_ratio <= 0.7915 |
| 63 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.6316 | 36.842 | 52.778 | 15.936 | -2.9134 | -0.3024 | 2.611 | -21.2895 | 11.111 | 12.866 | conviction_score <= 45.55<br>tech_score <= 54.5 |
| 64 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 56.667 | 19.825 | -2.9134 | 0.2545 | 3.1679 | -21.2895 | 6.667 | 8.421 | volume_ratio <= 0.8<br>whale_score <= 57.5 |
| 65 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 52.381 | 15.539 | -2.9134 | 1.0491 | 3.9625 | -21.2895 | 9.524 | 16.04 | tech_score <= 40<br>volume_ratio <= 0.9 |
| 66 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 55.882 | 19.04 | -2.9134 | -0.3815 | 2.5319 | -21.2895 | 7.844 | 8.617 | volume_ratio <= 0.7175<br>whale_score <= 57.5 |
| 67 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 55.882 | 19.04 | -2.9134 | -0.3815 | 2.5319 | -21.2895 | 7.844 | 8.617 | volume_ratio <= 0.7915<br>whale_score <= 57.5 |
| 68 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.386 | 36.842 | 50.0 | 13.158 | -2.9134 | -0.1389 | 2.7745 | -21.2346 | 16.667 | 16.906 | prob_clean >= 31.975<br>volume_ratio <= 0.6 |
| 69 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.6667 | 36.842 | 52.632 | 15.79 | -2.9134 | 1.2565 | 4.1699 | -21.2895 | 8.772 | 3.509 | decision_score >= 98.395<br>priority_rank >= 12.1 |
| 70 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 53.333 | 16.491 | -2.9134 | -0.0863 | 2.8271 | -21.2895 | 10.0 | 11.755 | decision_score >= 88<br>volume_ratio <= 0.8 |
| 71 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5263 | 36.842 | 53.333 | 16.491 | -2.9134 | -0.0863 | 2.8271 | -21.2895 | 10.0 | 11.755 | decision_score >= 91<br>volume_ratio <= 0.8 |
| 72 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4386 | 36.842 | 56.0 | 19.158 | -2.9134 | 0.8126 | 3.726 | -20.2828 | 10.667 | -0.912 | tech_score <= 40<br>whale_score <= 74.95 |
| 73 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5088 | 36.842 | 51.724 | 14.882 | -2.9134 | 1.4727 | 4.3861 | -21.2895 | 11.495 | 4.054 | priority_rank >= 12.1<br>prob_clean >= 33.7 |
| 74 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | -0.6823 | 2.2311 | -21.2895 | 10.785 | 11.559 | decision_score >= 88<br>volume_ratio <= 0.7175 |
| 75 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | -0.6823 | 2.2311 | -21.2895 | 10.785 | 11.559 | decision_score >= 91<br>volume_ratio <= 0.7175 |
| 76 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | -0.6823 | 2.2311 | -21.2895 | 10.785 | 11.559 | decision_score >= 88<br>volume_ratio <= 0.7915 |
| 77 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5965 | 36.842 | 52.941 | 16.099 | -2.9134 | -0.6823 | 2.2311 | -21.2895 | 10.785 | 11.559 | decision_score >= 91<br>volume_ratio <= 0.7915 |
| 78 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5439 | 36.842 | 54.839 | 17.997 | -2.9134 | -0.4418 | 2.4716 | -21.2895 | 8.603 | 9.282 | conviction_score <= 45.55<br>volume_ratio <= 0.8 |
| 79 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.6316 | 36.842 | 52.778 | 15.936 | -2.9134 | -0.1139 | 2.7995 | -21.2895 | 8.334 | 10.088 | tech_score <= 54.5<br>whale_score <= 57.5 |
| 80 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.614 | 36.842 | 54.286 | 17.444 | -2.9134 | -0.9801 | 1.9333 | -21.2895 | 9.524 | 9.374 | conviction_score <= 45.55<br>volume_ratio <= 0.7175 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=34.587 avg_delta=9.0776 :: conviction_score >= 64.225 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=29.825 avg_delta=6.1908 :: conviction_score >= 64.225 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=29.825 avg_delta=6.1908 :: conviction_score >= 64.225 / volume_ratio <= 0.7915
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4561 win_delta=28.543 avg_delta=6.0126 :: conviction_score >= 64.225 / volume_ratio <= 0.8
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5439 win_delta=24.448 avg_delta=6.5025 :: conviction_score >= 64.225 / decision_score >= 91
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=20.301 avg_delta=6.9465 :: conviction_score >= 59.395 / prob_clean >= 31.975
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=28.158 avg_delta=6.9001 :: conviction_score >= 59.395 / whale_score <= 70
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=26.121 avg_delta=5.7857 :: alpha_score >= 68.75 / volume_ratio <= 0.8
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4035 win_delta=19.68 avg_delta=6.2498 :: conviction_score >= 64.225 / prob_clean >= 31.975
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=23.158 avg_delta=5.8526 :: alpha_score >= 68.75 / volume_ratio <= 0.9
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4912 win_delta=20.301 avg_delta=6.0394 :: conviction_score >= 59.395 / decision_score >= 91
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5088 win_delta=25.227 avg_delta=5.7626 :: priority_rank >= 12.1 / tech_score <= 54.5
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5263 win_delta=23.158 avg_delta=5.4456 :: conviction_score >= 64.225 / tech_score <= 40
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5439 win_delta=24.448 avg_delta=4.7503 :: alpha_score >= 68.75 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5439 win_delta=24.448 avg_delta=4.7503 :: alpha_score >= 68.75 / volume_ratio <= 0.7915
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4035 win_delta=24.028 avg_delta=5.3049 :: conviction_score >= 59.395 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4035 win_delta=24.028 avg_delta=5.3049 :: conviction_score >= 59.395 / volume_ratio <= 0.7915
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4737 win_delta=22.417 avg_delta=6.3848 :: conviction_score >= 59.395 / priority_rank >= 12.1
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.386 win_delta=26.794 avg_delta=4.9555 :: volume_ratio <= 0.7175 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.386 win_delta=26.794 avg_delta=4.9555 :: volume_ratio <= 0.7915 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4912 win_delta=27.444 avg_delta=5.028 :: priority_rank >= 12.1 / volume_ratio <= 0.7175
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4912 win_delta=27.444 avg_delta=5.028 :: priority_rank >= 12.1 / volume_ratio <= 0.7915
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=27.158 avg_delta=5.5501 :: priority_rank >= 12.1 / volume_ratio <= 0.8
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5614 win_delta=22.533 avg_delta=5.5354 :: conviction_score >= 64.225 / priority_rank >= 12.1
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5965 win_delta=19.04 avg_delta=5.1923 :: conviction_score >= 64.225 / decision_score >= 98.395
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=27.158 avg_delta=4.161 :: volume_ratio <= 0.7175 / whale_score <= 70
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4386 win_delta=27.158 avg_delta=4.161 :: volume_ratio <= 0.7915 / whale_score <= 70
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.386 win_delta=22.249 avg_delta=5.054 :: conviction_score >= 59.395 / volume_ratio <= 0.8
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3684 win_delta=25.063 avg_delta=4.9334 :: volume_ratio <= 0.8 / whale_score <= 74.95
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3509 win_delta=23.158 avg_delta=5.0527 :: volume_ratio <= 0.9 / whale_score <= 57.5

## Diagnostics

- `KOSDAQ` `exception_leader` rows=219 days=27 cut=2026-05-13 predicates=105 levels={'sample_fail': 199, 'shadow_candidate': 114, 'coverage_fail': 108, 'diagnostic': 104}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
