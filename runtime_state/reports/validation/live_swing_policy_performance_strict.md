# Live Swing Policy Performance

- generated_at: `2026-06-29T07:03:25.213123+00:00`
- source_rows: `30766`
- quality_scope: `strict_feature_complete`
- quality_note: Strict policy performance excludes validation_excluded and dummy rows.
- goal: source OHLCV High 기준 hit_5pct_within_5d >= 70%, avg_max_high_return_5d >= +5%, target_rows >= 30

## Policies

### KOSPI
- policy: `RETRACTED legacy audit: exception_leader OR expected_edge_score>=5`
- rows: `125`
- target_rows: `43`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `28.0`
- hit_5pct_within_5d_high_pct: `41.86`
- avg_max_high_return_5d_pct: `8.6978`
- median_max_high_return_5d_pct: `3.3046`
- min_max_high_return_5d_pct: `-1.0`
- max_max_high_return_5d_pct: `69.4118`
- hit_5pct_within_observed_5d_pct: `41.86`
- avg_return_5d_pct: `-3.3574`
- median_return_5d_pct: `-4.5599`
- min_return_5d_pct: `-26.6541`
- max_return_5d_pct: `41.8953`
- loss_5pct_or_worse_5d_pct: `46.4`
- hit_5pct_or_better_close_5d_pct: `18.4`
- avg_max_return_observed_5d_pct: `8.6978`
- passes_goal: `False`
- close_5d_quality_pass: `False`

### KOSDAQ
- policy: `RETRACTED legacy audit: exception_leader AND trend=UP`
- rows: `26`
- target_rows: `19`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `19.231`
- hit_5pct_within_5d_high_pct: `57.895`
- avg_max_high_return_5d_pct: `7.1981`
- median_max_high_return_5d_pct: `5.7067`
- min_max_high_return_5d_pct: `-0.6173`
- max_max_high_return_5d_pct: `24.3599`
- hit_5pct_within_observed_5d_pct: `57.895`
- avg_return_5d_pct: `-7.1765`
- median_return_5d_pct: `-8.4417`
- min_return_5d_pct: `-25.9487`
- max_return_5d_pct: `16.7081`
- loss_5pct_or_worse_5d_pct: `65.385`
- hit_5pct_or_better_close_5d_pct: `15.385`
- avg_max_return_observed_5d_pct: `7.1981`
- passes_goal: `False`
- close_5d_quality_pass: `False`
