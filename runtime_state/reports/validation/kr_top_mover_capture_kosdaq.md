# KRX Top Mover Capture (KOSDAQ)

- generated_at: 2026-04-10T13:02:11.495772+00:00
- confidence_level: 98.00%
- rows: 14637
- days: 10

## Baseline
- 10% hit rate: 7.48% (CI 6.99% ~ 8.00%)
- positive 1D: 32.57% (CI 31.59% ~ 33.58%)
- positive 3D: 31.14% (CI 29.78% ~ 32.52%)
- avoid down 1D: 33.73% (CI 32.74% ~ 34.75%)
- avoid down 3D: 31.79% (CI 30.42% ~ 33.18%)
- avg max return: +0.46% (CI +0.26% ~ +0.67%)
- avg 1D return: -2.00% (CI -2.13% ~ -1.87%)
- avg 3D return: -2.57% (CI -2.89% ~ -2.24%)

## Daily Top-N
- top5: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=16.67% | positive3D=50.00% | avoidDown1D=16.67% | avoidDown3D=50.00% | avg1D=-2.26% | avg3D=+0.53% | avg_max_return=-1.89% (CI -4.21% ~ +1.33%)
- top10: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=21.43% | positive3D=66.67% | avoidDown1D=21.43% | avoidDown3D=66.67% | avg1D=-1.68% | avg3D=+0.58% | avg_max_return=-1.35% (CI -3.77% ~ +1.48%)
- top20: precision=0.00% (CI 0.00% ~ 0.00%) | recall=0.00% (CI 0.00% ~ 0.00%) | positive1D=26.19% | positive3D=75.00% | avoidDown1D=26.19% | avoidDown3D=75.00% | avg1D=-1.36% | avg3D=+1.05% | avg_max_return=-0.72% (CI -3.49% ~ +2.10%)
- top50: precision=0.60% (CI 0.00% ~ 2.40%) | recall=0.83% (CI 0.00% ~ 2.50%) | positive1D=32.91% | positive3D=58.67% | avoidDown1D=32.91% | avoidDown3D=58.67% | avg1D=-1.35% | avg3D=+1.79% | avg_max_return=-0.50% (CI -3.00% ~ +1.91%)

## By Scan Mode
- scan_mode=SWING: n=3337 hit10=9.83% (CI 8.69% ~ 11.09%) lift=1.3139
- scan_mode=INTRADAY: n=11299 hit10=6.79% (CI 6.26% ~ 7.36%) lift=0.9074

## By Decision Bucket
- decision_bucket=picked: n=8400 hit10=8.02% (CI 7.36% ~ 8.74%) lift=1.0726
- decision_bucket=watchlist: n=3605 hit10=8.32% (CI 7.31% ~ 9.46%) lift=1.1124
- decision_bucket=exception_leader: n=1578 hit10=7.67% (CI 6.25% ~ 9.37%) lift=1.025
- decision_bucket=unknown: n=1054 hit10=0.00% (CI 0.00% ~ 0.51%) lift=0.0

## By Scan Mode + Bucket
- scan_mode=SWING | decision_bucket=watchlist: n=1068 hit10=12.36% (CI 10.20% ~ 14.89%) lift=1.6521
- scan_mode=SWING | decision_bucket=picked: n=704 hit10=10.94% (CI 8.49% ~ 13.98%) lift=1.462
- scan_mode=INTRADAY | decision_bucket=picked: n=7696 hit10=7.76% (CI 7.08% ~ 8.50%) lift=1.0369
- scan_mode=SWING | decision_bucket=exception_leader: n=1535 hit10=7.75% (CI 6.31% ~ 9.49%) lift=1.0363
- scan_mode=INTRADAY | decision_bucket=watchlist: n=2537 hit10=6.62% (CI 5.56% ~ 7.87%) lift=0.8852
- scan_mode=INTRADAY | decision_bucket=unknown: n=1023 hit10=0.00% (CI 0.00% ~ 0.53%) lift=0.0

## By Phase25 Variant
- phase25_variant=unknown: n=13587 hit10=7.93% (CI 7.40% ~ 8.48%) lift=1.0596
- phase25_variant=phase25_kr_intraday_xgboost: n=1043 hit10=1.73% (CI 1.01% ~ 2.94%) lift=0.2307

## Score Bands
- (100.0, 136.3] [100.2, 136.3]: n=364 hit10=1.65% (CI 0.66% ~ 4.05%)
- (95.0, 100.0] [95.1, 100.0]: n=2099 hit10=5.81% (CI 4.73% ~ 7.12%)
- (88.3, 95.0] [88.4, 95.0]: n=822 hit10=13.26% (CI 10.75% ~ 16.25%)
- (82.5, 88.3] [82.6, 88.3]: n=817 hit10=6.24% (CI 4.55% ~ 8.51%)
- (79.8, 82.5] [79.9, 82.5]: n=858 hit10=8.16% (CI 6.24% ~ 10.60%)
- (76.0, 79.8] [76.1, 79.8]: n=826 hit10=6.90% (CI 5.12% ~ 9.25%)
- (72.4, 76.0] [72.6, 76.0]: n=818 hit10=4.40% (CI 3.01% ~ 6.39%)
- (68.0, 72.4] [68.1, 72.4]: n=760 hit10=5.92% (CI 4.22% ~ 8.24%)
