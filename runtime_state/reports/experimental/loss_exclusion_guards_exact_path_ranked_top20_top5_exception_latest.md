# Loss Exclusion Guard Mining

- generated_at: `2026-05-27T11:57:54.789879+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `4220`
- quality_scope: `exact_path`
- guard_count: `47527`
- production_candidate_count: `0`
- shadow_candidate_count: `475`
- guard_levels: `{'coverage_fail': 25752, 'sample_fail': 12303, 'diagnostic': 8997, 'shadow_candidate': 475}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3515 | 23.636 | 43.103 | 19.467 | -4.8507 | -0.6735 | 4.1772 | -30.1013 | 20.073 | 12.236 | alpha_score >= 70<br>volume_ratio <= 0.8 |
| 2 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3515 | 23.636 | 43.103 | 19.467 | -4.8507 | -0.6735 | 4.1772 | -30.1013 | 20.073 | 12.236 | alpha_score >= 70<br>volume_ratio <= 0.88 |
| 3 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3818 | 23.636 | 42.857 | 19.221 | -4.8507 | -1.2107 | 3.64 | -30.1013 | 16.652 | 12.756 | conviction_score >= 69.4<br>volume_ratio <= 0.8 |
| 4 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3818 | 23.636 | 42.857 | 19.221 | -4.8507 | -1.2107 | 3.64 | -30.1013 | 16.652 | 12.756 | conviction_score >= 69.4<br>volume_ratio <= 0.88 |
| 5 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3818 | 23.636 | 41.27 | 17.634 | -4.8507 | -1.2385 | 3.6122 | -30.1013 | 19.827 | 12.756 | alpha_score >= 70<br>volume_ratio <= 0.758 |
| 6 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3939 | 23.636 | 41.538 | 17.902 | -4.8507 | -1.3641 | 3.4866 | -30.1013 | 15.432 | 14.173 | decision_score >= 90<br>volume_ratio <= 0.8 |
| 7 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3818 | 23.636 | 41.27 | 17.634 | -4.8507 | -1.4881 | 3.3626 | -30.1013 | 15.065 | 14.344 | decision_score >= 86.3<br>volume_ratio <= 0.8 |
| 8 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3714 | 26.531 | 41.758 | 15.227 | -4.4174 | -0.8255 | 3.5919 | -25.8716 | 12.308 | 11.931 | priority_rank >= 10<br>regime_volatility_20d <= 2.22 |
| 9 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.3731 | 24.627 | 44.0 | 19.373 | -6.5535 | -2.8269 | 3.7266 | -46.3097 | 3.791 | 6.149 | alpha_score >= 82<br>volume_ratio <= 0.8 |
| 10 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.3731 | 24.627 | 44.0 | 19.373 | -6.5535 | -2.8269 | 3.7266 | -46.3097 | 3.791 | 6.149 | alpha_score >= 82<br>volume_ratio <= 0.88 |
| 11 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3758 | 23.636 | 35.484 | 11.848 | -4.8507 | -2.1148 | 2.7359 | -21.2346 | 15.68 | 12.014 | kosdaq_chg <= 0.543<br>volume_ratio <= 0.8 |
| 12 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3758 | 23.636 | 35.484 | 11.848 | -4.8507 | -2.1148 | 2.7359 | -21.2346 | 15.68 | 12.014 | kosdaq_chg <= 0.543<br>volume_ratio <= 0.88 |
| 13 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4485 | 23.636 | 37.838 | 14.202 | -4.8507 | -2.3767 | 2.474 | -30.1013 | 13.456 | 11.491 | alpha_score >= 82<br>volume_ratio <= 0.8 |
| 14 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4485 | 23.636 | 37.838 | 14.202 | -4.8507 | -2.3767 | 2.474 | -30.1013 | 13.456 | 11.491 | alpha_score >= 82<br>volume_ratio <= 0.88 |
| 15 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4788 | 23.636 | 36.709 | 13.073 | -4.8507 | -2.7195 | 2.1312 | -30.1013 | 13.679 | 11.953 | alpha_score >= 82<br>volume_ratio <= 0.758 |
| 16 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3636 | 23.636 | 33.333 | 9.697 | -4.8507 | -2.161 | 2.6897 | -19.2781 | 15.303 | 13.788 | decision == WATCHLIST_ONLY<br>volume_ratio <= 1.01 |
| 17 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.3881 | 24.627 | 42.308 | 17.681 | -6.5535 | -3.3404 | 3.2131 | -46.3097 | 3.329 | 4.764 | alpha_score >= 87<br>volume_ratio <= 0.8 |
| 18 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 36.842 | 13.206 | -4.8507 | -2.6354 | 2.2153 | -30.1013 | 12.496 | 10.104 | alpha_score >= 87<br>volume_ratio <= 0.8 |
| 19 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 36.842 | 13.206 | -4.8507 | -2.6354 | 2.2153 | -30.1013 | 12.496 | 10.104 | alpha_score >= 87<br>volume_ratio <= 0.88 |
| 20 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.503 | 23.636 | 33.735 | 10.099 | -4.8507 | -2.0414 | 2.8093 | -30.1013 | 14.319 | 10.595 | alpha_score >= 70<br>priority_rank >= 10 |
| 21 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 36.842 | 13.206 | -4.8507 | -2.2731 | 2.5776 | -30.1013 | 9.865 | 10.104 | conviction_score >= 74.5<br>volume_ratio <= 0.8 |
| 22 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 36.842 | 13.206 | -4.8507 | -2.2731 | 2.5776 | -30.1013 | 9.865 | 10.104 | conviction_score >= 74.5<br>volume_ratio <= 0.88 |
| 23 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4242 | 23.636 | 34.286 | 10.65 | -4.8507 | -2.4346 | 2.4161 | -21.2346 | 12.684 | 10.217 | kosdaq_chg <= 0<br>volume_ratio <= 0.8 |
| 24 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4242 | 23.636 | 34.286 | 10.65 | -4.8507 | -2.4346 | 2.4161 | -21.2346 | 12.684 | 10.217 | kosdaq_chg <= 0<br>volume_ratio <= 0.88 |
| 25 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4909 | 23.636 | 35.802 | 12.166 | -4.8507 | -2.9537 | 1.897 | -30.1013 | 12.773 | 10.64 | alpha_score >= 87<br>volume_ratio <= 0.758 |
| 26 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.4319 | 2.4188 | -30.1013 | 10.72 | 8.788 | alpha_score >= 93<br>volume_ratio <= 0.8 |
| 27 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.4319 | 2.4188 | -30.1013 | 10.72 | 8.788 | alpha_score >= 93<br>volume_ratio <= 0.88 |
| 28 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4909 | 23.636 | 35.802 | 12.166 | -4.8507 | -2.6138 | 2.2369 | -30.1013 | 10.303 | 10.64 | conviction_score >= 74.5<br>volume_ratio <= 0.758 |
| 29 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4328 | 24.627 | 37.931 | 13.304 | -6.5535 | -2.9163 | 3.6372 | -23.1481 | 2.136 | -3.989 | kosdaq_chg <= 0<br>selection_lane == 1d |
| 30 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3939 | 23.636 | 36.923 | 13.287 | -4.8507 | -2.2038 | 2.6469 | -30.1013 | 9.278 | 8.019 | regime_breadth_pct >= 32.06<br>volume_ratio <= 0.8 |
| 31 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.3939 | 23.636 | 36.923 | 13.287 | -4.8507 | -2.2038 | 2.6469 | -30.1013 | 9.278 | 8.019 | regime_breadth_pct >= 32.06<br>volume_ratio <= 0.88 |
| 32 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.6353 | 2.2154 | -30.1013 | 10.72 | 7.538 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.8 |
| 33 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.6353 | 2.2154 | -30.1013 | 10.72 | 7.538 | phase25_shadow_variant == phase25_kr_swing_lightgbm<br>volume_ratio <= 0.8 |
| 34 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.6353 | 2.2154 | -30.1013 | 10.72 | 7.538 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.88 |
| 35 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4848 | 23.636 | 36.25 | 12.614 | -4.8507 | -2.6353 | 2.2154 | -30.1013 | 10.72 | 7.538 | phase25_shadow_variant == phase25_kr_swing_lightgbm<br>volume_ratio <= 0.88 |
| 36 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5152 | 23.636 | 35.294 | 11.658 | -4.8507 | -2.7472 | 2.1035 | -30.1013 | 11.088 | 9.376 | alpha_score >= 93<br>volume_ratio <= 0.758 |
| 37 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4727 | 23.636 | 35.897 | 12.261 | -4.8507 | -2.1328 | 2.7179 | -30.1013 | 9.021 | 7.506 | priority_rank >= 10<br>volume_ratio <= 0.758 |
| 38 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.3507 | 24.627 | 36.17 | 11.543 | -6.5535 | -1.7841 | 4.7694 | -27.3349 | 2.429 | -4.319 | alpha_score >= 58<br>prob_clean <= 17.9 |
| 39 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.5143 | 26.531 | 38.889 | 12.358 | -4.4174 | -1.6788 | 2.7386 | -25.8716 | 8.889 | 2.835 | regime_volatility_20d <= 2.22<br>theme_risk == ['KOSDAQ_SWING_PROBATION'] |
| 40 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5152 | 23.636 | 35.294 | 11.658 | -4.8507 | -2.9386 | 1.9121 | -30.1013 | 11.088 | 8.2 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.758 |
| 41 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.497 | 23.636 | 35.366 | 11.73 | -4.8507 | -2.5225 | 2.3282 | -21.2346 | 7.458 | 6.349 | kosdaq_chg <= -0.126<br>volume_ratio <= 0.8 |
| 42 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.497 | 23.636 | 35.366 | 11.73 | -4.8507 | -2.5225 | 2.3282 | -21.2346 | 7.458 | 6.349 | kosdaq_chg <= -0.126<br>volume_ratio <= 0.88 |
| 43 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4727 | 23.636 | 32.051 | 8.415 | -4.8507 | -2.3848 | 2.4659 | -21.1454 | 12.867 | 6.224 | alpha_score >= 82<br>regime_avg_chg <= 1.85 |
| 44 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.4475 | 33.149 | 49.383 | 16.234 | -1.872 | 1.5787 | 3.4507 | -20.6854 | 4.12 | -4.597 | phase25_shadow_variant == phase25_kr_swing_lightgbm<br>regime_breadth_pct >= 32.06 |
| 45 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4179 | 24.627 | 39.286 | 14.659 | -6.5535 | -3.6268 | 2.9267 | -46.3097 | 2.505 | 2.292 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.8 |
| 46 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3959 | 26.531 | 37.113 | 10.582 | -4.4174 | -1.6006 | 2.8168 | -19.2781 | 9.102 | 3.514 | theme_risk == ['KOSDAQ_SWING_PROBATION']<br>volume_ratio <= 1 |
| 47 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3959 | 26.531 | 37.113 | 10.582 | -4.4174 | -1.6006 | 2.8168 | -19.2781 | 9.102 | 3.514 | theme_risk == ['KOSDAQ_SWING_PROBATION']<br>volume_ratio <= 1.08 |
| 48 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.4179 | 24.627 | 39.286 | 14.659 | -6.5535 | -4.024 | 2.5295 | -46.3097 | 2.505 | 4.078 | alpha_score >= 93<br>volume_ratio <= 0.8 |
| 49 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 35.526 | 11.89 | -4.8507 | -2.1725 | 2.6782 | -30.1013 | 7.233 | 6.156 | priority_rank >= 10<br>volume_ratio <= 0.8 |
| 50 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4606 | 23.636 | 35.526 | 11.89 | -4.8507 | -2.1725 | 2.6782 | -30.1013 | 7.233 | 6.156 | priority_rank >= 10<br>volume_ratio <= 0.88 |
| 51 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5091 | 23.636 | 33.333 | 9.697 | -4.8507 | -2.4487 | 2.402 | -30.1013 | 11.494 | 6.407 | alpha_score >= 82<br>regime_breadth_pct >= 32.06 |
| 52 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5758 | 23.636 | 31.579 | 7.943 | -4.8507 | -2.6835 | 2.1672 | -30.1013 | 12.759 | 8.262 | alpha_score >= 82<br>priority_rank >= 10 |
| 53 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3735 | 28.313 | 38.71 | 10.397 | -3.2644 | 0.6341 | 3.8985 | -23.0453 | 7.113 | 2.41 | expected_return_3d_pct >= -0.24<br>priority_rank >= 5 |
| 54 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.5028 | 33.149 | 48.352 | 15.203 | -1.872 | 1.3191 | 3.1911 | -20.6854 | 3.74 | -4.122 | phase25_prob <= 33.275<br>regime_breadth_pct >= 32.06 |
| 55 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5152 | 23.636 | 35.294 | 11.658 | -4.8507 | -2.7208 | 2.1299 | -30.1013 | 6.382 | 8.2 | decision_score >= 93.9<br>volume_ratio <= 0.8 |
| 56 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5152 | 23.636 | 35.294 | 11.658 | -4.8507 | -2.7208 | 2.1299 | -30.1013 | 6.382 | 8.2 | decision_score >= 93.9<br>volume_ratio <= 0.88 |
| 57 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3721 | 33.555 | 41.964 | 8.409 | -2.2237 | 0.9397 | 3.1634 | -24.2948 | 7.267 | 9.281 | expected_edge_score >= -3.325<br>regime_breadth_pct >= 34.61 |
| 58 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3721 | 33.555 | 41.964 | 8.409 | -2.2237 | 0.9397 | 3.1634 | -24.2948 | 7.267 | 9.281 | expected_return_1d_pct >= -0.235<br>regime_breadth_pct >= 34.61 |
| 59 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3837 | 26.531 | 35.106 | 8.575 | -4.4174 | -2.6467 | 1.7707 | -30.1013 | 13.313 | 12.376 | alpha_score >= 77<br>volume_ratio <= 0.8 |
| 60 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3837 | 26.531 | 35.106 | 8.575 | -4.4174 | -2.6467 | 1.7707 | -30.1013 | 13.313 | 12.376 | alpha_score >= 77<br>volume_ratio <= 0.8905 |
| 61 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4545 | 23.636 | 34.667 | 11.031 | -4.8507 | -2.9452 | 1.9055 | -30.1013 | 7.637 | 9.455 | volume_ratio <= 0.8<br>whale_score <= 63.05 |
| 62 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4545 | 23.636 | 34.667 | 11.031 | -4.8507 | -2.9452 | 1.9055 | -30.1013 | 7.637 | 9.455 | volume_ratio <= 0.88<br>whale_score <= 63.05 |
| 63 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.4122 | 26.531 | 34.654 | 8.123 | -4.4174 | -2.3649 | 2.0525 | -21.1454 | 12.787 | 5.719 | kosdaq_chg <= 1.81<br>theme_risk == ['KOSDAQ_SWING_PROBATION'] |
| 64 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3606 | 29.327 | 41.333 | 12.006 | -4.3008 | -1.6575 | 2.6433 | -46.3097 | 3.129 | 7.788 | decision_score >= 83<br>volume_ratio <= 0.7345 |
| 65 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.351 | 26.531 | 30.233 | 3.702 | -4.4174 | -1.985 | 2.4324 | -21.875 | 16.678 | 10.347 | expected_return_3d_pct <= 0.01<br>priority_rank >= 8 |
| 66 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3555 | 33.555 | 42.991 | 9.436 | -2.2237 | 0.5691 | 2.7928 | -30.7921 | 7.417 | 8.088 | alpha_score >= 83<br>prob_clean >= 29.5 |
| 67 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4909 | 23.636 | 30.864 | 7.228 | -4.8507 | -2.645 | 2.2057 | -21.1454 | 11.538 | 4.467 | alpha_score >= 87<br>regime_avg_chg <= 1.85 |
| 68 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5394 | 23.636 | 33.708 | 10.072 | -4.8507 | -3.0698 | 1.7809 | -30.1013 | 7.307 | 8.226 | theme_risk == ['KOSDAQ_SWING_CLEAN_PROB_GUARD', 'KOSDAQ_SWING_PROBATION']<br>volume_ratio <= 0.8 |
| 69 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3554 | 28.313 | 37.288 | 8.975 | -3.2644 | 0.0277 | 3.2921 | -24.2948 | 8.179 | 4.952 | alpha_score >= 83<br>expected_return_1d_pct >= -0.15 |
| 70 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.5249 | 33.149 | 47.368 | 14.219 | -1.872 | 1.1436 | 3.0156 | -20.6854 | 2.768 | -3.96 | phase25_prob <= 28.3<br>regime_breadth_pct >= 32.06 |
| 71 | shadow_candidate | KOSDAQ | top5_exception | 5d | 2 | 0.5075 | 24.627 | 32.353 | 7.726 | -6.5535 | -3.7416 | 2.8119 | -27.3349 | 3.556 | 1.031 | alpha_score >= 70<br>priority_rank <= 2 |
| 72 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.4612 | 26.531 | 32.743 | 6.212 | -4.4174 | -2.8053 | 1.6121 | -22.1512 | 11.656 | 10.511 | kosdaq_chg <= 0<br>volume_ratio <= 0.8 |
| 73 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.4204 | 26.531 | 35.922 | 9.391 | -4.4174 | -2.6941 | 1.7233 | -30.1013 | 11.124 | 6.757 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.8 |
| 74 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.4204 | 26.531 | 35.922 | 9.391 | -4.4174 | -2.6941 | 1.7233 | -30.1013 | 11.124 | 6.757 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.8905 |
| 75 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.4449 | 26.531 | 35.78 | 9.249 | -4.4174 | -2.7899 | 1.6275 | -30.1013 | 11.088 | 6.89 | phase25_variant == phase25_kosdaq_swing<br>volume_ratio <= 0.7345 |
| 76 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3714 | 26.531 | 35.165 | 8.634 | -4.4174 | -2.0617 | 2.3557 | -30.1013 | 10.11 | 7.536 | priority_rank >= 8<br>volume_ratio <= 0.7345 |
| 77 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.5394 | 23.636 | 33.708 | 10.072 | -4.8507 | -2.9071 | 1.9436 | -30.1013 | 6.184 | 7.103 | decision_score >= 100<br>volume_ratio <= 0.8 |
| 78 | shadow_candidate | KOSDAQ | top5_exception | 3d | 2 | 0.4061 | 23.636 | 32.836 | 9.2 | -4.8507 | -3.1914 | 1.6593 | -21.1454 | 9.806 | 5.057 | alpha_score >= 70<br>feature_quality == complete |
| 79 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3887 | 33.555 | 45.299 | 11.744 | -2.2237 | 1.072 | 3.2957 | -24.569 | 3.711 | -3.303 | conviction_score >= 74.75<br>regime_breadth_pct >= 32.06 |
| 80 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.4073 | 35.258 | 47.761 | 12.503 | -1.3139 | 1.1302 | 2.4441 | -20.6854 | 5.727 | -1.175 | phase25_variant == phase25_kospi_swing<br>regime_breadth_pct >= 32.06 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3515 win_delta=19.467 avg_delta=4.1772 :: alpha_score >= 70 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3515 win_delta=19.467 avg_delta=4.1772 :: alpha_score >= 70 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3818 win_delta=19.221 avg_delta=3.64 :: conviction_score >= 69.4 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3818 win_delta=19.221 avg_delta=3.64 :: conviction_score >= 69.4 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3818 win_delta=17.634 avg_delta=3.6122 :: alpha_score >= 70 / volume_ratio <= 0.758
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3939 win_delta=17.902 avg_delta=3.4866 :: decision_score >= 90 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3818 win_delta=17.634 avg_delta=3.3626 :: decision_score >= 86.3 / volume_ratio <= 0.8
- `KOSDAQ` `ranked_top20` `3d` level=shadow_candidate retain=0.3714 win_delta=15.227 avg_delta=3.5919 :: priority_rank >= 10 / regime_volatility_20d <= 2.22
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.3731 win_delta=19.373 avg_delta=3.7266 :: alpha_score >= 82 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.3731 win_delta=19.373 avg_delta=3.7266 :: alpha_score >= 82 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3758 win_delta=11.848 avg_delta=2.7359 :: kosdaq_chg <= 0.543 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3758 win_delta=11.848 avg_delta=2.7359 :: kosdaq_chg <= 0.543 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4485 win_delta=14.202 avg_delta=2.474 :: alpha_score >= 82 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4485 win_delta=14.202 avg_delta=2.474 :: alpha_score >= 82 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4788 win_delta=13.073 avg_delta=2.1312 :: alpha_score >= 82 / volume_ratio <= 0.758
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3636 win_delta=9.697 avg_delta=2.6897 :: decision == WATCHLIST_ONLY / volume_ratio <= 1.01
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.3881 win_delta=17.681 avg_delta=3.2131 :: alpha_score >= 87 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4606 win_delta=13.206 avg_delta=2.2153 :: alpha_score >= 87 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4606 win_delta=13.206 avg_delta=2.2153 :: alpha_score >= 87 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.503 win_delta=10.099 avg_delta=2.8093 :: alpha_score >= 70 / priority_rank >= 10
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4606 win_delta=13.206 avg_delta=2.5776 :: conviction_score >= 74.5 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4606 win_delta=13.206 avg_delta=2.5776 :: conviction_score >= 74.5 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4242 win_delta=10.65 avg_delta=2.4161 :: kosdaq_chg <= 0 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4242 win_delta=10.65 avg_delta=2.4161 :: kosdaq_chg <= 0 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4909 win_delta=12.166 avg_delta=1.897 :: alpha_score >= 87 / volume_ratio <= 0.758
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4848 win_delta=12.614 avg_delta=2.4188 :: alpha_score >= 93 / volume_ratio <= 0.8
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4848 win_delta=12.614 avg_delta=2.4188 :: alpha_score >= 93 / volume_ratio <= 0.88
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.4909 win_delta=12.166 avg_delta=2.2369 :: conviction_score >= 74.5 / volume_ratio <= 0.758
- `KOSDAQ` `top5_exception` `5d` level=shadow_candidate retain=0.4328 win_delta=13.304 avg_delta=3.6372 :: kosdaq_chg <= 0 / selection_lane == 1d
- `KOSDAQ` `top5_exception` `3d` level=shadow_candidate retain=0.3939 win_delta=13.287 avg_delta=2.6469 :: regime_breadth_pct >= 32.06 / volume_ratio <= 0.8

## Diagnostics

- `KOSPI` `top5_exception` rows=508 days=39 cut=2026-05-07 predicates=174 levels={'coverage_fail': 8321, 'diagnostic': 1799, 'sample_fail': 627, 'shadow_candidate': 125}
- `KOSPI` `ranked_top20` rows=1082 days=39 cut=2026-05-07 predicates=216 levels={'coverage_fail': 8744, 'diagnostic': 2457, 'sample_fail': 1620, 'shadow_candidate': 151}
- `KOSDAQ` `top5_exception` rows=530 days=39 cut=2026-05-07 predicates=223 levels={'sample_fail': 4830, 'coverage_fail': 3940, 'diagnostic': 2413, 'shadow_candidate': 125}
- `KOSDAQ` `ranked_top20` rows=900 days=39 cut=2026-05-07 predicates=245 levels={'sample_fail': 5226, 'coverage_fail': 4747, 'diagnostic': 2328, 'shadow_candidate': 74}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
