# KR producer status uses eligible sessions — 2026-10-07

At 13:38 KST, the daily panel already contained October 7's unfinished bar.
The swing producer correctly excluded it and reported October 6 with an ABSTAIN
gate. The web status consumer compared that date against the raw daily maximum
and incorrectly called all three KR producers stale.

Readiness times now have one shared definition, used by the existing producers
and status consumer: swing at 15:40 KST, and the 15:00 intraday snapshot at 15:10.
The thresholds and producer scoring behavior are unchanged. Status selects the
latest observed market date eligible at its lane's readiness time, including
correct UTC-to-KST conversion and holidays from the observed calendar.

A missing calendar produces an explicit error; an unconfirmed report date is
blocked. A genuinely older report remains stale once the newer observed session
is eligible. The reference date, readiness time and calendar source accompany
the status. The observed calendar does not prove that globally missing sessions
or partial provider coverage are complete.

## Verification

`runtime_state/audit/producer_calendar_20261007/` preserves both real production
reports, their SHA256 hashes, the observed calendar and the previous status code.
`replay.json` compares the same unchanged reports at three times:

| KST reference | KOSPI swing | KOSDAQ swing | KOSDAQ intraday |
|---|---|---|---|
| 13:38 | abstain | abstain | no candidates |
| 15:10 | abstain | abstain | stale |
| 15:40 | stale | stale | stale |

The previous consumer reported all three as stale at every time. Pick counts,
source dates, generation timestamps, scored-row counts, gates and diagnostics
are identical before and after. Production source files are byte-identical;
no producer was rerun and no ledger, model, issuance rule or entry time changed.

The combined suite passes 36 tests. Tests compare the status cutoff against both actual producer functions at all
boundary times, preserve the existing swing settlement and ledger-freeze cases,
and cover holidays/weekends, UTC boundaries, missing evidence and premature
reports. The web wrapper test rejects accidental use of the raw freshness maximum.

`swing-main-vmjq` tracks this status repair. It does not establish a qualified
edge lane or fix the still-running daily batch's remaining data coverage.
