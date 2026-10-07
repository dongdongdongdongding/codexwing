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

## Outcome boundary and source limits

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
