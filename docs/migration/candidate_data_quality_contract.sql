alter table public.scan_deep_reports
  add column if not exists candidate_data_quality jsonb default '{}'::jsonb;

alter table public.post_scan_outcome_ledger
  add column if not exists candidate_data_quality jsonb default '{}'::jsonb,
  add column if not exists data_required_present_pct double precision,
  add column if not exists data_warning_level text;
