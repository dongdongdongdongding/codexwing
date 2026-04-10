# KR Swing Model Benchmark

- rows: `187`
- positives(3D >= 5%): `40`

## xgboost
- auc: `0.6224`
- accuracy: `0.7719`
- positive_precision: `0.5000`
- positive_recall: `0.0769`
- best_threshold: `0.25` | picks `10` | avg_return `+7.82%` | win `80.0%` | hit `40.0%`

## histgb
- auc: `0.6897`
- accuracy: `0.7719`
- positive_precision: `0.0000`
- positive_recall: `0.0000`
- best_threshold: `0.20` | picks `14` | avg_return `+6.80%` | win `71.4%` | hit `50.0%`

## lightgbm
- auc: `0.6897`
- accuracy: `0.7719`
- positive_precision: `0.5000`
- positive_recall: `0.5385`
- best_threshold: `0.50` | picks `14` | avg_return `+6.80%` | win `71.4%` | hit `50.0%`

## rf
- auc: `0.5140`
- accuracy: `0.7895`
- positive_precision: `1.0000`
- positive_recall: `0.0769`
- best_threshold: `0.25` | picks `20` | avg_return `+4.33%` | win `70.0%` | hit `25.0%`

## extratrees
- auc: `0.4108`
- accuracy: `0.7895`
- positive_precision: `1.0000`
- positive_recall: `0.0769`
- best_threshold: `0.30` | picks `8` | avg_return `+3.55%` | win `62.5%` | hit `25.0%`

## logistic
- auc: `0.3794`
- accuracy: `0.6842`
- positive_precision: `0.1429`
- positive_recall: `0.0769`
- best_threshold: `0.20` | picks `16` | avg_return `+1.80%` | win `62.5%` | hit `12.5%`

