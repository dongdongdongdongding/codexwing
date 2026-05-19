alter table public.scan_deep_reports
  add column if not exists policy_metadata jsonb default '{}'::jsonb;
