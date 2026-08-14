# Paper Trade Shadow Ledger

- generated_at: `2026-08-13T22:00:43.810153+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `793`
- closed_rows: `788`
- unresolved_rows: `5`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSPI: n=788 win=33.88 avg=-1.3478 median=-5.0 max=20.0 min=-10.0 hit5=18.02 loss5=51.14

## Rank Metrics
- KOSPI rank 1: n=164 win=33.54 avg=-1.4505 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 2: n=158 win=35.44 avg=-1.4417 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 3: n=154 win=33.77 avg=-1.3459 median=-4.7569 max=20.0 min=-10.0
- KOSPI rank 4: n=155 win=30.97 avg=-1.0323 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 5: n=157 win=35.67 avg=-1.4591 median=-5.0 max=17.9523 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
