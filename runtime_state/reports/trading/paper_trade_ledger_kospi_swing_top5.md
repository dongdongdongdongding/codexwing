# Paper Trade Shadow Ledger

- generated_at: `2026-06-09T06:29:55.338787+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `488`
- closed_rows: `458`
- unresolved_rows: `30`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSPI: n=458 win=32.97 avg=-1.9774 median=-5.0 max=20.0 min=-10.0 hit5=17.69 loss5=51.97

## Rank Metrics
- KOSPI rank 1: n=103 win=34.95 avg=-1.6314 median=-4.899 max=20.0 min=-10.0
- KOSPI rank 2: n=97 win=34.02 avg=-1.9692 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 3: n=94 win=32.98 avg=-1.8498 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 4: n=83 win=32.53 avg=-1.6373 median=-5.0 max=15.0 min=-10.0
- KOSPI rank 5: n=81 win=29.63 avg=-2.9237 median=-5.0 max=15.0 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
