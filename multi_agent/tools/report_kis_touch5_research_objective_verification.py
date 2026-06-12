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
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/learning/kis_touch5_research_objective_verification_20260612.json"
DEFAULT_SHADOW_REPORT = ROOT / "runtime_state/reports/learning/kis_shadow_research_verification_20260612.json"
DEFAULT_THREE_STAGE_DYNAMIC_REPORT = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_dynamic_exit_20260101_20260610.json"
)
DEFAULT_THREE_STAGE_FIXED_REPORT = (
    ROOT / "runtime_state/reports/learning/kis_three_stage_ev_ranker_20260101_20260610.json"
)
DEFAULT_MARKET_COMPARISON_REPORT = ROOT / "runtime_state/reports/learning/kis_model_market_comparison.json"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


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
        "avg_min_low_5d_pct",
        "min_min_low_5d_pct",
        "expected_touch_policy_net_5d_pct",
        "stop5_pct",
        "target_before_stop_5d_pct",
        "stop_before_target_5d_pct",
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
    return {
        "identity": current.get("identity") or {
            "feature_set": result.get("feature_set"),
            "model": result.get("model"),
            "selection_rule": result.get("selection_rule"),
            "prob_threshold": result.get("prob_threshold"),
            "tail_risk_prob_threshold": result.get("dd10_safety_threshold"),
        },
        "metrics": _pick_metrics(result),
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
) -> Dict[str, Any]:
    shadow_report = _load_json(shadow_report_path)
    three_stage_dynamic = _load_json(three_stage_dynamic_path)
    three_stage_fixed = _load_json(three_stage_fixed_path)
    market_comparison = _load_json(market_comparison_path)
    markets: Dict[str, Any] = {}
    for market in ("KOSPI", "KOSDAQ"):
        markets[market] = {
            "three_stage_ev_ranker": _three_stage_market(three_stage_dynamic, three_stage_fixed, market),
            "kis_sidecar_longfold_shadow": _shadow_market(shadow_report, market_comparison, market),
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
        ],
        "markets": markets,
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
        lines.extend(
            [
                f"## {market}",
                f"- selected_shadow_model: `{identity.get('feature_set')}` / `{identity.get('model')}` / `{identity.get('selection_rule')}`",
                f"- gate: status=`{gate.get('status')}`, production_ready=`{gate.get('production_ready')}`, shadow_display_allowed=`{gate.get('shadow_display_allowed')}`",
                f"- blockers: `{gate.get('production_blocking_reasons') or []}`",
                f"- shadow metrics: n=`{metrics.get('n')}`, active_days=`{metrics.get('active_days')}`, active_runs=`{metrics.get('active_runs')}`, hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}`, hit10=`{metrics.get('hit10_5d_pct')}`, avg5=`{metrics.get('avg_5d_pct')}`, min_low=`{metrics.get('min_min_low_5d_pct')}`, expected_touch_net=`{metrics.get('expected_touch_policy_net_5d_pct') or econ.get('expected_touch_policy_net_5d_pct')}`",
                f"- three_stage_result: hit5_dd10=`{three_metrics.get('hit5_dd10_5d_pct')}`, dynamic_exit=`{three_metrics.get('avg_dynamic_exit_5d_pct')}`, tail=`{three_metrics.get('tail_breach_5d_pct')}`, min_low=`{three_metrics.get('min_min_low_5d_pct')}`",
                f"- three_stage_improvement_vs_broad: avg_exit_delta=`{three_imp.get('avg_ordered_exit_delta_pct')}`, hit5_delta=`{three_imp.get('hit5_dd10_delta_pct')}`",
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
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report(
        shadow_report_path=Path(args.shadow_report),
        three_stage_dynamic_path=Path(args.three_stage_dynamic_report),
        three_stage_fixed_path=Path(args.three_stage_fixed_report),
        market_comparison_path=Path(args.market_comparison_report),
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
