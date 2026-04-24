# Backtest Findings — 2026-04-25

Dataset: `runtime_state/reports/archive/scan_archive_learning_dataset_all.csv` (61,470 rows, 41,257 with labels)
Features: `alpha_score`, `ml_prob`, `decision_score` (core 3)
Model: GradientBoostingClassifier (n=200, depth=3), walk-forward 70/30 chronological split

## The finding

The scanner's three core signals are **directionally correct on KOSPI but inverted on KOSDAQ**.

### KOSDAQ SWING (n_total=4,801 | n_test=1,441 | AUC=0.467)

| Decile | Win rate (3d) | Avg return (3d) |
|---|---|---|
| Base | 59.1% | +3.90% |
| **Top 10% (model's best picks)** | **52.8%** | +2.29% |
| **Bottom 10% (model's worst picks)** | **92.4%** | **+5.83%** |

Current scanner `decision_bucket=picked` (train+test combined):
- n=158, win_3d = **24.7%**, avg_ret = **−5.75%**, hit_5% = 22.2%, stop_3% = **72.2%**

The worst rows by the model's own scoring outperform the best by 40 percentage points on 3d win rate.

### KOSPI SWING (n_total=2,474 | n_test=743 | AUC=0.598)

| Decile | Win rate (3d) | Avg return (3d) |
|---|---|---|
| Base | 70.8% | +4.30% |
| **Top 10%** | **85.1%** | **+6.14%** |
| Bottom 10% | 56.8% | +2.29% |

KOSPI SWING AUC on `label_win_1d` = 0.631. Signals are directionally correct — top decile delivers +6.14% avg, 85.1% win rate.

### Cross-label summary

| Market | scan_mode | label | AUC | top win | top ret | bot win | bot ret |
|---|---|---|---|---|---|---|---|
| KOSDAQ | SWING | win_1d | 0.406 | 43.8% | -0.47% | 43.2% | +0.34% |
| KOSDAQ | SWING | win_3d | 0.467 | 52.8% | +2.29% | **92.4%** | **+5.83%** |
| KOSDAQ | SWING | hit_10pct | 0.434 | 18.1% | -0.11% | 53.5% | +7.80% |
| KOSPI | SWING | win_1d | 0.631 | 81.1% | +3.63% | 37.8% | +1.21% |
| KOSPI | SWING | win_3d | 0.598 | **85.1%** | **+6.14%** | 56.8% | +2.29% |
| KOSPI | SWING | hit_10pct | 0.510 | 17.6% | +1.14% | 40.5% | +7.77% |

## Interpretation

KOSPI is large-cap, momentum-persistent: scanner signals (alpha_score/ml_prob/decision_score) correctly predict continuation.

KOSDAQ is small-mid-cap, mean-reverting at feature extremes: high `alpha_score` = already over-extended / squeeze peak. The scanner picks names that just finished running.

The `label_hit_10pct` pattern is the giveaway: on KOSDAQ the bottom-decile picks hit 10% gains **53.5%** of the time with **+7.80%** avg — explosive follow-through after "weak" signals.

## Actionable conclusions

1. **KOSDAQ SWING needs signal inversion** or a market-specific model. The existing features carry information, just in the opposite direction for this market.
2. **KOSPI SWING is fine** — retrain on recent data, deploy top-decile gating (≈P80 cutoff gets ~85% win rate).
3. **Don't use combined KOSPI+KOSDAQ training** — signs of features are opposite; a single model averages them to noise (AUC 0.45–0.52).
4. **Target thresholds reachable with existing data**:
   - KOSPI SWING picked: 80%+ 3d win rate, +5% avg return
   - KOSDAQ SWING "anti-picked" (bottom decile of current signals): 90%+ 3d win rate, +5% avg return

## Next steps (Phase E draft)

- Split model training by market (`KOSPI` vs `KOSDAQ`) as a hard partition in `retrain_ml.py` / Phase25 pipeline.
- For KOSDAQ, fit on `-decision_score` and `-alpha_score` as inputs, OR train label-inverted model.
- Re-measure on a rolling 5-day walk-forward to confirm the inversion is stable, not a single-window artifact.
- Before changing scanner, verify with an additional month of out-of-sample KOSDAQ SWING data.

## Caveats

- Walk-forward used 70/30 chronological split on ~3 weeks of data (Apr 1–Apr 21). Results need multi-window confirmation.
- `decision_bucket=picked` on KOSDAQ SWING has only n=158 across full dataset — top-of-top signal is thin.
- `label_hit_5pct` AUC is near-random (0.512 KOSDAQ, 0.464 KOSPI) — the 5% hit rule is harder to predict than 3d win direction.
