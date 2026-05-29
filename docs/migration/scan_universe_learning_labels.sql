-- Learning labels and feature/flow quality fields for scan_universe_snapshots.
--
-- These columns make model training independent from selected scan outputs by
-- storing forward path labels for every emitted and rejected scan-universe row.

alter table public.scan_universe_snapshots
add column if not exists min_low_return_1d_pct double precision,
add column if not exists min_low_return_3d_pct double precision,
add column if not exists min_low_return_5d_pct double precision,
add column if not exists target_hit_1d boolean,
add column if not exists target_hit_3d boolean,
add column if not exists target_hit_5d boolean,
add column if not exists stop_hit_1d boolean,
add column if not exists stop_hit_3d boolean,
add column if not exists stop_hit_5d boolean,
add column if not exists target_before_stop_1d boolean,
add column if not exists target_before_stop_3d boolean,
add column if not exists target_before_stop_5d boolean,
add column if not exists stop_before_target_1d boolean,
add column if not exists stop_before_target_3d boolean,
add column if not exists stop_before_target_5d boolean,
add column if not exists target_hit_at_1d date,
add column if not exists target_hit_at_3d date,
add column if not exists target_hit_at_5d date,
add column if not exists stop_hit_at_1d date,
add column if not exists stop_hit_at_3d date,
add column if not exists stop_hit_at_5d date,
add column if not exists days_to_target_1d integer,
add column if not exists days_to_target_3d integer,
add column if not exists days_to_target_5d integer,
add column if not exists days_to_stop_1d integer,
add column if not exists days_to_stop_3d integer,
add column if not exists days_to_stop_5d integer,
add column if not exists first_touch_1d text,
add column if not exists first_touch_3d text,
add column if not exists first_touch_5d text,
add column if not exists label_target_pct double precision,
add column if not exists label_stop_pct double precision,
add column if not exists path_label_version text,
add column if not exists path_label_source text,
add column if not exists path_label_updated_at timestamptz,
add column if not exists whale_flow_1d double precision,
add column if not exists whale_flow_3d double precision,
add column if not exists whale_flow_10d double precision,
add column if not exists flow_source text,
add column if not exists flow_unit text,
add column if not exists flow_asof text,
add column if not exists flow_warnings jsonb not null default '[]'::jsonb,
add column if not exists flow_consensus_buying boolean,
add column if not exists retail_dominant boolean,
add column if not exists dominant text,
add column if not exists whale_trend text,
add column if not exists feature_coverage_score double precision,
add column if not exists feature_missing_keys jsonb not null default '[]'::jsonb,
add column if not exists has_actual_flow boolean,
add column if not exists normalized_feature_version text;

create index if not exists idx_scan_universe_snapshots_path_label
  on public.scan_universe_snapshots (market, base_trade_date desc, target_hit_5d, stop_hit_5d);

create index if not exists idx_scan_universe_snapshots_feature_coverage
  on public.scan_universe_snapshots (market, feature_coverage_score desc);
