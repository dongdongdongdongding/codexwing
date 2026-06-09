# Paper Trade Shadow Ledger

- generated_at: `2026-06-09T06:29:54.862003+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `305`
- closed_rows: `295`
- unresolved_rows: `10`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSDAQ: n=295 win=42.71 avg=-1.2467 median=-0.9563 max=15.0 min=-10.0 hit5=25.76 loss5=35.93

## Rank Metrics
- KOSDAQ rank 1: n=53 win=37.74 avg=-2.3718 median=-1.305 max=10.0 min=-10.0
- KOSDAQ rank 2: n=58 win=32.76 avg=-2.4571 median=-2.9328 max=10.0 min=-10.0
- KOSDAQ rank 3: n=63 win=46.03 avg=-0.3854 median=-0.3084 max=15.0 min=-10.0
- KOSDAQ rank 4: n=58 win=53.45 avg=0.7928 median=1.7286 max=10.0 min=-10.0
- KOSDAQ rank 5: n=63 win=42.86 avg=-1.9248 median=-4.7619 max=10.6804 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
