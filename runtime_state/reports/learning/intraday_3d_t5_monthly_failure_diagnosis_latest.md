# KOSDAQ Intraday 3D Touch5 Monthly Failure Diagnosis

- Candidate: `kosdaq_intraday_1500_3d_t5_vwap_guard_shadow_v1`
- Model: `kosdaq_intraday_3d_t5_lgbm_isotonic_vwapguard_v1`
- Segment: `KOSDAQ` / `INTRADAY` / `KR_INTRADAY_3D_T5`
- Entry: `15:00`
- Guard: `p_cal>=0.80`, `pre_vwap_dist_pct>=0`, daily top2
- Return policy: 3D close hold, cost 0.33%

## Why 2025-10 / 2026-02 Were Low
- Unguarded selected hit was 66.67% in 2025-10 and 62.50% in 2026-02, but the same-segment base was only 38.05% and 40.79%. The model still had lift; it did not clear the production target.
- Misses were concentrated in names below the 15:00 VWAP or with weak late tape. Selected hits had mean `pre_vwap_dist_pct` +2.79%; misses had -1.88%.
- Bad months had mean `pre_vwap_dist_pct` -2.09% versus +2.78% in other selected months.
- Drawdown pressure was high; tight stops reduce expectancy.

## Guarded OOS Validation
- Selected: n=81, days=49, months=7
- Hit: 90.12% CI[81.70,94.91]
- Month hit minimum: 80.00%
- Day hit: 93.88%
- Exact 3D close return: 10.60% CI[5.48,15.82], net@0.33=10.27%
- Liquidity-decile excess: 9.30% CI[4.26,14.52]
- Exact MFE/MAE: 26.50% / -7.46%
- Stop -2% touch: 66.67%

## Exit Check, net@0.33
- Hold 3D close: 10.27%
- TP15/SL5 first-touch: 6.67%
- TP15 no stop else close: 5.85%
- TP10 no stop else close: 4.80%

## Production Path
- Shadow only now. Wire live 15:00 scoring with the VWAP guard.
- Micro-production only after at least 60 forward picks, 30 days, 2 months, target hit >=75%, day hit >=80%, net 3D close return >0, liquidity-decile excess >0, no month with n>=5 below 65%, realized slippage <=0.50%.
- Full production only after 120 forward picks and 4 forward months with target hit >=70%, Wilson lower >=65%, positive net return, and drawdown review if average MAE is below -9%.
