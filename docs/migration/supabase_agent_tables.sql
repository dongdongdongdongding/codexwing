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
  add column if not exists latest_return_pct double precision,
  add column if not exists return_30m_pct double precision,
  add column if not exists return_1h_pct double precision,
  add column if not exists return_close_pct double precision,
  add column if not exists return_1d_pct double precision,
  add column if not exists return_2d_pct double precision,
  add column if not exists return_3d_pct double precision,
  add column if not exists return_5d_pct double precision,
  add column if not exists return_7d_pct double precision,
  add column if not exists return_14d_pct double precision,
  add column if not exists return_30d_pct double precision;

create index if not exists idx_agent_realized_outcomes_decision_bucket
  on public.agent_realized_outcomes (decision_bucket);

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
  add column if not exists day_return_pct double precision,
  add column if not exists latest_return_pct double precision,
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
  add column if not exists theme_routing_path text;

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
