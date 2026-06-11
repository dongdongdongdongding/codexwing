-- Exact operational-entry labels for scan_universe_snapshots.
--
-- Existing path labels use the scan reference entry. These columns store the
-- stricter real-buy assumption used for operation review: entry happens 2%
-- above the scan reference, then target/stop ordering is evaluated from OHLC.

alter table public.scan_universe_snapshots
add column if not exists operational_buy_premium_pct double precision,
add column if not exists buy_premium_entry_price double precision,
add column if not exists buy_premium_return_1d_pct double precision,
add column if not exists buy_premium_return_3d_pct double precision,
add column if not exists buy_premium_return_5d_pct double precision,
add column if not exists buy_premium_max_high_return_1d_pct double precision,
add column if not exists buy_premium_max_high_return_3d_pct double precision,
add column if not exists buy_premium_max_high_return_5d_pct double precision,
add column if not exists buy_premium_min_low_return_1d_pct double precision,
add column if not exists buy_premium_min_low_return_3d_pct double precision,
add column if not exists buy_premium_min_low_return_5d_pct double precision,
add column if not exists buy_premium_target_hit_1d boolean,
add column if not exists buy_premium_target_hit_3d boolean,
add column if not exists buy_premium_target_hit_5d boolean,
add column if not exists buy_premium_stop_hit_1d boolean,
add column if not exists buy_premium_stop_hit_3d boolean,
add column if not exists buy_premium_stop_hit_5d boolean,
add column if not exists buy_premium_target_before_stop_1d boolean,
add column if not exists buy_premium_target_before_stop_3d boolean,
add column if not exists buy_premium_target_before_stop_5d boolean,
add column if not exists buy_premium_stop_before_target_1d boolean,
add column if not exists buy_premium_stop_before_target_3d boolean,
add column if not exists buy_premium_stop_before_target_5d boolean,
add column if not exists buy_premium_target_hit_at_1d date,
add column if not exists buy_premium_target_hit_at_3d date,
add column if not exists buy_premium_target_hit_at_5d date,
add column if not exists buy_premium_stop_hit_at_1d date,
add column if not exists buy_premium_stop_hit_at_3d date,
add column if not exists buy_premium_stop_hit_at_5d date,
add column if not exists buy_premium_days_to_target_1d integer,
add column if not exists buy_premium_days_to_target_3d integer,
add column if not exists buy_premium_days_to_target_5d integer,
add column if not exists buy_premium_days_to_stop_1d integer,
add column if not exists buy_premium_days_to_stop_3d integer,
add column if not exists buy_premium_days_to_stop_5d integer,
add column if not exists buy_premium_first_touch_1d text,
add column if not exists buy_premium_first_touch_3d text,
add column if not exists buy_premium_first_touch_5d text,
add column if not exists buy_premium_label_target_pct double precision,
add column if not exists buy_premium_label_stop_pct double precision,
add column if not exists buy_premium_path_label_version text,
add column if not exists buy_premium_path_label_source text,
add column if not exists buy_premium_path_label_updated_at timestamptz;

create index if not exists idx_scan_universe_snapshots_buy_premium_path
  on public.scan_universe_snapshots (
    market,
    base_trade_date desc,
    buy_premium_target_before_stop_5d,
    buy_premium_stop_before_target_5d
  );
