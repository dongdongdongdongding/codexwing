# KOSPI Ordered OHLCV Revalidation

- generated_at: `2026-05-14T12:41:34.334512+00:00`
- input_rows: `4335`
- kospi_rows: `2462`
- selected_rows: `152`
- ordered_labeled_rows: `152`
- entry_policy: `signal_day_close_from_same_ohlcv_source`
- same_bar_policy: `stop_first`

## Candidate Results

- `high_upside_top3_10v5`: n=51/51, ordered_win=50.9804%, stop_first=35.2941%, no_touch=13.7255%, avg_mfe=10.3049%, avg_mae=-3.2867%, proxy_win=78.947%, proxy_min_fold=62.5%
- `strict_top5_low_ml_10v5`: n=40/40, ordered_win=50.0%, stop_first=25.0%, no_touch=25.0%, avg_mfe=9.3378%, avg_mae=-2.5893%, proxy_win=73.684%, proxy_min_fold=71.429%
- `strict_top5_core_8v4`: n=61/61, ordered_win=44.2623%, stop_first=54.0984%, no_touch=1.6393%, avg_mfe=7.9065%, avg_mae=-3.5643%, proxy_win=78.947%, proxy_min_fold=71.429%

## Interpretation

- `high_upside_top3_10v5`: not validated by ordered OHLCV
- `strict_top5_low_ml_10v5`: not validated by ordered OHLCV
- `strict_top5_core_8v4`: not validated by ordered OHLCV

## Ordered Refinement Candidates

- `ordered_prob_floor_core_route`: conditions=['prob_clean>=28.1', 'theme_routing_path=core_only'], all n=39 win=71.7949%, train n=27 win=70.3704%, test n=12 win=75.0%, test_stop=25.0%, unique_ticker_dates=24
- `ordered_high_upside_top3_prob_band_10v5`: conditions=['candidate_id=high_upside_top3_10v5', 'prob_clean>=28.1'], all n=20 win=70.0%, train n=10 win=70.0%, test n=10 win=70.0%, test_stop=30.0%, unique_ticker_dates=20

## Notes

- This report revalidates archive-discovered candidate rules using ordered daily OHLCV.
- Same-day target and stop cannot be ordered with daily bars; stop_first is used conservatively.
- The signal-day close from FinanceDataReader is used as entry to avoid archive entry-reference drift.
- Rows without enough forward bars remain selected but are excluded from ordered win-rate denominators.
