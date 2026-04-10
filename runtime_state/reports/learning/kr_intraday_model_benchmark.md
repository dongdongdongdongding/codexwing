# KR Intraday Model Benchmark

- rows: `769`
- positives(1D > 0%): `199`

## xgboost
- auc: `0.6117`
- accuracy: `0.5931`
- positive_precision: `0.5556`
- positive_recall: `0.5660`
- best_threshold: `0.60` | picks `79` | avg_return `+1.67%` | win `55.7%` | hit `55.7%`

## histgb
- auc: `0.6061`
- accuracy: `0.5844`
- positive_precision: `0.5463`
- positive_recall: `0.5566`
- best_threshold: `0.70` | picks `48` | avg_return `+1.43%` | win `58.3%` | hit `58.3%`

## rf
- auc: `0.6195`
- accuracy: `0.5628`
- positive_precision: `0.5138`
- positive_recall: `0.8774`
- best_threshold: `0.70` | picks `152` | avg_return `+1.07%` | win `52.0%` | hit `52.0%`

## extratrees
- auc: `0.6120`
- accuracy: `0.5368`
- positive_precision: `0.4975`
- positive_recall: `0.9528`
- best_threshold: `0.70` | picks `191` | avg_return `+0.73%` | win `50.3%` | hit `50.3%`

## lightgbm
- auc: `0.5951`
- accuracy: `0.4545`
- positive_precision: `0.4533`
- positive_recall: `0.9151`
- best_threshold: `0.65` | picks `208` | avg_return `+0.44%` | win `46.2%` | hit `46.2%`

## logistic
- auc: `0.4931`
- accuracy: `0.4589`
- positive_precision: `0.4589`
- positive_recall: `1.0000`
- best_threshold: `0.70` | picks `227` | avg_return `+0.38%` | win `45.8%` | hit `45.8%`

