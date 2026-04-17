# Segment Overlay Proxy Validation (Top 5)

- generated_at: 2026-04-17T00:12:48.136343+00:00
- source: supabase.market_scan_results + shared_working/scanner_handoff + bridge_fallback
- recent_days: 20

## KOSDAQ:SWING
- supabase_rows: 208 | scanner_origin_rows: 29 | matched_rows: 29
- supabase_runs: 27 | scanner_origin_runs: 14 | matched_runs: 14
- recent dates: ['2026-04-02', '2026-04-03', '2026-04-06', '2026-04-08', '2026-04-09', '2026-04-10', '2026-04-13']
- recent baseline positive-rate: 52.98% | avg return +0.23%
- recent overlay positive-rate: 52.98% | avg return +0.23%
- recent delta positive-rate: +0.00% | avg return +0.00% | hit5 +0.00%
- all-history baseline positive-rate: 52.98% | avg return +0.23%
- all-history overlay positive-rate: 52.98% | avg return +0.23%
- row origins: {'OUTCOME_ONLY': 146, 'PLANNER': 33, 'SCANNER': 29}
- overlay reasons: {'SEGMENT_KOSDAQ_SWING_T3_RISING_CLEAN_BONUS': 5, 'SEGMENT_KOSDAQ_SWING_RISING_CLEAN_CONFIRM': 5, 'SEGMENT_KOSDAQ_SWING_WEAK_T2_PENALTY': 3, 'SEGMENT_KOSDAQ_SWING_DIVERGENCE_BONUS': 2, 'SEGMENT_KOSDAQ_SWING_LEADER_CONTEXT_BONUS': 1, 'SEGMENT_KOSDAQ_SWING_T2_LOW_RANKER': 1}
- continuation reasons: {'ML_PROB_LT_27': 25, 'DECISION_SCORE_LT_78': 16, 'ALPHA_SCORE_LT_45': 2}
- quant reasons: {'KOSDAQ_QUANT_LATE_CHASE_PENALTY': 6, 'KOSDAQ_QUANT_3D_RISING_BONUS': 5, 'KOSDAQ_QUANT_T1_PEAK_FADE': 3}
- feature sources: {'shared_working': 29}

