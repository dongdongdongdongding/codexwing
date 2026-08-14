# Loss Exclusion Guard Mining

- generated_at: `2026-08-14T00:52:18.093865+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `6174`
- quality_scope: `all`
- guard_count: `1002`
- production_candidate_count: `0`
- shadow_candidate_count: `143`
- guard_levels: `{'diagnostic': 421, 'coverage_fail': 410, 'shadow_candidate': 143, 'sample_fail': 28}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | 2.983 | 9.5389 | -20.9589 | 13.174 | 16.256 | expected_edge_score >= -12.1575<br>theme_inference_status == inferred |
| 2 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | 2.983 | 9.5389 | -20.9589 | 13.174 | 16.256 | expected_return_1d_pct >= -0.85<br>theme_inference_status == inferred |
| 3 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | 2.983 | 9.5389 | -20.9589 | 13.174 | 16.256 | expected_return_3d_pct >= -1.5325<br>theme_inference_status == inferred |
| 4 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 52.0 | 23.186 | -6.5559 | 0.2637 | 6.8196 | -35.0171 | 9.356 | 6.983 | expected_edge_score >= -7.2775<br>volume_ratio >= 1.2 |
| 5 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 52.0 | 23.186 | -6.5559 | 0.2637 | 6.8196 | -35.0171 | 9.356 | 6.983 | expected_return_1d_pct >= -0.509<br>volume_ratio >= 1.2 |
| 6 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 52.0 | 23.186 | -6.5559 | 0.2637 | 6.8196 | -35.0171 | 9.356 | 6.983 | expected_return_3d_pct >= -0.919<br>volume_ratio >= 1.2 |
| 7 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4068 | 28.814 | 50.0 | 21.186 | -6.5559 | 0.0077 | 6.5636 | -35.0171 | 10.523 | 9.816 | expected_edge_inversion_score <= 8.5115<br>volume_ratio >= 1.2 |
| 8 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3729 | 33.898 | 54.546 | 20.648 | -3.9965 | 2.7784 | 6.7749 | -23.9709 | 8.629 | 11.71 | theme_inference_status == inferred<br>volume_ratio >= 2.005 |
| 9 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4237 | 33.898 | 56.0 | 22.102 | -3.9965 | 2.1485 | 6.145 | -22.9508 | 5.356 | 10.983 | expected_edge_inversion_score >= 4.05<br>theme_inference_status == inferred |
| 10 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3559 | 28.814 | 38.095 | 9.281 | -6.5559 | 2.7225 | 9.2784 | -20.9589 | 9.927 | 15.174 | phase25_shadow_prob <= 56.25<br>theme_inference_status == inferred |
| 11 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4237 | 33.898 | 56.0 | 22.102 | -3.9965 | 0.191 | 4.1875 | -24.5039 | 9.356 | 14.983 | tech_score >= 75<br>whale_score >= 85 |
| 12 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3559 | 28.814 | 38.095 | 9.281 | -6.5559 | 1.7592 | 8.3151 | -34.5278 | 14.689 | 15.174 | ml_prob >= 39.25<br>theme_inference_status == inferred |
| 13 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 47.826 | 19.012 | -6.5559 | -0.2248 | 6.3311 | -35.0171 | 7.443 | 8.548 | expected_edge_score >= -12.1575<br>volume_ratio >= 1.2 |
| 14 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 47.826 | 19.012 | -6.5559 | -0.2248 | 6.3311 | -35.0171 | 7.443 | 8.548 | expected_return_1d_pct >= -0.85<br>volume_ratio >= 1.2 |
| 15 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 47.826 | 19.012 | -6.5559 | -0.2248 | 6.3311 | -35.0171 | 7.443 | 8.548 | expected_return_3d_pct >= -1.5325<br>volume_ratio >= 1.2 |
| 16 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 39.13 | 10.316 | -6.5559 | 1.3521 | 7.908 | -34.5278 | 11.791 | 17.244 | expected_edge_score >= -7.2775<br>theme_inference_status == inferred |
| 17 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 39.13 | 10.316 | -6.5559 | 1.3521 | 7.908 | -34.5278 | 11.791 | 17.244 | expected_return_1d_pct >= -0.509<br>theme_inference_status == inferred |
| 18 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 39.13 | 10.316 | -6.5559 | 1.3521 | 7.908 | -34.5278 | 11.791 | 17.244 | expected_return_3d_pct >= -0.919<br>theme_inference_status == inferred |
| 19 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 39.13 | 10.316 | -6.5559 | 1.3521 | 7.908 | -34.5278 | 11.791 | 17.244 | expected_edge_inversion_score <= 8.5115<br>theme_inference_status == inferred |
| 20 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4576 | 28.814 | 48.148 | 19.334 | -6.5559 | -0.2796 | 6.2763 | -35.0171 | 7.282 | 5.65 | expected_edge_score >= -7.2775<br>volume_ratio >= 1.3 |
| 21 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4576 | 28.814 | 48.148 | 19.334 | -6.5559 | -0.2796 | 6.2763 | -35.0171 | 7.282 | 5.65 | expected_return_1d_pct >= -0.509<br>volume_ratio >= 1.3 |
| 22 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4576 | 28.814 | 48.148 | 19.334 | -6.5559 | -0.2796 | 6.2763 | -35.0171 | 7.282 | 5.65 | expected_return_3d_pct >= -0.919<br>volume_ratio >= 1.3 |
| 23 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3559 | 28.814 | 47.619 | 18.805 | -6.5559 | 1.9849 | 8.5408 | -23.7248 | 5.165 | -8.636 | ml_prob >= 39.25<br>volume_ratio >= 1.5 |
| 24 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4407 | 33.898 | 53.846 | 19.948 | -3.9965 | -0.0844 | 3.9121 | -24.5039 | 8.279 | 15.906 | tech_score >= 75<br>whale_score >= 88 |
| 25 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 46.154 | 17.34 | -6.5559 | -0.5369 | 6.019 | -35.0171 | 8.279 | 8.214 | expected_edge_inversion_score <= 8.5115<br>volume_ratio >= 1.3 |
| 26 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5424 | 28.814 | 43.75 | 14.936 | -6.5559 | 0.475 | 7.0309 | -23.7248 | 9.481 | -1.642 | ml_prob >= 39.25<br>tech_score >= 90 |
| 27 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 47.826 | 19.012 | -6.5559 | -0.3136 | 6.2423 | -35.0171 | 3.095 | 4.2 | phase25_shadow_prob <= 56.25<br>volume_ratio >= 1.2 |
| 28 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4915 | 28.814 | 44.828 | 16.014 | -6.5559 | -0.6973 | 5.8586 | -35.0171 | 5.494 | 7.949 | expected_edge_score >= -7.2775<br>volume_ratio >= 1.5 |
| 29 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4915 | 28.814 | 44.828 | 16.014 | -6.5559 | -0.6973 | 5.8586 | -35.0171 | 5.494 | 7.949 | expected_return_1d_pct >= -0.509<br>volume_ratio >= 1.5 |
| 30 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4915 | 28.814 | 44.828 | 16.014 | -6.5559 | -0.6973 | 5.8586 | -35.0171 | 5.494 | 7.949 | expected_return_3d_pct >= -0.919<br>volume_ratio >= 1.5 |
| 31 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3559 | 33.898 | 52.381 | 18.483 | -3.9965 | -0.0423 | 3.9542 | -24.5039 | 9.927 | 10.412 | tech_score >= 75<br>whale_score >= 78 |
| 32 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 36.0 | 7.186 | -6.5559 | 0.8551 | 7.411 | -29.5945 | 9.356 | 14.983 | phase25_prob <= 33.5<br>theme_inference_status == inferred |
| 33 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 36.364 | 7.55 | -6.5559 | 1.7857 | 8.3416 | -34.5278 | 8.629 | 11.71 | theme_inference_status == inferred<br>volume_ratio >= 2.005 |
| 34 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4746 | 28.814 | 42.857 | 14.043 | -6.5559 | -0.9511 | 5.6048 | -35.0171 | 6.356 | 10.412 | expected_edge_inversion_score <= 8.5115<br>volume_ratio >= 1.5 |
| 35 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 44.0 | 15.186 | -6.5559 | -0.7725 | 5.7834 | -35.0171 | 5.356 | 6.983 | expected_edge_score >= -12.1575<br>volume_ratio >= 1.3 |
| 36 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 44.0 | 15.186 | -6.5559 | -0.7725 | 5.7834 | -35.0171 | 5.356 | 6.983 | expected_return_1d_pct >= -0.85<br>volume_ratio >= 1.3 |
| 37 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 44.0 | 15.186 | -6.5559 | -0.7725 | 5.7834 | -35.0171 | 5.356 | 6.983 | expected_return_3d_pct >= -1.5325<br>volume_ratio >= 1.3 |
| 38 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4237 | 28.814 | 36.0 | 7.186 | -6.5559 | 0.7569 | 7.3128 | -29.5945 | 9.356 | 10.983 | tech_score >= 90<br>theme_inference_status == inferred |
| 39 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3898 | 28.814 | 34.783 | 5.969 | -6.5559 | 1.471 | 8.0269 | -34.5278 | 7.443 | 12.896 | theme_inference_status == inferred<br>volume_ratio >= 3 |
| 40 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 45.454 | 16.64 | -6.5559 | 0.6224 | 7.1783 | -27.9907 | 4.083 | -11.017 | ml_prob >= 39.25<br>volume_ratio >= 1.54 |
| 41 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5593 | 33.898 | 51.515 | 17.617 | -3.9965 | -1.119 | 2.8775 | -24.5039 | 8.629 | 5.65 | loss_risk_score >= 35.1141<br>whale_score >= 85 |
| 42 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5593 | 33.898 | 51.515 | 17.617 | -3.9965 | -1.119 | 2.8775 | -24.5039 | 8.629 | 5.65 | loss_risk_score >= 35.1141<br>whale_score >= 88 |
| 43 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_edge_score >= -12.1575<br>volume_ratio >= 1.5 |
| 44 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_return_1d_pct >= -0.85<br>volume_ratio >= 1.5 |
| 45 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_return_3d_pct >= -1.5325<br>volume_ratio >= 1.5 |
| 46 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_edge_score >= -12.1575<br>volume_ratio >= 1.54 |
| 47 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_return_1d_pct >= -0.85<br>volume_ratio >= 1.54 |
| 48 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 42.308 | 13.494 | -6.5559 | -0.794 | 5.7619 | -35.0171 | 4.433 | 8.214 | expected_return_3d_pct >= -1.5325<br>volume_ratio >= 1.54 |
| 49 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.4915 | 28.814 | 44.828 | 16.014 | -6.5559 | -1.3278 | 5.2281 | -35.0171 | 5.494 | 1.052 | volume_ratio >= 1.2 |
| 50 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4915 | 28.814 | 44.828 | 16.014 | -6.5559 | -1.3278 | 5.2281 | -35.0171 | 5.494 | 1.052 | phase25_prob <= 33.5<br>volume_ratio >= 1.2 |
| 51 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6949 | 28.814 | 39.024 | 10.21 | -6.5559 | -1.7631 | 4.7928 | -35.0171 | 5.746 | 12.154 | expected_edge_score >= -7.2775<br>tech_score >= 90 |
| 52 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6949 | 28.814 | 39.024 | 10.21 | -6.5559 | -1.7631 | 4.7928 | -35.0171 | 5.746 | 12.154 | expected_return_1d_pct >= -0.509<br>tech_score >= 90 |
| 53 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6949 | 28.814 | 39.024 | 10.21 | -6.5559 | -1.7631 | 4.7928 | -35.0171 | 5.746 | 12.154 | expected_return_3d_pct >= -0.919<br>tech_score >= 90 |
| 54 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4068 | 33.898 | 50.0 | 16.102 | -3.9965 | -0.27 | 3.7265 | -25.6376 | 10.523 | 5.65 | alpha_score >= 57<br>whale_score >= 85 |
| 55 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3729 | 33.898 | 50.0 | 16.102 | -3.9965 | -0.3092 | 3.6873 | -25.6376 | 13.174 | 2.619 | alpha_score >= 57<br>whale_score >= 78 |
| 56 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4407 | 28.814 | 46.154 | 17.34 | -6.5559 | -1.6288 | 4.9271 | -35.0171 | 4.433 | 0.521 | volume_ratio >= 1.2<br>whale_score <= 65 |
| 57 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5085 | 28.814 | 43.333 | 14.519 | -6.5559 | -1.6071 | 4.9488 | -35.0171 | 4.689 | 5.65 | expected_edge_score >= -7.2775<br>volume_ratio >= 1.54 |
| 58 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5085 | 28.814 | 43.333 | 14.519 | -6.5559 | -1.6071 | 4.9488 | -35.0171 | 4.689 | 5.65 | expected_return_1d_pct >= -0.509<br>volume_ratio >= 1.54 |
| 59 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5085 | 28.814 | 43.333 | 14.519 | -6.5559 | -1.6071 | 4.9488 | -35.0171 | 4.689 | 5.65 | expected_return_3d_pct >= -0.919<br>volume_ratio >= 1.54 |
| 60 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.5254 | 33.898 | 51.613 | 17.715 | -3.9965 | -0.4081 | 3.5884 | -24.5039 | 7.162 | 0.273 | tech_score >= 90<br>whale_score >= 78 |
| 61 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.678 | 28.814 | 37.5 | 8.686 | -6.5559 | -1.9675 | 4.5884 | -35.0171 | 6.356 | 13.983 | expected_edge_inversion_score <= 8.5115<br>tech_score >= 90 |
| 62 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | -0.662 | 5.8939 | -23.7248 | 4.083 | 2.619 | volume_ratio >= 0.97 |
| 63 | shadow_candidate | KOSDAQ | exception_leader | 5d | 1 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | -0.662 | 5.8939 | -23.7248 | 4.083 | 2.619 | volume_ratio >= 1 |
| 64 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | -0.662 | 5.8939 | -23.7248 | 4.083 | 2.619 | phase25_prob <= 33.5<br>volume_ratio >= 0.97 |
| 65 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | -0.662 | 5.8939 | -23.7248 | 4.083 | 2.619 | tech_score >= 90<br>volume_ratio >= 1 |
| 66 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 40.909 | 12.095 | -6.5559 | -0.662 | 5.8939 | -23.7248 | 4.083 | 2.619 | phase25_prob <= 33.5<br>volume_ratio >= 1 |
| 67 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4407 | 33.898 | 46.154 | 12.256 | -3.9965 | -0.6631 | 3.3334 | -24.5039 | 8.279 | 15.906 | loss_risk_score >= 35.1141<br>tech_score >= 75 |
| 68 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4915 | 28.814 | 41.379 | 12.565 | -6.5559 | -1.8835 | 4.6724 | -35.0171 | 5.494 | 7.949 | expected_edge_inversion_score <= 8.5115<br>volume_ratio >= 1.54 |
| 69 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.4576 | 28.814 | 44.444 | 15.63 | -6.5559 | -1.8456 | 4.7103 | -35.0171 | 3.578 | 1.946 | volume_ratio >= 1.3<br>whale_score <= 65 |
| 70 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4237 | 33.898 | 48.0 | 14.102 | -3.9965 | -0.538 | 3.4585 | -25.6376 | 9.356 | 6.983 | alpha_score >= 57<br>whale_score >= 88 |
| 71 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.661 | 28.814 | 38.462 | 9.648 | -6.5559 | -1.9067 | 4.6492 | -35.0171 | 4.433 | 10.778 | phase25_shadow_prob <= 56.25<br>tech_score >= 90 |
| 72 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.3729 | 28.814 | 36.364 | 7.55 | -6.5559 | -3.4366 | 3.1193 | -23.7248 | 8.629 | 20.801 | tech_score >= 65<br>whale_score <= 65 |
| 73 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6441 | 28.814 | 36.842 | 8.028 | -6.5559 | -1.9135 | 4.6424 | -35.0171 | 5.04 | 12.667 | expected_edge_score >= -12.1575<br>tech_score >= 90 |
| 74 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6441 | 28.814 | 36.842 | 8.028 | -6.5559 | -1.9135 | 4.6424 | -35.0171 | 5.04 | 12.667 | expected_return_1d_pct >= -0.85<br>tech_score >= 90 |
| 75 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.6441 | 28.814 | 36.842 | 8.028 | -6.5559 | -1.9135 | 4.6424 | -35.0171 | 5.04 | 12.667 | expected_return_3d_pct >= -1.5325<br>tech_score >= 90 |
| 76 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3559 | 33.898 | 42.857 | 8.959 | -3.9965 | -0.7717 | 3.2248 | -22.6027 | 9.927 | 19.935 | alpha_score >= 57<br>whale_score <= 65 |
| 77 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4237 | 33.898 | 44.0 | 10.102 | -3.9965 | -0.072 | 3.9245 | -24.5039 | 9.356 | 10.983 | alpha_score >= 57<br>tech_score >= 75 |
| 78 | shadow_candidate | KOSDAQ | exception_leader | 5d | 2 | 0.5254 | 28.814 | 41.935 | 13.121 | -6.5559 | -1.6983 | 4.8576 | -35.0171 | 3.937 | 0.273 | phase25_prob <= 33.5<br>volume_ratio >= 1.3 |
| 79 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4746 | 33.898 | 42.857 | 8.959 | -3.9965 | -0.4566 | 3.5399 | -22.6027 | 6.356 | 17.554 | phase25_shadow_prob <= 56.25<br>tech_score >= 75 |
| 80 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.4746 | 33.898 | 42.857 | 8.959 | -3.9965 | -0.0341 | 3.9624 | -24.5039 | 9.927 | 10.412 | alpha_score >= 57<br>tech_score >= 90 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3729 win_delta=12.095 avg_delta=9.5389 :: expected_edge_score >= -12.1575 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3729 win_delta=12.095 avg_delta=9.5389 :: expected_return_1d_pct >= -0.85 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3729 win_delta=12.095 avg_delta=9.5389 :: expected_return_3d_pct >= -1.5325 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4237 win_delta=23.186 avg_delta=6.8196 :: expected_edge_score >= -7.2775 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4237 win_delta=23.186 avg_delta=6.8196 :: expected_return_1d_pct >= -0.509 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4237 win_delta=23.186 avg_delta=6.8196 :: expected_return_3d_pct >= -0.919 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4068 win_delta=21.186 avg_delta=6.5636 :: expected_edge_inversion_score <= 8.5115 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.3729 win_delta=20.648 avg_delta=6.7749 :: theme_inference_status == inferred / volume_ratio >= 2.005
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4237 win_delta=22.102 avg_delta=6.145 :: expected_edge_inversion_score >= 4.05 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3559 win_delta=9.281 avg_delta=9.2784 :: phase25_shadow_prob <= 56.25 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4237 win_delta=22.102 avg_delta=4.1875 :: tech_score >= 75 / whale_score >= 85
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3559 win_delta=9.281 avg_delta=8.3151 :: ml_prob >= 39.25 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=19.012 avg_delta=6.3311 :: expected_edge_score >= -12.1575 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=19.012 avg_delta=6.3311 :: expected_return_1d_pct >= -0.85 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=19.012 avg_delta=6.3311 :: expected_return_3d_pct >= -1.5325 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=10.316 avg_delta=7.908 :: expected_edge_score >= -7.2775 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=10.316 avg_delta=7.908 :: expected_return_1d_pct >= -0.509 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=10.316 avg_delta=7.908 :: expected_return_3d_pct >= -0.919 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=10.316 avg_delta=7.908 :: expected_edge_inversion_score <= 8.5115 / theme_inference_status == inferred
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4576 win_delta=19.334 avg_delta=6.2763 :: expected_edge_score >= -7.2775 / volume_ratio >= 1.3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4576 win_delta=19.334 avg_delta=6.2763 :: expected_return_1d_pct >= -0.509 / volume_ratio >= 1.3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4576 win_delta=19.334 avg_delta=6.2763 :: expected_return_3d_pct >= -0.919 / volume_ratio >= 1.3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3559 win_delta=18.805 avg_delta=8.5408 :: ml_prob >= 39.25 / volume_ratio >= 1.5
- `KOSDAQ` `exception_leader` `3d` level=shadow_candidate retain=0.4407 win_delta=19.948 avg_delta=3.9121 :: tech_score >= 75 / whale_score >= 88
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4407 win_delta=17.34 avg_delta=6.019 :: expected_edge_inversion_score <= 8.5115 / volume_ratio >= 1.3
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.5424 win_delta=14.936 avg_delta=7.0309 :: ml_prob >= 39.25 / tech_score >= 90
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.3898 win_delta=19.012 avg_delta=6.2423 :: phase25_shadow_prob <= 56.25 / volume_ratio >= 1.2
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4915 win_delta=16.014 avg_delta=5.8586 :: expected_edge_score >= -7.2775 / volume_ratio >= 1.5
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4915 win_delta=16.014 avg_delta=5.8586 :: expected_return_1d_pct >= -0.509 / volume_ratio >= 1.5
- `KOSDAQ` `exception_leader` `5d` level=shadow_candidate retain=0.4915 win_delta=16.014 avg_delta=5.8586 :: expected_return_3d_pct >= -0.919 / volume_ratio >= 1.5

## Diagnostics

- `KOSDAQ` `exception_leader` rows=420 days=64 cut=2026-06-19 predicates=208 levels={'diagnostic': 421, 'coverage_fail': 410, 'shadow_candidate': 143, 'sample_fail': 28}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
