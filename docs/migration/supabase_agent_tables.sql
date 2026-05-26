-- Multi-agent persistence tables (additive)
-- Safe to run with existing legacy tables; no destructive operations.

create table if not exists public.agent_run_summaries (
  run_id text primary key,
  market text,
  strategy_version text,
  model_version text,
  code_version text,
  artifact_refs jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.agent_postmortems (
  run_id text primary key,
  market text,
  scope text,
  failure_summary text,
  likely_causes jsonb not null default '[]'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  produced_at timestamptz,
  created_at timestamptz not null default now(),
  constraint fk_agent_postmortems_run
    foreign key (run_id)
    references public.agent_run_summaries(run_id)
    on delete cascade
);

create table if not exists public.agent_improvement_tickets (
  ticket_id text primary key,
  run_id text,
  owner_agent text,
  owner_module text,
  title text,
  hypothesis text,
  requested_change text,
  priority text,
  status text,
  created_at timestamptz not null default now(),
  constraint fk_agent_tickets_run
    foreign key (run_id)
    references public.agent_run_summaries(run_id)
    on delete set null
);

create table if not exists public.agent_realized_outcomes (
  outcome_key text primary key,
  run_id text not null,
  ticker text not null,
  priority_rank integer,
  decision text,
  status text,
  horizon text,
  recommended_at timestamptz,
  realized_return_pct double precision,
  outcome_label text,
  outcome_recorded_at timestamptz,
  source_ref text,
  resolved_signal_created_at timestamptz,
  resolved_signal_type text,
  resolved_stock_name text,
  updated_at timestamptz not null default now(),
  constraint fk_agent_realized_outcomes_run
    foreign key (run_id)
    references public.agent_run_summaries(run_id)
    on delete cascade
);

create table if not exists public.agent_profile_diagnostics (
  run_id text primary key,
  market text,
  current_profile text,
  current_total_scans integer,
  current_result_count integer,
  current_top_reject_reason jsonb not null default '{}'::jsonb,
  profile_summary jsonb not null default '{}'::jsonb,
  flags jsonb not null default '{}'::jsonb,
  fallback_watchlist jsonb not null default '{}'::jsonb,
  generated_at timestamptz,
  created_at timestamptz not null default now(),
  constraint fk_agent_profile_diagnostics_run
    foreign key (run_id)
    references public.agent_run_summaries(run_id)
    on delete cascade
);

create table if not exists public.agent_outcome_health (
  run_id text primary key,
  market text,
  window_runs integer,
  runs_with_outcomes integer,
  outcomes_total integer,
  pending integer,
  resolved integer,
  expired integer,
  expired_rate double precision,
  fallback_total integer,
  fallback_pending integer,
  fallback_resolved integer,
  fallback_expired integer,
  fallback_expired_rate double precision,
  generated_at timestamptz,
  created_at timestamptz not null default now(),
  constraint fk_agent_outcome_health_run
    foreign key (run_id)
    references public.agent_run_summaries(run_id)
    on delete cascade
);

create index if not exists idx_agent_run_summaries_created_at
  on public.agent_run_summaries (created_at desc);

create index if not exists idx_agent_postmortems_created_at
  on public.agent_postmortems (created_at desc);

create index if not exists idx_agent_tickets_run_id
  on public.agent_improvement_tickets (run_id);

create index if not exists idx_agent_tickets_owner
  on public.agent_improvement_tickets (owner_agent);

create index if not exists idx_agent_tickets_status_priority
  on public.agent_improvement_tickets (status, priority);

create index if not exists idx_agent_realized_outcomes_run_id
  on public.agent_realized_outcomes (run_id);

create index if not exists idx_agent_realized_outcomes_status
  on public.agent_realized_outcomes (status);

create index if not exists idx_agent_realized_outcomes_ticker
  on public.agent_realized_outcomes (ticker);

alter table public.agent_realized_outcomes
  add column if not exists market text,
  add column if not exists decision_bucket text,
  add column if not exists strategy_family text,
  add column if not exists stock_name text,
  add column if not exists scan_mode text,
  add column if not exists quality_flags jsonb,
  add column if not exists validation_excluded boolean default false,
  add column if not exists base_trade_date date,
  add column if not exists entry_reference_price double precision,
  add column if not exists scan_entry_reference_price double precision,
  add column if not exists latest_return_pct double precision,
  add column if not exists return_10m_pct double precision,
  add column if not exists return_30m_pct double precision,
  add column if not exists return_1h_pct double precision,
  add column if not exists return_close_pct double precision,
  add column if not exists return_1d_pct double precision,
  add column if not exists return_2d_pct double precision,
  add column if not exists return_3d_pct double precision,
  add column if not exists return_5d_pct double precision,
  add column if not exists return_7d_pct double precision,
  add column if not exists return_14d_pct double precision,
  add column if not exists return_30d_pct double precision,
  add column if not exists mfe_intraday_pct double precision,
  add column if not exists mae_intraday_pct double precision,
  add column if not exists mfe_5d_pct double precision,
  add column if not exists mae_5d_pct double precision,
  add column if not exists target_before_stop_5d boolean,
  add column if not exists stop_before_target_5d boolean,
  add column if not exists target_hit_at_5d date,
  add column if not exists stop_hit_at_5d date,
  add column if not exists ordered_entry_at timestamptz,
  add column if not exists ordered_entry_price double precision,
  add column if not exists ordered_target_hit_at timestamptz,
  add column if not exists ordered_stop_hit_at timestamptz,
  add column if not exists ordered_mfe_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_before_target_5d_pct double precision,
  add column if not exists outcome_path_bar_count integer,
  add column if not exists outcome_path_source text,
  add column if not exists outcome_path_warnings jsonb,
  add column if not exists outcome_path_terminal_status text,
  add column if not exists outcome_path_label_version text,
  add column if not exists primary_theme text,
  add column if not exists theme_source text,
  add column if not exists theme_inference_status text,
  add column if not exists secondary_themes jsonb,
  add column if not exists theme_routing_path text,
  add column if not exists theme_score_adjustment double precision,
  add column if not exists theme_day_symbol_count double precision,
  add column if not exists theme_day_avg_alpha_score double precision,
  add column if not exists theme_day_avg_decision_score double precision,
  add column if not exists theme_day_avg_volume_ratio double precision,
  add column if not exists theme_day_avg_day_return_pct double precision,
  add column if not exists theme_day_positive_return_pct double precision,
  add column if not exists theme_day_strength_rank double precision,
  add column if not exists theme_day_strength_bucket text,
  add column if not exists regime_breadth_pct double precision,
  add column if not exists regime_avg_chg double precision,
  add column if not exists regime_volatility_20d double precision,
  add column if not exists kospi_chg double precision,
  add column if not exists kosdaq_chg double precision;

create index if not exists idx_agent_realized_outcomes_decision_bucket
  on public.agent_realized_outcomes (decision_bucket);

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
  primary_theme text,
  theme_source text,
  theme_inference_status text,
  secondary_themes jsonb,
  theme_routing_path text,
  theme_score_adjustment double precision,
  theme_day_symbol_count double precision,
  theme_day_avg_alpha_score double precision,
  theme_day_avg_decision_score double precision,
  theme_day_avg_volume_ratio double precision,
  theme_day_avg_day_return_pct double precision,
  theme_day_positive_return_pct double precision,
  theme_day_strength_rank double precision,
  theme_day_strength_bucket text,
  regime_breadth_pct double precision,
  regime_avg_chg double precision,
  regime_volatility_20d double precision,
  kospi_chg double precision,
  kosdaq_chg double precision,
  feature_snapshot jsonb,
  regime_theme_adjustment jsonb,
  candidate_data_quality jsonb default '{}'::jsonb,
  data_required_present_pct double precision,
  data_warning_level text,
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
  ordered_entry_at timestamptz,
  ordered_entry_price double precision,
  ordered_target_hit_at timestamptz,
  ordered_stop_hit_at timestamptz,
  ordered_mfe_until_terminal_5d_pct double precision,
  ordered_mae_until_terminal_5d_pct double precision,
  ordered_mae_before_target_5d_pct double precision,
  outcome_path_bar_count integer,
  outcome_path_source text,
  outcome_path_warnings jsonb,
  outcome_path_terminal_status text,
  outcome_path_label_version text,
  ledger_status text,
  source_ref text,
  updated_at timestamptz not null default now()
);

create index if not exists idx_post_scan_outcome_ledger_run_id
  on public.post_scan_outcome_ledger (run_id);

create index if not exists idx_post_scan_outcome_ledger_market_section
  on public.post_scan_outcome_ledger (market, scan_mode, section, ledger_status);

create index if not exists idx_post_scan_outcome_ledger_recommended_at
  on public.post_scan_outcome_ledger (recommended_at desc);

alter table public.post_scan_outcome_ledger
  add column if not exists primary_theme text,
  add column if not exists theme_source text,
  add column if not exists theme_inference_status text,
  add column if not exists secondary_themes jsonb,
  add column if not exists theme_routing_path text,
  add column if not exists theme_score_adjustment double precision,
  add column if not exists theme_day_symbol_count double precision,
  add column if not exists theme_day_avg_alpha_score double precision,
  add column if not exists theme_day_avg_decision_score double precision,
  add column if not exists theme_day_avg_volume_ratio double precision,
  add column if not exists theme_day_avg_day_return_pct double precision,
  add column if not exists theme_day_positive_return_pct double precision,
  add column if not exists theme_day_strength_rank double precision,
  add column if not exists theme_day_strength_bucket text,
  add column if not exists regime_breadth_pct double precision,
  add column if not exists regime_avg_chg double precision,
  add column if not exists regime_volatility_20d double precision,
  add column if not exists kospi_chg double precision,
  add column if not exists kosdaq_chg double precision,
  add column if not exists feature_snapshot jsonb,
  add column if not exists regime_theme_adjustment jsonb,
  add column if not exists candidate_data_quality jsonb default '{}'::jsonb,
  add column if not exists data_required_present_pct double precision,
  add column if not exists data_warning_level text;

create index if not exists idx_agent_profile_diagnostics_profile
  on public.agent_profile_diagnostics (current_profile);

create index if not exists idx_agent_profile_diagnostics_generated_at
  on public.agent_profile_diagnostics (generated_at desc);

create index if not exists idx_agent_outcome_health_generated_at
  on public.agent_outcome_health (generated_at desc);

create index if not exists idx_agent_outcome_health_market
  on public.agent_outcome_health (market);

-- Legacy scanner sink table required by DBManager.upsert_scan_result(...)
create table if not exists public.market_scan_results (
  id bigserial primary key,
  ticker text not null,
  stock_name text,
  alpha_score integer,
  tech_score integer,
  ml_prob double precision,
  whale_score integer,
  fund_status text,
  trend text,
  market_type text,
  created_at timestamptz not null default now(),
  tier text,
  volume text,
  day_return_pct double precision,
  context text,
  surge text,
  win_rate text,
  position text,
  strategy text,
  decision_score double precision
);

create index if not exists idx_market_scan_results_created_at
  on public.market_scan_results (created_at desc);

create index if not exists idx_market_scan_results_ticker_created_at
  on public.market_scan_results (ticker, created_at desc);

alter table public.market_scan_results
  add column if not exists run_id text,
  add column if not exists market text,
  add column if not exists scan_mode text,
  add column if not exists strategy_family text,
  add column if not exists priority_rank integer,
  add column if not exists decision text,
  add column if not exists decision_bucket text,
  add column if not exists quality_flags jsonb,
  add column if not exists validation_excluded boolean default false,
  add column if not exists outcome_status text,
  add column if not exists recommended_at timestamptz,
  add column if not exists outcome_recorded_at timestamptz,
  add column if not exists horizon text,
  add column if not exists base_trade_date date,
  add column if not exists entry_reference_price double precision,
  add column if not exists scan_entry_reference_price double precision,
  add column if not exists day_return_pct double precision,
  add column if not exists latest_return_pct double precision,
  add column if not exists return_10m_pct double precision,
  add column if not exists return_30m_pct double precision,
  add column if not exists return_1h_pct double precision,
  add column if not exists return_close_pct double precision,
  add column if not exists return_1d_pct double precision,
  add column if not exists return_2d_pct double precision,
  add column if not exists return_3d_pct double precision,
  add column if not exists return_5d_pct double precision,
  add column if not exists return_7d_pct double precision,
  add column if not exists return_14d_pct double precision,
  add column if not exists return_30d_pct double precision,
  add column if not exists mfe_intraday_pct double precision,
  add column if not exists mae_intraday_pct double precision,
  add column if not exists mfe_5d_pct double precision,
  add column if not exists mae_5d_pct double precision,
  add column if not exists target_before_stop_5d boolean,
  add column if not exists stop_before_target_5d boolean,
  add column if not exists target_hit_at_5d date,
  add column if not exists stop_hit_at_5d date,
  add column if not exists ordered_entry_at timestamptz,
  add column if not exists ordered_entry_price double precision,
  add column if not exists ordered_target_hit_at timestamptz,
  add column if not exists ordered_stop_hit_at timestamptz,
  add column if not exists ordered_mfe_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_before_target_5d_pct double precision,
  add column if not exists outcome_path_bar_count integer,
  add column if not exists outcome_path_source text,
  add column if not exists outcome_path_warnings jsonb,
  add column if not exists outcome_path_terminal_status text,
  add column if not exists outcome_path_label_version text,
  add column if not exists source_ref text,
  add column if not exists phase25_variant text,
  add column if not exists phase25_shadow_variant text,
  add column if not exists phase25_shadow_prob double precision,
  add column if not exists phase25_recommended_threshold double precision,
  add column if not exists expected_edge_score double precision,
  add column if not exists expected_return_1d_pct double precision,
  add column if not exists expected_return_3d_pct double precision,
  add column if not exists model_prob_available_count double precision,
  add column if not exists model_prob_mean double precision,
  add column if not exists low_model_prob_score double precision,
  add column if not exists low_prob_high_score double precision,
  add column if not exists expected_edge_inversion_score double precision,
  add column if not exists loss_risk_score double precision,
  add column if not exists relative_rank_score double precision,
  add column if not exists relative_rank_pct double precision,
  add column if not exists regime_adjusted_grade text,
  add column if not exists relative_rank_model text,
  add column if not exists primary_theme text,
  add column if not exists theme_source text,
  add column if not exists theme_inference_status text,
  add column if not exists secondary_themes jsonb,
  add column if not exists theme_routing_path text,
  add column if not exists foreigner double precision,
  add column if not exists foreign_flow double precision,
  add column if not exists institution double precision,
  add column if not exists institution_flow double precision,
  add column if not exists retail double precision,
  add column if not exists retail_flow double precision,
  add column if not exists flow_consensus_buying boolean,
  add column if not exists retail_dominant boolean,
  add column if not exists dominant text,
  add column if not exists whale_trend text,
  add column if not exists rationale jsonb,
  add column if not exists theme_risk jsonb;

create index if not exists idx_market_scan_results_run_id
  on public.market_scan_results (run_id);

create index if not exists idx_market_scan_results_decision_bucket
  on public.market_scan_results (decision_bucket);

-- Legacy signal table required by DBManager.save_signal/update_performance
create table if not exists public.signals (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  ticker text not null,
  stock_name text,
  price double precision,
  alpha_score integer,
  ai_prediction double precision,
  signal_type text,
  result_3d double precision,
  entry_price double precision,
  target_price double precision,
  stop_loss double precision
);

create index if not exists idx_signals_created_at
  on public.signals (created_at desc);

create index if not exists idx_signals_ticker_created_at
  on public.signals (ticker, created_at desc);

-- Real-data paper/live shadow execution ledger.
-- This stores trade-like validation rows derived from actual recommendations
-- and realized outcome columns. It does not fabricate broker fills.
create table if not exists public.paper_trade_ledger (
  trade_id text primary key,
  ledger_mode text not null,
  ticker text not null,
  stock_name text,
  market text,
  scan_mode text,
  run_id text,
  priority_rank integer,
  decision text,
  decision_bucket text,
  recommended_at timestamptz,
  base_trade_date date,
  entry_model text,
  entry_reference_price double precision,
  target_tp_pct double precision,
  stop_sl_pct double precision,
  hold_days integer,
  exit_day integer,
  exit_reason text,
  trade_status text,
  gross_return_pct double precision,
  net_return_pct double precision,
  fee_bps double precision,
  slippage_bps double precision,
  relative_rank_score double precision,
  loss_risk_score double precision,
  relative_rank_model text,
  source_scan_result_id text,
  data_warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_paper_trade_ledger_market_status
  on public.paper_trade_ledger (market, scan_mode, trade_status);

create index if not exists idx_paper_trade_ledger_recommended_at
  on public.paper_trade_ledger (recommended_at desc);

create index if not exists idx_paper_trade_ledger_run_id
  on public.paper_trade_ledger (run_id);

-- Auto-generated Top candidate deep analysis reports. One row per run/ticker.
create table if not exists public.scan_deep_reports (
  report_id text primary key,
  report_version text not null,
  run_id text not null,
  market text,
  scan_mode text,
  rank integer,
  ticker text not null,
  stock_name text,
  generated_at timestamptz not null default now(),
  signal_label text,
  decision text,
  decision_bucket text,
  buy_score double precision,
  accuracy double precision,
  day_change_pct double precision,
  loss_risk_score double precision,
  selection_alignment jsonb default '{}'::jsonb,
  risk_flags jsonb default '[]'::jsonb,
  rationale jsonb default '[]'::jsonb,
  prediction jsonb default '{}'::jsonb,
  selection_thesis jsonb default '{}'::jsonb,
  risk_overrides jsonb default '{}'::jsonb,
  display_contract jsonb default '{}'::jsonb,
  candidate_data_quality jsonb default '{}'::jsonb,
  candidate_interpretation jsonb default '{}'::jsonb,
  policy_metadata jsonb default '{}'::jsonb,
  realized_expectancy_admission jsonb default '{}'::jsonb,
  entry_action jsonb default '{}'::jsonb,
  practical_entry_gate jsonb default '{}'::jsonb,
  trade_plan jsonb default '{}'::jsonb,
  flow jsonb default '{}'::jsonb,
  theme jsonb default '{}'::jsonb,
  price jsonb default '{}'::jsonb,
  news jsonb default '{}'::jsonb,
  data_warnings jsonb default '[]'::jsonb
);

create index if not exists idx_scan_deep_reports_generated_at
  on public.scan_deep_reports (generated_at desc);

create index if not exists idx_scan_deep_reports_run_rank
  on public.scan_deep_reports (run_id, rank);

create index if not exists idx_scan_deep_reports_ticker_generated_at
  on public.scan_deep_reports (ticker, generated_at desc);

alter table public.scan_deep_reports
  add column if not exists selection_alignment jsonb default '{}'::jsonb,
  add column if not exists selection_thesis jsonb default '{}'::jsonb,
  add column if not exists risk_overrides jsonb default '{}'::jsonb,
  add column if not exists display_contract jsonb default '{}'::jsonb,
  add column if not exists candidate_data_quality jsonb default '{}'::jsonb,
  add column if not exists candidate_interpretation jsonb default '{}'::jsonb,
  add column if not exists policy_metadata jsonb default '{}'::jsonb,
  add column if not exists realized_expectancy_admission jsonb default '{}'::jsonb,
  add column if not exists entry_action jsonb default '{}'::jsonb,
  add column if not exists practical_entry_gate jsonb default '{}'::jsonb,
  add column if not exists flow jsonb default '{}'::jsonb;
