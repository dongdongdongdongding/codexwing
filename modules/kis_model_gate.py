from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Dict, List, Mapping

from modules.tradable_pnl import TradableCostModel, compute_net_return_pct


KIS_MODEL_GATE_VERSION = "kis_model_gate_v4_touch5_dd10"
TOUCH5_DD10_LABEL = "touch5_dd10_5d"
WIN_METRIC_SEMANTICS = "win_5d_pct means +5% target-touch rate after the operational buy-premium assumption; touch5_dd10_5d production gates use hit5_dd10_5d_pct and a -10% 5D low guard."

_COMMON_SHADOW = {
    "min_n": 8,
    "min_active_days": 3,
    "min_active_runs": 5,
    "min_win_5d_pct": 45.0,
    "min_avg_5d_pct": 0.0,
    "min_low_5d_pct": -25.0,
    "max_bad_path_pct": 60.0,
    "max_stop5_pct": 60.0,
}

_PROFILES: Dict[str, Dict[str, Any]] = {
    "KOSPI": {
        "production": {
            "min_n": 30,
            "min_active_days": 15,
            "min_active_runs": 20,
            "min_win_3d_pct": 65.0,
            "min_win_5d_pct": 73.0,
            "min_avg_3d_pct": 3.0,
            "min_avg_5d_pct": 5.0,
            "min_1d_pct": -5.0,
            "min_low_5d_pct": -15.0,
            "max_bad_path_pct": 15.0,
            "max_stop5_pct": 10.0,
            "max_stop_before_target_5d_pct": 15.0,
            "min_target_before_stop_5d_pct": 70.0,
        },
        "shadow": _COMMON_SHADOW,
        "risk_review": {
            "min_low_5d_pct": -15.0,
            "max_bad_path_pct": 25.0,
            "max_stop5_pct": 15.0,
            "min_1d_pct": -5.0,
        },
    },
    "KOSDAQ": {
        "production": {
            "min_n": 45,
            "min_active_days": 20,
            "min_active_runs": 20,
            "min_win_3d_pct": 65.0,
            "min_win_5d_pct": 73.0,
            "min_avg_3d_pct": 3.0,
            "min_avg_5d_pct": 5.0,
            "min_1d_pct": -4.0,
            "min_low_5d_pct": -12.0,
            "max_bad_path_pct": 15.0,
            "max_stop5_pct": 10.0,
            "max_stop_before_target_5d_pct": 12.0,
            "min_target_before_stop_5d_pct": 75.0,
        },
        "shadow": _COMMON_SHADOW,
        "risk_review": {
            "min_low_5d_pct": -18.0,
            "max_bad_path_pct": 35.0,
            "max_stop5_pct": 25.0,
            "min_1d_pct": -4.0,
        },
    },
}

_TOUCH5_DD10_SHADOW = {
    "min_n": 8,
    "min_active_days": 3,
    "min_active_runs": 5,
    "min_touch5_dd10_5d_pct": 45.0,
    "min_low_5d_pct": -18.0,
}

_TOUCH5_DD10_PROFILES: Dict[str, Dict[str, Any]] = {
    "KOSPI": {
        "production": {
            "min_n": 30,
            "min_active_days": 15,
            "min_active_runs": 20,
            "min_touch5_dd10_5d_pct": 73.0,
            "min_low_5d_pct": -10.0,
        },
        "shadow": _TOUCH5_DD10_SHADOW,
        "risk_review": {
            "min_low_5d_pct": -10.0,
        },
    },
    "KOSDAQ": {
        "production": {
            "min_n": 45,
            "min_active_days": 20,
            "min_active_runs": 20,
            "min_touch5_dd10_5d_pct": 73.0,
            "min_low_5d_pct": -10.0,
        },
        "shadow": _TOUCH5_DD10_SHADOW,
        "risk_review": {
            "min_low_5d_pct": -10.0,
        },
    },
}

_PRODUCTION_ECONOMICS: Dict[str, Dict[str, float]] = {
    "KOSPI": {
        "min_net_avg_3d_pct": 0.25,
        "min_net_avg_5d_pct": 0.50,
    },
    "KOSDAQ": {
        "min_net_avg_3d_pct": 0.50,
        "min_net_avg_5d_pct": 1.00,
    },
}

_TOUCH5_DD10_ECONOMICS: Dict[str, Dict[str, float]] = {
    "KOSPI": {"min_expected_touch_policy_net_5d_pct": 0.25},
    "KOSDAQ": {"min_expected_touch_policy_net_5d_pct": 0.50},
}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            text = value.replace(",", "").replace("%", "").strip()
            if not text or text.lower() in {"none", "nan", "null", "-"}:
                return default
            value = text
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _safe_int(value: Any, default: int = 0) -> int:
    number = _safe_float(value)
    if number is None:
        return default
    return int(number)


def _market(identity: Mapping[str, Any], fallback: str = "") -> str:
    value = str(identity.get("market") or fallback or "").upper().strip()
    if value in _PROFILES:
        return value
    return "KOSPI" if value == "KS" else "KOSDAQ" if value == "KQ" else value


def _is_kis_feature_set(identity: Mapping[str, Any]) -> bool:
    feature_set = str(identity.get("feature_set") or "").lower().strip()
    return feature_set.startswith("kis")


def _is_touch5_dd10_label(identity: Mapping[str, Any]) -> bool:
    return str(identity.get("label") or "").strip() == TOUCH5_DD10_LABEL


def _check(
    checks: List[Dict[str, Any]],
    *,
    gate: str,
    name: str,
    actual: Any,
    expected: str,
    passed: bool,
    reason: str,
    blockers: List[str],
) -> None:
    checks.append(
        {
            "gate": gate,
            "name": name,
            "actual": actual,
            "expected": expected,
            "passed": bool(passed),
            "reason": reason if not passed else None,
        }
    )
    if not passed and reason not in blockers:
        blockers.append(reason)


def _reason_value(value: float) -> str:
    if float(value).is_integer():
        text = str(int(value))
    else:
        text = str(value).rstrip("0").rstrip(".")
    return text.replace(".", "p").replace("-", "neg")


def _threshold_checks(
    *,
    gate_name: str,
    metrics: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    checks: List[Dict[str, Any]],
    stop_aware: bool = False,
) -> List[str]:
    blockers: List[str] = []
    numeric_map = {
        "min_n": ("n", "n"),
        "min_active_days": ("active_days", "active_days"),
        "min_active_runs": ("active_runs", "active_runs"),
        "min_touch5_dd10_5d_pct": ("hit5_dd10_5d_pct", "hit5_dd10_5d"),
        "min_win_3d_pct": ("win_3d_pct", "win_3d"),
        "min_win_5d_pct": ("win_5d_pct", "win_5d"),
        "min_avg_3d_pct": ("avg_3d_pct", "avg_3d"),
        "min_avg_5d_pct": ("avg_5d_pct", "avg_5d"),
        "min_1d_pct": ("min_1d_pct", "min_1d"),
        "min_low_5d_pct": ("min_min_low_5d_pct", "min_low_5d"),
        "min_target_before_stop_5d_pct": ("target_before_stop_5d_pct", "target_before_stop_5d"),
    }
    for threshold_key, (metric_key, label) in numeric_map.items():
        if threshold_key not in thresholds:
            continue
        if stop_aware and threshold_key == "min_low_5d_pct" and metrics.get("min_ordered_exit_5d_pct") is not None:
            metric_key = "min_ordered_exit_5d_pct"
            label = "ordered_exit_floor_5d"
        actual = _safe_float(metrics.get(metric_key))
        expected = float(thresholds[threshold_key])
        passed = actual is not None and actual >= expected
        _check(
            checks,
            gate=gate_name,
            name=metric_key,
            actual=actual,
            expected=f">={expected:g}",
            passed=passed,
            reason=f"{label}_lt_{_reason_value(expected)}",
            blockers=blockers,
        )
    max_map = {
        "max_bad_path_pct": ("bad_path_pct", "bad_path"),
        "max_stop5_pct": ("stop5_pct", "stop5"),
        "max_stop_before_target_5d_pct": ("stop_before_target_5d_pct", "stop_before_target_5d"),
    }
    for threshold_key, (metric_key, label) in max_map.items():
        if threshold_key not in thresholds:
            continue
        actual = _safe_float(metrics.get(metric_key))
        expected = float(thresholds[threshold_key])
        passed = actual is not None and actual <= expected
        _check(
            checks,
            gate=gate_name,
            name=metric_key,
            actual=actual,
            expected=f"<={expected:g}",
            passed=passed,
            reason=f"{label}_gt_{_reason_value(expected)}",
            blockers=blockers,
        )
    return blockers


def _metric_or_computed_net(metrics: Mapping[str, Any], *, net_key: str, gross_key: str) -> float | None:
    explicit = _safe_float(metrics.get(net_key))
    if explicit is not None:
        return explicit
    gross = _safe_float(metrics.get(gross_key))
    return compute_net_return_pct(gross)


def _production_economic_checks(
    *,
    market_key: str,
    metrics: Mapping[str, Any],
    checks: List[Dict[str, Any]],
) -> tuple[List[str], Dict[str, Any]]:
    blockers: List[str] = []
    thresholds = _PRODUCTION_ECONOMICS.get(market_key, {})
    cost_model = TradableCostModel()
    economics: Dict[str, Any] = {
        "cost_model": asdict(cost_model),
        "gross_avg_3d_pct": _safe_float(metrics.get("avg_3d_pct")),
        "gross_avg_5d_pct": _safe_float(metrics.get("avg_5d_pct")),
        "net_avg_3d_pct": _metric_or_computed_net(metrics, net_key="net_avg_3d_pct", gross_key="avg_3d_pct"),
        "net_avg_5d_pct": _metric_or_computed_net(metrics, net_key="net_avg_5d_pct", gross_key="avg_5d_pct"),
    }
    for threshold_key, metric_key in (
        ("min_net_avg_3d_pct", "net_avg_3d_pct"),
        ("min_net_avg_5d_pct", "net_avg_5d_pct"),
    ):
        if threshold_key not in thresholds:
            continue
        actual = _safe_float(economics.get(metric_key))
        expected = float(thresholds[threshold_key])
        label = metric_key.replace("_pct", "")
        _check(
            checks,
            gate="production_economics",
            name=metric_key,
            actual=actual,
            expected=f">={expected:g}",
            passed=actual is not None and actual >= expected,
            reason=f"{label}_lt_{_reason_value(expected)}",
            blockers=blockers,
        )
    economics["thresholds"] = thresholds
    return blockers, economics


def _target_touch_economic_checks(
    *,
    market_key: str,
    metrics: Mapping[str, Any],
    checks: List[Dict[str, Any]],
) -> tuple[List[str], Dict[str, Any]]:
    blockers: List[str] = []
    thresholds = _TOUCH5_DD10_ECONOMICS.get(market_key, {})
    cost_model = TradableCostModel()
    target_net = compute_net_return_pct(5.0, cost_model)
    hit_rate = _safe_float(metrics.get("hit5_dd10_5d_pct"), _safe_float(metrics.get("label_win_pct")))
    loss_floor_pct = -10.0
    expected_net = None
    if target_net is not None and hit_rate is not None:
        win_prob = max(0.0, min(1.0, hit_rate / 100.0))
        expected_net = round(win_prob * float(target_net) + (1.0 - win_prob) * loss_floor_pct, 6)
    economics: Dict[str, Any] = {
        "policy": "target_touch_5d_dd10_after_buy_premium",
        "cost_model": asdict(cost_model),
        "target_touch_gross_pct": 5.0,
        "target_touch_net_pct": target_net,
        "loss_floor_pct": loss_floor_pct,
        "hit5_dd10_5d_pct": hit_rate,
        "expected_touch_policy_net_5d_pct": expected_net,
        "thresholds": thresholds,
    }
    for threshold_key, metric_key in (("min_expected_touch_policy_net_5d_pct", "expected_touch_policy_net_5d_pct"),):
        if threshold_key not in thresholds:
            continue
        actual = _safe_float(economics.get(metric_key))
        expected = float(thresholds[threshold_key])
        label = metric_key.replace("_pct", "")
        _check(
            checks,
            gate="production_economics",
            name=metric_key,
            actual=actual,
            expected=f">={expected:g}",
            passed=actual is not None and actual >= expected,
            reason=f"{label}_lt_{_reason_value(expected)}",
            blockers=blockers,
        )
    return blockers, economics


def evaluate_kis_model_gate(
    *,
    identity: Mapping[str, Any] | None,
    metrics: Mapping[str, Any] | None,
    market: str = "",
) -> Dict[str, Any]:
    """Evaluate a KIS challenger under production, shadow, and risk gates.

    This gate is intentionally stricter than generic challenger ranking. It
    separates the action decision from the model score so high-upside KIS
    models can remain visible as shadow candidates without being promoted when
    path risk or sample maturity is not strong enough. Win-rate thresholds use
    target-touch outcomes, not close-return-above-zero defensive outcomes.
    """

    identity = identity if isinstance(identity, Mapping) else {}
    metrics = metrics if isinstance(metrics, Mapping) else {}
    market_key = _market(identity, market)
    is_touch5_dd10 = _is_touch5_dd10_label(identity)
    profile = (_TOUCH5_DD10_PROFILES if is_touch5_dd10 else _PROFILES).get(market_key)
    checks: List[Dict[str, Any]] = []
    source_blockers: List[str] = []
    if not profile:
        source_blockers.append("unsupported_market")
    if not _is_kis_feature_set(identity):
        source_blockers.append("feature_set_not_kis")
    if not metrics:
        source_blockers.append("metrics_missing")
    for reason in source_blockers:
        checks.append(
            {
                "gate": "source",
                "name": reason,
                "actual": False,
                "expected": "real KIS model identity and completed metrics",
                "passed": False,
                "reason": reason,
            }
        )
    if source_blockers:
        return {
            "version": KIS_MODEL_GATE_VERSION,
            "win_metric_semantics": WIN_METRIC_SEMANTICS,
            "market": market_key,
            "status": "blocked",
            "production_ready": False,
            "shadow_display_allowed": False,
            "deep_analysis_allowed": False,
            "risk_review_required": False,
            "source_ok": False,
            "production_blocking_reasons": source_blockers,
            "shadow_blocking_reasons": source_blockers,
            "risk_review_reasons": [],
            "blocking_reasons": source_blockers,
            "checks": checks,
            "action": "block",
        }

    production_blockers = _threshold_checks(
        gate_name="production",
        metrics=metrics,
        thresholds=profile["production"],
        checks=checks,
        stop_aware=is_touch5_dd10,
    )
    shadow_blockers = _threshold_checks(
        gate_name="shadow",
        metrics=metrics,
        thresholds=profile["shadow"],
        checks=checks,
        stop_aware=is_touch5_dd10,
    )

    risk_review_reasons = _threshold_checks(
        gate_name="risk_review",
        metrics=metrics,
        thresholds=profile["risk_review"],
        checks=checks,
        stop_aware=is_touch5_dd10,
    )
    if is_touch5_dd10:
        economic_blockers, economics = _target_touch_economic_checks(
            market_key=market_key,
            metrics=metrics,
            checks=checks,
        )
    else:
        economic_blockers, economics = _production_economic_checks(
            market_key=market_key,
            metrics=metrics,
            checks=checks,
        )

    production_blocking_reasons = list(dict.fromkeys([*production_blockers, *economic_blockers]))
    production_ready = not production_blocking_reasons
    shadow_ready = production_ready or not shadow_blockers
    risk_review_required = bool(risk_review_reasons) and shadow_ready and not production_ready
    if production_ready:
        status = "production_ready"
        action = "allow_operational_promotion"
    elif shadow_ready and risk_review_required:
        status = "shadow_risk_review"
        action = "show_shadow_with_risk_review"
    elif shadow_ready:
        status = "shadow_ready"
        action = "show_shadow_only"
    else:
        status = "blocked"
        action = "block"

    return {
        "version": KIS_MODEL_GATE_VERSION,
        "win_metric_semantics": WIN_METRIC_SEMANTICS,
        "label_gate_profile": "touch5_dd10" if is_touch5_dd10 else "default",
        "market": market_key,
        "status": status,
        "production_ready": production_ready,
        "shadow_display_allowed": shadow_ready,
        "deep_analysis_allowed": shadow_ready,
        "risk_review_required": risk_review_required,
        "source_ok": True,
        "production_economics": economics,
        "production_blocking_reasons": production_blocking_reasons,
        "shadow_blocking_reasons": shadow_blockers,
        "risk_review_reasons": risk_review_reasons,
        "blocking_reasons": production_blocking_reasons if not production_ready else [],
        "checks": checks,
        "action": action,
    }


__all__ = ["KIS_MODEL_GATE_VERSION", "WIN_METRIC_SEMANTICS", "evaluate_kis_model_gate"]
