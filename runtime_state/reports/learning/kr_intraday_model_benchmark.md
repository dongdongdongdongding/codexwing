# KR Intraday Model Benchmark

- rows: `2391`
- positives(1D > 0%): `1035`

## logistic
- auc: `0.5253`
- accuracy: `0.4624`
- positive_precision: `0.4629`
- positive_recall: `0.9701`
- best_threshold: `0.70` | picks `38` | avg_return `+1.36%` | win `57.9%` | hit `57.9%`

## extratrees
- auc: `0.4830`
- accuracy: `0.4916`
- positive_precision: `0.4705`
- positive_recall: `0.7395`
- best_threshold: `0.40` | picks `535` | avg_return `+0.61%` | win `47.5%` | hit `47.5%`

## rf
- auc: `0.4818`
- accuracy: `0.4833`
- positive_precision: `0.4637`
- positive_recall: `0.7066`
- best_threshold: `0.40` | picks `535` | avg_return `+0.61%` | win `47.5%` | hit `47.5%`

## histgb
- auc: `0.4693`
- accuracy: `0.4791`
- positive_precision: `0.4603`
- positive_recall: `0.6946`
- best_threshold: `0.30` | picks `530` | avg_return `+0.59%` | win `47.2%` | hit `47.2%`

## lightgbm
- auc: `0.4714`
- accuracy: `0.4875`
- positive_precision: `0.4673`
- positive_recall: `0.7275`
- best_threshold: `0.40` | picks `532` | avg_return `+0.59%` | win `47.4%` | hit `47.4%`

## xgboost
- auc: `0.4776`
- accuracy: `0.4791`
- positive_precision: `0.4608`
- positive_recall: `0.7036`
- best_threshold: `0.30` | picks `538` | avg_return `+0.59%` | win `47.2%` | hit `47.2%`

