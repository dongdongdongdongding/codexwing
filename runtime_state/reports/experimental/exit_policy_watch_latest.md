# Exit Policy Watch

- generated_at: `2026-05-27T07:49:04.827487+00:00`
- report_version: `exit_policy_watch_v1`
- optimizer_generated_at: `2026-05-27T07:46:27.958414+00:00`
- friction_pct: `0.35`
- watch_count: `0`
- blocked_path_warning_count: `162`
- ready_review_count: `0`

## Watch Rows

| Rank | State | Market | Cohort | Label | Model | TopN | N | Days | Target | Stop | Exit Win | Net Exit Avg | Exit Min | Close Avg5 | Close Min5 | Stop First | Path Warn | Failed Checks |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

## Blocked By Path Warning

| Rank | Market | Cohort | Label | Model | TopN | N | Days | Exit Win | Net Exit Avg | Path Warn | Failed Checks |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | prob_clean | 5 | 72 | 16 | 97.22% | +4.43% | 63.89% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 2 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | decision_score | 5 | 72 | 16 | 98.61% | +4.54% | 66.67% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 3 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | phase25_prob | 5 | 72 | 16 | 95.83% | +4.32% | 66.67% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 4 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | expected_edge_score | 5 | 72 | 16 | 95.83% | +4.32% | 66.67% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 5 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 72 | 16 | 95.83% | +4.32% | 68.06% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 6 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | whale_score | 5 | 72 | 16 | 94.44% | +4.21% | 68.06% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 7 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 72 | 16 | 97.22% | +4.43% | 69.44% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 8 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | volume_ratio | 5 | 72 | 16 | 98.61% | +4.54% | 72.22% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 9 | KOSPI | ranked_top20 | ordered_5d_5v3_lowmae | relative_rank_score | 5 | 72 | 16 | 95.83% | +4.32% | 72.22% | path_warning_gate,bad_path_gate,tail_loss_gate |
| 10 | KOSPI | core_trend | ordered_5d_5v3_lowmae | phase25_prob | 5 | 71 | 16 | 98.59% | +4.54% | 66.20% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 11 | KOSPI | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 71 | 16 | 97.18% | +4.42% | 66.20% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 12 | KOSPI | core_trend | ordered_5d_5v3_lowmae | prob_clean | 5 | 71 | 16 | 95.78% | +4.31% | 66.20% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 13 | KOSPI | core_trend | ordered_5d_5v3_lowmae | expected_edge_score | 5 | 71 | 16 | 94.37% | +4.20% | 66.20% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 14 | KOSPI | core_trend | ordered_5d_5v3_lowmae | decision_score | 5 | 71 | 16 | 94.37% | +4.20% | 66.20% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 15 | KOSPI | core_trend | ordered_5d_5v3_lowmae | relative_rank_score | 5 | 71 | 16 | 97.18% | +4.42% | 69.01% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 16 | KOSPI | core_trend | ordered_5d_5v3_lowmae | whale_score | 5 | 71 | 16 | 92.96% | +4.09% | 69.01% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 17 | KOSPI | core_trend | ordered_5d_5v3_lowmae | volume_ratio | 5 | 71 | 16 | 97.18% | +4.42% | 70.42% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 18 | KOSPI | core_trend | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 71 | 16 | 98.59% | +4.54% | 71.83% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 19 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 67 | 14 | 98.51% | +4.53% | 71.64% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 20 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | loss_risk_score | 5 | 67 | 14 | 98.51% | +4.53% | 71.64% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 21 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | phase25_prob | 5 | 67 | 14 | 97.02% | +4.41% | 71.64% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 22 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | volume_ratio | 5 | 67 | 14 | 98.51% | +4.53% | 73.13% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 23 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | relative_rank_score | 5 | 67 | 14 | 98.51% | +4.53% | 73.13% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 24 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | prob_clean | 5 | 67 | 14 | 97.02% | +4.41% | 73.13% | path_warning_gate,avg_return_gate,tail_loss_gate |
| 25 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | expected_edge_score | 5 | 67 | 14 | 97.02% | +4.41% | 73.13% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 26 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | decision_score | 5 | 67 | 14 | 97.02% | +4.41% | 73.13% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate,fold_stability_gate |
| 27 | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | whale_score | 5 | 67 | 14 | 95.52% | +4.29% | 73.13% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 28 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | decision_score | 5 | 66 | 14 | 100.00% | +4.65% | 71.21% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 29 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | 5 | 66 | 14 | 100.00% | +4.65% | 71.21% | path_warning_gate,label_win_gate,avg_return_gate,bad_path_gate,tail_loss_gate |
| 30 | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | phase25_prob | 5 | 66 | 14 | 98.48% | +4.53% | 72.73% | path_warning_gate,avg_return_gate,bad_path_gate,tail_loss_gate |

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
