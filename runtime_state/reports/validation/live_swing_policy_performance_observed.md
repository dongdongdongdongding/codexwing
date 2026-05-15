# Live Swing Policy Performance

- generated_at: `2026-05-15T16:50:19.605049+00:00`
- source_rows: `16741`
- quality_scope: `observed_archive`
- quality_note: Observed policy performance ignores legacy validation_excluded flags so old resolved rows can be audited. Use --strict-quality for gold-style feature-complete validation.
- goal: source OHLCV High 기준 hit_5pct_within_5d >= 70%, avg_max_high_return_5d >= +5%, target_rows >= 30

## Policies

### KOSPI
- policy: `exception_leader OR expected_edge_score>=5`
- rows: `501`
- target_rows: `428`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `74.85`
- hit_5pct_within_5d_high_pct: `80.607`
- avg_max_high_return_5d_pct: `13.9386`
- median_max_high_return_5d_pct: `11.3661`
- min_max_high_return_5d_pct: `-0.8616`
- max_max_high_return_5d_pct: `68.8427`
- hit_5pct_within_observed_5d_pct: `80.607`
- avg_return_5d_pct: `8.2569`
- median_return_5d_pct: `7.1259`
- min_return_5d_pct: `-26.3577`
- max_return_5d_pct: `54.3027`
- loss_5pct_or_worse_5d_pct: `7.984`
- hit_5pct_or_better_close_5d_pct: `57.086`
- avg_max_return_observed_5d_pct: `13.9386`
- passes_goal: `True`
- close_5d_quality_pass: `True`

### KOSDAQ
- policy: `exception_leader AND trend=UP`
- rows: `97`
- target_rows: `92`
- target_definition: `forward_high_within_5d`
- win_5d_pct: `69.072`
- hit_5pct_within_5d_high_pct: `75.0`
- avg_max_high_return_5d_pct: `13.1409`
- median_max_high_return_5d_pct: `11.1234`
- min_max_high_return_5d_pct: `-5.3398`
- max_max_high_return_5d_pct: `73.703`
- hit_5pct_within_observed_5d_pct: `75.0`
- avg_return_5d_pct: `5.3844`
- median_return_5d_pct: `4.5646`
- min_return_5d_pct: `-22.0679`
- max_return_5d_pct: `65.653`
- loss_5pct_or_worse_5d_pct: `22.68`
- hit_5pct_or_better_close_5d_pct: `48.454`
- avg_max_return_observed_5d_pct: `13.1409`
- passes_goal: `True`
- close_5d_quality_pass: `False`
