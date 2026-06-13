#!/usr/bin/env python3
"""Build the operator-facing KIS touch5/dd10 research verification report."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_VERSION = "kis_touch5_research_objective_verification_v1"
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/learning/kis_touch5_research_objective_verification_20260613.json"
DEFAULT_SHADOW_REPORT = ROOT / "runtime_state/reports/learning/kis_shadow_research_verification_20260612.json"
DEFAULT_THREE_STAGE_DYNAMIC_REPORT = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_dynamic_exit_20260101_20260610.json"
)
DEFAULT_THREE_STAGE_FIXED_REPORT = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_20260101_20260610.json"
)
DEFAULT_MARKET_COMPARISON_REPORT = ROOT / "runtime_state/reports/learning/kis_model_market_comparison.json"
DEFAULT_SIDECAR_BASELINE_SWEEP = (
    ROOT / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json"
)
DEFAULT_SIDECAR_SCORE_SWEEP = (
    ROOT / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json"
)
DEFAULT_SIDECAR_PROXY_GAP = ROOT / "runtime_state/reports/learning/kis_sidecar_proxy_feature_gap_20260613.json"
DEFAULT_SIDECAR_AUGMENTATION = ROOT / "runtime_state/reports/learning/kis_sidecar_cache_augmented_proxy_20260613.json"
DEFAULT_AUGMENTED_THREE_STAGE = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_sidecar_cache_augmented_20260331_20260610.json"
)
DEFAULT_MATCHED_ONLY_THREE_STAGE = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_sidecar_cache_matched_only_20260331_20260610.json"
)
DEFAULT_MATCHED_ONLY_SWEEPS = {
    "kis_sidecar_failure_risk_augmented": ROOT
    / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_matched_only_augmented_20260331_20260610.json",
    "kis_sidecar_only": ROOT
    / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_matched_only_sidecar_only_20260331_20260610.json",
    "kis_full_augmented": ROOT
    / "runtime_state/reports/learning/kis_sidecar_threshold_sweep_matched_only_full_augmented_20260331_20260610.json",
}
DEFAULT_DEPLOYMENT_CONSISTENCY = ROOT / "runtime_state/reports/learning/kis_shadow_deployment_consistency_20260613.json"
DEFAULT_CANDIDATE_LEADERBOARD = ROOT / "runtime_state/reports/learning/kis_touch5_candidate_leaderboard_20260613.json"
DEFAULT_FINALTOPN_PREFILTER_PROXY = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_finaltopn_prefilter_proxy_20260101_20260610.json"
)
DEFAULT_FINALTOPN_ACTUAL_SIDECAR = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_finaltopn_actual_sidecar_20260331_20260610.json"
)
DEFAULT_STATIC_MASTER_AUGMENTATION = (
    ROOT / "runtime_state/reports/learning/kis_static_sidecar_master_augmented_proxy_20260613.json"
)
DEFAULT_STATIC_MASTER_FOCUSED_SUITE = (
    ROOT / "runtime_state/reports/learning/kis_historical_best_effort_suite_static_master_focused_20260101_20260610.json"
)
DEFAULT_STATIC_MASTER_THREE_STAGE = {
    "KOSPI": ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_static_master_kospi_20260613.json",
    "KOSDAQ": ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_static_master_kosdaq_20260613.json",
}


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_optional_json(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _load_json(path)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _market_items(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    markets = payload.get("markets")
    if isinstance(markets, dict):
        return {str(k).upper(): v for k, v in markets.items() if isinstance(v, dict)}
    if isinstance(markets, list):
        return {
            str(item.get("market") or "").upper(): item
            for item in markets
            if isinstance(item, dict) and item.get("market")
        }
    return {}


def _pick_metrics(row: Mapping[str, Any] | None) -> Dict[str, Any]:
    row = row if isinstance(row, Mapping) else {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else row
    keys = (
        "n",
        "active_days",
        "active_runs",
        "coverage_test_days_pct",
        "hit5_dd10_5d_pct",
        "target_hit_5d_pct",
        "win_5d_pct",
        "hit10_5d_pct",
        "safe_hit10_5d_pct",
        "tail_breach_5d_pct",
        "bad_path_pct",
        "avg_1d_pct",
        "avg_3d_pct",
        "avg_5d_pct",
        "min_1d_pct",
        "min_3d_pct",
        "min_5d_pct",
        "avg_ordered_exit_5d_pct",
        "avg_dynamic_exit_5d_pct",
        "avg_max_high_5d_pct",
        "avg_mfe_5d_pct",
        "avg_min_low_5d_pct",
        "min_min_low_5d_pct",
        "expected_touch_policy_net_5d_pct",
        "stop5_pct",
        "target_before_stop_5d_pct",
        "stop_before_target_5d_pct",
        "min_ordered_exit_5d_pct",
        "buy_premium_pct",
    )
    return {key: metrics.get(key) for key in keys if key in metrics}


def _three_stage_market(dynamic_report: Mapping[str, Any], fixed_report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    dynamic = _market_items(dynamic_report).get(market, {})
    fixed = _market_items(fixed_report).get(market, {})
    best = dynamic.get("best") if isinstance(dynamic.get("best"), dict) else {}
    fixed_best = fixed.get("best") if isinstance(fixed.get("best"), dict) else {}
    return {
        "status": dynamic_report.get("status"),
        "validation": dynamic_report.get("validation"),
        "dummy_data_used": dynamic_report.get("dummy_data_used"),
        "rows": dynamic.get("rows"),
        "days": dynamic.get("days"),
        "folds": dynamic.get("folds"),
        "best_config": best.get("config") or {},
        "baseline_best_metrics": _pick_metrics(dynamic.get("baseline_best_metrics")),
        "fixed_exit_best_metrics": _pick_metrics(fixed_best),
        "dynamic_exit_best_metrics": _pick_metrics(best),
        "improvement": dynamic.get("improvement") or {},
        "decision": {
            "performance_improved_vs_broad_baseline": bool(
                (dynamic.get("improvement") or {}).get("avg_ordered_exit_delta_pct", 0) is not None
                and float((dynamic.get("improvement") or {}).get("avg_ordered_exit_delta_pct") or 0) > 0
            ),
            "production_candidate": False,
            "reason": "hit5_dd10 and tail/path metrics remain below the KIS production gate; useful as research evidence, not as a live replacement.",
        },
    }


def _shadow_market(shadow_report: Mapping[str, Any], comparison_report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    market_results = shadow_report.get("market_results") if isinstance(shadow_report.get("market_results"), dict) else {}
    result = market_results.get(market, {}) if isinstance(market_results.get(market), dict) else {}
    comparison_markets = comparison_report.get("markets") if isinstance(comparison_report.get("markets"), dict) else {}
    comparison = comparison_markets.get(market, {}) if isinstance(comparison_markets.get(market), dict) else {}
    current = comparison.get("current_kis_model") if isinstance(comparison.get("current_kis_model"), dict) else {}
    gate = current.get("kis_model_gate") if isinstance(current.get("kis_model_gate"), dict) else {}
    current_metrics = current.get("metrics") if isinstance(current.get("metrics"), dict) else result
    return {
        "identity": current.get("identity") or {
            "feature_set": result.get("feature_set"),
            "model": result.get("model"),
            "selection_rule": result.get("selection_rule"),
            "prob_threshold": result.get("prob_threshold"),
            "tail_risk_prob_threshold": result.get("dd10_safety_threshold"),
        },
        "metrics": _pick_metrics(current_metrics),
        "gate": {
            "status": gate.get("status") or result.get("gate_status"),
            "production_ready": bool(gate.get("production_ready") or result.get("production_ready")),
            "shadow_display_allowed": bool(gate.get("shadow_display_allowed") or result.get("shadow_display_allowed")),
            "risk_review_required": bool(gate.get("risk_review_required")),
            "production_blocking_reasons": gate.get("production_blocking_reasons")
            or result.get("production_blocking_reasons")
            or [],
            "checks": gate.get("checks") or [],
            "production_economics": gate.get("production_economics") or {},
        },
        "operational_reflection": comparison.get("operational_reflection") or {},
        "theme_news_readiness": comparison.get("theme_news_readiness") or {},
    }


def _sweep_rows(report: Mapping[str, Any], market: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for market_report in report.get("market_reports") or []:
        if not isinstance(market_report, dict):
            continue
        scope = market_report.get("scope") if isinstance(market_report.get("scope"), dict) else {}
        if str(scope.get("market") or "").upper() != market:
            continue
        rows.extend([row for row in market_report.get("results") or [] if isinstance(row, dict)])
    return rows


def _sweep_fold_signature(report: Mapping[str, Any], market: str) -> List[List[str]]:
    for market_report in report.get("market_reports") or []:
        if not isinstance(market_report, dict):
            continue
        scope = market_report.get("scope") if isinstance(market_report.get("scope"), dict) else {}
        if str(scope.get("market") or "").upper() != market:
            continue
        fold_meta = market_report.get("fold_meta") if isinstance(market_report.get("fold_meta"), dict) else {}
        return [list(row.get("test_days") or []) for row in fold_meta.get("folds") or [] if isinstance(row, dict)]
    return []


def _sweep_analysis_summary(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    for market_report in report.get("market_reports") or []:
        if not isinstance(market_report, dict):
            continue
        scope = market_report.get("scope") if isinstance(market_report.get("scope"), dict) else {}
        if str(scope.get("market") or "").upper() != market:
            continue
        summary = market_report.get("analysis_summary")
        return summary if isinstance(summary, dict) else {}
    return {}


def _sort_sweep_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    status_rank = {"production_ready": 0, "shadow_ready": 1, "shadow_risk_review": 2, "blocked": 3}
    return sorted(
        rows,
        key=lambda row: (
            status_rank.get(str((row.get("kis_model_gate") or {}).get("status")), 9),
            -float(row.get("quality_score") or -1e9),
            -float(((row.get("metrics") or {}).get("hit5_dd10_5d_pct")) or 0.0),
            -int(((row.get("metrics") or {}).get("n")) or 0),
        ),
    )


def _sweep_row_summary(row: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    gate = row.get("kis_model_gate") if isinstance(row.get("kis_model_gate"), dict) else {}
    return {
        "selection_rule": row.get("selection_rule"),
        "score_mode": row.get("score_mode") or "prob",
        "quality_score": row.get("quality_score"),
        "gate_status": gate.get("status"),
        "production_ready": bool(gate.get("production_ready")),
        "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
        "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
        "metrics": _pick_metrics(row),
    }


def _risk_adjusted_alternative(rows: List[Dict[str, Any]], baseline: Mapping[str, Any]) -> Dict[str, Any]:
    baseline_metrics = baseline.get("metrics") if isinstance(baseline.get("metrics"), dict) else {}
    baseline_hit = float(baseline_metrics.get("hit5_dd10_5d_pct") or 0.0)
    baseline_min_low = float(baseline_metrics.get("min_min_low_5d_pct") or -999.0)
    baseline_avg5 = float(baseline_metrics.get("avg_5d_pct") or -999.0)
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("score_mode") or "prob") == "prob":
            continue
        gate = row.get("kis_model_gate") if isinstance(row.get("kis_model_gate"), dict) else {}
        if not gate.get("shadow_display_allowed"):
            continue
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        hit = float(metrics.get("hit5_dd10_5d_pct") or 0.0)
        min_low = float(metrics.get("min_min_low_5d_pct") or -999.0)
        if hit > baseline_hit or min_low > baseline_min_low:
            candidates.append(row)
    if not candidates:
        return {"found": False}
    candidates.sort(
        key=lambda row: (
            float(((row.get("metrics") or {}).get("hit5_dd10_5d_pct")) or 0.0) - baseline_hit,
            float(((row.get("metrics") or {}).get("min_min_low_5d_pct")) or -999.0) - baseline_min_low,
            float(((row.get("metrics") or {}).get("avg_5d_pct")) or -999.0),
        ),
        reverse=True,
    )
    best = candidates[0]
    metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    return {
        "found": True,
        "candidate": _sweep_row_summary(best),
        "deltas_vs_baseline": {
            "hit5_dd10_5d_pct": round(float(metrics.get("hit5_dd10_5d_pct") or 0.0) - baseline_hit, 6),
            "min_min_low_5d_pct": round(float(metrics.get("min_min_low_5d_pct") or -999.0) - baseline_min_low, 6),
            "avg_5d_pct": round(float(metrics.get("avg_5d_pct") or 0.0) - baseline_avg5, 6),
            "n": int(metrics.get("n") or 0) - int(baseline_metrics.get("n") or 0),
            "active_days": int(metrics.get("active_days") or 0) - int(baseline_metrics.get("active_days") or 0),
        },
        "decision": "risk_adjusted_shadow_candidate_not_current_replacement",
    }


def _sample_only_blockers(blockers: Iterable[Any]) -> tuple[bool, List[str], List[str]]:
    blocker_list = [str(item) for item in blockers if str(item)]
    sample_blockers = [
        item
        for item in blocker_list
        if item.startswith("n_lt_") or item.startswith("active_days_lt_") or item.startswith("active_runs_lt_")
    ]
    non_sample = [item for item in blocker_list if item not in sample_blockers]
    return bool(blocker_list and not non_sample), sample_blockers, non_sample


def _near_production_candidate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        gate = row.get("kis_model_gate") if isinstance(row.get("kis_model_gate"), dict) else {}
        blockers = gate.get("production_blocking_reasons") or []
        sample_only, sample_blockers, non_sample = _sample_only_blockers(blockers)
        if gate.get("production_ready") or not sample_only:
            continue
        summary = _sweep_row_summary(row)
        summary["sample_blockers"] = sample_blockers
        summary["non_sample_blockers"] = non_sample
        candidates.append(summary)
    if not candidates:
        return {"found": False}

    def sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float]:
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        return (
            float(metrics.get("active_days") or 0.0),
            float(metrics.get("n") or 0.0),
            float(metrics.get("hit5_dd10_5d_pct") or 0.0),
            float(metrics.get("min_min_low_5d_pct") or -999.0),
            float(metrics.get("avg_5d_pct") or -999.0),
        )

    candidates.sort(key=sort_key, reverse=True)
    return {
        "found": True,
        "candidate": candidates[0],
        "candidate_count": len(candidates),
        "decision": "forward_track_until_sample_gate_clears",
    }


def _sidecar_score_experiment(
    baseline_report: Mapping[str, Any],
    score_report: Mapping[str, Any],
    market: str,
) -> Dict[str, Any]:
    baseline_rows = _sort_sweep_rows(_sweep_rows(baseline_report, market))
    score_rows = _sort_sweep_rows(_sweep_rows(score_report, market))
    baseline_best = baseline_rows[0] if baseline_rows else {}
    score_best = score_rows[0] if score_rows else {}
    same_fold_scope = _sweep_fold_signature(baseline_report, market) == _sweep_fold_signature(score_report, market)
    return {
        "same_fold_scope_verified": same_fold_scope,
        "baseline_best": _sweep_row_summary(baseline_best),
        "score_mode_best": _sweep_row_summary(score_best),
        "risk_adjusted_alternative": _risk_adjusted_alternative(score_rows, baseline_best),
        "near_production_candidate": _near_production_candidate(score_rows),
        "score_report_analysis_summary": _sweep_analysis_summary(score_report, market),
        "decision": (
            "keep_current_best_shadow"
            if _sweep_row_summary(score_best).get("selection_rule") == _sweep_row_summary(baseline_best).get("selection_rule")
            else "review_score_mode_shadow_candidate"
        ),
    }


def _three_stage_experiment(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    if not report:
        return {}
    item = _market_items(report).get(market, {})
    best = item.get("best") if isinstance(item.get("best"), dict) else {}
    unconstrained = item.get("unconstrained_best") if isinstance(item.get("unconstrained_best"), dict) else {}
    gate = best.get("gate") if isinstance(best.get("gate"), dict) else {}
    return {
        "status": report.get("status"),
        "validation": report.get("validation"),
        "dummy_data_used": report.get("dummy_data_used"),
        "rows": item.get("rows"),
        "days": item.get("days"),
        "best_config": best.get("config") or {},
        "best_metrics": _pick_metrics(best),
        "best_gate": {
            "status": gate.get("status"),
            "production_ready": bool(gate.get("production_ready")),
            "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
            "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
            "shadow_blocking_reasons": gate.get("shadow_blocking_reasons") or [],
        },
        "unconstrained_best_config": unconstrained.get("config") or {},
        "unconstrained_best_metrics": _pick_metrics(unconstrained),
        "improvement": item.get("improvement") or {},
        "decision": {
            "production_candidate": False,
            "promotable": False,
            "reason": "augmentation experiment only; production promotion requires positive expectancy, hit/risk gates, and sufficient samples.",
        },
    }


def _leaderboard_candidate_summary(row: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    identity = row.get("identity") if isinstance(row.get("identity"), dict) else {}
    gate = row.get("gate") if isinstance(row.get("gate"), dict) else {}
    return {
        "selection_rule": identity.get("selection_rule") or row.get("selection_rule"),
        "feature_set": identity.get("feature_set") or row.get("feature_set"),
        "model": identity.get("model") or row.get("model"),
        "score_mode": identity.get("score_mode") or row.get("score_mode"),
        "source_path": row.get("source_path"),
        "gate_status": gate.get("status"),
        "production_ready": bool(gate.get("production_ready")),
        "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
        "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
        "non_sample_blockers": gate.get("non_sample_blockers") or [],
        "sample_progress": row.get("sample_progress") or {},
        "metrics": _pick_metrics(row),
    }


def _candidate_leaderboard_market(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    if not report:
        return {}
    markets = report.get("markets") if isinstance(report.get("markets"), dict) else {}
    payload = markets.get(market, {}) if isinstance(markets.get(market), dict) else {}
    if not payload:
        return {}
    return {
        "status": payload.get("status"),
        "candidate_count": payload.get("candidate_count"),
        "production_ready_count": payload.get("production_ready_count"),
        "shadow_display_allowed_count": payload.get("shadow_display_allowed_count"),
        "sample_only_shadow_count": payload.get("sample_only_shadow_count"),
        "current": _leaderboard_candidate_summary(payload.get("current")),
        "best_sample_only_shadow": _leaderboard_candidate_summary(payload.get("best_sample_only_shadow")),
        "best_high_precision_shadow": _leaderboard_candidate_summary(payload.get("best_high_precision_shadow")),
        "verified_upgrade_candidate": _leaderboard_candidate_summary(payload.get("verified_upgrade_candidate")),
    }


def _augmentation_market(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    for row in report.get("markets") or []:
        if isinstance(row, dict) and str(row.get("market") or "").upper() == market:
            coverage_delta = row.get("coverage_delta") if isinstance(row.get("coverage_delta"), dict) else {}
            coverage_delta_summary = {
                family: {
                    "features_improved": payload.get("features_improved"),
                    "avg_positive_delta_pct": payload.get("avg_positive_delta_pct"),
                    "top_deltas": (payload.get("top_deltas") or [])[:3],
                }
                for family, payload in coverage_delta.items()
                if isinstance(payload, dict)
            }
            return {
                "matched_rows": row.get("matched_rows"),
                "matched_row_pct": row.get("matched_row_pct"),
                "matched_days": row.get("matched_days"),
                "matched_tickers": row.get("matched_tickers"),
                "output_cache": row.get("output_cache"),
                "matched_only_output_cache": row.get("matched_only_output_cache"),
                "no_dummy_data": row.get("no_dummy_data"),
                "leakage_policy": row.get("leakage_policy"),
                "coverage_delta_summary": coverage_delta_summary,
            }
    return {}


def _static_master_augmentation_market(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    for row in report.get("markets") or []:
        if isinstance(row, dict) and str(row.get("market") or "").upper() == market:
            coverage_delta = row.get("coverage_delta") if isinstance(row.get("coverage_delta"), dict) else {}
            coverage_delta_summary = {
                family: {
                    "features_improved": payload.get("features_improved"),
                    "avg_positive_delta_pct": payload.get("avg_positive_delta_pct"),
                    "top_deltas": (payload.get("top_deltas") or [])[:3],
                }
                for family, payload in coverage_delta.items()
                if isinstance(payload, dict)
            }
            return {
                "master_matched_rows": row.get("master_matched_rows"),
                "master_matched_row_pct": row.get("master_matched_row_pct"),
                "augmented_rows": row.get("augmented_rows"),
                "augmented_row_pct": row.get("augmented_row_pct"),
                "output_cache": row.get("output_cache"),
                "no_dummy_data": row.get("no_dummy_data"),
                "leakage_policy": row.get("leakage_policy"),
                "feature_fill_counts_top": (row.get("feature_fill_counts_top") or [])[:8],
                "coverage_delta_summary": coverage_delta_summary,
            }
    return {}


def _best_effort_suite_market(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    item = _market_items(report).get(market, {})
    if not item:
        return {}
    best = item.get("best") if isinstance(item.get("best"), dict) else {}
    gate = best.get("gate") if isinstance(best.get("gate"), dict) else {}
    identity = best.get("identity") if isinstance(best.get("identity"), dict) else {}
    metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    return {
        "status": item.get("status") or report.get("status") or decision.get("status"),
        "decision": decision,
        "rows": item.get("rows"),
        "days": item.get("days"),
        "candidate_count": item.get("candidate_count"),
        "shadow_display_allowed": item.get("shadow_display_allowed"),
        "production_ready": item.get("production_ready"),
        "best_identity": identity,
        "best_metrics": _pick_metrics(metrics),
        "best_gate": {
            "status": gate.get("status"),
            "production_ready": bool(gate.get("production_ready")),
            "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
            "risk_review_required": bool(gate.get("risk_review_required")),
            "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
            "shadow_blocking_reasons": gate.get("shadow_blocking_reasons") or [],
            "risk_review_reasons": gate.get("risk_review_reasons") or [],
            "production_economics": gate.get("production_economics") or {},
        },
        "quality_score": best.get("quality_score"),
    }


def _best_shadow_ready_from_analysis(summary: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("sample_only_top", "pareto_top", "sample_sufficient_top"):
        rows = summary.get(key)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
    return {}


def _matched_only_sweep_experiments(
    sweep_reports: Mapping[str, Mapping[str, Any]],
    market: str,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    best_candidate: Dict[str, Any] = {}
    best_feature_set = None
    for feature_set, report in sweep_reports.items():
        if not report:
            continue
        summary = _sweep_analysis_summary(report, market)
        candidate = _best_shadow_ready_from_analysis(summary)
        candidate_summary = _sweep_row_summary(candidate)
        out[feature_set] = {
            "summary": {
                "status_counts": summary.get("status_counts") or {},
                "production_blocking_reason_counts": summary.get("production_blocking_reason_counts") or {},
                "sample_only_blocked_count": summary.get("sample_only_blocked_count"),
                "sample_sufficient_count": summary.get("sample_sufficient_count"),
            },
            "best_candidate": candidate_summary,
        }
        current_metrics = candidate_summary.get("metrics") if isinstance(candidate_summary.get("metrics"), dict) else {}
        best_metrics = best_candidate.get("metrics") if isinstance(best_candidate.get("metrics"), dict) else {}
        if candidate_summary and (
            not best_candidate
            or float(current_metrics.get("avg_5d_pct") or -999.0) > float(best_metrics.get("avg_5d_pct") or -999.0)
            or (
                float(current_metrics.get("avg_5d_pct") or -999.0) == float(best_metrics.get("avg_5d_pct") or -999.0)
                and float(current_metrics.get("hit5_dd10_5d_pct") or 0.0)
                > float(best_metrics.get("hit5_dd10_5d_pct") or 0.0)
            )
        ):
            best_candidate = candidate_summary
            best_feature_set = feature_set
    return {
        "by_feature_set": out,
        "best_feature_set": best_feature_set,
        "best_candidate": best_candidate,
        "decision": "matched_only_shadow_research_only" if best_candidate else "no_matched_only_candidate",
    }


def _historical_proxy_augmentation_experiment(
    *,
    feature_gap_report: Mapping[str, Any],
    augmentation_report: Mapping[str, Any],
    augmented_three_stage_report: Mapping[str, Any],
    matched_only_three_stage_report: Mapping[str, Any],
    matched_only_sweep_reports: Mapping[str, Mapping[str, Any]],
    static_master_report: Mapping[str, Any],
    static_master_focused_report: Mapping[str, Any],
    static_master_three_stage_reports: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    markets: Dict[str, Any] = {}
    for market in ("KOSPI", "KOSDAQ"):
        markets[market] = {
            "augmentation": _augmentation_market(augmentation_report, market),
            "static_master_augmentation": _static_master_augmentation_market(static_master_report, market),
            "static_master_focused_suite": _best_effort_suite_market(static_master_focused_report, market),
            "static_master_three_stage": _three_stage_experiment(
                static_master_three_stage_reports.get(market, {}),
                market,
            ),
            "augmented_three_stage": _three_stage_experiment(augmented_three_stage_report, market),
            "matched_only_three_stage": _three_stage_experiment(matched_only_three_stage_report, market),
            "matched_only_threshold_sweeps": _matched_only_sweep_experiments(matched_only_sweep_reports, market),
        }
    static_suites = {
        market: (markets.get(market) or {}).get("static_master_focused_suite") or {}
        for market in ("KOSPI", "KOSDAQ")
    }
    static_shadow_ready = all(
        ((static_suites.get(market) or {}).get("best_gate") or {}).get("shadow_display_allowed")
        for market in ("KOSPI", "KOSDAQ")
    )
    static_production_ready = all(
        ((static_suites.get(market) or {}).get("best_gate") or {}).get("production_ready")
        for market in ("KOSPI", "KOSDAQ")
    )
    static_three_stage = {
        market: (markets.get(market) or {}).get("static_master_three_stage") or {}
        for market in ("KOSPI", "KOSDAQ")
    }
    static_three_stage_improved = all(
        float(((static_three_stage.get(market) or {}).get("improvement") or {}).get("avg_ordered_exit_delta_pct") or 0.0)
        > 0.0
        for market in ("KOSPI", "KOSDAQ")
    )
    static_three_stage_production_ready = any(
        (((static_three_stage.get(market) or {}).get("best_gate") or {}).get("production_ready"))
        for market in ("KOSPI", "KOSDAQ")
    )
    if static_shadow_ready:
        positive_shadow_result = (
            "real KIS static stock-info master augmentation produced both-market shadow-ready focused walk-forward "
            "results; production gates still failed on hit5_dd10, ordered-exit floor, and expected net return."
        )
    else:
        positive_shadow_result = (
            "KOSPI matched-only KIS full/sidecar sweep produced shadow-ready candidates; KOSDAQ did not reproduce in historical proxy."
        )
    return {
        "inputs": {
            "feature_gap_report_available": bool(feature_gap_report),
            "augmentation_report_available": bool(augmentation_report),
            "augmented_three_stage_report_available": bool(augmented_three_stage_report),
            "matched_only_three_stage_report_available": bool(matched_only_three_stage_report),
            "matched_only_sweep_feature_sets": sorted(k for k, v in matched_only_sweep_reports.items() if v),
            "static_master_report_available": bool(static_master_report),
            "static_master_focused_suite_report_available": bool(static_master_focused_report),
        },
        "feature_gap_decision": (feature_gap_report.get("decision") or {}) if feature_gap_report else {},
        "backfill_priorities": (feature_gap_report.get("backfill_priorities") or []) if feature_gap_report else [],
        "markets": markets,
        "decision": {
            "historical_proxy_promotable": False,
            "augmentation_ready_for_research": bool((augmentation_report.get("decision") or {}).get("augmented_cache_ready_for_research")),
            "static_master_shadow_ready": bool(static_shadow_ready),
            "static_master_production_ready": bool(static_production_ready),
            "static_master_three_stage_improved": bool(static_three_stage_improved),
            "static_master_three_stage_production_ready": bool(static_three_stage_production_ready),
            "positive_shadow_result": positive_shadow_result,
            "production_replacement_ready": False,
            "reason": "static KIS stock-info augmentation improves historical proxy feature parity and fold-separated research performance, but production replacement still requires all touch5/dd10 risk and net-return gates to pass.",
        },
    }


def _best_available_decision(shadow_by_market: Mapping[str, Any]) -> Dict[str, Any]:
    required = ("KOSPI", "KOSDAQ")
    production_ready = all(((shadow_by_market.get(market) or {}).get("gate") or {}).get("production_ready") for market in required)
    shadow_ready = all(((shadow_by_market.get(market) or {}).get("gate") or {}).get("shadow_display_allowed") for market in required)
    blockers = {
        market: ((shadow_by_market.get(market) or {}).get("gate") or {}).get("production_blocking_reasons") or []
        for market in required
    }
    if production_ready:
        status = "production_replacement_candidate"
        action = "human_review_then_controlled_promotion"
    elif shadow_ready:
        status = "verified_shadow_performance"
        action = "keep_existing_production_and_show_kis_shadow_top_section"
    else:
        status = "blocked"
        action = "do_not_display_as_trade_candidate"
    return {
        "status": status,
        "recommended_action": action,
        "production_replacement_proven": bool(production_ready),
        "shadow_performance_proven": bool(shadow_ready),
        "production_blockers_by_market": blockers,
    }


def build_report(
    *,
    shadow_report_path: Path = DEFAULT_SHADOW_REPORT,
    three_stage_dynamic_path: Path = DEFAULT_THREE_STAGE_DYNAMIC_REPORT,
    three_stage_fixed_path: Path = DEFAULT_THREE_STAGE_FIXED_REPORT,
    market_comparison_path: Path = DEFAULT_MARKET_COMPARISON_REPORT,
    sidecar_baseline_sweep_path: Path = DEFAULT_SIDECAR_BASELINE_SWEEP,
    sidecar_score_sweep_path: Path = DEFAULT_SIDECAR_SCORE_SWEEP,
    sidecar_proxy_gap_path: Path | None = None,
    sidecar_augmentation_path: Path | None = None,
    augmented_three_stage_path: Path | None = None,
    matched_only_three_stage_path: Path | None = None,
    matched_only_sweep_paths: Mapping[str, Path] | None = None,
    deployment_consistency_path: Path | None = None,
    candidate_leaderboard_path: Path | None = None,
    finaltopn_prefilter_proxy_path: Path | None = None,
    finaltopn_actual_sidecar_path: Path | None = None,
    static_master_augmentation_path: Path | None = None,
    static_master_focused_suite_path: Path | None = None,
    static_master_three_stage_paths: Mapping[str, Path] | None = None,
) -> Dict[str, Any]:
    shadow_report = _load_json(shadow_report_path)
    three_stage_dynamic = _load_json(three_stage_dynamic_path)
    three_stage_fixed = _load_json(three_stage_fixed_path)
    market_comparison = _load_json(market_comparison_path)
    sidecar_baseline_sweep = _load_json(sidecar_baseline_sweep_path)
    sidecar_score_sweep = _load_json(sidecar_score_sweep_path) if sidecar_score_sweep_path.exists() else {}
    feature_gap_report = _load_optional_json(sidecar_proxy_gap_path)
    augmentation_report = _load_optional_json(sidecar_augmentation_path)
    augmented_three_stage = _load_optional_json(augmented_three_stage_path)
    matched_only_three_stage = _load_optional_json(matched_only_three_stage_path)
    matched_only_sweeps = {
        feature_set: _load_optional_json(path)
        for feature_set, path in (matched_only_sweep_paths or {}).items()
    }
    deployment_consistency = _load_optional_json(deployment_consistency_path)
    candidate_leaderboard = _load_optional_json(candidate_leaderboard_path)
    finaltopn_prefilter_proxy = _load_optional_json(finaltopn_prefilter_proxy_path)
    finaltopn_actual_sidecar = _load_optional_json(finaltopn_actual_sidecar_path)
    static_master_augmentation = _load_optional_json(static_master_augmentation_path)
    static_master_focused_suite = _load_optional_json(static_master_focused_suite_path)
    static_master_three_stage_reports = {
        str(market).upper(): _load_optional_json(path)
        for market, path in (static_master_three_stage_paths or {}).items()
    }
    markets: Dict[str, Any] = {}
    for market in ("KOSPI", "KOSDAQ"):
        markets[market] = {
            "three_stage_ev_ranker": _three_stage_market(three_stage_dynamic, three_stage_fixed, market),
            "finaltopn_three_stage_experiments": {
                "prefilter_proxy": _three_stage_experiment(finaltopn_prefilter_proxy, market),
                "actual_sidecar": _three_stage_experiment(finaltopn_actual_sidecar, market),
            },
            "kis_sidecar_longfold_shadow": _shadow_market(shadow_report, market_comparison, market),
            "sidecar_score_mode_experiment": _sidecar_score_experiment(
                sidecar_baseline_sweep,
                sidecar_score_sweep,
                market,
            )
            if sidecar_score_sweep
            else {},
            "candidate_leaderboard": _candidate_leaderboard_market(candidate_leaderboard, market),
        }
    decision = _best_available_decision({m: row["kis_sidecar_longfold_shadow"] for m, row in markets.items()})
    return {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_goal": {
            "primary_goal": "실제 매수 관점에서 KIS 기반 후보가 5거래일 안에 +5% 이상 터치하고 -10%보다 깊은 하락을 피하는지 검증한다.",
            "win_definition": "스캔 기준가보다 2% 높게 매수한다고 가정하고 5거래일 내 +5% 이상 터치하면 승리로 본다.",
            "defense_definition": "0.1% 상승이나 종가 양전은 승리가 아니라 방어/참고 지표다.",
            "loss_guard": "5거래일 최저가가 진입가 대비 -10%보다 깊게 밀리면 실전 실패 경로로 본다.",
        },
        "service_feature_scope": {
            "scanner_agent": "KIS 가격, 거래대금, 수급, 프리필터, scan_universe 후보 생성",
            "aggregation_agent": "Top 후보와 KIS shadow 후보를 같은 run_id 기준으로 병합하고 gate를 보존",
            "backtest_learning_agent": "touch5_dd10 라벨, close-failure prior, threshold sweep, walk-forward 검증",
            "market_news_context_agent": "KIS 테마/뉴스 evidence 필드는 보존하되 mature_for_training=false이면 승격 판단에서 제외",
            "pm_planner_agent": "production_ready, shadow_display_allowed, risk_review_required, 차단 사유를 운영 의사결정으로 변환",
        },
        "research_inputs": {
            "no_dummy_data": True,
            "shadow_report": _rel(shadow_report_path),
            "three_stage_dynamic_report": _rel(three_stage_dynamic_path),
            "three_stage_fixed_report": _rel(three_stage_fixed_path),
            "market_comparison_report": _rel(market_comparison_path),
            "sidecar_baseline_sweep_report": _rel(sidecar_baseline_sweep_path),
            "sidecar_score_sweep_report": _rel(sidecar_score_sweep_path) if sidecar_score_sweep_path.exists() else None,
            "sidecar_proxy_gap_report": _rel(sidecar_proxy_gap_path) if sidecar_proxy_gap_path and sidecar_proxy_gap_path.exists() else None,
            "sidecar_augmentation_report": _rel(sidecar_augmentation_path)
            if sidecar_augmentation_path and sidecar_augmentation_path.exists()
            else None,
            "augmented_three_stage_report": _rel(augmented_three_stage_path)
            if augmented_three_stage_path and augmented_three_stage_path.exists()
            else None,
            "matched_only_three_stage_report": _rel(matched_only_three_stage_path)
            if matched_only_three_stage_path and matched_only_three_stage_path.exists()
            else None,
            "matched_only_sweep_reports": {
                key: _rel(path)
                for key, path in (matched_only_sweep_paths or {}).items()
                if path.exists()
            },
            "deployment_consistency_report": _rel(deployment_consistency_path)
            if deployment_consistency_path and deployment_consistency_path.exists()
            else None,
            "deployment_consistency": (deployment_consistency.get("decision") or {}) if deployment_consistency else {},
            "candidate_leaderboard_report": _rel(candidate_leaderboard_path)
            if candidate_leaderboard_path and candidate_leaderboard_path.exists()
            else None,
            "candidate_leaderboard": (candidate_leaderboard.get("decision") or {}) if candidate_leaderboard else {},
            "finaltopn_prefilter_proxy_report": _rel(finaltopn_prefilter_proxy_path)
            if finaltopn_prefilter_proxy_path and finaltopn_prefilter_proxy_path.exists()
            else None,
            "finaltopn_actual_sidecar_report": _rel(finaltopn_actual_sidecar_path)
            if finaltopn_actual_sidecar_path and finaltopn_actual_sidecar_path.exists()
            else None,
            "static_master_augmentation_report": _rel(static_master_augmentation_path)
            if static_master_augmentation_path and static_master_augmentation_path.exists()
            else None,
            "static_master_focused_suite_report": _rel(static_master_focused_suite_path)
            if static_master_focused_suite_path and static_master_focused_suite_path.exists()
            else None,
            "static_master_three_stage_reports": {
                market: _rel(path)
                for market, path in (static_master_three_stage_paths or {}).items()
                if path.exists()
            },
            "static_master_focused_suite_decision": (static_master_focused_suite.get("decision") or {})
            if static_master_focused_suite
            else {},
            "sidecar_score_evaluated_results": (sidecar_score_sweep.get("summary") or {}).get("evaluated_results")
            if sidecar_score_sweep
            else None,
            "sidecar_score_shadow_display_allowed": (sidecar_score_sweep.get("summary") or {}).get("shadow_display_allowed")
            if sidecar_score_sweep
            else None,
            "sidecar_score_production_ready": (sidecar_score_sweep.get("summary") or {}).get("production_ready")
            if sidecar_score_sweep
            else None,
            "shadow_data_rows": (shadow_report.get("research_inputs") or {}).get("data_rows"),
            "shadow_prepared_rows": (shadow_report.get("research_inputs") or {}).get("prepared_rows"),
            "shadow_evaluated_results": (shadow_report.get("exploration_result") or {}).get("evaluated_results"),
            "shadow_display_allowed_results": (shadow_report.get("exploration_result") or {}).get("shadow_display_allowed"),
            "shadow_production_ready_results": (shadow_report.get("exploration_result") or {}).get("production_ready"),
            "three_stage_validation": three_stage_dynamic.get("validation"),
        },
        "research_path": [
            {
                "step": "baseline_boundary_check",
                "finding": "단순 broad ML/top1 방식은 touch5_dd10 목표를 강제하면 기대값이 약하거나 음수라 운영 후보로 부적합했다.",
            },
            {
                "step": "three_stage_ev_ranker",
                "finding": "wide recall pool, tail-risk model, EV/no-trade ranker는 broad baseline 대비 개선됐지만 hit5/dd10이 73% 운영 기준에 미달했다.",
            },
            {
                "step": "kis_sidecar_longfold_threshold_sweep",
                "finding": "KIS sidecar failure-risk augmented LightGBM long-fold sweep가 양시장 shadow 성과를 만들었다.",
            },
            {
                "step": "consumer_contract_verification",
                "finding": "TopDeep, UI/Discord/정밀분석 경로는 KIS shadow gate와 동적 TP/SL/보유일 trace를 보존해야 한다.",
            },
            {
                "step": "sidecar_score_mode_expansion",
                "finding": "동일 long-fold 조건에서 EV/safety 결합 score mode를 추가 검증한다. 생산 승격은 여전히 0개이며, 성과가 있는 경우 risk-adjusted shadow 후보로만 기록한다.",
            },
            {
                "step": "exact_date_sidecar_augmentation",
                "finding": "historical proxy cache에는 실제 KIS flow/financial/static/news가 부족하므로 ticker/date가 정확히 일치하는 실제 sidecar 행만 병합하고, full cache와 matched-only cache로 분리 검증한다.",
            },
            {
                "step": "static_sidecar_master_augmentation",
                "finding": "실제 KIS sidecar cache에서 ticker 정적 stock-info master만 추출해 2026-01-01 이후 historical proxy의 stock/theme category 결손을 보강했고, focused walk-forward에서 양시장 shadow gate를 통과했다. 단, 수급/재무/뉴스 시계열은 as-of 유출 위험 때문에 채우지 않았다.",
            },
            {
                "step": "static_master_three_stage_validation",
                "finding": "static stock-info master 증강 캐시에 fold-separated 3단 EV/no-trade 랭커를 재적용해 양시장 dynamic exit 성과 개선을 확인했다. 다만 touch5_dd10 73%와 -10% tail 방어 기준을 동시에 넘지 못해 연구 성과로만 기록한다.",
            },
            {
                "step": "final_topn_no_trade_expansion",
                "finding": "최종 후보를 하루 1개로 제한하지 않고 final topN/no-trade threshold를 추가 검증한다. 성과가 기준 미달이면 shadow 승격 근거로 사용하지 않는다.",
            },
        ],
        "markets": markets,
        "historical_proxy_augmentation_experiment": _historical_proxy_augmentation_experiment(
            feature_gap_report=feature_gap_report,
            augmentation_report=augmentation_report,
            augmented_three_stage_report=augmented_three_stage,
            matched_only_three_stage_report=matched_only_three_stage,
            matched_only_sweep_reports=matched_only_sweeps,
            static_master_report=static_master_augmentation,
            static_master_focused_report=static_master_focused_suite,
            static_master_three_stage_reports=static_master_three_stage_reports,
        )
        if any(
            [
                feature_gap_report,
                augmentation_report,
                augmented_three_stage,
                matched_only_three_stage,
                matched_only_sweeps,
                static_master_augmentation,
                static_master_focused_suite,
                static_master_three_stage_reports,
            ]
        )
        else {},
        "decision": decision,
        "operator_report_rule": "성과가 검증된 항목만 후보로 보고한다. production_ready=false이면 운영 대체가 아니라 shadow_only로만 표시한다.",
        "ui_requirements": [
            "웹 최상단에 KIS Shadow 섹션을 두고 production_ready, shadow_display_allowed, 차단 사유를 한국어로 표시",
            "후보 카드에는 목표 +5%, 손절 -10%, 5일 보유, KIS gate, dd10 safety threshold를 같이 표시",
            "정밀분석과 Discord lookup도 동일한 gate와 action_reason_codes를 사용",
            "테마/뉴스 evidence coverage가 부족하면 학습/승격 제외 배지를 표시",
            "운영 Top 후보와 KIS Shadow 후보를 같은 run_id에서 나란히 비교",
        ],
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    goal = report.get("user_goal") if isinstance(report.get("user_goal"), dict) else {}
    lines = [
        "# KIS Touch5/DD10 Research Objective Verification",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- decision: `{decision.get('status')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        f"- production_replacement_proven: `{decision.get('production_replacement_proven')}`",
        f"- shadow_performance_proven: `{decision.get('shadow_performance_proven')}`",
        "",
        "## 목표",
        f"- primary_goal: {goal.get('primary_goal')}",
        f"- win_definition: {goal.get('win_definition')}",
        f"- defense_definition: {goal.get('defense_definition')}",
        f"- loss_guard: {goal.get('loss_guard')}",
        "",
        "## 연구 경로",
    ]
    for row in report.get("research_path") or []:
        lines.append(f"- {row.get('step')}: {row.get('finding')}")
    lines.extend(
        [
            "",
            "## 입력과 검증",
            f"- no_dummy_data: `{(report.get('research_inputs') or {}).get('no_dummy_data')}`",
            f"- shadow rows/evaluated/shadow_allowed/production_ready: `{(report.get('research_inputs') or {}).get('shadow_data_rows')}` / `{(report.get('research_inputs') or {}).get('shadow_evaluated_results')}` / `{(report.get('research_inputs') or {}).get('shadow_display_allowed_results')}` / `{(report.get('research_inputs') or {}).get('shadow_production_ready_results')}`",
            f"- sidecar score sweep evaluated/shadow_allowed/production_ready: `{(report.get('research_inputs') or {}).get('sidecar_score_evaluated_results')}` / `{(report.get('research_inputs') or {}).get('sidecar_score_shadow_display_allowed')}` / `{(report.get('research_inputs') or {}).get('sidecar_score_production_ready')}`",
            f"- deployment_consistency: `{((report.get('research_inputs') or {}).get('deployment_consistency') or {}).get('status')}` / `{((report.get('research_inputs') or {}).get('deployment_consistency') or {}).get('recommended_action')}`",
            f"- candidate_leaderboard: `{((report.get('research_inputs') or {}).get('candidate_leaderboard') or {}).get('status')}` / `{((report.get('research_inputs') or {}).get('candidate_leaderboard') or {}).get('recommended_action')}`",
            f"- three_stage_validation: `{(report.get('research_inputs') or {}).get('three_stage_validation')}`",
            "",
        ]
    )
    for market, payload in (report.get("markets") or {}).items():
        three = payload.get("three_stage_ev_ranker") or {}
        three_metrics = three.get("dynamic_exit_best_metrics") or {}
        three_imp = three.get("improvement") or {}
        shadow = payload.get("kis_sidecar_longfold_shadow") or {}
        identity = shadow.get("identity") or {}
        metrics = shadow.get("metrics") or {}
        gate = shadow.get("gate") or {}
        econ = gate.get("production_economics") if isinstance(gate.get("production_economics"), dict) else {}
        score_exp = payload.get("sidecar_score_mode_experiment") or {}
        score_best = score_exp.get("score_mode_best") or {}
        risk_alt = score_exp.get("risk_adjusted_alternative") or {}
        risk_candidate = risk_alt.get("candidate") or {}
        risk_metrics = risk_candidate.get("metrics") or {}
        near_prod = score_exp.get("near_production_candidate") or {}
        near_candidate = near_prod.get("candidate") or {}
        near_metrics = near_candidate.get("metrics") or {}
        score_summary = score_exp.get("score_report_analysis_summary") or {}
        leaderboard = payload.get("candidate_leaderboard") or {}
        leaderboard_best = leaderboard.get("best_sample_only_shadow") or {}
        leaderboard_best_metrics = leaderboard_best.get("metrics") or {}
        leaderboard_high_precision = leaderboard.get("best_high_precision_shadow") or {}
        leaderboard_high_metrics = leaderboard_high_precision.get("metrics") or {}
        leaderboard_upgrade = leaderboard.get("verified_upgrade_candidate") or {}
        sample_only_top = score_summary.get("sample_only_top") or []
        sample_sufficient_top = score_summary.get("sample_sufficient_top") or []
        pareto_top = score_summary.get("pareto_top") or []
        sample_candidate = sample_only_top[0] if sample_only_top and isinstance(sample_only_top[0], dict) else {}
        sample_sufficient_candidate = (
            sample_sufficient_top[0] if sample_sufficient_top and isinstance(sample_sufficient_top[0], dict) else {}
        )
        pareto_candidate = pareto_top[0] if pareto_top and isinstance(pareto_top[0], dict) else {}
        constraint_frontiers = (
            score_summary.get("constraint_frontiers")
            if isinstance(score_summary.get("constraint_frontiers"), dict)
            else {}
        )
        one_day_short_top = constraint_frontiers.get("one_day_short_low_safe_touch_top") or []
        low_fail_top = constraint_frontiers.get("sample_sufficient_touch_but_low_fail_top") or []
        one_day_short = (
            one_day_short_top[0] if one_day_short_top and isinstance(one_day_short_top[0], dict) else {}
        )
        low_fail = low_fail_top[0] if low_fail_top and isinstance(low_fail_top[0], dict) else {}
        one_day_short_metrics = one_day_short.get("metrics") if isinstance(one_day_short.get("metrics"), dict) else {}
        low_fail_metrics = low_fail.get("metrics") if isinstance(low_fail.get("metrics"), dict) else {}
        low_fail_frontier = (
            low_fail.get("production_frontier") if isinstance(low_fail.get("production_frontier"), dict) else {}
        )
        low_fail_deficits = (
            low_fail_frontier.get("deficits") if isinstance(low_fail_frontier.get("deficits"), dict) else {}
        )
        finaltopn = payload.get("finaltopn_three_stage_experiments") or {}
        finaltopn_proxy = finaltopn.get("prefilter_proxy") if isinstance(finaltopn.get("prefilter_proxy"), dict) else {}
        finaltopn_actual = finaltopn.get("actual_sidecar") if isinstance(finaltopn.get("actual_sidecar"), dict) else {}
        finaltopn_proxy_metrics = (
            finaltopn_proxy.get("best_metrics") if isinstance(finaltopn_proxy.get("best_metrics"), dict) else {}
        )
        finaltopn_actual_metrics = (
            finaltopn_actual.get("best_metrics") if isinstance(finaltopn_actual.get("best_metrics"), dict) else {}
        )
        finaltopn_proxy_gate = (
            finaltopn_proxy.get("best_gate") if isinstance(finaltopn_proxy.get("best_gate"), dict) else {}
        )
        finaltopn_actual_gate = (
            finaltopn_actual.get("best_gate") if isinstance(finaltopn_actual.get("best_gate"), dict) else {}
        )
        lines.extend(
            [
                f"## {market}",
                f"- selected_shadow_model: `{identity.get('feature_set')}` / `{identity.get('model')}` / `{identity.get('selection_rule')}`",
                f"- gate: status=`{gate.get('status')}`, production_ready=`{gate.get('production_ready')}`, shadow_display_allowed=`{gate.get('shadow_display_allowed')}`",
                f"- blockers: `{gate.get('production_blocking_reasons') or []}`",
                f"- shadow metrics: n=`{metrics.get('n')}`, active_days=`{metrics.get('active_days')}`, active_runs=`{metrics.get('active_runs')}`, hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}`, hit10=`{metrics.get('hit10_5d_pct')}`, avg5=`{metrics.get('avg_5d_pct')}`, min_low=`{metrics.get('min_min_low_5d_pct')}`, expected_touch_net=`{metrics.get('expected_touch_policy_net_5d_pct') or econ.get('expected_touch_policy_net_5d_pct')}`",
                f"- three_stage_result: hit5_dd10=`{three_metrics.get('hit5_dd10_5d_pct')}`, dynamic_exit=`{three_metrics.get('avg_dynamic_exit_5d_pct')}`, tail=`{three_metrics.get('tail_breach_5d_pct')}`, min_low=`{three_metrics.get('min_min_low_5d_pct')}`",
                f"- three_stage_improvement_vs_broad: avg_exit_delta=`{three_imp.get('avg_ordered_exit_delta_pct')}`, hit5_delta=`{three_imp.get('hit5_dd10_delta_pct')}`",
                f"- score_mode_experiment: same_fold_scope=`{score_exp.get('same_fold_scope_verified')}`, decision=`{score_exp.get('decision')}`, best=`{score_best.get('selection_rule')}`",
                f"- risk_adjusted_alternative: found=`{risk_alt.get('found')}`, candidate=`{risk_candidate.get('selection_rule')}`, hit5_dd10=`{risk_metrics.get('hit5_dd10_5d_pct')}`, avg5=`{risk_metrics.get('avg_5d_pct')}`, min_low=`{risk_metrics.get('min_min_low_5d_pct')}`, deltas=`{risk_alt.get('deltas_vs_baseline')}`",
                f"- near_production_candidate: found=`{near_prod.get('found')}`, candidate=`{near_candidate.get('selection_rule')}`, score=`{near_candidate.get('score_mode')}`, n=`{near_metrics.get('n')}`, active_days=`{near_metrics.get('active_days')}`, active_runs=`{near_metrics.get('active_runs')}`, hit5=`{near_metrics.get('hit5_dd10_5d_pct')}`, avg5=`{near_metrics.get('avg_5d_pct')}`, min_low=`{near_metrics.get('min_min_low_5d_pct')}`, blockers=`{near_candidate.get('sample_blockers')}`",
                f"- score_sweep_gate_summary: status_counts=`{score_summary.get('status_counts')}`, blockers=`{score_summary.get('production_blocking_reason_counts')}`, sample_only_count=`{score_summary.get('sample_only_blocked_count')}`, sample_sufficient_count=`{score_summary.get('sample_sufficient_count')}`",
                f"- score_sweep_near_candidates: sample_only_top=`{sample_candidate.get('selection_rule')}`, sample_sufficient_top=`{sample_sufficient_candidate.get('selection_rule')}`, pareto_top=`{pareto_candidate.get('selection_rule')}`",
                f"- score_sweep_constraint_frontier: production_ready=`{constraint_frontiers.get('production_ready_count')}`, days_low_safe_touch=`{constraint_frontiers.get('days_low_safe_touch_count')}`, one_day_short_low_safe_touch=`{constraint_frontiers.get('one_day_short_low_safe_touch_count')}` best=`{one_day_short.get('selection_rule')}` hit5=`{one_day_short_metrics.get('hit5_dd10_5d_pct')}` active_days=`{one_day_short_metrics.get('active_days')}`, sample_sufficient_touch_but_low_fail=`{constraint_frontiers.get('sample_sufficient_touch_but_low_fail_count')}` best=`{low_fail.get('selection_rule')}` min_low=`{low_fail_metrics.get('min_min_low_5d_pct')}` low_deficit=`{low_fail_deficits.get('min_low_5d_pct')}`",
                f"- candidate_leaderboard: status=`{leaderboard.get('status')}`, candidates=`{leaderboard.get('candidate_count')}`, shadow=`{leaderboard.get('shadow_display_allowed_count')}`, sample_only=`{leaderboard.get('sample_only_shadow_count')}`, production=`{leaderboard.get('production_ready_count')}`, best_sample_only=`{leaderboard_best.get('selection_rule')}`, hit5=`{leaderboard_best_metrics.get('hit5_dd10_5d_pct')}`, n=`{leaderboard_best_metrics.get('n')}`, active_days=`{leaderboard_best_metrics.get('active_days')}`, best_high_precision=`{leaderboard_high_precision.get('selection_rule')}`, high_precision_hit5=`{leaderboard_high_metrics.get('hit5_dd10_5d_pct')}`, high_precision_sample=`{((leaderboard_high_precision.get('sample_progress') or {}) if isinstance(leaderboard_high_precision.get('sample_progress'), dict) else {}).get('completion_pct')}`, upgrade=`{leaderboard_upgrade.get('selection_rule')}`",
                f"- finaltopn_prefilter_proxy: status=`{finaltopn_proxy.get('status')}`, gate=`{finaltopn_proxy_gate.get('status')}`, production_ready=`{finaltopn_proxy_gate.get('production_ready')}`, shadow_display_allowed=`{finaltopn_proxy_gate.get('shadow_display_allowed')}`, n=`{finaltopn_proxy_metrics.get('n')}`, active_days=`{finaltopn_proxy_metrics.get('active_days')}`, hit5=`{finaltopn_proxy_metrics.get('hit5_dd10_5d_pct')}`, avg_exit=`{finaltopn_proxy_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{finaltopn_proxy_metrics.get('avg_dynamic_exit_5d_pct')}`, min_low=`{finaltopn_proxy_metrics.get('min_min_low_5d_pct')}`, blockers=`{finaltopn_proxy_gate.get('production_blocking_reasons')}`",
                f"- finaltopn_actual_sidecar: status=`{finaltopn_actual.get('status')}`, gate=`{finaltopn_actual_gate.get('status')}`, production_ready=`{finaltopn_actual_gate.get('production_ready')}`, shadow_display_allowed=`{finaltopn_actual_gate.get('shadow_display_allowed')}`, n=`{finaltopn_actual_metrics.get('n')}`, active_days=`{finaltopn_actual_metrics.get('active_days')}`, hit5=`{finaltopn_actual_metrics.get('hit5_dd10_5d_pct')}`, avg_exit=`{finaltopn_actual_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{finaltopn_actual_metrics.get('avg_dynamic_exit_5d_pct')}`, min_low=`{finaltopn_actual_metrics.get('min_min_low_5d_pct')}`, blockers=`{finaltopn_actual_gate.get('production_blocking_reasons')}`",
                "",
            ]
        )
    aug = report.get("historical_proxy_augmentation_experiment")
    if isinstance(aug, dict) and aug:
        aug_decision = aug.get("decision") if isinstance(aug.get("decision"), dict) else {}
        lines.extend(
            [
                "## Historical Proxy Exact-Date Augmentation",
                f"- historical_proxy_promotable: `{aug_decision.get('historical_proxy_promotable')}`",
                f"- augmentation_ready_for_research: `{aug_decision.get('augmentation_ready_for_research')}`",
                f"- production_replacement_ready: `{aug_decision.get('production_replacement_ready')}`",
                f"- positive_shadow_result: {aug_decision.get('positive_shadow_result')}",
                f"- reason: {aug_decision.get('reason')}",
                "",
            ]
        )
        for market, payload in (aug.get("markets") or {}).items():
            if not isinstance(payload, dict):
                continue
            augmentation = payload.get("augmentation") if isinstance(payload.get("augmentation"), dict) else {}
            static_aug = (
                payload.get("static_master_augmentation")
                if isinstance(payload.get("static_master_augmentation"), dict)
                else {}
            )
            static_suite = (
                payload.get("static_master_focused_suite")
                if isinstance(payload.get("static_master_focused_suite"), dict)
                else {}
            )
            static_three = (
                payload.get("static_master_three_stage")
                if isinstance(payload.get("static_master_three_stage"), dict)
                else {}
            )
            full_three = payload.get("augmented_three_stage") if isinstance(payload.get("augmented_three_stage"), dict) else {}
            matched_three = payload.get("matched_only_three_stage") if isinstance(payload.get("matched_only_three_stage"), dict) else {}
            sweeps = (
                payload.get("matched_only_threshold_sweeps")
                if isinstance(payload.get("matched_only_threshold_sweeps"), dict)
                else {}
            )
            best_sweep = sweeps.get("best_candidate") if isinstance(sweeps.get("best_candidate"), dict) else {}
            best_sweep_metrics = best_sweep.get("metrics") if isinstance(best_sweep.get("metrics"), dict) else {}
            full_metrics = full_three.get("best_metrics") if isinstance(full_three.get("best_metrics"), dict) else {}
            matched_metrics = (
                matched_three.get("best_metrics") if isinstance(matched_three.get("best_metrics"), dict) else {}
            )
            static_metrics = (
                static_suite.get("best_metrics") if isinstance(static_suite.get("best_metrics"), dict) else {}
            )
            static_gate = static_suite.get("best_gate") if isinstance(static_suite.get("best_gate"), dict) else {}
            static_identity = (
                static_suite.get("best_identity") if isinstance(static_suite.get("best_identity"), dict) else {}
            )
            static_three_metrics = (
                static_three.get("best_metrics") if isinstance(static_three.get("best_metrics"), dict) else {}
            )
            static_three_gate = (
                static_three.get("best_gate") if isinstance(static_three.get("best_gate"), dict) else {}
            )
            static_three_imp = (
                static_three.get("improvement") if isinstance(static_three.get("improvement"), dict) else {}
            )
            lines.extend(
                [
                    f"### {market} Augmentation",
                    f"- exact_match: rows=`{augmentation.get('matched_rows')}`, pct=`{augmentation.get('matched_row_pct')}`, days=`{augmentation.get('matched_days')}`, tickers=`{augmentation.get('matched_tickers')}`",
                    f"- leakage_policy: `{augmentation.get('leakage_policy')}`",
                    f"- static_master: matched_rows=`{static_aug.get('master_matched_rows')}`, matched_pct=`{static_aug.get('master_matched_row_pct')}`, augmented_rows=`{static_aug.get('augmented_rows')}`, augmented_pct=`{static_aug.get('augmented_row_pct')}`, leakage_policy=`{static_aug.get('leakage_policy')}`",
                    f"- static_master_focused_suite: model=`{static_identity.get('model')}`, feature_set=`{static_identity.get('feature_set')}`, gate=`{static_gate.get('status')}`, production_ready=`{static_gate.get('production_ready')}`, shadow_display_allowed=`{static_gate.get('shadow_display_allowed')}`, hit5=`{static_metrics.get('hit5_dd10_5d_pct')}`, win5=`{static_metrics.get('win_5d_pct')}`, hit10=`{static_metrics.get('hit10_5d_pct')}`, avg5=`{static_metrics.get('avg_5d_pct')}`, min_ordered_exit=`{static_metrics.get('min_ordered_exit_5d_pct')}`, expected_net=`{(static_gate.get('production_economics') or {}).get('expected_touch_policy_net_5d_pct')}`, blockers=`{static_gate.get('production_blocking_reasons')}`",
                    f"- static_master_3stage: status=`{static_three.get('status')}`, gate=`{static_three_gate.get('status')}`, production_ready=`{static_three_gate.get('production_ready')}`, shadow_display_allowed=`{static_three_gate.get('shadow_display_allowed')}`, hit5=`{static_three_metrics.get('hit5_dd10_5d_pct')}`, avg_exit=`{static_three_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{static_three_metrics.get('avg_dynamic_exit_5d_pct')}`, tail=`{static_three_metrics.get('tail_breach_5d_pct')}`, min_low=`{static_three_metrics.get('min_min_low_5d_pct')}`, avg_exit_delta=`{static_three_imp.get('avg_ordered_exit_delta_pct')}`, hit5_delta=`{static_three_imp.get('hit5_dd10_delta_pct')}`, blockers=`{static_three_gate.get('production_blocking_reasons')}`",
                    f"- full_augmented_3stage: status=`{full_three.get('status')}`, hit5=`{full_metrics.get('hit5_dd10_5d_pct')}`, avg_exit=`{full_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{full_metrics.get('avg_dynamic_exit_5d_pct')}`, tail=`{full_metrics.get('tail_breach_5d_pct')}`, min_low=`{full_metrics.get('min_min_low_5d_pct')}`",
                    f"- matched_only_3stage: status=`{matched_three.get('status')}`, hit5=`{matched_metrics.get('hit5_dd10_5d_pct')}`, avg_exit=`{matched_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{matched_metrics.get('avg_dynamic_exit_5d_pct')}`, tail=`{matched_metrics.get('tail_breach_5d_pct')}`, min_low=`{matched_metrics.get('min_min_low_5d_pct')}`",
                    f"- matched_only_sweep_best: feature_set=`{sweeps.get('best_feature_set')}`, rule=`{best_sweep.get('selection_rule')}`, status=`{best_sweep.get('gate_status')}`, hit5=`{best_sweep_metrics.get('hit5_dd10_5d_pct')}`, avg5=`{best_sweep_metrics.get('avg_5d_pct')}`, min_low=`{best_sweep_metrics.get('min_min_low_5d_pct')}`, blockers=`{best_sweep.get('production_blocking_reasons')}`",
                    "",
                ]
            )
    lines.extend(["## UI 요구사항"])
    lines.extend(f"- {item}" for item in report.get("ui_requirements") or [])
    lines.extend(["", f"- operator_report_rule: {report.get('operator_report_rule')}"])
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(_markdown(report) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-report", default=str(DEFAULT_SHADOW_REPORT))
    parser.add_argument("--three-stage-dynamic-report", default=str(DEFAULT_THREE_STAGE_DYNAMIC_REPORT))
    parser.add_argument("--three-stage-fixed-report", default=str(DEFAULT_THREE_STAGE_FIXED_REPORT))
    parser.add_argument("--market-comparison-report", default=str(DEFAULT_MARKET_COMPARISON_REPORT))
    parser.add_argument("--sidecar-baseline-sweep-report", default=str(DEFAULT_SIDECAR_BASELINE_SWEEP))
    parser.add_argument("--sidecar-score-sweep-report", default=str(DEFAULT_SIDECAR_SCORE_SWEEP))
    parser.add_argument("--sidecar-proxy-gap-report", default=str(DEFAULT_SIDECAR_PROXY_GAP))
    parser.add_argument("--sidecar-augmentation-report", default=str(DEFAULT_SIDECAR_AUGMENTATION))
    parser.add_argument("--augmented-three-stage-report", default=str(DEFAULT_AUGMENTED_THREE_STAGE))
    parser.add_argument("--matched-only-three-stage-report", default=str(DEFAULT_MATCHED_ONLY_THREE_STAGE))
    parser.add_argument(
        "--matched-only-sweep-report",
        action="append",
        default=[f"{key}={path}" for key, path in DEFAULT_MATCHED_ONLY_SWEEPS.items()],
        help="FEATURE_SET=report json path",
    )
    parser.add_argument("--deployment-consistency-report", default=str(DEFAULT_DEPLOYMENT_CONSISTENCY))
    parser.add_argument("--candidate-leaderboard-report", default=str(DEFAULT_CANDIDATE_LEADERBOARD))
    parser.add_argument("--finaltopn-prefilter-proxy-report", default=str(DEFAULT_FINALTOPN_PREFILTER_PROXY))
    parser.add_argument("--finaltopn-actual-sidecar-report", default=str(DEFAULT_FINALTOPN_ACTUAL_SIDECAR))
    parser.add_argument("--static-master-augmentation-report", default=str(DEFAULT_STATIC_MASTER_AUGMENTATION))
    parser.add_argument("--static-master-focused-suite-report", default=str(DEFAULT_STATIC_MASTER_FOCUSED_SUITE))
    parser.add_argument(
        "--static-master-three-stage-report",
        action="append",
        default=[f"{key}={path}" for key, path in DEFAULT_STATIC_MASTER_THREE_STAGE.items()],
        help="MARKET=report json path",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(list(argv) if argv is not None else None)
    matched_only_sweep_paths = {}
    for value in args.matched_only_sweep_report:
        if "=" not in value:
            continue
        feature_set, raw_path = value.split("=", 1)
        matched_only_sweep_paths[feature_set.strip()] = Path(raw_path)
    static_master_three_stage_paths = {}
    for value in args.static_master_three_stage_report:
        if "=" not in value:
            continue
        market, raw_path = value.split("=", 1)
        static_master_three_stage_paths[market.strip().upper()] = Path(raw_path)
    report = build_report(
        shadow_report_path=Path(args.shadow_report),
        three_stage_dynamic_path=Path(args.three_stage_dynamic_report),
        three_stage_fixed_path=Path(args.three_stage_fixed_report),
        market_comparison_path=Path(args.market_comparison_report),
        sidecar_baseline_sweep_path=Path(args.sidecar_baseline_sweep_report),
        sidecar_score_sweep_path=Path(args.sidecar_score_sweep_report),
        sidecar_proxy_gap_path=Path(args.sidecar_proxy_gap_report),
        sidecar_augmentation_path=Path(args.sidecar_augmentation_report),
        augmented_three_stage_path=Path(args.augmented_three_stage_report),
        matched_only_three_stage_path=Path(args.matched_only_three_stage_report),
        matched_only_sweep_paths=matched_only_sweep_paths,
        deployment_consistency_path=Path(args.deployment_consistency_report),
        candidate_leaderboard_path=Path(args.candidate_leaderboard_report),
        finaltopn_prefilter_proxy_path=Path(args.finaltopn_prefilter_proxy_report),
        finaltopn_actual_sidecar_path=Path(args.finaltopn_actual_sidecar_report),
        static_master_augmentation_path=Path(args.static_master_augmentation_report),
        static_master_focused_suite_path=Path(args.static_master_focused_suite_report),
        static_master_three_stage_paths=static_master_three_stage_paths,
    )
    write_report(report, Path(args.output))
    print(
        json.dumps(
            {
                "output": args.output,
                "decision": report.get("decision"),
                "markets": sorted((report.get("markets") or {}).keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
