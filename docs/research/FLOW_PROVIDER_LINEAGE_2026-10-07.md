# Flow feature provenance audit — 2026-10-07

`swing-main-x0fq` remains in progress: current stored rows can be audited, but
the exact historical training caches are missing. No historical model effect
or replacement qualification is established.

## Observed scope

Read-only, ID-paginated Supabase queries captured every existing
`scan_universe_snapshots` row through pinned ID 456400: 264,544 rows, all KR.
Independent projected-owner queries captured all 37,641 rows with at least one
of the nine investor-value fields present. All chunks retain hashes and ID
bounds. This was not a transactionally isolated snapshot; it observes current
database contents, not the historical training dataset.

Every flow row's outer metadata says `scan_universe_snapshot` / `source_units`.
For 37,639 rows, all selected non-null numeric values match the metadata owner
inside the preserved `feature_snapshot` exactly. Resolved provenance:

| Scan mode | Provider | Unit | Rows |
|---|---|---|---:|
| SWING | Naver | shares | 24,853 |
| SWING | unresolved | source_units | 2 |
| INTRADAY | KIS | shares | 6,547 |
| INTRADAY | KIS | million KRW | 6,239 |

The two unresolved rows are IDs 151599 and 151600 (`RUN-C3BF4B38`, 005930 and
035420, June 4). Their owner metadata is absent. Do not infer units from zero
values or attach unrelated sidecar units.

Within January 1–June 10 SWING, the current table contains 166,318 rows, of which
15,770 have flow: 15,768 Naver shares and the two unresolved rows. September
1–October 7 SWING has 9,654 rows and 915 flow rows, all Naver shares. No pykrx
amount rows were observed in this captured scope. This does **not** prove that
every earlier training input was Naver or that a model never encounters a
different provider at inference.

## Date loss and dimension changes

All 37,639 resolved date strings differ from the outer field: 13,069 only in
format, and 24,570 in calendar date. Calendar differences are 1 day (16,792),
2 (3,591), 3 (3,367), 4 (819), and 875 (1). ID 156969 / `RUN-2BA12563` / 091990.KQ
is a June 4, 2026 signal whose Naver owner says January 11, 2024. Restoring that
date reveals stale input; it does not make the value current or valid.

The parser chooses investor amounts when the latest API row has amount fields,
otherwise quantities. KIS current-date fallback can therefore use shares while
completed-date amount responses use million KRW. Shares cannot be repaired by a
constant money multiplier. No raw input was rescaled during this audit.

## Repair deployed with this investigation

`flow_metadata_for_values` preserves source, canonical unit, source observation
date and warnings only when the owner contains every selected flow value and
all agree. It checks the base row, its direct flow object, and preserved base
snapshot; it does not borrow a KIS sidecar's metadata for unrelated values.
Unverified provenance is explicit, and an unknown source date is not replaced
by the signal date.

Admission feature extraction and both snapshot/return backfills share that
helper. Return backfill now fetches the original snapshot and no longer
overwrites its source date with the label base date. Training fetches unit and
source date alongside the existing source field; these are metadata, not new
model features. Existing historical DB rows are not bulk rewritten by this
change. `swing-main-vva4` owns the concrete compare-and-swap repair plan.

93 relevant tests passed. Actual preserved source rows (30 early, 30 recent)
produce exactly the same numeric features and 240 identical predictions across
the four selected admission/shadow bundles. Model hashes are unchanged. This is
a compatibility check, not a profitability or out-of-sample performance test.

## Limits and evidence

The two prepared caches referenced by the June shadow deployment reports were
not found in production, the current workspace, research cache or the configured
ORICO archive searched here. Exact training-row reconstruction remains open.
The four inspected bundles omit unit features. Deep-report and Discord
rendering call admission scoring, whereas the separate KR swing issuing model
uses price/volume features and no investor-value columns. Do not confuse these
model paths or attribute the issuing lane's performance to this repair.

Audit root in production: `runtime_state/audit/flow_provider_lineage_20261007/`.

- `collect_slim.py`, `collect_owners.py` and logs: executed read-only collectors.
- `census_manifest.json`, `owners_manifest.json`: ranges and chunk hashes.
- `resolved_flow_owners.json`, `unit_census.json`, `audit_summary.json`: findings.
- `metadata_repair_plan.json`: 37,639 proposed three-field changes with old
  metadata, selected numeric values and owner evidence; **plan only, no DB writes**.
- `early_flow_details.json`, `recent_flow_details.json`, `model_invariance.json`:
  actual-row compatibility evidence.

The original source fields, prices, labels, models and issued ledgers remain
unchanged. No H10/+5%/70%/2–3 firing-date replacement passed from this work.
