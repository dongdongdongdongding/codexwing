from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

INCIDENT_REGRESSION_VERSION = "incident_regression_v1"
DEFAULT_SEVERE_LOSS_PCT = -7.0
DEFAULT_ELEVATED_SCORE = 60.0
HIGH_CONFIDENCE_DECISIONS = {"PRIORITY_WATCHLIST", "EXCEPTION_LEADER", "WATCHLIST", "WATCHLIST_ONLY"}
PROTECTIVE_REASON_CODES = {
    "NO_BUY_ACTION",
    "LOSS_RISK_HARD_CAP",
    "ENTRY_TIMING_RISK_HIGH",
    "CHASE_LOW_PROB_RISK",
    "PHASE25_SWING_BELOW_THRESHOLD_HARD",
    "THEME_HEADWIND",
    "VISIBLE_RISK_ANNOTATED",
}


@dataclass(frozen=True)
class IncidentPolicy:
    name: str = "current"
    severe_loss_pct: float = DEFAULT_SEVERE_LOSS_PCT
    elevated_score_threshold: float = DEFAULT_ELEVATED_SCORE
    accepted_tradeoff: bool = False
    accepted_tradeoff_reason: str = ""


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def load_incident_fixtures(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("incidents", [])
    else:
        rows = payload
    return [row for row in rows or [] if isinstance(row, dict)]


def detect_failure_risk_reason_codes(row: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    action = str(row.get("action_label") or row.get("signal_label") or "").strip().upper()
    if action in {"NO_BUY", "매수 금지".upper(), "신규 매수 금지".upper()} or str(row.get("signal_label") or "").upper() == "NO_BUY":
        codes.append("NO_BUY_ACTION")
    loss_risk = _safe_float(row.get("loss_risk_score"))
    if loss_risk is not None and loss_risk >= 65.0:
        codes.append("LOSS_RISK_HARD_CAP")
    for code in _as_list(row.get("risk_flags")) + _as_list(row.get("theme_risk")):
        upper = code.upper()
        codes.append(upper)
        if upper in PROTECTIVE_REASON_CODES or any(token in upper for token in ("CHASE", "ENTRY_TIMING", "HEADWIND", "BELOW_THRESHOLD")):
            codes.append(upper)
    display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
    if str(display_contract.get("display_status") or "").upper() == "VISIBLE_RISK_ANNOTATED":
        codes.append("VISIBLE_RISK_ANNOTATED")
    return sorted(set(codes))


def _outcome_path_values(row: Dict[str, Any]) -> List[float]:
    fields = (
        "return_10m_pct",
        "return_30m_pct",
        "return_1h_pct",
        "return_close_pct",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "mae_intraday_pct",
        "mae_5d_pct",
    )
    return [value for value in (_safe_float(row.get(field)) for field in fields) if value is not None]


def evaluate_incident_case(row: Dict[str, Any], policy: IncidentPolicy | None = None) -> Dict[str, Any]:
    policy = policy or IncidentPolicy()
    path_values = _outcome_path_values(row)
    worst_path = min(path_values) if path_values else None
    severe_loss = worst_path is not None and worst_path <= float(policy.severe_loss_pct)
    score = _safe_float(row.get("buy_score") or row.get("relative_rank_score") or row.get("decision_score"))
    decision = str(row.get("decision") or "").upper()
    bucket = str(row.get("decision_bucket") or "").lower()
    elevated = (
        decision in HIGH_CONFIDENCE_DECISIONS
        or bucket in {"picked", "exception_leader"}
        or (score is not None and score >= float(policy.elevated_score_threshold))
    )
    reason_codes = detect_failure_risk_reason_codes(row)
    protected = bool(set(reason_codes).intersection(PROTECTIVE_REASON_CODES))
    unprotected_elevation = bool(severe_loss and elevated and not protected)
    return {
        "version": INCIDENT_REGRESSION_VERSION,
        "policy": {
            "name": policy.name,
            "severe_loss_pct": policy.severe_loss_pct,
            "elevated_score_threshold": policy.elevated_score_threshold,
            "accepted_tradeoff": policy.accepted_tradeoff,
            "accepted_tradeoff_reason": policy.accepted_tradeoff_reason,
        },
        "incident_id": row.get("incident_id"),
        "run_id": row.get("run_id"),
        "ticker": row.get("ticker"),
        "market": row.get("market"),
        "section": row.get("section") or row.get("analysis_section"),
        "decision": row.get("decision"),
        "decision_bucket": row.get("decision_bucket"),
        "score": score,
        "worst_path_return_pct": None if worst_path is None else round(float(worst_path), 6),
        "severe_loss": severe_loss,
        "elevated": elevated,
        "failure_risk_reason_codes": reason_codes,
        "protected_by_reason_code": protected,
        "unprotected_elevation": unprotected_elevation,
        "status": "FAIL" if unprotected_elevation and not policy.accepted_tradeoff else "PASS",
    }


def build_incident_regression_report(
    rows: Iterable[Dict[str, Any]],
    *,
    current_policy: IncidentPolicy | None = None,
    candidate_policy: IncidentPolicy | None = None,
) -> Dict[str, Any]:
    current_policy = current_policy or IncidentPolicy(name="current")
    candidate_policy = candidate_policy or current_policy
    current_results = [evaluate_incident_case(row, current_policy) for row in rows]
    candidate_results = [evaluate_incident_case(row, candidate_policy) for row in rows]

    def _count(results: List[Dict[str, Any]], key: str) -> int:
        return sum(1 for row in results if row.get(key))

    current_unprotected = _count(current_results, "unprotected_elevation")
    candidate_unprotected = _count(candidate_results, "unprotected_elevation")
    worsening = candidate_unprotected > current_unprotected and not candidate_policy.accepted_tradeoff
    return {
        "version": INCIDENT_REGRESSION_VERSION,
        "rows": len(current_results),
        "current": {
            "policy": current_policy.name,
            "severe_loss_count": _count(current_results, "severe_loss"),
            "unprotected_elevation_count": current_unprotected,
            "status": "FAIL" if current_unprotected else "PASS",
            "results": current_results,
        },
        "candidate": {
            "policy": candidate_policy.name,
            "severe_loss_count": _count(candidate_results, "severe_loss"),
            "unprotected_elevation_count": candidate_unprotected,
            "worsening_vs_current": worsening,
            "status": "FAIL" if worsening else ("WAIVED" if candidate_policy.accepted_tradeoff else "PASS"),
            "results": candidate_results,
        },
    }
