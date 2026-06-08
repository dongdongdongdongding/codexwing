create table if not exists public.kis_ticker_category_daily (
  category_key text primary key,
  trade_date date not null,
  market_scope text not null,
  ticker text not null,
  stock_name text,
  primary_theme text,
  secondary_themes jsonb default '[]'::jsonb,
  theme_source text,
  theme_routing_path text,
  sector_name text,
  standard_industry_code text,
  market_name text,
  market_code text,
  large_sector_name text,
  mid_sector_name text,
  small_sector_name text,
  stock_type text,
  kospi200_item text,
  listed_date text,
  per numeric,
  pbr numeric,
  roe numeric,
  debt_ratio numeric,
  revenue_growth_rate numeric,
  value_traded numeric,
  day_return_pct numeric,
  volume_rank numeric,
  fluctuation_rank numeric,
  volume_power_rank numeric,
  vi_triggered boolean default false,
  news_count integer default 0,
  raw_news_count integer default 0,
  news_positive_tags jsonb default '[]'::jsonb,
  news_risk_tags jsonb default '[]'::jsonb,
  news_source_scope text,
  kis_evidence_strength_score numeric,
  kis_evidence_strength_level text,
  source_ref text,
  payload jsonb not null default '{}'::jsonb,
  no_dummy_data boolean not null default true,
  generated_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_kis_ticker_category_daily_trade_market
  on public.kis_ticker_category_daily (trade_date desc, market_scope, primary_theme);

create index if not exists idx_kis_ticker_category_daily_ticker
  on public.kis_ticker_category_daily (ticker, trade_date desc);

create table if not exists public.kis_theme_daily_state (
  theme_state_key text primary key,
  trade_date date not null,
  market_scope text not null,
  theme_name text not null,
  symbol_count integer not null default 0,
  avg_day_return_pct numeric,
  positive_return_ratio numeric,
  total_value_traded numeric,
  news_count integer not null default 0,
  vi_triggered_count integer not null default 0,
  avg_kis_evidence_strength_score numeric,
  top_symbols jsonb default '[]'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  no_dummy_data boolean not null default true,
  generated_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_kis_theme_daily_state_trade_market
  on public.kis_theme_daily_state (trade_date desc, market_scope, theme_name);

create table if not exists public.kis_valuechain_evidence (
  evidence_key text primary key,
  from_symbol text not null,
  to_symbol text not null,
  relationship text not null,
  theme_name text,
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  source_type text not null,
  source_urls jsonb not null default '[]'::jsonb,
  source_title text,
  evidence_text text not null,
  evidence_collected_at timestamptz,
  production_valuechain boolean not null default false,
  blocked_reasons jsonb not null default '[]'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  no_dummy_data boolean not null default true,
  generated_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint kis_valuechain_production_confidence_check
    check (production_valuechain = false or confidence >= 0.95),
  constraint kis_valuechain_source_url_check
    check (production_valuechain = false or jsonb_array_length(source_urls) > 0)
);

create index if not exists idx_kis_valuechain_evidence_symbols
  on public.kis_valuechain_evidence (from_symbol, to_symbol, relationship);

create index if not exists idx_kis_valuechain_evidence_production
  on public.kis_valuechain_evidence (production_valuechain, confidence desc);

create table if not exists public.kis_theme_network_edges (
  edge_key text primary key,
  market_scope text not null,
  source_node text not null,
  target_node text not null,
  edge_kind text not null,
  relationship text not null,
  confidence numeric not null check (confidence >= 0 and confidence <= 1),
  weight numeric not null default 1,
  production_valuechain boolean not null default false,
  source_type text,
  source_urls jsonb default '[]'::jsonb,
  evidence jsonb default '[]'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  no_dummy_data boolean not null default true,
  generated_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint kis_theme_network_production_confidence_check
    check (production_valuechain = false or confidence >= 0.95)
);

create index if not exists idx_kis_theme_network_edges_market_kind
  on public.kis_theme_network_edges (market_scope, edge_kind, confidence desc);
