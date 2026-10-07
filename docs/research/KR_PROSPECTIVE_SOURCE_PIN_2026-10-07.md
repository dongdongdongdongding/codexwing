# Prospective H10 producer integrity repair — 2026-10-07

Beads: `swing-main-cyh9` (discovered from `swing-main-q6va`).

At 13:54 KST, before either study's first observation, the deployed swing
producer no longer matched either preregistered SHA256. Commit `7a81448` moved
three time constants into a shared import. Its behavior was unchanged, but the
prospective collector intentionally checks the entire producer file. The next
eligible report would therefore fail with `producer_changed_since_preregistration`.
The previous calendar-only tests missed this integration constraint.

The producer is restored byte-for-byte to the source present at registration
(`a7ac9c6`):

- Before: `b4d07a684b9cecc000a55f650da6cc5efe91ed58d1d21c8cf4dda2d5dec81e16`.
- Restored: `bc452be9d3a4d7786f197035c2af6eaf6d73acf5cb17a4c8aacf7b1496c8c6f8`.

Neither preregistration nor the collector's hash check changes. Both studies
still have zero frozen snapshots. The status consumer retains its observed-date
readiness fix; boundary tests compare it with the actual original producer.
The duplicated swing time constants are deliberate while this source is pinned.

## Verification

`python3 -m pytest tests/test_kr_touch10_prospective.py -k deployed_producer -q`
first reproduced two failures, one for each registered study. After restoring
the constants, the prospective, producer-calendar, pipeline-status, swing
unconfirmed-session, KOSDAQ ledger-freeze and lane-map suites pass **48 tests**.
`git diff --check` passes.

Production audit `runtime_state/audit/prospective_source_pin_20261007/` contains
both source versions and `source_check.json`: exact registration-time bytes,
both unchanged preregistration hashes, and zero existing snapshots. This is a
source-integrity repair, not an H10 outcome or successful future capture. The
fixed 60/120-session windows and promotion restrictions remain in effect.
