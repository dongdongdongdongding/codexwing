# KOSDAQ Universe Prefilter

- Date: 2026-03-31
- Goal: stop spending scan budget on non-tradable KOSDAQ names before deep evaluation.

## What Changed
- added live-amount universe prefilter inside [quant_analysis.py](/Users/dongdong/Desktop/codex_swing/swing-main/modules/quant_analysis.py)
- default thresholds:
  - `AG_KOSDAQ_UNIVERSE_MIN_AMOUNT=5000000000`
  - `AG_KOSPI_UNIVERSE_MIN_AMOUNT=12000000000`
- current post-filter universe sizes:
  - `KOSDAQ`: `276`
  - `KOSPI`: `178`

## Validation
Run: [RUN-758DCA86 scanner_handoff.json](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/shared_working/RUN-758DCA86/scanner_handoff.json)

Before prefilter:
- KOSDAQ sample runs repeatedly showed `LIQUIDITY_FILTER_FAIL`

After prefilter:
- top reject reasons shifted to:
  - `KR_HARD_FILTER_FAIL`: `12`
  - `KR_SIGNAL_WINDOW_FAIL`: `4`
  - `PRECISION_GATE_RED_MARKET`: `3`
  - `KR_BASELINE_FILTER_FAIL`: `1`
- `LIQUIDITY_FILTER_FAIL`: `0`

## Meaning
- this is a healthy change.
- the scanner is no longer wasting work on obviously illiquid KOSDAQ names.
- the remaining blockers are now strategy-quality gates, which are the right place to tune for win-rate improvement.

## Next Target
- analyze the `KR_HARD_FILTER_FAIL` distribution in the liquid KOSDAQ universe and decide whether the downtrend/alpha rules still need a regime-specific split.
