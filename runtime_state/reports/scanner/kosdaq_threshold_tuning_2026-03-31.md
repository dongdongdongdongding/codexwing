# KOSDAQ Threshold Tuning

- Date: 2026-03-31
- Goal: improve KOSDAQ scan quality without weakening core safety controls blindly.

## What We Changed
- split KR liquidity thresholds by market
  - `KOSPI` turnover floor: `10B`
  - `KOSDAQ` turnover floor: `7B`
- relaxed `KOSDAQ + RED` precision gate only for stronger alpha names
  - `AG_KOSDAQ_RED_MIN_CONVICTION=64`
  - `AG_KOSDAQ_RED_ALPHA_RELAX_FLOOR=45`
- relaxed `KOSDAQ BEAR` hard filter for downtrend names from `alpha>=50` to `alpha>=45`
- added reject detail tracing for
  - liquidity failures
  - KR hard-filter failures
  - KR precision-gate failures

## External Label Evidence
From [signals_rows_enriched.csv](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/reports/external_signals/signals_rows_enriched.csv):
- `KOSDAQ BEAR`, `alpha >= 45`
  - samples: `31`
  - average 5D return: `+15.31%`
  - win rate: `70.97%`
- `KOSDAQ BEAR`, `alpha >= 40`
  - samples: `33`
  - average 5D return: `+14.64%`
  - win rate: `69.70%`
- `KOSDAQ BULL`, `alpha >= 25`
  - samples: `143`
  - average 5D return: `+6.69%`
  - win rate: `68.53%`

Interpretation:
- `KOSDAQ BEAR` is not a blanket avoid bucket in the external labels.
- strong `alpha` matters more than raw `ai_prediction` in the current KOSDAQ sample.

## Runtime Validation
Latest diagnostic run: [scanner_handoff.json](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/shared_working/RUN-2DEC9974/scanner_handoff.json)

Reject details:
- `266870.KQ`
  - liquidity fail
  - turnover `3.39M` vs required `7.0B`
- `347860.KQ`
  - liquidity fail
  - turnover `550.7M` vs required `7.0B`
- `214150.KQ`
  - KR hard filter fail
  - `alpha=42`, `real_trend=DOWN`
  - after relax, still below the new `45` floor
- `137950.KQ`
  - precision gate red-market fail
  - `alpha=49`, `conviction=45.9`, `prob_5=36.7`, `clean_prob=18.0`, `tier_sort=3`

## Conclusion
- current KOSDAQ 0-result behavior is now explainable, not silent failure.
- small liquidity loosening would not save the sampled fails because the liquidity gap is huge.
- the new `alpha>=45` KOSDAQ-BEAR hard-filter relax is justified by the external labeled dataset.
- the remaining red-market precision block still looks reasonable for weak T3 / low-clean-prob setups.

## Best Next Step
- add a `tradable KOSDAQ universe` prefilter based on recent turnover before the deep scan begins.
- that will improve hit-rate more safely than forcing weak or illiquid names through late-stage gates.
