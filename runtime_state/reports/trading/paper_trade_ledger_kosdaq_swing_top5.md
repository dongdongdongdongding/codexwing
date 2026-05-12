# Paper Trade Shadow Ledger

- generated_at: `2026-05-12T15:17:10.822659+00:00`
- mode: `close_to_close_shadow_v1`
- ledger_rows: `121`
- closed_rows: `119`
- unresolved_rows: `2`
- fee_bps: `0.0`
- slippage_bps: `0.0`

## Market Metrics
- KOSDAQ: n=119 win=55.46 avg=0.5351 median=0.8757 max=10.0 min=-10.0 hit5=24.37 loss5=18.49

## Rank Metrics
- KOSDAQ rank 1: n=24 win=62.5 avg=0.1079 median=0.6689 max=10.0 min=-10.0
- KOSDAQ rank 2: n=25 win=44.0 avg=-0.5232 median=-0.863 max=10.0 min=-10.0
- KOSDAQ rank 3: n=24 win=45.83 avg=-0.7577 median=-1.1704 max=10.0 min=-10.0
- KOSDAQ rank 4: n=22 win=86.36 avg=4.9742 median=4.6855 max=10.0 min=-4.258
- KOSDAQ rank 5: n=24 win=41.67 avg=-0.7115 median=-1.8753 max=10.0 min=-10.0

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
