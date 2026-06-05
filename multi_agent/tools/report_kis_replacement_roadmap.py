#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_report(report_dir: Path = REPORT_DIR) -> Dict[str, Any]:
    from modules.kis_operational_adapter import KIS_OPERATIONAL_CONTRACT_VERSION, kis_replacement_roadmap

    readiness = _read_json(report_dir / "kis_operational_readiness.json")
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    quote_coverage = readiness.get("quote_coverage") if isinstance(readiness.get("quote_coverage"), dict) else {}
    endpoint_rollup = readiness.get("endpoint_rollup") if isinstance(readiness.get("endpoint_rollup"), dict) else {}
    kis_challenger = _read_json(PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "kis_augmented_challenger_readiness.json")
    kis_feature_readiness = (
        kis_challenger.get("kis_feature_readiness")
        if isinstance(kis_challenger.get("kis_feature_readiness"), dict)
        else {}
    )
    kis_families = kis_feature_readiness.get("families") if isinstance(kis_feature_readiness.get("families"), dict) else {}
    roadmap = kis_replacement_roadmap()

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
            "current_status": "KIS operational prefilter rank/VI/quote/flow payload is archived per run; news enrichment remains opt-in because of latency budget",
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
                "challenger_report": "runtime_state/reports/learning/kis_augmented_challenger_readiness.json",
            },
            "promotion_required": True,
        },
    ]

    return {
        "tool": "report_kis_replacement_roadmap",
        "contract_version": KIS_OPERATIONAL_CONTRACT_VERSION,
        "summary": {
            "operator_answer": "KIS is now the default KR daily operational scan source with a legacy scanner fallback. Controlled production replacement is acceptable for the source path, but KIS-augmented model promotion remains blocked until real KIS sidecar/prefilter rows have enough resolved outcomes.",
            "source_only_change": "The promotion changes the daily operational execution path, archives KIS prefilter/sidecar features, and now exposes those features to challenger training with maturity gates; scanner/planner scoring contracts remain compatible.",
            "current_replacement_level": "production-primary default with legacy fallback; model lift pending",
            "prior_readiness_verdict": summary.get("operational_replacement_verdict"),
            "endpoint_ok_count": endpoint_rollup.get("ok_count"),
            "endpoint_failed_count": endpoint_rollup.get("failed_count"),
            "kis_model_readiness_status": kis_feature_readiness.get("status"),
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
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    implemented = report.get("implemented_now") if isinstance(report.get("implemented_now"), dict) else {}
    gates = report.get("replacement_gates") if isinstance(report.get("replacement_gates"), list) else []
    model_plan = report.get("model_upgrade_plan") if isinstance(report.get("model_upgrade_plan"), list) else []
    scan_plan = report.get("scan_logic_maximization_plan") if isinstance(report.get("scan_logic_maximization_plan"), list) else []

    lines = [
        "# KIS Replacement Roadmap",
        "",
        "## Summary",
        f"- operator_answer: {summary.get('operator_answer')}",
        f"- current_replacement_level: {summary.get('current_replacement_level')}",
        f"- source_only_change: {summary.get('source_only_change')}",
        f"- endpoint_ok_count: {summary.get('endpoint_ok_count')}",
        f"- endpoint_failed_count: {summary.get('endpoint_failed_count')}",
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
