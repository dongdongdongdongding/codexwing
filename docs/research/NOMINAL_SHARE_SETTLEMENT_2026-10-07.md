# Nominal share settlement for a corrected research epoch

Issue `swing-main-ia04`; parent `swing-main-jm3e`.

`research/nominal_share_settlement.py` supplies a separate, pure settlement
primitive. The frozen low-liquidity study, canonical legacy settlement function,
models, inputs and live producers are unchanged. This contract has not been
adopted into a new study or approved for publication. No Q3 strategy outcomes
were calculated.

The new contract buys a positive integer quantity at the next market-session
open. Entry counts toward the H10 window. It tracks nominal cash invested,
tradeable shares and pending share entitlements. TP means the modeled sale of
**all** entitled shares produces at least 105% of initial cash. It uses the daily
high/open fill approximation; it does not certify actual queue fills, tick-size
rounding, market capacity or realized broker execution. Those remain required
before research results can support replacement. The output always states
`execution_verified=false`, `source_certified=false`, `publication_allowed=false`.

Share conversion uses an exact rational new/old share ratio; a bonus uses an
exact additional-shares/held-share ratio. Quote-reference adjustment factors
never imply shareholder entitlements. Whole-share conversion and delayed bonus
availability are supported. Fractional entitlements, overlapping pending
entitlements, unverified same-day action order, rights, cash dividends, mergers
and unknown actions remain unresolved. No value or cash-in-lieu is fabricated.
An event effective on entry day confers no pre-entry holding entitlement. An
already closed position does not inherit later action claims.

All horizon bars must be present and valid before any outcome, including early
touches or unfilled entries. A halted scheduled entry is retained with zero
return/touch, never replaced or delayed. A halted terminal exit remains pending.
Pending/unverified bonus availability prevents a full-position exit. A merely
planned listing date cannot release shares. The caller must validate actual
listing/credit availability and the complete action calendar; the arithmetic
module cannot infer that evidence from OHLCV.

The coverage object binds code, nominal price basis, time interval and exact
canonical JSON hashes of supplied bars and actions. It includes a source-evidence
digest. This is input identity validation, not verification of the evidence's
truth or completeness. No current captured corpus is being represented as a
complete action-coverage certificate.

## Fixed official-source finding

`audit_nominal_entitlement_schedule.py` verifies the previously frozen plan,
12 official HTML/text resources (six decision bodies and six ex-date notices),
and extracts the six bonus ratios and **planned** listing dates. It writes an
immutable receipt under `runtime_state/audit/nominal_entitlement_schedule_20261007`.

| Code | Additional shares per share | Ex-date | Planned listing | Calendar-day gap |
|---|---:|---|---|---:|
| 002070 | 1 | 2026-07-31 | 2026-08-20 | 20 |
| 220100 | 0.2 | 2026-09-17 | 2026-10-13 | 26 |
| 240600 | 0.2 | 2026-07-29 | 2026-08-25 | 27 |
| 340570 | 1 | 2026-08-06 | 2026-08-28 | 22 |
| 475460 | 2 | 2026-09-16 | 2026-10-13 | 27 |
| 494120 | 1 | 2026-07-15 | 2026-08-10 | 26 |

These are the dates in the captured decision versions, not final listing or
account-credit verification. For example, the captured 002070 August 12 correction
changes August 25 to August 20; that correction was not known on its July 31
ex-date. The extraction is a retrospective source audit, not point-in-time
information for a trading decision. Neither future dates nor a planned listing
are proof that the shares can currently be sold.

56 tests passed, including independent cash-flow checks for 240 deterministic
synthetic paths, splits/reverse splits, bonus delays, planned-vs-actual dates,
fractional claims, incomplete/corrupt horizons, coverage identity, unfilled and
terminal-suspension behavior. These tests establish arithmetic and refusal
behavior, not strategy performance.
