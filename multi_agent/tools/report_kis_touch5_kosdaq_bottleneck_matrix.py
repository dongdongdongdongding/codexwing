#!/usr/bin/env python3
"""Summarize KOSDAQ KIS touch5/dd10 bottleneck evidence across real reports."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORT_VERSION = "kis_touch5_kosdaq_bottleneck_matrix_v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "runtime_state/reports/learning/kis_touch5_kosdaq_bottleneck_matrix_20260613.json"
)
DEFAULT_STABILITY_REPORTS = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_kosdaq_stability_kis_sidecar_only_lightgbm_20260613.json",
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_kosdaq_stability_kis_full_augmented_lightgbm_20260613.json",
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_kosdaq_stability_kis_failure_risk_augmented_lightgbm_20260613.json",
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_kosdaq_stability_kis_failure_risk_numeric_lightgbm_20260613.json",
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_kosdaq_stability_kis_failure_risk_augmented_logistic_20260613.json",
)
DEFAULT_DRAWDOWN_REPORT = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_dd10_drawdown_filter_research_kosdaq_probtail_p05_20260613.json"
)
DEFAULT_COMPOUND_DRAWDOWN_REPORT = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_dd10_drawdown_filter_research_kosdaq_compound_p05_20260613.json"
)
DEFAULT_COMPOUND_DRAWDOWN_REPORTS = (
    DEFAULT_COMPOUND_DRAWDOWN_REPORT,
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_dd10_drawdown_filter_research_kosdaq_compound_top5_p03_20260613.json",
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_dd10_drawdown_filter_research_kosdaq_compound_top10_all_20260613.json",
)
REQUIRED_HIT5 = 73.0
REQUIRED_MIN_LOW = -10.0
REQUIRED_N = 45
REQUIRED_ACTIVE_DAYS = 20
REQUIRED_ACTIVE_RUNS = 20


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_optional(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _load_json(path)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def _metric(row: Mapping[str, Any], key: str) -> Any:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else row
    return metrics.get(key) if isinstance(metrics, Mapping) else None


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _candidate_summary(row: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(row, Mapping) or not row:
        return {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    gate = row.get("kis_model_gate") if isinstance(row.get("kis_model_gate"), Mapping) else row.get("gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "selection_rule": row.get("selection_rule") or (row.get("identity") or {}).get("selection_rule"),
        "stability_status": row.get("stability_status"),
        "gate_status": row.get("gate_status") or gate.get("status"),
        "period_pass_count": row.get("period_pass_count"),
        "period_result_count": row.get("period_result_count"),
        "selected_month_coverage": row.get("selected_month_coverage") or {},
        "metrics": {
            key: metrics.get(key)
            for key in (
                "n",
                "active_days",
                "active_runs",
                "hit5_dd10_5d_pct",
                "hit10_5d_pct",
                "avg_5d_pct",
                "min_min_low_5d_pct",
                "expected_touch_policy_net_5d_pct",
            )
            if key in metrics
        },
        "blockers": gate.get("production_blocking_reasons")
        or row.get("production_blocking_reasons")
        or [],
    }


def _stability_market_summary(path: Path, report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    contract = report.get("evaluation_contract") if isinstance(report.get("evaluation_contract"), Mapping) else {}
    markets = report.get("markets") if isinstance(report.get("markets"), Mapping) else {}
    row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
    top_candidates = row.get("top_candidates") if isinstance(row.get("top_candidates"), list) else []
    best = top_candidates[0] if top_candidates and isinstance(top_candidates[0], Mapping) else {}
    stable_top = row.get("period_stable_top") if isinstance(row.get("period_stable_top"), list) else []
    stable = stable_top[0] if stable_top and isinstance(stable_top[0], Mapping) else {}
    best_summary = _candidate_summary(best)
    metrics = best_summary.get("metrics") or {}
    return {
        "source_path": _rel(path),
        "feature_set": contract.get("feature_set"),
        "model": contract.get("model"),
        "evaluated_count": row.get("evaluated_count"),
        "production_ready_count": row.get("production_ready_count"),
        "period_stable_count": row.get("period_stable_count"),
        "shadow_period_stable_count": row.get("shadow_period_stable_count"),
        "best_overall": best_summary,
        "best_period_stable": _candidate_summary(stable),
        "gate_checks": {
            "hit5_pass": _float(metrics.get("hit5_dd10_5d_pct"), -999.0) >= REQUIRED_HIT5,
            "min_low_pass": _float(metrics.get("min_min_low_5d_pct"), -999.0) >= REQUIRED_MIN_LOW,
            "active_days_pass": int(metrics.get("active_days") or 0) >= REQUIRED_ACTIVE_DAYS,
            "period_stable_pass": bool(row.get("period_stable_count")),
        },
    }


def _drawdown_summary(report: Mapping[str, Any]) -> Dict[str, Any]:
    if not report:
        return {}
    base = report.get("base_candidate") if isinstance(report.get("base_candidate"), Mapping) else {}
    holdout = report.get("holdout_validation") if isinstance(report.get("holdout_validation"), Mapping) else {}
    selection_best = (
        holdout.get("selection_best_holdout_evaluation")
        if isinstance(holdout.get("selection_best_holdout_evaluation"), Mapping)
        else {}
    )
    top_results = report.get("top_results") if isinstance(report.get("top_results"), list) else []
    best_top_result = top_results[0] if top_results and isinstance(top_results[0], Mapping) else {}
    return {
        "status": report.get("status"),
        "validation_mode": report.get("validation_mode"),
        "score_mode": report.get("score_mode"),
        "topn": report.get("topn"),
        "prob_threshold": report.get("prob_threshold"),
        "tail_threshold": report.get("tail_threshold"),
        "compound_filter_depth": report.get("compound_filter_depth"),
        "compound_single_limit": report.get("compound_single_limit"),
        "compound_candidate_limit": report.get("compound_candidate_limit"),
        "filters_tested": report.get("filters_tested"),
        "production_ready_count": report.get("production_ready_count"),
        "deployment_ready": bool(report.get("deployment_ready")),
        "base_candidate": _candidate_summary(base),
        "best_top_result": _candidate_summary(best_top_result),
        "candidate_frontier": report.get("candidate_frontier") or {},
        "holdout": {
            "status": holdout.get("status"),
            "selection_candidates_tested": holdout.get("selection_candidates_tested"),
            "holdout_candidates_evaluated": holdout.get("holdout_candidates_evaluated"),
            "holdout_gate_pass_count": holdout.get("holdout_gate_pass_count"),
            "selection_best_holdout_evaluation": _candidate_summary(selection_best),
            "holdout_frontier": holdout.get("holdout_frontier") or {},
            "decision": holdout.get("decision") or {},
        },
        "rolling_prior": report.get("rolling_prior_validation") or {},
    }


def _rank_key(row: Mapping[str, Any]) -> tuple[float, float, float, int]:
    metrics = ((row.get("best_overall") or {}).get("metrics") or {})
    return (
        _float(metrics.get("hit5_dd10_5d_pct"), -999.0),
        _float(metrics.get("min_min_low_5d_pct"), -999.0),
        _float(metrics.get("avg_5d_pct"), -999.0),
        int(metrics.get("active_days") or 0),
    )


def _best_safe_tail(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    eligible = []
    for row in rows:
        metrics = ((row.get("best_overall") or {}).get("metrics") or {})
        if _float(metrics.get("min_min_low_5d_pct"), -999.0) >= REQUIRED_MIN_LOW:
            eligible.append(row)
    if not eligible:
        return {}
    return dict(sorted(eligible, key=_rank_key, reverse=True)[0])


def _sample_gate_pass(metrics: Mapping[str, Any]) -> bool:
    return (
        int(metrics.get("n") or 0) >= REQUIRED_N
        and int(metrics.get("active_days") or 0) >= REQUIRED_ACTIVE_DAYS
        and int(metrics.get("active_runs") or 0) >= REQUIRED_ACTIVE_RUNS
    )


def _compound_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, int, int, int]:
    candidate = row.get("best_top_result") if isinstance(row.get("best_top_result"), Mapping) else {}
    metrics = candidate.get("metrics") if isinstance(candidate.get("metrics"), Mapping) else {}
    return (
        _float(metrics.get("hit5_dd10_5d_pct"), -999.0),
        _float(metrics.get("min_min_low_5d_pct"), -999.0),
        _float(metrics.get("avg_5d_pct"), -999.0),
        int(metrics.get("active_days") or 0),
        int(metrics.get("active_runs") or 0),
        int(metrics.get("n") or 0),
    )


def _compound_report_summaries(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        row = _drawdown_summary(_load_json(path))
        row["source_path"] = _rel(path)
        rows.append(row)
    rows.sort(key=_compound_sort_key, reverse=True)
    return rows


def build_report(
    *,
    stability_report_paths: Sequence[Path] = DEFAULT_STABILITY_REPORTS,
    drawdown_report_path: Path | None = DEFAULT_DRAWDOWN_REPORT,
    compound_drawdown_report_path: Path | None = None,
    compound_drawdown_report_paths: Sequence[Path] | None = None,
    market: str = "KOSDAQ",
) -> Dict[str, Any]:
    matrix: List[Dict[str, Any]] = []
    missing: List[str] = []
    for path in stability_report_paths:
        if not path.exists():
            missing.append(_rel(path))
            continue
        matrix.append(_stability_market_summary(path, _load_json(path), market))
    matrix.sort(key=_rank_key, reverse=True)
    best = dict(matrix[0]) if matrix else {}
    best_safe_tail = _best_safe_tail(matrix)
    drawdown = _drawdown_summary(_load_optional(drawdown_report_path))
    if compound_drawdown_report_paths is not None:
        compound_paths = list(compound_drawdown_report_paths)
    elif compound_drawdown_report_path is not None:
        compound_paths = [compound_drawdown_report_path]
    else:
        compound_paths = list(DEFAULT_COMPOUND_DRAWDOWN_REPORTS)
    compound_drawdowns = _compound_report_summaries(compound_paths)
    compound_drawdown = compound_drawdowns[0] if compound_drawdowns else {}
    drawdown_holdout = drawdown.get("holdout") if isinstance(drawdown.get("holdout"), Mapping) else {}
    compound_holdout = (
        compound_drawdown.get("holdout") if isinstance(compound_drawdown.get("holdout"), Mapping) else {}
    )
    holdout_gate_count = int(drawdown_holdout.get("holdout_gate_pass_count") or 0)
    compound_holdout_gate_count = int(compound_holdout.get("holdout_gate_pass_count") or 0)
    period_stable_total = sum(int(row.get("period_stable_count") or 0) for row in matrix)
    production_ready_total = sum(int(row.get("production_ready_count") or 0) for row in matrix)
    compound_best = (
        compound_drawdown.get("best_top_result")
        if isinstance(compound_drawdown.get("best_top_result"), Mapping)
        else {}
    )
    compound_best_metrics = compound_best.get("metrics") if isinstance(compound_best.get("metrics"), Mapping) else {}
    compound_sample_gate = _sample_gate_pass(compound_best_metrics)
    compound_sample_sufficient_total = sum(
        int((row.get("candidate_frontier") or {}).get("sample_sufficient_count") or 0)
        for row in compound_drawdowns
    )
    compound_sample_hit_low_safe_total = sum(
        int((row.get("candidate_frontier") or {}).get("sample_hit_low_safe_count") or 0)
        for row in compound_drawdowns
    )
    primary_blockers = [
        "no_period_stable_kosdaq_candidate",
        "min_low_5d_tail_below_minus10",
        "drawdown_filter_holdout_gate_pass_count_zero",
    ]
    if compound_drawdown:
        if compound_holdout_gate_count <= 0:
            primary_blockers.append("compound_veto_holdout_gate_pass_count_zero")
        if not compound_sample_gate:
            primary_blockers.append("compound_veto_sample_gate_shortfall")
        if compound_sample_sufficient_total <= 0:
            primary_blockers.append("compound_veto_no_sample_sufficient_candidate_across_recall")
        if compound_sample_hit_low_safe_total <= 0:
            primary_blockers.append("compound_veto_no_sample_hit_low_safe_candidate_across_recall")
    decision_status = (
        "production_candidate_found"
        if production_ready_total > 0 and holdout_gate_count > 0 and compound_holdout_gate_count > 0
        else "kosdaq_tail_risk_blocks_production_replacement"
    )
    return {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "market": market,
        "no_dummy_data": True,
        "input_reports": {
            "stability_reports": [_rel(path) for path in stability_report_paths if path.exists()],
            "missing_stability_reports": missing,
            "drawdown_report": _rel(drawdown_report_path)
            if drawdown_report_path and drawdown_report_path.exists()
            else None,
            "compound_drawdown_report": _rel(compound_drawdown_report_path)
            if compound_drawdown_report_path and compound_drawdown_report_path.exists()
            else None,
            "compound_drawdown_reports": [_rel(path) for path in compound_paths if path.exists()],
        },
        "gate_requirements": {
            "hit5_dd10_5d_pct_gte": REQUIRED_HIT5,
            "min_min_low_5d_pct_gte": REQUIRED_MIN_LOW,
            "n_gte": REQUIRED_N,
            "active_days_gte": REQUIRED_ACTIVE_DAYS,
            "active_runs_gte": REQUIRED_ACTIVE_RUNS,
            "holdout_gate_pass_required": True,
        },
        "matrix": matrix,
        "best_by_hit5": best,
        "best_safe_tail": best_safe_tail,
        "drawdown_filter": drawdown,
        "compound_drawdown_filter": compound_drawdown,
        "compound_drawdown_filters": compound_drawdowns,
        "decision": {
            "status": decision_status,
            "production_replacement_ready": False,
            "period_stable_candidate_count": period_stable_total,
            "production_ready_count": production_ready_total,
            "holdout_gate_pass_count": holdout_gate_count,
            "compound_holdout_gate_pass_count": compound_holdout_gate_count,
            "best_research_candidate": (best.get("best_overall") or {}),
            "best_safe_tail_candidate": (best_safe_tail.get("best_overall") or {}),
            "best_compound_veto_candidate": compound_best,
            "best_compound_veto_sample_gate_pass": compound_sample_gate,
            "compound_veto_sample_sufficient_candidate_count": compound_sample_sufficient_total,
            "compound_veto_sample_hit_low_safe_candidate_count": compound_sample_hit_low_safe_total,
            "model_change_helped": bool(
                best.get("model") and str(best.get("model")).lower() != "lightgbm"
            ),
            "primary_blockers": primary_blockers,
            "recommended_action": (
                "keep KOSDAQ KIS touch5/dd10 in shadow; prioritize KOSDAQ-specific tail-risk "
                "veto features and cached prediction matrix before any promotion review"
            ),
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    lines = [
        "# KIS Touch5 KOSDAQ Bottleneck Matrix",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- market: `{report.get('market')}`",
        f"- status: `{decision.get('status')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- period_stable_candidate_count: `{decision.get('period_stable_candidate_count')}`",
        f"- production_ready_count: `{decision.get('production_ready_count')}`",
        f"- holdout_gate_pass_count: `{decision.get('holdout_gate_pass_count')}`",
        f"- compound_holdout_gate_pass_count: `{decision.get('compound_holdout_gate_pass_count')}`",
        f"- recommended_action: {decision.get('recommended_action')}",
        "",
        "## Stability Matrix",
        "| feature_set | model | stable | prod | rule | n | days | hit5 | avg5 | min_low | blockers |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("matrix") or []:
        best = row.get("best_overall") if isinstance(row.get("best_overall"), Mapping) else {}
        metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
        lines.append(
            f"| {row.get('feature_set')} | {row.get('model')} | {row.get('period_stable_count')} | "
            f"{row.get('production_ready_count')} | {best.get('selection_rule')} | {metrics.get('n')} | "
            f"{metrics.get('active_days')} | {metrics.get('hit5_dd10_5d_pct')} | {metrics.get('avg_5d_pct')} | "
            f"{metrics.get('min_min_low_5d_pct')} | {best.get('blockers')} |"
        )
    drawdown = report.get("drawdown_filter") if isinstance(report.get("drawdown_filter"), Mapping) else {}
    base = drawdown.get("base_candidate") if isinstance(drawdown.get("base_candidate"), Mapping) else {}
    base_metrics = base.get("metrics") if isinstance(base.get("metrics"), Mapping) else {}
    holdout = drawdown.get("holdout") if isinstance(drawdown.get("holdout"), Mapping) else {}
    selection_best = (
        holdout.get("selection_best_holdout_evaluation")
        if isinstance(holdout.get("selection_best_holdout_evaluation"), Mapping)
        else {}
    )
    selection_metrics = selection_best.get("metrics") if isinstance(selection_best.get("metrics"), Mapping) else {}
    compound = (
        report.get("compound_drawdown_filter")
        if isinstance(report.get("compound_drawdown_filter"), Mapping)
        else {}
    )
    compounds = (
        report.get("compound_drawdown_filters")
        if isinstance(report.get("compound_drawdown_filters"), list)
        else []
    )
    compound_best = (
        compound.get("best_top_result") if isinstance(compound.get("best_top_result"), Mapping) else {}
    )
    compound_metrics = compound_best.get("metrics") if isinstance(compound_best.get("metrics"), Mapping) else {}
    compound_holdout = compound.get("holdout") if isinstance(compound.get("holdout"), Mapping) else {}
    compound_selection_best = (
        compound_holdout.get("selection_best_holdout_evaluation")
        if isinstance(compound_holdout.get("selection_best_holdout_evaluation"), Mapping)
        else {}
    )
    compound_selection_metrics = (
        compound_selection_best.get("metrics") if isinstance(compound_selection_best.get("metrics"), Mapping) else {}
    )
    lines.extend(
        [
            "",
            "## Drawdown Holdout",
            f"- status: `{drawdown.get('status')}`",
            f"- base: rule=`{base.get('selection_rule')}`, n=`{base_metrics.get('n')}`, days=`{base_metrics.get('active_days')}`, hit5=`{base_metrics.get('hit5_dd10_5d_pct')}`, avg5=`{base_metrics.get('avg_5d_pct')}`, min_low=`{base_metrics.get('min_min_low_5d_pct')}`",
            f"- holdout: status=`{holdout.get('status')}`, candidates=`{holdout.get('selection_candidates_tested')}`, evaluated=`{holdout.get('holdout_candidates_evaluated')}`, gate_pass=`{holdout.get('holdout_gate_pass_count')}`",
            f"- selection_best_holdout: rule=`{selection_best.get('selection_rule')}`, n=`{selection_metrics.get('n')}`, days=`{selection_metrics.get('active_days')}`, hit5=`{selection_metrics.get('hit5_dd10_5d_pct')}`, min_low=`{selection_metrics.get('min_min_low_5d_pct')}`",
            "",
            "## Compound Veto Drawdown",
            f"- status: `{compound.get('status')}`",
            f"- filters_tested: `{compound.get('filters_tested')}`",
            f"- compound_filter_depth: `{compound.get('compound_filter_depth')}`",
            f"- best_compound: rule=`{compound_best.get('selection_rule')}`, n=`{compound_metrics.get('n')}`, days=`{compound_metrics.get('active_days')}`, runs=`{compound_metrics.get('active_runs')}`, hit5=`{compound_metrics.get('hit5_dd10_5d_pct')}`, avg5=`{compound_metrics.get('avg_5d_pct')}`, min_low=`{compound_metrics.get('min_min_low_5d_pct')}`",
            f"- holdout: status=`{compound_holdout.get('status')}`, candidates=`{compound_holdout.get('selection_candidates_tested')}`, evaluated=`{compound_holdout.get('holdout_candidates_evaluated')}`, gate_pass=`{compound_holdout.get('holdout_gate_pass_count')}`",
            f"- selection_best_holdout: rule=`{compound_selection_best.get('selection_rule')}`, n=`{compound_selection_metrics.get('n')}`, days=`{compound_selection_metrics.get('active_days')}`, hit5=`{compound_selection_metrics.get('hit5_dd10_5d_pct')}`, min_low=`{compound_selection_metrics.get('min_min_low_5d_pct')}`",
            "",
            "| source | score | topN | prob | base_n | base_days | base_hit5 | base_min_low | candidates | sample | low_safe | hit_low_safe | sample_hit_low_safe | holdout_gate |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in compounds:
        if not isinstance(row, Mapping):
            continue
        base_candidate = row.get("base_candidate") if isinstance(row.get("base_candidate"), Mapping) else {}
        base_metrics = base_candidate.get("metrics") if isinstance(base_candidate.get("metrics"), Mapping) else {}
        frontier = row.get("candidate_frontier") if isinstance(row.get("candidate_frontier"), Mapping) else {}
        row_holdout = row.get("holdout") if isinstance(row.get("holdout"), Mapping) else {}
        lines.append(
            f"| {row.get('source_path')} | {row.get('score_mode')} | {row.get('topn')} | {row.get('prob_threshold')} | "
            f"{base_metrics.get('n')} | {base_metrics.get('active_days')} | {base_metrics.get('hit5_dd10_5d_pct')} | "
            f"{base_metrics.get('min_min_low_5d_pct')} | {frontier.get('total_candidates')} | "
            f"{frontier.get('sample_sufficient_count')} | {frontier.get('low_safe_count')} | "
            f"{frontier.get('hit_low_safe_count')} | {frontier.get('sample_hit_low_safe_count')} | "
            f"{row_holdout.get('holdout_gate_pass_count')} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", default="KOSDAQ")
    parser.add_argument("--stability-report", action="append", default=None)
    parser.add_argument("--drawdown-report", default=str(DEFAULT_DRAWDOWN_REPORT))
    parser.add_argument("--compound-drawdown-report", action="append", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    stability_paths = (
        [Path(item) for item in args.stability_report]
        if args.stability_report
        else list(DEFAULT_STABILITY_REPORTS)
    )
    report = build_report(
        stability_report_paths=stability_paths,
        drawdown_report_path=Path(args.drawdown_report) if args.drawdown_report else None,
        compound_drawdown_report_paths=[Path(item) for item in args.compound_drawdown_report]
        if args.compound_drawdown_report
        else None,
        market=str(args.market).upper(),
    )
    output = Path(args.output)
    write_report(report, output)
    print(
        json.dumps(
            {
                "output": _rel(output),
                "status": (report.get("decision") or {}).get("status"),
                "production_replacement_ready": (report.get("decision") or {}).get("production_replacement_ready"),
                "best_rule": ((report.get("decision") or {}).get("best_research_candidate") or {}).get(
                    "selection_rule"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
