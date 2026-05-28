-- Full-universe scan snapshots for independent KR model research.
--
-- market_scan_results is intentionally candidate/archive oriented. This table
-- stores every symbol considered by a scan run, including rejected symbols, so
-- challenger models can be trained outside the production scanner's selected
-- output distribution.

create table if not exists public.scan_universe_snapshots (
  id bigserial primary key,
  snapshot_key text not null unique,
  run_id text not null,
  ticker text not null,
  stock_name text,
  market text,
  scan_mode text,
  base_trade_date date,
  scanned_at timestamptz,
  row_role text not null default 'unknown',
  passed_current_model boolean not null default false,
  priority_rank integer,
  decision text,
  decision_bucket text,
  reject_stage text,
  reject_reason text,
  reject_reason_codes jsonb not null default '[]'::jsonb,
  reject_detail_history jsonb not null default '[]'::jsonb,
  feature_snapshot jsonb not null default '{}'::jsonb,
  feature_origin text,
  source_ref text,
  total_scans integer,
  filtered_count integer,
  alpha_score double precision,
  tech_score double precision,
  ml_prob double precision,
  prob_clean double precision,
  whale_score double precision,
  decision_score double precision,
  day_return_pct double precision,
  volume_ratio double precision,
  turnover double precision,
  foreigner_1d double precision,
  institution_1d double precision,
  retail_1d double precision,
  foreigner_3d double precision,
  institution_3d double precision,
  retail_3d double precision,
  foreigner_10d double precision,
  institution_10d double precision,
  retail_10d double precision,
  primary_theme text,
  theme_source text,
  theme_inference_status text,
  kr_universe_role text,
  scanner_timeframe_profile text,
  entry_reference_price double precision,
  return_1d_pct double precision,
  return_3d_pct double precision,
  return_5d_pct double precision,
  max_high_return_1d_pct double precision,
  max_high_return_3d_pct double precision,
  max_high_return_5d_pct double precision,
  outcome_available boolean not null default false,
  outcome_source text,
  backfill_version text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_scan_universe_snapshots_run_id
  on public.scan_universe_snapshots (run_id);

create index if not exists idx_scan_universe_snapshots_ticker_date
  on public.scan_universe_snapshots (ticker, base_trade_date desc);

create index if not exists idx_scan_universe_snapshots_market_date
  on public.scan_universe_snapshots (market, base_trade_date desc);

create index if not exists idx_scan_universe_snapshots_role
  on public.scan_universe_snapshots (row_role, passed_current_model);

create index if not exists idx_scan_universe_snapshots_reject_reason
  on public.scan_universe_snapshots (reject_reason);
