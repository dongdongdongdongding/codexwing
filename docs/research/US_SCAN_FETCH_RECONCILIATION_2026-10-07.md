# US scan source failures, October 7

The scheduled premarket scan finished at 08:50:02 UTC: 14 batches, 3,972
attempted symbols, 155 research results, 3,817 filters and zero worker errors.
However, 211 filters were `FETCH_DATA_FAIL`; the original report's `ok` status
did not establish source availability. None of the 211 original failures had
per-symbol fetch details. Original reports and inputs remain unchanged.

## Fixed cohort and actual reproduction

All 211 symbols were frozen from the original 14 run inputs before new requests.
The cohort SHA is `4cac0aff88d6a86e10247718991a3d93ee5428abc49c0b6162671e7dab9fad27`.
A source-only collector called the existing `get_history(period='5y', interval='1d')`
with its original provider ordering, an 8-second provider timeout and a 30-second
outer deadline. It captured provider frames, normalized frames, sanitized errors,
timestamps and hashes. All 211 completed in 90.13 seconds, without model scans or
DB writes:

| Later observation | Symbols | Evidence |
|---|---:|---|
| Nonempty history below the existing 50-bar minimum | 164 | 1–48 bars |
| Empty normalized history | 47 | All Yahoo frames empty; fallback yielded 41 HTTP errors and six missing-timestamp errors |

This later observation reproduces failure but cannot restore missing historical
provider details. Short histories are not automatically IPOs; empty histories
are not automatically delisted securities.

## Repair and verification

`QuantStrategy.fetch_data` now records row counts, valid row counts, provider,
date range and failure class. It enforces its existing 50-row minimum after
incomplete OHLCV rows are removed; previously 50 raw rows could pass despite fewer
usable rows. Exception messages are sanitized before logging and persistence.
The worker retains the existing rejection codes and adds structured evidence,
so admission rules continue to reject these symbols.

The shared persistence path and non-UI pipeline emit separate counts for short
history and unavailable/unknown source. The US batch report returns `degraded`
and exit 2 when source failures remain, independently of worker errors. Attempted
scan coverage and source coverage have distinct flags. Legacy fetch failures
without details remain unknown rather than being silently counted as short history.

Actual replay of all 211 captured frames through the repaired worker and shared
disk persistence produced exactly 164 short-history exclusions and 47 source
failures, with no network calls or DB writes. Under repaired semantics, the
unchanged original report is degraded with 211 unknown fetch failures; the later
captured-frame audit is degraded with 47 source failures. These are separate
observations. All original 14 input hashes remained unchanged. Fifty-one focused
tests passed, including the existing admission and persistence tests.

## Current official membership discrepancy

A separate read-only [Nasdaq directory](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt)
capture at 09:06:35 UTC has source generation time 07:02:00 UTC and 5,626 rows;
its SHA is `92193f6dcfc3e3f3cd8514884b5f2016102e21786966ebf9fbbdfab5b12e38da`.
Of the 47 empty-response symbols, 46 are absent from this current official
observation. FBYDP is present. This establishes a discrepancy with the scan's
universe, not the legal cause or historical date of each security's removal.
No scanner universe, old contract, issued result or price cache was changed.

Reconstructing all 3,972 unique attempted symbols from the 14 original inputs
found 73 absent from this current directory. Of 4,325 official non-ETF, non-test
entries, 427 were not attempted. These include warrants and notes, so this is
not evidence that 427 common stocks were omitted. Instrument classification
and the complete universe source are tracked in `swing-main-mfa7`; deleting only
the failed symbols would not resolve the discrepancy consistently.

The installed FDR dispatch uses `NaverStockListing`, not its older Nasdaq class.
A later capture preserved 68 Naver response pages: 3,996 rows, 3,972 unique
symbols, 24 duplicated symbols and a terminal empty page. Its unique symbol set
matches the original attempted set exactly. Some absent symbols retain Naver's
`tradable` status despite last-trade dates in 2025 or early 2026 (including LNW,
VERB, BITF and HTBK). That flag is therefore insufficient evidence of current
Nasdaq membership. The capture is a later observation, not a reconstruction of
the original responses.

All 427 official-only descriptions contain warrant, right, note, bond or
debenture terminology. This description check does not establish a complete
security classification, but there is no basis to label this set as missing
common stocks. The existing attempted set also contains preferred FBYDP, rights,
notes and official ETF OBTC. A blanket assumption that it contains only common
stocks would be incorrect. Raw pages, implementation source, per-page hashes
and the independent set comparison are in `naver_universe/` under the audit.

Commit `42a46be` was deployed to both branches. The six deployed module hashes
match the actual worker replay receipt. All 51 focused tests also pass in the
production checkout; health, picks, overview and ops status endpoints return
HTTP 200 on port 8800. The pinned KR prospective producer hash is unchanged.

Evidence: production `runtime_state/audit/us_fetch_failures_20261007/`, including
`cohort.json`, `capture_plan.json`, `responses/`, `capture_result.json`,
`worker_replay_verification.json`, isolated replay artifacts and official listing
reconciliation. Remaining retrieval/identity and universe repair is tracked in
`swing-main-25ly`. This repair provides no H10 probability or lane qualification.
