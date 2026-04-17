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

from multi_agent.tools.report_kr_explosive_leader_validation import build_report as build_validation_report
from multi_agent.tools.report_kr_top_mover_capture import _load_archive


GATE_CONFIG: Dict[str, Dict[str, float]] = {
    "KOSPI": {
        "topn": 20,
        "min_rows": 200,
        "min_days": 5,
        "min_delta_avg_1d": 0.0,
        "min_delta_positive_1d": 0.0,
        "min_delta_hit10": 0.0,
        "min_avg_1d_lower": 0.0,
        "min_avg_3d_mean": 0.0,
    },
    "KOSDAQ": {
        "topn": 20,
        "min_rows": 400,
        "min_days": 5,
        "min_delta_avg_1d": 0.0,
        "min_delta_positive_1d": 0.0,
        "min_delta_hit10": 0.0,
        "min_avg_1d_lower": 0.0,
        "min_avg_3d_mean": 0.0,
    },
}


def _check(condition: bool, code: str, detail: str) -> Dict[str, Any]:
    return {"code": code, "passed": bool(condition), "detail": detail}


def _find_topn(rows: List[Dict[str, Any]], topn: int) -> Dict[str, Any]:
    for row in rows:
        if int(row.get("topn", 0) or 0) == int(topn):
            return row
    return {}


def build_release_gate(df, market: str, confidence: float, bootstrap_iters: int) -> Dict[str, Any]:
    market = str(market).upper()
    config = GATE_CONFIG[market]
    validation = build_validation_report(
        df=df,
        market=market,
        confidence=confidence,
        topn_values=[5, 10, int(config["topn"])],
        bootstrap_iters=bootstrap_iters,
    )
    focus = _find_topn(validation.get("comparisons", []), int(config["topn"]))
    eligible = focus.get("eligible", {})
    delta = focus.get("delta", {})

    checks = [
        _check(
            int(validation.get("eligible_rows", 0) or 0) >= int(config["min_rows"]),
            "ELIGIBLE_ROWS_MIN",
            f"eligible_rows={int(validation.get('eligible_rows', 0) or 0)}",
        ),
        _check(
            int(validation.get("eligible_days", 0) or 0) >= int(config["min_days"]),
            "ELIGIBLE_DAYS_MIN",
            f"eligible_days={int(validation.get('eligible_days', 0) or 0)}",
        ),
        _check(
            float(delta.get("avg_1d_return_pct", 0.0) or 0.0) >= float(config["min_delta_avg_1d"]),
            "DELTA_AVG_1D_NON_NEGATIVE",
            f"delta_avg_1d={float(delta.get('avg_1d_return_pct', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(delta.get("positive_1d", 0.0) or 0.0) >= float(config["min_delta_positive_1d"]),
            "DELTA_POSITIVE_1D_NON_NEGATIVE",
            f"delta_positive_1d={float(delta.get('positive_1d', 0.0) or 0.0) * 100.0:+.2f}%p",
        ),
        _check(
            float(delta.get("precision_hit_10pct", 0.0) or 0.0) >= float(config["min_delta_hit10"]),
            "DELTA_HIT10_NON_NEGATIVE",
            f"delta_hit10={float(delta.get('precision_hit_10pct', 0.0) or 0.0) * 100.0:+.2f}%p",
        ),
        _check(
            float(eligible.get("avg_1d_return_pct", {}).get("lower", 0.0) or 0.0) > float(config["min_avg_1d_lower"]),
            "AVG_1D_LOWER_POSITIVE",
            f"eligible_avg_1d_lower={float(eligible.get('avg_1d_return_pct', {}).get('lower', 0.0) or 0.0):+.2f}%",
        ),
        _check(
            float(eligible.get("avg_3d_return_pct", {}).get("mean", 0.0) or 0.0) >= float(config["min_avg_3d_mean"]),
            "AVG_3D_MEAN_NON_NEGATIVE",
            f"eligible_avg_3d_mean={float(eligible.get('avg_3d_return_pct', {}).get('mean', 0.0) or 0.0):+.2f}%",
        ),
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "confidence_level": float(confidence),
        "score_floor": int(validation.get("score_floor", 0) or 0),
        "focus_topn": int(config["topn"]),
        "release_ready": all(item["passed"] for item in checks),
        "checks": checks,
        "summary": {
            "rows": int(validation.get("rows", 0) or 0),
            "eligible_rows": int(validation.get("eligible_rows", 0) or 0),
            "eligible_days": int(validation.get("eligible_days", 0) or 0),
            "eligible_rate": float(validation.get("eligible_rate", 0.0) or 0.0),
            "delta_avg_1d_pct": float(delta.get("avg_1d_return_pct", 0.0) or 0.0),
            "delta_avg_3d_pct": float(delta.get("avg_3d_return_pct", 0.0) or 0.0),
            "delta_positive_1d": float(delta.get("positive_1d", 0.0) or 0.0),
            "delta_positive_3d": float(delta.get("positive_3d", 0.0) or 0.0),
            "delta_hit10": float(delta.get("precision_hit_10pct", 0.0) or 0.0),
            "eligible_avg_1d_mean": float(eligible.get("avg_1d_return_pct", {}).get("mean", 0.0) or 0.0),
            "eligible_avg_1d_lower": float(eligible.get("avg_1d_return_pct", {}).get("lower", 0.0) or 0.0),
            "eligible_avg_3d_mean": float(eligible.get("avg_3d_return_pct", {}).get("mean", 0.0) or 0.0),
        },
    }


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# KR Explosive Release Gate ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- score_floor: {report['score_floor']}",
        f"- focus_topn: {report['focus_topn']}",
        f"- release_ready: {report['release_ready']}",
        "",
    ]
    for row in report.get("checks", []):
        lines.append(f"- [{'PASS' if row['passed'] else 'FAIL'}] {row['code']}: {row['detail']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate KR explosive leader release gate.")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    input_path = Path(args.input_dir) / f"scan_archive_learning_dataset_{str(args.market).lower()}.csv"
    df = _load_archive(input_path)
    report = build_release_gate(
        df=df,
        market=str(args.market).upper(),
        confidence=float(args.confidence),
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    market = str(args.market).lower()
    json_path = out_dir / f"kr_explosive_release_gate_{market}.json"
    md_path = out_dir / f"kr_explosive_release_gate_{market}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "release_ready": report["release_ready"],
                "focus_topn": report["focus_topn"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
