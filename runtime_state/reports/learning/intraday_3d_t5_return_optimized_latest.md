# Intraday 3D +5% Touch Return-Optimized Model

- Model: `kosdaq_intraday_3d_t5_lgbm_isotonic_returnmax_v1`
- Segment: `KOSDAQ` / `INTRADAY` / `KR_INTRADAY_3D_T5`
- Entry: `15:00`
- Liquidity floor: `30eok`
- Target: entry price 기준 3거래일 안에 high가 +5% 이상 터치
- Selection: p>=80%, daily top2
- Return policy: 3D close hold, cost 0.33%

## OOS Validation
- Base hit: 43.78%
- AUC calibrated: 0.623
- Selected: n=105, days=65, months=7
- Hit: 82.86% CI[74.52,88.87]
- Day hit: 84.62%
- Avg predicted probability: 92.82%
- Exact 3D close return: 7.66% CI[3.54,12.07], net@0.33=7.33%
- Same-day universe excess: 6.61%
- Liquidity-decile excess: 6.55% CI[2.42,11.04]
- Exact MFE/MAE: 22.35% / -8.28%
- Stop -2% touch incidence: 74.29%

## Exact Exit Policy Sweep, net@0.33
- Hold 3D close: 7.33%
- TP5 no stop else close: 2.12%
- TP10 no stop else close: 3.16%
- TP15 no stop else close: 4.29%
- TP10/SL5 first-touch: 2.94%
- TP15/SL5 first-touch: 3.97%

## Warning
- Return maximization favors holding to the 3D close, not tight stops. Drawdown is large and monthly target hit is below 70% in 2025-10 and 2026-02. Shadow/forward ledger only.
