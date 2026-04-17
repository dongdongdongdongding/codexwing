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

from multi_agent.agents.kr_quant_reranker import is_kr_explosive_leader_eligible
from multi_agent.tools.report_kr_top_mover_capture import _bootstrap_ci, _load_archive


def _market_suffix_filter(df: pd.DataFrame, market: str) -> pd.DataFrame:
    work = df.copy()
    work = work[work["market_type"].fillna("").astype(str).str.upper().eq("KR")].copy()
    ticker = work["ticker"].fillna("").astype(str)
    if market == "KOSPI":
        return work[ticker.str.endswith(".KS")].copy()
    if market == "KOSDAQ":
        return work[ticker.str.endswith(".KQ")].copy()
    return work.iloc[0:0].copy()


def _daily_metric_report(df: pd.DataFrame, topn: int, confidence: float, bootstrap_iters: int) -> Dict[str, Any]:
    rows_1d: List[float] = []
    rows_3d: List[float] = []
    pos_1d: List[float] = []
    pos_3d: List[float] = []
    avoid_1d: List[float] = []
    avoid_3d: List[float] = []
    hit10: List[float] = []
    days = 0

    for _, day_df in df.groupby("trade_date", dropna=False):
        ordered = day_df.sort_values(["decision_score", "priority_rank"], ascending=[False, True], na_position="last").head(topn)
        if ordered.empty:
            continue
        days += 1
        r1 = pd.to_numeric(ordered["return_1d_pct"], errors="coerce").dropna()
        r3 = pd.to_numeric(ordered["return_3d_pct"], errors="coerce").dropna()
        if not r1.empty:
            rows_1d.append(float(r1.mean()))
            pos_1d.append(float(r1.gt(0).mean()))
            avoid_1d.append(float(r1.ge(0).mean()))
        if not r3.empty:
            rows_3d.append(float(r3.mean()))
            pos_3d.append(float(r3.gt(0).mean()))
            avoid_3d.append(float(r3.ge(0).mean()))
        hit = pd.to_numeric(ordered["label_hit_10pct"], errors="coerce").fillna(0.0)
        hit10.append(float(hit.mean()))

    return {
        "topn": int(topn),
        "days": int(days),
        "avg_1d_return_pct": _bootstrap_ci(rows_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 41 + 3),
        "avg_3d_return_pct": _bootstrap_ci(rows_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 43 + 3),
        "positive_1d": _bootstrap_ci(pos_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 47 + 3),
        "positive_3d": _bootstrap_ci(pos_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 53 + 3),
        "avoid_down_1d": _bootstrap_ci(avoid_1d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 59 + 3),
        "avoid_down_3d": _bootstrap_ci(avoid_3d, confidence=confidence, iterations=bootstrap_iters, seed=topn * 61 + 3),
        "precision_hit_10pct": _bootstrap_ci(hit10, confidence=confidence, iterations=bootstrap_iters, seed=topn * 67 + 3),
    }


def _delta_report(base: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, float]:
    keys = [
        "avg_1d_return_pct",
        "avg_3d_return_pct",
        "positive_1d",
        "positive_3d",
        "avoid_down_1d",
        "avoid_down_3d",
        "precision_hit_10pct",
    ]
    return {
        key: round(float(model[key]["mean"]) - float(base[key]["mean"]), 6)
        for key in keys
    }


def _score_floor(market: str) -> int:
    return 70 if str(market).upper() == "KOSPI" else 85


def build_report(df: pd.DataFrame, market: str, confidence: float, topn_values: List[int], bootstrap_iters: int) -> Dict[str, Any]:
    market = str(market).upper()
    work = _market_suffix_filter(df, market)
    role = work["kr_universe_role"].fillna("").astype(str).str.upper() if "kr_universe_role" in work.columns else pd.Series("", index=work.index, dtype="object")
    work = work[role.eq("EXPLOSIVE_LEADER")].copy()
    work["decision_score"] = pd.to_numeric(work["decision_score"], errors="coerce").fillna(0.0)
    work["priority_rank"] = pd.to_numeric(work["priority_rank"], errors="coerce").fillna(9999)

    gate_rows: List[Dict[str, Any]] = []
    for _, row in work.iterrows():
        payload = row.to_dict()
        gate = is_kr_explosive_leader_eligible(payload, market)
        gate_rows.append(
            {
                **payload,
                "explosive_eligible": bool(gate.get("eligible", False)),
                "explosive_gate_reasons": list(gate.get("reasons", []) or []),
            }
        )

    gated_df = pd.DataFrame(gate_rows)
    if gated_df.empty:
        gated_df = work.copy()
        gated_df["explosive_eligible"] = False
        gated_df["explosive_gate_reasons"] = [[] for _ in range(len(gated_df))]

    eligible_df = gated_df[gated_df["explosive_eligible"].fillna(False).astype(bool)].copy()
    eligible_days = set(eligible_df["trade_date"].astype(str).replace("nan", "").replace("", None).dropna().tolist())
    baseline_scope = work[work["trade_date"].astype(str).isin(eligible_days)].copy() if eligible_days else work.copy()

    comparisons: List[Dict[str, Any]] = []
    for topn in topn_values:
        baseline = _daily_metric_report(baseline_scope, topn, confidence, bootstrap_iters)
        eligible = _daily_metric_report(eligible_df, topn, confidence, bootstrap_iters)
        comparisons.append(
            {
                "topn": int(topn),
                "baseline": baseline,
                "eligible": eligible,
                "delta": _delta_report(baseline, eligible),
            }
        )

    per_day = eligible_df.groupby("trade_date", dropna=False).size() if not eligible_df.empty else []
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "confidence_level": float(confidence),
        "score_floor": int(_score_floor(market)),
        "rows": int(len(work)),
        "eligible_rows": int(len(eligible_df)),
        "days": int(work["trade_date"].astype(str).replace("nan", "").replace("", None).dropna().nunique()) if not work.empty else 0,
        "eligible_days": int(len(eligible_days)),
        "eligible_rate": round(float(len(eligible_df) / len(work)), 6) if len(work) else 0.0,
        "avg_candidates_per_eligible_day": round(float(per_day.mean()), 3) if len(per_day) else 0.0,
        "comparisons": comparisons,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    def pct(v: float) -> str:
        return f"{float(v) * 100.0:.2f}%"

    lines = [
        f"# KR Explosive Leader Validation ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- score_floor: {report['score_floor']}",
        f"- explosive_rows: {report['rows']}",
        f"- eligible_rows: {report['eligible_rows']}",
        f"- days: {report['days']}",
        f"- eligible_days: {report['eligible_days']}",
        f"- eligible_rate: {pct(report['eligible_rate'])}",
        f"- avg_candidates_per_eligible_day: {report['avg_candidates_per_eligible_day']}",
        "",
    ]
    for row in report["comparisons"]:
        base = row["baseline"]
        eligible = row["eligible"]
        delta = row["delta"]
        lines.extend(
            [
                f"## Top {row['topn']}",
                f"- avg 1D: baseline {base['avg_1d_return_pct']['mean']:+.2f}% -> eligible {eligible['avg_1d_return_pct']['mean']:+.2f}% (delta {delta['avg_1d_return_pct']:+.2f}%)",
                f"- avg 3D: baseline {base['avg_3d_return_pct']['mean']:+.2f}% -> eligible {eligible['avg_3d_return_pct']['mean']:+.2f}% (delta {delta['avg_3d_return_pct']:+.2f}%)",
                f"- positive 1D: baseline {pct(base['positive_1d']['mean'])} -> eligible {pct(eligible['positive_1d']['mean'])} (delta {pct(delta['positive_1d'])})",
                f"- positive 3D: baseline {pct(base['positive_3d']['mean'])} -> eligible {pct(eligible['positive_3d']['mean'])} (delta {pct(delta['positive_3d'])})",
                f"- hit 10% precision: baseline {pct(base['precision_hit_10pct']['mean'])} -> eligible {pct(eligible['precision_hit_10pct']['mean'])} (delta {pct(delta['precision_hit_10pct'])})",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate KR explosive leader eligible universe against explosive baseline.")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--topn", default="5,10,20")
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    input_path = Path(args.input_dir) / f"scan_archive_learning_dataset_{str(args.market).lower()}.csv"
    df = _load_archive(input_path)
    report = build_report(
        df=df,
        market=str(args.market).upper(),
        confidence=float(args.confidence),
        topn_values=[int(x) for x in str(args.topn).split(",") if str(x).strip()],
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    market = str(args.market).lower()
    json_path = out_dir / f"kr_explosive_leader_validation_{market}.json"
    md_path = out_dir / f"kr_explosive_leader_validation_{market}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "rows": report["rows"],
                "eligible_rows": report["eligible_rows"],
                "eligible_days": report["eligible_days"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
