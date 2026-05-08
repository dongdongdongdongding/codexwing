# KR Swing Model Benchmark

- rows: `2380`
- positives(3D >= 5%): `962`

## logistic
- auc: `0.5706`
- accuracy: `0.5854`
- positive_precision: `0.4303`
- positive_recall: `0.4138`
- best_threshold: `0.50` | picks `251` | avg_return `+6.29%` | win `58.6%` | hit `43.0%`

## histgb
- auc: `0.5641`
- accuracy: `0.5714`
- positive_precision: `0.4221`
- positive_recall: `0.4674`
- best_threshold: `0.50` | picks `289` | avg_return `+5.97%` | win `58.8%` | hit `42.2%`

## lightgbm
- auc: `0.5654`
- accuracy: `0.5392`
- positive_precision: `0.4071`
- positive_recall: `0.5709`
- best_threshold: `0.60` | picks `257` | avg_return `+5.82%` | win `58.8%` | hit `42.4%`

## rf
- auc: `0.5675`
- accuracy: `0.5700`
- positive_precision: `0.4196`
- positive_recall: `0.4598`
- best_threshold: `0.60` | picks `180` | avg_return `+5.78%` | win `55.0%` | hit `41.1%`

## xgboost
- auc: `0.5617`
- accuracy: `0.5714`
- positive_precision: `0.4176`
- positive_recall: `0.4368`
- best_threshold: `0.50` | picks `273` | avg_return `+5.72%` | win `57.5%` | hit `41.8%`

## extratrees
- auc: `0.5668`
- accuracy: `0.5630`
- positive_precision: `0.4141`
- positive_recall: `0.4713`
- best_threshold: `0.55` | picks `220` | avg_return `+5.68%` | win `57.7%` | hit `41.8%`

