# Exit Policy Watch

- generated_at: `2026-08-14T00:56:02.967671+00:00`
- report_version: `exit_policy_watch_v1`
- optimizer_generated_at: `2026-08-13T22:10:15.511818+00:00`
- friction_pct: `0.35`
- watch_count: `11`
- blocked_path_warning_count: `0`
- ready_review_count: `0`

## Watch Rows

| Rank | State | Market | Cohort | Label | Model | TopN | N | Days | Target | Stop | Exit Win | Net Exit Avg | Exit Min | Close Avg5 | Close Min5 | Stop First | Path Warn | Failed Checks |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_10v5 | expected_edge_score | None | 1 | 1 | +10.00% | -5.00% | 100.00% | +9.65% | +10.00% | +19.93% | +19.93% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 2 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | ranked_top20 | ordered_5d_10v5 | phase25_shadow_prob | None | 1 | 1 | +10.00% | -5.00% | 100.00% | +9.65% | +10.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 3 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_10v5 | phase25_shadow_prob | None | 1 | 1 | +10.00% | -5.00% | 100.00% | +9.65% | +10.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 4 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_8v5 | expected_edge_score | None | 1 | 1 | +8.00% | -5.00% | 100.00% | +7.65% | +8.00% | +19.93% | +19.93% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 5 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | ranked_top20 | ordered_5d_8v5 | phase25_shadow_prob | None | 1 | 1 | +8.00% | -5.00% | 100.00% | +7.65% | +8.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 6 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_8v5 | phase25_shadow_prob | None | 1 | 1 | +8.00% | -5.00% | 100.00% | +7.65% | +8.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 7 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_5v5 | expected_edge_score | None | 1 | 1 | +5.00% | -5.00% | 100.00% | +4.65% | +5.00% | +19.93% | +19.93% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 8 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | ranked_top20 | ordered_5d_5v5 | phase25_shadow_prob | None | 1 | 1 | +5.00% | -5.00% | 100.00% | +4.65% | +5.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 9 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | ranked_top20 | ordered_5d_5v3_lowmae | phase25_shadow_prob | None | 1 | 1 | +5.00% | -3.00% | 100.00% | +4.65% | +5.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 10 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_5v5 | phase25_shadow_prob | None | 1 | 1 | +5.00% | -5.00% | 100.00% | +4.65% | +5.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |
| 11 | FORWARD_TRACK_SMALL_SAMPLE | KOSDAQ | core_trend | ordered_5d_5v3_lowmae | phase25_shadow_prob | None | 1 | 1 | +5.00% | -3.00% | 100.00% | +4.65% | +5.00% | +10.56% | +10.56% | 0.00% | 0.00% | enough_samples,enough_days,enough_folds |

## Blocked By Path Warning

| Rank | Market | Cohort | Label | Model | TopN | N | Days | Exit Win | Net Exit Avg | Path Warn | Failed Checks |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|

## Baselines

### KOSDAQ

| Cohort | N | Win5 | Avg5 | Min5 | Max5 | Bad Path | Clean Riser |
|---|---:|---:|---:|---:|---:|---:|---:|
| Top5 | 1197 | 44.28% | -0.82% | -46.31% | +65.65% | 74.77% | 7.27% |
| Exception Leader | 695 | 44.75% | -0.97% | -38.12% | +65.65% | 76.26% | 8.20% |
| Practical 80 Gate | 0 | - | - | - | - | - | - |

## Notes
- EXIT-WATCH is not a production scanner replacement.
- Close-hold failures remain visible through failed_checks and close_avg/min fields.
- Net exit average subtracts configured friction_pct for fees/slippage/tax approximation.
