alter table public.scan_deep_reports
  add column if not exists realized_expectancy_admission jsonb default '{}'::jsonb;
