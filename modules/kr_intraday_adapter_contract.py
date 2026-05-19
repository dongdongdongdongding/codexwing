from __future__ import annotations

import os
from importlib.util import find_spec
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple


KR_INTRADAY_ADAPTER_CONTRACT_VERSION = "kr_intraday_adapter_contract_v1"


@dataclass(frozen=True)
class IntradaySourceProfile:
    key: str
    label: str
    priority: int
    auth_required: bool
    realtime_capable: bool
    minute_bar_capable: bool
    investor_flow_capable: bool
    production_role: str
    reliability: str
    notes: Tuple[str, ...]


KIS_REQUIRED_ENV_VARS: Tuple[str, ...] = (
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIS_ACCOUNT_NO",
    "KIS_ACCOUNT_PRODUCT_CODE",
)


SOURCE_PROFILES: Dict[str, IntradaySourceProfile] = {
    "kis_openapi": IntradaySourceProfile(
        key="kis_openapi",
        label="Korea Investment Open API",
        priority=1,
        auth_required=True,
        realtime_capable=True,
        minute_bar_capable=True,
        investor_flow_capable=True,
        production_role="primary_candidate_snapshot_source",
        reliability="best_free_or_broker_provided_candidate",
        notes=(
            "Official KIS portal lists domestic current price, day minute bars, investor data, and realtime 체결가 APIs.",
            "Use only after credentials, rate limits, and private-guild dry-run health pass.",
        ),
    ),
    "yfinance": IntradaySourceProfile(
        key="yfinance",
        label="yfinance",
        priority=2,
        auth_required=False,
        realtime_capable=False,
        minute_bar_capable=True,
        investor_flow_capable=False,
        production_role="fallback_price_volume_snapshot",
        reliability="best_effort_unofficial_yahoo_wrapper",
        notes=(
            "Official yfinance docs support intraday intervals including 1m/5m, but intraday history cannot extend beyond 60 days.",
            "Use for bounded price/volume fallback only; do not treat it as investor flow or exchange-authoritative data.",
        ),
    ),
    "naver_scrape": IntradaySourceProfile(
        key="naver_scrape",
        label="Naver finance scrape",
        priority=3,
        auth_required=False,
        realtime_capable=False,
        minute_bar_capable=False,
        investor_flow_capable=True,
        production_role="fallback_display_only",
        reliability="fragile_html_scrape",
        notes=(
            "Existing code uses Naver as fallback when pykrx investor flow fails.",
            "Use only with source warnings because HTML layout and delayed/partial fields can change.",
        ),
    ),
    "pykrx": IntradaySourceProfile(
        key="pykrx",
        label="pykrx",
        priority=4,
        auth_required=False,
        realtime_capable=False,
        minute_bar_capable=False,
        investor_flow_capable=True,
        production_role="daily_or_investor_flow_fallback",
        reliability="useful_but_currently_unstable_for_live_investor_endpoint",
        notes=(
            "Project live checks have seen empty investor endpoint responses.",
            "Keep as a daily/fallback adapter until endpoint stability is repaired.",
        ),
    ),
}


SNAPSHOT_FEATURE_FIELDS: Tuple[str, ...] = (
    "ticker",
    "market",
    "snapshot_at_kst",
    "source",
    "source_status",
    "last_price",
    "day_change_pct",
    "session_open",
    "session_high",
    "session_low",
    "volume",
    "value_traded",
    "volume_acceleration",
    "vwap",
    "high_breakout_pct",
    "theme_breadth_pct",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "warnings",
)


def storage_budget_policy(
    *,
    universe_count: int = 2000,
    candidate_count: int = 50,
    snapshots_per_day: int = 4,
    retention_days: int = 20,
) -> Dict[str, Any]:
    universe_rows_per_day = int(universe_count) * int(snapshots_per_day)
    candidate_rows_per_day = int(candidate_count) * int(snapshots_per_day)
    # JSONL row estimates are intentionally conservative. Persisted candidate
    # summaries are small; full-universe rows should stay temporary/cache only.
    candidate_mb_per_day = round(candidate_rows_per_day * 1.5 / 1024.0, 3)
    universe_mb_per_day = round(universe_rows_per_day * 1.2 / 1024.0, 3)
    return {
        "policy_version": KR_INTRADAY_ADAPTER_CONTRACT_VERSION,
        "raw_tick_storage": "forbidden",
        "full_universe_intraday_retention": "cache_only",
        "candidate_summary_retention_days": int(retention_days),
        "snapshots_per_day": int(snapshots_per_day),
        "candidate_rows_per_day": candidate_rows_per_day,
        "candidate_mb_per_day_estimate": candidate_mb_per_day,
        "candidate_mb_retention_estimate": round(candidate_mb_per_day * int(retention_days), 3),
        "full_universe_rows_per_day_if_cached": universe_rows_per_day,
        "full_universe_mb_per_day_estimate": universe_mb_per_day,
        "persisted_fields": list(SNAPSHOT_FEATURE_FIELDS),
    }


def adapter_decision_contract() -> Dict[str, Any]:
    return {
        "version": KR_INTRADAY_ADAPTER_CONTRACT_VERSION,
        "recommended_primary": "kis_openapi",
        "promotion_gate": {
            "required": [
                "credentials_present",
                "token_dry_run_ok",
                "quote_dry_run_ok",
                "rate_limit_backoff_ok",
                "source_warning_propagation_ok",
            ],
            "production_dependency_allowed": False,
            "reason": "Current task approves contract/research only; live production dependency needs a separate promotion issue.",
        },
        "source_profiles": {key: asdict(profile) for key, profile in SOURCE_PROFILES.items()},
        "storage_budget": storage_budget_policy(),
    }


def kis_env_status(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    source = env if env is not None else os.environ
    present = [key for key in KIS_REQUIRED_ENV_VARS if str(source.get(key) or "").strip()]
    missing = [key for key in KIS_REQUIRED_ENV_VARS if key not in present]
    return {
        "source": "kis_openapi",
        "required_env_vars": list(KIS_REQUIRED_ENV_VARS),
        "present_env_vars": present,
        "missing_env_vars": missing,
        "credentials_present": not missing,
    }


def build_kr_intraday_adapter_health(env: Dict[str, str] | None = None) -> Dict[str, Any]:
    status = kis_env_status(env)
    checks: List[Dict[str, Any]] = [
        {
            "name": "kis_credentials",
            "ok": bool(status["credentials_present"]),
            "detail": "all required KIS env vars present" if status["credentials_present"] else "missing: " + ", ".join(status["missing_env_vars"]),
        }
    ]
    checks.append({"name": "yfinance_import", "ok": find_spec("yfinance") is not None, "detail": "available" if find_spec("yfinance") else "missing"})
    checks.append({"name": "pykrx_import", "ok": find_spec("pykrx") is not None, "detail": "available" if find_spec("pykrx") else "missing"})

    return {
        "version": KR_INTRADAY_ADAPTER_CONTRACT_VERSION,
        "dry_run": True,
        "network_called": False,
        "kis": status,
        "checks": checks,
        "ok_for_contract_only": True,
        "ok_for_live_kis_promotion": all(check["ok"] for check in checks if check["name"] == "kis_credentials"),
        "next_step": "Run a separate live KIS quote/token smoke test only after credentials are configured and promotion is approved.",
    }


__all__ = [
    "KIS_REQUIRED_ENV_VARS",
    "KR_INTRADAY_ADAPTER_CONTRACT_VERSION",
    "SNAPSHOT_FEATURE_FIELDS",
    "SOURCE_PROFILES",
    "adapter_decision_contract",
    "build_kr_intraday_adapter_health",
    "kis_env_status",
    "storage_budget_policy",
]
