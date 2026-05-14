# KOSDAQ Ordered Candidate Assessment

- generated_at: `2026-05-14T14:18:19Z`
- source report: `runtime_state/reports/experimental/kosdaq_ordered_candidate_search_latest.md`
- scope: internal shadow validation only; production scanner ranking is unchanged.

## Dataset

- KOSDAQ SWING archive rows: `2597`
- ordered rows labeled across profiles: `6272`
- ordered label ready rows: `5838`
- unique ticker-dates: `1568`
- split_day: `2026-04-22`

## Operating Baseline

From `target_touch_kr_top5_exception_ordered.md`:

| Cohort | Horizon | n | Win Target-Before-Stop % | Stop-First % | Avg Close Return % |
| --- | ---: | ---: | ---: | ---: | ---: |
| KOSDAQ Top5 | 5D +5/-5 | 207 | 57.0 | 39.61 | 3.5493 |
| KOSDAQ Exception Leader | 5D +5/-5 | 170 | 54.71 | 39.41 | 5.6661 |

KOSDAQ remains materially weaker than KOSPI under the same ordered stop-first rules.

## Latest Search Baseline

| Profile | All n | All Win % | Test n | Test Win % | Test Stop % |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5D_ordered_5v5 | 1480 | 41.9595 | 806 | 35.1117 | 63.5236 |
| 5D_ordered_8v5 | 1460 | 31.9178 | 786 | 27.0992 | 69.8473 |
| 5D_ordered_10v5 | 1451 | 26.6023 | 777 | 21.6216 | 73.7452 |
| 5D_ordered_12v5 | 1447 | 22.322 | 773 | 18.37 | 75.5498 |

## Best Current Shadow Candidate

- profile: `5D_ordered_5v5`
- conditions: `volume_ratio<=1.23`, `trend=DOWN`, `selection_lane=1d`
- all: n=`20`, win=`85.0%`, stop=`15.0%`, avg MFE=`10.0859%`, avg MAE=`-2.8729%`, avg close 5D=`8.1598%`
- train: n=`11`, win=`81.8182%`, stop=`18.1818%`
- test: n=`9`, win=`88.8889%`, stop=`11.1111%`
- rolling: fold weighted win=`89.4737%`, min fold=`80.0%`, max fold stop=`20.0%`

## Higher Target Check

- release-like candidates were found only for `5D_ordered_5v5`.
- no release-like candidates survived for `5D_ordered_8v5`, `5D_ordered_10v5`, or `5D_ordered_12v5`.
- best 8% target diagnostic candidate: `tech_score>=80`, `ml_prob>=50`, `core_trend_flag=1`, `selection_lane=1d`
  - all n=`13`, win=`69.2308%`, test n=`6`, test win=`100.0%`, test stop=`0.0%`, fold weighted win=`69.2307%`, min fold=`42.8571%`
  - not release-like because all/fold stability is below threshold.

## Existing Validated-Touch Exception Recheck

- rule: `cohort=Top5`, `trend=UP`, `alpha_score>=90`, `volume_ratio>=2`
- profile: `5D_ordered_5v5`
- all n=`5`, win=`40.0%`, stop=`60.0%`, avg MFE=`11.8694%`, avg MAE=`-5.7941%`, avg close 5D=`20.2144%`
- test n=`4`, win=`50.0%`, stop=`50.0%`

This proxy touch exception should not be promoted. Ordered stop-first validation shows too much downside path risk in the current ready sample.

## Interpretation

The best KOSDAQ pattern is not a high-momentum chase pattern. It is a small-sample, low-volume, down-trend, 1D-lane rebound pattern that reaches +5% before -5% more often than the broad KOSDAQ cohorts.

That makes it useful as a daily shadow observation target, but not a production replacement:

- sample size is only n=20
- target is +5%, not +10%
- condition shape conflicts with normal momentum-entry intuition
- KOSDAQ broad baseline remains weak and stop-heavy
- the previous `trend=UP + alpha>=90 + volume_ratio>=2` proxy exception fails ordered stop-first validation

## Daily Observation Rule

Observe this candidate daily, but do not replace the operating model:

- `5D_ordered_5v5`
- `volume_ratio<=1.23`
- `trend=DOWN`
- `selection_lane=1d`

Promotion should require materially larger forward-ready sample size, win >=70%, stop-first <=20%, and evidence that the pattern is not just a short-lived low-volume rebound artifact.
