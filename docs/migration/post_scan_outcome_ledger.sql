create table if not exists public.post_scan_outcome_ledger (
  ledger_key text primary key,
  ledger_version text not null,
  run_id text not null,
  ticker text not null,
  stock_name text,
  market text,
  scan_mode text,
  strategy_family text,
  section text,
  section_rank integer,
  priority_rank integer,
  decision text,
  decision_bucket text,
  recommended_at timestamptz,
  base_trade_date date,
  scan_entry_reference_price double precision,
  entry_reference_price double precision,
  target_tp_pct double precision,
  stop_sl_pct double precision,
  hold_days integer,
  market_gate text,
  scanner_timeframe_profile text,
  kr_universe_role text,
  selection_lane text,
  relative_rank_score double precision,
  loss_risk_score double precision,
  return_10m_pct double precision,
  return_30m_pct double precision,
  return_1h_pct double precision,
  return_close_pct double precision,
  return_1d_pct double precision,
  return_3d_pct double precision,
  return_5d_pct double precision,
  mfe_intraday_pct double precision,
  mae_intraday_pct double precision,
  mfe_5d_pct double precision,
  mae_5d_pct double precision,
  target_before_stop_5d boolean,
  stop_before_target_5d boolean,
  target_hit_at_5d date,
  stop_hit_at_5d date,
  outcome_path_terminal_status text,
  outcome_path_label_version text,
  ledger_status text,
  source_ref text,
  updated_at timestamptz not null default now()
);

alter table public.agent_realized_outcomes
  add column if not exists return_10m_pct double precision,
  add column if not exists mfe_intraday_pct double precision,
  add column if not exists mae_intraday_pct double precision,
  add column if not exists mfe_5d_pct double precision,
  add column if not exists mae_5d_pct double precision,
  add column if not exists target_before_stop_5d boolean,
  add column if not exists stop_before_target_5d boolean,
  add column if not exists target_hit_at_5d date,
  add column if not exists stop_hit_at_5d date,
  add column if not exists outcome_path_terminal_status text,
  add column if not exists outcome_path_label_version text;

alter table public.market_scan_results
  add column if not exists return_10m_pct double precision,
  add column if not exists mfe_intraday_pct double precision,
  add column if not exists mae_intraday_pct double precision,
  add column if not exists mfe_5d_pct double precision,
  add column if not exists mae_5d_pct double precision,
  add column if not exists target_before_stop_5d boolean,
  add column if not exists stop_before_target_5d boolean,
  add column if not exists target_hit_at_5d date,
  add column if not exists stop_hit_at_5d date,
  add column if not exists outcome_path_terminal_status text,
  add column if not exists outcome_path_label_version text;

create index if not exists idx_post_scan_outcome_ledger_run_id
  on public.post_scan_outcome_ledger (run_id);

create index if not exists idx_post_scan_outcome_ledger_market_section
  on public.post_scan_outcome_ledger (market, scan_mode, section, ledger_status);

create index if not exists idx_post_scan_outcome_ledger_recommended_at
  on public.post_scan_outcome_ledger (recommended_at desc);
