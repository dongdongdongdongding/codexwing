# KIS Performance Research Actual Follow-up

- version: `kis_performance_research_actual_followup_v1`
- generated_at: `2026-06-14T04:25:09Z`
- dummy_data_used: `False`
- objective: resume from the strongest prior `touch5_dd10` KIS candidates, verify them on actual fullrank backfilled data, then search the next defensible performance path.

## Executive Result

No new production-ready candidate survived actual fullrank validation.

The strongest prior KOSPI candidate is still the best observed idea, but only as shadow/research: in the original sidecar universe it passed production gates, while strict holdout and fullrank actual recheck both blocked promotion. KOSDAQ compound filters are weaker: they showed high in-sample slices before, but holdout and fullrank matched-sidecar validation both failed.

## Actual Data Used

| input | path | rows/days used |
|---|---|---:|
| KOSPI fullrank actual | `kis_historical_universe_fullrank_actual_augmented_prepared_kospi_20260101_20260610.pkl` | 97,638 / 103 |
| KOSDAQ fullrank actual | `kis_historical_universe_fullrank_actual_augmented_prepared_kosdaq_20260101_20260610.pkl` | 186,203 / 103 |
| KOSPI fullrank sidecar augmented | `kis_historical_universe_fullrank_sidecar_cache_augmented_prepared_kospi_20260101_20260610.pkl` | scoped by KIS presence |
| KOSDAQ fullrank matched sidecar | `kis_historical_universe_fullrank_sidecar_cache_augmented_matched_only_kosdaq_20260101_20260610.pkl` | matched sidecar rows only |

## Fullrank Actual Search

| market | best config | n | days | hit5_dd10 | hit10 | tail | avg exit | dynamic exit | min low | gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| KOSPI | composite pool 50, top1, `ev_hit10` | 23 | 23 | 69.5652 | 30.4348 | 13.0435 | 1.373243 | 2.889206 | -15.847695 | `shadow_risk_review` |
| KOSDAQ | composite pool 100, top1, `ev_hit10` | 20 | 20 | 60.0 | 50.0 | 15.0 | 1.201685 | 3.692196 | -14.301385 | `shadow_risk_review` |

This improved the broad fullrank baseline, but not enough. Both markets missed the production hit-rate gate and the -10% low guard.

## Prior Best Rechecks

| market | candidate | data basis | n | days | hit5_dd10 | avg5 | min low | result |
|---|---|---|---:|---:|---:|---:|---:|---|
| KOSPI | `top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667` | original sidecar cache | 54 | 15 | 98.1481 | 24.676158 | -9.230497 | production-ready research candidate |
| KOSPI | same shape, fullrank sidecar recheck | fullrank sidecar actual | 17 | 17 | 17.6471 | -0.877676 | -6.232202 | blocked |
| KOSDAQ | top5 compound `prob_plus_tail p0.3 tail0` | original sidecar cache | 144 | 16 | 68.0556 | 5.931853 | -33.704825 | blocked |
| KOSDAQ | same shape, fullrank matched sidecar recheck | fullrank matched actual sidecar | 52 | 11 | 53.8462 | -0.481049 | -30.923396 | blocked |

The KOSPI prior result was not fake: the production candidate was driven by a concrete factor, low `close_failure_prior_kis_sector_failure_rate_pct`. The problem is stability. Its holdout best still had `hit5=92.6829`, but min low was `-10.87344`, so it required risk review and did not pass production.

The KOSDAQ compound result is not production-grade. The original run had many low-safe/hit-low-safe in-sample filters, but no sample-sufficient hit-low-safe candidate, and holdout collapsed to `hit5=62.2951`, `min_low=-23.62384`. In fullrank matched-sidecar recheck, holdout selection best fell to `hit5=30.7692`, `avg5=-8.086069`, `min_low=-28.540083`.

## Important Factors

- `close_failure_prior_kis_sector_failure_rate_pct`: strongest positive evidence. It made the prior KOSPI top1 sidecar candidate production-ready in the original sidecar universe.
- Tail-risk / `min_min_low_5d_pct`: main blocker. Fullrank actual best candidates still breached the -10% guard.
- Sample and active-day sufficiency: KOSDAQ compound candidates often looked strong before sample gates, but could not satisfy sample plus low-safety plus holdout at the same time.
- Sidecar exact-date coverage: fullrank actual sidecar coverage is sparse, so flow/news/financial features are not yet reliable enough across the full universe.

## Needed Data

- Ticker-period KIS flow history: foreigner, institution, retail, whale flow windows, whale score.
- Ticker-period KIS financial/valuation history: market cap, PER/PBR, growth, margins, ROE, EPS/BPS, debt and reserve ratios.
- Ticker-period theme/news evidence: title counts, filtered counts, source-scope confidence, promotion-block flags, raw/news counts.
- Exact daily sidecar joins across the fullrank universe, not only scan-emitted exact-date rows.

## Decision

- status: `no_new_production_candidate`
- best current path: keep the original KOSPI sidecar failure-prior filter as shadow/research only.
- reject for production: KOSDAQ compound filters.
- next bottleneck: complete ticker-period sidecar feature backfill in `swing-main-s280`, then rerun the KOSPI sector-failure and KOSDAQ compound families with stable fullrank coverage.
