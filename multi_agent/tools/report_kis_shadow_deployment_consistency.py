#!/usr/bin/env python3
"""Verify KIS shadow comparison, deployment report, and model bundles agree."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REPORT_VERSION = "kis_shadow_deployment_consistency_v1"
DEFAULT_COMPARISON = ROOT / "runtime_state/reports/learning/kis_model_market_comparison.json"
DEFAULT_DEPLOYMENT = ROOT / "runtime_state/reports/learning/kis_shadow_admission_model_deployment.json"
DEFAULT_MODEL_DIR = ROOT / "models/scan_universe_challengers"
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/learning/kis_shadow_deployment_consistency_20260613.json"
REQUIRED_MARKETS = ("KOSPI", "KOSDAQ")
IDENTITY_KEYS = (
    "market",
    "label",
    "feature_set",
    "model",
    "topn",
    "prob_threshold",
    "tail_risk_prob_threshold",
    "selection_rule",
)
METRIC_KEYS = (
    "n",
    "active_days",
    "active_runs",
    "buy_premium_pct",
    "hit5_dd10_5d_pct",
    "hit10_5d_pct",
    "avg_5d_pct",
    "min_min_low_5d_pct",
    "avg_max_high_5d_pct",
    "target_before_stop_5d_pct",
    "stop_before_target_5d_pct",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, 6)
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _round_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, 10)


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        return _round_float(left) == _round_float(right)
    return left == right


def _identity_subset(identity: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: identity.get(key) for key in IDENTITY_KEYS if key in identity}


def _bundle_identity(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "market": bundle.get("market"),
        "label": bundle.get("label"),
        "feature_set": bundle.get("feature_set"),
        "model": bundle.get("model_name"),
        "topn": bundle.get("topn"),
        "prob_threshold": bundle.get("prob_threshold"),
        "tail_risk_prob_threshold": bundle.get("tail_risk_prob_threshold"),
        "selection_rule": bundle.get("selection_rule"),
    }


def _bundle_metrics(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    validation = bundle.get("validation") if isinstance(bundle.get("validation"), Mapping) else {}
    metrics = validation.get("metrics") if isinstance(validation.get("metrics"), Mapping) else {}
    return {key: metrics.get(key) for key in METRIC_KEYS if key in metrics}


def _model_path_from_identity(model_dir: Path, identity: Mapping[str, Any]) -> Path:
    rule = str(identity.get("selection_rule") or f"top{identity.get('topn')}").replace(".", "p")
    return (
        model_dir
        / f"{str(identity.get('market')).lower()}__{identity.get('label')}__{identity.get('feature_set')}__{identity.get('model')}__{rule}.pkl"
    )


def _alias_path(model_dir: Path, market: str) -> Path:
    return model_dir / f"{market.lower()}__touch5_dd10_5d__kis_shadow_best_effort_current.pkl"


def _mismatches(left: Mapping[str, Any], right: Mapping[str, Any], *, keys: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    mismatched: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        if not _same_value(left.get(key), right.get(key)):
            mismatched[key] = {"left": left.get(key), "right": right.get(key)}
    return mismatched


def _gate_summary(gate: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "status": gate.get("status"),
        "production_ready": bool(gate.get("production_ready")),
        "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
        "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
    }


def _market_report(
    *,
    market: str,
    comparison: Mapping[str, Any],
    deployment: Mapping[str, Any],
    model_dir: Path,
) -> Dict[str, Any]:
    issues = []
    comparison_markets = comparison.get("markets") if isinstance(comparison.get("markets"), Mapping) else {}
    comparison_row = comparison_markets.get(market) if isinstance(comparison_markets.get(market), Mapping) else {}
    current = comparison_row.get("current_kis_model") if isinstance(comparison_row.get("current_kis_model"), Mapping) else {}
    comparison_identity = _identity_subset(current.get("identity") if isinstance(current.get("identity"), Mapping) else {})
    comparison_gate = _gate_summary(current.get("kis_model_gate") if isinstance(current.get("kis_model_gate"), Mapping) else {})
    comparison_metrics = current.get("metrics") if isinstance(current.get("metrics"), Mapping) else {}

    deployments = deployment.get("deployments") if isinstance(deployment.get("deployments"), Mapping) else {}
    deployment_row = deployments.get(market) if isinstance(deployments.get(market), Mapping) else {}
    deployment_identity = _identity_subset(deployment_row.get("identity") if isinstance(deployment_row.get("identity"), Mapping) else {})
    deployment_metrics = deployment_row.get("metrics") if isinstance(deployment_row.get("metrics"), Mapping) else {}
    deployment_model = deployment_row.get("model") if isinstance(deployment_row.get("model"), Mapping) else {}
    deployment_gate = {
        "status": deployment_model.get("kis_model_gate_status"),
        "source_report": deployment_model.get("source_report"),
    }

    if not comparison_identity:
        issues.append("comparison_current_kis_model_missing")
    if not deployment_identity:
        issues.append("deployment_identity_missing")
    if not comparison_metrics:
        issues.append("comparison_metrics_missing")
    if not deployment_metrics:
        issues.append("deployment_metrics_missing")
    identity_mismatches = _mismatches(comparison_identity, deployment_identity, keys=IDENTITY_KEYS)
    if identity_mismatches:
        issues.append("comparison_deployment_identity_mismatch")
    metric_mismatches = _mismatches(comparison_metrics, deployment_metrics, keys=METRIC_KEYS)
    if metric_mismatches:
        issues.append("comparison_deployment_metric_mismatch")

    expected_path = _model_path_from_identity(model_dir, comparison_identity) if comparison_identity else None
    deployed_path = Path(str(deployment_model.get("model_path") or "")) if deployment_model.get("model_path") else None
    if expected_path and not expected_path.exists():
        issues.append("expected_model_bundle_missing")
    if deployed_path and not deployed_path.exists():
        issues.append("deployment_model_path_missing")
    if expected_path and deployed_path and expected_path.resolve() != deployed_path.resolve():
        issues.append("deployment_model_path_mismatch")
    deployment_gate_mismatches = _mismatches(comparison_gate, deployment_gate, keys=("status",))
    if deployment_gate_mismatches:
        issues.append("comparison_deployment_gate_mismatch")

    bundle_identity: Dict[str, Any] = {}
    bundle_gate: Dict[str, Any] = {}
    bundle_metrics: Dict[str, Any] = {}
    if expected_path and expected_path.exists():
        bundle = joblib.load(expected_path)
        bundle_identity = _bundle_identity(bundle if isinstance(bundle, Mapping) else {})
        bundle_metrics = _bundle_metrics(bundle if isinstance(bundle, Mapping) else {})
        bundle_gate = _gate_summary((bundle.get("kis_model_gate") if isinstance(bundle, Mapping) else {}) or {})
    bundle_mismatches = _mismatches(comparison_identity, bundle_identity, keys=IDENTITY_KEYS)
    if bundle_mismatches:
        issues.append("comparison_bundle_identity_mismatch")
    bundle_metric_mismatches = _mismatches(comparison_metrics, bundle_metrics, keys=METRIC_KEYS)
    if bundle_metric_mismatches:
        issues.append("comparison_bundle_metric_mismatch")
    gate_mismatches = _mismatches(comparison_gate, bundle_gate, keys=("status", "production_ready", "shadow_display_allowed"))
    if gate_mismatches:
        issues.append("comparison_bundle_gate_mismatch")

    alias_path = _alias_path(model_dir, market)
    alias_identity: Dict[str, Any] = {}
    alias_gate: Dict[str, Any] = {}
    alias_metrics: Dict[str, Any] = {}
    alias_gate_mismatches: Dict[str, Dict[str, Any]] = {}
    alias_metric_mismatches: Dict[str, Dict[str, Any]] = {}
    if not alias_path.exists():
        issues.append("current_alias_missing")
    else:
        alias_bundle = joblib.load(alias_path)
        alias_identity = _bundle_identity(alias_bundle if isinstance(alias_bundle, Mapping) else {})
        alias_metrics = _bundle_metrics(alias_bundle if isinstance(alias_bundle, Mapping) else {})
        alias_gate = _gate_summary((alias_bundle.get("kis_model_gate") if isinstance(alias_bundle, Mapping) else {}) or {})
        alias_mismatches = _mismatches(comparison_identity, alias_identity, keys=IDENTITY_KEYS)
        if alias_mismatches:
            issues.append("comparison_alias_identity_mismatch")
        alias_metric_mismatches = _mismatches(comparison_metrics, alias_metrics, keys=METRIC_KEYS)
        if alias_metric_mismatches:
            issues.append("comparison_alias_metric_mismatch")
        alias_gate_mismatches = _mismatches(
            comparison_gate,
            alias_gate,
            keys=("status", "production_ready", "shadow_display_allowed"),
        )
        if alias_gate_mismatches:
            issues.append("comparison_alias_gate_mismatch")
    return {
        "market": market,
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "comparison_identity": comparison_identity,
        "deployment_identity": deployment_identity,
        "bundle_identity": bundle_identity,
        "alias_identity": alias_identity,
        "comparison_metrics": {key: comparison_metrics.get(key) for key in METRIC_KEYS if key in comparison_metrics},
        "deployment_metrics": {key: deployment_metrics.get(key) for key in METRIC_KEYS if key in deployment_metrics},
        "bundle_metrics": bundle_metrics,
        "alias_metrics": alias_metrics,
        "comparison_gate": comparison_gate,
        "deployment_gate": deployment_gate,
        "bundle_gate": bundle_gate,
        "alias_gate": alias_gate,
        "identity_mismatches": identity_mismatches,
        "metric_mismatches": metric_mismatches,
        "bundle_mismatches": bundle_mismatches,
        "bundle_metric_mismatches": bundle_metric_mismatches,
        "gate_mismatches": gate_mismatches,
        "deployment_gate_mismatches": deployment_gate_mismatches,
        "alias_metric_mismatches": alias_metric_mismatches,
        "alias_gate_mismatches": alias_gate_mismatches,
        "expected_model_path": _rel(expected_path) if expected_path else None,
        "deployment_model_path": _rel(deployed_path) if deployed_path else None,
        "alias_model_path": _rel(alias_path),
    }


def build_report(
    *,
    comparison_path: Path,
    deployment_path: Path,
    model_dir: Path,
    required_markets: Iterable[str] = REQUIRED_MARKETS,
) -> Dict[str, Any]:
    comparison = _load_json(comparison_path)
    deployment = _load_json(deployment_path)
    market_reports = [
        _market_report(market=market, comparison=comparison, deployment=deployment, model_dir=model_dir)
        for market in required_markets
    ]
    all_pass = bool(market_reports) and all(row.get("status") == "pass" for row in market_reports)
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "inputs": {
            "comparison_report": _rel(comparison_path),
            "deployment_report": _rel(deployment_path),
            "model_dir": _rel(model_dir),
        },
        "required_markets": list(required_markets),
        "markets": market_reports,
        "decision": {
            "status": "pass" if all_pass else "fail",
            "deployment_consistent": all_pass,
            "production_replacement_ready": False,
            "recommended_action": (
                "use_current_kis_shadow_deployment"
                if all_pass
                else "block_shadow_deployment_until_identity_mismatches_are_fixed"
            ),
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    lines = [
        "# KIS Shadow Deployment Consistency",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- status: `{decision.get('status')}`",
        f"- deployment_consistent: `{decision.get('deployment_consistent')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        "",
        "| market | status | rule | gate | model | alias | issues |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report.get("markets") or []:
        if not isinstance(row, Mapping):
            continue
        identity = row.get("comparison_identity") if isinstance(row.get("comparison_identity"), Mapping) else {}
        gate = row.get("comparison_gate") if isinstance(row.get("comparison_gate"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("market")),
                    str(row.get("status")),
                    str(identity.get("selection_rule")),
                    str(gate.get("status")),
                    str(row.get("expected_model_path")),
                    str(row.get("alias_model_path")),
                    ", ".join(row.get("issues") or []) or "-",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison-report", default=str(DEFAULT_COMPARISON))
    parser.add_argument("--deployment-report", default=str(DEFAULT_DEPLOYMENT))
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--markets", default=",".join(REQUIRED_MARKETS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    markets = [item.strip().upper() for item in str(args.markets).split(",") if item.strip()]
    report = build_report(
        comparison_path=Path(args.comparison_report),
        deployment_path=Path(args.deployment_report),
        model_dir=Path(args.model_dir),
        required_markets=markets,
    )
    write_report(report, Path(args.output))
    print(json.dumps({"output": args.output, "decision": report.get("decision")}, ensure_ascii=False, indent=2))
    return 0 if (report.get("decision") or {}).get("deployment_consistent") else 2


if __name__ == "__main__":
    raise SystemExit(main())
