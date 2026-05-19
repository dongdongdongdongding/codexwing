# PyKRX Investor Flow Diagnostics

Updated: 2026-05-19

## Decision

Keep pykrx as preferred KR investor-flow source only when it returns non-empty,
non-zero investor trading value rows. A pykrx empty response is not a neutral or
safe flow signal. It is a source warning and must remain visible.

Current operating stance:

- `pykrx_value`: usable for flow direction when non-empty and parsed.
- `naver`: fallback only; unit is shares, not KRW.
- `score_only`: not enough to claim foreigner/institution direction.
- `unavailable`: block flow-based claims.

## Empty Response Classification

`pykrx_flow_failed:pykrx_empty_investor_flow` means the primary source returned
no rows. Likely causes:

- non-trading/holiday date window
- KRX throttling or session/cookie behavior change
- pykrx parser no longer matching the KRX response shape
- ticker/date range mismatch

`pykrx_flow_failed:pykrx_zero_investor_flow` means rows existed but investor
sums were zero or unmapped. Treat it as a source warning, not as flat flow.

## Required Runtime Behavior

- Warnings must include the pykrx failure class.
- Naver fallback rows must be labelled `flow_source=naver` and
  `flow_unit=shares`.
- pykrx rows must be labelled `flow_source=pykrx_value` and `flow_unit=KRW`.
- If only `whale_score` exists, the system must not invent foreigner or
  institution values.
- Buy/action display may show scanner candidates, but cannot cite flow as
  supportive when source decision is `score_only` or `unavailable`.

## Diagnostic Tool

Generate the local diagnostic report:

```bash
python3 multi_agent/tools/report_pykrx_investor_flow_diagnostics.py
```

Output:

```text
runtime_state/reports/validation/pykrx_investor_flow_diagnostics.json
runtime_state/reports/validation/pykrx_investor_flow_diagnostics.md
```

## Next Implementation Step

The next live-data issue should run a trading-day smoke test for `005930.KS`:

- pykrx `get_market_trading_value_by_date(start, end, "005930")`
- pykrx version and returned columns
- whether the latest index is a trading day
- same call through KIS OpenAPI after credentials are configured

Promote KIS as the primary official source only after live token/quote/flow
smoke tests pass with rate-limit backoff.

