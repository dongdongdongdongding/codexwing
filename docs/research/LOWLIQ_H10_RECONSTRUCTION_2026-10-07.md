# Fixed low-liquidity H10 reconstruction

This is a retrospective research screen, not a qualified replacement lane. No test
returns or touch statistics have been computed. Production KR models, issued
contracts, and the two existing prospective studies remain unchanged.

## Registration and actual fit

The parent protocol `research/prereg_lowliq_touch10_20261007.json` was committed
and pushed as `a9fbf07` before fitting. Implementation `401eda4` uses the fixed
June 30 cutoff, July 2024–June 2026 training signals, and July–September 2026 test
calendar. Date prefixes are removed **before** reconstructing adjustments. This
repairs demonstrated future-row dependence; it does not certify historical
publication times, provider revisions, or economic corporate-action factors.

The universe is KOSPI/KOSDAQ with actual 20-session average turnover of
KRW 0.5–3 billion, positive signal volume and the six required return features.
There are 35 predictors. Future outcomes, future exit flags and delisting dates
never determine test eligibility. All six fixed LightGBM fits completed:
three real-feature seeds and three equal-dimension noise controls, 400 trees each.

| Training eligibility | Rows |
|---|---:|
| Resolved and admitted to training | 360,602 |
| Unfilled scheduled entry | 188 |
| Suspended unresolved terminal exit | 552 |
| Invalid or missing source | 81 |
| Incomplete H10 window | 7,336 |
| Total eligibility records retained | 368,759 |

Training includes 190,423 touches and 170,179 complete no-touch labels. Those are
**training labels**, not an out-of-sample success rate. The last admitted signal
is June 16 and the last label-availability date June 30. Whole-table verification
matched every availability date to the tenth subsequent observed market session;
384 deterministic training samples matched the separate contract settlement engine.
All six model hashes, 35-input counts and 400-tree counts were checked.

Training SHA256: `535e19b68a8906a526106aec54183e754897ae03526c998b71dca09d8387700e`.
Research artifacts live under production `runtime_state/audit/lowliq_touch10_20261007/`;
independent fit checks are in `lowliq_touch10_verification_20261007/`.

## Cadence boundary amendment before outcomes

The parent's first-three-dates-in-five rule can generate 38 firing dates in a
62-session window: 3.0645 per five sessions. Each rolling five-session interval
still obeys its cap; the aggregate rate exceeds the requested ceiling because of
the incomplete terminal interval. The discrepancy was identified after 20 date
score receipts, before any test labels or return statistics were inspected.

Separate protocol `prereg_lowliq_touch10_cumulative_20261007.json` was committed
as `3295087`. It adds the deterministic prefix cap
`total_fires <= floor(3 * elapsed_sessions / 5)`, retaining the rolling cap.
`f5b9e58` implements it and corrects copied parent wording about already-seen
scores; no numerical or selection parameter changed in that wording correction.
Models, universe, scores, ranking, contract and test period are reused unchanged.
Blocked dates abstain; their picks are not carried to another date.

This is an explicitly disclosed pre-outcome amendment on the same history, not
independent unseen evidence. Original records remain intact. The amended screen
uses family size four (parent, amendment, existing KR60 and KR120 studies), without
silently editing the existing studies or claiming to adjust all historical research.
The derivative refuses to run until every parent date is frozen and verified.

Tests cover all prefixes and rolling windows across 500 sessions, missing eligible
dates, exact original top-three preservation, parent-record tampering and replay.
The original 20 tests and five additional cadence tests pass (25 distinct tests).

Actual reconstruction completed all 62 dates, retaining 41,625 eligible
code/date rows and all six scores per row. The separate verifier
`audit_lowliq_frozen_scores.py` reproduced **249,750 prediction cells exactly**,
then independently checked rankings with NumPy ordering and both calendars with
separate count logic. It read no test outcomes. Every variant has 38 parent firing
dates versus 37 amended dates. The amendment has 111 selected records (three per
firing date), a full-window rate of **2.98387097 firing dates per five sessions**,
and at most three in every rolling five-session window. These are historical
reconstructed selections, not issued recommendations or measured success rates.

The amended completion receipt SHA256 is
`a91747571ef13771f74b9a0396c80ed20d5281d7637361ad7e031a5f723603dc`.
Both score sets are immutable; repeated reconstruction must reproduce them.
Independent source capture covered all 1,310 distinct eligible codes, with 2,620
completed KIS J requests across adjusted and nominal bases through October 2.
Its request plan precedes capture and includes parser/adapter fingerprints;
errors and missing dates remain records. This collection reads no test returns
and changes no live price cache. The actual run completed in 531.17 seconds:
170,208 basis-specific daily rows, no missing or additional existing-panel dates,
and no failed or empty captures. Separate Decimal checks verified 851,040 OHLCV
fields plus request identities, dates and hashes. Actual replay made zero network
calls and preserved all 2,620 response files byte-for-byte.

**The two provider bases report different volume values on 1,977 code/dates.**
That observation is not a source-error or economic-basis verdict; it means the
adjusted and nominal volume fields must not be assumed interchangeable. Nominal
source comparison, adjusted price-path comparison and any supported correction
are tracked separately in `swing-main-ivuh`. Earlier feature lookbacks and the
remaining final H10 prices are outside this June 30–October 2 capture. Evidence is
in production `runtime_state/audit/lowliq_krx_source_20261007/`; capture task
`swing-main-djdd` is complete, source certification and strategy qualification are not.

## Outcome boundary and source limits

### Independent source comparison, October 7

`research/compare_lowliq_krx_source.py` compared all 85,104 existing code/dates
for the fixed 1,310-code universe, June 30–October 2. Its create-only plan pins
the frozen panel, capture plan, comparison code and all 2,620 response files.
An independent arithmetic replay verified every difference record and all
510,624 nominal OHLCV/amount comparisons. A separate join verified all six raw
fields against the current marcap source for all 85,104 rows, pinning its SHA
before and after the read. Neither comparison computed test strategy outcomes.

All nominal close, volume and traded amount values agree exactly. The only
nominal differences are open/high/low on 1,394 rows across 106 codes (4,182
cells): every such row has zero volume and amount, the panel stores zero OHL,
and KIS stores the matching close in all three fields. The frozen builder copies
these raw fields from marcap without replacing zeros. These are observed
nontrading display conventions; copying KIS prices must not create a fill.
All six nominal fields agree on every positive-volume row in this scope.

After removing a constant currency scale at each code's last common traded
close, adjusted OHLC differs by more than 1e-6 KRW in 11,532 cells across 129
codes. Of these, 4,897 cells are on zero-volume rows; 6,635 cells across 65 codes
are on positive-volume rows. Within the latter group, 3,586 cells across 41
codes differ by more than one KRW. These two numerical cutoffs are diagnostics,
not economic correctness thresholds or permissions to exclude observations.
The frozen builder's share-count, administrative-reset and lagged-event
heuristics require corporate-action reconciliation; a price difference alone
does not establish which source is correct. Provider nominal versus adjusted
volumes differ on 1,977 code/dates, while traded amounts agree on every row.

Original data, frozen scores and study universes remain unchanged. Detailed
differences, provider flags/factors, the independent replay script and its
receipt are in production `runtime_state/audit/lowliq_krx_comparison_20261007/`.
Nine focused comparison/capture tests cover scaling, missing/duplicate dates,
nonfinite values, preservation and nontrading conventions. Source comparison
task `swing-main-ivuh` is complete; economic-factor reconciliation, earlier
feature history, final H10 prices and strategy qualification remain separate.

### Confirmed input errors: qualification rejected pending reconstruction

`trace_lowliq_adjustment_events.py` reproduced all five adjusted fields on all
119,834 historical rows of the 65 positive-volume mismatch codes. The comparison
window contains 57 algorithm events: 37 same-day share-count rules, 15 lag rules
and five limit rules. An observer injected into the hash-pinned builder records
which later share-count observation caused each lagged assignment; it does not
change that algorithm or the frozen panel. Twelve focused tests passed and the
actual trace replay reproduced the same result.

Two event errors are now supported by official documents:

- **005440, July 20:** the lag rule assigns a factor of 1.1763447052047653 from
  a 27,492,898-share increase. The [KRX additional-listing notice](https://kind.krx.co.kr/external/2026/07/14/000152/20260714000196/68154.htm)
  identifies this as a share exchange, and the [exchange filing](https://kind.krx.co.kr/external/2026/02/12/000133/20260212000353/10084.htm)
  explains that Hyundai Home Shopping holders receive the new shares. Therefore
  this increase is not a proportional share entitlement for existing 005440
  holders. KIS adjusted and nominal OHLC agree throughout the captured window.
- **008830:** the August 24 share-count increase causes the lag rule to place
  its 1.3 factor on August 7. The [official July 31 ex-rights notice](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260731901116)
  specifies August 3 and a 7,000 KRW reference price. The [offering document](https://kind.krx.co.kr/external/2026/06/10/000744/20260610002005/10601.htm)
  gives the 30% bonus allocation. The heuristic chose a date four observed
  trading sessions too late; KIS marks the adjustment on August 3.

Direct HTTP captures preserved all five official HTML documents and extracted
text with request/receipt times and SHA hashes. The DART main page links document
11505343; its separately captured viewer contains the actual ex-date table.
The first trace attempt stopped at a Parquet index round-trip assertion before
producing a verdict. Its plan is preserved; the corrected index serialization
uses `trace_plan_v2.json` with a new code hash.

An independent two-event reconstruction compared 260 OHLC cells per code over
June 30–October 2. Using event factor 1 for 005440 removes all differences;
placing the 1.3 factor on August 3 for 008830 reduces the maximum difference to
0.923077 KRW. Cells over one KRW fall from 52 and 16, respectively, to zero.
Sub-KRW provider differences are retained; this diagnostic is not a blanket
certification threshold. No source file, model, score, universe or live consumer
was changed. No strategy outcome was computed.

The immutable `lowliq_corporate_actions_20261007/source_verdict.json` records
`INPUT_REJECTED_FOR_QUALIFICATION`. This rejects the current input basis, not the
strategy's alpha; waiting for H10 maturity alone cannot make it admissible.
Remaining codes and earlier feature history still require reconciliation under
`swing-main-5pfa`. Any corrected study must use an explicit new source epoch and
preserve the original preregistration, scores and evidence rather than silently
replacing their inputs.

### Separate partial source correction

`normalize_verified_kr_events.py` and its reviewed JSON rules now create a
separate source epoch, `runtime_state/audit/kr_verified_events_v1_20261007/`.
The exact frozen parent hash, official captures, old factors, share counts and
row counts are guarded. The writer streams bounded batches, verifies all raw
columns and unaffected rows, and publishes the output by atomic create-only
link. Revisions or overlapping rules fail; the original study and live caches
are never replaced by this command.

The actual output contains the same 5,360,785 rows and schema metadata. Only
56 rows change: 005440's 52 rows from July 20 through October 2 remove the false
issuance factor; 008830's four August 3–6 rows receive the correctly dated bonus
factor. Each changes only `adj_factor` and four adjusted OHLC fields. Independent
full-file verification proved every column of the other 5,360,729 rows exact and
all raw columns exact across the whole panel, including nominal volume/amount.
The original panel SHA remains unchanged. The corrected panel SHA is
`803fa406aa946f1a35ef0eb928f7a2f9ff3928f779cbedfe6f570e448bb7d862`.

Independent KIS comparison on the two corrected histories checks 520 OHLC cells;
maximum scale-adjusted errors are 2.27e-12 KRW for 005440 and 0.923077 KRW for
008830. An actual repeat returns `REUSED`, with the manifest, panel and receipt
mtime/size unchanged. Sixteen focused tests pass, including wrong-source share
counts, altered adjusted fields, overlapping rules and double-adjustment refusal.

This is a **partial corrected source**, not a qualified model input or deployed
lane. `source_certified` and `publication_allowed` remain false. Other mismatch
codes and earlier history still need reconciliation. The parent input rejection,
fixed scores and preregistration remain intact. Tracking: `swing-main-hov1`.

The next-open contract is TP5/H10, with entry day included, no stop, and 1.0%
round-trip primary cost; 0.30% and 0.215% are sensitivities. Unfilled entries stay
in the selected denominator with zero touch and zero return. Missing or suspended
outcomes are retained; unresolved selected or control records block qualification.
The final evaluator must use the full fixed window, same-day market-matched
controls, five-session block intervals, fixed ticker/date placebos and all seeds.
No threshold, sign, calendar phase or market subset may be chosen from outcomes.

The frozen source ends October 2. Its Q3 calendar contains 62 dates. The absent
weekdays coincide with the published July 17, August 17 and September 24–25 holidays.
The [July notice](https://strn.krx.co.kr/corebbs5/BHPSTRN0401/view?bbsSeq=146),
[August notice](https://strn.krx.co.kr/corebbs5/BHPSTRN0401/view?bbsSeq=149), and
[September notice](https://strn.krx.co.kr/corebbs5/BHPSTRN0401/view?bbsSeq=150)
are KRX mock-market notices and serve as corroboration, not a complete cash-market
calendar certificate. July's body contains a copied holiday-name error; its title
and date identify July 17. August 7's mock-system maintenance is not a cash holiday.

Allowing for [October 5 and 9 closures](https://strn.krx.co.kr/corebbs5/BHPSTRN0401/view?bbsSeq=151),
the expected final H10 session for September 30 is October 16. This is a calendar
expectation, subject to actual observed sessions and final source availability.
The calendar audit preserves web-tool text separately from direct HTTP captures:
direct requests returned non-content pages despite HTTP 200 and are not evidence.

Passing retrospective numerical gates would still require independent price and
corporate-action checks, genuinely prospective evidence for the exact configuration,
category-specific admission and verified consumer wiring before replacement.
Neither model scores nor training touch counts are calibrated H10 probabilities.

Tracking: `swing-main-jm3e` (study), `swing-main-3h1h` (boundary amendment).

## Additional official issuance corrections

The separate v2 research source adds three verified corrections for 291810,
270520 and 071950 to the earlier two-event v1 source. Exactly 63 additional rows
change, all raw fields and other 5,360,722 rows remain exact, and six parent models
retain their hashes. See [official evidence, full-panel verification and source
limitations](KR_ISSUANCE_FACTOR_REPAIR_2026-10-07.md). Other 60 mismatch codes and
earlier history remain uncertified. This is not a new strategy outcome or a
replacement of the frozen parent study.

The remaining fixed 60-code cohort now has a [verified official disclosure
corpus](KR_REMAINING_ACTION_CORPUS_2026-10-07.md): 462 selected query/document
records and 884 HTML body resources, including supplemental preferred-share
issuer evidence. This completes the declared collection scope, not economic
factor certification or strategy qualification.

The separate [v3 issuance correction](KR_ISSUANCE_FACTOR_REPAIR_V3_2026-10-07.md)
adds eight supported event repairs (338 rows), including a mixed 5-for-1 split
that the heuristic treated as 9.519035-fold holder entitlement. All other rows
and raw fields remain exact. The cumulative 13 event repairs do not certify
complete security histories or qualify a replacement lane.

The [official ex-right reference audit](KR_EXRIGHTS_PRICE_BASIS_2026-10-07.md)
separates price continuity, shareholder entitlements and provider rounding for
18 notices/17 securities. All 16 in-window percentages agree with rounded KRX
reference ratios, but two-decimal percentages alone do not reproduce all 4,420
prices. Source normalization must use an explicit convention; event-spanning
portfolio returns require separate execution/valuation evidence.

The separate [v4 official ex-reference source](KR_EX_REFERENCE_REPAIR_V4_2026-10-07.md)
applies 16 price-reference events and removes two mistimed paid-issue factors:
17 codes, 700 rows, whole-panel raw/unaffected fields exact. It preserves earlier
uncertified bases and does not certify event-spanning portfolio returns. The
cumulative 31 event corrections remain partial source work, not lane promotion.

The [v5 fixed-reference overlay](KR_FIXED_REFERENCE_REPAIR_V5_2026-10-07.md)
reconciles 30 par-change reference notices (29 updates, one already matching),
changing 737 rows while retaining later unrelated factors. Direct comparison
against the original source confirms 55 codes/1,765 cumulative changed rows;
complete-history, auction-reference and event-spanning return certification
remain unresolved.
### Quote-reference source extension v6

`swing-main-s4m7` adds ten reference events / 341 rows to the separate v5 research
panel. Full independent comparison preserves every raw field and all unaffected
rows; cumulative original-to-v6 scope is 63 codes / 2,040 rows. Two remaining
original mismatch codes have October 7 actions outside the frozen source and
constant provider-scale compatibility across all 520 OHLC cells; no future
action is inserted. See `KR_EVENT_REFERENCE_REPAIR_V6_2026-10-07.md` for evidence
and limitations. All certification and publication gates remain false; no parent
study replacement, model change or test outcome calculation was performed.
### Full fixed-cohort v6 recheck

`swing-main-iti8` rechecked all 1,310 codes / 85,104 dates and found six additional
nontrading-history reference contradictions outside the earlier 65 traded-row
mismatch codes. `swing-main-5yeb` captured their 32 relevant primary documents;
`swing-main-6hsa` tracks their guarded correction. Source certification remains
false. See `KR_V6_FULL_COHORT_RECHECK_2026-10-07.md` for complete scope and evidence.
