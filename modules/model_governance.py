from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


GOVERNANCE_VERSION = "model_governance_v1"
ACTIVE_KR_POLICY_VERSION = "kr_scanner_policy_2026_05_19"
ROLLBACK_KR_POLICY_VERSION = "kr_scanner_policy_2026_05_18"
ROLLBACK_ENV_FLAG = "KR_SCANNER_POLICY_ROLLBACK"
REQUIRED_KR_MARKETS = ("KOSPI", "KOSDAQ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "nan", "None"):
            return float(default)
        result = float(value)
        if result != result or result in (float("inf"), float("-inf")):
            return float(default)
        return result
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, "", "nan", "None"):
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _truthy_env(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "rollback"}


@dataclass(frozen=True)
class PolicyMetricSet:
    market: str
    section: str = "Top5"
    horizon: str = "3d"
    samples: int = 0
    active_days: int = 0
    win_rate_pct: float = 0.0
    avg_return_pct: float = 0.0
    worst_loss_pct: float = 0.0
    stop_first_rate_pct: float = 0.0
    capture_rate_pct: float = 0.0

    @classmethod
    def from_mapping(cls, payload: Dict[str, Any]) -> "PolicyMetricSet":
        return cls(
            market=str(payload.get("market") or "").upper(),
            section=str(payload.get("section") or "Top5"),
            horizon=str(payload.get("horizon") or "3d").lower(),
            samples=_safe_int(payload.get("samples")),
            active_days=_safe_int(payload.get("active_days")),
            win_rate_pct=_safe_float(payload.get("win_rate_pct")),
            avg_return_pct=_safe_float(payload.get("avg_return_pct")),
            worst_loss_pct=_safe_float(payload.get("worst_loss_pct")),
            stop_first_rate_pct=_safe_float(payload.get("stop_first_rate_pct")),
            capture_rate_pct=_safe_float(payload.get("capture_rate_pct")),
        )


@dataclass(frozen=True)
class ReleaseGateThresholds:
    min_samples: int = 30
    min_active_days: int = 5
    min_win_rate_lift_pct: float = 0.0
    min_avg_return_lift_pct: float = 0.0
    max_worst_loss_deterioration_pct: float = 0.0
    max_stop_first_deterioration_pct: float = 0.0
    min_capture_rate_lift_pct: float = 0.0

    @classmethod
    def from_mapping(cls, payload: Optional[Dict[str, Any]]) -> "ReleaseGateThresholds":
        payload = payload or {}
        return cls(
            min_samples=_safe_int(payload.get("min_samples"), 30),
            min_active_days=_safe_int(payload.get("min_active_days"), 5),
            min_win_rate_lift_pct=_safe_float(payload.get("min_win_rate_lift_pct"), 0.0),
            min_avg_return_lift_pct=_safe_float(payload.get("min_avg_return_lift_pct"), 0.0),
            max_worst_loss_deterioration_pct=_safe_float(payload.get("max_worst_loss_deterioration_pct"), 0.0),
            max_stop_first_deterioration_pct=_safe_float(payload.get("max_stop_first_deterioration_pct"), 0.0),
            min_capture_rate_lift_pct=_safe_float(payload.get("min_capture_rate_lift_pct"), 0.0),
        )


@dataclass(frozen=True)
class PolicyReleaseSpec:
    champion_policy_version: str
    challenger_policy_version: str
    training_window: Dict[str, Any] = field(default_factory=dict)
    validation_window: Dict[str, Any] = field(default_factory=dict)
    promotion_reason: str = ""
    leakage_warnings: List[str] = field(default_factory=list)
    rollback_env_flag: str = ROLLBACK_ENV_FLAG
    rollback_to_policy_version: str = ROLLBACK_KR_POLICY_VERSION

    @classmethod
    def from_mapping(cls, payload: Dict[str, Any]) -> "PolicyReleaseSpec":
        return cls(
            champion_policy_version=str(payload.get("champion_policy_version") or ACTIVE_KR_POLICY_VERSION),
            challenger_policy_version=str(payload.get("challenger_policy_version") or ""),
            training_window=payload.get("training_window") if isinstance(payload.get("training_window"), dict) else {},
            validation_window=payload.get("validation_window") if isinstance(payload.get("validation_window"), dict) else {},
            promotion_reason=str(payload.get("promotion_reason") or ""),
            leakage_warnings=list(payload.get("leakage_warnings") or []),
            rollback_env_flag=str(payload.get("rollback_env_flag") or ROLLBACK_ENV_FLAG),
            rollback_to_policy_version=str(payload.get("rollback_to_policy_version") or ROLLBACK_KR_POLICY_VERSION),
        )


def _check(condition: bool, code: str, detail: str, market: str = "", horizon: str = "") -> Dict[str, Any]:
    return {
        "code": code,
        "passed": bool(condition),
        "market": market,
        "horizon": horizon,
        "detail": detail,
    }


def _metric_index(metrics: Iterable[PolicyMetricSet]) -> Dict[tuple, PolicyMetricSet]:
    indexed: Dict[tuple, PolicyMetricSet] = {}
    for metric in metrics or []:
        indexed[(metric.market.upper(), metric.section, metric.horizon.lower())] = metric
    return indexed


def _iter_matching_keys(champion: Dict[tuple, PolicyMetricSet], challenger: Dict[tuple, PolicyMetricSet]) -> List[tuple]:
    keys = sorted(set(champion.keys()) | set(challenger.keys()))
    return [key for key in keys if key[0] in REQUIRED_KR_MARKETS]


def evaluate_policy_release_gate(
    *,
    spec: PolicyReleaseSpec,
    champion_metrics: Iterable[PolicyMetricSet],
    challenger_metrics: Iterable[PolicyMetricSet],
    thresholds: ReleaseGateThresholds | None = None,
) -> Dict[str, Any]:
    threshold = thresholds or ReleaseGateThresholds()
    champion_by_key = _metric_index(champion_metrics)
    challenger_by_key = _metric_index(challenger_metrics)
    checks: List[Dict[str, Any]] = []
    market_results: Dict[str, Dict[str, Any]] = {}

    checks.append(
        _check(
            bool(spec.challenger_policy_version and spec.challenger_policy_version != spec.champion_policy_version),
            "CHALLENGER_VERSION_DISTINCT",
            f"champion={spec.champion_policy_version} challenger={spec.challenger_policy_version}",
        )
    )
    checks.append(
        _check(
            not spec.leakage_warnings,
            "NO_KNOWN_LEAKAGE_WARNINGS",
            "none" if not spec.leakage_warnings else ", ".join(map(str, spec.leakage_warnings)),
        )
    )

    for market in REQUIRED_KR_MARKETS:
        has_champion = any(key[0] == market for key in champion_by_key)
        has_challenger = any(key[0] == market for key in challenger_by_key)
        checks.append(_check(has_champion, "MARKET_CHAMPION_PRESENT", f"market={market}", market=market))
        checks.append(_check(has_challenger, "MARKET_CHALLENGER_PRESENT", f"market={market}", market=market))

    for key in _iter_matching_keys(champion_by_key, challenger_by_key):
        market, section, horizon = key
        champion = champion_by_key.get(key)
        challenger = challenger_by_key.get(key)
        if not champion or not challenger:
            continue
        row_checks = [
            _check(
                challenger.samples >= threshold.min_samples,
                "MIN_SAMPLES",
                f"{section} samples={challenger.samples} min={threshold.min_samples}",
                market,
                horizon,
            ),
            _check(
                challenger.active_days >= threshold.min_active_days,
                "MIN_ACTIVE_DAYS",
                f"{section} active_days={challenger.active_days} min={threshold.min_active_days}",
                market,
                horizon,
            ),
            _check(
                challenger.win_rate_pct >= champion.win_rate_pct + threshold.min_win_rate_lift_pct,
                "WIN_RATE_NOT_WORSE",
                f"{section} champion={champion.win_rate_pct:.2f}% challenger={challenger.win_rate_pct:.2f}%",
                market,
                horizon,
            ),
            _check(
                challenger.avg_return_pct >= champion.avg_return_pct + threshold.min_avg_return_lift_pct,
                "AVG_RETURN_NOT_WORSE",
                f"{section} champion={champion.avg_return_pct:+.3f}% challenger={challenger.avg_return_pct:+.3f}%",
                market,
                horizon,
            ),
            _check(
                challenger.worst_loss_pct >= champion.worst_loss_pct - threshold.max_worst_loss_deterioration_pct,
                "WORST_LOSS_NOT_WORSE",
                f"{section} champion={champion.worst_loss_pct:+.3f}% challenger={challenger.worst_loss_pct:+.3f}%",
                market,
                horizon,
            ),
            _check(
                challenger.stop_first_rate_pct <= champion.stop_first_rate_pct + threshold.max_stop_first_deterioration_pct,
                "STOP_FIRST_NOT_WORSE",
                f"{section} champion={champion.stop_first_rate_pct:.2f}% challenger={challenger.stop_first_rate_pct:.2f}%",
                market,
                horizon,
            ),
            _check(
                challenger.capture_rate_pct >= champion.capture_rate_pct + threshold.min_capture_rate_lift_pct,
                "CAPTURE_RATE_NOT_WORSE",
                f"{section} champion={champion.capture_rate_pct:.2f}% challenger={challenger.capture_rate_pct:.2f}%",
                market,
                horizon,
            ),
        ]
        checks.extend(row_checks)
        market_results.setdefault(market, {"market": market, "sections": []})["sections"].append(
            {
                "section": section,
                "horizon": horizon,
                "champion": asdict(champion),
                "challenger": asdict(challenger),
                "passed": all(item["passed"] for item in row_checks),
                "checks": row_checks,
            }
        )

    release_ready = bool(checks) and all(item["passed"] for item in checks)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "governance_version": GOVERNANCE_VERSION,
        "release_ready": release_ready,
        "promotion_status": "promote_allowed" if release_ready else "shadow_only",
        "spec": asdict(spec),
        "thresholds": asdict(threshold),
        "market_results": [market_results[key] for key in sorted(market_results.keys())],
        "all_checks": checks,
        "rollback": {
            "enabled": not release_ready,
            "env_flag": spec.rollback_env_flag,
            "rollback_to_policy_version": spec.rollback_to_policy_version,
            "command": f"{spec.rollback_env_flag}=1 python3 -m streamlit run app.py --server.port 8501",
        },
    }


def active_policy_metadata(market: str = "", scan_mode: str = "") -> Dict[str, Any]:
    rollback = _truthy_env(os.getenv(ROLLBACK_ENV_FLAG))
    active_version = ROLLBACK_KR_POLICY_VERSION if rollback else ACTIVE_KR_POLICY_VERSION
    return {
        "governance_version": GOVERNANCE_VERSION,
        "policy_family": "kr_scanner",
        "active_policy_version": active_version,
        "champion_policy_version": ACTIVE_KR_POLICY_VERSION,
        "rollback_policy_version": ROLLBACK_KR_POLICY_VERSION,
        "rollback_active": rollback,
        "rollback_env_flag": ROLLBACK_ENV_FLAG,
        "market": str(market or "").upper(),
        "scan_mode": str(scan_mode or "").upper(),
        "promotion_status": "rollback_active" if rollback else "production_champion",
    }


def build_policy_release_report_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = PolicyReleaseSpec.from_mapping(payload.get("spec") if isinstance(payload.get("spec"), dict) else payload)
    thresholds = ReleaseGateThresholds.from_mapping(payload.get("thresholds") if isinstance(payload.get("thresholds"), dict) else {})
    champion_metrics = [
        PolicyMetricSet.from_mapping(row)
        for row in payload.get("champion_metrics", [])
        if isinstance(row, dict)
    ]
    challenger_metrics = [
        PolicyMetricSet.from_mapping(row)
        for row in payload.get("challenger_metrics", [])
        if isinstance(row, dict)
    ]
    return evaluate_policy_release_gate(
        spec=spec,
        champion_metrics=champion_metrics,
        challenger_metrics=challenger_metrics,
        thresholds=thresholds,
    )


def write_policy_release_report(report: Dict[str, Any], output_dir: Path, stem: str = "kr_model_release_gate") -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(policy_release_report_markdown(report), encoding="utf-8")
    return {"json_path": str(json_path), "md_path": str(md_path)}


def policy_release_report_markdown(report: Dict[str, Any]) -> str:
    status = "PASS" if report.get("release_ready") else "FAIL"
    spec = report.get("spec") if isinstance(report.get("spec"), dict) else {}
    lines = [
        "# KR Model Release Gate",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- governance_version: `{report.get('governance_version')}`",
        f"- release_ready: **{status}**",
        f"- champion: `{spec.get('champion_policy_version') or '-'}`",
        f"- challenger: `{spec.get('challenger_policy_version') or '-'}`",
        f"- promotion_status: `{report.get('promotion_status')}`",
        "",
        "## Checks",
    ]
    for check in report.get("all_checks") or []:
        mark = "PASS" if check.get("passed") else "FAIL"
        market = check.get("market") or "-"
        horizon = check.get("horizon") or "-"
        lines.append(f"- [{mark}] {market}/{horizon} {check.get('code')}: {check.get('detail')}")
    rollback = report.get("rollback") if isinstance(report.get("rollback"), dict) else {}
    lines.extend(
        [
            "",
            "## Rollback",
            f"- env_flag: `{rollback.get('env_flag') or ROLLBACK_ENV_FLAG}`",
            f"- rollback_to_policy_version: `{rollback.get('rollback_to_policy_version') or '-'}`",
            f"- command: `{rollback.get('command') or '-'}`",
        ]
    )
    return "\n".join(lines) + "\n"
