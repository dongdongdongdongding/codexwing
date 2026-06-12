#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
import pandas as pd  # noqa: E402

from modules.close_failure_prior_profile import (  # noqa: E402
    build_close_failure_prior_profile,
    write_close_failure_prior_profile,
)
from modules.kis_model_gate import evaluate_kis_model_gate  # noqa: E402
from modules.kis_shadow_exit_policy import build_kis_shadow_exit_policy  # noqa: E402
from multi_agent.tools.train_scan_universe_admission_challenger import (  # noqa: E402
    attach_close_failure_risk_features,
    train_final_model,
)


DEFAULT_PREPARED_CACHE = ROOT / "runtime_state/reports/learning/scan_universe_admission_challenger_buy_premium_v2_idscan_20260401_20260528.pkl"
DEFAULT_PROFILE_OUTPUT = ROOT / "runtime_state/reports/learning/close_failure_prior_profile_latest.json"
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/learning/kis_shadow_admission_model_deployment.json"
DEFAULT_MODEL_DIR = ROOT / "models/scan_universe_challengers"
DEFAULT_SOURCES = {
    "KOSPI": ROOT / "runtime_state/reports/learning/scan_universe_admission_challenger_failure_risk_numeric_20260401_20260528.json",
    "KOSDAQ": ROOT / "runtime_state/reports/learning/scan_universe_admission_challenger_failure_risk_top5_20260401_20260528.json",
}
REPORT_VERSION = "kis_shadow_admission_model_deployment_v1"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def _read_sources(raw: str) -> Dict[str, Path]:
    if not raw.strip():
        return dict(DEFAULT_SOURCES)
    out: Dict[str, Path] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        market, path = item.split("=", 1)
        out[market.strip().upper()] = Path(path.strip())
    return out


def _read_selection_rules(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in str(raw or "").split(","):
        if not item.strip():
            continue
        market, rule = item.split("=", 1)
        out[market.strip().upper()] = rule.strip()
    return out


def _best_kis_from_source(path: Path, market: str, *, selection_rule: str = "") -> Dict[str, Any]:
    report = _load_json(path)
    best = report.get("best_kis") if isinstance(report.get("best_kis"), dict) else {}
    if selection_rule or best.get("market") != market:
        candidate_rows = report.get("top_kis_results") or report.get("top_results") or []
        candidates = [
            row
            for row in candidate_rows
            if isinstance(row, dict)
            and row.get("market") == market
            and (not selection_rule or row.get("selection_rule") == selection_rule)
        ]
        if not candidates:
            raise ValueError(f"{market}: selected KIS rule not found in {path}: {selection_rule or '<market best>'}")
        best = candidates[0]
    gate = evaluate_kis_model_gate(
        identity={
            "market": best.get("market"),
            "label": best.get("label"),
            "feature_set": best.get("feature_set"),
            "model": best.get("model"),
            "topn": best.get("topn"),
            "prob_threshold": best.get("prob_threshold"),
            "tail_risk_prob_threshold": best.get("tail_risk_prob_threshold"),
            "selection_rule": best.get("selection_rule"),
        },
        metrics=best.get("metrics") or {},
        market=market,
    )
    if not gate.get("shadow_display_allowed"):
        raise ValueError(f"{market}: selected model is not allowed for shadow display: {gate.get('status')}")
    best = dict(best)
    best["kis_model_gate"] = gate
    best["_source_report"] = str(path)
    return best


def _example_exit_policy(best: Dict[str, Any]) -> Dict[str, Any]:
    return build_kis_shadow_exit_policy(
        features={},
        metrics=best.get("metrics") or {},
        identity={
            "label": best.get("label"),
            "feature_set": best.get("feature_set"),
            "model": best.get("model"),
            "selection_rule": best.get("selection_rule"),
        },
        market=str(best.get("market") or ""),
    )


def _save_shadow_bundle(data: pd.DataFrame, best: Dict[str, Any], *, model_dir: Path, profile_path: Path) -> Dict[str, Any]:
    result = train_final_model(data, best, output_dir=model_dir)
    if not result.get("saved"):
        return result
    model_path = Path(result["model_path"])
    bundle = joblib.load(model_path)
    bundle["deployment_scope"] = "kis_operational_shadow"
    bundle["shadow_only"] = True
    bundle["source_report"] = best.get("_source_report")
    bundle["close_failure_prior_profile_path"] = str(profile_path)
    bundle["kis_model_gate"] = best.get("kis_model_gate")
    bundle["dynamic_exit_policy_template"] = _example_exit_policy(best)
    bundle["validation"] = {
        **(bundle.get("validation") if isinstance(bundle.get("validation"), dict) else {}),
        "kis_model_gate": best.get("kis_model_gate"),
        "source_report": best.get("_source_report"),
        "shadow_only": True,
    }
    joblib.dump(bundle, model_path)
    return {
        **result,
        "shadow_only": True,
        "deployment_scope": "kis_operational_shadow",
        "source_report": best.get("_source_report"),
        "kis_model_gate_status": (best.get("kis_model_gate") or {}).get("status"),
        "dynamic_exit_policy_template": bundle["dynamic_exit_policy_template"],
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    prepared_cache = Path(args.prepared_cache)
    data = pd.read_pickle(prepared_cache)
    data = attach_close_failure_risk_features(data)
    profile = build_close_failure_prior_profile(data, source_path=str(prepared_cache))
    profile_path = write_close_failure_prior_profile(profile, Path(args.profile_output))
    sources = _read_sources(args.sources)
    selection_rules = _read_selection_rules(args.selection_rules)
    deployments: Dict[str, Any] = {}
    for market, source in sources.items():
        best = _best_kis_from_source(source, market, selection_rule=selection_rules.get(market, ""))
        deployments[market] = {
            "identity": {
                "market": best.get("market"),
                "label": best.get("label"),
                "feature_set": best.get("feature_set"),
                "model": best.get("model"),
                "topn": best.get("topn"),
                "prob_threshold": best.get("prob_threshold"),
                "tail_risk_prob_threshold": best.get("tail_risk_prob_threshold"),
                "selection_rule": best.get("selection_rule"),
                "quality_score": best.get("quality_score"),
            },
            "metrics": best.get("metrics") or {},
            "model": _save_shadow_bundle(data, best, model_dir=Path(args.model_dir), profile_path=profile_path),
        }
    return {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prepared_cache": str(prepared_cache),
        "prepared_rows": int(len(data)),
        "close_failure_prior_profile": {
            "path": str(profile_path),
            "rows": profile.get("rows"),
            "touch5_rows": profile.get("touch5_rows"),
            "max_trade_date": profile.get("max_trade_date"),
        },
        "deployments": deployments,
        "no_dummy_data": True,
    }


def write_report(report: Dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    lines = [
        "# KIS Shadow Admission Model Deployment",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- prepared_rows: `{report.get('prepared_rows')}`",
        f"- close_failure_prior_profile: `{(report.get('close_failure_prior_profile') or {}).get('path')}`",
        f"- no_dummy_data: `{report.get('no_dummy_data')}`",
        "",
        "| market | label | feature_set | model | rule | model_path | gate | TP/SL/hold |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for market, row in (report.get("deployments") or {}).items():
        identity = row.get("identity") or {}
        model = row.get("model") or {}
        policy = model.get("dynamic_exit_policy_template") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(market),
                    str(identity.get("label")),
                    str(identity.get("feature_set")),
                    str(identity.get("model")),
                    str(identity.get("selection_rule")),
                    str(model.get("model_path")),
                    str(model.get("kis_model_gate_status")),
                    f"{policy.get('target_tp_pct')}%/{policy.get('stop_sl_pct')}%/{policy.get('hold_days')}d",
                ]
            )
            + " |"
        )
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--sources", default="")
    parser.add_argument(
        "--selection-rules",
        default="",
        help="Optional comma-separated MARKET=selection_rule overrides. Selects from top_kis_results instead of report best_kis.",
    )
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--profile-output", default=str(DEFAULT_PROFILE_OUTPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    report = build_report(args)
    write_report(report, Path(args.output))
    print(json.dumps({"output": args.output, "markets": sorted((report.get("deployments") or {}).keys())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
