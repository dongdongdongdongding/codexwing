from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_REPORT_PATH = Path("runtime_state/reports/experimental/operational_admission_optimizer_latest.json")
KOSDAQ_THEME_REPORT_PATH = Path("runtime_state/reports/experimental/operational_admission_optimizer_kosdaq_theme_latest.json")
FALLBACK_REPORT_PATH = Path("runtime_state/reports/experimental/operational_admission_optimizer.json")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if number != number:
            return default
        return number
    except Exception:
        return default


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "-"


def load_admission_optimizer_report(path: str | Path | None = None, *, market: str | None = None) -> Dict[str, Any]:
    market_key = str(market or "").strip().upper()
    if path:
        report_path = Path(path)
    elif market_key == "KOSDAQ" and KOSDAQ_THEME_REPORT_PATH.exists():
        report_path = KOSDAQ_THEME_REPORT_PATH
    else:
        report_path = DEFAULT_REPORT_PATH
    if not report_path.exists() and not path:
        report_path = FALLBACK_REPORT_PATH
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def admission_optimizer_rows(
    report: Dict[str, Any] | None = None,
    *,
    market: str | None = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    payload = report if isinstance(report, dict) else load_admission_optimizer_report(market=market)
    if not payload:
        return []
    target_market = str(market or "").strip().upper()
    rows: List[Dict[str, Any]] = []
    policies = list(payload.get("promotable_policies") or []) + list(payload.get("top_policies") or [])
    seen: set[tuple[Any, ...]] = set()
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        if target_market and str(policy.get("market") or "").upper() != target_market:
            continue
        metrics = policy.get("metrics") if isinstance(policy.get("metrics"), dict) else {}
        promotion = policy.get("promotion") if isinstance(policy.get("promotion"), dict) else {}
        label_profile = policy.get("label_profile") if isinstance(policy.get("label_profile"), dict) else {}
        key = (
            policy.get("market"),
            policy.get("cohort"),
            label_profile.get("name"),
            policy.get("policy_type"),
            policy.get("model"),
            policy.get("feature_set"),
            policy.get("topn"),
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "state": "PROMOTE" if promotion.get("promotable") else "WATCH",
                "market": policy.get("market"),
                "cohort": policy.get("cohort"),
                "label": label_profile.get("name"),
                "policy_type": policy.get("policy_type"),
                "model": policy.get("model"),
                "feature_set": policy.get("feature_set"),
                "topn": policy.get("topn"),
                "n": metrics.get("n"),
                "days": metrics.get("active_days"),
                "label_win_pct": metrics.get("label_win_pct"),
                "avg_5d_pct": metrics.get("avg_5d_pct"),
                "min_5d_pct": metrics.get("min_5d_pct"),
                "target_before_stop_5d_pct": metrics.get("target_before_stop_5d_pct"),
                "stop_before_target_5d_pct": metrics.get("stop_before_target_5d_pct"),
                "no_touch_5d_pct": metrics.get("no_touch_5d_pct"),
                "ordered_path_coverage_pct": metrics.get("ordered_path_coverage_pct"),
                "folds": promotion.get("folds"),
                "min_fold_label_win_pct": promotion.get("min_fold_label_win_pct"),
                "quality_score": policy.get("quality_score"),
                "report_source": str(payload.get("report_source") or payload.get("stem") or ""),
            }
        )
        if len(rows) >= max(int(limit or 0), 0):
            break
    return rows


def admission_optimizer_discord_summary(market: str | None = None, *, limit: int = 3) -> str:
    report = load_admission_optimizer_report(market=market)
    if not report:
        return "optimizer report 없음"
    rows = admission_optimizer_rows(report, market=market, limit=limit)
    generated_at = str(report.get("generated_at") or "-")
    header = (
        f"generated {generated_at[:19]} · evaluated {report.get('evaluated_policies') or 0} · "
        f"promote {report.get('promotable_count') or 0}"
    )
    if not rows:
        return f"{header}\n표시 후보 없음"
    lines = [header]
    for row in rows[:limit]:
        lines.append(
            (
                f"{row.get('state')} {row.get('market')}/{row.get('cohort')} "
                f"{row.get('label')} {row.get('model')} top{row.get('topn')} · "
                f"win {_fmt_pct(row.get('label_win_pct'))} avg5 {_fmt_pct(row.get('avg_5d_pct'))} "
                f"stop {_fmt_pct(row.get('stop_before_target_5d_pct'))} "
                f"n={row.get('n')} days={row.get('days')}"
            )[:900]
        )
    return "\n".join(lines)


def admission_optimizer_status(report: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = report if isinstance(report, dict) else load_admission_optimizer_report()
    if not payload:
        return {"available": False}
    rows = admission_optimizer_rows(payload, limit=20)
    promotable = [row for row in rows if row.get("state") == "PROMOTE"]
    best = rows[0] if rows else {}
    return {
        "available": True,
        "generated_at": payload.get("generated_at"),
        "report_version": payload.get("report_version"),
        "evaluated_policies": payload.get("evaluated_policies"),
        "promotable_count": payload.get("promotable_count"),
        "display_rows": rows,
        "promotable_rows": promotable,
        "best_row": best,
        "best_quality_score": _safe_float(best.get("quality_score"), 0.0) if best else 0.0,
    }
