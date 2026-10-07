# Invalid investor-flow feature audit — 2026-10-07

The KIS sidecar exported numeric flow features even when its own `flow_contract.valid`
and coverage were false. The historical feature flattener also accepted these values.
This extended the invalid-score problem already fixed in prefilter ranking by `e00cb2d`.

New sidecars now export missing values for the six flow model features unless the
flow contract is valid. Historical sidecar and prefilter readers mask flow features
when their preserved validity/coverage explicitly says false. They retain raw
diagnostics, source/unit metadata, validity flags and original selection scores.
Absent legacy flags remain unknown; valid flow, including individual zero values,
is preserved. No stored snapshot, model weight, label or issued ledger is rewritten.

## Actual-source verification

Audit directory in production: `runtime_state/audit/flow_freshness_20261007/`.
`replay_and_age_audit.py` preserves comparison modules from commit `ab95e65`.

- Six paired KIS responses for 005930, 035420 and 091990 reproduce the issue.
  Current 005930/035420 have unpublished first-day fields; both 091990 responses
  normalize invalid. All four invalid responses lose only numeric model evidence;
  the two valid completed responses are identical. Diagnostics are identical for all six.
- Sixty preserved historical snapshots: 30 change only the six KIS sidecar flow
  features; 30 remain identical. Source objects remain unchanged.
- Both selected basic admission models have identical predictions on all 60 rows.
  Both selected KIS shadow models change on the 30 affected rows: maximum absolute
  probability-output changes are **14.011999 pp KOSPI** and **4.715655 pp KOSDAQ**.
  Model file hashes match the prior audit. These are input-correction effects,
  not evidence of calibration, better outcomes or a qualified replacement lane.
- 41 focused adapter/prefilter/unit/dataset tests and 72 consumer/training/sidecar
  tests pass (overlapping groups, not 113 distinct tests).

Receipts: `sidecar_live_replay.json`, `historical_feature_replay.json`,
`feature_replay.log`; each original response remains preserved with its hash.

## Observation dates

The pinned 37,641-row owner census was compared with the current observed market
calendar from `~/research_cache/px_long.parquet`, not calendar-day age alone.
13,062 rows have the signal date, 24,576 have the immediately preceding observed
market session, two have unknown source dates, and one is older.

The exception is ID 156969, 091990.KQ, signal 2026-06-04 / source 2024-01-11:
579 observed market dates intervene strictly between those dates. All nine raw
flow fields are zero; the stored whale score is 50 and explicit validity is absent.
The captured full row is `stale_naver_row.json`; the census and calendar identity
are `observed_session_age_census.json`.

This is a current-calendar diagnostic, not point-in-time publication evidence.
No general age gate is deployed by this change. The two original prepared training
caches remain unavailable, so exact historical fitting impact is unresolved.
Broader freshness work remains tracked by `swing-main-lk6b`, and provider/training
lineage by `swing-main-x0fq`. This correction is `swing-main-l391`.
