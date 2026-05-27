# Paper Trade Shadow Ledger

- generated_at: `2026-05-27T10:53:32.779335+00:00`
- mode: `close_to_close_shadow_v1`
- ledger_rows: `273`
- closed_rows: `273`
- unresolved_rows: `0`
- fee_bps: `0.0`
- slippage_bps: `0.0`

## Market Metrics
- KOSDAQ: n=273 win=60.07 avg=0.924 median=1.6854 max=15.0 min=-10.0 hit5=31.5 loss5=19.78

## Rank Metrics
- KOSDAQ rank 1: n=50 win=58.0 avg=-0.6203 median=0.7723 max=10.0 min=-10.0
- KOSDAQ rank 2: n=53 win=47.17 avg=-0.4706 median=0.0 max=10.0 min=-10.0
- KOSDAQ rank 3: n=59 win=64.41 avg=1.6294 median=1.8097 max=15.0 min=-10.0
- KOSDAQ rank 4: n=54 win=77.78 avg=3.5302 median=4.5156 max=10.0 min=-10.0
- KOSDAQ rank 5: n=57 win=52.63 avg=0.3761 median=1.9143 max=12.894 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
