#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kosdaq_3d_continuation_ranker import predict_continuation_overlay
from multi_agent.agents.kr_quant_reranker import is_kosdaq_3d_continuation_eligible
from multi_agent.tools.report_kr_top_mover_capture import _bootstrap_ci, _load_archive


def _daily_metric_report(df, rank_col: str, topn: int, confidence: float, bootstrap_iters: int) -> Dict[str, Any]:
    rows_1d: List[float] = []
    rows_3d: List[float] = []
    pos_1d: List[float] = []
    pos_3d: List[float] = []
    days = 0

    for _, day_df in df.groupby("trade_date", dropna=False):
        ordered = day_df.sort_values([rank_col, "priority_rank"], ascending=[False, True], na_position="last").head(topn)
        if ordered.empty:
            continue
        days += 1
        r1 = ordered["return_1d_pct"].dropna().astype(float)
        r3 = ordered["return_3d_pct"].dropna().astype(float)
        if not r1.empty:
            rows_1d.append(float(r1.mean()))
            pos_1d.append(float(r1.gt(0).mean()))
        if not r3.empty:
            rows_3d.append(float(r3.mean()))
            pos_3d.append(float(r3.gt(0).mean()))

    return {
        "topn": int(topn),
        "days": int(days),
        "avg_1d_return_pct": _bootstrap_ci(rows_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 11 + 7),
        "avg_3d_return_pct": _bootstrap_ci(rows_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 13 + 7),
        "positive_1d": _bootstrap_ci(pos_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 17 + 7),
        "positive_3d": _bootstrap_ci(pos_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 19 + 7),
    }


def _delta_report(base: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, float]:
    return {
        "avg_1d_return_pct": round(float(model["avg_1d_return_pct"]["mean"]) - float(base["avg_1d_return_pct"]["mean"]), 6),
        "avg_3d_return_pct": round(float(model["avg_3d_return_pct"]["mean"]) - float(base["avg_3d_return_pct"]["mean"]), 6),
        "positive_1d": round(float(model["positive_1d"]["mean"]) - float(base["positive_1d"]["mean"]), 6),
        "positive_3d": round(float(model["positive_3d"]["mean"]) - float(base["positive_3d"]["mean"]), 6),
    }


def build_report(df, confidence: float, topn_values: List[int], bootstrap_iters: int) -> Dict[str, Any]:
    work = df.copy()
    work = work[work["market_type"].fillna("").astype(str).eq("KR")].copy()
    work = work[work["ticker"].fillna("").astype(str).str.endswith(".KQ")].copy()

    eligible_rows: List[Dict[str, Any]] = []
    for _, row in work.iterrows():
        payload = row.to_dict()
        gate = is_kosdaq_3d_continuation_eligible(payload)
        if not gate.get("eligible", False):
            continue
        overlay = predict_continuation_overlay(
            decision_score=payload.get("decision_score"),
            alpha_score=payload.get("alpha_score"),
            ml_prob=payload.get("ml_prob"),
            trend=payload.get("trend"),
        )
        eligible_rows.append(
            {
                **payload,
                "continuation_prob_3d": float(overlay.get("prob_up_3d", 50.0) or 50.0),
                "continuation_enabled": bool(overlay.get("enabled", False)),
            }
        )

    eligible_df = pd.DataFrame(eligible_rows)

    comparisons: List[Dict[str, Any]] = []
    for topn in topn_values:
        baseline = _daily_metric_report(eligible_df, "decision_score", topn, confidence, bootstrap_iters)
        model = _daily_metric_report(eligible_df, "continuation_prob_3d", topn, confidence, bootstrap_iters)
        comparisons.append(
            {
                "topn": int(topn),
                "baseline": baseline,
                "model": model,
                "delta": _delta_report(baseline, model),
            }
        )

    per_day = eligible_df.groupby("trade_date", dropna=False).size() if not eligible_df.empty else []
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": "KOSDAQ",
        "confidence_level": float(confidence),
        "eligible_rows": int(len(eligible_df)),
        "eligible_days": int(eligible_df["trade_date"].astype(str).replace("nan", "").replace("", None).dropna().nunique()) if not eligible_df.empty else 0,
        "avg_candidates_per_day": round(float(per_day.mean()), 3) if len(per_day) else 0.0,
        "enabled_rate": round(float(eligible_df["continuation_enabled"].mean()), 6) if not eligible_df.empty else 0.0,
        "comparisons": comparisons,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    def pct(v: float) -> str:
        return f"{float(v) * 100.0:.2f}%"

    lines = [
        "# KOSDAQ 3D Continuation Validation",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- eligible_rows: {report['eligible_rows']}",
        f"- eligible_days: {report['eligible_days']}",
        f"- avg_candidates_per_day: {report['avg_candidates_per_day']}",
        f"- enabled_rate: {pct(report['enabled_rate'])}",
        "",
    ]
    for row in report["comparisons"]:
        base = row["baseline"]
        model = row["model"]
        delta = row["delta"]
        lines.extend(
            [
                f"## Top {row['topn']}",
                f"- avg 1D: baseline {base['avg_1d_return_pct']['mean']:+.2f}% -> model {model['avg_1d_return_pct']['mean']:+.2f}% (delta {delta['avg_1d_return_pct']:+.2f}%)",
                f"- avg 3D: baseline {base['avg_3d_return_pct']['mean']:+.2f}% -> model {model['avg_3d_return_pct']['mean']:+.2f}% (delta {delta['avg_3d_return_pct']:+.2f}%)",
                f"- positive 1D: baseline {pct(base['positive_1d']['mean'])} -> model {pct(model['positive_1d']['mean'])} (delta {pct(delta['positive_1d'])})",
                f"- positive 3D: baseline {pct(base['positive_3d']['mean'])} -> model {pct(model['positive_3d']['mean'])} (delta {pct(delta['positive_3d'])})",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate KOSDAQ 3D continuation eligible universe and model ranking.")
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--topn", default="3,5")
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    input_path = Path(args.input_dir) / "scan_archive_learning_dataset_kosdaq.csv"
    df = _load_archive(input_path)
    report = build_report(
        df=df,
        confidence=float(args.confidence),
        topn_values=[int(x) for x in str(args.topn).split(",") if str(x).strip()],
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "kosdaq_3d_continuation_validation.json"
    md_path = out_dir / "kosdaq_3d_continuation_validation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "eligible_rows": report["eligible_rows"], "eligible_days": report["eligible_days"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
