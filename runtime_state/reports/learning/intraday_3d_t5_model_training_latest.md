# Intraday 3D +5% Touch Model

- Model: `kosdaq_intraday_3d_t5_lgbm_isotonic_v1`
- Segment: `KOSDAQ` / `INTRADAY` / `KR_INTRADAY_3D_T5`
- Entry: `14:00`
- Liquidity floor: `30eok`
- Target: entry price 기준 3거래일 안에 high가 +5% 이상 터치
- Selection: p>=75%, daily top5

## OOS Validation
- Base hit: 44.53%
- AUC calibrated: 0.613
- Selected: n=218, days=91, months=8
- Hit: 81.65% CI[76.61,86.24]
- Day hit: 93.41%
- Avg predicted probability: 88.15%
- MFE/MAE/close3: 19.30% / -9.21% / 3.61%
- Stop -2% touch incidence: 78.44%

## Warning
- This is a target-touch probability model, not a low-drawdown model. Forward ledger must track drawdown and fill quality separately.
