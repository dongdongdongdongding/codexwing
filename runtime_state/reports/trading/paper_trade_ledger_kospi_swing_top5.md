# Paper Trade Shadow Ledger

- generated_at: `2026-06-29T08:31:32.076985+00:00`
- mode: `close_to_close_shadow_buy_premium_v2`
- ledger_rows: `588`
- closed_rows: `577`
- unresolved_rows: `11`
- fee_bps: `0.0`
- slippage_bps: `0.0`
- buy_premium_pct: `2.0`

## Market Metrics
- KOSPI: n=577 win=34.14 avg=-1.5944 median=-5.0 max=20.0 min=-10.0 hit5=18.2 loss5=51.47

## Rank Metrics
- KOSPI rank 1: n=131 win=32.82 avg=-1.8331 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 2: n=121 win=35.54 avg=-1.5924 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 3: n=113 win=33.63 avg=-1.5796 median=-5.0 max=20.0 min=-10.0
- KOSPI rank 4: n=107 win=33.64 avg=-0.8037 median=-3.6998 max=20.0 min=-10.0
- KOSPI rank 5: n=105 win=35.24 avg=-2.1204 median=-5.0 max=17.9523 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Return paths are evaluated after assuming the actual buy happens above the scan reference price by buy_premium_pct.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
