# Paper Trade Shadow Ledger

- generated_at: `2026-08-13T22:00:56.684088+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `611`
- closed_rows: `610`
- unresolved_rows: `1`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSDAQ: n=610 win=41.31 avg=-1.9436 median=-1.9608 max=15.0 min=-10.0 hit5=29.84 loss5=42.95

## Rank Metrics
- KOSDAQ rank 1: n=134 win=44.78 avg=-1.9965 median=-1.3896 max=10.0 min=-10.0
- KOSDAQ rank 2: n=142 win=34.51 avg=-3.0323 median=-5.8789 max=15.0 min=-10.0
- KOSDAQ rank 3: n=129 win=38.76 avg=-1.7419 median=-1.1796 max=15.0 min=-10.0
- KOSDAQ rank 4: n=106 win=48.11 avg=-0.6722 median=-0.0881 max=10.0 min=-10.0
- KOSDAQ rank 5: n=99 win=42.42 avg=-1.9346 median=-4.361 max=10.6804 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
