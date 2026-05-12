# Paper Trade Shadow Ledger

- generated_at: `2026-05-11T12:38:02.944001+00:00`
- mode: `close_to_close_shadow_v1`
- ledger_rows: `345`
- closed_rows: `308`
- unresolved_rows: `37`
- fee_bps: `0.0`
- slippage_bps: `0.0`

## Market Metrics
- : n=76 win=55.26 avg=0.9003 median=0.6452 max=7.0 min=-5.0 hit5=28.95 loss5=28.95
- AMEX: n=22 win=36.36 avg=-0.5456 median=-0.1779 max=4.9671 min=-5.0 hit5=0.0 loss5=9.09
- KOSDAQ: n=115 win=55.65 avg=0.506 median=0.8757 max=10.0 min=-10.0 hit5=24.35 loss5=19.13
- KOSPI: n=81 win=59.26 avg=3.0199 median=1.1029 max=20.0 min=-7.0671 hit5=34.57 loss5=23.46
- KR: n=9 win=33.33 avg=-1.2421 median=-1.7028 max=7.0 min=-5.0 hit5=11.11 loss5=22.22
- NASDAQ: n=5 win=100.0 avg=5.8738 median=7.0 max=7.0 min=1.8449 hit5=80.0 loss5=0.0

## Rank Metrics
-  rank 1: n=21 win=38.1 avg=-0.3167 median=-2.8412 max=7.0 min=-5.0
-  rank 2: n=16 win=56.25 avg=1.26 median=1.4517 max=7.0 min=-5.0
-  rank 3: n=14 win=64.29 avg=2.4364 median=1.9569 max=7.0 min=-5.0
-  rank 4: n=14 win=42.86 avg=-0.1519 median=-0.4814 max=7.0 min=-5.0
-  rank 5: n=11 win=90.91 avg=2.0846 median=0.7207 max=7.0 min=-5.0
- AMEX rank 1: n=6 win=16.67 avg=-1.8715 median=-2.2244 max=1.2321 min=-5.0
- AMEX rank 2: n=3 win=33.33 avg=-0.011 median=0.0 max=4.9671 min=-5.0
- AMEX rank 3: n=5 win=40.0 avg=0.5626 median=-0.3063 max=4.7392 min=-1.0709
- AMEX rank 4: n=4 win=25.0 avg=-1.8521 median=-2.4147 max=2.2284 min=-4.8077
- AMEX rank 5: n=4 win=75.0 avg=0.9637 median=0.6829 max=2.6365 min=-0.1477
- KOSDAQ rank 1: n=23 win=60.87 avg=0.0502 median=0.6689 max=10.0 min=-10.0
- KOSDAQ rank 2: n=25 win=48.0 avg=-0.453 median=0.0 max=10.0 min=-10.0
- KOSDAQ rank 3: n=23 win=43.48 avg=-0.5151 median=-1.7129 max=10.0 min=-10.0
- KOSDAQ rank 4: n=21 win=80.95 avg=3.7825 median=3.4951 max=10.0 min=-10.0
- KOSDAQ rank 5: n=23 win=47.83 avg=0.0334 median=-0.25 max=10.0 min=-10.0
- KOSPI rank 1: n=15 win=73.33 avg=8.7191 median=9.5062 max=20.0 min=-5.0
- KOSPI rank 2: n=19 win=57.89 avg=1.9969 median=0.8499 max=20.0 min=-5.0
- KOSPI rank 3: n=14 win=42.86 avg=0.9835 median=-0.5703 max=20.0 min=-5.0
- KOSPI rank 4: n=18 win=55.56 avg=1.4679 median=1.8636 max=9.4268 min=-7.0671
- KOSPI rank 5: n=15 win=66.67 avg=2.3793 median=1.4368 max=17.0775 min=-5.0
- KR rank 1: n=3 win=33.33 avg=0.0991 median=-1.7028 max=7.0 min=-5.0
- KR rank 2: n=3 win=66.67 avg=0.3226 median=1.1006 max=1.1261 min=-1.2589
- KR rank 3: n=1 win=0.0 avg=-5.0 median=-5.0 max=-5.0 min=-5.0
- KR rank 4: n=1 win=0.0 avg=-3.3129 median=-3.3129 max=-3.3129 min=-3.3129
- KR rank 5: n=1 win=0.0 avg=-4.1314 median=-4.1314 max=-4.1314 min=-4.1314
- NASDAQ rank 1: n=1 win=100.0 avg=7.0 median=7.0 max=7.0 min=7.0
- NASDAQ rank 2: n=1 win=100.0 avg=7.0 median=7.0 max=7.0 min=7.0
- NASDAQ rank 3: n=1 win=100.0 avg=7.0 median=7.0 max=7.0 min=7.0
- NASDAQ rank 4: n=1 win=100.0 avg=6.524 median=6.524 max=6.524 min=6.524
- NASDAQ rank 5: n=1 win=100.0 avg=1.8449 median=1.8449 max=1.8449 min=1.8449

## Interpretation
- This is a real-data shadow ledger, not a broker fill ledger.
- Rows without realized return data remain unresolved instead of being filled as losses or wins.
- The schema is Supabase-friendly and can be upserted when the execution table is added.
