alter table public.scan_deep_reports
  add column if not exists scan_universe_admission jsonb default '{}'::jsonb;
