# NASDAQ High-Win High-Return Edge Search

- report_version: `nasdaq_high_win_edge_search_v1`
- generated_at: `2026-06-29T16:26:24.819332+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- rows_eligible: `1288099`
- symbols_eligible: `2301`
- date_range: `2020-01-02` ~ `2026-06-18`
- train_years: `2020-2023`
- holdout_years: `2024-2026`
- promotion_gate_thresholds: `{'min_n': 1000.0, 'min_days': 250.0, 'min_ret5_pct': 1.0, 'min_alpha5_net_cost_0_2_pct': 0.5, 'min_alpha5_net_cost_0_2_ci95_lo_pct': 0.0, 'min_ret5_pos_rate': 0.55, 'min_alpha5_net_cost_0_2_pos_rate': 0.55, 'min_touch3': 0.55, 'min_ft55': 0.55, 'max_dd3': 0.35, 'min_years_alpha5_net_0_2_pos': 5.0}`

## Summary

- candidates_evaluated: `3`
- promotion_ready_count: `0`
- holdout_gate_ready_count: `0`

## Top Holdout Candidates

- `pullback_not_broken` / `score_first_touch_trend` floor `10,000,000` top1 holdout n `587` days `587` ret5 `+1.021%` ret5_pos `53.83%` net `+0.735%` net_pos `54.68%` touch3 `37.82%` ft55 `43.95%` dd3 `32.20%` full_gate `BLOCK`
  - blockers: `ret5_below_min:0.725663<1, alpha5_net_cost_0_2_below_min:0.473323<0.5, ret5_pos_rate_below_min:0.535333<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.539333<0.55, touch3_below_min:0.364667<0.55, ft55_below_min:0.433333<0.55`
  - full_oos: n `1500` days `1500` ret5 `+0.726%` touch3 `36.47%` ft55 `43.33%` dd3 `31.80%`
- `quality_breakout` / `score_first_touch_trend` floor `100,000,000` top1 holdout n `611` days `611` ret5 `+0.551%` ret5_pos `56.14%` net `-0.040%` net_pos `53.68%` touch3 `44.68%` ft55 `48.61%` dd3 `40.43%` full_gate `BLOCK`
  - blockers: `ret5_below_min:0.820998<1, alpha5_net_cost_0_2_below_min:0.300772<0.5, alpha5_net_cost_0_2_ci95_lo_below_min:-0.225648<0, ret5_pos_rate_below_min:0.536616<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.510732<0.55, touch3_below_min:0.393939<0.55, ft55_below_min:0.432449<0.55, dd3_above_max:0.36553>0.35`
  - full_oos: n `1584` days `1584` ret5 `+0.821%` touch3 `39.39%` ft55 `43.24%` dd3 `36.55%`
- `breakout_confirmed` / `score_first_touch_trend` floor `100,000,000` top1 holdout n `618` days `618` ret5 `+0.373%` ret5_pos `54.53%` net `-0.175%` net_pos `52.43%` touch3 `45.95%` ft55 `48.87%` dd3 `41.42%` full_gate `BLOCK`
  - blockers: `ret5_below_min:0.725194<1, alpha5_net_cost_0_2_below_min:0.210127<0.5, alpha5_net_cost_0_2_ci95_lo_below_min:-0.317212<0, ret5_pos_rate_below_min:0.533251<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.505542<0.55, touch3_below_min:0.418103<0.55, ft55_below_min:0.450739<0.55, dd3_above_max:0.376847>0.35`
  - full_oos: n `1624` days `1624` ret5 `+0.725%` touch3 `41.81%` ft55 `45.07%` dd3 `37.68%`
