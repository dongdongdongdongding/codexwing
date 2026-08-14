# NASDAQ Session Edge Operational Scan Lane

- report_version: `nasdaq_session_edge_operational_scan_v1`
- generated_at: `2026-08-14T00:53:27.628455+00:00`
- model_version: `nasdaq_session_regular_close_strength_liq_trend_top1_v1`
- market_session: `nasdaq_regular_close`
- source_price_kind: `yfinance_5m_prepost`
- scoring_allowed: `True`
- score_date: `None`
- pick_count: `0`
- ledger_appended: `0`
- ledger_settled: `0`
- capital_status: `operator_enabled_live_scan`
- source_report: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/us_research/nasdaq_session_edge_search_20260630_020522.json`
- unsupported_session_warning: `20:00-04:00 ET overnight/day-market bars require a separate provider.`

## Policies

- `nasdaq_session_regular_close_strength_liq_trend_top1_v1` `regular_close_strength_liq_trend` / `score_liquid_open_drive` top1 recent_validated `False` production `False` ret5 `None` win `None` net `None` touch `None` ft `None` dd `None`

## Picks

| Rank | Ticker | Score | Entry | SessionRet | r_liq20 | r_ret20 |
|---:|---|---:|---:|---:|---:|---:|

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
