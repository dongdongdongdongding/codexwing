# KOSDAQ entry-reference timezone repair

Issue `swing-main-pncm`; evidence census `swing-main-emru`.

Korean minute-bar timestamps were serialized without an offset and stored as UTC
in `market_scan_results.ordered_entry_at`. This moved a 15:00 Korean entry
reference to midnight Korea time, creating six false before-entry classifications
in the fourteen captured recommendations. It is an entry-reference metadata
error, not a newly established fill or a change to original recommendation time.

`kst_entry_timestamp` now attaches `Asia/Seoul` to known naive Korean bar times.
Already aware instants retain their offset and instant. `live_pick_payload`
uses it for new rows; routing uses the same conversion for previously frozen
naive ledger rows. The original ledger, recording timestamps, scores, contracts,
returns and ranks are preserved. Internal feature arithmetic is unchanged.

`research/repair_kosdaq_entry_timezone.py` derives a fixed plan from the prior
hash-checked, complete database and ledger captures. Twelve rows have their
original ledger bar time; two June 30 archive-only rows explicitly declare
`entry_time_kst=15:00` and are identified individually. The latter repairs only
the documented schedule representation, without reconstructing missing picks.
All fourteen expected differences are exactly nine hours; wrong identity,
contract, score, recording time, source or unexpected entry differences fail.

The tool defaults to dry-run. Before application it saves complete captured and
current rows and validates every field against the original or already-applied
state. A typed full-row SQL compare-and-swap updates only `ordered_entry_at`;
other fields, including performance timestamps, are outside the patch. Full
PostgREST readback must equal the exact planned row. A repeat accepts already
correct rows without writing. A concurrent change fails rather than overwriting.

The actual dry-run planned fourteen corrections. Production verification follows. Evidence:
`runtime_state/audit/kosdaq_entry_timezone_20261007/`.

This correction does not add an eligible forward observation or qualify a new
H10 lane. Missing original scoring inputs and the two missing research-ledger
identities remain unresolved in the parent provenance/meta audit.


## Applied verification

`c86e663` was deployed and pushed to both branches before application. The exact
fourteen-row plan changed only `ordered_entry_at`; all other fields in all
fourteen full PostgREST readbacks equal their captured originals. The complete
current-row backup SHA256 is
`e07fe29920632c498f37268232ddc4eed17ba8f18b68d29ade26ef8f90976709`.
Repeating the repair finds fourteen already-correct rows and performs zero writes.
The original research ledger remains byte-identical.

The complete CSV and JSON exports each retain 64,603 rows and the same identity
set. All 64,586 rows outside this repair and three previously completed H30
updates are exactly unchanged across every field. The fourteen target rows
change only the entry time. The other three changes, IDs 2161/2162/2168, are
`return_30d_pct` and `performance_updated_at` from the earlier scanner backfill
pilot; their values match its independent audit and a fresh DB readback.
No additional export difference was found. An initial expectation based on an
older 64,250-row report was not the current export baseline; the preserved
before-export files establish the correct 64,603-row comparison.

Thirty-nine focused tests pass. A deployed-module replay of all twelve original
ledger picks, with external writes stubbed, verifies KST serialization while
preserving their recommendation timestamps, scores and contracts. It does not
call the scorer or send new recommendations. Health, picks, ops-status and a
targeted archive API call return HTTP 200. The archive endpoint does not expose
`ordered_entry_at`, so no claim is made that the UI displays this time field.

Evidence includes `plan.json`, `apply_before.json`, `after.json`, application and
zero-write replay receipts, verified before-export hardlinks, `export_delta.json`,
`prior_H30_updates_current.json`, streaming CSV/JSON `verify.py`,
`verification.json`, `api_after.json` and `deployed_route_check.json`.
The apply/export and verification processes completed. The independent daily
collector remained live and was not restarted; overall batch success is still
unverified.
