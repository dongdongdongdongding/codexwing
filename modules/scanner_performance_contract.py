from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


SECTION_PERFORMANCE_PATH = Path("runtime_state/reports/trading/signal_section_performance_daily.json")
LIVE_POLICY_OBSERVED_PATH = Path("runtime_state/reports/validation/live_swing_policy_performance_observed.json")
LIVE_POLICY_STRICT_PATH = Path("runtime_state/reports/validation/live_swing_policy_performance_strict.json")
SCAN_COHORT_PERFORMANCE_PATH = Path("runtime_state/reports/validation/scan_cohort_performance.json")
SLICE_VALIDATION_PATHS = {
    "KOSPI": Path("runtime_state/reports/validation/kospi_swing_5d_slice_validation.json"),
    "KOSDAQ": Path("runtime_state/reports/validation/kosdaq_swing_5d_slice_validation.json"),
}

DEFAULT_PRODUCTION_MIN_SAMPLE_N = 30
LONG_HORIZON_PRODUCTION_MIN_SAMPLE_N = {
    14: 120,
    30: 180,
}
LONG_HORIZON_PRODUCTION_MIN_ACTIVE_DAYS = {
    14: 8,
    30: 10,
}


def min_samples_for_horizon(horizon_days: int) -> int:
    return LONG_HORIZON_PRODUCTION_MIN_SAMPLE_N.get(int(horizon_days or 0), DEFAULT_PRODUCTION_MIN_SAMPLE_N)


def min_active_days_for_horizon(horizon_days: int) -> int:
    return LONG_HORIZON_PRODUCTION_MIN_ACTIVE_DAYS.get(int(horizon_days or 0), 0)


@dataclass(frozen=True)
class PerformanceMetric:
    market: str
    scan_mode: str
    section: str
    horizon_days: int
    sample_n: int
    win_rate_pct: Optional[float]
    avg_return_pct: Optional[float]
    median_return_pct: Optional[float]
    avg_win_return_pct: Optional[float]
    avg_loss_return_pct: Optional[float]
    best_return_pct: Optional[float]
    worst_return_pct: Optional[float]
    source: str
    active_day_n: int = 0
    generated_at: str = ""
    as_of_date: str = ""

    @property
    def min_sample_n_required(self) -> int:
        return min_samples_for_horizon(self.horizon_days)

    @property
    def min_active_day_n_required(self) -> int:
        return min_active_days_for_horizon(self.horizon_days)

    @property
    def long_horizon_ready(self) -> bool:
        if self.horizon_days < 14:
            return True
        if self.sample_n < self.min_sample_n_required:
            return False
        active_required = self.min_active_day_n_required
        if active_required and self.active_day_n < active_required:
            return False
        return True

    @property
    def reliability_level(self) -> str:
        if not self.long_horizon_ready:
            return "immature"
        if self.sample_n >= 50:
            return "high"
        if self.sample_n >= 30:
            return "medium"
        if self.sample_n >= 10:
            return "low"
        return "small_sample"

    @property
    def production_pass(self) -> bool:
        return (
            self.long_horizon_ready
            and self.sample_n >= self.min_sample_n_required
            and (self.win_rate_pct or 0.0) >= 70.0
            and (self.avg_return_pct or 0.0) >= 5.0
        )

    @property
    def near_pass(self) -> bool:
        return (
            not self.production_pass
            and self.long_horizon_ready
            and self.sample_n >= 10
            and (self.win_rate_pct or 0.0) >= 65.0
            and (self.avg_return_pct or 0.0) >= 3.0
        )


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "nan", "None"):
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _load_json(path: Path) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload


def _norm_market(value: Any) -> str:
    return str(value or "").upper().strip()


def _norm_section(value: Any) -> str:
    text = str(value or "").strip()
    upper = text.upper()
    if "EXCEPTION" in upper:
        return "Exception Leader"
    if "SHADOW" in upper:
        return "Shadow"
    return "Top5"


def _metric_from_section_row(row: Dict[str, Any]) -> PerformanceMetric:
    return PerformanceMetric(
        market=_norm_market(row.get("market")),
        scan_mode=str(row.get("scan_mode") or "SWING").upper().strip() or "SWING",
        section=_norm_section(row.get("section")),
        horizon_days=int(row.get("horizon_days") or 0),
        sample_n=int(row.get("sample_n") or 0),
        win_rate_pct=_safe_float(row.get("win_rate_pct")),
        avg_return_pct=_safe_float(row.get("avg_return_pct")),
        median_return_pct=_safe_float(row.get("median_return_pct")),
        avg_win_return_pct=_safe_float(row.get("avg_win_return_pct")),
        avg_loss_return_pct=_safe_float(row.get("avg_loss_return_pct")),
        best_return_pct=_safe_float(row.get("best_return_pct")),
        worst_return_pct=_safe_float(row.get("worst_return_pct")),
        source=str(row.get("source") or "signal_section_performance_daily"),
        active_day_n=int(row.get("active_day_n") or 0),
        generated_at=str(row.get("generated_at") or ""),
        as_of_date=str(row.get("as_of_date") or ""),
    )


def latest_section_metric(
    market: Any,
    section: Any,
    *,
    horizon_days: int = 5,
    scan_mode: Any = "SWING",
    path: Path = SECTION_PERFORMANCE_PATH,
) -> Optional[PerformanceMetric]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        return None
    market_key = _norm_market(market)
    section_key = _norm_section(section)
    scan_mode_key = str(scan_mode or "SWING").upper().strip() or "SWING"
    candidates = [
        row
        for row in payload
        if isinstance(row, dict)
        and _norm_market(row.get("market")) == market_key
        and str(row.get("scan_mode") or "SWING").upper().strip() == scan_mode_key
        and _norm_section(row.get("section")) == section_key
        and int(row.get("horizon_days") or 0) == int(horizon_days)
    ]
    if not candidates:
        return None
    latest = sorted(
        candidates,
        key=lambda row: (str(row.get("as_of_date") or ""), str(row.get("generated_at") or "")),
    )[-1]
    return _metric_from_section_row(latest)


def slice_metric(market: Any, slice_name: str) -> Optional[PerformanceMetric]:
    market_key = _norm_market(market)
    path = SLICE_VALIDATION_PATHS.get(market_key)
    if path is None:
        return None
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return None
    target = None
    for row in payload.get("slices") or []:
        if isinstance(row, dict) and str(row.get("slice") or "") == slice_name:
            target = row
            break
    if not isinstance(target, dict):
        return None
    section = "Exception Leader" if "exception" in slice_name.lower() else "Top5"
    return PerformanceMetric(
        market=market_key,
        scan_mode="SWING",
        section=section,
        horizon_days=5,
        sample_n=int(target.get("n") or 0),
        win_rate_pct=_safe_float(target.get("win_5d_pct")),
        avg_return_pct=_safe_float(target.get("avg_5d_pct")),
        median_return_pct=_safe_float(target.get("median_5d_pct")),
        avg_win_return_pct=None,
        avg_loss_return_pct=None,
        best_return_pct=_safe_float(target.get("max_5d_pct")),
        worst_return_pct=_safe_float(target.get("min_5d_pct")),
        source=f"{market_key.lower()}_swing_5d_slice_validation:{slice_name}",
        generated_at=str(payload.get("generated_at") or ""),
        as_of_date="",
    )


def _practical_gate_policy_summary(market: Any, *, path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    payload = _load_json(path or SCAN_COHORT_PERFORMANCE_PATH)
    if not isinstance(payload, dict):
        return None
    market_key = _norm_market(market)
    market_payload = payload.get("markets", {}).get(market_key) if isinstance(payload.get("markets"), dict) else None
    if not isinstance(market_payload, dict):
        return None
    cohorts = market_payload.get("cohorts") if isinstance(market_payload.get("cohorts"), dict) else {}
    cohort = cohorts.get("Practical 80 Gate")
    if not isinstance(cohort, dict):
        return None
    horizons = cohort.get("horizons") if isinstance(cohort.get("horizons"), dict) else {}
    horizon = horizons.get("5D") if isinstance(horizons.get("5D"), dict) else {}
    sample_n = int(horizon.get("n") or 0)
    if sample_n <= 0:
        return None
    win = _safe_float(horizon.get("win_pct"))
    avg = _safe_float(horizon.get("avg_pct"))
    path_metrics = cohort.get("path") if isinstance(cohort.get("path"), dict) else {}
    bad_path = _safe_float(path_metrics.get("bad_path_pct"))
    validation_pass = (
        sample_n >= DEFAULT_PRODUCTION_MIN_SAMPLE_N
        and (win or 0.0) >= 70.0
        and (avg or 0.0) >= 5.0
        and (bad_path is None or bad_path <= 20.0)
    )
    sample = f"n={sample_n}"
    if bad_path is not None:
        sample += f" · bad {bad_path:.1f}%"
    if sample_n < DEFAULT_PRODUCTION_MIN_SAMPLE_N:
        sample += " · small_sample"
    return {
        "policy": "Practical 80 Gate",
        "validated_win": "-" if win is None else f"{win:.1f}%",
        "validated_return": "-" if avg is None else f"{avg:+.2f}%",
        "sample": sample,
        "quality_scope": "scan_cohort_practical_gate",
        "validation_pass": bool(validation_pass),
    }


def format_metric(metric: Optional[PerformanceMetric], *, horizon_label: str = "5D") -> str:
    if metric is None:
        return "검증 없음"
    win = "-" if metric.win_rate_pct is None else f"{metric.win_rate_pct:.1f}%"
    avg = "-" if metric.avg_return_pct is None else f"{metric.avg_return_pct:+.2f}%"
    worst = "-" if metric.worst_return_pct is None else f"{metric.worst_return_pct:+.2f}%"
    suffix = ""
    if metric.horizon_days >= 14:
        suffix = f" · gate n {metric.sample_n}/{metric.min_sample_n_required}"
        if metric.min_active_day_n_required:
            suffix += f" days {metric.active_day_n}/{metric.min_active_day_n_required}"
    return f"n={metric.sample_n} · win{horizon_label} {win} · avg{horizon_label} {avg} · worst {worst}{suffix}"


def profile_level(metric: Optional[PerformanceMetric]) -> str:
    if metric is None:
        return "fail"
    if not metric.long_horizon_ready:
        return "immature"
    if metric.production_pass:
        return "pass"
    if metric.near_pass:
        return "near"
    if metric.sample_n < 30:
        return "small_sample"
    return "fail"


def live_policy_summary(market: Any, *, strict_quality_gate: bool = True) -> Dict[str, Any]:
    if strict_quality_gate:
        practical = _practical_gate_policy_summary(market)
        if practical:
            return practical
    path = LIVE_POLICY_STRICT_PATH if strict_quality_gate else LIVE_POLICY_OBSERVED_PATH
    payload = _load_json(path)
    market_key = _norm_market(market)
    # NOTE 2026-06-24 (Claude+Codex two-way re-validation): these labels are compatibility
    # fallbacks, not validated edges. Under the fair same-day size-matched control,
    # exception_leader (+1.95%) and Practical-80 (+1.64%) are in-window positive but on ~4
    # months (2026-04-concentrated) so durability is unverified; expected_edge_score is
    # borderline (+1.42% CI incl 0). The only 8y-durable signal (daily price ML) is a
    # low-liquidity premium that dies at >=30억/>=100억. => NO tradeable daily promotion.
    # Defaults OFF until a candidate clears size-matched CI>0 at a tradeable liquidity floor.
    fallback_policy = {
        "KOSPI": "no validated daily promotion (no tradeable daily edge)",
        "KOSDAQ": "no validated daily promotion (no tradeable daily edge)",
    }.get(market_key, "segment policy")
    if not isinstance(payload, dict):
        return {
            "policy": fallback_policy,
            "validated_win": "-",
            "validated_return": "-",
            "sample": "n=0",
            "quality_scope": "missing_report",
            "validation_pass": False,
        }
    for row in payload.get("policies") or []:
        if not isinstance(row, dict) or _norm_market(row.get("market")) != market_key:
            continue
        win = _safe_float(row.get("win_5d_pct"))
        avg = _safe_float(row.get("avg_return_5d_pct"))
        target_rows = int(row.get("target_rows") or 0)
        loss5 = _safe_float(row.get("loss_5pct_or_worse_5d_pct"))
        sample = f"n={target_rows}"
        if loss5 is not None:
            sample += f" · loss5 {loss5:.1f}%"
        return {
            "policy": str(row.get("policy") or fallback_policy),
            "validated_win": "-" if win is None else f"{win:.1f}%",
            "validated_return": "-" if avg is None else f"{avg:+.2f}%",
            "sample": sample,
            "quality_scope": str(payload.get("quality_scope") or ""),
            "validation_pass": bool(row.get("passes_goal")) and bool(row.get("close_5d_quality_pass")),
        }
    return {
        "policy": fallback_policy,
        "validated_win": "-",
        "validated_return": "-",
        "sample": "n=0",
        "quality_scope": str(payload.get("quality_scope") or ""),
        "validation_pass": False,
    }


__all__ = [
    "PerformanceMetric",
    "format_metric",
    "latest_section_metric",
    "live_policy_summary",
    "min_active_days_for_horizon",
    "min_samples_for_horizon",
    "profile_level",
    "slice_metric",
]
