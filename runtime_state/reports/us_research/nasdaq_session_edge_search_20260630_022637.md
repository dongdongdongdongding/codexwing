# NASDAQ Session Edge Search

- report_version: `nasdaq_session_edge_search_v1`
- generated_at: `2026-06-29T17:26:37.516998+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- max_symbols: `120`
- period: `60d` interval `5m`
- data_limit: `yfinance_recent_intraday_only; 5m bars are approximately 60 calendar days`
- unsupported_session_warning: `This source covers 04:00-20:00 America/New_York premarket/regular/afterhours. 20:00-04:00 overnight/day-market bars are not present and require a separate provider.`

## Summary

- rows: `25936`
- symbols: `119`
- date_range: `2026-04-02` ~ `2026-06-22`
- candidate_count: `1232`
- recent_shadow_ready_count: `51`
- promotion_ready_count: `0`
- fetch_stats: `{'symbols_requested': 120, 'sources': {'cache': 120}, 'errors': {}, 'rows': 25936, 'symbols_with_rows': 119, 'date_min': '2026-04-02', 'date_max': '2026-06-22'}`

## Session Coverage

- `afterhours` rows `6425` days `54` symbols `119` ret5 `+2.103%` win `55.88%` touch `38.58%` ft `41.98%` dd `30.01%`
- `premarket` rows `6542` days `55` symbols `119` ret5 `+1.932%` win `55.73%` touch `35.85%` ft `40.74%` dd `29.18%`
- `regular_close` rows `6425` days `54` symbols `119` ret5 `+2.228%` win `55.94%` touch `39.00%` ft `42.32%` dd `29.98%`
- `regular_open` rows `6544` days `55` symbols `119` ret5 `+1.927%` win `56.01%` touch `37.36%` ft `40.02%` dd `28.58%`

## Top Candidates

- `regular_close` `regular_close_strength_liq_trend` regime `market_up20_calm` / `score_liquid_open_drive` top1 n `39` days `39` symbols `15` ret5 `+10.124%` win `66.67%` net `+6.435%` net_win `64.10%` touch `64.10%` ft `71.79%` dd `33.33%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:39<1000, days_below_min:39<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `all` / `score_session_reversal` top1 n `54` days `54` symbols `11` ret5 `+9.907%` win `68.52%` net `+6.510%` net_win `64.81%` touch `75.93%` ft `59.26%` dd `48.15%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, dd3_above_max:0.481481>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_calm` / `score_session_reversal` top1 n `44` days `44` symbols `9` ret5 `+10.163%` win `63.64%` net `+6.507%` net_win `61.36%` touch `72.73%` ft `59.09%` dd `50.00%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:44<1000, days_below_min:44<250, dd3_above_max:0.5>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `market_up20` / `score_liquid_open_drive` top1 n `48` days `48` symbols `17` ret5 `+9.476%` win `66.67%` net `+6.154%` net_win `66.67%` touch `70.83%` ft `75.00%` dd `33.33%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:48<1000, days_below_min:48<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `market_calm` / `score_liquid_open_drive` top1 n `41` days `41` symbols `16` ret5 `+9.950%` win `68.29%` net `+5.882%` net_win `60.98%` touch `65.85%` ft `70.73%` dd `34.15%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:41<1000, days_below_min:41<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `all` / `score_liquid_open_drive` top1 n `50` days `50` symbols `18` ret5 `+9.359%` win `68.00%` net `+5.711%` net_win `64.00%` touch `72.00%` ft `74.00%` dd `34.00%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:50<1000, days_below_min:50<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_up20` / `score_session_reversal` top1 n `52` days `52` symbols `11` ret5 `+9.245%` win `67.31%` net `+6.158%` net_win `63.46%` touch `75.00%` ft `57.69%` dd `50.00%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:52<1000, days_below_min:52<250, dd3_above_max:0.5>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_strong20` / `score_session_reversal` top1 n `43` days `43` symbols `10` ret5 `+8.736%` win `62.79%` net `+6.735%` net_win `62.79%` touch `72.09%` ft `55.81%` dd `53.49%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:43<1000, days_below_min:43<250, dd3_above_max:0.534884>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_up20_calm` / `score_session_reversal` top1 n `42` days `42` symbols `9` ret5 `+9.356%` win `61.90%` net `+6.071%` net_win `59.52%` touch `71.43%` ft `57.14%` dd `52.38%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, dd3_above_max:0.52381>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_breadth20` / `score_session_reversal` top1 n `45` days `45` symbols `10` ret5 `+8.766%` win `64.44%` net `+6.397%` net_win `62.22%` touch `73.33%` ft `57.78%` dd `51.11%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:45<1000, days_below_min:45<250, dd3_above_max:0.511111>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_strong20_breadth` / `score_session_reversal` top1 n `42` days `42` symbols `10` ret5 `+8.620%` win `61.90%` net `+6.687%` net_win `61.90%` touch `71.43%` ft `54.76%` dd `54.76%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, ft55_below_min:0.547619<0.55, dd3_above_max:0.547619>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_up20_calm` / `score_liquid_open_drive` top1 n `42` days `42` symbols `14` ret5 `+8.944%` win `64.29%` net `+5.780%` net_win `59.52%` touch `59.52%` ft `66.67%` dd `28.57%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `market_breadth20` / `score_liquid_open_drive` top1 n `42` days `42` symbols `14` ret5 `+8.523%` win `61.90%` net `+5.844%` net_win `66.67%` touch `66.67%` ft `73.81%` dd `35.71%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, dd3_above_max:0.357143>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_calm` / `score_liquid_open_drive` top1 n `44` days `44` symbols `14` ret5 `+9.047%` win `65.91%` net `+5.507%` net_win `59.09%` touch `61.36%` ft `65.91%` dd `29.55%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:44<1000, days_below_min:44<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `market_strong20` / `score_liquid_open_drive` top1 n `39` days `39` symbols `14` ret5 `+8.282%` win `58.97%` net `+6.048%` net_win `64.10%` touch `64.10%` ft `71.79%` dd `38.46%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:39<1000, days_below_min:39<250, dd3_above_max:0.384615>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_trend` regime `market_strong20_breadth` / `score_liquid_open_drive` top1 n `39` days `39` symbols `14` ret5 `+8.282%` win `58.97%` net `+6.048%` net_win `64.10%` touch `64.10%` ft `71.79%` dd `38.46%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:39<1000, days_below_min:39<250, dd3_above_max:0.384615>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_up20_calm` / `score_session_momentum` top1 n `42` days `42` symbols `12` ret5 `+9.121%` win `64.29%` net `+5.684%` net_win `64.29%` touch `54.76%` ft `52.38%` dd `45.24%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, touch3_below_min:0.547619<0.55, ft55_below_min:0.52381<0.55, dd3_above_max:0.452381>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_breadth20` / `score_liquid_open_drive` top1 n `45` days `45` symbols `14` ret5 `+8.215%` win `60.00%` net `+5.856%` net_win `62.22%` touch `62.22%` ft `68.89%` dd `28.89%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:45<1000, days_below_min:45<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_up20` / `score_liquid_open_drive` top1 n `52` days `52` symbols `17` ret5 `+8.339%` win `63.46%` net `+5.390%` net_win `61.54%` touch `65.38%` ft `69.23%` dd `28.85%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:52<1000, days_below_min:52<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `all` / `score_liquid_open_drive` top1 n `54` days `54` symbols `17` ret5 `+8.446%` win `64.81%` net `+5.182%` net_win `61.11%` touch `66.67%` ft `68.52%` dd `29.63%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_strong20_breadth` / `score_liquid_open_drive` top1 n `42` days `42` symbols `14` ret5 `+7.969%` win `57.14%` net `+6.047%` net_win `59.52%` touch `59.52%` ft `66.67%` dd `30.95%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_calm` / `score_session_momentum` top1 n `44` days `44` symbols `13` ret5 `+9.004%` win `65.91%` net `+5.203%` net_win `61.36%` touch `56.82%` ft `52.27%` dd `45.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:44<1000, days_below_min:44<250, ft55_below_min:0.522727<0.55, dd3_above_max:0.454545>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` regime `all` / `score_liquid_open_drive` top1 n `54` days `54` symbols `17` ret5 `+8.288%` win `66.67%` net `+5.014%` net_win `61.11%` touch `66.67%` ft `68.52%` dd `27.78%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` regime `market_up20` / `score_liquid_open_drive` top1 n `52` days `52` symbols `16` ret5 `+8.179%` win `65.38%` net `+5.113%` net_win `61.54%` touch `65.38%` ft `69.23%` dd `26.92%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:52<1000, days_below_min:52<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `all` / `score_session_reversal` top2 n `108` days `54` symbols `17` ret5 `+8.392%` win `63.89%` net `+5.047%` net_win `58.33%` touch `71.30%` ft `56.48%` dd `46.30%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:108<1000, days_below_min:54<250, dd3_above_max:0.462963>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_ma200` regime `market_calm` / `score_session_reversal` top2 n `88` days `44` symbols `16` ret5 `+8.670%` win `60.23%` net `+5.056%` net_win `55.68%` touch `67.05%` ft `54.55%` dd `46.59%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:88<1000, days_below_min:44<250, ft55_below_min:0.545455<0.55, dd3_above_max:0.465909>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength_liq_ma200` regime `market_strong20` / `score_liquid_open_drive` top1 n `43` days `43` symbols `14` ret5 `+7.726%` win `55.81%` net `+5.736%` net_win `58.14%` touch `58.14%` ft `65.12%` dd `30.23%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:43<1000, days_below_min:43<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` regime `market_calm` / `score_liquid_open_drive` top1 n `44` days `44` symbols `14` ret5 `+8.183%` win `65.91%` net `+4.630%` net_win `56.82%` touch `59.09%` ft `63.64%` dd `27.27%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:44<1000, days_below_min:44<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` regime `market_up20_calm` / `score_liquid_open_drive` top1 n `42` days `42` symbols `13` ret5 `+8.042%` win `64.29%` net `+4.733%` net_win `57.14%` touch `57.14%` ft `64.29%` dd `26.19%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:42<1000, days_below_min:42<250, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_core_close_ma200` regime `market_strong20` / `score_liquid_open_drive` top1 n `43` days `43` symbols `14` ret5 `+7.533%` win `58.14%` net `+5.400%` net_win `58.14%` touch `58.14%` ft `65.12%` dd `27.91%` recent_shadow `PASS` production `BLOCK`
  - production_blockers: `n_below_min:43<1000, days_below_min:43<250, years_alpha5_net_0_2_pos_below_min:1<5`
