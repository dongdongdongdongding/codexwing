# Paper Trade Shadow Ledger

- generated_at: `2026-05-12T15:17:01.628262+00:00`
- mode: `close_to_close_shadow_v1`
- ledger_rows: `133`
- closed_rows: `114`
- unresolved_rows: `19`
- fee_bps: `0.0`
- slippage_bps: `0.0`

## Market Metrics
- KOSPI: n=114 win=51.75 avg=1.8098 median=0.5729 max=20.0 min=-10.0 hit5=28.95 loss5=29.82

## Rank Metrics
- KOSPI rank 1: n=22 win=59.09 avg=6.2426 median=7.0622 max=20.0 min=-7.2271
- KOSPI rank 2: n=24 win=50.0 avg=0.8105 median=-0.8733 max=20.0 min=-6.4232
- KOSPI rank 3: n=23 win=43.48 avg=0.6682 median=0.0 max=20.0 min=-8.6471
- KOSPI rank 4: n=24 win=54.17 avg=0.3861 median=1.0562 max=9.4268 min=-10.0
- KOSPI rank 5: n=21 win=52.38 avg=1.1852 median=1.1111 max=17.0775 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
