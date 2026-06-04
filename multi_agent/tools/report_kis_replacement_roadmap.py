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
            "current_status": "sidecar contract and scanner payload hook added; live rank/VI/news persistence still pending",
            "promotion_required": True,
        },
        {
            "gate": "consumer_parity",
            "target": "scanner, Discord, archive, top-deep, Supabase, and learning outputs consume the same normalized contract",
            "current_status": "not promoted to production default",
            "promotion_required": True,
        },
        {
            "gate": "model_lift",
            "target": "KIS-augmented challenger beats current segment gates without worse tail loss",
            "current_status": "needs sidecar archive and challenger training",
            "promotion_required": True,
        },
    ]

    return {
        "tool": "report_kis_replacement_roadmap",
        "contract_version": KIS_OPERATIONAL_CONTRACT_VERSION,
        "summary": {
            "operator_answer": "KIS can become the KR primary operational data source, but the current safe state is KIS-first test mode plus sidecar collection, not unconditional production default.",
            "source_only_change": "The implementation keeps scanner/planner decisions unchanged by default and changes only optional source adapters behind explicit environment toggles.",
            "current_replacement_level": "contract-ready, not production-promoted",
            "prior_readiness_verdict": summary.get("operational_replacement_verdict"),
            "endpoint_ok_count": endpoint_rollup.get("ok_count"),
            "endpoint_failed_count": endpoint_rollup.get("failed_count"),
        },
        "implemented_now": {
            "market_data_toggle": "AG_KR_MARKET_DATA_PROVIDER=kis_first or kis_only",
            "investor_flow_toggle": "AG_KR_INVESTOR_FLOW_PROVIDER=kis_first or kis_only",
            "scanner_sidecar_toggle": "AG_ENABLE_KIS_SIDECAR=1",
            "sidecar_adapter": "modules.kis_operational_adapter",
            "production_default_changed": False,
            "legacy_fallback_preserved": True,
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
                "step": "dual_run_quality_report",
                "action": "Compare KIS-first and legacy outputs for scanner rows, archive rows, Discord lookup, and top-deep reports.",
                "success_metric": "No silent missing-field drift; all consumer payloads carry source warnings.",
            },
            {
                "step": "challenger_training",
                "action": "Train KIS-augmented segment challengers with feature groups on/off.",
                "success_metric": "Segment Top5 positive-rate, average 5D return, bad-path rate, and stop-first rate improve.",
            },
            {
                "step": "promotion",
                "action": "Promote KIS primary with explicit fallback after gates pass.",
                "success_metric": "Production KR scanner uses KIS primary without lowering current release gates.",
            },
        ],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    implemented = report.get("implemented_now") if isinstance(report.get("implemented_now"), dict) else {}
    gates = report.get("replacement_gates") if isinstance(report.get("replacement_gates"), list) else []
    model_plan = report.get("model_upgrade_plan") if isinstance(report.get("model_upgrade_plan"), list) else []

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
