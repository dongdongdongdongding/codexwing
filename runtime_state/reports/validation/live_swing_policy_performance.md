# Live Swing Policy Performance

- generated_at: `2026-05-12T17:14:11.163492+00:00`
- source_rows: `15502`
- quality_scope: `strict_feature_complete`
- quality_note: Strict policy performance excludes validation_excluded and dummy rows.
- goal: source OHLCV High 기준 hit_5pct_within_5d >= 70%, avg_max_high_return_5d >= +5%, target_rows >= 30

## Policies

### KOSPI
- policy: `exception_leader OR expected_edge_score>=5`
- rows: `1`
- target_rows: `0`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `100.0`
- hit_5pct_within_5d_high_pct: `None`
- avg_max_high_return_5d_pct: `None`
- hit_5pct_within_observed_5d_pct: `None`
- avg_return_5d_pct: `5.9226`
- avg_max_return_observed_5d_pct: `None`
- passes_goal: `False`
- close_5d_quality_pass: `False`

### KOSDAQ
- policy: `exception_leader AND trend=UP`
- rows: `1`
- target_rows: `1`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `100.0`
- hit_5pct_within_5d_high_pct: `100.0`
- avg_max_high_return_5d_pct: `11.0619`
- hit_5pct_within_observed_5d_pct: `100.0`
- avg_return_5d_pct: `9.9115`
- avg_max_return_observed_5d_pct: `11.0619`
- passes_goal: `False`
- close_5d_quality_pass: `False`
