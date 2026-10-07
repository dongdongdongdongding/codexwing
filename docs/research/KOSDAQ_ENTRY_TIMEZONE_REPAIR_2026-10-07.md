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

The actual dry-run plans fourteen corrections; production application and export
verification will be recorded below. Evidence:
`runtime_state/audit/kosdaq_entry_timezone_20261007/`.

This correction does not add an eligible forward observation or qualify a new
H10 lane. Missing original scoring inputs and the two missing research-ledger
identities remain unresolved in the parent provenance/meta audit.
