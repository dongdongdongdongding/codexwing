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

from multi_agent.agents.kr_quant_reranker import compute_kr_quant_rerank
from multi_agent.agents.kr_quant_reranker import compute_kr_basket_priority, resolve_kr_active_lane
from multi_agent.tools.report_kr_top_mover_capture import _bootstrap_ci, _load_archive


def _daily_metric_report(df, rank_col: str, topn: int, confidence: float, bootstrap_iters: int) -> Dict[str, Any]:
    rows_1d: List[float] = []
    rows_3d: List[float] = []
    pos_1d: List[float] = []
    pos_3d: List[float] = []
    avoid_1d: List[float] = []
    avoid_3d: List[float] = []
    hit10: List[float] = []
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
            avoid_1d.append(float(r1.ge(0).mean()))
        if not r3.empty:
            rows_3d.append(float(r3.mean()))
            pos_3d.append(float(r3.gt(0).mean()))
            avoid_3d.append(float(r3.ge(0).mean()))
        hit = ordered["label_hit_10pct"].fillna(0).astype(float)
        hit10.append(float(hit.mean()))

    return {
        "topn": int(topn),
        "days": int(days),
        "avg_1d_return_pct": _bootstrap_ci(rows_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 11 + 1),
        "avg_3d_return_pct": _bootstrap_ci(rows_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 13 + 1),
        "positive_1d": _bootstrap_ci(pos_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 17 + 1),
        "positive_3d": _bootstrap_ci(pos_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 19 + 1),
        "avoid_down_1d": _bootstrap_ci(avoid_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 23 + 1),
        "avoid_down_3d": _bootstrap_ci(avoid_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 29 + 1),
        "precision_hit_10pct": _bootstrap_ci(hit10, confidence=confidence, iterations=bootstrap_iters, seed=topn * 31 + 1),
    }


def _delta_report(base: Dict[str, Any], quant: Dict[str, Any]) -> Dict[str, float]:
    keys = [
        "avg_1d_return_pct",
        "avg_3d_return_pct",
        "positive_1d",
        "positive_3d",
        "avoid_down_1d",
        "avoid_down_3d",
        "precision_hit_10pct",
    ]
    out: Dict[str, float] = {}
    for key in keys:
        out[key] = round(float(quant[key]["mean"]) - float(base[key]["mean"]), 6)
    return out


def build_report(df, market: str, confidence: float, topn_values: List[int], bootstrap_iters: int) -> Dict[str, Any]:
    work = df.copy()
    work["decision_score"] = work["decision_score"].fillna(0.0)
    quant_rows: List[Dict[str, Any]] = []
    for _, row in work.iterrows():
        payload = row.to_dict()
        meta = compute_kr_quant_rerank(payload, market.upper())
        quant_rows.append({"row": payload, "_quant_rerank": meta})
    active_lane = resolve_kr_active_lane(quant_rows, market.upper())
    basket_scores: List[float] = []
    for item in quant_rows:
        basket = compute_kr_basket_priority(item, market.upper(), active_lane)
        basket_scores.append(float(basket.get("score", 0.0) or 0.0))
    work["quant_rerank_score"] = basket_scores
    work["quant_rerank_score_1d"] = [float(item["_quant_rerank"].get("score_1d", item["_quant_rerank"].get("score", 0.0)) or 0.0) for item in quant_rows]
    work["quant_rerank_score_3d"] = [float(item["_quant_rerank"].get("score_3d", item["_quant_rerank"].get("score", 0.0)) or 0.0) for item in quant_rows]

    comparisons: List[Dict[str, Any]] = []
    for topn in topn_values:
        base = _daily_metric_report(work, "decision_score", topn, confidence, bootstrap_iters)
        quant = _daily_metric_report(work, "quant_rerank_score", topn, confidence, bootstrap_iters)
        quant_1d = _daily_metric_report(work, "quant_rerank_score_1d", topn, confidence, bootstrap_iters)
        quant_3d = _daily_metric_report(work, "quant_rerank_score_3d", topn, confidence, bootstrap_iters)
        comparisons.append(
            {
                "topn": int(topn),
                "baseline": base,
                "quant_rerank": quant,
                "quant_rerank_1d": quant_1d,
                "quant_rerank_3d": quant_3d,
                "delta": _delta_report(base, quant),
                "delta_1d_lane": _delta_report(base, quant_1d),
                "delta_3d_lane": _delta_report(base, quant_3d),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market.upper(),
        "confidence_level": float(confidence),
        "rows": int(len(work)),
        "days": int(work["trade_date"].astype(str).replace("nan", "").replace("", None).dropna().nunique()),
        "active_lane": active_lane,
        "comparisons": comparisons,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    def pct(v: float) -> str:
        return f"{float(v) * 100.0:.2f}%"

    lines = [
        f"# KRX Quant Rerank Validation ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- rows: {report['rows']}",
        f"- days: {report['days']}",
        f"- active_lane: {report['active_lane']}",
        "",
    ]
    for row in report["comparisons"]:
        base = row["baseline"]
        quant = row["quant_rerank"]
        delta = row["delta"]
        lines.extend(
            [
                f"## Top {row['topn']}",
                f"- primary lane avg 1D: baseline {base['avg_1d_return_pct']['mean']:+.2f}% -> quant {quant['avg_1d_return_pct']['mean']:+.2f}% (delta {delta['avg_1d_return_pct']:+.2f}%)",
                f"- primary lane avg 3D: baseline {base['avg_3d_return_pct']['mean']:+.2f}% -> quant {quant['avg_3d_return_pct']['mean']:+.2f}% (delta {delta['avg_3d_return_pct']:+.2f}%)",
                f"- primary lane positive 1D: baseline {pct(base['positive_1d']['mean'])} -> quant {pct(quant['positive_1d']['mean'])} (delta {pct(delta['positive_1d'])})",
                f"- primary lane positive 3D: baseline {pct(base['positive_3d']['mean'])} -> quant {pct(quant['positive_3d']['mean'])} (delta {pct(delta['positive_3d'])})",
                f"- 1D lane avg 1D: {row['quant_rerank_1d']['avg_1d_return_pct']['mean']:+.2f}% | positive 1D {pct(row['quant_rerank_1d']['positive_1d']['mean'])}",
                f"- 1D lane avg 3D: {row['quant_rerank_1d']['avg_3d_return_pct']['mean']:+.2f}% | positive 3D {pct(row['quant_rerank_1d']['positive_3d']['mean'])}",
                f"- 3D lane avg 1D: {row['quant_rerank_3d']['avg_1d_return_pct']['mean']:+.2f}% | positive 1D {pct(row['quant_rerank_3d']['positive_1d']['mean'])}",
                f"- 3D lane avg 3D: {row['quant_rerank_3d']['avg_3d_return_pct']['mean']:+.2f}% | positive 3D {pct(row['quant_rerank_3d']['positive_3d']['mean'])}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate KRX quant rerank score against archive rows.")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--topn", default="5,10,20")
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    market = str(args.market).upper()
    input_path = Path(args.input_dir) / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = _load_archive(input_path)
    report = build_report(
        df=df,
        market=market,
        confidence=float(args.confidence),
        topn_values=[int(x) for x in str(args.topn).split(",") if str(x).strip()],
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"kr_quant_rerank_validation_{market.lower()}.json"
    md_path = out_dir / f"kr_quant_rerank_validation_{market.lower()}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": report["rows"], "days": report["days"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
