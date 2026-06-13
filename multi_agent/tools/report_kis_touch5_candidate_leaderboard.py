#!/usr/bin/env python3
"""Build a tracked-report leaderboard for KIS touch5_dd10 candidates.

The report re-evaluates every discovered candidate with the shared
``evaluate_kis_model_gate`` contract instead of trusting stale embedded gates.
It is intentionally a research/audit artifact; promotion still requires the
deployment and model-bundle consistency checks to pass.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_gate import TOUCH5_DD10_LABEL, evaluate_kis_model_gate


REPORT_VERSION = "kis_touch5_candidate_leaderboard_v2"
DEFAULT_REPORT_DIR = ROOT / "runtime_state/reports/learning"
DEFAULT_CURRENT_COMPARISON = DEFAULT_REPORT_DIR / "kis_model_market_comparison.json"
DEFAULT_OUTPUT = DEFAULT_REPORT_DIR / "kis_touch5_candidate_leaderboard_20260613.json"
REQUIRED_MARKETS = ("KOSPI", "KOSDAQ")
SAMPLE_CHECKS = ("n", "active_days", "active_runs")
SAMPLE_BLOCKER_PREFIXES = ("n_lt", "active_days_lt", "active_runs_lt")
EXCLUDED_NAME_PARTS = (
    "deployment",
    "comparison",
    "objective_verification",
    "shadow_research_verification",
    "research_goal_validation",
    "readiness",
    "theme",
    "smoke",
    "proxy_feature_gap",
    "cache_augmented_proxy",
)
INCLUDED_NAME_PARTS = (
    "touch5_dd10",
    "three_stage",
    "tail_safe_policy",
    "sidecar_threshold_sweep",
    "historical_best_effort",
)
PREFERRED_VALIDATION_MODE = "dayfold_realistic_coverage"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip().replace("%", "").replace(",", "")
            if not text or text.lower() in {"none", "nan", "null", "-"}:
                return None
            value = text
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 6) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number, digits)


def _field(row: Mapping[str, Any], key: str) -> Any:
    nested = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    value = row.get(key)
    if isinstance(value, Mapping):
        value = None
    return value if value is not None else nested.get(key)


def _identity(row: Mapping[str, Any]) -> Dict[str, Any]:
    nested = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    return {
        "market": _field(row, "market"),
        "label": _field(row, "label") or TOUCH5_DD10_LABEL,
        "feature_set": _field(row, "feature_set"),
        "model": _field(row, "model"),
        "topn": _field(row, "topn"),
        "prob_threshold": _field(row, "prob_threshold") or nested.get("score_threshold"),
        "tail_risk_prob_threshold": _field(row, "tail_risk_prob_threshold") or nested.get("max_stop_probability"),
        "selection_rule": _field(row, "selection_rule") or nested.get("score_mode"),
        "score_mode": row.get("score_mode") or nested.get("score_mode"),
    }


def _is_kis_touch5_candidate(row: Mapping[str, Any]) -> bool:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    if not metrics:
        return False
    identity = _identity(row)
    market = str(identity.get("market") or "").upper()
    feature_set = str(identity.get("feature_set") or "").lower()
    label = str(identity.get("label") or "")
    return (
        market in REQUIRED_MARKETS
        and feature_set.startswith("kis")
        and (label == TOUCH5_DD10_LABEL or "hit5_dd10_5d_pct" in metrics)
    )


def _extract_rows(payload: Any, *, source_path: Path, out: List[Dict[str, Any]]) -> None:
    if isinstance(payload, Mapping):
        if _is_kis_touch5_candidate(payload):
            identity = _identity(payload)
            market = str(identity.get("market") or "").upper()
            metrics = dict(payload.get("metrics") or {})
            gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
            out.append(
                {
                    "source_path": _rel(source_path),
                    "identity": identity,
                    "metrics": metrics,
                    "quality_score": payload.get("quality_score"),
                    "reevaluated_gate": gate,
                }
            )
        for value in payload.values():
            _extract_rows(value, source_path=source_path, out=out)
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for value in payload:
            _extract_rows(value, source_path=source_path, out=out)


def _tracked_learning_reports(report_dir: Path) -> set[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", str(report_dir.relative_to(ROOT))],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except Exception:
        return set()
    return {(ROOT / line.strip()).resolve() for line in result.stdout.splitlines() if line.strip().endswith(".json")}


def discover_report_paths(report_dir: Path, *, tracked_only: bool = True) -> List[Path]:
    paths = sorted(report_dir.glob("*.json"))
    if tracked_only:
        tracked = _tracked_learning_reports(report_dir)
        paths = [path for path in paths if path.resolve() in tracked]
    selected: List[Path] = []
    for path in paths:
        name = path.name.lower()
        if any(part in name for part in EXCLUDED_NAME_PARTS):
            continue
        if not any(part in name for part in INCLUDED_NAME_PARTS):
            continue
        selected.append(path)
    return selected


def _dedupe_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    return (
        row.get("source_path"),
        identity.get("market"),
        identity.get("label"),
        identity.get("feature_set"),
        identity.get("model"),
        identity.get("selection_rule"),
        identity.get("topn"),
        identity.get("prob_threshold"),
        identity.get("tail_risk_prob_threshold"),
        metrics.get("n"),
        metrics.get("active_days"),
        metrics.get("active_runs"),
        metrics.get("hit5_dd10_5d_pct"),
        metrics.get("avg_5d_pct"),
        metrics.get("min_min_low_5d_pct"),
    )


def _dedupe(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for row in rows:
        key = _dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _sample_progress(gate: Mapping[str, Any]) -> Dict[str, Any]:
    checks = [row for row in gate.get("checks") or [] if isinstance(row, Mapping) and row.get("gate") == "production"]
    parts: Dict[str, Dict[str, Any]] = {}
    for row in checks:
        name = str(row.get("name") or "")
        if name not in SAMPLE_CHECKS:
            continue
        actual = _safe_float(row.get("actual")) or 0.0
        expected_text = str(row.get("expected") or "").replace(">=", "")
        expected = _safe_float(expected_text) or 0.0
        ratio = min(actual / expected, 1.0) if expected > 0 else 0.0
        parts[name] = {
            "actual": _round(actual),
            "expected": _round(expected),
            "missing": _round(max(expected - actual, 0.0)),
            "completion_pct": _round(ratio * 100.0),
        }
    completion_values = [float(part["completion_pct"]) for part in parts.values() if part.get("completion_pct") is not None]
    return {
        "checks": parts,
        "completion_pct": _round(sum(completion_values) / len(completion_values)) if completion_values else None,
    }


def _compact_candidate(row: Mapping[str, Any]) -> Dict[str, Any]:
    identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    gate = row.get("reevaluated_gate") if isinstance(row.get("reevaluated_gate"), Mapping) else {}
    production_reasons = [str(item) for item in gate.get("production_blocking_reasons") or []]
    non_sample_blockers = [
        reason for reason in production_reasons if not reason.startswith(SAMPLE_BLOCKER_PREFIXES)
    ]
    sample_progress = _sample_progress(gate)
    source_path = str(row.get("source_path") or "")
    return {
        "source_path": row.get("source_path"),
        "validation_mode": _validation_mode(source_path),
        "identity": {
            key: identity.get(key)
            for key in (
                "market",
                "label",
                "feature_set",
                "model",
                "selection_rule",
                "topn",
                "prob_threshold",
                "tail_risk_prob_threshold",
                "score_mode",
            )
        },
        "metrics": {
            "n": metrics.get("n"),
            "active_days": metrics.get("active_days"),
            "active_runs": metrics.get("active_runs"),
            "buy_premium_pct": metrics.get("buy_premium_pct"),
            "hit5_dd10_5d_pct": metrics.get("hit5_dd10_5d_pct"),
            "hit10_5d_pct": metrics.get("hit10_5d_pct"),
            "avg_5d_pct": metrics.get("avg_5d_pct"),
            "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
            "avg_max_high_5d_pct": metrics.get("avg_max_high_5d_pct"),
            "target_before_stop_5d_pct": metrics.get("target_before_stop_5d_pct"),
            "stop_before_target_5d_pct": metrics.get("stop_before_target_5d_pct"),
        },
        "quality_score": row.get("quality_score"),
        "gate": {
            "status": gate.get("status"),
            "production_ready": bool(gate.get("production_ready")),
            "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
            "risk_review_required": bool(gate.get("risk_review_required")),
            "production_blocking_reasons": production_reasons,
            "non_sample_blockers": non_sample_blockers,
            "sample_only_blocked": bool(gate.get("shadow_display_allowed")) and bool(production_reasons) and not non_sample_blockers,
            "production_economics": gate.get("production_economics") or {},
        },
        "sample_progress": sample_progress,
    }


def _validation_mode(source_path: str) -> str:
    name = Path(str(source_path or "")).name.lower()
    if PREFERRED_VALIDATION_MODE in name:
        return PREFERRED_VALIDATION_MODE
    if "dayfold" in name:
        return "dayfold"
    if "longfold" in name:
        return "longfold"
    return "legacy"


def _preferred_validation_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[List[Mapping[str, Any]], bool]:
    preferred = [row for row in rows if row.get("validation_mode") == PREFERRED_VALIDATION_MODE]
    return (preferred, True) if preferred else (list(rows), False)


def _status_rank(row: Mapping[str, Any]) -> int:
    gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
    if gate.get("production_ready"):
        return 0
    if gate.get("sample_only_blocked"):
        return 1
    if gate.get("shadow_display_allowed"):
        return 2
    return 3


def _sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    progress = row.get("sample_progress") if isinstance(row.get("sample_progress"), Mapping) else {}
    return (
        _status_rank(row),
        -float(progress.get("completion_pct") or 0.0),
        -float(metrics.get("hit5_dd10_5d_pct") or 0.0),
        -float(metrics.get("avg_5d_pct") or -999.0),
        -float(metrics.get("min_min_low_5d_pct") or -999.0),
        -int(metrics.get("n") or 0),
    )


def _current_candidates(current_comparison_path: Path) -> Dict[str, Dict[str, Any]]:
    if not current_comparison_path.exists():
        return {}
    report = _load_json(current_comparison_path)
    markets = report.get("markets") if isinstance(report.get("markets"), Mapping) else {}
    out: Dict[str, Dict[str, Any]] = {}
    for market, payload in markets.items():
        if market not in REQUIRED_MARKETS or not isinstance(payload, Mapping):
            continue
        current = payload.get("current_kis_model") if isinstance(payload.get("current_kis_model"), Mapping) else {}
        identity = current.get("identity") if isinstance(current.get("identity"), Mapping) else {}
        metrics = current.get("metrics") if isinstance(current.get("metrics"), Mapping) else {}
        gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
        out[market] = _compact_candidate(
            {
                "source_path": payload.get("source_path") or _rel(current_comparison_path),
                "identity": identity,
                "metrics": metrics,
                "quality_score": current.get("quality_score"),
                "reevaluated_gate": gate,
            }
        )
    return out


def _is_upgrade(candidate: Mapping[str, Any], current: Mapping[str, Any] | None) -> bool:
    if not current:
        return False
    gate = candidate.get("gate") if isinstance(candidate.get("gate"), Mapping) else {}
    if not gate.get("sample_only_blocked") and not gate.get("production_ready"):
        return False
    c_metrics = candidate.get("metrics") if isinstance(candidate.get("metrics"), Mapping) else {}
    cur_metrics = current.get("metrics") if isinstance(current.get("metrics"), Mapping) else {}
    c_progress = candidate.get("sample_progress") if isinstance(candidate.get("sample_progress"), Mapping) else {}
    cur_progress = current.get("sample_progress") if isinstance(current.get("sample_progress"), Mapping) else {}
    if float(c_metrics.get("hit5_dd10_5d_pct") or 0.0) < float(cur_metrics.get("hit5_dd10_5d_pct") or 0.0):
        return False
    if float(c_metrics.get("min_min_low_5d_pct") or -999.0) < -10.0:
        return False
    progress_gain = float(c_progress.get("completion_pct") or 0.0) - float(cur_progress.get("completion_pct") or 0.0)
    sample_gain = int(c_metrics.get("n") or 0) - int(cur_metrics.get("n") or 0)
    avg_gain = float(c_metrics.get("avg_5d_pct") or -999.0) - float(cur_metrics.get("avg_5d_pct") or -999.0)
    return progress_gain >= 5.0 and sample_gain > 0 and avg_gain >= 0.0


def _high_precision_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    progress = row.get("sample_progress") if isinstance(row.get("sample_progress"), Mapping) else {}
    return (
        -float(metrics.get("hit5_dd10_5d_pct") or 0.0),
        -float(metrics.get("avg_5d_pct") or -999.0),
        -float(metrics.get("min_min_low_5d_pct") or -999.0),
        -float(progress.get("completion_pct") or 0.0),
        -int(metrics.get("active_runs") or 0),
        -int(metrics.get("n") or 0),
    )


def _is_high_precision_sample_only(row: Mapping[str, Any]) -> bool:
    gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
    progress = row.get("sample_progress") if isinstance(row.get("sample_progress"), Mapping) else {}
    return bool(gate.get("sample_only_blocked")) and float(progress.get("completion_pct") or 0.0) >= 80.0


def _market_report(market: str, rows: Sequence[Mapping[str, Any]], current: Mapping[str, Any] | None) -> Dict[str, Any]:
    market_rows = [row for row in rows if ((row.get("identity") or {}).get("market") == market)]
    evaluation_rows, using_preferred_validation = _preferred_validation_rows(market_rows)
    ranked = sorted(evaluation_rows, key=_sort_key)
    production = [row for row in ranked if (row.get("gate") or {}).get("production_ready")]
    sample_only = [row for row in ranked if (row.get("gate") or {}).get("sample_only_blocked")]
    shadow = [row for row in ranked if (row.get("gate") or {}).get("shadow_display_allowed")]
    high_precision = sorted([row for row in sample_only if _is_high_precision_sample_only(row)], key=_high_precision_sort_key)
    best = ranked[0] if ranked else None
    best_sample_only = sample_only[0] if sample_only else None
    best_high_precision = high_precision[0] if high_precision else None
    upgrade_candidates = [row for row in sample_only if _is_upgrade(row, current)]
    upgrade = upgrade_candidates[0] if upgrade_candidates else None
    if production:
        status = "production_candidate_found"
    elif upgrade:
        status = "shadow_upgrade_candidate_found"
    elif shadow:
        status = "shadow_candidates_found_no_upgrade"
    else:
        status = "no_displayable_candidate"
    return {
        "status": status,
        "candidate_count": len(market_rows),
        "evaluated_candidate_count": len(evaluation_rows),
        "preferred_validation_mode": PREFERRED_VALIDATION_MODE if using_preferred_validation else None,
        "production_ready_count": len(production),
        "shadow_display_allowed_count": len(shadow),
        "sample_only_shadow_count": len(sample_only),
        "current": current,
        "best_candidate": best,
        "best_sample_only_shadow": best_sample_only,
        "best_high_precision_shadow": best_high_precision,
        "verified_upgrade_candidate": upgrade,
        "upgrade_candidates": upgrade_candidates[:10],
        "top_candidates": ranked[:10],
    }


def build_report(
    *,
    report_paths: Sequence[Path],
    current_comparison_path: Path = DEFAULT_CURRENT_COMPARISON,
    tracked_sources_only: bool = True,
) -> Dict[str, Any]:
    extracted: List[Dict[str, Any]] = []
    failed_reports: List[Dict[str, str]] = []
    for path in report_paths:
        try:
            payload = _load_json(path)
            _extract_rows(payload, source_path=path, out=extracted)
        except Exception as exc:
            failed_reports.append({"path": _rel(path), "error": str(exc)})
    compact_rows = [_compact_candidate(row) for row in _dedupe(extracted)]
    current = _current_candidates(current_comparison_path)
    markets = {market: _market_report(market, compact_rows, current.get(market)) for market in REQUIRED_MARKETS}
    production_found = any((payload.get("production_ready_count") or 0) > 0 for payload in markets.values())
    upgrade_found = any(payload.get("verified_upgrade_candidate") for payload in markets.values())
    if production_found:
        status = "production_candidate_found"
        recommended_action = "run_deployment_consistency_before_controlled_promotion"
    elif upgrade_found:
        status = "shadow_upgrade_candidate_found"
        recommended_action = "promote_verified_upgrade_to_shadow_after_deployment_consistency"
    else:
        status = "keep_current_shadow"
        recommended_action = "continue_forward_tracking_until_sample_gate_clears"
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "tracked_sources_only": bool(tracked_sources_only),
        "inputs": {
            "current_comparison": _rel(current_comparison_path),
            "report_count": len(report_paths),
            "source_mode": "tracked_only" if tracked_sources_only else "all_files",
            "reports": [_rel(path) for path in report_paths],
        },
        "failed_reports": failed_reports,
        "candidate_rows_extracted": len(extracted),
        "unique_candidates": len(compact_rows),
        "markets": markets,
        "decision": {
            "status": status,
            "production_replacement_ready": production_found,
            "shadow_upgrade_found": upgrade_found,
            "recommended_action": recommended_action,
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _candidate_line(row: Mapping[str, Any] | None) -> str:
    if not row:
        return "-"
    identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
    progress = row.get("sample_progress") if isinstance(row.get("sample_progress"), Mapping) else {}
    return (
        f"`{identity.get('feature_set')}` `{identity.get('model')}` `{identity.get('selection_rule')}` "
        f"status=`{gate.get('status')}` n=`{metrics.get('n')}` days=`{metrics.get('active_days')}` "
        f"runs=`{metrics.get('active_runs')}` sample=`{_fmt(progress.get('completion_pct'))}%` "
        f"hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}` avg5=`{metrics.get('avg_5d_pct')}` "
        f"low=`{metrics.get('min_min_low_5d_pct')}` source=`{row.get('source_path')}`"
    )


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    lines = [
        "# KIS Touch5 Candidate Leaderboard",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- tracked_sources_only: `{report.get('tracked_sources_only')}`",
        f"- report_count: `{(report.get('inputs') or {}).get('report_count')}`",
        f"- unique_candidates: `{report.get('unique_candidates')}`",
        f"- status: `{decision.get('status')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- shadow_upgrade_found: `{decision.get('shadow_upgrade_found')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        "",
    ]
    for market, payload in (report.get("markets") or {}).items():
        lines.extend(
            [
                f"## {market}",
                f"- status: `{payload.get('status')}`",
                f"- candidates/shadow/sample_only/production: `{payload.get('candidate_count')}` / `{payload.get('shadow_display_allowed_count')}` / `{payload.get('sample_only_shadow_count')}` / `{payload.get('production_ready_count')}`",
                f"- current: {_candidate_line(payload.get('current'))}",
                f"- best_sample_only_shadow: {_candidate_line(payload.get('best_sample_only_shadow'))}",
                f"- best_high_precision_shadow: {_candidate_line(payload.get('best_high_precision_shadow'))}",
                f"- verified_upgrade_candidate: {_candidate_line(payload.get('verified_upgrade_candidate'))}",
                "",
                "| rank | status | feature_set | model | rule | n | days | runs | sample% | hit5_dd10 | avg5 | low | source |",
                "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for idx, row in enumerate(payload.get("top_candidates") or [], start=1):
            identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
            metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
            gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
            progress = row.get("sample_progress") if isinstance(row.get("sample_progress"), Mapping) else {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(idx),
                        str(gate.get("status")),
                        str(identity.get("feature_set")),
                        str(identity.get("model")),
                        str(identity.get("selection_rule")),
                        _fmt(metrics.get("n")),
                        _fmt(metrics.get("active_days")),
                        _fmt(metrics.get("active_runs")),
                        _fmt(progress.get("completion_pct")),
                        _fmt(metrics.get("hit5_dd10_5d_pct")),
                        _fmt(metrics.get("avg_5d_pct")),
                        _fmt(metrics.get("min_min_low_5d_pct")),
                        str(row.get("source_path")),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report).rstrip() + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--current-comparison", default=str(DEFAULT_CURRENT_COMPARISON))
    parser.add_argument("--all-files", action="store_true", help="Include untracked report files too.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    tracked_only = not bool(args.all_files)
    paths = discover_report_paths(Path(args.report_dir), tracked_only=tracked_only)
    report = build_report(
        report_paths=paths,
        current_comparison_path=Path(args.current_comparison),
        tracked_sources_only=tracked_only,
    )
    write_report(report, Path(args.output))
    print(json.dumps({"output": args.output, "decision": report.get("decision")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
