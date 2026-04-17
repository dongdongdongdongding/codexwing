#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.report_kr_top_mover_capture import _load_archive
from multi_agent.tools.report_kosdaq_3d_continuation_validation import build_report as build_continuation_report
from multi_agent.tools.report_kr_quant_rerank_validation import build_report as build_rerank_report


def _find_topn(rows: List[Dict[str, Any]], topn: int) -> Dict[str, Any]:
    for row in rows:
        if int(row.get("topn", 0) or 0) == int(topn):
            return row
    return {}


def _check(condition: bool, code: str, detail: str) -> Dict[str, Any]:
    return {
        "code": code,
        "passed": bool(condition),
        "detail": detail,
    }


def build_release_gate(df, confidence: float, bootstrap_iters: int) -> Dict[str, Any]:
    continuation = build_continuation_report(
        df=df,
        confidence=confidence,
        topn_values=[3, 5],
        bootstrap_iters=bootstrap_iters,
    )
    rerank = build_rerank_report(
        df=df,
        market="KOSDAQ",
        confidence=confidence,
        topn_values=[10, 20],
        bootstrap_iters=bootstrap_iters,
    )

    cont_top5 = _find_topn(continuation.get("comparisons", []), 5)
    overall_top10 = _find_topn(rerank.get("comparisons", []), 10)
    overall_top20 = _find_topn(rerank.get("comparisons", []), 20)

    top5_model = cont_top5.get("model", {})
    top5_delta = cont_top5.get("delta", {})
    top10_delta = overall_top10.get("delta", {})
    top20_delta = overall_top20.get("delta", {})

    subbasket_checks = [
        _check(
            int(continuation.get("eligible_rows", 0) or 0) >= 250,
            "ELIGIBLE_ROWS_MIN",
            f"eligible_rows={int(continuation.get('eligible_rows', 0) or 0)}",
        ),
        _check(
            int(continuation.get("eligible_days", 0) or 0) >= 5,
            "ELIGIBLE_DAYS_MIN",
            f"eligible_days={int(continuation.get('eligible_days', 0) or 0)}",
        ),
        _check(
            float(top5_delta.get("avg_3d_return_pct", 0.0) or 0.0) >= 5.0,
            "TOP5_AVG_3D_DELTA",
            f"delta_avg_3d={float(top5_delta.get('avg_3d_return_pct', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(top5_delta.get("positive_3d", 0.0) or 0.0) >= 0.25,
            "TOP5_POSITIVE_3D_DELTA",
            f"delta_positive_3d={float(top5_delta.get('positive_3d', 0.0) or 0.0) * 100.0:+.2f}%p",
        ),
        _check(
            float(top5_model.get("avg_3d_return_pct", {}).get("lower", 0.0) or 0.0) > 0.0,
            "TOP5_AVG_3D_LOWER_POSITIVE",
            f"model_avg_3d_lower={float(top5_model.get('avg_3d_return_pct', {}).get('lower', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(top5_model.get("positive_3d", {}).get("lower", 0.0) or 0.0) >= 0.50,
            "TOP5_POSITIVE_3D_LOWER_MIN",
            f"model_positive_3d_lower={float(top5_model.get('positive_3d', {}).get('lower', 0.0) or 0.0) * 100.0:.2f}%",
        ),
    ]

    primary_checks = [
        _check(
            str(rerank.get("active_lane", "") or "") == "3d",
            "ACTIVE_LANE_3D",
            f"active_lane={str(rerank.get('active_lane', '') or '')}",
        ),
        _check(
            float(top10_delta.get("avg_3d_return_pct", 0.0) or 0.0) >= 0.0,
            "TOP10_AVG_3D_NON_NEGATIVE",
            f"delta_avg_3d_top10={float(top10_delta.get('avg_3d_return_pct', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(top20_delta.get("avg_3d_return_pct", 0.0) or 0.0) >= 0.0,
            "TOP20_AVG_3D_NON_NEGATIVE",
            f"delta_avg_3d_top20={float(top20_delta.get('avg_3d_return_pct', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(top10_delta.get("positive_3d", 0.0) or 0.0) >= 0.0,
            "TOP10_POSITIVE_3D_NON_NEGATIVE",
            f"delta_positive_3d_top10={float(top10_delta.get('positive_3d', 0.0) or 0.0) * 100.0:+.2f}%p",
        ),
        _check(
            float(top20_delta.get("positive_3d", 0.0) or 0.0) >= 0.0,
            "TOP20_POSITIVE_3D_NON_NEGATIVE",
            f"delta_positive_3d_top20={float(top20_delta.get('positive_3d', 0.0) or 0.0) * 100.0:+.2f}%p",
        ),
    ]

    subbasket_ready = all(item["passed"] for item in subbasket_checks)
    primary_ready = all(item["passed"] for item in primary_checks)
    release_ready = subbasket_ready and primary_ready

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": "KOSDAQ",
        "confidence_level": float(confidence),
        "subbasket_ready": bool(subbasket_ready),
        "primary_ready": bool(primary_ready),
        "release_ready": bool(release_ready),
        "subbasket_checks": subbasket_checks,
        "primary_checks": primary_checks,
        "continuation_summary": {
            "eligible_rows": int(continuation.get("eligible_rows", 0) or 0),
            "eligible_days": int(continuation.get("eligible_days", 0) or 0),
            "enabled_rate": float(continuation.get("enabled_rate", 0.0) or 0.0),
            "top5_delta_avg_3d_pct": float(top5_delta.get("avg_3d_return_pct", 0.0) or 0.0),
            "top5_delta_positive_3d": float(top5_delta.get("positive_3d", 0.0) or 0.0),
        },
        "primary_summary": {
            "active_lane": str(rerank.get("active_lane", "") or ""),
            "top10_delta_avg_3d_pct": float(top10_delta.get("avg_3d_return_pct", 0.0) or 0.0),
            "top20_delta_avg_3d_pct": float(top20_delta.get("avg_3d_return_pct", 0.0) or 0.0),
            "top10_delta_positive_3d": float(top10_delta.get("positive_3d", 0.0) or 0.0),
            "top20_delta_positive_3d": float(top20_delta.get("positive_3d", 0.0) or 0.0),
        },
    }


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# KOSDAQ 3D Continuation Release Gate",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- subbasket_ready: {report['subbasket_ready']}",
        f"- primary_ready: {report['primary_ready']}",
        f"- release_ready: {report['release_ready']}",
        "",
        "## Continuation Sub-basket",
    ]
    for row in report.get("subbasket_checks", []):
        lines.append(f"- [{'PASS' if row['passed'] else 'FAIL'}] {row['code']}: {row['detail']}")
    lines.extend(["", "## Primary Basket",])
    for row in report.get("primary_checks", []):
        lines.append(f"- [{'PASS' if row['passed'] else 'FAIL'}] {row['code']}: {row['detail']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate KOSDAQ 3D continuation release gate.")
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    input_path = Path(args.input_dir) / "scan_archive_learning_dataset_kosdaq.csv"
    df = _load_archive(input_path)
    report = build_release_gate(df, confidence=float(args.confidence), bootstrap_iters=int(args.bootstrap_iters))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "kosdaq_3d_release_gate.json"
    md_path = out_dir / "kosdaq_3d_release_gate.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "release_ready": report["release_ready"],
                "subbasket_ready": report["subbasket_ready"],
                "primary_ready": report["primary_ready"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
