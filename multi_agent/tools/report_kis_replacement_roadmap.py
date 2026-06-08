#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
LEARNING_REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "learning"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _compact_market_reflections(model_comparison: Mapping[str, Any]) -> Dict[str, Any]:
    markets = model_comparison.get("markets")
    if not isinstance(markets, dict):
        return {}

    compact: Dict[str, Any] = {}
    for market, payload in sorted(markets.items()):
        if not isinstance(payload, dict):
            continue
        current = _as_dict(payload.get("current_kis_model"))
        identity = _as_dict(current.get("identity"))
        metrics = _as_dict(current.get("metrics"))
        gate = _as_dict(current.get("kis_model_gate"))
        reflection = _as_dict(payload.get("operational_reflection"))

        deltas: List[Dict[str, Any]] = []
        raw_deltas = payload.get("performance_comparison_vs_existing")
        if isinstance(raw_deltas, list):
            for delta in raw_deltas:
                if not isinstance(delta, dict):
                    continue
                deltas.append(
                    {
                        "baseline": delta.get("baseline"),
                        "topn": delta.get("topn"),
                        "sample_delta_n": delta.get("sample_delta_n"),
                        "active_days_delta": delta.get("active_days_delta"),
                        "win_1d_delta_pct": delta.get("win_1d_delta_pct"),
                        "win_3d_delta_pct": delta.get("win_3d_delta_pct"),
                        "win_5d_delta_pct": delta.get("win_5d_delta_pct"),
                        "avg_1d_delta_pct": delta.get("avg_1d_delta_pct"),
                        "avg_3d_delta_pct": delta.get("avg_3d_delta_pct"),
                        "avg_5d_delta_pct": delta.get("avg_5d_delta_pct"),
                        "min_1d_delta_pct": delta.get("min_1d_delta_pct"),
                        "min_5d_delta_pct": delta.get("min_5d_delta_pct"),
                        "min_low_5d_delta_pct": delta.get("min_low_5d_delta_pct"),
                    }
                )

        compact[market] = {
            "kis_candidate": {
                "label": identity.get("label"),
                "feature_set": identity.get("feature_set"),
                "model": identity.get("model"),
                "selection_rule": identity.get("selection_rule"),
                "topn": identity.get("topn"),
            },
            "current_metrics": {
                "n": metrics.get("n"),
                "active_days": metrics.get("active_days"),
                "active_runs": metrics.get("active_runs"),
                "win_1d_pct": metrics.get("win_1d_pct"),
                "win_3d_pct": metrics.get("win_3d_pct"),
                "win_5d_pct": metrics.get("win_5d_pct"),
                "avg_1d_pct": metrics.get("avg_1d_pct"),
                "avg_3d_pct": metrics.get("avg_3d_pct"),
                "avg_5d_pct": metrics.get("avg_5d_pct"),
                "min_1d_pct": metrics.get("min_1d_pct"),
                "min_5d_pct": metrics.get("min_5d_pct"),
                "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
                "max_5d_pct": metrics.get("max_5d_pct"),
                "bad_path_pct": metrics.get("bad_path_pct"),
            },
            "gate": {
                "status": gate.get("status"),
                "production_ready": gate.get("production_ready"),
                "shadow_display_allowed": gate.get("shadow_display_allowed"),
                "risk_review_required": gate.get("risk_review_required"),
                "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
                "risk_review_reasons": gate.get("risk_review_reasons") or [],
            },
            "operational_action": reflection.get("action"),
            "ui_recommendations": reflection.get("ui_recommendations") or [],
            "performance_delta_vs_existing": deltas,
        }
    return compact


def _theme_news_backfill_status(
    *,
    backfill_report: Mapping[str, Any],
    verify_report: Mapping[str, Any],
) -> Dict[str, Any]:
    backfill_summary = _as_dict(backfill_report.get("summary"))
    verify_summary = _as_dict(verify_report.get("summary"))
    kis_call_counts = _as_dict(backfill_summary.get("kis_call_counts"))
    return {
        "source_backfill_report": "runtime_state/reports/learning/kis_theme_news_emitted_news_backfill.json",
        "source_verify_report": "runtime_state/reports/learning/kis_theme_news_emitted_news_backfill_verify.json",
        "candidate_rows": backfill_summary.get("candidate_rows"),
        "rows_written": backfill_summary.get("rows_written"),
        "unique_ticker_date_keys": backfill_summary.get("unique_keys"),
        "kis_news_api_calls": kis_call_counts.get("news_titles"),
        "kis_failures": backfill_summary.get("kis_failures") or {},
        "key_failures": backfill_summary.get("key_failures") or {},
        "verified_rows": verify_summary.get("checked_rows"),
        "evidence_rows": verify_summary.get("kis_theme_news_evidence_rows"),
        "kis_backed_rows": verify_summary.get("kis_theme_news_kis_backed_rows"),
        "news_checked_rows": verify_summary.get("kis_theme_news_news_checked_rows"),
        "strength_levels": verify_summary.get("kis_theme_news_levels") or {},
        "rows_by_market": backfill_summary.get("rows_by_market")
        or verify_summary.get("kis_sidecar_by_market")
        or {},
        "no_dummy_data": bool(backfill_summary.get("no_dummy_data") and verify_summary.get("no_dummy_data")),
        "latency_policy": "candidate-only existing-sidecar news enrichment with ticker/date de-duplication; not full-universe news calls during live scan",
    }


def _current_kis_feature_readiness(
    *,
    fallback_readiness: Mapping[str, Any],
    model_comparison: Mapping[str, Any],
) -> Dict[str, Any]:
    markets = model_comparison.get("markets")
    if not isinstance(markets, dict):
        result = dict(fallback_readiness)
        result["source_report"] = "runtime_state/reports/learning/kis_augmented_challenger_readiness.json"
        return result

    by_market: Dict[str, Any] = {}
    family_rollup: Dict[str, Dict[str, Any]] = {}
    statuses: List[str] = []
    required_rows: List[Any] = []
    required_days: List[Any] = []

    for market, payload in sorted(markets.items()):
        if not isinstance(payload, dict):
            continue
        readiness = _as_dict(payload.get("source_kis_feature_readiness"))
        if not readiness:
            continue
        statuses.append(str(readiness.get("status") or "not_checked"))
        required_rows.append(readiness.get("required_rows"))
        required_days.append(readiness.get("required_days"))
        families = _as_dict(readiness.get("families"))
        by_market[market] = {
            "status": readiness.get("status"),
            "required_rows": readiness.get("required_rows"),
            "required_days": readiness.get("required_days"),
            "families": {
                family: {
                    "rows": _as_dict(value).get("rows"),
                    "outcome_label_rows": _as_dict(value).get("outcome_label_rows"),
                    "unique_days": _as_dict(value).get("unique_days"),
                    "unique_runs": _as_dict(value).get("unique_runs"),
                    "mature_for_training": _as_dict(value).get("mature_for_training"),
                }
                for family, value in families.items()
                if isinstance(value, dict)
            },
        }
        for family, value in families.items():
            if not isinstance(value, dict):
                continue
            bucket = family_rollup.setdefault(
                family,
                {
                    "rows": 0,
                    "outcome_label_rows": 0,
                    "unique_days": 0,
                    "unique_runs": 0,
                    "mature_markets": 0,
                    "checked_markets": 0,
                },
            )
            bucket["rows"] += int(value.get("rows") or 0)
            bucket["outcome_label_rows"] += int(value.get("outcome_label_rows") or 0)
            bucket["unique_days"] = max(int(bucket["unique_days"]), int(value.get("unique_days") or 0))
            bucket["unique_runs"] = max(int(bucket["unique_runs"]), int(value.get("unique_runs") or 0))
            bucket["checked_markets"] += 1
            if value.get("mature_for_training"):
                bucket["mature_markets"] += 1

    if not by_market:
        result = dict(fallback_readiness)
        result["source_report"] = "runtime_state/reports/learning/kis_augmented_challenger_readiness.json"
        return result

    for bucket in family_rollup.values():
        bucket["mature_for_training"] = bool(
            bucket.get("checked_markets") and bucket.get("mature_markets") == bucket.get("checked_markets")
        )

    numeric_required_rows = [value for value in required_rows if isinstance(value, (int, float))]
    numeric_required_days = [value for value in required_days if isinstance(value, (int, float))]
    return {
        "status": "ok" if statuses and all(status == "ok" for status in statuses) else "blocked",
        "required_rows": max(numeric_required_rows) if numeric_required_rows else fallback_readiness.get("required_rows"),
        "required_days": max(numeric_required_days) if numeric_required_days else fallback_readiness.get("required_days"),
        "families": family_rollup,
        "by_market": by_market,
        "promotion_rule": fallback_readiness.get("promotion_rule")
        or "KIS feature sets only train on rows with real KIS payload; no dummy or missing-only KIS rows are used.",
        "source_report": "runtime_state/reports/learning/kis_model_market_comparison.json",
    }


def build_report(report_dir: Path = REPORT_DIR, learning_dir: Path = LEARNING_REPORT_DIR) -> Dict[str, Any]:
    from modules.kis_operational_adapter import KIS_OPERATIONAL_CONTRACT_VERSION, kis_replacement_roadmap

    readiness = _read_json(report_dir / "kis_operational_readiness.json")
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    quote_coverage = readiness.get("quote_coverage") if isinstance(readiness.get("quote_coverage"), dict) else {}
    endpoint_rollup = readiness.get("endpoint_rollup") if isinstance(readiness.get("endpoint_rollup"), dict) else {}
    kis_challenger = _read_json(learning_dir / "kis_augmented_challenger_readiness.json")
    theme_news_backfill = _read_json(learning_dir / "kis_theme_news_emitted_news_backfill.json")
    theme_news_verify = _read_json(learning_dir / "kis_theme_news_emitted_news_backfill_verify.json")
    model_comparison = _read_json(learning_dir / "kis_model_market_comparison.json")
    kis_feature_readiness = (
        kis_challenger.get("kis_feature_readiness")
        if isinstance(kis_challenger.get("kis_feature_readiness"), dict)
        else {}
    )
    kis_feature_readiness = _current_kis_feature_readiness(
        fallback_readiness=kis_feature_readiness,
        model_comparison=model_comparison,
    )
    kis_families = kis_feature_readiness.get("families") if isinstance(kis_feature_readiness.get("families"), dict) else {}
    roadmap = kis_replacement_roadmap()
    theme_news_status = _theme_news_backfill_status(
        backfill_report=theme_news_backfill,
        verify_report=theme_news_verify,
    )
    market_reflections = _compact_market_reflections(model_comparison)

    gates: List[Dict[str, Any]] = [
        {
            "gate": "source_contract",
            "target": "KIS payloads map to existing OHLCV, quote, and whale-flow fields",
            "current_status": "implemented_and_unit_tested",
            "promotion_required": False,
        },
        {
            "gate": "quote_universe",
            "target": "100% effective KR quote coverage with retry/cache",
            "current_status": {
                "effective_quote_success_rate_pct": quote_coverage.get("total_effective_quote_success_rate_pct"),
                "source": "prior live KIS readiness sweep",
            },
            "promotion_required": True,
        },
        {
            "gate": "ohlcv_history",
            "target": ">=99% KOSPI/KOSDAQ daily OHLCV availability for scanner candidates and archive replay",
            "current_status": "adapter_added; live dual-run not complete",
            "promotion_required": True,
        },
        {
            "gate": "intraday_bars",
            "target": "same-day minute bars support intraday refresh without stale yfinance dependency",
            "current_status": "adapter_added; production replay not complete",
            "promotion_required": True,
        },
        {
            "gate": "investor_flow",
            "target": "KIS stock investor flow works after the exchange time gate and falls back explicitly when unavailable",
            "current_status": "KIS-first toggle added; prior live check saw time-gated failures",
            "promotion_required": True,
        },
        {
            "gate": "rank_vi_news_financial",
            "target": "rank membership, VI status, news-title count, and financial ratios persist as model sidecar fields",
            "current_status": {
                "status": "KIS operational prefilter rank/VI/quote/flow payload is archived per run; emitted candidate theme/news evidence is backfilled from real KIS news-title API results",
                "emitted_theme_news_rows": theme_news_status.get("evidence_rows"),
                "emitted_news_checked_rows": theme_news_status.get("news_checked_rows"),
                "emitted_kis_backed_rows": theme_news_status.get("kis_backed_rows"),
                "emitted_strength_levels": theme_news_status.get("strength_levels"),
                "kis_news_api_calls": theme_news_status.get("kis_news_api_calls"),
                "no_dummy_data": theme_news_status.get("no_dummy_data"),
                "latency_policy": theme_news_status.get("latency_policy"),
            },
            "promotion_required": True,
        },
        {
            "gate": "consumer_parity",
            "target": "scanner, Discord, archive, top-deep, Supabase, and learning outputs consume the same normalized contract",
            "current_status": "daily KR autoscan defaults to KIS operational primary with explicit legacy fallback; Supabase compatibility was verified on live KIS rows; Top Deep now records KIS source timing when sidecar evidence is present",
            "promotion_required": True,
        },
        {
            "gate": "candidate_only_deep_analysis",
            "target": "Deep analysis runs only on emitted Top/Admission/Exception candidates, never on the whole raw universe",
            "current_status": "implemented_and_unit_tested",
            "promotion_required": False,
        },
        {
            "gate": "deep_analysis_source_timing",
            "target": "scan_as_of and deep_analysis_as_of are stored separately with price/flow/news source snapshots",
            "current_status": "implemented_and_unit_tested",
            "promotion_required": False,
        },
        {
            "gate": "nightly_full_universe_validation",
            "target": "Full-universe KIS validation is checkpointed per item and remains a validation lane, not the operational scan path",
            "current_status": "implemented_and_unit_tested",
            "promotion_required": False,
        },
        {
            "gate": "model_lift",
            "target": "KIS-augmented challenger beats current segment gates without worse tail loss",
            "current_status": {
                "readiness_status": kis_feature_readiness.get("status") or "not_checked",
                "required_rows": kis_feature_readiness.get("required_rows"),
                "required_days": kis_feature_readiness.get("required_days"),
                "sidecar_rows": (kis_families.get("sidecar") or {}).get("rows"),
                "sidecar_outcome_label_rows": (kis_families.get("sidecar") or {}).get("outcome_label_rows"),
                "prefilter_rows": (kis_families.get("prefilter") or {}).get("rows"),
                "prefilter_outcome_label_rows": (kis_families.get("prefilter") or {}).get("outcome_label_rows"),
                "theme_news_rows": (kis_families.get("theme_news") or {}).get("rows"),
                "theme_news_outcome_label_rows": (kis_families.get("theme_news") or {}).get("outcome_label_rows"),
                "challenger_report": kis_feature_readiness.get("source_report")
                or "runtime_state/reports/learning/kis_augmented_challenger_readiness.json",
            },
            "promotion_required": True,
        },
    ]

    return {
        "tool": "report_kis_replacement_roadmap",
        "contract_version": KIS_OPERATIONAL_CONTRACT_VERSION,
        "summary": {
            "operator_answer": "KIS can stay as the KR daily operational source path with legacy fallback. KIS model candidates must remain in the top Shadow/Risk Review lane until the market-specific promotion gates pass, and final production replacement must report existing Top1/Top3/Top5 versus KIS metrics side by side.",
            "source_only_change": "The promotion changes the daily operational execution path, archives KIS prefilter/sidecar/theme-news features, and exposes those real KIS fields to challenger training with maturity gates; scanner/planner scoring contracts remain compatible.",
            "current_replacement_level": "production-primary source default with legacy fallback; KIS model promotion remains shadow/risk-review",
            "prior_readiness_verdict": summary.get("operational_replacement_verdict"),
            "endpoint_ok_count": endpoint_rollup.get("ok_count"),
            "endpoint_failed_count": endpoint_rollup.get("failed_count"),
            "kis_model_readiness_status": kis_feature_readiness.get("status"),
            "emitted_theme_news_backfill_rows": theme_news_status.get("evidence_rows"),
            "emitted_theme_news_news_checked_rows": theme_news_status.get("news_checked_rows"),
            "emitted_theme_news_no_dummy_data": theme_news_status.get("no_dummy_data"),
            "model_comparison_report": "runtime_state/reports/learning/kis_model_market_comparison.json",
        },
        "implemented_now": {
            "market_data_toggle": "AG_KR_MARKET_DATA_PROVIDER=kis_first or kis_only",
            "investor_flow_toggle": "AG_KR_INVESTOR_FLOW_PROVIDER=kis_first or kis_only",
            "scanner_sidecar_toggle": "AG_ENABLE_KIS_SIDECAR=1",
            "sidecar_adapter": "modules.kis_operational_adapter",
            "top_deep_kis_source_timing": "scan_as_of/deep_analysis_as_of/source_timing persisted in scan_deep_reports",
            "kis_challenger_feature_pipeline": "scan_universe_snapshots.feature_snapshot KIS sidecar/prefilter payload is flattened into KIS-only and KIS-augmented challenger feature sets",
            "kis_challenger_maturity_gate": "KIS feature sets train only on real KIS payload rows and require configured rows/days; no dummy rows are accepted",
            "candidate_only_deep_analysis": "Top Deep consumes scan_universe_admission + Exception Leader candidates, not all tickers",
            "daily_scan_engine_default": "AG_KR_DAILY_SCAN_ENGINE=kis_operational",
            "production_default_changed": True,
            "legacy_fallback_preserved": True,
            "legacy_fallback_toggle": "AG_KR_DAILY_LEGACY_FALLBACK=1",
        },
        "replacement_gates": gates,
        "roadmap": roadmap,
        "model_upgrade_plan": [
            {
                "step": "sidecar_persistence",
                "action": "Persist KIS quote, OHLCV summary, flow, rank, VI, news-title, and financial fields next to KR scanner rows.",
                "success_metric": "No recommendation order change; complete KIS sidecar for eligible KR candidates.",
            },
            {
                "step": "source_timing_contract",
                "action": "Separate scan snapshot time from Top Deep generation time and record source snapshots for price, flow, and news.",
                "success_metric": "Every Top Deep row explains whether KIS sidecar, scan proxy, or fallback fetch supplied each field.",
            },
            {
                "step": "dual_run_quality_report",
                "action": "Compare KIS-first and legacy outputs for scanner rows, archive rows, Discord lookup, and top-deep reports.",
                "success_metric": "No silent missing-field drift; all consumer payloads carry source warnings.",
            },
            {
                "step": "challenger_training",
                "action": "Run KIS sidecar-only, prefilter-only, sidecar-augmented, prefilter-augmented, and full KIS-augmented challengers after the maturity gate passes.",
                "success_metric": "Segment Top5 positive-rate, average 5D return, bad-path rate, and stop-first rate improve on real resolved KIS rows.",
            },
            {
                "step": "promotion",
                "action": "Promote KIS primary with explicit fallback after gates pass.",
                "success_metric": "Production KR scanner uses KIS primary without lowering current release gates.",
            },
        ],
        "scan_logic_maximization_plan": [
            {
                "layer": "prefilter",
                "action": "Use KIS rank, quote activity, VI, trade value, and flow availability to bound the candidate universe before expensive scanner work.",
                "guardrail": "Prefilter must store selected and rejected evidence; no dummy rows and no silent empty candidate success.",
            },
            {
                "layer": "admission",
                "action": "Score only KIS-prefiltered candidates with current scan_universe_admission lanes, preserving Top5/Exception/Shadow section traces.",
                "guardrail": "Promotion requires live outcome gates by market/section/horizon, including bad-path and stop-first risk.",
            },
            {
                "layer": "deep_analysis",
                "action": "Use KIS sidecar as the primary Top Deep evidence source and keep fallback sources visible in source_timing.",
                "guardrail": "scan_as_of and deep_analysis_as_of must differ when data is refreshed after scan time.",
            },
            {
                "layer": "learning",
                "action": "Use flattened KIS sidecar and prefilter features in explicit feature-group ablations.",
                "guardrail": "Only train/promote a KIS-augmented challenger on real KIS payload rows with enough resolved outcomes; no dummy or missing-only KIS rows.",
            },
            {
                "layer": "operations",
                "action": "Keep operational scan KIS-prefiltered and reserve 3-way full-universe KIS scans for checkpointed nightly validation.",
                "guardrail": "Full-universe validation failure cannot block candidate-only operational persistence unless source contract gates fail.",
            },
        ],
        "final_operational_reflection_plan": {
            "performance_report": {
                "source": "runtime_state/reports/learning/kis_model_market_comparison.json",
                "metric_contract": model_comparison.get("metric_contract")
                or "2d excluded; use completed 1d/3d/5d outcome labels",
                "required_markets": ["KOSPI", "KOSDAQ"],
                "comparison_contract": "For each market, show existing production Top1/Top3/Top5 versus the current KIS challenger on n, active_days, active_runs, win_1d/3d/5d, avg_1d/3d/5d, min_1d/5d, max_5d, min_low_5d, bad_path, and promotion-gate blockers.",
                "current_market_reflections": market_reflections,
            },
            "ui_report": {
                "web": [
                    "Place KIS Shadow candidates above the normal result sections, with gate status, production_ready, risk_review_required, and blocking reasons visible.",
                    "Keep production_ready=false candidates labeled as Shadow/Risk Review, not as final buy candidates.",
                    "Show existing Top1/Top3/Top5 versus KIS challenger delta in the same market/run context before any promotion decision.",
                ],
                "top_deep": [
                    "Show KIS theme/news summary, evidence score/level, kis_backed, news_checked, and source_timing for each candidate.",
                    "Display coverage warnings when theme/news evidence is missing or not mature for training.",
                ],
                "discord": [
                    "Include the same KIS gate, Shadow/Risk Review status, and theme/news summary in scan-result and precision-analysis messages.",
                    "Avoid promotion wording in Discord until the same gate used by the web UI passes.",
                ],
                "promotion_guard": [
                    "Production switch requires both markets to have completed comparison reports and no hidden missing-field drift across web, archive, Top Deep, Discord, and Supabase rows.",
                    "KIS model promotion remains blocked when tail-risk gates fail even if average return delta is positive.",
                ],
            },
            "theme_news_backfill": theme_news_status,
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    implemented = report.get("implemented_now") if isinstance(report.get("implemented_now"), dict) else {}
    gates = report.get("replacement_gates") if isinstance(report.get("replacement_gates"), list) else []
    model_plan = report.get("model_upgrade_plan") if isinstance(report.get("model_upgrade_plan"), list) else []
    scan_plan = report.get("scan_logic_maximization_plan") if isinstance(report.get("scan_logic_maximization_plan"), list) else []
    reflection = (
        report.get("final_operational_reflection_plan")
        if isinstance(report.get("final_operational_reflection_plan"), dict)
        else {}
    )
    performance_report = (
        reflection.get("performance_report") if isinstance(reflection.get("performance_report"), dict) else {}
    )
    ui_report = reflection.get("ui_report") if isinstance(reflection.get("ui_report"), dict) else {}
    theme_news_backfill = (
        reflection.get("theme_news_backfill") if isinstance(reflection.get("theme_news_backfill"), dict) else {}
    )

    lines = [
        "# KIS Replacement Roadmap",
        "",
        "## Summary",
        f"- operator_answer: {summary.get('operator_answer')}",
        f"- current_replacement_level: {summary.get('current_replacement_level')}",
        f"- source_only_change: {summary.get('source_only_change')}",
        f"- endpoint_ok_count: {summary.get('endpoint_ok_count')}",
        f"- endpoint_failed_count: {summary.get('endpoint_failed_count')}",
        f"- emitted_theme_news_backfill_rows: {summary.get('emitted_theme_news_backfill_rows')}",
        f"- emitted_theme_news_news_checked_rows: {summary.get('emitted_theme_news_news_checked_rows')}",
        f"- emitted_theme_news_no_dummy_data: {summary.get('emitted_theme_news_no_dummy_data')}",
        f"- model_comparison_report: {summary.get('model_comparison_report')}",
        "",
        "## Implemented Now",
    ]
    for key, value in implemented.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 100 Percent Replacement Gates",
            "| Gate | Target | Current Status |",
            "|---|---|---|",
        ]
    )
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        status = gate.get("current_status")
        if isinstance(status, dict):
            status = json.dumps(status, ensure_ascii=False, sort_keys=True)
        lines.append(f"| {gate.get('gate')} | {gate.get('target')} | {status} |")

    lines.extend(["", "## Model Upgrade Plan"])
    for item in model_plan:
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('step')}: {item.get('action')} Success: {item.get('success_metric')}")
    lines.extend(["", "## Scan Logic Maximization Plan"])
    for item in scan_plan:
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('layer')}: {item.get('action')} Guardrail: {item.get('guardrail')}")

    lines.extend(
        [
            "",
            "## Final Operational Reflection Plan",
            f"- performance_source: {performance_report.get('source')}",
            f"- metric_contract: {performance_report.get('metric_contract')}",
            f"- comparison_contract: {performance_report.get('comparison_contract')}",
            "",
            "### Current KIS Market Reflection",
            "| Market | Action | Gate | Production Ready | n | Active Days | Win 5D | Avg 5D | Min Low 5D |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    market_reflections = performance_report.get("current_market_reflections")
    if isinstance(market_reflections, dict):
        for market, payload in sorted(market_reflections.items()):
            if not isinstance(payload, dict):
                continue
            metrics = payload.get("current_metrics") if isinstance(payload.get("current_metrics"), dict) else {}
            gate = payload.get("gate") if isinstance(payload.get("gate"), dict) else {}
            lines.append(
                "| "
                f"{market} | {payload.get('operational_action')} | {gate.get('status')} | "
                f"{gate.get('production_ready')} | {metrics.get('n')} | {metrics.get('active_days')} | "
                f"{metrics.get('win_5d_pct')} | {metrics.get('avg_5d_pct')} | {metrics.get('min_min_low_5d_pct')} |"
            )

    lines.extend(
        [
            "",
            "### Theme News Backfill",
            f"- source_backfill_report: {theme_news_backfill.get('source_backfill_report')}",
            f"- source_verify_report: {theme_news_backfill.get('source_verify_report')}",
            f"- rows_written: {theme_news_backfill.get('rows_written')}",
            f"- evidence_rows: {theme_news_backfill.get('evidence_rows')}",
            f"- news_checked_rows: {theme_news_backfill.get('news_checked_rows')}",
            f"- kis_news_api_calls: {theme_news_backfill.get('kis_news_api_calls')}",
            f"- strength_levels: {json.dumps(theme_news_backfill.get('strength_levels') or {}, ensure_ascii=False, sort_keys=True)}",
            f"- no_dummy_data: {theme_news_backfill.get('no_dummy_data')}",
            f"- latency_policy: {theme_news_backfill.get('latency_policy')}",
            "",
            "### UI Required Changes",
        ]
    )
    for surface in ("web", "top_deep", "discord", "promotion_guard"):
        items = ui_report.get(surface) if isinstance(ui_report.get(surface), list) else []
        for item in items:
            lines.append(f"- {surface}: {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "kis_replacement_roadmap.json"
    md_path = REPORT_DIR / "kis_replacement_roadmap.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
