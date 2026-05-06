# PRIORITY_WATCHLIST Gate Policy

Generated from real Supabase `market_scan_results` and local planner handoff
artifacts on 2026-05-06.

## Current Finding

`PRIORITY_WATCHLIST` last appeared on 2026-04-10. From 2026-04-12 through
2026-05-06, production rows contain zero `PRIORITY_WATCHLIST` decisions.

This is not a data-fill problem and must not be patched with dummy picks. Recent
KR candidates with `decision_score >= 80` still exist, but the planner demotes
them through explicit Phase25 and expected-edge guardrails:

- KOSPI SWING: `priority_guard=KOSPI_SWING`
- KOSDAQ SWING: `market_mode_probation=KOSDAQ_SWING`
- Secondary demotions: `expected_edge_watch_guard`, trend guard, clean-prob guard

The local planner handoffs for 2026-05-04 through 2026-05-06 show the same
pattern:

- KOSPI runs: 47-57 OBSERVE decisions, mostly `priority_guard=KOSPI_SWING`
- KOSDAQ runs: 57-69 OBSERVE decisions, mostly `market_mode_probation=KOSDAQ_SWING`

## Why Priority Is Not Forced Back On

Relaxing the gate would create recommendations from weak forward evidence. A
real DB check over the recent high-score demoted population showed that naive
relaxation rules are loss-making:

- `phase25_prob >= 60` and `prob_clean >= 28`: 36 resolved rows, 30.56% win,
  -1.99% average return
- `decision_score >= 95`, `phase25_prob >= 45`, `prob_clean >= 32`,
  `expected_return_3d_pct >= 1.0`: 7 resolved rows, 14.29% win,
  -3.76% average return
- `decision_score >= 86`, `phase25_prob >= 70`, `prob_clean >= 28`,
  `expected_return_3d_pct >= 0.5`: 16 resolved rows, 43.75% win,
  -1.26% average return

Therefore the correct policy is to keep Stream A dormant when no candidate
passes the validated gate. A zero-count `PRIORITY_WATCHLIST` day is allowed only
when the report records the gate cause and candidate performance evidence.

## Monitoring Requirements

- `multi_agent/tools/report_priority_watchlist_gap.py` is the source report for
  the zero-priority diagnosis.
- The daily picked-realized rollup must use the row's actual label horizon:
  KOSDAQ SWING uses `return_5d_pct`, KOSPI SWING uses `return_3d_pct`, and
  intraday uses `return_1d_pct` when available.
- Do not promote OBSERVE/WATCHLIST rows to `PRIORITY_WATCHLIST` unless a new
  validation report shows positive realized performance for the exact proposed
  rule.

## 2026-05-06 Update — Gate-Cause Stratified Validation (swing-main-0nr)

After swing-main-h4x persisted `rationale` and `theme_risk` into
`market_scan_results`, we re-ran the validation per gate cause instead of
treating "the gate" as one knob. This invalidates the earlier conclusion that
*all* relaxation is loss-making — that result came from mixing causes.

Forward 3d/5d performance over 30 days, gated rows in
`OBSERVE/AVOID/WATCHLIST/WATCHLIST_ONLY`:

| Gate cause | n_resolved_3d | win_3d | avg_3d | win_5d | avg_5d |
| --- | ---: | ---: | ---: | ---: | ---: |
| KOSPI_SWING_PRIORITY_GUARD (KOSPI SWING) | 1,309 | **69.4%** | 3.83% | **73.8%** | 7.72% |
| EXPECTED_EDGE_WATCH_GUARD (KOSPI SWING combo) | 1,228 | **69.4%** | 3.92% | **74.6%** | 7.92% |
| EXPECTED_EDGE_WATCH_GUARD alone (KOSPI SWING) | 345 | 66.7% | 3.61% | **75.4%** | 7.53% |
| KOSDAQ_SWING_PROBATION (KOSDAQ SWING) | 744 | 43.7% | 0.52% | 53.6% | 3.60% |
| KOSDAQ_INTRADAY_WATCH_GUARD | 23 | 34.8% | -3.88% | 30.4% | -5.17% |
| KOSDAQ_SWING_TREND_GUARD | 22 | 31.8% | -0.59% | — | — |

Same window, the rows that *did* pass to `PRIORITY_WATCHLIST` (baseline):

| market | scan_mode | n_picked | win_3d | avg_3d | win_5d | avg_5d |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| KOSPI INTRADAY | | 360 | 76.8% | 7.19% | 78.8% | 10.97% |
| KOSDAQ INTRADAY | | 740 | 60.9% | 3.07% | 69.6% | 10.03% |
| KOSPI SWING | | 29 | 62.1% | 2.29% | 72.4% | 5.32% |
| KOSDAQ SWING | | 18 | 0.0% | -1.64% | 100.0% | 7.73% |

Two observations are decisive:

1. KOSPI SWING is the stream that has been turned off — only 29 picks in
   30 days. The rows blocked under `KOSPI_SWING_PRIORITY_GUARD` and
   `EXPECTED_EDGE_WATCH_GUARD` outperform that baseline by ~7pp on win-rate
   and ~1.5pp on average return. The KOSPI SWING hard demote is inverted.
2. KOSDAQ SWING and KOSDAQ INTRADAY guards are correctly blocking loss
   candidates. Their gated populations sit below their respective
   baselines.

### Policy change applied

- `KOSPI_SWING_PRIORITY_GUARD`: hard demote → soft note. The marker is still
  emitted in `theme_risk` as `KOSPI_SWING_PRIORITY_GUARD_SOFT` so audits keep
  the trace, but the candidate stays at its original decision rank.
- `EXPECTED_EDGE_WATCH_GUARD`: KOSPI SWING only → soft note
  (`EXPECTED_EDGE_WATCH_GUARD_SOFT`). KOSPI INTRADAY, KOSDAQ INTRADAY, and
  KOSDAQ SWING keep the original demote.
- All other guards (`KOSDAQ_SWING_PROBATION`, `KOSDAQ_SWING_TREND_GUARD`,
  `KOSDAQ_SWING_CLEAN_PROB_GUARD`, `KOSDAQ_INTRADAY_WATCH_GUARD`) keep
  hard demote.

Both relaxations gate on environment toggles
(`AG_KOSPI_SWING_PRIORITY_GUARD_RELAX`, `AG_EXPECTED_EDGE_WATCH_GUARD_RELAX`,
default `1` = relax). Setting either to `0` restores the previous behavior
without redeployment.

### Acceptance / monitoring

- KOSPI SWING `PRIORITY_WATCHLIST` count over the 30-day rolling window must
  rise from ~29 toward ≥100 within seven trading days of the change.
- 7-day forward holdout must keep `win_3d ≥ 65%` and `avg_3d ≥ 3.5%` on
  KOSPI SWING `PRIORITY_WATCHLIST` rows. If either falls, set the
  corresponding env toggle to `0` and reopen the analysis.
- The 30-day diagnostic SQL above (gate-cause stratified) must be re-run
  weekly to catch regime shift in the gated population. If a gated cause
  re-inverts (gated win below picked baseline), the soft demote should be
  promoted back to hard.

