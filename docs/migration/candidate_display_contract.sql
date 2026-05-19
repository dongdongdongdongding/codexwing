alter table public.scan_deep_reports
  add column if not exists display_contract jsonb default '{}'::jsonb;
