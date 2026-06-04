alter table if exists public.market_scan_results
  add column if not exists leader_metrics jsonb,
  add column if not exists feature_snapshot jsonb;

comment on column public.market_scan_results.leader_metrics is
  'Scanner leader metrics payload, including KIS sidecar metadata when available.';

comment on column public.market_scan_results.feature_snapshot is
  'Full scanner feature snapshot payload for archive, planner, and KIS parity replay.';
