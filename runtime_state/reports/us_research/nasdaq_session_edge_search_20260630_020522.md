# NASDAQ Session Edge Search

- report_version: `nasdaq_session_edge_search_v1`
- generated_at: `2026-06-29T17:05:22.887910+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- max_symbols: `120`
- period: `60d` interval `5m`
- data_limit: `yfinance_recent_intraday_only; 5m bars are approximately 60 calendar days`
- unsupported_session_warning: `This source covers 04:00-20:00 America/New_York premarket/regular/afterhours. 20:00-04:00 overnight/day-market bars are not present and require a separate provider.`

## Summary

- rows: `25936`
- symbols: `119`
- date_range: `2026-04-02` ~ `2026-06-22`
- candidate_count: `96`
- recent_shadow_ready_count: `0`
- promotion_ready_count: `0`
- fetch_stats: `{'symbols_requested': 120, 'sources': {'yfinance': 120}, 'errors': {}, 'rows': 25936, 'symbols_with_rows': 119, 'date_min': '2026-04-02', 'date_max': '2026-06-22'}`

## Session Coverage

- `afterhours` rows `6425` days `54` symbols `119` ret5 `+2.103%` win `55.88%` touch `38.58%` ft `41.98%` dd `30.01%`
- `premarket` rows `6542` days `55` symbols `119` ret5 `+1.932%` win `55.73%` touch `35.85%` ft `40.74%` dd `29.18%`
- `regular_close` rows `6425` days `54` symbols `119` ret5 `+2.228%` win `55.94%` touch `39.00%` ft `42.32%` dd `29.98%`
- `regular_open` rows `6544` days `55` symbols `119` ret5 `+1.927%` win `56.01%` touch `37.36%` ft `40.02%` dd `28.58%`

## Top Candidates

- `regular_open` `regular_open_liquid_drive` / `score_liquid_open_drive` top1 n `55` days `55` symbols `23` ret5 `+6.303%` win `74.55%` net `+3.307%` net_win `61.82%` touch `70.91%` ft `54.55%` dd `43.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, ft55_below_min:0.545455<0.55, dd3_above_max:0.436364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_reversal` top1 n `53` days `53` symbols `29` ret5 `+6.452%` win `62.26%` net `+4.015%` net_win `52.83%` touch `56.60%` ft `52.83%` dd `41.51%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:53<1000, days_below_min:53<250, alpha5_net_cost_0_2_pos_rate_below_min:0.528302<0.55, ft55_below_min:0.528302<0.55, dd3_above_max:0.415094>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_session_momentum` top2 n `110` days `55` symbols `26` ret5 `+6.052%` win `70.91%` net `+3.004%` net_win `57.27%` touch `67.27%` ft `36.36%` dd `55.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:110<1000, days_below_min:55<250, ft55_below_min:0.363636<0.55, dd3_above_max:0.554545>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_session_reversal` top1 n `55` days `55` symbols `17` ret5 `+5.626%` win `67.27%` net `+2.712%` net_win `60.00%` touch `63.64%` ft `54.55%` dd `45.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.222938<0, ft55_below_min:0.545455<0.55, dd3_above_max:0.454545>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_momentum` top2 n `110` days `55` symbols `27` ret5 `+5.663%` win `70.91%` net `+2.676%` net_win `57.27%` touch `72.73%` ft `32.73%` dd `64.55%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:110<1000, days_below_min:55<250, ft55_below_min:0.327273<0.55, dd3_above_max:0.645455>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_momentum` top1 n `55` days `55` symbols `15` ret5 `+5.572%` win `72.73%` net `+2.539%` net_win `58.18%` touch `74.55%` ft `36.36%` dd `65.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, ft55_below_min:0.363636<0.55, dd3_above_max:0.654545>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_reversal` top3 n `158` days `54` symbols `27` ret5 `+5.377%` win `65.19%` net `+2.018%` net_win `56.96%` touch `69.62%` ft `65.82%` dd `37.34%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:54<250, dd3_above_max:0.373418>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_momentum` top5 n `255` days `54` symbols `32` ret5 `+5.483%` win `63.92%` net `+2.181%` net_win `54.51%` touch `64.71%` ft `63.14%` dd `38.04%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:255<1000, days_below_min:54<250, alpha5_net_cost_0_2_pos_rate_below_min:0.545098<0.55, dd3_above_max:0.380392>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_liquid_open_drive` top1 n `55` days `55` symbols `28` ret5 `+5.418%` win `69.09%` net `+2.305%` net_win `58.18%` touch `72.73%` ft `45.45%` dd `50.91%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, ft55_below_min:0.454545<0.55, dd3_above_max:0.509091>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_reversal` top5 n `255` days `54` symbols `32` ret5 `+5.350%` win `62.75%` net `+1.980%` net_win `57.25%` touch `65.88%` ft `63.53%` dd `39.22%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:255<1000, days_below_min:54<250, dd3_above_max:0.392157>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_calm_strength` top1 n `53` days `53` symbols `34` ret5 `+5.100%` win `62.26%` net `+2.604%` net_win `54.72%` touch `52.83%` ft `50.94%` dd `32.08%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:53<1000, days_below_min:53<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.133113<0, alpha5_net_cost_0_2_pos_rate_below_min:0.54717<0.55, touch3_below_min:0.528302<0.55, ft55_below_min:0.509434<0.55, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_reversal` top2 n `108` days `54` symbols `22` ret5 `+4.973%` win `64.81%` net `+1.712%` net_win `59.26%` touch `69.44%` ft `66.67%` dd `36.11%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:108<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.320056<0, dd3_above_max:0.361111>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_session_momentum` top1 n `55` days `55` symbols `15` ret5 `+5.245%` win `70.91%` net `+2.059%` net_win `56.36%` touch `69.09%` ft `36.36%` dd `63.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:55<1000, days_below_min:55<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.18984<0, ft55_below_min:0.363636<0.55, dd3_above_max:0.636364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_momentum` top3 n `158` days `54` symbols `30` ret5 `+5.044%` win `63.29%` net `+1.740%` net_win `55.06%` touch `63.29%` ft `61.39%` dd `42.41%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.004768<0, dd3_above_max:0.424051>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_momentum` top3 n `165` days `55` symbols `35` ret5 `+5.088%` win `69.70%` net `+2.198%` net_win `53.94%` touch `67.27%` ft `31.52%` dd `63.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:165<1000, days_below_min:55<250, alpha5_net_cost_0_2_pos_rate_below_min:0.539394<0.55, ft55_below_min:0.315152<0.55, dd3_above_max:0.636364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_liquid_open_drive` top3 n `158` days `54` symbols `31` ret5 `+4.896%` win `62.66%` net `+1.580%` net_win `51.90%` touch `62.03%` ft `61.39%` dd `36.08%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.104711<0, alpha5_net_cost_0_2_pos_rate_below_min:0.518987<0.55, dd3_above_max:0.360759>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_session_momentum` top3 n `165` days `55` symbols `32` ret5 `+5.168%` win `66.06%` net `+2.113%` net_win `53.94%` touch `61.82%` ft `32.73%` dd `58.18%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:165<1000, days_below_min:55<250, alpha5_net_cost_0_2_pos_rate_below_min:0.539394<0.55, ft55_below_min:0.327273<0.55, dd3_above_max:0.581818>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_momentum` top1 n `53` days `53` symbols `32` ret5 `+4.761%` win `62.26%` net `+2.171%` net_win `49.06%` touch `52.83%` ft `50.94%` dd `37.74%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:53<1000, days_below_min:53<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.741059<0, alpha5_net_cost_0_2_pos_rate_below_min:0.490566<0.55, touch3_below_min:0.528302<0.55, ft55_below_min:0.509434<0.55, dd3_above_max:0.377358>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_reversal` top1 n `54` days `54` symbols `15` ret5 `+4.536%` win `62.96%` net `+1.261%` net_win `57.41%` touch `70.37%` ft `68.52%` dd `35.19%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-1.38537<0, dd3_above_max:0.351852>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength` / `score_session_reversal` top2 n `108` days `54` symbols `28` ret5 `+4.752%` win `57.41%` net `+1.990%` net_win `56.48%` touch `58.33%` ft `50.93%` dd `48.15%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:108<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.15284<0, ft55_below_min:0.509259<0.55, dd3_above_max:0.481481>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_momentum` top5 n `275` days `55` symbols `46` ret5 `+4.852%` win `66.18%` net `+2.043%` net_win `53.09%` touch `63.27%` ft `34.91%` dd `57.82%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:275<1000, days_below_min:55<250, alpha5_net_cost_0_2_pos_rate_below_min:0.530909<0.55, ft55_below_min:0.349091<0.55, dd3_above_max:0.578182>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_reversal` top2 n `110` days `55` symbols `29` ret5 `+4.626%` win `60.91%` net `+1.883%` net_win `56.36%` touch `67.27%` ft `40.00%` dd `55.45%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:110<1000, days_below_min:55<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.135078<0, ft55_below_min:0.4<0.55, dd3_above_max:0.554545>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_session_reversal` top3 n `165` days `55` symbols `33` ret5 `+4.678%` win `63.03%` net `+1.809%` net_win `55.15%` touch `66.67%` ft `39.39%` dd `56.36%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:165<1000, days_below_min:55<250, ft55_below_min:0.393939<0.55, dd3_above_max:0.563636>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_reversal` top2 n `106` days `53` symbols `49` ret5 `+4.409%` win `58.49%` net `+1.962%` net_win `50.94%` touch `55.66%` ft `50.94%` dd `36.79%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:106<1000, days_below_min:53<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.085145<0, alpha5_net_cost_0_2_pos_rate_below_min:0.509434<0.55, ft55_below_min:0.509434<0.55, dd3_above_max:0.367925>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_liquid_open_drive` top5 n `255` days `54` symbols `36` ret5 `+4.617%` win `63.92%` net `+1.286%` net_win `50.98%` touch `58.43%` ft `58.82%` dd `36.08%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:255<1000, days_below_min:54<250, alpha5_net_cost_0_2_pos_rate_below_min:0.509804<0.55, dd3_above_max:0.360784>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `afterhours` `afterhours_calm_positive` / `score_session_reversal` top3 n `158` days `53` symbols `61` ret5 `+4.368%` win `60.76%` net `+1.792%` net_win `51.27%` touch `51.90%` ft `49.37%` dd `32.91%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:53<250, alpha5_net_cost_0_2_pos_rate_below_min:0.512658<0.55, touch3_below_min:0.518987<0.55, ft55_below_min:0.493671<0.55, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_liquid_drive` / `score_session_momentum` top5 n `272` days `55` symbols `38` ret5 `+4.652%` win `65.07%` net `+1.666%` net_win `52.57%` touch `58.09%` ft `36.76%` dd `51.84%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:272<1000, days_below_min:55<250, alpha5_net_cost_0_2_pos_rate_below_min:0.525735<0.55, ft55_below_min:0.367647<0.55, dd3_above_max:0.518382>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_strength` / `score_session_reversal` top1 n `54` days `54` symbols `16` ret5 `+4.546%` win `57.41%` net `+1.671%` net_win `57.41%` touch `62.96%` ft `50.00%` dd `57.41%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:54<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-1.25811<0, ft55_below_min:0.5<0.55, dd3_above_max:0.574074>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_close` `regular_close_liquid_trend` / `score_session_calm_strength` top3 n `158` days `54` symbols `33` ret5 `+4.584%` win `59.49%` net `+1.207%` net_win `50.00%` touch `55.70%` ft `56.33%` dd `36.08%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:158<1000, days_below_min:54<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.441554<0, alpha5_net_cost_0_2_pos_rate_below_min:0.5<0.55, dd3_above_max:0.360759>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
- `regular_open` `regular_open_drive` / `score_liquid_open_drive` top2 n `110` days `55` symbols `36` ret5 `+4.321%` win `66.36%` net `+1.323%` net_win `50.91%` touch `66.36%` ft `43.64%` dd `43.64%` recent_shadow `BLOCK` production `BLOCK`
  - production_blockers: `n_below_min:110<1000, days_below_min:55<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.123041<0, alpha5_net_cost_0_2_pos_rate_below_min:0.509091<0.55, ft55_below_min:0.436364<0.55, dd3_above_max:0.436364>0.35, years_alpha5_net_0_2_pos_below_min:1<5`
