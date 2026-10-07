# KOSDAQ VWAP ledger rerun repair — 2026-10-07

`record_picks` removed existing rows with matching date/ticker/candidate identity
and replaced them with the latest scores, timestamps and contracts. The incoming
row also reset several outcome fields. This destroys the evidence needed to
interpret a forward ledger or reopen meta-calibration research.

The producer now preserves the first recorded selections for each candidate/day.
Reruns cannot replace those rows or append different tickers to exceed that day's
selection. New days respect the configured top-N limit and deduplicate identities.
Report and routing paths read the recorded picks, while new scores remain separate
diagnostics. Archive and deep-report writes use each pick's original creation
timestamp and recorded rank. Contract TP/horizon values continue to come from the
recorded pick.

Recording and settlement share a file lock; ledger replacement is atomic.
Malformed rows fail visibly instead of being silently dropped on rewrite.
The scope is recorded selections: this does not create immutable abstention
snapshots or repair missing historical pick-time evidence.

## Evidence

Production audit: `runtime_state/audit/kosdaq_vwap_freeze_20261007/`.
`source.jsonl` preserves all 12 original rows. A replay on copies changes every
row's proposed score and contract and supplies a later creation time. The prior
producer changes all 12 rows; the corrected producer records zero new rows and
preserves the copy byte-for-byte. The actual production ledger remains unchanged.
`replay.json` records original hashes and each changed field under the prior code.
After deployment of `28e441e`, importing the production module and repeating the
copy-only check again records zero rows and preserves both copy and source bytes.
`deployed_readback.json` records the module path, commit and original SHA256.

Fifteen tests pass across the freeze, VWAP-guard and consumer contract suites.
They cover rescore preservation, changed-ticker quota bypass, duplicates, malformed
input, failed atomic replacement, two concurrent processes, report/routing parity,
original per-pick timestamps/ranks and TP/horizon display wiring.

The overwrite mechanism explains how late timestamps can arise, but this replay
does not prove which historical rows were overwritten or reconstruct their lost
values. No historical score, contract, timestamp or settled result was guessed.
No production scorer or message route was executed for this validation.
`swing-main-g37h` is closed after deployed verification; `swing-main-379m` retains the unresolved
historical provenance/contract audit. No new edge or calibrated probability is
claimed.
