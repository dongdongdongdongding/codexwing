# Accuracy Tuning Report (2026-03-31)

## Key Findings
- Legacy `decision_score` ranking was underperforming on recent labeled scans.
- `Peak + Overheat + ML>=30` was the clearest positive pocket.
- `Rising without expansion` and `RSI_DIV` patterns were weak.
- Historical `ml_prob > 100` outliers existed and needed sanitization.

## Recent Proxy Evaluation
- Old Top20: avg `-2.16%`, win>0 `35.0%`, win>5 `0.0%`
- New proxy Top20: avg `+6.15%`, win>0 `50.0%`, win>5 `50.0%`
- New proxy Top50: avg `+2.98%`, win>0 `50.0%`, win>5 `36.0%`

## Applied Changes
- Reweighted `decision_score` toward alpha/model and away from whale-heavy ranking.
- Added edge adjustment for `Peak+Overheat+ModelConfirm`.
- Penalized `Rising without expansion`, `RSI_DIV`, and weak `OBV_DIV`.
- Sanitized DB `ml_prob` writes to `0..100`.
