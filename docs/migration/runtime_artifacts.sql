create table if not exists public.runtime_artifacts (
    id bigserial primary key,
    run_id text not null,
    artifact_key text not null,
    artifact_type text not null default 'runtime_json',
    market text,
    scan_mode text,
    source text,
    source_path text,
    content_type text not null default 'application/json',
    payload jsonb,
    content_text text,
    payload_rows integer,
    size_bytes bigint,
    checksum text,
    metadata jsonb not null default '{}'::jsonb,
    artifact_version text not null default 'runtime_artifact_v1',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (run_id, artifact_key)
);

create index if not exists runtime_artifacts_run_id_idx
    on public.runtime_artifacts (run_id);

create index if not exists runtime_artifacts_key_idx
    on public.runtime_artifacts (artifact_key);

create index if not exists runtime_artifacts_market_updated_idx
    on public.runtime_artifacts (market, updated_at desc);

-- Payload is retained as JSONB for exact recovery, but operational reads use
-- run_id/artifact_key/market indexes. A payload GIN index makes large run JSON
-- backfills prone to Supabase statement timeouts, so keep it disabled unless a
-- future query pattern explicitly needs JSON path search.
drop index if exists public.runtime_artifacts_payload_gin_idx;
