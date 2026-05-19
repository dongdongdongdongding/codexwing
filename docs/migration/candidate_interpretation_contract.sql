alter table public.scan_deep_reports
  add column if not exists candidate_interpretation jsonb default '{}'::jsonb;
