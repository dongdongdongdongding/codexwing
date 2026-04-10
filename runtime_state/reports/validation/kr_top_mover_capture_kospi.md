# KRX Top Mover Capture (KOSPI)

- generated_at: 2026-04-10T08:50:53.303498+00:00
- confidence_level: 98.00%
- rows: 5289
- days: 10

## Baseline
- 10% hit rate: 11.80% (CI 10.80% ~ 12.87%)
- positive 1D: 32.40% (CI 30.78% ~ 34.07%)
- positive 3D: 37.06% (CI 34.87% ~ 39.30%)
- avoid down 1D: 32.50% (CI 30.87% ~ 34.16%)
- avoid down 3D: 38.46% (CI 36.25% ~ 40.71%)
- avg max return: +2.18% (CI +1.80% ~ +2.58%)
- avg 1D return: -1.30% (CI -1.53% ~ -1.09%)
- avg 3D return: +1.14% (CI +0.63% ~ +1.64%)

## Daily Top-N
- top5: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=58.33% | positive3D=0.00% | avoidDown1D=58.33% | avoidDown3D=0.00% | avg1D=+0.91% | avg3D=+0.00% | avg_max_return=+0.91% (CI -3.16% ~ +4.48%)
- top10: precision=5.00% (CI 0.00% ~ 12.50%) | recall=5.96% (CI 0.00% ~ 15.96%) | positive1D=46.88% | positive3D=100.00% | avoidDown1D=46.88% | avoidDown3D=100.00% | avg1D=+0.18% | avg3D=+23.20% | avg_max_return=+3.48% (CI -1.12% ~ +5.84%)
- top20: precision=6.25% (CI 0.00% ~ 17.50%) | recall=9.04% (CI 0.68% ~ 18.37%) | positive1D=68.87% | positive3D=100.00% | avoidDown1D=68.87% | avoidDown3D=100.00% | avg1D=+1.68% | avg3D=+19.55% | avg_max_return=+4.75% (CI +1.96% ~ +6.80%)
- top50: precision=5.00% (CI 0.00% ~ 11.00%) | recall=19.45% (CI 3.37% ~ 36.08%) | positive1D=52.49% | positive3D=83.33% | avoidDown1D=52.49% | avoidDown3D=83.33% | avg1D=+0.93% | avg3D=+7.39% | avg_max_return=+2.62% (CI +0.65% ~ +5.22%)

## By Scan Mode
- scan_mode=SWING: n=1808 hit10=18.86% (CI 16.81% ~ 21.09%) lift=1.5986
- scan_mode=INTRADAY: n=3440 hit10=8.23% (CI 7.20% ~ 9.38%) lift=0.6973

## By Decision Bucket
- decision_bucket=watchlist: n=1640 hit10=16.59% (CI 14.56% ~ 18.83%) lift=1.4058
- decision_bucket=picked: n=2883 hit10=10.82% (CI 9.55% ~ 12.24%) lift=0.9173
- decision_bucket=unknown: n=367 hit10=5.45% (CI 3.29% ~ 8.91%) lift=0.4619
- decision_bucket=exception_leader: n=399 hit10=5.01% (CI 3.02% ~ 8.21%) lift=0.4249

## By Scan Mode + Bucket
- scan_mode=SWING | decision_bucket=picked: n=356 hit10=25.56% (CI 20.58% ~ 31.28%) lift=2.1666
- scan_mode=SWING | decision_bucket=watchlist: n=894 hit10=23.49% (CI 20.36% ~ 26.94%) lift=1.991
- scan_mode=INTRADAY | decision_bucket=picked: n=2527 hit10=8.75% (CI 7.52% ~ 10.14%) lift=0.7413
- scan_mode=SWING | decision_bucket=unknown: n=169 hit10=11.83% (CI 7.21% ~ 18.83%) lift=1.0031
- scan_mode=INTRADAY | decision_bucket=watchlist: n=746 hit10=8.31% (CI 6.25% ~ 10.97%) lift=0.7044
- scan_mode=SWING | decision_bucket=exception_leader: n=389 hit10=5.14% (CI 3.10% ~ 8.42%) lift=0.4358
- scan_mode=INTRADAY | decision_bucket=unknown: n=157 hit10=0.00% (CI 0.00% ~ 3.33%) lift=0.0

## By Phase25 Variant
- phase25_variant=unknown: n=4996 hit10=12.47% (CI 11.42% ~ 13.60%) lift=1.0569
- phase25_variant=phase25_kr_intraday_xgboost: n=226 hit10=0.44% (CI 0.06% ~ 3.14%) lift=0.0375

## Score Bands
- (112.36, 155.35] [112.9, 155.3]: n=142 hit10=7.75% (CI 3.95% ~ 14.65%)
- (105.0, 112.36] [105.2, 112.4]: n=130 hit10=6.92% (CI 3.29% ~ 14.00%)
- (100.0, 105.0] [101.0, 105.0]: n=154 hit10=24.68% (CI 17.55% ~ 33.52%)
- (94.9, 100.0] [95.2, 100.0]: n=170 hit10=8.24% (CI 4.53% ~ 14.52%)
- (86.7, 94.9] [87.1, 94.9]: n=148 hit10=7.43% (CI 3.78% ~ 14.08%)
- (80.2, 86.7] [80.5, 86.7]: n=149 hit10=2.01% (CI 0.57% ~ 6.82%)
- (75.4, 80.2] [75.5, 80.2]: n=144 hit10=8.33% (CI 4.37% ~ 15.31%)
- (69.9, 75.4] [70.2, 75.4]: n=152 hit10=0.00% (CI 0.00% ~ 3.44%)
