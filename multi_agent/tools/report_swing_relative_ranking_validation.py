#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.loss_risk_features import compute_entry_timing_risk_features  # noqa: E402

DEFAULT_ARCHIVE = ROOT / "runtime_state" / "reports" / "archive" / "scan_archive_learning_dataset_all.csv"
DEFAULT_OUT_DIR = ROOT / "runtime_state" / "reports" / "validation"

BASE_HORIZONS = [
    ("1d", "return_1d_pct"),
    ("3d", "return_3d_pct"),
    ("5d", "return_5d_pct"),
    ("7d", "return_7d_pct"),
    ("14d", "return_14d_pct"),
    ("30d", "return_30d_pct"),
]

RANK_BUCKETS = [
    ("top5pct", 0.05),
    ("top15pct", 0.15),
    ("top30pct", 0.30),
    ("all_ranked", 1.00),
]

FEATURES = [
    "decision_score",
    "alpha_score",
    "tech_score",
    "whale_score",
    "volume_ratio",
    "prob_clean",
    "phase25_prob",
    "model_prob_mean",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_score",
    "loss_risk_score",
    "entry_timing_risk_score",
    "volatility_20d",
    "atr_pct_14",
    "rsi_14",
    "prev_pct_change_1d",
    "prev_pct_change_5d",
]

KOSPI_WEIGHTS = {
    # 2026-05-11 KR SWING floor/win grid: modestly improves 1/3/5/7d win
    # and average return versus decision_score-only without worsening minima.
    "decision_score": 0.55,
    "volume_ratio": 0.20,
    "loss_risk_score": -0.10,
}

KOSDAQ_WEIGHTS = {
    # 2026-05-11 KR SWING floor/win grid: improves 3/5/7d win and average
    # return, keeps 3/5d minima stable, and improves 7d minimum. 1d remains
    # a separate early-diagnostic horizon rather than the swing objective.
    "tech_score": 0.10,
    "volume_ratio": 0.22,
    "prob_clean": 0.20,
    "low_model_prob_score": 0.10,
    "low_prob_high_score": 0.15,
    "loss_risk_score": -0.10,
    "entry_timing_risk_score": -0.04,
}


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


def _spearman(x: pd.Series, y: pd.Series) -> float | None:
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 50:
        return None
    rx = valid["x"].rank()
    ry = valid["y"].rank()
    corr = rx.corr(ry)
    if corr is None or pd.isna(corr):
        return None
    return round(float(corr), 4)


def _load_archive(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df = df[df.get("market").isin(["KOSPI", "KOSDAQ"]) & df.get("scan_mode").eq("SWING")].copy()
    df["trade_date"] = pd.to_datetime(df["created_at"], errors="coerce").dt.date
    df = df.dropna(subset=["trade_date", "ticker"])
    df = df.sort_values("created_at").drop_duplicates(["trade_date", "market", "ticker"], keep="last")
    for col in set(FEATURES + [c for _, c in BASE_HORIZONS]):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _add_inverted_features_if_missing(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    prob_cols = [c for c in ["ml_prob", "prob_clean", "phase25_prob"] if c in work.columns]
    if prob_cols:
        computed_mean = work[prob_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
        computed_count = work[prob_cols].apply(pd.to_numeric, errors="coerce").notna().sum(axis=1)
        if "model_prob_mean" not in work.columns:
            work["model_prob_mean"] = computed_mean
        else:
            work["model_prob_mean"] = pd.to_numeric(work["model_prob_mean"], errors="coerce").fillna(computed_mean)
        if "model_prob_available_count" not in work.columns:
            work["model_prob_available_count"] = computed_count
        else:
            work["model_prob_available_count"] = (
                pd.to_numeric(work["model_prob_available_count"], errors="coerce")
                .fillna(computed_count)
            )
    if "model_prob_mean" in work.columns:
        count = work.get("model_prob_available_count", pd.Series(0, index=work.index))
        computed_low_model = (50.0 - work["model_prob_mean"]).clip(lower=0.0).where(count.gt(0), 0.0)
        if "low_model_prob_score" not in work.columns:
            work["low_model_prob_score"] = computed_low_model
        else:
            work["low_model_prob_score"] = pd.to_numeric(work["low_model_prob_score"], errors="coerce").fillna(computed_low_model)
        score_cols = [c for c in ["alpha_score", "tech_score"] if c in work.columns]
        if score_cols:
            score_mean = work[score_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
            computed_low_high = (score_mean - work["model_prob_mean"]).clip(lower=0).where(count.gt(0))
            if "low_prob_high_score" not in work.columns:
                work["low_prob_high_score"] = computed_low_high
            else:
                work["low_prob_high_score"] = pd.to_numeric(work["low_prob_high_score"], errors="coerce").fillna(computed_low_high)
    if "entry_timing_risk_score" not in work.columns:
        work["entry_timing_risk_score"] = float("nan")
    for idx, row in work.iterrows():
        current = _safe_float(row.get("entry_timing_risk_score"))
        if current is not None:
            continue
        computed = compute_entry_timing_risk_features(
            market_subtype=row.get("market"),
            expected_return_1d_pct=row.get("expected_return_1d_pct"),
            expected_return_3d_pct=row.get("expected_return_3d_pct"),
            expected_edge_score=row.get("expected_edge_score"),
            prev_pct_change_1d=row.get("prev_pct_change_1d"),
            prev_pct_change_5d=row.get("prev_pct_change_5d"),
            volume_ratio=row.get("volume_ratio"),
            prob_clean=row.get("prob_clean"),
            loss_risk_score=row.get("loss_risk_score"),
            position=row.get("position"),
            tier=row.get("tier"),
            trend=row.get("real_trend") or row.get("trend"),
        )
        work.at[idx, "entry_timing_risk_score"] = computed["entry_timing_risk_score"]
    return work


def _rank_feature(group: pd.DataFrame, feature: str, direction: int) -> pd.Series:
    values = pd.to_numeric(group.get(feature), errors="coerce")
    if values.notna().sum() < 3:
        return pd.Series(float("nan"), index=group.index)
    ascending = direction > 0
    return values.rank(pct=True, ascending=ascending)


def _composite_for_market(group: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
    pieces: List[pd.Series] = []
    total = 0.0
    for feature, weight in weights.items():
        if feature not in group.columns:
            continue
        ranked = _rank_feature(group, feature, 1 if weight >= 0 else -1)
        if ranked.notna().sum() == 0:
            continue
        pieces.append(ranked.fillna(0.5) * abs(float(weight)))
        total += abs(float(weight))
    if total <= 0 or not pieces:
        return pd.Series(float("nan"), index=group.index)
    score = sum(pieces) / total * 100.0
    return score


def _add_relative_scores(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["legacy_decision_score_rank"] = work.groupby(["trade_date", "market"])["decision_score"].rank(pct=True, ascending=False)
    work["relative_composite_score"] = float("nan")
    for (trade_date, market), group in work.groupby(["trade_date", "market"], dropna=False):
        weights = KOSPI_WEIGHTS if market == "KOSPI" else KOSDAQ_WEIGHTS
        score = _composite_for_market(group, weights)
        thresholds = {"KOSPI": {"soft": 50.0, "hard": 65.0}, "KOSDAQ": {"soft": 45.0, "hard": 65.0}}.get(
            str(market),
            {"soft": 58.0, "hard": 75.0},
        )
        if "loss_risk_score" in group.columns:
            loss = pd.to_numeric(group["loss_risk_score"], errors="coerce")
            score = score.mask(loss.ge(float(thresholds["hard"])), score.clip(upper=30.0))
            score = score.mask(
                loss.ge(float(thresholds["soft"])) & loss.lt(float(thresholds["hard"])),
                score.clip(upper=55.0),
            )
        work.loc[group.index, "relative_composite_score"] = score
    work["relative_composite_rank"] = work.groupby(["trade_date", "market"])["relative_composite_score"].rank(pct=True, ascending=False)
    return work


def _metric(vals: pd.Series) -> Dict[str, Any]:
    clean = pd.to_numeric(vals, errors="coerce").dropna()
    if clean.empty:
        return {"n": 0, "win_pct": None, "avg_pct": None, "median_pct": None, "hit5_pct": None, "loss5_pct": None}
    return {
        "n": int(len(clean)),
        "win_pct": round(float(clean.gt(0).mean() * 100.0), 2),
        "avg_pct": round(float(clean.mean()), 3),
        "median_pct": round(float(clean.median()), 3),
        "max_pct": round(float(clean.max()), 3),
        "min_pct": round(float(clean.min()), 3),
        "hit5_pct": round(float(clean.ge(5.0).mean() * 100.0), 2),
        "loss5_pct": round(float(clean.le(-5.0).mean() * 100.0), 2),
    }


def _bucket_metrics(df: pd.DataFrame, rank_col: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for market in ["KOSPI", "KOSDAQ", "ALL"]:
        market_df = df if market == "ALL" else df[df["market"].eq(market)]
        for bucket, cutoff in RANK_BUCKETS:
            sub = market_df[market_df[rank_col].le(cutoff)].copy()
            for label, ret_col in BASE_HORIZONS:
                if ret_col not in sub.columns:
                    rows.append({"market": market, "rank_source": rank_col, "bucket": bucket, "horizon": label, **_metric(pd.Series(dtype="float64"))})
                    continue
                abs_metric = _metric(sub[ret_col])
                if ret_col in market_df.columns:
                    market_median = market_df.groupby(["trade_date", "market"])[ret_col].transform("median")
                    excess = market_df[ret_col] - market_median
                    excess_sub = excess.loc[sub.index]
                    excess_metric = _metric(excess_sub)
                else:
                    excess_metric = _metric(pd.Series(dtype="float64"))
                item = {"market": market, "rank_source": rank_col, "bucket": bucket, "horizon": label}
                item.update({f"abs_{k}": v for k, v in abs_metric.items()})
                item.update({f"excess_{k}": v for k, v in excess_metric.items()})
                rows.append(item)
    return rows


def _feature_diagnostics(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    available = [f for f in FEATURES if f in df.columns]
    for market in ["KOSPI", "KOSDAQ", "ALL"]:
        market_df = df if market == "ALL" else df[df["market"].eq(market)]
        for feature in available:
            for label, ret_col in BASE_HORIZONS:
                if ret_col not in market_df.columns:
                    continue
                valid = market_df[[feature, ret_col]].dropna()
                if len(valid) < 50:
                    continue
                q_hi = valid[feature].quantile(0.80)
                q_lo = valid[feature].quantile(0.20)
                hi = valid[valid[feature].ge(q_hi)][ret_col]
                lo = valid[valid[feature].le(q_lo)][ret_col]
                rows.append(
                    {
                        "market": market,
                        "feature": feature,
                        "horizon": label,
                        "n": int(len(valid)),
                        "spearman": _spearman(valid[feature], valid[ret_col]),
                        "top20": _metric(hi),
                        "bottom20": _metric(lo),
                        "top_minus_bottom_avg_pct": None
                        if hi.dropna().empty or lo.dropna().empty
                        else round(float(hi.mean() - lo.mean()), 3),
                    }
                )
    rows.sort(key=lambda r: (str(r["market"]), str(r["horizon"]), abs(float(r.get("spearman") or 0))), reverse=True)
    return rows


def _factor_sufficiency(feature_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        sub = [r for r in feature_rows if r["market"] == market and r["horizon"] in {"5d", "7d"}]
        positive = [
            r for r in sub
            if (r.get("spearman") is not None and float(r["spearman"]) >= 0.05)
            and (r.get("top_minus_bottom_avg_pct") is not None and float(r["top_minus_bottom_avg_pct"]) > 0)
        ]
        negative = [
            r for r in sub
            if (r.get("spearman") is not None and float(r["spearman"]) <= -0.05)
        ]
        summary[market] = {
            "positive_factor_count_5d_7d": len(positive),
            "negative_or_inverted_factor_count_5d_7d": len(negative),
            "strongest_positive": positive[:8],
            "strongest_negative": negative[:8],
            "sufficient_for_single_global_score": False,
            "recommended_model": "market_specific_relative_ranking",
        }
    return summary


def build_report(df: pd.DataFrame) -> Dict[str, Any]:
    work = _add_relative_scores(_add_inverted_features_if_missing(df))
    feature_rows = _feature_diagnostics(work)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DEFAULT_ARCHIVE.relative_to(ROOT)) if DEFAULT_ARCHIVE.exists() else str(DEFAULT_ARCHIVE),
        "scope": "KR SWING deduped by trade_date/market/ticker",
        "rows": int(len(work)),
        "dates": int(work["trade_date"].nunique()),
        "available_horizons": {label: int(work[col].notna().sum()) if col in work.columns else 0 for label, col in BASE_HORIZONS},
        "rank_bucket_metrics": {
            "legacy_decision_score_rank": _bucket_metrics(work, "legacy_decision_score_rank"),
            "relative_composite_rank": _bucket_metrics(work, "relative_composite_rank"),
        },
        "feature_diagnostics": feature_rows,
        "factor_sufficiency": _factor_sufficiency(feature_rows),
        "proposed_weights": {
            "KOSPI": KOSPI_WEIGHTS,
            "KOSDAQ": KOSDAQ_WEIGHTS,
        },
        "recommendations": [
            "Use hard rejects only for data quality, liquidity, non-common stocks, and extreme risk.",
            "Compute ranking percentile within trade_date and market, not against absolute global thresholds.",
            "Use separate KOSPI and KOSDAQ factor weights; KOSDAQ probability features are regime-inverted.",
            "Keep 1d/3d as early diagnostics, but optimize swing admission on 5d/7d until 14d/30d fill rates mature.",
            "Add and backfill return_14d_pct/return_30d_pct before promoting long-horizon claims.",
        ],
    }


def _best_rows(rows: List[Dict[str, Any]], market: str, horizon: str, rank_source: str) -> List[Dict[str, Any]]:
    return [
        r for r in rows
        if r["market"] == market and r["horizon"] == horizon and r["rank_source"] == rank_source
    ]


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Swing Relative Ranking Validation",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- rows: `{report['rows']}`",
        f"- dates: `{report['dates']}`",
        f"- horizon fill: `{report['available_horizons']}`",
        "",
        "## Bucket Performance",
    ]
    for rank_source, rows in report["rank_bucket_metrics"].items():
        lines.append(f"### {rank_source}")
        for market in ["KOSPI", "KOSDAQ", "ALL"]:
            lines.append(f"**{market}**")
            for horizon in ["1d", "3d", "5d", "7d", "14d", "30d"]:
                selected = _best_rows(rows, market, horizon, rank_source)
                if not selected:
                    continue
                compact = []
                for row in selected:
                    compact.append(
                        f"{row['bucket']}:n={row.get('abs_n', 0)},"
                        f"win={row.get('abs_win_pct')},avg={row.get('abs_avg_pct')},"
                        f"exAvg={row.get('excess_avg_pct')}"
                    )
                lines.append(f"- {horizon}: " + " | ".join(compact))
            lines.append("")
    lines.extend(["## Strong Factors"])
    for market in ["KOSPI", "KOSDAQ"]:
        lines.append(f"### {market}")
        sub = [
            r for r in report["feature_diagnostics"]
            if r["market"] == market and r["horizon"] in {"5d", "7d"} and r.get("spearman") is not None
        ]
        sub = sorted(sub, key=lambda r: (float(r.get("spearman") or 0), float(r.get("top_minus_bottom_avg_pct") or 0)), reverse=True)
        for row in sub[:10]:
            top = row["top20"]
            bot = row["bottom20"]
            lines.append(
                f"- `{row['feature']}` {row['horizon']}: rho={row['spearman']}, "
                f"top20 avg={top.get('avg_pct')} win={top.get('win_pct')} "
                f"vs bottom20 avg={bot.get('avg_pct')} win={bot.get('win_pct')}"
            )
        lines.append("")
    lines.extend(
        [
            "## Factor Sufficiency",
            "```json",
            json.dumps(report["factor_sufficiency"], ensure_ascii=False, indent=2)[:6000],
            "```",
            "",
            "## Recommendations",
        ]
    )
    lines.extend([f"- {item}" for item in report["recommendations"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate market-relative swing ranking factors and bucket outcomes.")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    archive = Path(args.archive)
    df = _load_archive(archive)
    report = build_report(df)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "swing_relative_ranking_validation.json"
    md_path = out_dir / "swing_relative_ranking_validation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": report["rows"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
