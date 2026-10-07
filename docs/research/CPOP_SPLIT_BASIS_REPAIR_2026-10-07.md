# CPOP partial split-basis repair

Issue: `swing-main-xj0v`; source audit `swing-main-dr43`.

CPOP's official reverse-split chain is 10 on 2023-10-27, 10 on 2026-07-13,
and 15 on 2026-09-14. Primary notices are Nasdaq
[ECA2023-614](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-614),
[ECA2026-484](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-484) and
[ECA2026-658](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-658).
HTTP bodies and hashes are retained with the complete KIS MODP0/MODP1 history.
No model scores, returns or strategy outcomes determine this source repair.

Of 1,306 pre-event observations, 1,299 satisfy the existing price tolerance
(0.5% plus 0.0001) and volume tolerance (5% plus one adjusted share). Four were
already adjusted and 1,295 need the latest factor: price times 15, volume divided
by 15, dollar volume recomputed. KIS volume is nominal in both modes and is
compared after division by the full official cumulative factor.

Seven observations remain exactly original and quarantined:

| Reason | Dates |
|---|---|
| Unexplained OHLC units under fixed tolerance | 2026-06-29, 2026-07-01, 2026-07-02, 2026-07-09 |
| Unexplained adjusted volume | 2024-12-26, 2025-02-26, 2026-09-11 |

The integrity-pinned reference `modules/data/cpop_split_basis_20261007.json`
has SHA256 `b5dfbe3fc72ffd81a34858c91e6d96fae97184d976edfcbe0ebb1d539d9e8d85`.
All nine numeric fields must match the original row before normalization and
the supported row before quarantine release. Unknown revisions require a new
audit. Deferred dates retain their original nine fields and explicit reasons.
The shared Yahoo extraction, exact-match guard and feature-cache fingerprint
apply to CPOP just as to the previous verified exceptions.

`build_cpop_split_reference_20261007.py` reconstructs the evidence from the
original hash-pinned baseline and refuses a changed live source; it is a
pre-application evidence builder, not a live refresh command. The generic
`repair_vwav_split_basis_20261007.py --symbol CPOP` stages or applies under the
US writer lock with complete source backup and compare-and-swap. Repeated
repair is supported after application.

Validation before application: 127 tests across split, lineage, refresh,
cache, source-audit and lane-map suites; 20,756 independent Decimal source
checks. A new Yahoo full-history observation returned 1,323 dates; all 1,299
supported pre-event dates matched exactly after extraction, with only the
same seven unsupported dates. No tolerance was relaxed.

Evidence lives in production `runtime_state/audit/cpop_basis_repair_20261007/`.
The seven deferred rows join the previous forty in `swing-main-kc3g`; broader
source gaps remain `swing-main-d3f5`. This is verification of observed split
units, not exact exchange prices, complete source coverage, point-in-time
listing membership, model admission, or H10 strategy qualification.

## Production verification

Code `6716f32` was pushed to both branches before application. Under the US
writer lock, the current 14:42 panel received a hash-verified hardlink backup,
3,976 protected paths were hashed, and the full CPOP source backup was verified
before writing. The new raw SHA256 is
`fc3d1bb98548bde260f205910a94733cb1bc47aa06ab43a383ae4b3f6ee63578`.
Exactly 1,295 rows changed. All 28 other source rows, including seven deferred
and all post-event rows, are unchanged.

New panel: `daily_features_20180101_20261007_20261007_152154041532.parquet`.
SHA256: `e9feb8004c7b70cb9d50ec3c36be7985d3b9fa4f4d772d63feb5f6ef22a4cd57`.
It retains 5,605,406 rows. All 5,604,083 rows outside CPOP match the previous
panel exactly across every column. All other raw, universe, listing metadata,
old panel and issued-ledger hashes are unchanged.

Independent Decimal feature and forward-label verification passes 28,980
checks, including null labels whenever the future window crosses a retained
invalid date. CPOP invalid rows fall from 1,306 to seven; feature-ready rows
rise from zero to 974, and rows with current model features plus H20 target
available rise from zero to 734. These describe availability, not actual
training, admission, or a result under the requested H10 contract.

The current candidate pool remains exactly 322 with identical admission
history and percentiles. No model was refitted and no issued contract changed.
Application and independent full-panel verification terminated successfully.

Repeated repair writes zero raw files. Repeated full feature construction
reuses the verified panel with zero new panels. Health, picks, overview and
ops-status endpoints return HTTP 200. Replay and API checks terminated
successfully. At 15:26 KST, the separate daily worker 97991/97996 and intraday
collector 10244 remain live; overall daily completion is still unverified.
