# Loss Exclusion Guard Mining

- generated_at: `2026-06-29T07:07:51.371562+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `6906`
- quality_scope: `all`
- guard_count: `9494`
- production_candidate_count: `0`
- shadow_candidate_count: `117`
- guard_levels: `{'coverage_fail': 4443, 'diagnostic': 4220, 'sample_fail': 714, 'shadow_candidate': 117}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.5 | 33.333 | 50.0 | 16.667 | -10.1449 | 0.0806 | 10.2255 | -33.3333 | 20.834 | 16.667 | institution_3d <= -21.75<br>regime_adjusted_grade == RELATIVE_WATCHLIST |
| 2 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.5 | 33.333 | 50.0 | 16.667 | -10.1449 | 0.0806 | 10.2255 | -33.3333 | 20.834 | 16.667 | institution_3d <= -21.75<br>regime_adjusted_grade == RELATIVE_WATCHLIST |
| 3 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.4 | 32.0 | 50.0 | 18.0 | -5.503 | 1.2996 | 6.8026 | -23.6417 | 9.0 | 12.0 | ml_prob >= 60.2 |
| 4 | shadow_candidate | KOSDAQ | top5 | 3d | 2 | 0.4 | 32.0 | 50.0 | 18.0 | -5.503 | 1.2996 | 6.8026 | -23.6417 | 9.0 | 12.0 | ml_prob >= 60.2<br>volume_ratio >= 8.05 |
| 5 | shadow_candidate | KOSDAQ | top5 | 3d | 2 | 0.4 | 32.0 | 50.0 | 18.0 | -5.503 | 1.2996 | 6.8026 | -23.6417 | 9.0 | 12.0 | ml_prob >= 60.2<br>volume_ratio >= 12.625 |
| 6 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3704 | 18.518 | 33.333 | 14.815 | -12.8097 | -6.2764 | 6.5333 | -38.1679 | 7.16 | 8.025 | expected_edge_score <= 4.095<br>volume_ratio >= 11.525 |
| 7 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 1.5998 | 7.1028 | -24.6519 | 5.053 | 8.316 | volume_ratio >= 1.9025 |
| 8 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 1.5998 | 7.1028 | -24.6519 | 5.053 | 8.316 | volume_ratio >= 2 |
| 9 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 1.5998 | 7.1028 | -24.6519 | 5.053 | 8.316 | volume_ratio >= 1.9025 |
| 10 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 1.5998 | 7.1028 | -24.6519 | 5.053 | 8.316 | volume_ratio >= 2 |
| 11 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3827 | 18.518 | 32.258 | 13.74 | -12.8097 | -7.1757 | 5.634 | -38.1679 | 6.73 | 7.487 | expected_edge_score <= 4.095<br>volume_ratio >= 13.6 |
| 12 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 0.6029 | 6.1059 | -23.6417 | 5.053 | 8.316 | conviction_score >= 69.95 |
| 13 | shadow_candidate | KOSDAQ | top5 | 3d | 2 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 0.6029 | 6.1059 | -23.6417 | 5.053 | 8.316 | conviction_score >= 69.95<br>ml_prob >= 60.2 |
| 14 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.38 | 32.0 | 47.368 | 15.368 | -5.503 | 0.6029 | 6.1059 | -23.6417 | 5.053 | 8.316 | conviction_score >= 69.95 |
| 15 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.54 | 32.0 | 44.444 | 12.444 | -5.503 | -0.7051 | 4.7979 | -24.6519 | 9.926 | 11.63 | volume_ratio >= 8.05 |
| 16 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.54 | 32.0 | 44.444 | 12.444 | -5.503 | -0.7051 | 4.7979 | -24.6519 | 9.926 | 11.63 | volume_ratio >= 8.05 |
| 17 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | institution_10d >= 349.85<br>relative_rank_pct >= 0.166667 |
| 18 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | institution_3d >= 83<br>relative_rank_pct >= 0.166667 |
| 19 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | institution_10d >= 349.85<br>relative_rank_pct >= 0.166667 |
| 20 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | institution_3d >= 83<br>relative_rank_pct >= 0.166667 |
| 21 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | expected_edge_score >= 14.23<br>relative_rank_pct >= 0.166667 |
| 22 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | expected_return_1d_pct >= 1.28<br>relative_rank_pct >= 0.166667 |
| 23 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -4.4347 | 5.7102 | -33.5536 | 12.5 | 8.333 | expected_return_3d_pct >= 1.855<br>relative_rank_pct >= 0.166667 |
| 24 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.58 | 32.0 | 44.828 | 12.828 | -5.503 | -0.9927 | 4.5103 | -24.6519 | 8.138 | 9.586 | volume_ratio >= 12.625 |
| 25 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4074 | 18.518 | 30.303 | 11.785 | -12.8097 | -9.23 | 3.5797 | -41.0168 | 8.978 | 12.57 | expected_return_1d_pct >= 1.27<br>priority_rank >= 9 |
| 26 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4074 | 18.518 | 30.303 | 11.785 | -12.8097 | -9.8024 | 3.0073 | -41.0168 | 8.978 | 12.57 | priority_rank >= 9<br>retail_10d <= -10646.3 |
| 27 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -5.7129 | 4.432 | -33.5536 | 12.5 | 8.333 | foreigner_3d >= 6452.25<br>relative_rank_pct >= 0.166667 |
| 28 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.375 | 33.333 | 44.444 | 11.111 | -10.1449 | -5.7129 | 4.432 | -33.5536 | 12.5 | 8.333 | foreigner_3d >= 6452.25<br>relative_rank_pct >= 0.166667 |
| 29 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4321 | 18.518 | 31.429 | 12.911 | -12.8097 | -10.0181 | 2.7916 | -41.0168 | 8.113 | 8.501 | expected_edge_score <= 4.095<br>priority_rank >= 9 |
| 30 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3827 | 18.518 | 32.258 | 13.74 | -12.8097 | -10.2369 | 2.5728 | -56.139 | 9.956 | 13.939 | institution_10d <= -246.4<br>priority_rank >= 10 |
| 31 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -0.6879 | 4.8151 | -24.6519 | 5.739 | 8.087 | ml_prob >= 66.6 |
| 32 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -0.6879 | 4.8151 | -24.6519 | 5.739 | 8.087 | conviction_score >= 75.2 |
| 33 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -0.6879 | 4.8151 | -24.6519 | 5.739 | 8.087 | ml_prob >= 65.7 |
| 34 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -0.6879 | 4.8151 | -24.6519 | 5.739 | 8.087 | ml_prob >= 66.6 |
| 35 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -0.6879 | 4.8151 | -24.6519 | 5.739 | 8.087 | conviction_score >= 75.2 |
| 36 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.625 | 33.333 | 40.0 | 6.667 | -10.1449 | -5.5523 | 4.5926 | -35.4605 | 12.5 | 8.333 | institution_1d >= 20.75<br>regime_adjusted_grade == RELATIVE_WATCHLIST |
| 37 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.625 | 33.333 | 40.0 | 6.667 | -10.1449 | -5.5523 | 4.5926 | -35.4605 | 12.5 | 8.333 | institution_1d >= 20.75<br>regime_adjusted_grade == RELATIVE_WATCHLIST |
| 38 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.358 | 18.518 | 31.034 | 12.516 | -12.8097 | -9.268 | 3.5417 | -56.139 | 7.62 | 12.048 | retail_10d <= -10646.3<br>volume_ratio >= 13.6 |
| 39 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.3827 | 18.518 | 29.032 | 10.514 | -12.8097 | -8.3059 | 4.5038 | -56.139 | 6.73 | 10.713 | volume_ratio >= 6.5905 |
| 40 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -2.9551 | 2.5479 | -26.3566 | 10.087 | 12.435 | expected_edge_score >= 12.37 |
| 41 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -2.9551 | 2.5479 | -26.3566 | 10.087 | 12.435 | expected_return_1d_pct >= 1.11 |
| 42 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.46 | 32.0 | 43.478 | 11.478 | -5.503 | -2.9551 | 2.5479 | -26.3566 | 10.087 | 12.435 | expected_return_3d_pct >= 1.63 |
| 43 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3846 | 15.385 | 28.0 | 12.615 | -9.324 | -5.4633 | 3.8607 | -28.9944 | 5.846 | 6.769 | priority_rank >= 3<br>relative_rank_pct >= 0.050627 |
| 44 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3846 | 15.385 | 28.0 | 12.615 | -9.324 | -5.4633 | 3.8607 | -28.9944 | 5.846 | 6.769 | priority_rank >= 3<br>relative_rank_pct >= 0.066667 |
| 45 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.5417 | 33.333 | 38.462 | 5.129 | -10.1449 | -6.566 | 3.5789 | -41.0168 | 17.629 | 13.462 | institution_1d >= 20.75<br>institution_3d <= -21.75 |
| 46 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.5417 | 33.333 | 38.462 | 5.129 | -10.1449 | -6.566 | 3.5789 | -41.0168 | 17.629 | 13.462 | institution_1d >= 20.75<br>institution_3d <= -21.75 |
| 47 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3827 | 18.518 | 29.032 | 10.514 | -12.8097 | -8.7932 | 4.0165 | -56.139 | 6.73 | 10.713 | expected_return_1d_pct >= 1.27<br>volume_ratio >= 11.525 |
| 48 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3827 | 18.518 | 29.032 | 10.514 | -12.8097 | -8.7932 | 4.0165 | -56.139 | 6.73 | 10.713 | expected_return_1d_pct >= 1.27<br>volume_ratio >= 13.6 |
| 49 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.4198 | 18.518 | 29.412 | 10.894 | -12.8097 | -8.7718 | 4.0379 | -56.139 | 5.592 | 9.005 | volume_ratio >= 11.525 |
| 50 | shadow_candidate | KOSDAQ | top5 | 1d | 1 | 0.4412 | 45.588 | 56.667 | 11.079 | -1.1847 | 2.0234 | 3.2081 | -28.2258 | 11.274 | 9.118 | theme_inference_status == inferred |
| 51 | shadow_candidate | KOSDAQ | top5_exception | 1d | 1 | 0.4412 | 45.588 | 56.667 | 11.079 | -1.1847 | 2.0234 | 3.2081 | -28.2258 | 11.274 | 9.118 | theme_inference_status == inferred |
| 52 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.4691 | 18.518 | 28.947 | 10.429 | -12.8097 | -10.6433 | 2.1664 | -41.0168 | 6.985 | 9.779 | priority_rank >= 9 |
| 53 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3704 | 18.518 | 30.0 | 11.482 | -12.8097 | -9.4732 | 3.3365 | -41.0168 | 3.827 | 4.691 | priority_rank >= 12<br>relative_rank_pct >= 0.241379 |
| 54 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.625 | 33.333 | 40.0 | 6.667 | -10.1449 | -8.1351 | 2.0098 | -41.0168 | 12.5 | 15.0 | institution_10d <= -668.5<br>retail_10d <= -1763 |
| 55 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3704 | 18.518 | 30.0 | 11.482 | -12.8097 | -9.9229 | 2.8868 | -41.0168 | 3.827 | 4.691 | expected_return_1d_pct >= 1.27<br>relative_rank_pct >= 0.241379 |
| 56 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.4321 | 18.518 | 28.571 | 10.053 | -12.8097 | -9.497 | 3.3127 | -56.139 | 5.256 | 8.501 | volume_ratio >= 13.6 |
| 57 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.6667 | 33.333 | 37.5 | 4.167 | -10.1449 | -6.8736 | 3.2713 | -41.0168 | 10.417 | 12.5 | institution_10d >= 349.85<br>institution_3d <= -21.75 |
| 58 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.6667 | 33.333 | 37.5 | 4.167 | -10.1449 | -6.8736 | 3.2713 | -41.0168 | 10.417 | 12.5 | institution_10d >= 349.85<br>institution_3d <= -21.75 |
| 59 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4568 | 18.518 | 29.73 | 11.212 | -12.8097 | -11.4184 | 1.3913 | -41.0168 | 4.638 | 7.574 | day_return_pct <= 9.162<br>priority_rank >= 10 |
| 60 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.4286 | 24.49 | 31.746 | 7.256 | -8.2432 | -5.156 | 3.0872 | -32.2321 | 5.895 | 8.616 | volume_ratio >= 6.5905 |
| 61 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3827 | 18.518 | 29.032 | 10.514 | -12.8097 | -10.5601 | 2.2496 | -41.0168 | 3.504 | 4.261 | institution_10d <= -4242.5<br>relative_rank_pct >= 0.241379 |
| 62 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.44 | 32.0 | 40.909 | 8.909 | -5.503 | -1.3799 | 4.1231 | -24.6519 | 2.182 | 4.727 | prob_clean >= 50.4 |
| 63 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.5 | 32.0 | 40.0 | 8.0 | -5.503 | -1.873 | 3.63 | -24.6519 | 4.0 | 6.0 | volume_ratio >= 3 |
| 64 | shadow_candidate | KOSDAQ | top5 | 3d | 1 | 0.5 | 32.0 | 40.0 | 8.0 | -5.503 | -1.873 | 3.63 | -24.6519 | 4.0 | 6.0 | volume_ratio >= 3.525 |
| 65 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.5 | 32.0 | 40.0 | 8.0 | -5.503 | -1.873 | 3.63 | -24.6519 | 4.0 | 6.0 | volume_ratio >= 3 |
| 66 | shadow_candidate | KOSDAQ | top5_exception | 3d | 1 | 0.5 | 32.0 | 40.0 | 8.0 | -5.503 | -1.873 | 3.63 | -24.6519 | 4.0 | 6.0 | volume_ratio >= 3.525 |
| 67 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.5782 | 24.49 | 34.118 | 9.628 | -8.2432 | -6.0175 | 2.2257 | -35.7887 | 3.785 | 4.097 | priority_rank >= 10 |
| 68 | shadow_candidate | KOSPI | top5 | 1d | 1 | 0.3626 | 26.374 | 39.394 | 13.02 | -3.2413 | -1.3942 | 1.8471 | -29.9191 | 4.995 | 5.561 | volume_ratio <= 10.125 |
| 69 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3704 | 18.518 | 26.667 | 8.149 | -12.8097 | -10.263 | 2.5467 | -41.0168 | 3.827 | 4.691 | foreigner_10d >= 8991.5<br>relative_rank_pct >= 0.241379 |
| 70 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3704 | 18.518 | 26.667 | 8.149 | -12.8097 | -10.263 | 2.5467 | -41.0168 | 3.827 | 4.691 | relative_rank_pct >= 0.241379<br>retail_10d <= -10646.3 |
| 71 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.517 | 24.49 | 32.895 | 8.405 | -8.2432 | -6.4303 | 1.8129 | -35.7887 | 5.039 | 5.63 | priority_rank >= 9 |
| 72 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.3537 | 24.49 | 30.769 | 6.279 | -8.2432 | -4.7062 | 3.537 | -32.2321 | 2.812 | 6.541 | volume_ratio >= 2 |
| 73 | shadow_candidate | KOSDAQ | top5 | 5d | 1 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | relative_rank_pct >= 0.166667 |
| 74 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | institution_3d <= -1386.6<br>relative_rank_pct >= 0.166667 |
| 75 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | relative_rank_pct >= 0.166667<br>retail_10d <= -87543.8 |
| 76 | shadow_candidate | KOSDAQ | top5 | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | relative_rank_pct >= 0.166667<br>retail_1d >= 328.25 |
| 77 | shadow_candidate | KOSDAQ | top5_exception | 5d | 1 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | relative_rank_pct >= 0.166667 |
| 78 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | foreigner_3d <= -47897.3<br>relative_rank_pct >= 0.166667 |
| 79 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | foreigner_3d <= -17947<br>relative_rank_pct >= 0.166667 |
| 80 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4167 | 33.333 | 40.0 | 6.667 | -10.1449 | -7.3246 | 2.8203 | -33.5536 | 9.167 | 5.0 | institution_3d <= -1386.6<br>relative_rank_pct >= 0.166667 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `top5` `5d` level=shadow_candidate retain=0.5 win_delta=16.667 avg_delta=10.2255 :: institution_3d <= -21.75 / regime_adjusted_grade == RELATIVE_WATCHLIST
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.5 win_delta=16.667 avg_delta=10.2255 :: institution_3d <= -21.75 / regime_adjusted_grade == RELATIVE_WATCHLIST
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.4 win_delta=18.0 avg_delta=6.8026 :: ml_prob >= 60.2
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.4 win_delta=18.0 avg_delta=6.8026 :: ml_prob >= 60.2 / volume_ratio >= 8.05
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.4 win_delta=18.0 avg_delta=6.8026 :: ml_prob >= 60.2 / volume_ratio >= 12.625
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3704 win_delta=14.815 avg_delta=6.5333 :: expected_edge_score <= 4.095 / volume_ratio >= 11.525
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=7.1028 :: volume_ratio >= 1.9025
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=7.1028 :: volume_ratio >= 2
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=7.1028 :: volume_ratio >= 1.9025
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=7.1028 :: volume_ratio >= 2
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3827 win_delta=13.74 avg_delta=5.634 :: expected_edge_score <= 4.095 / volume_ratio >= 13.6
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=6.1059 :: conviction_score >= 69.95
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=6.1059 :: conviction_score >= 69.95 / ml_prob >= 60.2
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.38 win_delta=15.368 avg_delta=6.1059 :: conviction_score >= 69.95
- `KOSDAQ` `top5` `3d` level=shadow_candidate retain=0.54 win_delta=12.444 avg_delta=4.7979 :: volume_ratio >= 8.05
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.54 win_delta=12.444 avg_delta=4.7979 :: volume_ratio >= 8.05
- `KOSDAQ` `top5` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: institution_10d >= 349.85 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: institution_3d >= 83 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: institution_10d >= 349.85 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: institution_3d >= 83 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: expected_edge_score >= 14.23 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: expected_return_1d_pct >= 1.28 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=5.7102 :: expected_return_3d_pct >= 1.855 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.58 win_delta=12.828 avg_delta=4.5103 :: volume_ratio >= 12.625
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.4074 win_delta=11.785 avg_delta=3.5797 :: expected_return_1d_pct >= 1.27 / priority_rank >= 9
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.4074 win_delta=11.785 avg_delta=3.0073 :: priority_rank >= 9 / retail_10d <= -10646.3
- `KOSDAQ` `top5` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=4.432 :: foreigner_3d >= 6452.25 / relative_rank_pct >= 0.166667
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.375 win_delta=11.111 avg_delta=4.432 :: foreigner_3d >= 6452.25 / relative_rank_pct >= 0.166667
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.4321 win_delta=12.911 avg_delta=2.7916 :: expected_edge_score <= 4.095 / priority_rank >= 9
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3827 win_delta=13.74 avg_delta=2.5728 :: institution_10d <= -246.4 / priority_rank >= 10

## Diagnostics

- `KOSPI` `top5` rows=317 days=37 cut=2026-06-16 predicates=332 levels={'diagnostic': 656, 'coverage_fail': 521, 'sample_fail': 86, 'shadow_candidate': 11}
- `KOSPI` `top5_exception` rows=329 days=37 cut=2026-06-16 predicates=337 levels={'diagnostic': 659, 'coverage_fail': 530, 'sample_fail': 98, 'shadow_candidate': 7}
- `KOSPI` `ranked_top20` rows=925 days=37 cut=2026-06-16 predicates=375 levels={'coverage_fail': 931, 'diagnostic': 754, 'sample_fail': 78, 'shadow_candidate': 6}
- `KOSDAQ` `top5` rows=298 days=35 cut=2026-06-17 predicates=309 levels={'diagnostic': 760, 'coverage_fail': 664, 'sample_fail': 165, 'shadow_candidate': 25}
- `KOSDAQ` `top5_exception` rows=320 days=35 cut=2026-06-17 predicates=310 levels={'diagnostic': 741, 'coverage_fail': 717, 'sample_fail': 166, 'shadow_candidate': 34}
- `KOSDAQ` `ranked_top20` rows=942 days=35 cut=2026-06-17 predicates=334 levels={'coverage_fail': 1080, 'diagnostic': 650, 'sample_fail': 121, 'shadow_candidate': 34}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
