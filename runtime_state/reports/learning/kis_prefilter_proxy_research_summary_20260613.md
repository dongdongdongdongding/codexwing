# KIS Prefilter Proxy Research Summary

- generated_at: `2026-06-12T16:53:18Z`
- dummy_data_used: `false`
- objective: `historical KIS daily OHLCV 기반 prefilter/rank feature parity 복구가 touch5_dd10 성과를 개선하는지 검증`

## Data Result

- KOSPI prepared rows/days: `100260` / `106`, failed tickers: `3`
- KOSDAQ prepared rows/days: `190182` / `106`, failed tickers: `25`
- KIS feature coverage: both markets `97/153` nonempty
- prefilter feature coverage: both markets `31/49` nonempty
- prefilter positive rows: KOSPI `8479`, KOSDAQ `8480`
- source: `real KIS daily OHLCV cache`

## Model Result

- fast walk-forward report: `results embedded in this summary`
- KOSPI best: `lightgbm_ranker / kis_failure_prior_category / top1`, n `36`, active_days `36`, hit5_dd10 `38.8889`, avg_ordered_exit `-2.52715`, min_low `-21.190341`, gate `blocked`
- KOSDAQ best: `lightgbm_ranker / kis_failure_prior_numeric / top1`, n `36`, active_days `36`, hit5_dd10 `47.2222`, avg_ordered_exit `-0.888756`, min_low `-36.419012`, gate `shadow_risk_review`
- deterministic prefilter top1 failed: KOSPI hit5_dd10 `36.8932`, KOSDAQ hit5_dd10 `40.7767`, both with tail breach above `52%`
- best univariate segment observed: KOSPI `kis_prefilter_rank_volume` 1..5, n `515`, hit5_dd10 `52.8155`, avg5 `3.006112`, tail breach `30.8738`, min_low `-45.922318`

## Decision

Feature parity improved, but the model is not promotable. The daily OHLCV-derived historical prefilter proxy is useful as a candidate-pool feature, not as a standalone admission model. Production/shadow promotion remains blocked until true operational KIS sidecar evidence is persisted at scan time and tail-risk rejection/no-trade gates improve materially.
