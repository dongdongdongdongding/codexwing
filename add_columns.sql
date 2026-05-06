-- Run this in your Supabase SQL Editor:
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS tier text,
ADD COLUMN IF NOT EXISTS volume text,
ADD COLUMN IF NOT EXISTS context text,
ADD COLUMN IF NOT EXISTS surge text,
ADD COLUMN IF NOT EXISTS win_rate text,
ADD COLUMN IF NOT EXISTS position text,
ADD COLUMN IF NOT EXISTS strategy text,
ADD COLUMN IF NOT EXISTS decision_score numeric;

-- Added 2026-04-22 for ML inference propagation, exit rule fields, and regime flags
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS inference_failed boolean,
ADD COLUMN IF NOT EXISTS target_tp_pct numeric,
ADD COLUMN IF NOT EXISTS stop_sl_pct numeric,
ADD COLUMN IF NOT EXISTS hold_days integer,
ADD COLUMN IF NOT EXISTS regime_volatility_20d numeric,
ADD COLUMN IF NOT EXISTS regime_breadth_pct numeric,
ADD COLUMN IF NOT EXISTS kosdaq_chg numeric,
ADD COLUMN IF NOT EXISTS regime_avg_chg numeric;

-- Added 2026-04-23 for scanner feature provenance and no-dummy training gates.
-- Scanner rows must persist real measured feature values; incomplete/outcome-sync
-- rows are marked so they cannot silently train as zero-filled examples.
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS volume_ratio numeric,
ADD COLUMN IF NOT EXISTS volume_confirmed boolean,
ADD COLUMN IF NOT EXISTS prob_clean numeric,
ADD COLUMN IF NOT EXISTS model_trace_status text,
ADD COLUMN IF NOT EXISTS model_error text,
ADD COLUMN IF NOT EXISTS feature_origin text,
ADD COLUMN IF NOT EXISTS feature_quality text,
ADD COLUMN IF NOT EXISTS feature_completeness numeric,
ADD COLUMN IF NOT EXISTS feature_missing_fields jsonb,
ADD COLUMN IF NOT EXISTS validation_excluded_reason text,
ADD COLUMN IF NOT EXISTS is_dummy_data boolean DEFAULT false;

-- Added 2026-04-29 for phase25 model probability + signal direction + OOS metrics.
-- The scanner emits these in db_payload but Supabase had no matching columns,
-- so _filter_payload_to_existing_columns silently dropped them. Result: the
-- archive could not tell which model output produced the user-facing pick,
-- which bundle variant was used, or whether OOS validation passed — every
-- downstream training run, drift dashboard, and scan↔archive parity check
-- was reading partial truth. Adding these closes the silent-drop path.
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS phase25_prob numeric,
ADD COLUMN IF NOT EXISTS phase25_signal_direction text,
ADD COLUMN IF NOT EXISTS phase25_raw_auc numeric,
ADD COLUMN IF NOT EXISTS phase25_oos_auc numeric,
ADD COLUMN IF NOT EXISTS phase25_oos_win_rate_pct numeric,
ADD COLUMN IF NOT EXISTS phase25_oos_avg_return_pct numeric,
ADD COLUMN IF NOT EXISTS performance_updated_at timestamptz;

-- Added 2026-05-06 for planner gate-rationale traceability (swing-main-h4x).
-- swing-main-9e9 surfaced 14 days of zero PRIORITY_WATCHLIST picks; root cause
-- was explicit KR Phase25/expected-edge gates, but the DB had no columns to
-- explain WHY each candidate was admitted/rejected without re-reading local
-- planner_handoff.json artifacts. SCAN_RESULT_COLUMNS already mapped
-- market_gate/scanner_timeframe_profile/kr_universe_role, but
-- _filter_payload_to_existing_columns dropped them silently because the
-- physical columns never existed. rationale + theme_risk + selection_lane were
-- not even mapped — they live only in planner_handoff.json. Adding all six
-- closes the trace gap so DB-only priority_watchlist_gap reports can name the
-- gate cause.
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS market_gate text,
ADD COLUMN IF NOT EXISTS scanner_timeframe_profile text,
ADD COLUMN IF NOT EXISTS kr_universe_role text,
ADD COLUMN IF NOT EXISTS selection_lane text,
ADD COLUMN IF NOT EXISTS rationale jsonb,
ADD COLUMN IF NOT EXISTS theme_risk jsonb;
