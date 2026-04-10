# KRX Top Mover Capture (KOSDAQ)

- generated_at: 2026-04-10T08:51:05.027840+00:00
- confidence_level: 98.00%
- rows: 13900
- days: 10

## Baseline
- 10% hit rate: 6.80% (CI 6.32% ~ 7.31%)
- positive 1D: 32.78% (CI 31.76% ~ 33.82%)
- positive 3D: 30.27% (CI 28.84% ~ 31.74%)
- avoid down 1D: 33.97% (CI 32.94% ~ 35.02%)
- avoid down 3D: 30.86% (CI 29.42% ~ 32.33%)
- avg max return: +0.14% (CI -0.07% ~ +0.35%)
- avg 1D return: -1.96% (CI -2.10% ~ -1.82%)
- avg 3D return: -2.68% (CI -3.04% ~ -2.33%)

## Daily Top-N
- top5: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=20.00% | positive3D=0.00% | avoidDown1D=20.00% | avoidDown3D=0.00% | avg1D=-2.49% | avg3D=-6.47% | avg_max_return=-2.49% (CI -4.61% ~ +1.05%)
- top10: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=16.67% | positive3D=50.00% | avoidDown1D=16.67% | avoidDown3D=50.00% | avg1D=-2.32% | avg3D=-2.90% | avg_max_return=-2.32% (CI -4.48% ~ +0.91%)
- top20: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=20.83% | positive3D=66.67% | avoidDown1D=20.83% | avoidDown3D=66.67% | avg1D=-2.07% | avg3D=-1.11% | avg_max_return=-1.71% (CI -4.37% ~ +1.73%)
- top50: precision=0.20% (CI 0.00% ~ 0.80%) | recall=5.00% (CI 0.00% ~ 15.00%) | positive1D=31.65% | positive3D=49.52% | avoidDown1D=31.65% | avoidDown3D=49.52% | avg1D=-1.28% | avg3D=-0.93% | avg_max_return=-0.76% (CI -3.21% ~ +1.62%)

## By Scan Mode
- scan_mode=SWING: n=3059 hit10=9.25% (CI 8.10% ~ 10.54%) lift=1.3608
- scan_mode=INTRADAY: n=10840 hit10=6.11% (CI 5.59% ~ 6.66%) lift=0.8983

## By Decision Bucket
- decision_bucket=picked: n=8006 hit10=7.27% (CI 6.62% ~ 7.97%) lift=1.0693
- decision_bucket=watchlist: n=3415 hit10=7.47% (CI 6.49% ~ 8.58%) lift=1.0983
- decision_bucket=exception_leader: n=1430 hit10=7.55% (CI 6.08% ~ 9.34%) lift=1.1109
- decision_bucket=unknown: n=1049 hit10=0.00% (CI 0.00% ~ 0.51%) lift=0.0

## By Scan Mode + Bucket
- scan_mode=SWING | decision_bucket=watchlist: n=974 hit10=11.29% (CI 9.14% ~ 13.87%) lift=1.6612
- scan_mode=SWING | decision_bucket=picked: n=663 hit10=10.11% (CI 7.70% ~ 13.16%) lift=1.4864
- scan_mode=INTRADAY | decision_bucket=picked: n=7343 hit10=7.01% (CI 6.35% ~ 7.74%) lift=1.0316
- scan_mode=SWING | decision_bucket=exception_leader: n=1394 hit10=7.60% (CI 6.11% ~ 9.42%) lift=1.1185
- scan_mode=INTRADAY | decision_bucket=watchlist: n=2441 hit10=5.94% (CI 4.92% ~ 7.15%) lift=0.8737
- scan_mode=INTRADAY | decision_bucket=unknown: n=1020 hit10=0.00% (CI 0.00% ~ 0.53%) lift=0.0

## By Phase25 Variant
- phase25_variant=unknown: n=12853 hit10=7.25% (CI 6.74% ~ 7.80%) lift=1.0666
- phase25_variant=phase25_kr_intraday_xgboost: n=1040 hit10=1.25% (CI 0.66% ~ 2.34%) lift=0.1839

## Score Bands
- (100.0, 136.3] [100.2, 136.3]: n=322 hit10=0.00% (CI 0.00% ~ 1.65%)
- (95.0, 100.0] [95.1, 100.0]: n=2037 hit10=5.15% (CI 4.13% ~ 6.42%)
- (88.3, 95.0] [88.4, 95.0]: n=795 hit10=12.96% (CI 10.43% ~ 15.98%)
- (82.5, 88.3] [82.6, 88.3]: n=800 hit10=6.00% (CI 4.33% ~ 8.26%)
- (80.0, 82.5] [80.1, 82.5]: n=803 hit10=7.85% (CI 5.91% ~ 10.35%)
- (76.6, 80.0] [76.7, 80.0]: n=799 hit10=6.01% (CI 4.33% ~ 8.27%)
- (72.6, 76.6] [72.7, 76.6]: n=782 hit10=3.84% (CI 2.53% ~ 5.78%)
- (68.0, 72.6] [68.1, 72.6]: n=757 hit10=5.94% (CI 4.24% ~ 8.27%)
