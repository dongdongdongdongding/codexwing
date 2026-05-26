alter table public.agent_realized_outcomes
  add column if not exists ordered_entry_at timestamptz,
  add column if not exists ordered_entry_price double precision,
  add column if not exists ordered_target_hit_at timestamptz,
  add column if not exists ordered_stop_hit_at timestamptz,
  add column if not exists ordered_mfe_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_before_target_5d_pct double precision,
  add column if not exists outcome_path_bar_count integer,
  add column if not exists outcome_path_source text,
  add column if not exists outcome_path_warnings jsonb;

alter table public.market_scan_results
  add column if not exists ordered_entry_at timestamptz,
  add column if not exists ordered_entry_price double precision,
  add column if not exists ordered_target_hit_at timestamptz,
  add column if not exists ordered_stop_hit_at timestamptz,
  add column if not exists ordered_mfe_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_before_target_5d_pct double precision,
  add column if not exists outcome_path_bar_count integer,
  add column if not exists outcome_path_source text,
  add column if not exists outcome_path_warnings jsonb;

alter table public.post_scan_outcome_ledger
  add column if not exists ordered_entry_at timestamptz,
  add column if not exists ordered_entry_price double precision,
  add column if not exists ordered_target_hit_at timestamptz,
  add column if not exists ordered_stop_hit_at timestamptz,
  add column if not exists ordered_mfe_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_until_terminal_5d_pct double precision,
  add column if not exists ordered_mae_before_target_5d_pct double precision,
  add column if not exists outcome_path_bar_count integer,
  add column if not exists outcome_path_source text,
  add column if not exists outcome_path_warnings jsonb;
