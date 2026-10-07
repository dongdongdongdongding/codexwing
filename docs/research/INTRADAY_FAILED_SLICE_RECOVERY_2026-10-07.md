# Intraday failed-slice diagnosis and guarded checkpoint recovery

The 17:15–19:15 KST backfill (`20261007T171511552855`) reported ten `ValueError` requests. A fresh, read-only capture of those exact code/date/hour identities found **eight now-valid responses and two reproducible OHLC violations**. The original failing payloads were not retained, so the fresh captures cannot prove all original error causes or provider revisions.

All **440 accepted rows** from the eight valid responses already match the existing cached OHLCV exactly, with **zero new timestamps and zero conflicting values**. No price-bar repair or invented fill is justified. The recoverable difference is stale acquisition checkpoint state.

| Code / date | Accepted failed hours | State after verified recovery |
|---|---|---|
| 025860 / 2026-09-28 | 10:00 | Four requested slices completed |
| 388610 / 2026-09-29 | 15:30 | Four requested slices completed |
| 417180 / 2026-09-29 | 15:30 | Four requested slices completed |
| 419120 / 2026-09-29 | 11:30, 10:00 | Four requested slices completed |
| 443250 / 2026-09-29 | 11:30 | Partial; 15:30 response remains invalid |
| 444530 / 2026-09-29 | 11:30 | Four requested slices completed |
| 446840 / 2026-09-29 | 15:30 | Partial; 11:30 response remains invalid |

`REQUESTED_ALL_SLICES` means the four acquisition requests were accepted, **not** that every trading minute is available. `session_complete` stays null, and session completeness remains `NOT_ESTABLISHED`.

The two malformed responses are query-dependent:

- 443250, 09:04: the 15:30 query returns O/H/L/C `4905/4945/4945/4945`, volume 150, while the 11:30 query returns `4945/4945/4945/4945`, volume 1. Both report cumulative traded amount 735,790. The cache matches the valid latter row exactly.
- 446840, 09:00: the 11:30 query returns `3200/3155/3155/3155`, volume 186, while the 15:30 query returns valid `3200/3200/3155/3155`, volume 186. Both report cumulative traded amount 594,435. The cache matches the valid latter row exactly.

These observations do not justify clamping high/low, discarding validation, certifying the rejected request or claiming the provider's internal cause. Both invalid payloads remain preserved.

`research/recover_intraday_slice_checkpoints.py` provides a guarded, resumable recovery. It requires the exact frozen failed-request identities, provider payload hashes, unchanged parser dependencies, valid OHLCV and complete equality against existing cache rows. It stores immutable before/after state files, verifies backups, preflights all targets, repeats compare-and-set before atomic replacement, and takes the existing operational writer lock. It never writes Parquet price files or changes the original run report. Unexpected cache differences, new timestamps or changed state abort the plan.

Validation: **41 tests passed**, including mismatched cache values, malformed bars, preserved partial status, concurrent changes, whole-plan preflight, interrupted multi-file resume, idempotent reuse and active-writer rejection. A coherent snapshot of all seven actual cache/state pairs was used for an isolated rehearsal: eight hours recovered, seven price files byte-identical, other dates preserved, five complete-request states and two partial states. Actual replay changed none of 23 audit/state files and made zero network calls.

**Live application is pending.** The current natural backfill process PID 11105 (parent 73759) holds the operational writer lock. The recovery command refused mutation; that worker was not restarted or interrupted. After it exits, re-read current state and create a live plan before applying. A changed checkpoint must be reviewed rather than overwritten using the rehearsal plan.

Commands from the deployed checkout:

```bash
python3 research/recover_intraday_slice_checkpoints.py --root /Users/dongdong/Projects/codex_swing/swing-main
python3 research/recover_intraday_slice_checkpoints.py --root /Users/dongdong/Projects/codex_swing/swing-main --apply
```

Evidence is under production `runtime_state/audit/intraday_failed_slices_20261007`: original report, frozen plan, ten provider responses, diagnosis, overlap comparison, and `shadow_recovery/independent_verification.json`. Recovery is tracked in `swing-main-x0iz`; broad daily coverage remains `swing-main-5lj2`. This does not resolve the 615,928 unvisited pairs from the older run, the two invalid requests, US/scanner partials, or any strategy qualification.
