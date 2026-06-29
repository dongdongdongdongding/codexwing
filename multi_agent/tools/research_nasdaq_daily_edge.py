#!/usr/bin/env python3
"""Research NASDAQ daily edge from the 8y feature backfill.

The validation target is deliberately cross-sectional:
- train only on past dates
- evaluate top-N picks by date
- score against same-day universe and same-day liquidity bucket baselines
- keep liquidity floors explicit
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_PANEL = Path("/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"

FEATURES = [
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "ret_60d",
    "ma5_dist",
    "ma10_dist",
    "ma20_dist",
    "ma50_dist",
    "ma60_dist",
    "ma120_dist",
    "ma200_dist",
    "ma20_slope",
    "ma60_slope",
    "ma200_slope",
    "rsi14",
    "rsi_slope",
    "accel",
    "consec_up",
    "dist_hi20",
    "dist_hi60",
    "dist_hi120",
    "dist_lo20",
    "dist_lo60",
    "pos20",
    "bb_pctb",
    "bb_bw",
    "atr_pct",
    "vol20",
    "close_loc",
    "gap",
    "abs_gap",
    "vol_ratio",
    "vol_trend",
    "turn_z",
    "volume_z60",
    "dollar_volume_ratio20",
    "dollar_volume_z60",
    "obv_slope",
    "cmf20",
    "macd",
    "macd_signal",
    "macd_hist",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "high_low_spread_pct",
]

LABELS = [
    "touch5_3d",
    "touch5_5d",
    "dd5_3d",
    "dd5_5d",
    "ft_5_5",
    "fwd_close_ret_3d",
    "fwd_close_ret_5d",
    "fwd_high_ret_3d",
    "fwd_low_ret_3d",
]


@dataclass(frozen=True)
class ScoreSpec:
    name: str
    kind: str
    score_col: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _read_panel(path: Path) -> pd.DataFrame:
    cols = [
        "date",
        "symbol",
        "close",
        "volume",
        "dollar_volume",
        "liq20",
        "liq60",
        "feature_ready",
    ] + FEATURES + LABELS
    df = pd.read_parquet(path, columns=cols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "symbol", "close", "liq20"])
    df["year"] = df["date"].dt.year.astype(int)
    for col in ["close", "volume", "dollar_volume", "liq20", "liq60", "feature_ready"] + FEATURES + LABELS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _rank_by_date(df: pd.DataFrame, col: str, *, ascending: bool = True) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").groupby(df["date"]).rank(pct=True, ascending=ascending)


def add_formula_scores(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    r = lambda col, asc=True: _rank_by_date(work, col, ascending=asc)

    work["score_vol_touch"] = r("atr_pct") + r("vol20") + r("range_pct") + r("bb_bw")
    work["score_trend_momo"] = r("ret_20d") + r("ret_60d") + r("ma60_slope") + r("ma200_slope") + r("dist_hi120")
    work["score_breakout_volume"] = r("dist_hi20") + r("pos20") + r("vol_ratio") + r("dollar_volume_ratio20") + r("ret_5d")
    work["score_pullback_uptrend"] = (
        r("ma200_slope")
        + r("ma60_slope")
        + r("dist_hi120")
        + r("dist_hi20", False)
        + r("rsi14", False)
    )
    work["score_volume_surge"] = r("vol_ratio") + r("dollar_volume_ratio20") + r("turn_z") + r("ret_3d")
    work["score_quality_lowvol_momo"] = (
        r("ret_20d")
        + r("ma200_slope")
        + r("dist_hi120")
        + r("atr_pct", False)
        + r("vol20", False)
    )
    return work


def _sample_train(train: pd.DataFrame, target: str, max_rows: int, seed: int) -> pd.DataFrame:
    train = train[train[target].notna()].copy()
    if max_rows <= 0 or len(train) <= max_rows:
        return train
    positives = train[train[target].eq(1)]
    negatives = train[train[target].eq(0)]
    pos_n = min(len(positives), max_rows // 2)
    neg_n = max_rows - pos_n
    pieces = []
    if pos_n > 0:
        pieces.append(positives.sample(n=pos_n, random_state=seed))
    if neg_n > 0 and not negatives.empty:
        pieces.append(negatives.sample(n=min(len(negatives), neg_n), random_state=seed + 1))
    sampled = pd.concat(pieces, ignore_index=False) if pieces else train.sample(n=max_rows, random_state=seed)
    if len(sampled) < max_rows and len(train) > len(sampled):
        extra = train.drop(index=sampled.index, errors="ignore").sample(
            n=min(max_rows - len(sampled), len(train) - len(sampled)),
            random_state=seed + 2,
        )
        sampled = pd.concat([sampled, extra], ignore_index=False)
    return sampled.sample(frac=1.0, random_state=seed + 3)


def _fit_lgbm_classifier(train: pd.DataFrame, features: Sequence[str], target: str, seed: int, n_estimators: int):
    import lightgbm as lgb

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=int(n_estimators),
        learning_rate=0.035,
        num_leaves=31,
        max_depth=6,
        max_bin=127,
        min_child_samples=80,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.05,
        reg_lambda=0.25,
        force_col_wise=True,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )
    X = train[list(features)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = train[target].astype(int)
    model.fit(X, y)
    return model


def add_walk_forward_ml_scores(
    df: pd.DataFrame,
    *,
    feature_cols: Sequence[str],
    min_train_rows: int,
    max_train_rows: int,
    first_test_year: int,
    embargo_days: int,
    ml_targets: Sequence[str],
    n_estimators: int,
    seed: int,
) -> tuple[pd.DataFrame, List[Dict[str, Any]]]:
    work = df.copy()
    all_score_cols = {
        "touch5_3d": "ml_p_touch5_3d",
        "dd5_3d": "ml_p_dd5_3d",
        "ft_5_5": "ml_p_ft_5_5",
        "touch5_5d": "ml_p_touch5_5d",
    }
    target_set = {str(item).strip() for item in ml_targets if str(item).strip()}
    score_cols = {target: col for target, col in all_score_cols.items() if target in target_set}
    for col in score_cols.values():
        work[col] = np.nan

    fold_reports: List[Dict[str, Any]] = []
    years = sorted(int(y) for y in work["year"].dropna().unique() if int(y) >= first_test_year)
    for test_year in years:
        test_start = pd.Timestamp(year=test_year, month=1, day=1)
        train = work[(work["date"] < test_start - timedelta(days=int(embargo_days)))].copy()
        test_idx = work[work["year"].eq(test_year)].index
        if len(train) < min_train_rows or len(test_idx) == 0:
            continue
        fold: Dict[str, Any] = {
            "test_year": int(test_year),
            "train_rows_available": int(len(train)),
            "test_rows": int(len(test_idx)),
            "targets": {},
        }
        X_test = work.loc[test_idx, list(feature_cols)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        for offset, (target, out_col) in enumerate(score_cols.items()):
            train_target = train[train[target].notna()].copy()
            if len(train_target) < min_train_rows:
                continue
            sampled = _sample_train(train_target, target, max_train_rows, seed + test_year * 17 + offset)
            try:
                print(f"[ML] year={test_year} target={target} train={len(sampled)} test={len(test_idx)}")
                model = _fit_lgbm_classifier(
                    sampled,
                    feature_cols,
                    target,
                    seed + test_year * 31 + offset,
                    n_estimators,
                )
                prob = model.predict_proba(X_test)[:, 1]
                work.loc[test_idx, out_col] = prob
                fold["targets"][target] = {
                    "train_rows": int(len(sampled)),
                    "train_positive_rate": round(float(sampled[target].mean()), 6),
                    "test_scored_rows": int(np.isfinite(prob).sum()),
                    "prob_mean": round(float(np.nanmean(prob)), 6),
                }
            except Exception as exc:
                fold["targets"][target] = {"error": repr(exc)}
        fold_reports.append(fold)

    if "ml_p_touch5_3d" in work.columns and "ml_p_dd5_3d" in work.columns:
        work["ml_edge3"] = work["ml_p_touch5_3d"] - work["ml_p_dd5_3d"]
    if {"ml_p_touch5_3d", "ml_p_ft_5_5", "ml_p_dd5_3d"}.issubset(work.columns):
        work["ml_combo_touch_ft_risk"] = work["ml_p_touch5_3d"] + work["ml_p_ft_5_5"] - work["ml_p_dd5_3d"]
    if {"ml_p_touch5_5d", "ml_p_ft_5_5", "ml_p_dd5_3d"}.issubset(work.columns):
        work["ml_combo_5d_touch_ft_risk"] = work["ml_p_touch5_5d"] + work["ml_p_ft_5_5"] - work["ml_p_dd5_3d"]
    return work, fold_reports


def _add_baselines(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    liq_rank = work.groupby("date")["liq20"].rank(pct=True, ascending=True)
    work["liq_decile"] = np.minimum(9, np.floor(liq_rank.fillna(0.0) * 10.0).astype(int))
    metric_cols = ["touch5_3d", "touch5_5d", "dd5_3d", "dd5_5d", "ft_5_5", "fwd_close_ret_3d", "fwd_close_ret_5d"]
    daily = work.groupby("date", observed=True)[metric_cols].mean().add_prefix("base_day_")
    bucket = work.groupby(["date", "liq_decile"], observed=True)[metric_cols].mean().add_prefix("base_liq_")
    work = work.join(daily, on="date")
    work = work.join(bucket, on=["date", "liq_decile"])
    return work


def _mean_ci(series: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float]]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None, None, None
    mean = float(clean.mean())
    if len(clean) < 2:
        return mean, None, None
    se = float(clean.std(ddof=1) / math.sqrt(len(clean)))
    return mean, mean - 1.96 * se, mean + 1.96 * se


def _metric_block(picks: pd.DataFrame) -> Dict[str, Any]:
    if picks.empty:
        return {
            "n": 0,
            "days": 0,
        }
    out: Dict[str, Any] = {
        "n": int(len(picks)),
        "days": int(picks["date"].nunique()),
        "symbols": int(picks["symbol"].nunique()),
        "avg_liq20": round(float(picks["liq20"].mean()), 2),
        "median_liq20": round(float(picks["liq20"].median()), 2),
    }
    pairs = [
        ("touch5_3d", "touch3"),
        ("touch5_5d", "touch5"),
        ("dd5_3d", "dd3"),
        ("dd5_5d", "dd5"),
        ("ft_5_5", "ft55"),
        ("fwd_close_ret_3d", "ret3"),
        ("fwd_close_ret_5d", "ret5"),
    ]
    for col, name in pairs:
        vals = pd.to_numeric(picks[col], errors="coerce")
        out[name] = round(float(vals.mean()), 6) if vals.notna().any() else None
        day_ex = vals - pd.to_numeric(picks[f"base_day_{col}"], errors="coerce")
        liq_ex = vals - pd.to_numeric(picks[f"base_liq_{col}"], errors="coerce")
        mean, lo, hi = _mean_ci(day_ex)
        out[f"{name}_day_ex"] = None if mean is None else round(mean, 6)
        out[f"{name}_day_ex_ci95"] = [None if lo is None else round(lo, 6), None if hi is None else round(hi, 6)]
        mean, lo, hi = _mean_ci(liq_ex)
        out[f"{name}_liq_ex"] = None if mean is None else round(mean, 6)
        out[f"{name}_liq_ex_ci95"] = [None if lo is None else round(lo, 6), None if hi is None else round(hi, 6)]
    annual = []
    for year, grp in picks.groupby("year", observed=True):
        item = {
            "year": int(year),
            "n": int(len(grp)),
            "days": int(grp["date"].nunique()),
        }
        for col, name in [("touch5_3d", "touch3"), ("ft_5_5", "ft55"), ("dd5_3d", "dd3"), ("fwd_close_ret_3d", "ret3"), ("fwd_close_ret_5d", "ret5")]:
            vals = pd.to_numeric(grp[col], errors="coerce")
            liq_ex = vals - pd.to_numeric(grp[f"base_liq_{col}"], errors="coerce")
            item[name] = round(float(vals.mean()), 6) if vals.notna().any() else None
            item[f"{name}_liq_ex"] = round(float(liq_ex.mean()), 6) if liq_ex.notna().any() else None
        annual.append(item)
    out["annual"] = annual
    out["years_ret3_liq_ex_pos"] = int(sum((item.get("ret3_liq_ex") or 0) > 0 for item in annual))
    out["years_ret5_liq_ex_pos"] = int(sum((item.get("ret5_liq_ex") or 0) > 0 for item in annual))
    out["years_ft55_liq_ex_pos"] = int(sum((item.get("ft55_liq_ex") or 0) > 0 for item in annual))
    return out


def evaluate_scores(
    df: pd.DataFrame,
    *,
    score_specs: Sequence[ScoreSpec],
    liquidity_floors: Sequence[float],
    topn_values: Sequence[int],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    metric_cols = [
        "date",
        "symbol",
        "year",
        "liq20",
        "touch5_3d",
        "touch5_5d",
        "dd5_3d",
        "dd5_5d",
        "ft_5_5",
        "fwd_close_ret_3d",
        "fwd_close_ret_5d",
    ]
    score_cols = [spec.score_col for spec in score_specs if spec.score_col in df.columns]
    keep_cols = [col for col in metric_cols + score_cols if col in df.columns]
    for floor in liquidity_floors:
        pool = df.loc[df["liq20"].ge(float(floor)), keep_cols].copy()
        if pool.empty:
            continue
        pool = _add_baselines(pool)
        for spec in score_specs:
            if spec.score_col not in pool.columns:
                continue
            score = pd.to_numeric(pool[spec.score_col], errors="coerce")
            valid = score.notna()
            if not bool(valid.any()):
                continue
            rank = score.loc[valid].groupby(pool.loc[valid, "date"], observed=True).rank(method="first", ascending=False)
            for topn in topn_values:
                picks = pool.loc[rank[rank.le(int(topn))].index]
                metrics = _metric_block(picks)
                metrics.update(
                    {
                        "score": spec.name,
                        "kind": spec.kind,
                        "score_col": spec.score_col,
                        "liq20_floor": float(floor),
                        "topn": int(topn),
                    }
                )
                metrics["selection_key"] = _selection_key(metrics)
                rows.append(metrics)
    return rows


def _selection_key(metrics: Mapping[str, Any]) -> float:
    ret3 = _finite_float(metrics.get("ret3_liq_ex")) or 0.0
    ret5 = _finite_float(metrics.get("ret5_liq_ex")) or 0.0
    ft = _finite_float(metrics.get("ft55_liq_ex")) or 0.0
    touch = _finite_float(metrics.get("touch3_liq_ex")) or 0.0
    dd = _finite_float(metrics.get("dd3_liq_ex")) or 0.0
    years = float(metrics.get("years_ret3_liq_ex_pos") or 0) / max(1.0, float(len(metrics.get("annual") or [])))
    return round(ret3 + ret5 + 2.0 * ft + touch - dd + years * 0.25, 6)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_md(path: Path, report: Mapping[str, Any]) -> None:
    lines = [
        "# NASDAQ Daily Edge Research",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- panel_path: `{report.get('panel_path')}`",
        f"- rows_loaded: `{report.get('rows_loaded')}`",
        f"- rows_eligible_base: `{report.get('rows_eligible_base')}`",
        f"- research_liq_floor: `{report.get('research_liq_floor')}`",
        f"- symbols_eligible_base: `{report.get('symbols_eligible_base')}`",
        f"- date_range: `{report.get('date_min')}` ~ `{report.get('date_max')}`",
        f"- caveat: `{report.get('caveat')}`",
        "",
        "## Base Rates",
        "",
    ]
    for item in report.get("base_rates", []):
        lines.append(
            f"- liq20>={item['liq20_floor']:,}: rows `{item['rows']}`, symbols `{item['symbols']}`, "
            f"touch3 `{item['touch5_3d']:.2%}`, ft55 `{item['ft55']:.2%}`, "
            f"ret3 `{item['ret3']:+.3f}%`, ret5 `{item['ret5']:+.3f}%`"
        )
    lines.extend(["", "## Top Candidates", ""])
    for row in report.get("top_candidates", [])[:20]:
        lines.append(
            f"- `{row['score']}` {row['kind']} floor `{row['liq20_floor']:,.0f}` top{row['topn']} "
            f"n `{row['n']}` touch3 `{row.get('touch3', 0):.2%}` "
            f"ft55 `{row.get('ft55', 0):.2%}` dd3 `{row.get('dd3', 0):.2%}` "
            f"ret3_liq_ex `{row.get('ret3_liq_ex', 0):+.3f}%` "
            f"ret5_liq_ex `{row.get('ret5_liq_ex', 0):+.3f}%` "
            f"ft55_liq_ex `{row.get('ft55_liq_ex', 0):+.2%}` "
            f"years_ret3_pos `{row.get('years_ret3_liq_ex_pos')}/{len(row.get('annual') or [])}`"
        )
    lines.extend(["", "## Fold Summary", ""])
    for fold in report.get("ml_folds", []):
        targets = ", ".join(f"{k}:n={v.get('train_rows')}" for k, v in (fold.get("targets") or {}).items() if isinstance(v, dict))
        lines.append(f"- `{fold.get('test_year')}` train `{fold.get('train_rows_available')}` test `{fold.get('test_rows')}` {targets}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _base_rates(df: pd.DataFrame, floors: Sequence[float]) -> List[Dict[str, Any]]:
    rows = []
    for floor in floors:
        sub = df[df["liq20"].ge(float(floor))]
        rows.append(
            {
                "liq20_floor": int(floor),
                "rows": int(len(sub)),
                "symbols": int(sub["symbol"].nunique()) if not sub.empty else 0,
                "days": int(sub["date"].nunique()) if not sub.empty else 0,
                "touch5_3d": round(float(sub["touch5_3d"].mean()), 6) if not sub.empty else None,
                "touch5_5d": round(float(sub["touch5_5d"].mean()), 6) if not sub.empty else None,
                "ft55": round(float(sub["ft_5_5"].mean()), 6) if not sub.empty else None,
                "dd5_3d": round(float(sub["dd5_3d"].mean()), 6) if not sub.empty else None,
                "ret3": round(float(sub["fwd_close_ret_3d"].mean()), 6) if not sub.empty else None,
                "ret5": round(float(sub["fwd_close_ret_5d"].mean()), 6) if not sub.empty else None,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research NASDAQ daily edge on the 8y feature panel.")
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--min-price", type=float, default=1.0)
    parser.add_argument("--research-liq-floor", type=float, default=0.0)
    parser.add_argument("--first-test-year", type=int, default=2020)
    parser.add_argument("--min-train-rows", type=int, default=100000)
    parser.add_argument("--max-train-rows", type=int, default=450000)
    parser.add_argument("--embargo-days", type=int, default=20)
    parser.add_argument("--ml-targets", default="touch5_3d,dd5_3d,ft_5_5")
    parser.add_argument("--lgbm-estimators", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-ml", action="store_true")
    parser.add_argument("--topn", default="5,10,20,50")
    parser.add_argument("--liquidity-floors", default="1000000,10000000,30000000,100000000")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    panel_path = Path(args.panel).expanduser()
    if not panel_path.exists():
        raise SystemExit(f"panel not found: {panel_path}")

    floors = [float(x) for x in str(args.liquidity_floors).split(",") if str(x).strip()]
    research_floor = float(args.research_liq_floor)
    if research_floor > 0:
        floors = sorted({float(f) for f in floors if float(f) >= research_floor} | {research_floor})
    topn_values = [int(x) for x in str(args.topn).split(",") if str(x).strip()]

    raw = _read_panel(panel_path)
    eligible = raw[
        raw["feature_ready"].eq(1)
        & raw["touch5_3d"].notna()
        & raw["ft_5_5"].notna()
        & raw["close"].ge(float(args.min_price))
        & raw["liq20"].ge(research_floor)
    ].copy()
    eligible = add_formula_scores(eligible)

    ml_folds: List[Dict[str, Any]] = []
    if not args.skip_ml:
        eligible, ml_folds = add_walk_forward_ml_scores(
            eligible,
            feature_cols=FEATURES,
            min_train_rows=int(args.min_train_rows),
            max_train_rows=int(args.max_train_rows),
            first_test_year=int(args.first_test_year),
            embargo_days=int(args.embargo_days),
            ml_targets=[x for x in str(args.ml_targets).split(",") if x.strip()],
            n_estimators=int(args.lgbm_estimators),
            seed=int(args.seed),
        )

    score_specs = [
        ScoreSpec("formula_vol_touch", "formula", "score_vol_touch"),
        ScoreSpec("formula_trend_momo", "formula", "score_trend_momo"),
        ScoreSpec("formula_breakout_volume", "formula", "score_breakout_volume"),
        ScoreSpec("formula_pullback_uptrend", "formula", "score_pullback_uptrend"),
        ScoreSpec("formula_volume_surge", "formula", "score_volume_surge"),
        ScoreSpec("formula_quality_lowvol_momo", "formula", "score_quality_lowvol_momo"),
        ScoreSpec("ml_touch5_3d", "walk_forward_ml", "ml_p_touch5_3d"),
        ScoreSpec("ml_ft55", "walk_forward_ml", "ml_p_ft_5_5"),
        ScoreSpec("ml_edge3", "walk_forward_ml", "ml_edge3"),
        ScoreSpec("ml_combo_touch_ft_risk", "walk_forward_ml", "ml_combo_touch_ft_risk"),
        ScoreSpec("ml_combo_5d_touch_ft_risk", "walk_forward_ml", "ml_combo_5d_touch_ft_risk"),
    ]
    all_results = evaluate_scores(
        eligible,
        score_specs=score_specs,
        liquidity_floors=floors,
        topn_values=topn_values,
    )
    top_candidates = sorted(all_results, key=lambda row: row.get("selection_key", -999), reverse=True)[:50]

    report = {
        "generated_at": _utc_now(),
        "panel_path": str(panel_path),
        "caveat": "Current-listed NASDAQ universe; not survivorship-free delisted history.",
        "rows_loaded": int(len(raw)),
        "rows_eligible_base": int(len(eligible)),
        "research_liq_floor": research_floor,
        "symbols_eligible_base": int(eligible["symbol"].nunique()),
        "date_min": str(eligible["date"].min().date()) if not eligible.empty else None,
        "date_max": str(eligible["date"].max().date()) if not eligible.empty else None,
        "features": FEATURES,
        "labels": LABELS,
        "liquidity_floors": floors,
        "topn_values": topn_values,
        "base_rates": _base_rates(eligible, floors),
        "ml_folds": ml_folds,
        "top_candidates": top_candidates,
        "all_results": all_results,
    }

    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"nasdaq_daily_edge_research_{stamp}.json"
    md_path = out_dir / f"nasdaq_daily_edge_research_{stamp}.md"
    _write_json(json_path, report)
    _write_md(md_path, report)
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "rows_eligible": report["rows_eligible_base"],
                "top_candidate": top_candidates[0] if top_candidates else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
