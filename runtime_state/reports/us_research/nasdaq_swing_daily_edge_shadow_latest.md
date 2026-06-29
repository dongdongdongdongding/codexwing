# NASDAQ SWING Daily Edge Model

- report_version: `nasdaq_swing_daily_edge_shadow_v1`
- generated_at: `2026-06-29T07:34:11.347252+00:00`
- model_version: `nasdaq_swing_alpha3_pos60_v1`
- score_date: `2026-06-26`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- picks: `0`
- ledger_appended: `0`
- ledger_settled: `0`

## Policy Picks

| Lane | Rank | Ticker | Score | p(alpha5 net>0) | liq20 |
|---|---:|---|---:|---:|---:|

## Gate Diagnostics

- `nasdaq_swing_alpha3_pos60_liq30_top10_v1` pool `816` gate_pass `0` max_p `0.566305` max_score `0.999592`
  - `GOOG` score `0.999592` p `0.542397` reasons `pred_alpha5_net_pos_below_0_60`
  - `GOOGL` score `0.999592` p `0.536751` reasons `pred_alpha5_net_pos_below_0_60`
  - `MAR` score `0.998366` p `0.537487` reasons `pred_alpha5_net_pos_below_0_60`
- `nasdaq_swing_alpha3_pos60_liq100_top5_v1` pool `427` gate_pass `0` max_p `0.562278` max_score `0.999592`
  - `GOOG` score `0.999592` p `0.542397` reasons `pred_alpha5_net_pos_below_0_60`
  - `GOOGL` score `0.999592` p `0.536751` reasons `pred_alpha5_net_pos_below_0_60`
  - `MAR` score `0.998366` p `0.537487` reasons `pred_alpha5_net_pos_below_0_60`

## Forward Ledger

```json
{
  "rows": 0,
  "open": 0,
  "settled": 0,
  "by_candidate": []
}
```
