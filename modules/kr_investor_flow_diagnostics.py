from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List


PYKRX_FLOW_DIAGNOSTIC_VERSION = "pykrx_investor_flow_diagnostic_v1"


@dataclass(frozen=True)
class FlowSourceDecision:
    source: str
    role: str
    usable_for_buy_signal: bool
    required_warning: str


FLOW_SOURCE_DECISIONS = {
    "pykrx_value": FlowSourceDecision(
        source="pykrx_value",
        role="preferred_when_non_empty",
        usable_for_buy_signal=True,
        required_warning="",
    ),
    "naver": FlowSourceDecision(
        source="naver",
        role="fallback_shares_not_krw",
        usable_for_buy_signal=True,
        required_warning="NAVER_SCRAPE_FALLBACK",
    ),
    "score_only": FlowSourceDecision(
        source="score_only",
        role="insufficient_for_flow_direction",
        usable_for_buy_signal=False,
        required_warning="INVESTOR_FLOW_BREAKDOWN_MISSING",
    ),
    "unavailable": FlowSourceDecision(
        source="unavailable",
        role="block_flow_claims",
        usable_for_buy_signal=False,
        required_warning="INVESTOR_FLOW_UNAVAILABLE",
    ),
}


def classify_pykrx_warning(warnings: Iterable[str] | None) -> Dict[str, Any]:
    warning_texts = [str(item) for item in warnings or [] if str(item).strip()]
    joined = " | ".join(warning_texts).lower()
    if "pykrx_empty_investor_flow" in joined:
        return {
            "class": "empty_dataframe",
            "severity": "warning",
            "likely_causes": [
                "KRX/pykrx endpoint returned no rows for the date range or ticker",
                "holiday/non-trading date window was selected",
                "KRX throttling/session/cookie behavior changed",
                "pykrx wrapper parser no longer matches KRX response shape",
            ],
        }
    if "pykrx_zero_investor_flow" in joined:
        return {
            "class": "zero_flow",
            "severity": "warning",
            "likely_causes": [
                "endpoint returned rows but all investor sums were zero",
                "column names changed and parser mapped no investor columns",
                "ticker/date window has no valid investor trading value data",
            ],
        }
    if "pykrx_flow_failed" in joined:
        return {
            "class": "exception",
            "severity": "warning",
            "likely_causes": [
                "pykrx raised an exception",
                "network/session/parser failure",
                "KRX endpoint or pykrx version mismatch",
            ],
        }
    return {"class": "none", "severity": "ok", "likely_causes": []}


def source_decision(source: str, warnings: Iterable[str] | None = None) -> Dict[str, Any]:
    key = str(source or "").strip() or "unavailable"
    if key.startswith("live_fetch:"):
        key = key.split(":", 1)[1]
    decision = FLOW_SOURCE_DECISIONS.get(key, FLOW_SOURCE_DECISIONS["unavailable"])
    payload = asdict(decision)
    diagnostic = classify_pykrx_warning(warnings)
    if diagnostic["class"] != "none" and key == "naver":
        payload["required_warning"] = "PYKRX_FAILED_NAVER_FALLBACK"
    payload["pykrx_warning_class"] = diagnostic["class"]
    payload["pykrx_warning_severity"] = diagnostic["severity"]
    return payload


def build_pykrx_investor_flow_investigation(observed_rows: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    rows = [row for row in observed_rows or [] if isinstance(row, dict)]
    source_counts: Dict[str, int] = {}
    warning_classes: Dict[str, int] = {}
    for row in rows:
        source = str(row.get("flow_source") or row.get("source") or "unavailable")
        source_counts[source] = source_counts.get(source, 0) + 1
        diagnostic = classify_pykrx_warning(row.get("warnings") or row.get("flow_warnings"))
        warning_classes[diagnostic["class"]] = warning_classes.get(diagnostic["class"], 0) + 1

    return {
        "version": PYKRX_FLOW_DIAGNOSTIC_VERSION,
        "decision": "keep_pykrx_as_preferred_when_non_empty_but_do_not_treat_empty_as_safe",
        "observed_rows": len(rows),
        "source_counts": source_counts,
        "warning_class_counts": warning_classes,
        "source_decisions": {key: asdict(value) for key, value in FLOW_SOURCE_DECISIONS.items()},
        "required_runtime_behavior": [
            "pykrx empty/zero/exception must remain visible in warnings",
            "Naver fallback must be labelled shares, not KRW",
            "score-only rows must not claim foreigner/institution direction",
            "buyable labels should not cite investor flow as supportive when source decision is unusable",
        ],
        "recommended_next_steps": [
            "Run live pykrx smoke for 005930.KS on a trading day with latest pykrx installed",
            "Compare pykrx columns against expected institution/foreigner/retail aliases",
            "Promote KIS OpenAPI investor endpoints as primary after credentials and live quote/flow smoke pass",
            "Keep pykrx issue open only if live smoke can reproduce empty responses with trading-day date windows",
        ],
    }


def render_pykrx_investigation_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# PyKRX Investor Flow Diagnostics",
        "",
        f"- version: `{report.get('version')}`",
        f"- decision: `{report.get('decision')}`",
        f"- observed_rows: `{report.get('observed_rows', 0)}`",
        f"- source_counts: `{report.get('source_counts', {})}`",
        f"- warning_class_counts: `{report.get('warning_class_counts', {})}`",
        "",
        "## Runtime Behavior",
    ]
    for item in report.get("required_runtime_behavior") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Next Steps")
    for item in report.get("recommended_next_steps") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


__all__ = [
    "FLOW_SOURCE_DECISIONS",
    "PYKRX_FLOW_DIAGNOSTIC_VERSION",
    "build_pykrx_investor_flow_investigation",
    "classify_pykrx_warning",
    "render_pykrx_investigation_markdown",
    "source_decision",
]
