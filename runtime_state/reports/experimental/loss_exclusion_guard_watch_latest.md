# Loss Exclusion Guard Mining

- generated_at: `2026-06-29T07:03:39.549663+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `5402`
- quality_scope: `all`
- guard_count: `649`
- production_candidate_count: `0`
- shadow_candidate_count: `19`
- guard_levels: `{'coverage_fail': 347, 'diagnostic': 213, 'sample_fail': 70, 'shadow_candidate': 19}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3804 | 36.956 | 62.857 | 25.901 | -2.6251 | 5.3977 | 8.0228 | -18.5849 | 14.721 | -2.764 | conviction_score >= 66.9<br>volume_ratio >= 1.8685 |
| 2 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4022 | 36.956 | 59.459 | 22.503 | -2.6251 | 3.7236 | 6.3487 | -38.1162 | 12.867 | -0.91 | conviction_score >= 66.9<br>volume_ratio >= 2 |
| 3 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3587 | 36.956 | 57.576 | 20.62 | -2.6251 | 2.6268 | 5.2519 | -18.8406 | 13.768 | 1.219 | conviction_score >= 68.25<br>volume_ratio >= 1.4075 |
| 4 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3587 | 36.956 | 57.576 | 20.62 | -2.6251 | 2.6268 | 5.2519 | -18.8406 | 13.768 | 1.219 | conviction_score >= 68.25<br>volume_ratio >= 1.5 |
| 5 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3804 | 36.956 | 54.286 | 17.33 | -2.6251 | 3.0118 | 5.6369 | -23.0603 | 11.864 | -2.764 | conviction_score >= 63.3<br>volume_ratio >= 3 |
| 6 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5652 | 36.956 | 51.923 | 14.967 | -2.6251 | 1.6033 | 4.2284 | -38.1162 | 9.281 | 0.753 | conviction_score >= 66.9<br>volume_ratio >= 3 |
| 7 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.4457 | 36.956 | 48.78 | 11.824 | -2.6251 | 1.3754 | 4.0005 | -23.0603 | 7.264 | -0.185 | conviction_score >= 63.3 |
| 8 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.3587 | 36.956 | 45.454 | 8.498 | -2.6251 | 0.2265 | 2.8516 | -15.0895 | 10.738 | -1.811 | volume_ratio >= 0.9 |
| 9 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.375 | 41.346 | 51.282 | 9.936 | 0.5832 | 3.3881 | 2.8049 | -20.0301 | 12.5 | 0.321 | feature_quality == complete<br>volume_ratio >= 1 |
| 10 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.375 | 41.346 | 51.282 | 9.936 | 0.5832 | 3.3881 | 2.8049 | -20.0301 | 12.5 | 0.321 | feature_origin == scanner_full<br>volume_ratio >= 1 |
| 11 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4327 | 41.346 | 51.111 | 9.765 | 0.5832 | 3.3697 | 2.7865 | -20.9302 | 10.62 | -1.902 | feature_quality == complete<br>volume_ratio >= 1.183 |
| 12 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4327 | 41.346 | 51.111 | 9.765 | 0.5832 | 3.3697 | 2.7865 | -20.9302 | 10.62 | -1.902 | feature_origin == scanner_full<br>volume_ratio >= 1.183 |
| 13 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4327 | 41.346 | 51.111 | 9.765 | 0.5832 | 3.3697 | 2.7865 | -20.9302 | 10.62 | -1.902 | feature_quality == complete<br>volume_ratio >= 1.2 |
| 14 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4327 | 41.346 | 51.111 | 9.765 | 0.5832 | 3.3697 | 2.7865 | -20.9302 | 10.62 | -1.902 | feature_origin == scanner_full<br>volume_ratio >= 1.2 |
| 15 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5385 | 41.346 | 51.786 | 10.44 | 0.5832 | 2.6018 | 2.0186 | -20.9302 | 6.731 | 1.511 | feature_quality == complete<br>volume_ratio >= 1.4075 |
| 16 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5385 | 41.346 | 51.786 | 10.44 | 0.5832 | 2.6018 | 2.0186 | -20.9302 | 6.731 | 1.511 | feature_origin == scanner_full<br>volume_ratio >= 1.4075 |
| 17 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.663 | 36.956 | 45.902 | 8.946 | -2.6251 | -0.1324 | 2.4927 | -38.1162 | 5.025 | 0.374 | conviction_score >= 66.9 |
| 18 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.7283 | 36.956 | 43.284 | 6.328 | -2.6251 | -0.9637 | 1.6614 | -38.1162 | 2.823 | -1.314 | conviction_score >= 68.25 |
| 19 | shadow_candidate | KOSDAQ | exception_leader | 3d | 1 | 0.4615 | 41.346 | 45.833 | 4.487 | 0.5832 | 2.6587 | 2.0755 | -24.5039 | 6.731 | -1.763 | conviction_score >= 63.3 |
| 20 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.087 | 36.956 | 75.0 | 38.044 | -2.6251 | 8.41 | 11.0351 | -1.1236 | 30.435 | 19.022 | conviction_score >= 66.9<br>volume_ratio >= 0.7 |
| 21 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 80.0 | 43.044 | -2.6251 | 7.1845 | 9.8096 | -9.7059 | 20.435 | 11.522 | priority_rank <= 4.85<br>volume_ratio >= 0.7 |
| 22 | sample_fail | KOSDAQ | exception_leader | 5d | 1 | 0.0978 | 36.956 | 77.778 | 40.822 | -2.6251 | 15.5165 | 18.1416 | -12.3288 | 13.768 | -35.145 | market_gate == GREEN |
| 23 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 2.9078 | 5.5329 | -9.7059 | 25.889 | 22.431 | tech_score >= 55<br>volume_ratio >= 1.183 |
| 24 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 2.9078 | 5.5329 | -9.7059 | 25.889 | 22.431 | tech_score >= 55<br>volume_ratio >= 1.2 |
| 25 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 2.9078 | 5.5329 | -9.7059 | 25.889 | 22.431 | tech_score >= 55<br>volume_ratio >= 1 |
| 26 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 2.9078 | 5.5329 | -9.7059 | 25.889 | 22.431 | tech_score >= 55<br>volume_ratio >= 0.9 |
| 27 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1413 | 36.956 | 69.231 | 32.275 | -2.6251 | 5.6995 | 8.3246 | -9.7059 | 18.897 | 16.137 | priority_rank <= 4.85<br>volume_ratio >= 0.8 |
| 28 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.087 | 36.956 | 75.0 | 38.044 | -2.6251 | 2.9214 | 5.5465 | -9.7059 | 17.935 | 19.022 | tech_score >= 55<br>volume_ratio >= 0.7 |
| 29 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 80.0 | 43.044 | -2.6251 | 4.2389 | 6.864 | -9.0495 | 10.435 | 1.522 | alpha_score >= 57<br>volume_ratio >= 0.7 |
| 30 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 70.0 | 33.044 | -2.6251 | 3.0333 | 5.6584 | -9.7059 | 20.435 | 21.522 | tech_score >= 55<br>volume_ratio >= 0.8 |
| 31 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1848 | 36.956 | 70.588 | 33.632 | -2.6251 | 6.2223 | 8.8474 | -9.7059 | 15.729 | 2.11 | priority_rank <= 4.85<br>volume_ratio >= 1.183 |
| 32 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1848 | 36.956 | 70.588 | 33.632 | -2.6251 | 6.2223 | 8.8474 | -9.7059 | 15.729 | 2.11 | priority_rank <= 4.85<br>volume_ratio >= 1.2 |
| 33 | sample_fail | KOSDAQ | exception_leader | 3d | 1 | 0.1058 | 41.346 | 63.636 | 22.29 | 0.5832 | 19.3966 | 18.8134 | -13.8448 | 18.095 | -20.892 | market_gate == GREEN |
| 34 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.163 | 36.956 | 66.667 | 29.711 | -2.6251 | 5.5438 | 8.1689 | -9.7059 | 20.435 | 11.522 | priority_rank <= 4.85<br>volume_ratio >= 1 |
| 35 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.163 | 36.956 | 66.667 | 29.711 | -2.6251 | 5.5438 | 8.1689 | -9.7059 | 20.435 | 11.522 | priority_rank <= 4.85<br>volume_ratio >= 0.9 |
| 36 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 70.0 | 33.044 | -2.6251 | 1.3317 | 3.9568 | -6.7967 | 30.435 | 11.522 | loss_risk_score >= 24.1345<br>volume_ratio >= 1 |
| 37 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.25 | 36.956 | 65.217 | 28.261 | -2.6251 | 6.5674 | 9.1925 | -15.0895 | 23.913 | 1.087 | conviction_score >= 66.9<br>volume_ratio >= 1.183 |
| 38 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.25 | 36.956 | 65.217 | 28.261 | -2.6251 | 6.5674 | 9.1925 | -15.0895 | 23.913 | 1.087 | conviction_score >= 66.9<br>volume_ratio >= 1.2 |
| 39 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1522 | 36.956 | 64.286 | 27.33 | -2.6251 | 6.1055 | 8.7306 | -15.0895 | 30.435 | -4.192 | conviction_score >= 63.3<br>volume_ratio >= 1.183 |
| 40 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1522 | 36.956 | 64.286 | 27.33 | -2.6251 | 6.1055 | 8.7306 | -15.0895 | 30.435 | -4.192 | conviction_score >= 63.3<br>volume_ratio >= 1.2 |
| 41 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 1.2927 | 3.9178 | -6.7967 | 25.889 | 4.249 | loss_risk_score >= 24.1345<br>volume_ratio >= 1.183 |
| 42 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 72.727 | 35.771 | -2.6251 | 1.2927 | 3.9178 | -6.7967 | 25.889 | 4.249 | loss_risk_score >= 24.1345<br>volume_ratio >= 1.2 |
| 43 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.2174 | 36.956 | 65.0 | 28.044 | -2.6251 | 4.7171 | 7.3422 | -15.0895 | 25.435 | 1.522 | conviction_score >= 66.9<br>volume_ratio >= 1 |
| 44 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 70.0 | 33.044 | -2.6251 | 0.903 | 3.5281 | -18.5849 | 20.435 | 21.522 | alpha_score >= 50.7<br>volume_ratio >= 1.4075 |
| 45 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 70.0 | 33.044 | -2.6251 | 0.903 | 3.5281 | -18.5849 | 20.435 | 21.522 | alpha_score >= 50.7<br>volume_ratio >= 1.5 |
| 46 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.25 | 36.956 | 65.217 | 28.261 | -2.6251 | 6.4899 | 9.115 | -18.5849 | 19.565 | -7.608 | conviction_score >= 63.3<br>volume_ratio >= 1.8685 |
| 47 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.25 | 36.956 | 65.217 | 28.261 | -2.6251 | 6.4899 | 9.115 | -18.5849 | 19.565 | -7.608 | conviction_score >= 63.3<br>volume_ratio >= 2 |
| 48 | coverage_fail | KOSDAQ | exception_leader | 3d | 2 | 0.0865 | 41.346 | 66.667 | 25.321 | 0.5832 | 5.712 | 5.1288 | -6.8182 | 26.175 | 22.543 | loss_risk_score >= 20.442<br>tech_score >= 55 |
| 49 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 63.636 | 26.68 | -2.6251 | 4.3579 | 6.983 | -9.7059 | 16.799 | 13.34 | priority_rank <= 6<br>volume_ratio >= 1.183 |
| 50 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 63.636 | 26.68 | -2.6251 | 4.3579 | 6.983 | -9.7059 | 16.799 | 13.34 | priority_rank <= 5<br>volume_ratio >= 1.183 |
| 51 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 63.636 | 26.68 | -2.6251 | 4.3579 | 6.983 | -9.7059 | 16.799 | 13.34 | priority_rank <= 6<br>volume_ratio >= 1.2 |
| 52 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 63.636 | 26.68 | -2.6251 | 4.3579 | 6.983 | -9.7059 | 16.799 | 13.34 | priority_rank <= 5<br>volume_ratio >= 1.2 |
| 53 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | 0.9338 | 3.5589 | -6.7967 | 24.879 | 9.3 | loss_risk_score >= 20.442<br>volume_ratio >= 1.183 |
| 54 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | 0.9338 | 3.5589 | -6.7967 | 24.879 | 9.3 | loss_risk_score >= 20.442<br>volume_ratio >= 1.2 |
| 55 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | 0.9338 | 3.5589 | -6.7967 | 24.879 | 9.3 | loss_risk_score >= 20.442<br>volume_ratio >= 1 |
| 56 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | 0.9338 | 3.5589 | -6.7967 | 24.879 | 9.3 | loss_risk_score >= 24.1345<br>volume_ratio >= 0.9 |
| 57 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | 0.9338 | 3.5589 | -6.7967 | 24.879 | 9.3 | loss_risk_score >= 20.442<br>volume_ratio >= 0.9 |
| 58 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 6<br>volume_ratio >= 1 |
| 59 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 6<br>volume_ratio >= 0.8 |
| 60 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 6<br>volume_ratio >= 0.9 |
| 61 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 5<br>volume_ratio >= 1 |
| 62 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 5<br>volume_ratio >= 0.8 |
| 63 | sample_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 55.556 | 18.6 | -2.6251 | 2.8127 | 5.4378 | -9.7059 | 24.879 | 31.522 | priority_rank <= 5<br>volume_ratio >= 0.9 |
| 64 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1087 | 36.956 | 70.0 | 33.044 | -2.6251 | 3.3685 | 5.9936 | -18.5849 | 0.435 | 21.522 | conviction_score >= 63.3<br>ml_prob <= 37.2 |
| 65 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1957 | 36.956 | 61.111 | 24.155 | -2.6251 | 4.0111 | 6.6362 | -15.0895 | 24.879 | 3.744 | conviction_score >= 66.9<br>volume_ratio >= 0.9 |
| 66 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.3152 | 36.956 | 62.069 | 25.113 | -2.6251 | 4.1182 | 6.7433 | -18.5849 | 18.366 | 7.384 | conviction_score >= 66.9<br>volume_ratio >= 1.4075 |
| 67 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.3152 | 36.956 | 62.069 | 25.113 | -2.6251 | 4.1182 | 6.7433 | -18.5849 | 18.366 | 7.384 | conviction_score >= 66.9<br>volume_ratio >= 1.5 |
| 68 | sample_fail | KOSDAQ | exception_leader | 5d | 1 | 0.0761 | 36.956 | 71.429 | 34.473 | -2.6251 | -0.0843 | 2.5408 | -13.1818 | 23.292 | 2.951 | loss_risk_score >= 14.2205 |
| 69 | coverage_fail | KOSDAQ | exception_leader | 3d | 2 | 0.0865 | 41.346 | 66.667 | 25.321 | 0.5832 | 5.3104 | 4.7272 | -5.2989 | 26.175 | 11.432 | loss_risk_score >= 20.442<br>volume_ratio >= 0.9 |
| 70 | coverage_fail | KOSDAQ | exception_leader | 3d | 2 | 0.0865 | 41.346 | 66.667 | 25.321 | 0.5832 | 5.3104 | 4.7272 | -5.2989 | 26.175 | 11.432 | loss_risk_score >= 20.442<br>volume_ratio >= 1 |
| 71 | coverage_fail | KOSDAQ | exception_leader | 3d | 2 | 0.0865 | 41.346 | 66.667 | 25.321 | 0.5832 | 5.3104 | 4.7272 | -5.2989 | 26.175 | 11.432 | loss_risk_score >= 20.442<br>volume_ratio >= 1.183 |
| 72 | coverage_fail | KOSDAQ | exception_leader | 3d | 2 | 0.0865 | 41.346 | 66.667 | 25.321 | 0.5832 | 5.3104 | 4.7272 | -5.2989 | 26.175 | 11.432 | loss_risk_score >= 20.442<br>volume_ratio >= 1.2 |
| 73 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.087 | 36.956 | 62.5 | 25.544 | -2.6251 | -0.1326 | 2.4925 | -18.5849 | 30.435 | 19.022 | tech_score >= 50<br>volume_ratio >= 1.4075 |
| 74 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.087 | 36.956 | 62.5 | 25.544 | -2.6251 | -0.1326 | 2.4925 | -18.5849 | 30.435 | 19.022 | tech_score >= 50<br>volume_ratio >= 1.5 |
| 75 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1957 | 36.956 | 61.111 | 24.155 | -2.6251 | 3.4238 | 6.0489 | -18.5849 | 24.879 | 3.744 | conviction_score >= 63.3<br>volume_ratio >= 1.4075 |
| 76 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1957 | 36.956 | 61.111 | 24.155 | -2.6251 | 3.4238 | 6.0489 | -18.5849 | 24.879 | 3.744 | conviction_score >= 63.3<br>volume_ratio >= 1.5 |
| 77 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.0978 | 36.956 | 66.667 | 29.711 | -2.6251 | -1.3122 | 1.3129 | -18.5849 | 24.879 | 20.411 | loss_risk_score >= 20.442<br>tech_score >= 55 |
| 78 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.1196 | 36.956 | 63.636 | 26.68 | -2.6251 | 4.8526 | 7.4777 | -9.3918 | 16.799 | -4.842 | conviction_score >= 68.25<br>volume_ratio >= 0.7 |
| 79 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.2174 | 36.956 | 70.0 | 33.044 | -2.6251 | 4.0388 | 6.6639 | -35.0538 | 10.435 | 1.522 | priority_rank <= 4.85<br>volume_ratio >= 1.4075 |
| 80 | coverage_fail | KOSDAQ | exception_leader | 5d | 2 | 0.2174 | 36.956 | 70.0 | 33.044 | -2.6251 | 4.0388 | 6.6639 | -35.0538 | 10.435 | 1.522 | priority_rank <= 4.85<br>volume_ratio >= 1.5 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3804 win_delta=25.901 avg_delta=8.0228 :: conviction_score >= 66.9 / volume_ratio >= 1.8685
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4022 win_delta=22.503 avg_delta=6.3487 :: conviction_score >= 66.9 / volume_ratio >= 2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3587 win_delta=20.62 avg_delta=5.2519 :: conviction_score >= 68.25 / volume_ratio >= 1.4075
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3587 win_delta=20.62 avg_delta=5.2519 :: conviction_score >= 68.25 / volume_ratio >= 1.5
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3804 win_delta=17.33 avg_delta=5.6369 :: conviction_score >= 63.3 / volume_ratio >= 3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.5652 win_delta=14.967 avg_delta=4.2284 :: conviction_score >= 66.9 / volume_ratio >= 3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4457 win_delta=11.824 avg_delta=4.0005 :: conviction_score >= 63.3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3587 win_delta=8.498 avg_delta=2.8516 :: volume_ratio >= 0.9
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.375 win_delta=9.936 avg_delta=2.8049 :: feature_quality == complete / volume_ratio >= 1
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.375 win_delta=9.936 avg_delta=2.8049 :: feature_origin == scanner_full / volume_ratio >= 1
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4327 win_delta=9.765 avg_delta=2.7865 :: feature_quality == complete / volume_ratio >= 1.183
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4327 win_delta=9.765 avg_delta=2.7865 :: feature_origin == scanner_full / volume_ratio >= 1.183
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4327 win_delta=9.765 avg_delta=2.7865 :: feature_quality == complete / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4327 win_delta=9.765 avg_delta=2.7865 :: feature_origin == scanner_full / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5385 win_delta=10.44 avg_delta=2.0186 :: feature_quality == complete / volume_ratio >= 1.4075
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.5385 win_delta=10.44 avg_delta=2.0186 :: feature_origin == scanner_full / volume_ratio >= 1.4075
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.663 win_delta=8.946 avg_delta=2.4927 :: conviction_score >= 66.9
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.7283 win_delta=6.328 avg_delta=1.6614 :: conviction_score >= 68.25
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4615 win_delta=4.487 avg_delta=2.0755 :: conviction_score >= 63.3

## Diagnostics

- `KOSDAQ` `exception_leader` rows=384 days=50 cut=2026-06-08 predicates=132 levels={'coverage_fail': 347, 'diagnostic': 213, 'sample_fail': 70, 'shadow_candidate': 19}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
