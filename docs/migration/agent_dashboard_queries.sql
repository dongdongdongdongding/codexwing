-- Agent Dashboard SQL Templates (Supabase SQL Editor)
-- 목적: fallback watchlist / realized outcomes 만료·해결 상태를 운영 관점에서 추적

-- 1) 최근 실행별 fallback 상태 요약
select
  d.run_id,
  d.market,
  d.current_profile,
  d.generated_at,
  sum(case when o.decision = 'FALLBACK_WATCHLIST' then 1 else 0 end) as fallback_total,
  sum(case when o.decision = 'FALLBACK_WATCHLIST' and o.status = 'PENDING' then 1 else 0 end) as fallback_pending,
  sum(case when o.decision = 'FALLBACK_WATCHLIST' and o.status = 'RESOLVED' then 1 else 0 end) as fallback_resolved,
  sum(case when o.decision = 'FALLBACK_WATCHLIST' and o.status = 'EXPIRED' then 1 else 0 end) as fallback_expired
from public.agent_profile_diagnostics d
left join public.agent_realized_outcomes o
  on o.run_id = d.run_id
where d.market = 'NASDAQ'
group by d.run_id, d.market, d.current_profile, d.generated_at
order by d.generated_at desc
limit 100;

-- 2) horizon 경과했는데 아직 pending인 stale fallback 후보
select
  o.run_id,
  o.ticker,
  o.status,
  o.horizon,
  o.recommended_at,
  now() as inspected_at
from public.agent_realized_outcomes o
where o.decision = 'FALLBACK_WATCHLIST'
  and o.status = 'PENDING'
  and o.recommended_at is not null
  and now() >= (
    o.recommended_at
    + make_interval(
      days => coalesce(
        nullif(regexp_replace(coalesce(o.horizon, 'T+3D'), '[^0-9]', '', 'g'), '')::int,
        3
      )
    )
  )
order by o.recommended_at asc
limit 200;

-- 3) 일자별 결과 closure 추이 (resolved + expired)
select
  date_trunc('day', coalesce(o.recommended_at, o.updated_at))::date as day,
  count(*) as outcomes_total,
  sum(case when o.status = 'PENDING' then 1 else 0 end) as pending_count,
  sum(case when o.status = 'RESOLVED' then 1 else 0 end) as resolved_count,
  sum(case when o.status = 'EXPIRED' then 1 else 0 end) as expired_count,
  round(
    100.0 * (
      sum(case when o.status in ('RESOLVED', 'EXPIRED') then 1 else 0 end)::numeric
      / nullif(count(*), 0)::numeric
    ),
    2
  ) as closure_rate_pct
from public.agent_realized_outcomes o
group by 1
order by 1 desc
limit 60;

-- 4) profile 진단 + fallback 적용 여부 추적
select
  d.run_id,
  d.market,
  d.current_profile,
  d.generated_at,
  (d.flags ->> 'prod_dev_gap')::boolean as prod_dev_gap,
  (d.flags ->> 'prod_zero_streak_alert')::boolean as prod_zero_streak_alert,
  coalesce((d.fallback_watchlist ->> 'applied')::boolean, false) as fallback_applied,
  d.fallback_watchlist ->> 'source_run_id' as fallback_source_run_id
from public.agent_profile_diagnostics d
where d.market = 'NASDAQ'
order by d.generated_at desc
limit 100;

-- 5) outcome health 스냅샷 추적 (run 단위)
select
  h.run_id,
  h.market,
  h.generated_at,
  h.outcomes_total,
  h.pending,
  h.resolved,
  h.expired,
  h.expired_rate,
  h.fallback_total,
  h.fallback_pending,
  h.fallback_resolved,
  h.fallback_expired,
  h.fallback_expired_rate
from public.agent_outcome_health h
where h.market = 'NASDAQ'
order by h.generated_at desc
limit 100;
