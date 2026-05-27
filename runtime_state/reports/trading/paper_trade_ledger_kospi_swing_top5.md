# Paper Trade Shadow Ledger

- generated_at: `2026-05-27T10:53:33.134322+00:00`
- mode: `close_to_close_shadow_v1`
- ledger_rows: `416`
- closed_rows: `416`
- unresolved_rows: `0`
- fee_bps: `0.0`
- slippage_bps: `0.0`

## Market Metrics
- KOSPI: n=416 win=47.12 avg=0.2028 median=-1.137 max=20.0 min=-10.0 hit5=25.48 loss5=39.18

## Rank Metrics
- KOSPI rank 1: n=92 win=57.61 avg=1.8217 median=1.0539 max=20.0 min=-10.0
- KOSPI rank 2: n=87 win=45.98 avg=-0.1359 median=-2.8956 max=20.0 min=-10.0
- KOSPI rank 3: n=87 win=43.68 avg=-0.2127 median=-1.4675 max=20.0 min=-10.0
- KOSPI rank 4: n=77 win=46.75 avg=0.5779 median=-0.9879 max=17.0775 min=-10.0
- KOSPI rank 5: n=73 win=39.73 avg=-1.3341 median=-4.0 max=17.0775 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
