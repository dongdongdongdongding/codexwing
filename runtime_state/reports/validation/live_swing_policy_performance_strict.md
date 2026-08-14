# Live Swing Policy Performance

- generated_at: `2026-08-14T00:51:53.081812+00:00`
- source_rows: `44256`
- quality_scope: `strict_feature_complete`
- quality_note: Strict policy performance excludes validation_excluded and dummy rows.
- goal: source OHLCV High 기준 hit_5pct_within_5d >= 70%, avg_max_high_return_5d >= +5%, target_rows >= 30

## Policies

### KOSPI
- policy: `RETRACTED legacy audit: exception_leader OR expected_edge_score>=5`
- rows: `128`
- target_rows: `43`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `27.344`
- hit_5pct_within_5d_high_pct: `41.86`
- avg_max_high_return_5d_pct: `8.6978`
- median_max_high_return_5d_pct: `3.3046`
- min_max_high_return_5d_pct: `-1.0`
- max_max_high_return_5d_pct: `69.4118`
- hit_5pct_within_observed_5d_pct: `41.86`
- avg_return_5d_pct: `-3.4039`
- median_return_5d_pct: `-4.3287`
- min_return_5d_pct: `-26.6541`
- max_return_5d_pct: `41.8953`
- loss_5pct_or_worse_5d_pct: `46.094`
- hit_5pct_or_better_close_5d_pct: `17.969`
- avg_max_return_observed_5d_pct: `8.6978`
- passes_goal: `False`
- close_5d_quality_pass: `False`

### KOSDAQ
- policy: `RETRACTED legacy audit: exception_leader AND trend=UP`
- rows: `29`
- target_rows: `22`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `17.241`
- hit_5pct_within_5d_high_pct: `54.545`
- avg_max_high_return_5d_pct: `6.5465`
- median_max_high_return_5d_pct: `5.5103`
- min_max_high_return_5d_pct: `-0.6173`
- max_max_high_return_5d_pct: `24.3599`
- hit_5pct_within_observed_5d_pct: `54.545`
- avg_return_5d_pct: `-7.8183`
- median_return_5d_pct: `-8.4881`
- min_return_5d_pct: `-26.0569`
- max_return_5d_pct: `16.7081`
- loss_5pct_or_worse_5d_pct: `65.517`
- hit_5pct_or_better_close_5d_pct: `13.793`
- avg_max_return_observed_5d_pct: `6.5465`
- passes_goal: `False`
- close_5d_quality_pass: `False`
