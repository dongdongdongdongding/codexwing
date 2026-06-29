# NASDAQ Session Edge Search

- report_version: `nasdaq_session_edge_search_v1`
- generated_at: `2026-06-29T17:09:45.446267+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- max_symbols: `120`
- period: `60d` interval `5m`
- data_limit: `yfinance_recent_intraday_only; 5m bars are approximately 60 calendar days`
- unsupported_session_warning: `This source covers 04:00-20:00 America/New_York premarket/regular/afterhours. 20:00-04:00 overnight/day-market bars are not present and require a separate provider.`

## Summary

- rows: `25936`
- symbols: `119`
- date_range: `2026-04-02` ~ `2026-06-22`
- candidate_count: `176`
- recent_shadow_ready_count: `14`
- promotion_ready_count: `0`
- fetch_stats: `{'symbols_requested': 120, 'sources': {'cache': 120}, 'errors': {}, 'rows': 25936, 'symbols_with_rows': 119, 'date_min': '2026-04-02', 'date_max': '2026-06-22'}`

## Session Coverage

- `afterhours` rows `6425` days `54` symbols `119` ret5 `+2.103%` win `55.88%` touch `38.58%` ft `41.98%` dd `30.01%`
- `premarket` rows `6542` days `55` symbols `119` ret5 `+1.932%` win `55.73%` touch `35.85%` ft `40.74%` dd `29.18%`
- `regular_close` rows `6425` days `54` symbols `119` ret5 `+2.228%` win `55.94%` touch `39.00%` ft `42.32%` dd `29.98%`
- `regular_open` rows `6544` days `55` symbols `119` ret5 `+1.927%` win `56.01%` touch `37.36%` ft `40.02%` dd `28.58%`

## Top Candidates

- `regular_close` `regular_close_core_ma200` / `score_session_reversal` top1 n `54` days `54` symbols `11` ret5 `+9.907%` win `68.52%` net `+6.510%` net_win `64.81%` touch `75.93%` ft `59.26%` dd `48.15%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, dd3_above_max:0.481481>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top1 n `50` days `50` symbols `18` ret5 `+9.359%` win `68.00%` net `+5.711%` net_win `64.00%` touch `72.00%` ft `74.00%` dd `34.00%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:50<1000, days_below_min:50<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` / `score_liquid_open_drive` top1 n `54` days `54` symbols `17` ret5 `+8.446%` win `64.81%` net `+5.182%` net_win `61.11%` touch `66.67%` ft `68.52%` dd `29.63%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` / `score_liquid_open_drive` top1 n `54` days `54` symbols `17` ret5 `+8.288%` win `66.67%` net `+5.014%` net_win `61.11%` touch `66.67%` ft `68.52%` dd `27.78%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` / `score_session_reversal` top2 n `108` days `54` symbols `17` ret5 `+8.392%` win `63.89%` net `+5.047%` net_win `58.33%` touch `71.30%` ft `56.48%` dd `46.30%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:108<1000, days_below_min:54<250, dd3_above_max:0.462963>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_trend` / `score_liquid_open_drive` top1 n `54` days `54` symbols `21` ret5 `+7.791%` win `64.81%` net `+4.314%` net_win `59.26%` touch `70.37%` ft `72.22%` dd `33.33%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` / `score_session_momentum` top1 n `54` days `54` symbols `14` ret5 `+7.946%` win `62.96%` net `+4.470%` net_win `61.11%` touch `61.11%` ft `55.56%` dd `44.44%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, dd3_above_max:0.444444>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_reversal` top1 n `50` days `50` symbols `14` ret5 `+7.471%` win `62.00%` net `+4.148%` net_win `70.00%` touch `64.00%` ft `64.00%` dd `38.00%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:50<1000, days_below_min:50<250, dd3_above_max:0.38>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` / `score_session_reversal` top1 n `54` days `54` symbols `15` ret5 `+7.374%` win `62.96%` net `+3.907%` net_win `64.81%` touch `64.81%` ft `57.41%` dd `40.74%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, dd3_above_max:0.407407>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_reversal` top3 n `132` days `50` symbols `23` ret5 `+7.158%` win `65.15%` net `+3.798%` net_win `62.12%` touch `65.91%` ft `65.91%` dd `37.12%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:132<1000, days_below_min:50<250, dd3_above_max:0.371212>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top5 n `181` days `50` symbols `25` ret5 `+7.171%` win `66.30%` net `+3.678%` net_win `60.77%` touch `65.75%` ft `65.75%` dd `36.46%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:181<1000, days_below_min:50<250, dd3_above_max:0.364641>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top3 n `132` days `50` symbols `23` ret5 `+7.089%` win `67.42%` net `+3.739%` net_win `61.36%` touch `63.64%` ft `64.39%` dd `36.36%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:132<1000, days_below_min:50<250, dd3_above_max:0.363636>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` / `score_session_reversal` top3 n `162` days `54` symbols `19` ret5 `+7.343%` win `63.58%` net `+4.103%` net_win `55.56%` touch `66.67%` ft `54.94%` dd `46.30%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:162<1000, days_below_min:54<250, ft55_below_min:0.549383<0.55, dd3_above_max:0.462963>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_reversal` top5 n `181` days `50` symbols `24` ret5 `+6.981%` win `66.30%` net `+3.559%` net_win `62.43%` touch `66.85%` ft `66.85%` dd `36.46%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:181<1000, days_below_min:50<250, dd3_above_max:0.364641>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top2 n `94` days `50` symbols `21` ret5 `+7.024%` win `64.89%` net `+3.607%` net_win `59.57%` touch `64.89%` ft `65.96%` dd `37.23%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:94<1000, days_below_min:50<250, dd3_above_max:0.37234>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_momentum` top5 n `181` days `50` symbols `24` ret5 `+6.937%` win `66.30%` net `+3.507%` net_win `61.33%` touch `66.30%` ft `66.30%` dd `35.91%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:181<1000, days_below_min:50<250, dd3_above_max:0.359116>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_reversal` top2 n `94` days `50` symbols `19` ret5 `+6.912%` win `63.83%` net `+3.529%` net_win `61.70%` touch `68.09%` ft `67.02%` dd `37.23%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:94<1000, days_below_min:50<250, dd3_above_max:0.37234>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` / `score_session_reversal` top5 n `270` days `54` symbols `20` ret5 `+7.050%` win `65.19%` net `+3.785%` net_win `56.67%` touch `67.78%` ft `57.78%` dd `44.44%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:270<1000, days_below_min:54<250, dd3_above_max:0.444444>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` / `score_liquid_open_drive` top5 n `270` days `54` symbols `19` ret5 `+6.564%` win `68.89%` net `+3.277%` net_win `61.11%` touch `67.04%` ft `64.81%` dd `32.59%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:270<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` / `score_liquid_open_drive` top3 n `162` days `54` symbols `19` ret5 `+6.519%` win `68.52%` net `+3.267%` net_win `59.26%` touch `67.28%` ft `63.58%` dd `32.72%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:162<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_momentum` top1 n `50` days `50` symbols `15` ret5 `+7.017%` win `62.00%` net `+3.453%` net_win `62.00%` touch `62.00%` ft `58.00%` dd `48.00%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:50<1000, days_below_min:50<250, dd3_above_max:0.48>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` / `score_liquid_open_drive` top2 n `108` days `54` symbols `22` ret5 `+6.660%` win `67.59%` net `+3.294%` net_win `56.48%` touch `62.96%` ft `62.96%` dd `31.48%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:108<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_trend` / `score_liquid_open_drive` top2 n `107` days `54` symbols `24` ret5 `+6.630%` win `66.36%` net `+3.233%` net_win `57.94%` touch `65.42%` ft `66.36%` dd `36.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:107<1000, days_below_min:54<250, dd3_above_max:0.364486>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_calm_strength` top5 n `181` days `50` symbols `25` ret5 `+6.639%` win `65.75%` net `+3.143%` net_win `60.22%` touch `65.19%` ft `65.19%` dd `36.46%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:181<1000, days_below_min:50<250, dd3_above_max:0.364641>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_liquid_open_drive` top1 n `55` days `55` symbols `23` ret5 `+6.303%` win `74.55%` net `+3.307%` net_win `61.82%` touch `70.91%` ft `54.55%` dd `43.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, ft55_below_min:0.545455<0.55, dd3_above_max:0.436364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_momentum` top3 n `132` days `50` symbols `23` ret5 `+6.589%` win `65.91%` net `+3.164%` net_win `59.85%` touch `64.39%` ft `64.39%` dd `38.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:132<1000, days_below_min:50<250, dd3_above_max:0.386364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_reversal` top1 n `53` days `53` symbols `29` ret5 `+6.452%` win `62.26%` net `+4.015%` net_win `52.83%` touch `56.60%` ft `52.83%` dd `41.51%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:53<1000, days_below_min:53<250, alpha5_net_cost_0_2_pos_rate_below_min:0.528302<0.55, ft55_below_min:0.528302<0.55, dd3_above_max:0.415094>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` / `score_session_reversal` top5 n `242` days `54` symbols `27` ret5 `+6.415%` win `66.94%` net `+3.101%` net_win `59.09%` touch `63.64%` ft `60.33%` dd `35.95%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:242<1000, days_below_min:54<250, dd3_above_max:0.359504>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` / `score_session_calm_strength` top3 n `132` days `50` symbols `24` ret5 `+6.439%` win `64.39%` net `+2.972%` net_win `59.09%` touch `62.12%` ft `62.88%` dd `37.88%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:132<1000, days_below_min:50<250, dd3_above_max:0.378788>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` / `score_liquid_open_drive` top3 n `158` days `54` symbols `25` ret5 `+6.303%` win `67.72%` net `+2.948%` net_win `56.33%` touch `61.39%` ft `61.39%` dd `32.91%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
