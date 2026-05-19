# KR Intraday Data Adapter Decision

Updated: 2026-05-19

This is a research/contract decision for future 급등 레이더 work. It does not
add a production market-data dependency.

## Decision

Use Korea Investment Open API as the preferred future primary source for
scheduled KR intraday candidate snapshots, after credentials and live smoke
tests pass. Keep yfinance, Naver scrape, and pykrx as fallback or diagnostic
sources only.

Why:

- KIS Developers officially lists domestic stock current price, day-minute
  bars, investor data, and realtime KRX 체결가/호가 APIs:
  https://apiportal.koreainvestment.com/apiservice-summary
- yfinance officially supports intraday intervals such as `1m`, `5m`, `15m`,
  but intraday history cannot extend beyond 60 days:
  https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html
- pykrx and Naver remain useful, but the project has observed empty pykrx
  investor endpoint responses and Naver is HTML-scrape fallback, not an
  exchange-authoritative API.

## Source Comparison

| Source | Role | Auth | Intraday Bars | Realtime | Investor Flow | Decision |
|---|---|---:|---:|---:|---:|---|
| Korea Investment Open API | primary candidate snapshot | yes | yes | yes | yes | Preferred after dry-run/live smoke |
| yfinance | fallback price/volume | no | yes, limited | no | no | Use only as best-effort price/volume fallback |
| Naver finance scrape | display fallback | no | no | no | partial | Use with warnings only |
| pykrx | daily/investor fallback | no | no | no | yes | Keep fallback until empty-response issue is fixed |

## Adapter Interface

The adapter output is a bounded snapshot row, not raw ticks:

```text
ticker
market
snapshot_at_kst
source
source_status
last_price
day_change_pct
session_open
session_high
session_low
volume
value_traded
volume_acceleration
vwap
high_breakout_pct
theme_breadth_pct
foreigner_1d
institution_1d
retail_1d
warnings
```

Required behavior:

- Every row must include `source` and `source_status`.
- Missing price, volume, VWAP, or investor-flow fields must produce explicit
  warnings; do not synthesize values.
- Same-day flow and cumulative flow must remain separate fields.
- Source fallback must be visible in reports and archive rows.

## KIS Setup Contract

Required environment variables:

```bash
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_ACCOUNT_NO=
KIS_ACCOUNT_PRODUCT_CODE=
```

Dry-run health check:

```bash
python3 multi_agent/tools/check_kr_intraday_adapter_health.py
```

This check is intentionally non-network by default. It verifies local contract
readiness, imports, and credentials presence. A later live-smoke issue should
add token and quote calls with rate-limit backoff.

## Snapshot Timing

Recommended scheduled snapshots:

- `09:31 KST`: open confirmation, only after the first noisy prints settle
- `10:30 KST`: early volume acceleration and high-breakout check
- `13:30 KST`: afternoon continuation check
- `15:10 KST`: close-prep check for next-session archive

This is not 24-hour scanning. It is bounded scheduled sampling.

## Storage Budget

Default policy from `modules.kr_intraday_adapter_contract.storage_budget_policy`:

- raw tick storage: forbidden
- full-universe intraday rows: cache-only
- candidate summaries: persisted for 20 days by default
- default persisted scale: 50 candidates x 4 snapshots = 200 rows/day
- estimated persisted candidate storage: about 0.293 MB/day, about 5.86 MB for
  20 days
- full-universe estimate if cached only: 2,000 symbols x 4 snapshots = 8,000
  rows/day, about 9.375 MB/day

## Promotion Gate

Do not promote a live KIS dependency until all are true:

- credentials are configured locally
- token dry-run succeeds
- quote/day-minute smoke test succeeds for at least `005930.KS`
- KOSPI/KOSDAQ candidate snapshot returns source warnings correctly
- rate-limit backoff and retry policy are tested
- Discord/web/archive display source status and missing-data warnings

Until then, this remains an adapter contract and research decision only.

