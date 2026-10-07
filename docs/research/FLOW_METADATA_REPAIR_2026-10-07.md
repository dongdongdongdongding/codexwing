# Flow snapshot metadata repair — full application verified

All 37,639 planned rows passed application and independent full-row verification
on October 7 at 13:17 KST. Both processes terminated successfully. The resumed
application found 4,900 already-correct rows and applied the remaining 32,739.
Unresolved IDs 151599/151600 remain byte-equivalent as decoded full rows.

`swing-main-vva4` remains in progress only for the final same-command no-change
replay, started after both processes terminated. Live counters, rather than this
dated note, determine that replay's completion.

Plan SHA-256:
`70fa2839fa1a6e853a6a2c98c5c33a7ffd74736fa9607cc5cee7e2e21df22ef5`.
The [provenance audit](FLOW_PROVIDER_LINEAGE_2026-10-07.md) reconstructed three
fields from preserved owners whose selected numeric values match. The repair
assigns only `flow_source`, `flow_unit`, and `flow_asof`.

## Safeguards and actual recovery

`repair_flow_snapshot_metadata.py` rechecks ID/run/ticker, nine investor values,
projected owner metadata and the canonical result. Each batch saves and hashes
a full-row backup before writing. Typed full-row SQL compare-and-swap rejects
any intervening change, including labels or timestamps. No schema changes are
needed; a read-only check found no user triggers on this table. Post-write reads
require exact equality with the full backup except the three planned fields.
Lost responses are reconciled by reading; restarts recognize already-correct
rows without duplicate mutations. Attempt receipts are retained separately.

The first 100-row pilot passed, including independent PostgREST readback
(separate from the Management API write/readback). The first full pass verified
4,800 repaired rows, then stopped: the next request was 3,588,689 bytes and the
API returned HTTP 413. Readback showed its 100 rows still unchanged.

The transport now plans bounded statements before mutating, each at most
1,000,000 bytes. That failed batch was applied as four statements, largest
994,533 bytes, and all 100 rows passed full readback. The full run resumed
against the same immutable backups and plan. The rejected pass was confirmed
terminal (exit 2); no writer was restarted because of an observation timeout.

33 tests pass: full-row conflicts, value/owner drift, lost responses, crash
after commit, backup integrity, replay, field allowlisting, bounded requests,
and oversized-single-row refusal before any mutation. Commits `fc80a7a`,
`c84810e`, `81ebb47` are pushed to both branches.

## Live evidence and remaining verification

Production audit root: `runtime_state/audit/flow_provider_lineage_20261007/`.

- `metadata_repair/completed_application.json`: preserved full application,
  independent verification and unresolved-row results before replay.
- `metadata_repair/latest.json`: current replay counters and completion flag.
- `metadata_repair/no_change_replay.log`: final idempotence run, still pending.
- `metadata_repair/independent_rest/latest.json`: independent verified count.
- `metadata_repair/batch_*/before.json`, `before.sha256`, `events/`: originals
  and attempt receipts. The initial pilot also has `pilot100.json`.
- `metadata_repair/first_pass_result.json`, `recovered_413_batch.json`: failed
  pass and verified recovery. Logs retain both passes.
- `verify_metadata_rest.py`: full-row verifier; at completion it also checks
  that unresolved IDs 151599/151600 are unchanged.
- `live_watch.json`: process and service observations.

Both original counters reached 37,639 with no unresolved repair errors and
untouched unresolved rows. Closure still requires a completed no-change replay.
This restores provenance, not
source freshness, uniform feature dimensions, training reproducibility or an edge.

## Related live-input correction

`swing-main-lk6b` remains open. Actual current/completed KIS response pairs for
005930 and 035420 show empty current-day flow; the adapter marks it invalid but
the prefilter still used its diagnostic whale score. Commit `e00cb2d` requires
`valid=True` for prefilter scoring and keeps invalid scores only in diagnostics.
35 relevant tests pass. Captured-response replay removes spurious -0.9 and -5.4
contributions; valid completed-date contributions remain -22.5. No candidate
rescan, model replacement or outcome rewrite occurred.

For 091990 the current endpoint reports January 11, 2024, while the completed
endpoint supplies recent dates with zero volume and flow. Both normalize to
invalid. The historical 875-day-old Naver row also has nine zero flow values.
Broader source-date validation and training impact remain unproven. Evidence:
`runtime_state/audit/flow_freshness_20261007/`, including six timestamped response
captures and `prefilter_invalid_flow_replay.json`.
