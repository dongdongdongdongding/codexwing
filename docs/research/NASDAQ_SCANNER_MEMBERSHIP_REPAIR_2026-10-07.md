# Current Nasdaq scanner membership repair

The scanner's installed FinanceDataReader uses Naver's listing API. An actual
68-page capture returned 3,996 rows and 3,972 distinct symbols, exactly the
original October 7 premarket scan set. The current official Nasdaq directory
excluded 73 of those symbols. Some Naver records remained marked tradable even
though their last-trade timestamps were months old. These observations establish
an unreliable current-membership source, not each security's legal delisting
cause or historical effective date.

## Behavior

`QuantStrategy.get_market_tickers('NASDAQ')` now verifies every provider-seed
member against the official directory before returning it. It preserves provider
ordering and the existing instrument scope, uses official security names and
excludes test issues. This is not an expansion to every official instrument or
a new common-stock-only strategy policy. Preferred FBYDP and ETF OBTC remain
included; the original seed also includes rights and notes.

The shared directory parser checks format, uniqueness, flags, generation time and
its existing seven-day source-age bound. Each new capture preserves raw bytes,
HTTP status, observation/generation timestamps, SHA and validation/failure record.
A five-minute process cache avoids repeated identical downloads. An expired cache
cannot be used if refresh fails. Official membership failure stops universe
resolution rather than admitting a local list without verification.

A local provider fallback must pass the same check and is marked incomplete.
The batch report returns degraded/exit 2 for fallback seeds and failed/exit 2
with a durable receipt for universe-resolution failures. Source/attempt coverage
cannot be complete when the universe itself failed. Shared disk artifacts and
non-UI diagnostics preserve membership provenance and fallback warnings.

Manual Nasdaq selections use the same official membership evidence. Explicit
currently listed instruments outside the provider seed remain selectable, while
absent names cannot bypass membership checks. A batch run carries its initial
verified universe through all worker batches instead of fetching a changing
provider list separately for each batch. Scheduled US and Discord scans launch
the non-UI code in subprocesses and pick up the new code on subsequent launches.

## Actual verification

At 09:25:28 UTC, a fresh official capture had the same 5,626 rows and source SHA
`92193f6dcfc3e3f3cd8514884b5f2016102e21786966ebf9fbbdfab5b12e38da`
as the earlier independent observation. Source generation was 07:02 UTC.
The complete fixed 3,972-symbol seed produced exactly 3,899 retained members and
73 exclusions, matching the independent set comparison. All exclusions were
absent names, not test issues. Original provider ordering was preserved.

An independent zero-network replay executes the actual QuantStrategy and manual
normalization paths using captured source bytes. It confirms the complete set,
ordering, FBYDP/OBTC retention and rejection of manual LNW. Original source cohort
and comparison evidence hashes are unchanged. Of the original 211 fetch-failure
symbols, 157 remain in this current membership set. Membership verification does
not repair their histories. In particular, FBYDP's empty history remains an open
retrieval issue (`swing-main-dych`).

Seventy-three focused tests pass: real pipeline dispatch with a frozen verified
batch, expired-cache/source failure, malformed directory, fallback handling,
manual bypass prevention, shared disk evidence, durable failure receipts,
existing source diagnostics and the directory parser tests.

Audit: production `runtime_state/audit/nasdaq_membership_repair_20261007/` contains
`guard_verification.json`, `selected_names.json`, immutable source captures,
`verify.py` and `independent_verification.json`. The earlier full Naver capture is
in `runtime_state/audit/us_fetch_failures_20261007/naver_universe/`.

This change concerns the current scanner universe. It does not rewrite prior
scan reports, issued contracts, prices, the daily feature universe or historical
membership snapshots. It provides no H10 performance or new-lane qualification.
