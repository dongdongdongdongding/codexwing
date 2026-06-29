# NASDAQ Session Edge Operational Scan Lane

- report_version: `nasdaq_session_edge_operational_scan_v1`
- generated_at: `2026-06-29T17:51:12.479398+00:00`
- model_version: `nasdaq_session_regular_close_strength_liq_trend_top1_v1`
- market_session: `nasdaq_regular_close`
- source_price_kind: `yfinance_5m_prepost`
- scoring_allowed: `True`
- score_date: `2026-06-26`
- pick_count: `1`
- ledger_appended: `0`
- ledger_settled: `0`
- capital_status: `operator_enabled_live_scan`
- source_report: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/us_research/nasdaq_session_edge_search_20260630_022637.json`
- unsupported_session_warning: `20:00-04:00 ET overnight/day-market bars require a separate provider.`

## Policies

- `nasdaq_session_regular_close_strength_liq_trend_top1_v1` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top1 recent_validated `True` production `False` ret5 `9.359025` win `0.68` net `5.711348` touch `0.72` ft `0.74` dd `0.34`

## Picks

| Rank | Ticker | Score | Entry | SessionRet | r_liq20 | r_ret20 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | HOOD | 3.366667 | 98.699997 | 5.901288 | 0.791667 | 0.875 |

## Ledger

```json
{
  "rows": 1,
  "open": 1,
  "settled": 0,
  "by_candidate": [
    {
      "candidate_id": "nasdaq_session_regular_close_strength_liq_trend_top1_v1",
      "rows": 1,
      "open": 1,
      "settled": 0
    }
  ]
}
```
