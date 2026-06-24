# Intraday Candidate Registry

- Version: `intraday_candidate_registry_v1`
- Scope: `INTRADAY`
- Production enabled: `False`
- Swing contamination allowed: `False`

## Candidates

### kospi_intraday_0905_5d_t10s5_shadow_v1

- Status: `shadow_candidate`
- Segment: `KOSPI` / `INTRADAY` / `KR_INTRADAY_5D`
- Entry: `09:05 minute-confirmed entry`
- Horizon: `5D`
- Liquidity floor: `100eok`
- Validation: n=421, days=101, months=10, net=2.30%, excess=1.27%, win=62.71%, day_win=78.22%, stop_first=15.20%
- Promotion guard: `shadow_only` - Daily-basket win clears 75%, but per-pick win is below 75% and stop-first is near the 15% guard. Needs forward ledger before production.

### kosdaq_intraday_1400_3d_t5_lgbm_shadow_v1

- Status: `shadow_candidate`
- Segment: `KOSDAQ` / `INTRADAY` / `KR_INTRADAY_3D_T5`
- Entry: `14:00 minute-confirmed entry, daily top5 if calibrated probability >=75%`
- Horizon: `3D`
- Liquidity floor: `30eok`
- Validation: n=218, days=91, months=8, hit=81.70%, hit_ci=[76.60,86.20]%, day_hit=93.40%, avg_pred=88.20%, stop2_touch=78.40%
- Promotion guard: `shadow_only` - Meets the 3D +5% target-touch probability goal, but stop/drawdown incidence is high. Forward ledger must track target-touch and drawdown separately before production.

### kosdaq_intraday_tail_guard_research_v1

- Status: `research_only`
- Segment: `KOSDAQ` / `INTRADAY` / `KR_INTRADAY_5D`
- Entry: `11:30 minute-confirmed entry with nostop/MAE guard`
- Horizon: `5D`
- Liquidity floor: `30eok`
- Validation: n=174, days=101, months=9, net=1.08%, excess=1.19%, win=49.40%, day_win=50.50%, stop_first=17.80%
- Promotion guard: `research_only` - Tail guard lowers stop-first, but win/day-win stay near 50%; not an operating promotion candidate.
