from __future__ import annotations

from typing import Any, Dict

MEASURED_OUTCOME_BUCKETS = ("picked", "watchlist", "exception_leader")


def classify_decision_bucket(decision: Any) -> str:
    value = str(decision or "").strip().upper()
    if value == "EXCEPTION_LEADER":
        return "exception_leader"
    if value in {"WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"}:
        return "watchlist"
    if value in {"PRIORITY_WATCHLIST"}:
        return "picked"
    return "ignored"


def resolve_outcome_bucket(row: Dict[str, Any]) -> str:
    if not isinstance(row, dict):
        return "ignored"
    decision_value = str(row.get("decision", "")).strip()
    if decision_value:
        return classify_decision_bucket(decision_value)
    existing = str(row.get("decision_bucket", "")).strip().lower()
    if existing in MEASURED_OUTCOME_BUCKETS:
        return existing
    return classify_decision_bucket(row.get("decision"))


def init_bucket_stats() -> Dict[str, Dict[str, Any]]:
    return {
        bucket: {
            "total": 0,
            "pending": 0,
            "resolved": 0,
            "expired": 0,
            "closure_rate_pct": 0.0,
        }
        for bucket in MEASURED_OUTCOME_BUCKETS
    }


def finalize_bucket_stats(stats: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    for bucket in MEASURED_OUTCOME_BUCKETS:
        row = stats.get(bucket, {})
        total = int(row.get("total", 0) or 0)
        resolved = int(row.get("resolved", 0) or 0)
        expired = int(row.get("expired", 0) or 0)
        row["closure_rate_pct"] = round(((resolved + expired) / total * 100.0), 2) if total > 0 else 0.0
        stats[bucket] = row
    return stats
