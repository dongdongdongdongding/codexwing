# Loss Exclusion Guard Mining

- generated_at: `2026-05-27T06:04:37.219131+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `3697`
- guard_count: `1938`
- production_candidate_count: `0`
- shadow_candidate_count: `118`
- guard_levels: `{'diagnostic': 1007, 'sample_fail': 479, 'coverage_fail': 334, 'shadow_candidate': 118}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3521 | 45.07 | 64.0 | 18.93 | 0.4866 | 6.6116 | 6.125 | -16.1826 | 15.155 | 9.352 | ml_prob <= 41.6<br>priority_rank >= 10 |
| 2 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3803 | 45.07 | 62.963 | 17.893 | 0.4866 | 5.929 | 5.4424 | -16.1826 | 11.007 | 6.834 | priority_rank >= 10<br>prob_clean <= 34.76 |
| 3 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3803 | 45.07 | 62.963 | 17.893 | 0.4866 | 5.929 | 5.4424 | -16.1826 | 11.007 | 6.834 | alpha_score <= 72<br>priority_rank >= 10 |
| 4 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.3803 | 45.07 | 62.963 | 17.893 | 0.4866 | 5.929 | 5.4424 | -16.1826 | 11.007 | 6.834 | alpha_score <= 80<br>priority_rank >= 10 |
| 5 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3803 | 45.07 | 66.667 | 21.597 | 1.1593 | 4.379 | 3.2197 | -12.5074 | 11.007 | 6.834 | decision_score <= 79.64<br>priority_rank >= 10 |
| 6 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3803 | 45.07 | 66.667 | 21.597 | 1.1593 | 4.379 | 3.2197 | -12.5074 | 11.007 | 6.834 | decision_score <= 84.475<br>priority_rank >= 10 |
| 7 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.3662 | 45.07 | 61.538 | 16.468 | 0.4866 | 4.4349 | 3.9483 | -24.7525 | 13.001 | 9.967 | priority_rank >= 6.05 |
| 8 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 60.0 | 23.38 | -0.3714 | 3.1872 | 3.5586 | -3.8614 | 3.155 | -6.648 | decision == WATCHLIST<br>whale_score >= 90.1 |
| 9 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 60.0 | 23.38 | -0.3714 | 3.1872 | 3.5586 | -3.8614 | 3.155 | -6.648 | decision == WATCHLIST<br>tier == 🏆T1 |
| 10 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.3662 | 45.07 | 57.692 | 12.622 | 1.1593 | 3.1108 | 1.9515 | -12.5074 | 13.001 | 9.967 | priority_rank >= 6.05 |
| 11 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4507 | 36.62 | 56.25 | 19.63 | -0.3714 | 1.7514 | 2.1228 | -14.0774 | 2.905 | -2.773 | alpha_score >= 86<br>ml_prob >= 59 |
| 12 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 1 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | whale_score >= 90.1 |
| 13 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 1 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tier == 🏆T1 |
| 14 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tier == 🏆T1<br>whale_score >= 90.1 |
| 15 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>whale_score >= 90.1 |
| 16 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 82<br>whale_score >= 90.1 |
| 17 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>whale_score >= 90.1 |
| 18 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 86<br>whale_score >= 90.1 |
| 19 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 90<br>whale_score >= 90.1 |
| 20 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 90<br>whale_score >= 90.1 |
| 21 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 88<br>whale_score >= 90.1 |
| 22 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 82<br>whale_score >= 90.1 |
| 23 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 88<br>whale_score >= 90.1 |
| 24 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 72<br>whale_score >= 90.1 |
| 25 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 📈 Intraday Trend<br>whale_score >= 90.1 |
| 26 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | priority_rank >= 20<br>whale_score >= 90.1 |
| 27 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>tier == 🏆T1 |
| 28 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 82<br>tier == 🏆T1 |
| 29 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>tier == 🏆T1 |
| 30 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tier == 🏆T1<br>whale_score >= 100 |
| 31 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 86<br>tier == 🏆T1 |
| 32 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 90<br>tier == 🏆T1 |
| 33 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 90<br>tier == 🏆T1 |
| 34 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 88<br>tier == 🏆T1 |
| 35 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 82<br>tier == 🏆T1 |
| 36 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 88<br>tier == 🏆T1 |
| 37 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 72<br>tier == 🏆T1 |
| 38 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 📈 Intraday Trend<br>tier == 🏆T1 |
| 39 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | priority_rank >= 20<br>tier == 🏆T1 |
| 40 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>whale_score >= 100 |
| 41 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>tech_score <= 82 |
| 42 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>tech_score <= 88 |
| 43 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 80<br>tech_score <= 72 |
| 44 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score >= 82<br>whale_score >= 100 |
| 45 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>whale_score >= 100 |
| 46 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>tech_score <= 82 |
| 47 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>tech_score <= 88 |
| 48 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | position == 🚀 Intraday Breakout<br>tech_score <= 72 |
| 49 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | tech_score <= 88<br>whale_score >= 100 |
| 50 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 53.333 | 16.713 | -0.3714 | 2.3945 | 2.7659 | -3.8614 | 2.488 | -4.648 | alpha_score >= 86<br>tech_score <= 88 |
| 51 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4789 | 36.62 | 52.941 | 16.321 | -0.3714 | 1.5962 | 1.9676 | -14.0774 | 6.214 | -1.119 | alpha_score >= 86<br>decision == WATCHLIST |
| 52 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4507 | 36.62 | 53.125 | 16.505 | -0.3714 | 2.2478 | 2.6192 | -3.8614 | 2.905 | -5.898 | alpha_score >= 86<br>tech_score <= 82 |
| 53 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 1 | 0.5352 | 45.07 | 55.263 | 10.193 | 0.4866 | 3.5416 | 3.055 | -24.7525 | 6.523 | 6.931 | priority_rank >= 10 |
| 54 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 54.054 | 17.434 | -0.3714 | 1.5663 | 1.9377 | -14.0774 | 2.398 | -1.675 | alpha_score >= 90<br>ml_prob >= 59 |
| 55 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 54.054 | 17.434 | -0.3714 | 1.5663 | 1.9377 | -14.0774 | 2.398 | -1.675 | ml_prob >= 59<br>tech_score >= 90 |
| 56 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 1 | 0.5352 | 45.07 | 55.263 | 10.193 | 1.1593 | 3.268 | 2.1087 | -12.5074 | 6.523 | 6.931 | priority_rank >= 10 |
| 57 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4507 | 36.62 | 53.125 | 16.505 | -0.3714 | 1.6488 | 2.0202 | -14.0774 | 2.905 | -2.773 | alpha_score >= 80<br>decision == WATCHLIST |
| 58 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4507 | 36.62 | 53.125 | 16.505 | -0.3714 | 1.6488 | 2.0202 | -14.0774 | 2.905 | -2.773 | decision == WATCHLIST<br>position == 🚀 Intraday Breakout |
| 59 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3944 | 36.62 | 53.571 | 16.951 | -0.3714 | 1.6206 | 1.992 | -3.8614 | 2.012 | -6.791 | priority_rank >= 17<br>whale_score >= 90.1 |
| 60 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3944 | 36.62 | 53.571 | 16.951 | -0.3714 | 1.6206 | 1.992 | -3.8614 | 2.012 | -6.791 | priority_rank >= 17<br>tier == 🏆T1 |
| 61 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4225 | 36.62 | 50.0 | 13.38 | -0.3714 | 0.4664 | 0.8378 | -15.7969 | 5.822 | 8.685 | ml_prob >= 59<br>priority_rank >= 10 |
| 62 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.493 | 36.62 | 51.429 | 14.809 | -0.3714 | 1.5238 | 1.8952 | -14.0774 | 4.869 | -3.219 | decision == WATCHLIST<br>tech_score >= 88 |
| 63 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4789 | 36.62 | 50.0 | 13.38 | -0.3714 | 2.0235 | 2.3949 | -3.8614 | 3.273 | -7.001 | alpha_score >= 86<br>tech_score <= 72 |
| 64 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.4789 | 36.62 | 50.0 | 13.38 | -0.3714 | 2.0235 | 2.3949 | -3.8614 | 3.273 | -7.001 | alpha_score >= 86<br>position == 📈 Intraday Trend |
| 65 | shadow_candidate | KOSDAQ | ranked_top20 | 3d | 2 | 0.3521 | 45.07 | 56.0 | 10.93 | 1.1593 | 3.1808 | 2.0215 | -6.3758 | 11.155 | -6.648 | ml_prob <= 41.6<br>tech_score >= 88 |
| 66 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4225 | 45.07 | 53.333 | 8.263 | 0.4866 | 2.9651 | 2.4785 | -24.7525 | 5.822 | 8.685 | expected_edge_score <= 4.39<br>priority_rank >= 10 |
| 67 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4225 | 45.07 | 53.333 | 8.263 | 0.4866 | 2.9651 | 2.4785 | -24.7525 | 5.822 | 8.685 | expected_return_1d_pct <= 0.48<br>priority_rank >= 10 |
| 68 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4225 | 45.07 | 53.333 | 8.263 | 0.4866 | 2.9651 | 2.4785 | -24.7525 | 5.822 | 8.685 | expected_return_3d_pct <= 0.9<br>priority_rank >= 10 |
| 69 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 48.0 | 11.38 | -0.3714 | 1.5278 | 1.8992 | -3.8614 | 3.155 | -2.648 | priority_rank >= 13<br>whale_score >= 90.1 |
| 70 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 48.0 | 11.38 | -0.3714 | 1.5278 | 1.8992 | -3.8614 | 3.155 | -2.648 | alpha_score >= 80<br>priority_rank >= 13 |
| 71 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 48.0 | 11.38 | -0.3714 | 1.5278 | 1.8992 | -3.8614 | 3.155 | -2.648 | priority_rank >= 13<br>tech_score >= 82 |
| 72 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.3521 | 36.62 | 48.0 | 11.38 | -0.3714 | 1.5278 | 1.8992 | -3.8614 | 3.155 | -2.648 | position == 🚀 Intraday Breakout<br>priority_rank >= 13 |
| 73 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 1 | 0.5211 | 36.62 | 48.649 | 12.029 | -0.3714 | 1.214 | 1.5854 | -14.0774 | 2.398 | -1.675 | position == 🚀 Intraday Breakout |
| 74 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 48.649 | 12.029 | -0.3714 | 1.214 | 1.5854 | -14.0774 | 2.398 | -1.675 | alpha_score >= 86<br>tech_score >= 82 |
| 75 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 48.649 | 12.029 | -0.3714 | 1.214 | 1.5854 | -14.0774 | 2.398 | -1.675 | alpha_score >= 86<br>position == 🚀 Intraday Breakout |
| 76 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 48.649 | 12.029 | -0.3714 | 1.214 | 1.5854 | -14.0774 | 2.398 | -1.675 | position == 🚀 Intraday Breakout<br>tech_score >= 90 |
| 77 | shadow_candidate | KOSDAQ | ranked_top20 | 1d | 2 | 0.5211 | 36.62 | 48.649 | 12.029 | -0.3714 | 1.214 | 1.5854 | -14.0774 | 2.398 | -1.675 | position == 🚀 Intraday Breakout<br>tech_score >= 88 |
| 78 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4366 | 45.07 | 51.613 | 6.543 | 0.4866 | 2.8372 | 2.3506 | -24.7525 | 4.316 | 5.997 | expected_edge_score <= 3.98<br>priority_rank >= 10 |
| 79 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4366 | 45.07 | 51.613 | 6.543 | 0.4866 | 2.8372 | 2.3506 | -24.7525 | 4.316 | 5.997 | expected_return_1d_pct <= 0.44<br>priority_rank >= 10 |
| 80 | shadow_candidate | KOSDAQ | ranked_top20 | 5d | 2 | 0.4366 | 45.07 | 51.613 | 6.543 | 0.4866 | 2.8372 | 2.3506 | -24.7525 | 4.316 | 5.997 | expected_return_3d_pct <= 0.83<br>priority_rank >= 10 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3521 win_delta=18.93 avg_delta=6.125 :: ml_prob <= 41.6 / priority_rank >= 10
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3803 win_delta=17.893 avg_delta=5.4424 :: priority_rank >= 10 / prob_clean <= 34.76
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3803 win_delta=17.893 avg_delta=5.4424 :: alpha_score <= 72 / priority_rank >= 10
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3803 win_delta=17.893 avg_delta=5.4424 :: alpha_score <= 80 / priority_rank >= 10
- `KOSDAQ` `ranked_top20` `3d` level=shadow_candidate retain=0.3803 win_delta=21.597 avg_delta=3.2197 :: decision_score <= 79.64 / priority_rank >= 10
- `KOSDAQ` `ranked_top20` `3d` level=shadow_candidate retain=0.3803 win_delta=21.597 avg_delta=3.2197 :: decision_score <= 84.475 / priority_rank >= 10
- `KOSDAQ` `ranked_top20` `5d` level=shadow_candidate retain=0.3662 win_delta=16.468 avg_delta=3.9483 :: priority_rank >= 6.05
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.3521 win_delta=23.38 avg_delta=3.5586 :: decision == WATCHLIST / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.3521 win_delta=23.38 avg_delta=3.5586 :: decision == WATCHLIST / tier == 🏆T1
- `KOSDAQ` `ranked_top20` `3d` level=shadow_candidate retain=0.3662 win_delta=12.622 avg_delta=1.9515 :: priority_rank >= 6.05
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4507 win_delta=19.63 avg_delta=2.1228 :: alpha_score >= 86 / ml_prob >= 59
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tier == 🏆T1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tier == 🏆T1 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: alpha_score >= 80 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score >= 82 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: position == 🚀 Intraday Breakout / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: alpha_score >= 86 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: alpha_score >= 90 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score >= 90 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score >= 88 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score <= 82 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score <= 88 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score <= 72 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: position == 📈 Intraday Trend / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: priority_rank >= 20 / whale_score >= 90.1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: alpha_score >= 80 / tier == 🏆T1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tech_score >= 82 / tier == 🏆T1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: position == 🚀 Intraday Breakout / tier == 🏆T1
- `KOSDAQ` `ranked_top20` `1d` level=shadow_candidate retain=0.4225 win_delta=16.713 avg_delta=2.7659 :: tier == 🏆T1 / whale_score >= 100

## Diagnostics

- `KOSPI` `top5` rows=72 days=12 cut=2026-05-21 predicates=0 levels={}
- `KOSPI` `top5_exception` rows=85 days=12 cut=2026-05-21 predicates=9 levels={'sample_fail': 27}
- `KOSPI` `ranked_top20` rows=275 days=12 cut=2026-05-21 predicates=84 levels={'sample_fail': 252}
- `KOSDAQ` `top5` rows=68 days=11 cut=2026-04-15 predicates=0 levels={}
- `KOSDAQ` `top5_exception` rows=88 days=11 cut=2026-04-15 predicates=23 levels={'diagnostic': 222, 'coverage_fail': 56, 'sample_fail': 24}
- `KOSDAQ` `ranked_top20` rows=275 days=11 cut=2026-04-15 predicates=110 levels={'diagnostic': 785, 'coverage_fail': 278, 'sample_fail': 176, 'shadow_candidate': 118}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
