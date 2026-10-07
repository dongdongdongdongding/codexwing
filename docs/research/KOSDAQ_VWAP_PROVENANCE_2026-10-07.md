# KOSDAQ VWAP historical provenance census

Issue `swing-main-emru`, following the input audit `swing-main-379m` and
first-record preservation fix `swing-main-g37h`.

A complete read-only query of the exact `KQ-ITD-3D-T5-` run prefix finds fourteen
scan records and thirteen deep reports. The current research ledger has twelve
rows. The exported archive contains the same fourteen scan identities and
matches all 84 checked timestamp, score and contract fields exactly.

| Source difference | Observed identities |
|---|---|
| Scan/deep records absent from research ledger | June 30: 036930.KQ and 080220.KQ |
| Research/scan record absent from deep reports | June 26: 144960.KQ |

The two archive-only rows declare TP5/H3 and carry scores of 1.0 (100 in the
scan schema). Their reports were generated at 21:36 KST, after their declared
15:00 entry. They are additional recorded identities, not additional executable
forward samples. Their original ledger fields and disappearance mechanism are
not reconstructed. The missing deep report is not fabricated from today's schema.

## Nine-hour storage mismatch

All twelve matched ledger entries contain naive local Korean bar timestamps,
usually 15:00 and once 14:59. Their DB `ordered_entry_at` fields retain that wall
clock with a UTC offset, shifting the instant nine hours later. The two
archive-only rows independently declare `entry_time_kst=15:00` in their stored
feature metadata and also store 15:00 UTC. For these two, only the declared
schedule is available; an original observed entry bar is not recovered.

The source path is visible in code: `compute_pre_entry_features` emits the local
index with `isoformat()`, `live_pick_payload` copies it to `ordered_entry_at`, and
`db_schema` passes it through unchanged. This census identifies that mismatch;
`swing-main-pncm` tracks serialization and guarded historical normalization.
This read-only audit did not change the field. The subsequent
[KST serialization repair](KOSDAQ_ENTRY_TIMEZONE_REPAIR_2026-10-07.md) corrects
the fourteen stored references and prevents recurrence on the known producer path.

Comparing recommendation time against the stored DB instant would mark **7/14**
records as before entry. Comparing against the documented Korean entry clock
leaves **1/14**. The twelve matched scan rows exactly reproduce the ledger's
recording timestamps, scores and contracts; all thirteen deep rows reproduce
the scan timestamp and score. Those are matching stored copies, not independent
proof of an earlier recommendation. The one early timestamp also does not prove
that the full scoring inputs were available at that time.

## Recovery search and its limits

The search captures all 272 local JSON files in `runtime_state/reports/ops/` and
checks their stored command stdout/stderr tails. None contains the target run
prefix or candidate identifier. This does not establish that no earlier full
process log ever existed.

Three matching precision-cache JSON files are retained. Their model dictionaries
contain only `in_a` and `in_b`, not an original VWAP score/contract snapshot.
Their recorded cache times follow the relevant 15:00 entry dates; these cache
timestamps are naive and are not upgraded to independent issuance proof.

All reachable git history for the latest VWAP report contains one snapshot,
commit `c4c27f45925edb7030f9136c223f5c1f9ad774c4`, generated August 14 with zero
picks. There is no reachable git history for the research ledger path. Negative
recovery claims are limited to these locations and the captured DB/export rows.

**No additional original pre-entry pick or immutable model-input snapshot was
recovered.** No ledger, DB, model, contract, outcome or live report is changed.
The audit does not supply H10 labels or a new 70% probability estimate. Registered
meta-calibration still needs compatible contracts, immutable pick-time inputs,
independent settlement and forward evaluation; the future H10 studies remain
separate.

## Reproduction and validation

```bash
python3 research/audit_kosdaq_vwap_provenance.py \
  --root /Users/dongdong/Projects/codex_swing/swing-main \
  --audit /path/to/new-capture --capture-db
```

The explicit flag makes only database reads; without it, the tool uses existing
captured JSON. Existing evidence is never overwritten with different bytes.
Production evidence is in
`runtime_state/audit/kosdaq_vwap_provenance_20261007/full_capture/`:
full scan/deep captures, research ledger copy, selected archive rows, 272 ops
snapshots and hash census, three precision snapshots, the git report and
`report.json`. Initial and repeated complete DB captures match exactly.

Thirteen provenance and prior meta-input tests pass. They cover the false
UTC-before-entry classification, an explicitly declared schedule without an
original ledger row, missing/naive creation timestamps, preservation of aware
instants, differing scores/contracts, duplicate or unrelated identities and
immutable capture failures. An independent UTC-offset calculation and source
hash verification pass 380 checks; live ledger and archive hashes are unchanged.
