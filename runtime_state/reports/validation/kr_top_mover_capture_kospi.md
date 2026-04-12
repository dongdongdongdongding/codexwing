# KRX Top Mover Capture (KOSPI)

- generated_at: 2026-04-10T13:01:59.013210+00:00
- confidence_level: 98.00%
- rows: 5705
- days: 10

## Baseline
- 10% hit rate: 12.99% (CI 11.99% ~ 14.06%)
- positive 1D: 32.93% (CI 31.37% ~ 34.54%)
- positive 3D: 38.05% (CI 35.97% ~ 40.17%)
- avoid down 1D: 33.06% (CI 31.50% ~ 34.66%)
- avoid down 3D: 39.43% (CI 37.34% ~ 41.56%)
- avg max return: +2.69% (CI +2.31% ~ +3.09%)
- avg 1D return: -1.22% (CI -1.43% ~ -1.01%)
- avg 3D return: +1.25% (CI +0.79% ~ +1.71%)

## Daily Top-N
- top5: precision=2.50% (CI 0.00% ~ 10.00%) | recall=6.67% (CI 0.00% ~ 20.00%) | positive1D=68.75% | positive3D=50.00% | avoidDown1D=68.75% | avoidDown3D=50.00% | avg1D=+4.83% | avg3D=+1.44% | avg_max_return=+4.92% (CI -2.02% ~ +13.65%)
- top10: precision=7.50% (CI 0.00% ~ 17.50%) | recall=11.33% (CI 0.67% ~ 25.33%) | positive1D=57.50% | positive3D=88.89% | avoidDown1D=57.50% | avoidDown3D=88.89% | avg1D=+1.89% | avg3D=+16.33% | avg_max_return=+5.08% (CI +0.31% ~ +8.22%)
- top20: precision=7.50% (CI 0.00% ~ 20.62%) | recall=13.33% (CI 0.00% ~ 26.67%) | positive1D=68.75% | positive3D=91.67% | avoidDown1D=68.75% | avoidDown3D=91.67% | avg1D=+1.93% | avg3D=+14.14% | avg_max_return=+5.01% (CI +1.26% ~ +7.38%)
- top50: precision=6.75% (CI 0.50% ~ 13.75%) | recall=28.07% (CI 6.74% ~ 53.36%) | positive1D=60.13% | positive3D=85.19% | avoidDown1D=60.13% | avoidDown3D=85.19% | avg1D=+1.98% | avg3D=+7.57% | avg_max_return=+3.85% (CI +1.20% ~ +6.52%)

## By Scan Mode
- scan_mode=SWING: n=2012 hit10=19.18% (CI 17.23% ~ 21.31%) lift=1.4771
- scan_mode=INTRADAY: n=3652 hit10=9.72% (CI 8.64% ~ 10.92%) lift=0.7484

## By Decision Bucket
- decision_bucket=watchlist: n=1780 hit10=17.70% (CI 15.69% ~ 19.90%) lift=1.3625
- decision_bucket=picked: n=3089 hit10=12.24% (CI 10.93% ~ 13.68%) lift=0.9421
- decision_bucket=exception_leader: n=454 hit10=5.73% (CI 3.67% ~ 8.82%) lift=0.4409
- decision_bucket=unknown: n=382 hit10=5.76% (CI 3.56% ~ 9.20%) lift=0.4434

## By Scan Mode + Bucket
- scan_mode=SWING | decision_bucket=picked: n=386 hit10=26.17% (CI 21.32% ~ 31.67%) lift=2.0145
- scan_mode=SWING | decision_bucket=watchlist: n=988 hit10=23.99% (CI 20.97% ~ 27.28%) lift=1.8468
- scan_mode=INTRADAY | decision_bucket=picked: n=2703 hit10=10.25% (CI 8.97% ~ 11.69%) lift=0.789
- scan_mode=INTRADAY | decision_bucket=watchlist: n=792 hit10=9.85% (CI 7.65% ~ 12.59%) lift=0.7582
- scan_mode=SWING | decision_bucket=unknown: n=195 hit10=11.28% (CI 7.02% ~ 17.63%) lift=0.8686
- scan_mode=SWING | decision_bucket=exception_leader: n=443 hit10=5.87% (CI 3.77% ~ 9.04%) lift=0.4519
- scan_mode=INTRADAY | decision_bucket=unknown: n=146 hit10=0.00% (CI 0.00% ~ 3.57%) lift=0.0

## By Phase25 Variant
- phase25_variant=unknown: n=5399 hit10=13.71% (CI 12.65% ~ 14.83%) lift=1.0552
- phase25_variant=phase25_kr_intraday_xgboost: n=207 hit10=0.48% (CI 0.07% ~ 3.42%) lift=0.0372

## Score Bands
- (113.0, 155.35] [113.3, 155.3]: n=148 hit10=10.14% (CI 5.70% ~ 17.38%)
- (105.0, 113.0] [105.2, 113.0]: n=174 hit10=6.32% (CI 3.21% ~ 12.07%)
- (100.0, 105.0] [101.0, 105.0]: n=170 hit10=25.88% (CI 18.90% ~ 34.36%)
- (95.7, 100.0] [96.2, 100.0]: n=172 hit10=5.81% (CI 2.86% ~ 11.47%)
- (89.0, 95.7] [89.5, 95.7]: n=170 hit10=10.59% (CI 6.26% ~ 17.34%)
- (81.0, 89.0] [81.1, 89.0]: n=143 hit10=5.59% (CI 2.54% ~ 11.89%)
- (75.5, 81.0] [75.8, 81.0]: n=188 hit10=10.64% (CI 6.47% ~ 17.01%)
- (69.3, 75.5] [69.9, 75.5]: n=169 hit10=2.37% (CI 0.79% ~ 6.90%)
