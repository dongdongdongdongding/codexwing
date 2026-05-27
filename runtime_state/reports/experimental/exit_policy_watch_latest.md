# Exit Policy Watch

- generated_at: `2026-05-27T10:53:14.481859+00:00`
- report_version: `exit_policy_watch_v1`
- optimizer_generated_at: `2026-05-27T10:51:46.373651+00:00`
- friction_pct: `0.35`
- watch_count: `11`
- blocked_path_warning_count: `52`
- ready_review_count: `0`

## Watch Rows

| Rank | State | Market | Cohort | Label | Model | TopN | N | Days | Target | Stop | Exit Win | Net Exit Avg | Exit Min | Close Avg5 | Close Min5 | Stop First | Path Warn | Failed Checks |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | prob_clean | 5 | 78 | 17 | +5.00% | -3.00% | 93.59% | +4.14% | -3.00% | -0.14% | -33.30% | 6.41% | 20.51% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 2 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | exception_leader | ordered_5d_5v3_lowmae | volume_ratio | 5 | 57 | 16 | +5.00% | -3.00% | 94.74% | +4.23% | -3.00% | +1.58% | -24.75% | 5.26% | 24.56% | label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 3 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | prob_clean | 3 | 50 | 17 | +5.00% | -3.00% | 94.00% | +4.17% | -3.00% | -1.25% | -33.30% | 6.00% | 20.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 4 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | relative_rank_score | 3 | 50 | 17 | +5.00% | -3.00% | 92.00% | +4.01% | -3.00% | -3.13% | -33.30% | 8.00% | 18.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 5 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | loss_risk_score | 3 | 50 | 17 | +5.00% | -3.00% | 90.00% | +3.85% | -3.00% | -1.10% | -33.30% | 10.00% | 16.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 6 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | expected_edge_score | 3 | 50 | 17 | +5.00% | -3.00% | 90.00% | +3.85% | -3.00% | -0.61% | -33.30% | 10.00% | 18.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 7 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | decision_score | 3 | 50 | 17 | +5.00% | -3.00% | 90.00% | +3.85% | -3.00% | -1.48% | -33.30% | 10.00% | 12.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 8 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | phase25_shadow_prob | 3 | 50 | 17 | +5.00% | -3.00% | 90.00% | +3.85% | -3.00% | -0.71% | -21.54% | 10.00% | 14.00% | label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 9 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | whale_score | 3 | 50 | 17 | +5.00% | -3.00% | 90.00% | +3.85% | -3.00% | -3.18% | -25.94% | 10.00% | 18.00% | avg_return_gate,bad_path_gate,tail_loss_gate |
| 10 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | exception_leader | ordered_5d_5v3_lowmae | volume_ratio | 3 | 43 | 16 | +5.00% | -3.00% | 95.35% | +4.28% | -3.00% | -0.02% | -24.75% | 4.65% | 23.26% | label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 11 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | explosive_leader | ordered_5d_5v3_lowmae | expected_edge_score | 1 | 17 | 17 | +5.00% | -3.00% | 100.00% | +4.65% | +5.00% | -0.72% | -33.30% | 0.00% | 23.53% | enough_samples,avg_return_gate,bad_path_gate,tail_loss_gate |

## Blocked By Path Warning

| Rank | Market | Cohort | Label | Model | TopN | N | Days | Exit Win | Net Exit Avg | Path Warn | Failed Checks |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 131 | 27 | 90.08% | +3.86% | 32.82% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 2 | KOSPI | core_trend | ordered_5d_5v3_lowmae | whale_score | 5 | 131 | 27 | 91.60% | +4.01% | 35.88% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 3 | KOSPI | core_trend | ordered_5d_5v3_lowmae | volume_ratio | 5 | 131 | 27 | 92.37% | +4.04% | 36.64% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 4 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | whale_score | 5 | 130 | 27 | 90.00% | +3.89% | 38.46% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 5 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | relative_rank_score | 5 | 129 | 27 | 91.47% | +3.97% | 31.01% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 6 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 129 | 27 | 93.80% | +4.15% | 31.78% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 7 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | prob_clean | 5 | 129 | 27 | 90.70% | +3.91% | 33.33% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 8 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 129 | 27 | 90.70% | +3.91% | 34.11% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 9 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | relative_rank_score | 5 | 129 | 26 | 92.25% | +4.03% | 31.01% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 10 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 129 | 26 | 92.25% | +4.03% | 32.56% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 11 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 129 | 26 | 92.25% | +4.03% | 32.56% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 12 | KOSDAQ | top5_exception | ordered_5d_5v3_lowmae | volume_ratio | 5 | 112 | 27 | 90.18% | +3.86% | 37.50% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 13 | KOSDAQ | top5_exception | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 112 | 27 | 90.18% | +3.86% | 38.39% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 14 | KOSDAQ | top5_exception | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 112 | 27 | 91.07% | +3.94% | 39.29% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 15 | KOSPI | core_trend | ordered_5d_5v3_lowmae | whale_score | 3 | 81 | 27 | 90.12% | +3.92% | 34.57% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 16 | KOSPI | core_trend | ordered_5d_5v3_lowmae | volume_ratio | 3 | 81 | 27 | 92.59% | +4.06% | 35.80% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 17 | KOSPI | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 3 | 81 | 27 | 91.36% | +3.96% | 35.80% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 18 | KOSPI | core_trend | ordered_5d_5v3_lowmae | relative_rank_score | 3 | 81 | 27 | 91.36% | +3.96% | 39.51% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 19 | KOSPI | core_trend | ordered_5d_5v3_lowmae | loss_risk_score | 3 | 81 | 27 | 91.36% | +3.96% | 39.51% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 20 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | relative_rank_score | 3 | 79 | 27 | 93.67% | +4.14% | 29.11% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 21 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | loss_risk_score | 3 | 79 | 27 | 97.47% | +4.45% | 30.38% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate |
| 22 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | prob_clean | 3 | 79 | 27 | 91.14% | +3.94% | 30.38% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 23 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | prob_clean | 3 | 79 | 27 | 93.67% | +4.14% | 31.65% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 24 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | whale_score | 3 | 79 | 27 | 91.14% | +4.00% | 32.91% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 25 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | relative_rank_score | 3 | 79 | 27 | 91.14% | +3.94% | 41.77% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 26 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | relative_rank_score | 3 | 78 | 26 | 91.03% | +3.93% | 28.20% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 27 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | loss_risk_score | 3 | 78 | 26 | 93.59% | +4.14% | 29.49% | path_warning_gate,label_win_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 28 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | expected_edge_score | 3 | 78 | 26 | 91.03% | +3.93% | 30.77% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 29 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 3 | 78 | 26 | 91.03% | +3.93% | 30.77% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 30 | KOSDAQ | top5_exception | ordered_5d_5v3_lowmae | loss_risk_score | 3 | 75 | 27 | 93.33% | +4.12% | 34.67% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |

## Baselines

### KOSDAQ

| Cohort | N | Win5 | Avg5 | Min5 | Max5 | Bad Path | Clean Riser |
|---|---:|---:|---:|---:|---:|---:|---:|
| Top5 | 434 | 52.77% | +1.94% | -46.31% | +65.65% | 66.59% | 11.52% |
| Exception Leader | 278 | 54.68% | +1.92% | -34.81% | +65.65% | 69.78% | 13.31% |
| Practical 80 Gate | 14 | 92.86% | +19.95% | -2.58% | +37.81% | 7.14% | 50.00% |

### KOSPI

| Cohort | N | Win5 | Avg5 | Min5 | Max5 | Bad Path | Clean Riser |
|---|---:|---:|---:|---:|---:|---:|---:|
| Top5 | 498 | 51.20% | +1.97% | -31.21% | +112.16% | 59.04% | 9.24% |
| Exception Leader | 93 | 79.57% | +7.58% | -16.61% | +31.66% | 34.41% | 18.28% |
| Practical 80 Gate | 169 | 89.94% | +9.09% | -26.36% | +54.30% | 14.20% | 28.99% |

## Notes
- EXIT-WATCH is not a production scanner replacement.
- Close-hold failures remain visible through failed_checks and close_avg/min fields.
- Net exit average subtracts configured friction_pct for fees/slippage/tax approximation.
