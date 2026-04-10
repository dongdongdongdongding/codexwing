#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from statistics import NormalDist
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

import pandas as pd


RETURN_SPECS = [
    ("return_close", "return_close_pct", "close"),
    ("return_1d", "return_1d_pct", "1d"),
    ("return_3d", "return_3d_pct", "3d"),
]


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _quantile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = max(0.0, min(1.0, q)) * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_values[lo])
    weight = pos - lo
    return float(sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight)


def _bootstrap_ci(values: Iterable[float], confidence: float, iterations: int, seed: int) -> Dict[str, float]:
    sample = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if not sample:
        return {"mean": 0.0, "lower": 0.0, "upper": 0.0, "samples": 0}
    if len(sample) == 1:
        value = round(sample[0], 6)
        return {"mean": value, "lower": value, "upper": value, "samples": 1}
    rng = random.Random(seed)
    means: List[float] = []
    n = len(sample)
    for _ in range(max(200, int(iterations))):
        drawn = [sample[rng.randrange(n)] for _ in range(n)]
        means.append(sum(drawn) / n)
    means.sort()
    alpha = (1.0 - confidence) / 2.0
    return {
        "mean": round(sum(sample) / len(sample), 6),
        "lower": round(_quantile(means, alpha), 6),
        "upper": round(_quantile(means, 1.0 - alpha), 6),
        "samples": int(len(sample)),
    }


def _wilson_interval(successes: int, total: int, confidence: float) -> Dict[str, float]:
    if total <= 0:
        return {"rate": 0.0, "lower": 0.0, "upper": 0.0, "successes": 0, "total": 0}
    p = successes / total
    z = NormalDist().inv_cdf((1.0 + confidence) / 2.0)
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    margin = (
        z
        * math.sqrt((p * (1.0 - p) / total) + ((z * z) / (4.0 * total * total)))
        / denom
    )
    return {
        "rate": round(p, 6),
        "lower": round(max(0.0, center - margin), 6),
        "upper": round(min(1.0, center + margin), 6),
        "successes": int(successes),
        "total": int(total),
    }


def _load_archive(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "validation_excluded" in df.columns:
        raw = df["validation_excluded"]
        if raw.dtype == "object":
            excluded = raw.astype(str).str.lower().isin({"true", "1", "yes"})
        else:
            excluded = raw.astype("boolean").fillna(False)
        df = df[~excluded].copy()
    for col in [
        "label_hit_10pct",
        "decision_score",
        "max_return_observed_pct",
        "return_close_pct",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["decision_bucket", "scan_mode", "strategy_family", "theme_routing_path", "phase25_variant", "tier"]:
        if col in df.columns:
            df[col] = df[col].fillna("unknown").astype(str)
    if "base_trade_date" in df.columns:
        trade_date = df["base_trade_date"].astype(str).str[:10]
    else:
        trade_date = pd.Series("", index=df.index, dtype="object")
    if "recommended_at" in df.columns:
        fallback_date = df["recommended_at"].astype(str).str[:10]
        trade_date = trade_date.where(trade_date.ne("") & trade_date.ne("nan"), fallback_date)
    df["trade_date"] = trade_date
    return df


def _rate_interval(
    df: pd.DataFrame,
    *,
    column: str,
    predicate: Callable[[pd.Series], pd.Series],
    confidence: float,
) -> Dict[str, float]:
    if column not in df.columns:
        return {"rate": 0.0, "lower": 0.0, "upper": 0.0, "successes": 0, "total": 0}
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return {"rate": 0.0, "lower": 0.0, "upper": 0.0, "successes": 0, "total": 0}
    successes = int(predicate(values).sum())
    return _wilson_interval(successes, int(len(values)), confidence)


def _row_metric(df: pd.DataFrame, baseline_rate: float, confidence: float) -> Dict[str, Any]:
    total = int(len(df))
    hits = int(df["label_hit_10pct"].fillna(0).astype(float).ge(1.0).sum())
    interval = _wilson_interval(hits, total, confidence)
    max_returns = [v for v in df["max_return_observed_pct"].dropna().astype(float).tolist()]
    result = {
        "rows": total,
        "hit_10pct": interval,
        "lift_vs_baseline": round((interval["rate"] / baseline_rate), 4) if baseline_rate > 0 else None,
        "max_return_pct": _bootstrap_ci(max_returns, confidence=confidence, iterations=3000, seed=17),
    }
    for key, column, label in RETURN_SPECS:
        values = pd.to_numeric(df[column], errors="coerce").dropna() if column in df.columns else pd.Series(dtype="float64")
        result[f"avg_{label}_return_pct"] = _bootstrap_ci(values.tolist(), confidence=confidence, iterations=3000, seed=23 + len(values))
        result[f"positive_{label}"] = _rate_interval(
            df,
            column=column,
            predicate=lambda series: series.gt(0.0),
            confidence=confidence,
        )
        result[f"avoid_down_{label}"] = _rate_interval(
            df,
            column=column,
            predicate=lambda series: series.ge(0.0),
            confidence=confidence,
        )
    return result


def _group_metrics(
    df: pd.DataFrame,
    group_cols: List[str],
    baseline_rate: float,
    confidence: float,
    min_samples: int,
) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    rows: List[Dict[str, Any]] = []
    grouped = df.groupby(group_cols, dropna=False)
    for key, grp in grouped:
        if len(grp) < min_samples:
            continue
        names = list(key) if isinstance(key, tuple) else [key]
        item = {group_cols[idx]: str(names[idx]) for idx in range(len(group_cols))}
        item.update(_row_metric(grp, baseline_rate=baseline_rate, confidence=confidence))
        rows.append(item)
    rows.sort(key=lambda row: (row["hit_10pct"]["lower"], row["hit_10pct"]["rate"], row["rows"]), reverse=True)
    return rows


def _score_band_metrics(df: pd.DataFrame, baseline_rate: float, confidence: float) -> List[Dict[str, Any]]:
    work = df.dropna(subset=["decision_score"]).copy()
    if work.empty:
        return []
    work["score_band"] = pd.qcut(work["decision_score"], 10, duplicates="drop")
    rows: List[Dict[str, Any]] = []
    grouped = work.groupby("score_band", observed=False)
    for band, grp in grouped:
        band_scores = grp["decision_score"].astype(float)
        row = {
            "score_band": str(band),
            "score_min": round(float(band_scores.min()), 4),
            "score_max": round(float(band_scores.max()), 4),
        }
        row.update(_row_metric(grp, baseline_rate=baseline_rate, confidence=confidence))
        rows.append(row)
    rows.sort(key=lambda row: row["score_min"], reverse=True)
    return rows


def _daily_topn_metrics(df: pd.DataFrame, topn_values: List[int], confidence: float, bootstrap_iters: int) -> List[Dict[str, Any]]:
    work = df.dropna(subset=["decision_score"]).copy()
    work = work[work["trade_date"].astype(str).str.len() >= 8].copy()
    if work.empty:
        return []
    rows: List[Dict[str, Any]] = []
    for topn in topn_values:
        precision_daily: List[float] = []
        recall_daily: List[float] = []
        maxret_daily: List[float] = []
        return_daily: Dict[str, List[float]] = {label: [] for _, _, label in RETURN_SPECS}
        positive_daily: Dict[str, List[float]] = {label: [] for _, _, label in RETURN_SPECS}
        avoid_down_daily: Dict[str, List[float]] = {label: [] for _, _, label in RETURN_SPECS}
        day_rows = 0
        active_days = 0
        for _, day_df in work.groupby("trade_date", dropna=False):
            ordered = day_df.sort_values(["decision_score", "priority_rank"], ascending=[False, True], na_position="last")
            top = ordered.head(topn)
            if top.empty:
                continue
            active_days += 1
            day_rows += int(len(top))
            hit_series = top["label_hit_10pct"].fillna(0).astype(float)
            precision_daily.append(float(hit_series.mean()))
            total_hits = int(day_df["label_hit_10pct"].fillna(0).astype(float).sum())
            if total_hits > 0:
                recall_daily.append(float(hit_series.sum() / total_hits))
            maxret = pd.to_numeric(top["max_return_observed_pct"], errors="coerce").dropna()
            if not maxret.empty:
                maxret_daily.append(float(maxret.mean()))
            for _, column, label in RETURN_SPECS:
                if column not in top.columns:
                    continue
                outcomes = pd.to_numeric(top[column], errors="coerce").dropna()
                if outcomes.empty:
                    continue
                return_daily[label].append(float(outcomes.mean()))
                positive_daily[label].append(float(outcomes.gt(0.0).mean()))
                avoid_down_daily[label].append(float(outcomes.ge(0.0).mean()))
        row = {
            "topn": int(topn),
            "days": int(active_days),
            "rows_scored": int(day_rows),
            "precision_hit_10pct": _bootstrap_ci(precision_daily, confidence=confidence, iterations=bootstrap_iters, seed=topn * 11 + 3),
            "recall_hit_10pct": _bootstrap_ci(recall_daily, confidence=confidence, iterations=bootstrap_iters, seed=topn * 13 + 7),
            "avg_max_return_pct": _bootstrap_ci(maxret_daily, confidence=confidence, iterations=bootstrap_iters, seed=topn * 17 + 5),
        }
        for idx, (_, _, label) in enumerate(RETURN_SPECS, start=1):
            row[f"avg_{label}_return_pct"] = _bootstrap_ci(
                return_daily[label],
                confidence=confidence,
                iterations=bootstrap_iters,
                seed=topn * 19 + idx,
            )
            row[f"positive_{label}"] = _bootstrap_ci(
                positive_daily[label],
                confidence=confidence,
                iterations=bootstrap_iters,
                seed=topn * 23 + idx,
            )
            row[f"avoid_down_{label}"] = _bootstrap_ci(
                avoid_down_daily[label],
                confidence=confidence,
                iterations=bootstrap_iters,
                seed=topn * 29 + idx,
            )
        rows.append(row)
    return rows


def build_report(
    *,
    df: pd.DataFrame,
    market: str,
    confidence: float,
    min_samples: int,
    topn_values: List[int],
    bootstrap_iters: int,
) -> Dict[str, Any]:
    baseline = _row_metric(df, baseline_rate=0.0, confidence=confidence)
    baseline_rate = float(baseline["hit_10pct"]["rate"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market.upper(),
        "confidence_level": float(confidence),
        "rows": int(len(df)),
        "days": int(df["trade_date"].astype(str).replace("nan", "").replace("", pd.NA).dropna().nunique()),
        "baseline": baseline,
        "by_scan_mode": _group_metrics(df, ["scan_mode"], baseline_rate, confidence, min_samples),
        "by_decision_bucket": _group_metrics(df, ["decision_bucket"], baseline_rate, confidence, min_samples),
        "by_scan_mode_bucket": _group_metrics(df, ["scan_mode", "decision_bucket"], baseline_rate, confidence, min_samples),
        "by_phase25_variant": _group_metrics(df, ["phase25_variant"], baseline_rate, confidence, min_samples),
        "score_bands": _score_band_metrics(df, baseline_rate, confidence),
        "daily_topn": _daily_topn_metrics(df, topn_values, confidence, bootstrap_iters),
    }


def build_markdown(report: Dict[str, Any]) -> str:
    def _fmt_pct(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{float(value) * 100.0:.2f}%"

    lines = [
        f"# KRX Top Mover Capture ({report['market']})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- confidence_level: {report['confidence_level']:.2%}",
        f"- rows: {report['rows']}",
        f"- days: {report['days']}",
        "",
        "## Baseline",
    ]
    baseline = report["baseline"]
    hit = baseline["hit_10pct"]
    lines.extend(
        [
            f"- 10% hit rate: {_fmt_pct(hit['rate'])} (CI {_fmt_pct(hit['lower'])} ~ {_fmt_pct(hit['upper'])})",
            f"- positive 1D: {_fmt_pct(baseline['positive_1d']['rate'])} "
            f"(CI {_fmt_pct(baseline['positive_1d']['lower'])} ~ {_fmt_pct(baseline['positive_1d']['upper'])})",
            f"- positive 3D: {_fmt_pct(baseline['positive_3d']['rate'])} "
            f"(CI {_fmt_pct(baseline['positive_3d']['lower'])} ~ {_fmt_pct(baseline['positive_3d']['upper'])})",
            f"- avoid down 1D: {_fmt_pct(baseline['avoid_down_1d']['rate'])} "
            f"(CI {_fmt_pct(baseline['avoid_down_1d']['lower'])} ~ {_fmt_pct(baseline['avoid_down_1d']['upper'])})",
            f"- avoid down 3D: {_fmt_pct(baseline['avoid_down_3d']['rate'])} "
            f"(CI {_fmt_pct(baseline['avoid_down_3d']['lower'])} ~ {_fmt_pct(baseline['avoid_down_3d']['upper'])})",
            f"- avg max return: {baseline['max_return_pct']['mean']:+.2f}% "
            f"(CI {baseline['max_return_pct']['lower']:+.2f}% ~ {baseline['max_return_pct']['upper']:+.2f}%)",
            f"- avg 1D return: {baseline['avg_1d_return_pct']['mean']:+.2f}% "
            f"(CI {baseline['avg_1d_return_pct']['lower']:+.2f}% ~ {baseline['avg_1d_return_pct']['upper']:+.2f}%)",
            f"- avg 3D return: {baseline['avg_3d_return_pct']['mean']:+.2f}% "
            f"(CI {baseline['avg_3d_return_pct']['lower']:+.2f}% ~ {baseline['avg_3d_return_pct']['upper']:+.2f}%)",
            "",
            "## Daily Top-N",
        ]
    )
    for row in report["daily_topn"]:
        p = row["precision_hit_10pct"]
        r = row["recall_hit_10pct"]
        m = row["avg_max_return_pct"]
        lines.append(
            f"- top{row['topn']}: precision={_fmt_pct(p['mean'])} "
            f"(CI {_fmt_pct(p['lower'])} ~ {_fmt_pct(p['upper'])}) | "
            f"recall={_fmt_pct(r['mean'])} (CI {_fmt_pct(r['lower'])} ~ {_fmt_pct(r['upper'])}) | "
            f"positive1D={_fmt_pct(row['positive_1d']['mean'])} | "
            f"positive3D={_fmt_pct(row['positive_3d']['mean'])} | "
            f"avoidDown1D={_fmt_pct(row['avoid_down_1d']['mean'])} | "
            f"avoidDown3D={_fmt_pct(row['avoid_down_3d']['mean'])} | "
            f"avg1D={row['avg_1d_return_pct']['mean']:+.2f}% | "
            f"avg3D={row['avg_3d_return_pct']['mean']:+.2f}% | "
            f"avg_max_return={m['mean']:+.2f}% (CI {m['lower']:+.2f}% ~ {m['upper']:+.2f}%)"
        )

    sections = [
        ("By Scan Mode", report["by_scan_mode"], ["scan_mode"]),
        ("By Decision Bucket", report["by_decision_bucket"], ["decision_bucket"]),
        ("By Scan Mode + Bucket", report["by_scan_mode_bucket"], ["scan_mode", "decision_bucket"]),
        ("By Phase25 Variant", report["by_phase25_variant"], ["phase25_variant"]),
    ]
    for title, rows, keys in sections:
        lines.extend(["", f"## {title}"])
        if not rows:
            lines.append("- no rows")
            continue
        for row in rows[:8]:
            label = " | ".join(f"{key}={row[key]}" for key in keys)
            hit = row["hit_10pct"]
            lines.append(
                f"- {label}: n={row['rows']} hit10={_fmt_pct(hit['rate'])} "
                f"(CI {_fmt_pct(hit['lower'])} ~ {_fmt_pct(hit['upper'])}) "
                f"lift={row['lift_vs_baseline']}"
            )

    lines.extend(["", "## Score Bands"])
    for row in report["score_bands"][:8]:
        hit = row["hit_10pct"]
        lines.append(
            f"- {row['score_band']} [{row['score_min']:.1f}, {row['score_max']:.1f}]: "
            f"n={row['rows']} hit10={_fmt_pct(hit['rate'])} "
            f"(CI {_fmt_pct(hit['lower'])} ~ {_fmt_pct(hit['upper'])})"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantitative KRX upside capture and downside avoidance report with confidence intervals.")
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], required=True)
    parser.add_argument("--input-dir", default="runtime_state/reports/archive")
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    parser.add_argument("--confidence", type=float, default=0.98)
    parser.add_argument("--min-samples", type=int, default=100)
    parser.add_argument("--topn", default="5,10,20,50")
    parser.add_argument("--bootstrap-iters", type=int, default=4000)
    args = parser.parse_args()

    market = str(args.market).upper()
    input_path = Path(args.input_dir) / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = _load_archive(input_path)
    report = build_report(
        df=df,
        market=market,
        confidence=float(args.confidence),
        min_samples=int(args.min_samples),
        topn_values=[int(x) for x in str(args.topn).split(",") if str(x).strip()],
        bootstrap_iters=int(args.bootstrap_iters),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"kr_top_mover_capture_{market.lower()}.json"
    md_path = out_dir / f"kr_top_mover_capture_{market.lower()}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": report["rows"], "days": report["days"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
