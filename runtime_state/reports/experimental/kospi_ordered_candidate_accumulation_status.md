# KOSPI Ordered Candidate Accumulation Status

- generated_at: `2026-05-14T14:00:09Z`
- purpose: confirm whether KOSPI ordered shadow-gate samples can be expanded beyond the latest SWING archive without changing production scanner logic.

## Inputs Checked

- SWING archive: `runtime_state/reports/archive/scan_archive_learning_dataset_swing.csv`
  - rows: `6423`
  - KOSPI ticker suffix rows: `3602`
  - scan_mode distribution: `SWING=6257`, blank=`166`
- KOSPI all-mode archive: `runtime_state/reports/archive/scan_archive_learning_dataset_kospi.csv`
  - rows: `5710`
  - KOSPI ticker suffix rows: `5710`
  - scan_mode distribution: `SWING=3460`, `INTRADAY=2108`, blank=`142`

## Ordered Label Result

The expanded all-mode run produced the same effective ordered-label table as the latest SWING run after ticker/date/profile de-duplication.

- latest rows CSV SHA1: `357204f606431bb0395040bd04bc6db29893028a`
- expanded all-mode rows CSV SHA1: `357204f606431bb0395040bd04bc6db29893028a`
- rows: `5121`
- unique ticker-dates: `1707`
- ready ordered labels: `4585`
- retained scan_mode after de-duplication: `SWING=5121`

## Current Shadow Gate

- profile: `5D_ordered_10v5`
- conditions: `cohort=Top3`, `explosive_leader_flag=0`, `prob_clean=[28.1,31.8]`, `decision_score>=100`
- all: `n=19`, win=`73.6842%`, avg_mfe=`13.2918%`, avg_mae=`-1.5708%`
- train: `n=10`, win=`70.0%`
- test: `n=9`, win=`77.7778%`, test_stop=`22.2222%`
- rolling: fold_win=`71.4286%`, min_fold=`66.6667%`

## Interpretation

The current KOSPI SWING shadow gate has been stacked as far as the available archive can support without duplicating the same ticker/date or using immature future labels.

Do not inflate sample size by counting intraday duplicates for the same ticker/date. That would overstate confidence because the same future OHLCV path would be counted multiple times.

Further legitimate accumulation requires new trading days to mature into ordered labels, especially for no-touch rows that need the full 5-session horizon.
