# KRX Scanner Direction Audit

- generated_at: 2026-05-12T10:21:53.587609+00:00

## Timeframe Audit
- SWING verdict: daily-primary with intraday refresh, not pure daily-only
- INTRADAY verdict: explicit intraday engine

## KOSPI
- rows: 5705
- missing whale_score: 93.57%
- missing expected_edge_score: 96.62%
- missing expected_return_1d_pct: 96.62%
- missing expected_return_3d_pct: 96.62%
- missing primary_theme: 94.29%
- missing theme_routing_path: 95.30%

- hit10 scan_mode_top: {'SWING': 386, 'INTRADAY': 355}
- hit10 decision_bucket_top: {'picked': 378, 'watchlist': 315, 'exception_leader': 26, 'unknown': 22}
- hit10 selection_lane_top: {'3d': 386, '1d': 355}
- hit10 decision_score mean/median: 96.44 / 101.05

## KOSDAQ
- rows: 14637
- missing whale_score: 93.38%
- missing expected_edge_score: 96.34%
- missing expected_return_1d_pct: 96.34%
- missing expected_return_3d_pct: 96.34%
- missing primary_theme: 95.78%
- missing theme_routing_path: 96.32%

- hit10 scan_mode_top: {'INTRADAY': 767, 'SWING': 328}
- hit10 decision_bucket_top: {'picked': 674, 'watchlist': 300, 'exception_leader': 121}
- hit10 selection_lane_top: {'1d': 767, '3d': 328}
- hit10 decision_score mean/median: 85.6 / 84.9

## Verdicts
- KOSPI 10%+ winners are split between SWING and INTRADAY, so a mixed-lane approach is defensible.
- KOSDAQ 10%+ winners skew toward INTRADAY/1D lane, so daily-primary SWING alone is insufficient for explosive movers.
- Current archive validation is materially weakened by missing factor coverage: whale/theme/expected-return/phase25 fields are absent in more than 90% of rows.
- Current benchmark direction is partially right because lane separation helps, but it is still logically incomplete because the system scores with factors that historical validation barely records.

## Recommended Actions
- P1: Build KR dual-timeframe scanner inputs | Keep SWING on daily structure but attach hourly continuation/breakout confirmation for KR names instead of treating SWING as daily-only.
- P2: Persist factor traces end-to-end | Backfill or newly persist whale_score, theme_routing_path, expected_edge_score, expected_return_1d_pct, expected_return_3d_pct, and phase25 variant so validation can test the logic actually used by ranking.
- P3: Split KR into Core Trend / Explosive Leader / Reject universes | KOSDAQ explosive winners cluster in INTRADAY/1D lane; they should not be forced through the same thresholds as 3D continuation names.
- P4: Retune bucket semantics | Current picked bucket underperforms watchlist in archive-level realized returns, so picked thresholds and promotion rules are not logically aligned with realized edge.
