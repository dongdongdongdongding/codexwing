# Live meta-calibration input audit — 2026-10-07

The 200-row reopening threshold has fired, but its **346 settled rows are not
346 TP5/H10 calibration examples**. This audit separates declared contracts,
creation timestamps and prior independent price evidence before any refit.
It changes no ledger, model, issuance rule or probability display.

`research/audit_live_meta_inputs.py` captures all four original ledger files,
records SHA256 identities, checks that they remain unchanged during the audit,
and writes row-level classifications. Production evidence is in
`runtime_state/audit/live_meta_inputs_20261007/`.

| Old harness input | Rows / finite settled | Contract and timing findings |
|---|---:|---|
| KR swing candidate | 298 / 275 | 31 settled rows on 10 dates declare TP5/H10; all 31 were recorded before the next observed session's open. Only 15 have an input signature; none has a stored model label. Five older settled H5 rows have later recording timestamps. |
| KOSPI intraday | 59 / 59 | 44 declare the TP5/H5 label read by the harness; 15 have insufficient contract metadata. All 59 lack an aware creation timestamp in this ledger. |
| KOSDAQ intraday VWAP | 12 / 12 | Five declare TP5/H3 but the harness reads their shadow TP10/H5 return. Seven declare TP10/H5. Eleven have `generated_at` after `ordered_entry_at`. |
| Retired ensemble | 172 / 112 | Kept separate. Contract and creation-time metadata are absent; these do not add H10 evidence. |

The three live inputs contain 369 rows, 346 finite returns, 55 dates and regimes
NORMAL 113 / RISK_OFF 209 / UNKNOWN 24. The counts reproduce the reopening queue.
They satisfy its collection trigger; they do not establish compatible labels,
pick-time features, calibrated probabilities or an independent holdout.

Late or missing ledger timestamps do **not** prove that an original live signal
never existed. They mean this ledger alone does not establish its pick-time
provenance. Recover original source artifacts before deciding those rows' status.
Likewise, a timely timestamp and input signature are necessary evidence, not a
complete immutable training/feature snapshot. The current producer's source uses
`t5_5` labels; it does not make an old raw score a calibrated H10 probability.

## Reconciliation with the fixed-cohort price audit

The established 64-pick cohort is preserved. Its ledger currently has 42 finite
original-contract returns. The prior independent KIS replay through October 6
has 45 resolved original contracts, including three September 17 KOSPI picks
not yet settled in this ledger: 004170, 004310 and 010580.

Thus available price evidence for **declared H10 KOSPI** is 34 resolved picks on
11 dates, versus the raw ledger's 31 on 10 dates. The separate all-market H10
candidate replay has 45 resolved picks on 14 dates, including KOSDAQ picks
originally issued under H5. These candidate labels cannot silently replace the
original contracts in a pooled meta-calibration dataset.

The prior replay is linked by hash in `report.json`; this audit does not rerun
its price collection or claim a new selection holdout. Its frequency and
promotion failures remain unchanged. Ledger-return settlement and independent
candidate evaluation remain separate evidence.

## Research disposition

No refit was performed. The existing A4 harness targets positive **net returns**,
with 0.30/0.33% costs, while the H10 candidate study targets +5% touch and uses a
different fixed cost contract. Its shuffled date-group CV also does not represent
a forward-only validation. Pooling these inputs now would not answer the user's
H10 probability question.

`swing-main-379m` remains in progress: contract/epoch-specific provenance and
settlement must be resolved before the registered comparison can be interpreted.
This audit does not invent a new 200-row threshold per contract, change the
three-seed/noise comparison, revive a rejected feature family, or authorize
promotion. The separate preregistered prospective H10 studies remain the source
of future independent selection evidence.

Validation: seven focused tests cover conflicting contracts, H3/H5 shadow
misalignment, non-finite returns, holiday-aware observed-session timing, late
creation and distinct contract/settlement/timing counts. Actual full-ledger
capture preserves all source bytes and reproduces the reopening count.

## Historical provenance follow-up

The [VWAP provenance census](KOSDAQ_VWAP_PROVENANCE_2026-10-07.md) reconciles
fourteen scan identities with twelve research rows and thirteen deep reports.
Two June 30 archive-only identities are recorded after the declared entry and
do not add valid forward samples. The twelve matched DB entry timestamps are
nine hours later than their naive Korean ledger bar times; a DB-only comparison
would falsely increase before-entry counts from one to seven across the fourteen
identities. `swing-main-pncm` subsequently corrected those reference times without changing
recommendation timestamps, scores, contracts or outcomes. No original earlier
score/model-input evidence was recovered in the explicitly searched sources,
so this follow-up adds zero verified calibration samples and performs no refit.
