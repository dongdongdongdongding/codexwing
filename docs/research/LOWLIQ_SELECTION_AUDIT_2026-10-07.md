# Low-liquidity legacy selection audit

Issue: `swing-main-h4zv`; follow-up: `swing-main-jm3e`.

The inherited `lowliq_band_delisted_latest.json` says `SURVIVED`, but it cannot
support lane promotion. The available legacy harness filters the prediction
universe using future labels, treats no-barrier observations differently based
on a future exit heuristic, and trains on labels resolved after quarter start.
This audit changes evidence admissibility, not the original report's measured
values. No model was refitted or scored and no new strategy result was selected.

## Preserved inputs and scope

The final frozen evidence is under production
`runtime_state/audit/lowliq_selection_20261007/final/`:

| Input | SHA256 |
|---|---|
| Current `px_delisted.parquet` | `8c6fba2daf8d995be66441d873094928f347618c3a41f208c9286509f4fb1981` |
| Available legacy harness | `037d2a7b666755555d680c1087e2842af853569ddb12f54c979f67cd8d2ef52b` |
| Original August JSON report | `ccbe5c3e67302379a93248ec679aee967ed33fdf286cb78484e01f0d70289da0` |

Each complete copy and its live source were hashed before and after the audit.
The current panel ends on 2026-10-02, with 5,360,785 rows and 3,196 codes.
Counts below restrict signal dates to the legacy test range, 2019-01-01 through
2026-06-30. They do not reconstruct the August model's 5,515 selected picks:
that report did not pin its panel, scores or fitted models. The root audit
folder retains an earlier identical-count run with less precise field names;
`final/` is authoritative and adds concrete training-boundary examples.

## Reproduced defects

1. `first_touch_masked` leaves NaN when neither price barrier is touched, even
   with five fully observed future rows. `main` drops those labels before both
   training and prediction. At a fixed signal-time price history, changing only
   a future high changes eligibility for prediction.
2. For `exited` codes, all valid-entry NaN labels become zero, including fully
   observed no-touch windows. The heuristic is last observed date before panel
   end minus 14 calendar days; it is not an independently verified delisting
   date. Thus future exit classification changes historical candidate retention.
3. Quarterly training checks signal date against quarter start but does not
   check when the barrier event became known. Actual first-touch event dates
   on or after the first test date appear in the training label set.

| Current-panel measurement | Rows |
|---|---:|
| Eligible band and six return features, before future-label filtering | 1,464,462 |
| Retained after the legacy label filter | 994,563 |
| Fully observed, valid-entry windows with neither barrier touched | 484,564 |
| Such windows excluded for codes not flagged exited | 463,723 |
| Such windows retained for codes flagged exited | 20,841 |
| Fully observed windows with no valid next-open entry, excluded before selection | 5,945 |
| Barrier labels resolved on/after the corresponding quarterly fit boundary | 42,224 |

The last count is a conservative direct-event count over 30 quarter boundaries;
it does not quantify all additional effects of future exit classification or
unknown publication times. For example, code 000050's 2026-03-27 training signal
has its first event on 2026-04-02, after the 2026Q2 boundary. Exact examples and
counts by quarter are in `audit.json`.

The independent vectorized barrier calculation matched the reviewed legacy
function on all 5,360,785 source rows. Seven tests cover no-touch exclusion,
future-exit retention, event timing, suspension handling, unchanged causal
eligibility, future-only perturbation and refusal to execute unreviewed code.

## Consequence for the requested replacement

Old H5 touch 61.99%, positive paired spread, and `SURVIVED` are not evidence of
an executable H10 candidate with at least 70% touch probability or the requested
cadence. Corrected research must preregister the full signal-time universe,
training-label availability, unfilled/terminal handling, costs, controls and
holdout before fitting or inspecting new outcomes. A retrospective correction
must not be presented as a prospective record.

The current production KR swing producer already documents the August 21
replacement of `ft_5_5` with the contract label and separates training label
filtering from prediction eligibility. This audit concerns the separate inherited
low-liquidity harness; it does not alter the pinned production producer or the
two active prospective studies. A scoped search across `multi_agent`, `modules`,
`b_engine`, `docs` and `research` found the legacy output path only in its own
harness. No routing or publication configuration was changed.
