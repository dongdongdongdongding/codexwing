# Mandatory current swing evidence at publication consumers

Issue: `swing-main-o620`.

The consumer previously entered current-configuration checks only when the gate
report carried `epoch_scope_required`. A fresh legacy pooled healthy verdict
without that field could restore sizing and actionable cards. The web EV helper
had the same independent fallback. Current production reports already blocked
publication; this repair does not claim an observed unauthorized purchase.

`stream_exclusion.current_epoch_for_lane` now requires KR/US swing current evidence
in consumer code. Missing/false report flags cannot opt out. It verifies the
market and current configuration scope, including H and TP, and rejects malformed
or absent epochs. Opening requires explicit boolean `publication_block=false`
and `confirm_qualified=true`, followed by the existing verdict whitelist. The
current evidence producers still emit blocked, unqualified observations.

KR diagnostics now scope by issued TP as well as H/gate/q/top-k. Historical rows
with another or missing TP do not contribute to this exact contract. A stale KR
report lacking TP in its scope is rejected until the report is regenerated.

The web EV helper uses the same selector and status. For a hypothetical qualified
current epoch it applies the existing EV/win floors to that epoch's numbers; it
never borrows pooled EV. Render-time interpretation rechecks remain in place.
Tests cover omitted/false flags, malformed containers, cross-market and H/TP/
gate scope mismatch, nonboolean qualification values, high raw model scores,
stored-card rechecks, and the generic gate/retirement/operator-floor contracts.

This is report-contract validation, not authenticated scientific evidence. It
does not implement or approve a new research epoch, pin arbitrary model/source
proofs, certify per-pick calibration, or replace the low-liquidity lane. The
legacy producer, six frozen candidate models, historical capture dependencies,
issued picks, and research outcomes are unchanged. Existing explicit exclusion
rollback configuration is unchanged.

Operational evidence is retained under
`runtime_state/audit/required_current_epoch_20261007`. `gate_before.json` preserves
the exact prior report; `before_replay.json` compares old/new code against it.
The actual prior report had pooled DEGRADE and current publication blocks, so
omitting its flag did not itself open a live lane. The reproduced bypass uses
hypothetical healthy pooled evidence in tests, not fabricated live performance.
