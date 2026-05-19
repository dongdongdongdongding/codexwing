alter table public.agent_realized_outcomes
  add column if not exists scan_entry_reference_price double precision;

alter table public.market_scan_results
  add column if not exists scan_entry_reference_price double precision;
