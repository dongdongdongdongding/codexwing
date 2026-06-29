# Paper Trade Shadow Ledger

- generated_at: `2026-06-29T08:31:43.549827+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `477`
- closed_rows: `473`
- unresolved_rows: `4`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSDAQ: n=473 win=41.86 avg=-1.59 median=-1.4718 max=15.0 min=-10.0 hit5=30.66 loss5=39.32

## Rank Metrics
- KOSDAQ rank 1: n=83 win=43.37 avg=-1.7084 median=-1.305 max=10.0 min=-10.0
- KOSDAQ rank 2: n=103 win=36.89 avg=-2.2512 median=-3.0623 max=15.0 min=-10.0
- KOSDAQ rank 3: n=105 win=39.05 avg=-1.5538 median=-1.0839 max=15.0 min=-10.0
- KOSDAQ rank 4: n=91 win=49.45 avg=-0.2571 median=-0.0098 max=10.0 min=-10.0
- KOSDAQ rank 5: n=91 win=41.76 avg=-2.1085 median=-4.1133 max=10.6804 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
