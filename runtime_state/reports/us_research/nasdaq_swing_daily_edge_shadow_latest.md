# NASDAQ SWING Research Shadow Model

- report_version: `nasdaq_swing_daily_edge_shadow_v1`
- generated_at: `2026-06-29T18:00:21.040797+00:00`
- model_version: `nasdaq_swing_alpha3_pos60_v1`
- score_date: `2026-06-26`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- market_session: `manual_eod_latest`
- session_cutoff: ``
- source_price_kind: `daily_eod_close`
- freshness_status: `latest_eod_panel_scored`
- finality_status: `finalized_eod_session`
- picks: `0`
- ledger_appended: `0`
- ledger_settled: `0`
- promotion_ready: `False`
- capital_status: `research_shadow_only_win_return_gate_blocked`
- promotion_note: NASDAQ SWING stays research-shadow only until return, positive-rate, +5% touch, first-touch, drawdown, and year-stability gates all pass. Positive average alpha alone is not sufficient.

## Promotion Gate

- gate_version: `nasdaq_swing_win_return_gate_v1`
- status: `research_shadow_only_win_return_gate_blocked`
- source_report: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/us_research/nasdaq_production_edge_search_20260630_002301.json`
- ready_policy_count: `0`
- blocking_reasons: `ret5_pos_rate_below_min:0.526552<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.493269<0.55, touch3_below_min:0.393792<0.55, ft55_below_min:0.380329<0.55, dd3_above_max:0.367988>0.35, years_alpha5_net_0_2_pos_below_min:4<5, ret5_pos_rate_below_min:0.535826<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.482087<0.55, touch3_below_min:0.378505<0.55, ft55_below_min:0.376947<0.55`

## Policy Picks

| Lane | Rank | Ticker | Score | p(alpha5 net>0) | liq20 |
|---|---:|---|---:|---:|---:|

## Gate Diagnostics

- `nasdaq_swing_alpha3_pos60_liq30_top10_v1` pool `816` gate_pass `0` max_p `0.566305` max_score `0.999592`
  - `GOOG` score `0.999592` p `0.542397` reasons `pred_alpha5_net_pos_below_0_60`
  - `GOOGL` score `0.999592` p `0.536751` reasons `pred_alpha5_net_pos_below_0_60`
  - `MAR` score `0.998366` p `0.537487` reasons `pred_alpha5_net_pos_below_0_60`
  - historical: ret5 `1.443868` ret5_pos `0.526552` net@0.2 `0.694348` net_pos `0.493269` touch3 `0.393792` ft55 `0.380329` dd3 `0.367988` gate `BLOCK`
- `nasdaq_swing_alpha3_pos60_liq100_top5_v1` pool `427` gate_pass `0` max_p `0.562278` max_score `0.999592`
  - `GOOG` score `0.999592` p `0.542397` reasons `pred_alpha5_net_pos_below_0_60`
  - `GOOGL` score `0.999592` p `0.536751` reasons `pred_alpha5_net_pos_below_0_60`
  - `MAR` score `0.998366` p `0.537487` reasons `pred_alpha5_net_pos_below_0_60`
  - historical: ret5 `1.534694` ret5_pos `0.535826` net@0.2 `0.771697` net_pos `0.482087` touch3 `0.378505` ft55 `0.376947` dd3 `0.340343` gate `BLOCK`

## Forward Ledger

```json
{
  "rows": 0,
  "open": 0,
  "settled": 0,
  "by_candidate": []
}
```
