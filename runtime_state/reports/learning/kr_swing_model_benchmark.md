# KR Swing Model Benchmark

- rows: `2735`
- positives(3D >= 5%): `1071`

## logistic
- auc: `0.5705`
- accuracy: `0.5652`
- positive_precision: `0.3930`
- positive_recall: `0.5216`
- best_threshold: `0.60` | picks `171` | avg_return `+5.57%` | win `51.5%` | hit `41.5%`

## histgb
- auc: `0.5298`
- accuracy: `0.5420`
- positive_precision: `0.3639`
- positive_recall: `0.4712`
- best_threshold: `0.55` | picks `298` | avg_return `+4.22%` | win `52.3%` | hit `37.9%`

## xgboost
- auc: `0.5163`
- accuracy: `0.5311`
- positive_precision: `0.3476`
- positive_recall: `0.4388`
- best_threshold: `0.60` | picks `212` | avg_return `+4.13%` | win `49.1%` | hit `36.8%`

## extratrees
- auc: `0.5383`
- accuracy: `0.5238`
- positive_precision: `0.3584`
- positive_recall: `0.5144`
- best_threshold: `0.55` | picks `288` | avg_return `+3.85%` | win `47.6%` | hit `36.5%`

## lightgbm
- auc: `0.5245`
- accuracy: `0.5079`
- positive_precision: `0.3493`
- positive_recall: `0.5252`
- best_threshold: `0.50` | picks `418` | avg_return `+3.84%` | win `48.1%` | hit `34.9%`

## rf
- auc: `0.5169`
- accuracy: `0.5091`
- positive_precision: `0.3508`
- positive_recall: `0.5288`
- best_threshold: `0.50` | picks `419` | avg_return `+3.67%` | win `48.0%` | hit `35.1%`

