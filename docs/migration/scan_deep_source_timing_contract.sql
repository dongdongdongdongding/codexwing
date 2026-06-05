alter table public.scan_deep_reports
  add column if not exists scan_as_of timestamptz,
  add column if not exists deep_analysis_as_of timestamptz,
  add column if not exists source_timing jsonb default '{}'::jsonb,
  add column if not exists scan_source_snapshot jsonb default '{}'::jsonb,
  add column if not exists deep_analysis_source_snapshot jsonb default '{}'::jsonb;

create index if not exists idx_scan_deep_reports_scan_as_of
  on public.scan_deep_reports (scan_as_of desc);
