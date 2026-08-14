# Loss Exclusion Guard Mining

- generated_at: `2026-06-14T16:54:17.869032+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `5029`
- quality_scope: `all`
- guard_count: `64226`
- production_candidate_count: `0`
- shadow_candidate_count: `9152`
- guard_levels: `{'coverage_fail': 23037, 'sample_fail': 19319, 'diagnostic': 12718, 'shadow_candidate': 9152}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.386 | 32.895 | 64.773 | 31.878 | -2.1335 | 3.7741 | 5.9076 | -18.3014 | 23.066 | -3.768 | foreigner_1d >= -16831<br>retail_10d >= -693596 |
| 2 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.386 | 32.895 | 64.773 | 31.878 | -2.1335 | 3.7741 | 5.9076 | -18.3014 | 23.066 | -3.768 | foreigner_1d >= -16831<br>whale_flow_10d <= 693596 |
| 3 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.386 | 32.895 | 64.773 | 31.878 | -2.1335 | 3.7741 | 5.9076 | -18.3014 | 23.066 | -3.768 | foreigner >= 0<br>retail_10d >= -693596 |
| 4 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.386 | 32.895 | 64.773 | 31.878 | -2.1335 | 3.7741 | 5.9076 | -18.3014 | 23.066 | -3.768 | foreigner >= 0<br>whale_flow_10d <= 693596 |
| 5 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreigner_10d <= 1.0351e+06<br>foreigner_1d >= -16831 |
| 6 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreigner_10d <= 623668<br>foreigner_1d >= -16831 |
| 7 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreigner_10d <= 1.0351e+06<br>foreigner >= 0 |
| 8 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreign_flow >= 0<br>foreigner_10d <= 1.0351e+06 |
| 9 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreigner_10d <= 1.0351e+06<br>foreigner_1d >= 0 |
| 10 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | day_return_pct <= 6.26<br>foreigner_10d <= 1.0351e+06 |
| 11 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.7586 | 5.8921 | -18.3014 | 22.505 | -4.069 | foreigner_10d <= 623668<br>foreigner >= 0 |
| 12 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_completeness >= 1<br>retail_3d <= 9274.5 |
| 13 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_completeness >= 1<br>whale_flow_3d >= -9274.5 |
| 14 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_completeness >= 1<br>regime_avg_chg >= -0.68 |
| 15 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_completeness >= 1<br>whale_flow_3d >= 0 |
| 16 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_completeness >= 1<br>whale_trend == 🔥 당일+3일 순매수 |
| 17 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_quality == complete<br>retail_3d <= 9274.5 |
| 18 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_quality == complete<br>whale_flow_3d >= -9274.5 |
| 19 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_quality == complete<br>regime_avg_chg >= -0.68 |
| 20 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_quality == complete<br>whale_flow_3d >= 0 |
| 21 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_quality == complete<br>whale_trend == 🔥 당일+3일 순매수 |
| 22 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_origin == scanner_full<br>retail_3d <= 9274.5 |
| 23 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_origin == scanner_full<br>whale_flow_3d >= -9274.5 |
| 24 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_origin == scanner_full<br>regime_avg_chg >= -0.68 |
| 25 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_origin == scanner_full<br>whale_flow_3d >= 0 |
| 26 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6363 | 5.7698 | -18.3014 | 22.505 | -4.069 | feature_origin == scanner_full<br>whale_trend == 🔥 당일+3일 순매수 |
| 27 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreigner_1d >= -16831<br>regime_avg_chg >= -0.68 |
| 28 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreigner >= -19925<br>regime_avg_chg >= -0.68 |
| 29 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreigner >= -19925<br>retail_10d >= -693596 |
| 30 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreigner >= -19925<br>whale_flow_10d <= 693596 |
| 31 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreign_flow >= -19925<br>regime_avg_chg >= -0.68 |
| 32 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreign_flow >= -19925<br>retail_10d >= -693596 |
| 33 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreign_flow >= -19925<br>whale_flow_10d <= 693596 |
| 34 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3816 | 32.895 | 64.368 | 31.473 | -2.1335 | 3.6109 | 5.7444 | -18.3014 | 22.505 | -4.069 | foreigner >= 0<br>regime_avg_chg >= -0.68 |
| 35 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3556 | 24.444 | 52.083 | 27.639 | -4.0864 | 1.9425 | 6.0289 | -18.3014 | 25.556 | 0.509 | position == 🚀 상승 (Rising)<br>retail_3d <= 56938.2 |
| 36 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3556 | 24.444 | 52.083 | 27.639 | -4.0864 | 1.9425 | 6.0289 | -18.3014 | 25.556 | 0.509 | position == 🚀 상승 (Rising)<br>whale_flow_3d >= -56938.2 |
| 37 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.363 | 24.444 | 51.02 | 26.576 | -4.0864 | 1.8842 | 5.9706 | -18.3014 | 26.576 | 0.892 | position == 🚀 상승 (Rising)<br>retail_3d <= -573 |
| 38 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.363 | 24.444 | 51.02 | 26.576 | -4.0864 | 1.8842 | 5.9706 | -18.3014 | 26.576 | 0.892 | position == 🚀 상승 (Rising)<br>whale_flow_3d >= 0 |
| 39 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.363 | 24.444 | 51.02 | 26.576 | -4.0864 | 1.8842 | 5.9706 | -18.3014 | 26.576 | 0.892 | position == 🚀 상승 (Rising)<br>whale_flow_3d >= 573 |
| 40 | shadow_candidate | KOSPI | ranked_top20 | 3d | 1 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01 |
| 41 | shadow_candidate | KOSPI | ranked_top20 | 3d | 1 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.12 |
| 42 | shadow_candidate | KOSPI | ranked_top20 | 3d | 1 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.13 |
| 43 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | flow_window == 1d<br>regime_volatility_20d >= 2.01 |
| 44 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | feature_completeness >= 1<br>regime_volatility_20d >= 2.01 |
| 45 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | feature_quality == complete<br>regime_volatility_20d >= 2.01 |
| 46 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | feature_origin == scanner_full<br>regime_volatility_20d >= 2.01 |
| 47 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | fund_status == Pass<br>regime_volatility_20d >= 2.01 |
| 48 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution >= -239882<br>regime_volatility_20d >= 2.01 |
| 49 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_flow >= -239882<br>regime_volatility_20d >= 2.01 |
| 50 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_1d >= -231019<br>regime_volatility_20d >= 2.01 |
| 51 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail <= 0 |
| 52 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail_flow <= 0 |
| 53 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>whale_flow_1d >= 0 |
| 54 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail_3d <= 73879.5 |
| 55 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>whale_flow_3d >= -73879.5 |
| 56 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_10d >= -580704<br>regime_volatility_20d >= 2.01 |
| 57 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution <= 200662<br>regime_volatility_20d >= 2.01 |
| 58 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_flow <= 200662<br>regime_volatility_20d >= 2.01 |
| 59 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_1d <= 222277<br>regime_volatility_20d >= 2.01 |
| 60 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail_3d <= 9274.5 |
| 61 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>whale_flow_3d >= -9274.5 |
| 62 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner_1d >= -16831<br>regime_volatility_20d >= 2.01 |
| 63 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner >= -19925<br>regime_volatility_20d >= 2.01 |
| 64 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreign_flow >= -19925<br>regime_volatility_20d >= 2.01 |
| 65 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner_10d <= 1.0351e+06<br>regime_volatility_20d >= 2.01 |
| 66 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner >= 0<br>regime_volatility_20d >= 2.01 |
| 67 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreign_flow >= 0<br>regime_volatility_20d >= 2.01 |
| 68 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner_1d >= 0<br>regime_volatility_20d >= 2.01 |
| 69 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution >= -73309<br>regime_volatility_20d >= 2.01 |
| 70 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_flow >= -73309<br>regime_volatility_20d >= 2.01 |
| 71 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_10d >= -393876<br>regime_volatility_20d >= 2.01 |
| 72 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | institution_1d >= -68605<br>regime_volatility_20d >= 2.01 |
| 73 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner <= 470521<br>regime_volatility_20d >= 2.01 |
| 74 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreign_flow <= 470521<br>regime_volatility_20d >= 2.01 |
| 75 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | foreigner_1d <= 486655<br>regime_volatility_20d >= 2.01 |
| 76 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_avg_chg >= -0.68<br>regime_volatility_20d >= 2.01 |
| 77 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail >= -483645 |
| 78 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail_flow >= -483645 |
| 79 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>retail_1d >= -485467 |
| 80 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.3772 | 32.895 | 63.953 | 31.058 | -2.1335 | 3.5932 | 5.7267 | -18.3014 | 21.93 | -4.376 | regime_volatility_20d >= 2.01<br>whale_flow_1d <= 485467 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.386 win_delta=31.878 avg_delta=5.9076 :: foreigner_1d >= -16831 / retail_10d >= -693596
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.386 win_delta=31.878 avg_delta=5.9076 :: foreigner_1d >= -16831 / whale_flow_10d <= 693596
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.386 win_delta=31.878 avg_delta=5.9076 :: foreigner >= 0 / retail_10d >= -693596
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.386 win_delta=31.878 avg_delta=5.9076 :: foreigner >= 0 / whale_flow_10d <= 693596
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreigner_10d <= 1.0351e+06 / foreigner_1d >= -16831
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreigner_10d <= 623668 / foreigner_1d >= -16831
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreigner_10d <= 1.0351e+06 / foreigner >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreign_flow >= 0 / foreigner_10d <= 1.0351e+06
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreigner_10d <= 1.0351e+06 / foreigner_1d >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: day_return_pct <= 6.26 / foreigner_10d <= 1.0351e+06
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.8921 :: foreigner_10d <= 623668 / foreigner >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_completeness >= 1 / retail_3d <= 9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_completeness >= 1 / whale_flow_3d >= -9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_completeness >= 1 / regime_avg_chg >= -0.68
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_completeness >= 1 / whale_flow_3d >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_completeness >= 1 / whale_trend == 🔥 당일+3일 순매수
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_quality == complete / retail_3d <= 9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_quality == complete / whale_flow_3d >= -9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_quality == complete / regime_avg_chg >= -0.68
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_quality == complete / whale_flow_3d >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_quality == complete / whale_trend == 🔥 당일+3일 순매수
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_origin == scanner_full / retail_3d <= 9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_origin == scanner_full / whale_flow_3d >= -9274.5
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_origin == scanner_full / regime_avg_chg >= -0.68
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_origin == scanner_full / whale_flow_3d >= 0
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7698 :: feature_origin == scanner_full / whale_trend == 🔥 당일+3일 순매수
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7444 :: foreigner_1d >= -16831 / regime_avg_chg >= -0.68
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7444 :: foreigner >= -19925 / regime_avg_chg >= -0.68
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7444 :: foreigner >= -19925 / retail_10d >= -693596
- `KOSPI` `ranked_top20` `3d` level=shadow_candidate retain=0.3816 win_delta=31.473 avg_delta=5.7444 :: foreigner >= -19925 / whale_flow_10d <= 693596

## Diagnostics

- `KOSPI` `top5` rows=563 days=52 cut=2026-05-22 predicates=621 levels={'sample_fail': 6063, 'coverage_fail': 1720, 'diagnostic': 1376, 'shadow_candidate': 1183}
- `KOSPI` `exception_leader` rows=99 days=19 cut=2026-06-01 predicates=29 levels={'sample_fail': 87}
- `KOSPI` `top5_exception` rows=662 days=52 cut=2026-05-22 predicates=627 levels={'shadow_candidate': 4137, 'coverage_fail': 3209, 'diagnostic': 1567, 'sample_fail': 1444}
- `KOSPI` `ranked_top20` rows=1319 days=52 cut=2026-05-22 predicates=654 levels={'coverage_fail': 3280, 'sample_fail': 3240, 'diagnostic': 2786, 'shadow_candidate': 1015}
- `KOSDAQ` `top5` rows=360 days=48 cut=2026-05-19 predicates=384 levels={'sample_fail': 4133, 'coverage_fail': 2316, 'diagnostic': 752, 'shadow_candidate': 379}
- `KOSDAQ` `exception_leader` rows=340 days=41 cut=2026-05-27 predicates=132 levels={'coverage_fail': 3240, 'diagnostic': 1388, 'sample_fail': 926, 'shadow_candidate': 254}
- `KOSDAQ` `top5_exception` rows=700 days=51 cut=2026-05-21 predicates=500 levels={'coverage_fail': 4704, 'diagnostic': 2101, 'sample_fail': 1406, 'shadow_candidate': 1202}
- `KOSDAQ` `ranked_top20` rows=1091 days=51 cut=2026-05-21 predicates=552 levels={'coverage_fail': 4568, 'diagnostic': 2748, 'sample_fail': 2020, 'shadow_candidate': 982}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
