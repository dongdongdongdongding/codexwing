#!/usr/bin/env python3
"""Promotion-gated NASDAQ edge search.

This script is intentionally more aggressive than the first pass:
- train future liquidity-bucket excess returns directly
- include market-regime context features available at scan close
- rank top-N research policies by cost-adjusted OOS alpha
- fail closed unless both return quality and win-rate/touch quality clear gates
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.research_nasdaq_daily_edge import DEFAULT_PANEL, FEATURES, LABELS


DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"

PROMOTION_GATE_VERSION = "nasdaq_swing_win_return_gate_v1"
PROMOTION_GATE_THRESHOLDS: Dict[str, float] = {
    "min_n": 1000.0,
    "min_days": 250.0,
    "min_ret5_pct": 1.0,
    "min_alpha5_net_cost_0_2_pct": 0.50,
    "min_alpha5_net_cost_0_2_ci95_lo_pct": 0.0,
    "min_ret5_pos_rate": 0.55,
    "min_alpha5_net_cost_0_2_pos_rate": 0.55,
    "min_touch3": 0.55,
    "min_ft55": 0.55,
    "max_dd3": 0.35,
    "min_years_alpha5_net_0_2_pos": 5.0,
}

REGIME_GUARDS = {
    "all": lambda df: pd.Series(True, index=df.index),
    "avoid_deep_riskoff": lambda df: (df["mkt_ret20_mean"].ge(-5.0) & df["mkt_breadth5"].ge(0.35)),
    "risk_on": lambda df: (df["mkt_ret20_mean"].ge(0.0) & df["mkt_breadth5"].ge(0.45)),
}

ENTRY_GATES = {
    "none": lambda df: pd.Series(True, index=df.index),
    "pred_alpha5_ge_0_25": lambda df: df["pred_alpha5"].ge(0.25),
    "pred_alpha5_ge_0_50": lambda df: df["pred_alpha5"].ge(0.50),
    "pred_alpha5_ge_0_75": lambda df: df["pred_alpha5"].ge(0.75),
    "pred_alpha5_ge_1_00": lambda df: df["pred_alpha5"].ge(1.00),
    "pred_pos_ge_0_55": lambda df: df["pred_alpha5_pos"].ge(0.55),
    "pred_pos_ge_0_60": lambda df: df["pred_alpha5_pos"].ge(0.60),
    "pred_alpha5_ge_0_50_dd_le_0_45": lambda df: df["pred_alpha5"].ge(0.50) & df["pred_dd3"].le(0.45),
    "pred_alpha5_ge_0_75_dd_le_0_45": lambda df: df["pred_alpha5"].ge(0.75) & df["pred_dd3"].le(0.45),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _add_context_and_targets(df: pd.DataFrame, cost_pct: float) -> pd.DataFrame:
    work = df.copy()
    liq_rank = work.groupby("date")["liq20"].rank(pct=True, ascending=True)
    work["liq_decile"] = np.minimum(9, np.floor(liq_rank.fillna(0.0) * 10.0).astype(int))

    label_cols = ["fwd_close_ret_3d", "fwd_close_ret_5d", "touch5_3d", "touch5_5d", "dd5_3d", "ft_5_5"]
    liq_base = work.groupby(["date", "liq_decile"], observed=True)[label_cols].mean().add_prefix("base_liq_")
    day_base = work.groupby("date", observed=True)[label_cols].mean().add_prefix("base_day_")
    work = work.join(liq_base, on=["date", "liq_decile"])
    work = work.join(day_base, on="date")

    work["alpha3_liq"] = work["fwd_close_ret_3d"] - work["base_liq_fwd_close_ret_3d"]
    work["alpha5_liq"] = work["fwd_close_ret_5d"] - work["base_liq_fwd_close_ret_5d"]
    work["alpha3_day"] = work["fwd_close_ret_3d"] - work["base_day_fwd_close_ret_3d"]
    work["alpha5_day"] = work["fwd_close_ret_5d"] - work["base_day_fwd_close_ret_5d"]
    work["alpha5_net"] = work["alpha5_liq"] - float(cost_pct)
    work["alpha3_net"] = work["alpha3_liq"] - float(cost_pct)
    work["alpha5_net_pos"] = (work["alpha5_net"] > 0.0).astype(float).mask(work["alpha5_net"].isna(), np.nan)

    market = work.groupby("date", observed=True).agg(
        mkt_ret1_mean=("ret_1d", "mean"),
        mkt_ret5_mean=("ret_5d", "mean"),
        mkt_ret20_mean=("ret_20d", "mean"),
        mkt_ret60_mean=("ret_60d", "mean"),
        mkt_breadth1=("ret_1d", lambda s: float(pd.to_numeric(s, errors="coerce").gt(0).mean())),
        mkt_breadth5=("ret_5d", lambda s: float(pd.to_numeric(s, errors="coerce").gt(0).mean())),
        mkt_vol20_mean=("vol20", "mean"),
        mkt_atr_mean=("atr_pct", "mean"),
    )
    work = work.join(market, on="date")

    rank_features = [
        "ret_5d",
        "ret_20d",
        "ret_60d",
        "ma60_slope",
        "ma200_slope",
        "dist_hi20",
        "dist_hi120",
        "atr_pct",
        "vol20",
        "vol_ratio",
        "dollar_volume_ratio20",
        "rsi14",
        "bb_bw",
        "pos20",
    ]
    for col in rank_features:
        if col in work.columns:
            work[f"xrank_{col}"] = pd.to_numeric(work[col], errors="coerce").groupby(work["date"]).rank(pct=True)
    return work


def _sample_train(train: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    train = train.copy()
    if max_rows <= 0 or len(train) <= max_rows:
        return train
    return train.sample(n=max_rows, random_state=seed)


def _fit_regressor(train: pd.DataFrame, features: Sequence[str], target: str, seed: int, estimators: int):
    import lightgbm as lgb

    model = lgb.LGBMRegressor(
        objective="huber",
        n_estimators=int(estimators),
        learning_rate=0.035,
        num_leaves=31,
        max_depth=6,
        max_bin=127,
        min_child_samples=120,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.10,
        reg_lambda=0.35,
        force_col_wise=True,
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )
    x = train[list(features)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = pd.to_numeric(train[target], errors="coerce")
    model.fit(x, y)
    return model


def _fit_classifier(train: pd.DataFrame, features: Sequence[str], target: str, seed: int, estimators: int):
    import lightgbm as lgb

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=int(estimators),
        learning_rate=0.035,
        num_leaves=31,
        max_depth=6,
        max_bin=127,
        min_child_samples=120,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.10,
        reg_lambda=0.35,
        class_weight="balanced",
        force_col_wise=True,
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )
    x = train[list(features)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = pd.to_numeric(train[target], errors="coerce").astype(int)
    model.fit(x, y)
    return model


def _rank_by_date(df: pd.DataFrame, col: str, *, ascending: bool = True) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").groupby(df["date"]).rank(pct=True, ascending=ascending)


def _add_prediction_ranks(work: pd.DataFrame) -> pd.DataFrame:
    out = work.copy()
    rank_specs = [
        ("pred_alpha3", True),
        ("pred_alpha5", True),
        ("pred_alpha5_pos", True),
        ("pred_ft55", True),
        ("pred_dd3", False),
    ]
    for col, asc in rank_specs:
        if col in out.columns:
            out[f"rank_{col}"] = _rank_by_date(out, col, ascending=asc)
    out["score_alpha5"] = out.get("rank_pred_alpha5")
    out["score_alpha3"] = out.get("rank_pred_alpha3")
    out["score_prod_combo"] = (
        out.get("rank_pred_alpha5", 0) * 1.00
        + out.get("rank_pred_alpha3", 0) * 0.55
        + out.get("rank_pred_alpha5_pos", 0) * 0.65
        + out.get("rank_pred_ft55", 0) * 0.30
        + out.get("rank_pred_dd3", 0) * 0.75
    )
    out["score_prod_return_only"] = out.get("rank_pred_alpha5", 0) + out.get("rank_pred_alpha3", 0) * 0.50
    out["score_prod_path_safe"] = (
        out.get("rank_pred_alpha5", 0) * 0.70
        + out.get("rank_pred_alpha5_pos", 0) * 0.55
        + out.get("rank_pred_ft55", 0) * 0.45
        + out.get("rank_pred_dd3", 0) * 1.00
    )
    return out


def add_walk_forward_predictions(
    df: pd.DataFrame,
    *,
    features: Sequence[str],
    first_test_year: int,
    embargo_days: int,
    max_train_rows: int,
    min_train_rows: int,
    estimators: int,
    seed: int,
) -> tuple[pd.DataFrame, List[Dict[str, Any]]]:
    work = df.copy()
    pred_cols = ["pred_alpha3", "pred_alpha5", "pred_alpha5_pos", "pred_ft55", "pred_dd3"]
    for col in pred_cols:
        work[col] = np.nan
    folds: List[Dict[str, Any]] = []
    years = sorted(int(y) for y in work["year"].dropna().unique() if int(y) >= int(first_test_year))
    for year in years:
        test_start = pd.Timestamp(year=year, month=1, day=1)
        train = work[work["date"] < test_start - timedelta(days=int(embargo_days))].copy()
        test_idx = work.index[work["year"].eq(year)]
        if len(train) < min_train_rows or len(test_idx) == 0:
            continue
        x_test = work.loc[test_idx, list(features)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        fold: Dict[str, Any] = {"year": int(year), "train_available": int(len(train)), "test_rows": int(len(test_idx))}
        targets = [
            ("reg", "alpha3_liq", "pred_alpha3"),
            ("reg", "alpha5_liq", "pred_alpha5"),
            ("clf", "alpha5_net_pos", "pred_alpha5_pos"),
            ("clf", "ft_5_5", "pred_ft55"),
            ("clf", "dd5_3d", "pred_dd3"),
        ]
        for offset, (kind, target, out_col) in enumerate(targets):
            train_target = train[train[target].notna()].copy()
            if len(train_target) < min_train_rows:
                continue
            sampled = _sample_train(train_target, max_train_rows, seed + year * 37 + offset)
            print(f"[WF] year={year} target={target} kind={kind} train={len(sampled)} test={len(test_idx)}")
            if kind == "reg":
                model = _fit_regressor(sampled, features, target, seed + year * 101 + offset, estimators)
                pred = model.predict(x_test)
                fold[target] = {
                    "train_rows": int(len(sampled)),
                    "target_mean": round(float(sampled[target].mean()), 6),
                    "pred_mean": round(float(np.nanmean(pred)), 6),
                }
            else:
                model = _fit_classifier(sampled, features, target, seed + year * 101 + offset, estimators)
                pred = model.predict_proba(x_test)[:, 1]
                fold[target] = {
                    "train_rows": int(len(sampled)),
                    "target_mean": round(float(sampled[target].mean()), 6),
                    "pred_mean": round(float(np.nanmean(pred)), 6),
                }
            work.loc[test_idx, out_col] = pred
        folds.append(fold)
    work = _add_prediction_ranks(work)
    return work, folds


def _mean_ci(series: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float]]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None, None, None
    mean = float(clean.mean())
    if len(clean) < 2:
        return mean, None, None
    se = float(clean.std(ddof=1) / math.sqrt(len(clean)))
    return mean, mean - 1.96 * se, mean + 1.96 * se


def _positive_rate(series: pd.Series) -> Optional[float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return float(clean.gt(0.0).mean())


def evaluate_nasdaq_promotion_gate(
    metrics: Mapping[str, Any],
    *,
    thresholds: Mapping[str, float] = PROMOTION_GATE_THRESHOLDS,
) -> Dict[str, Any]:
    """Fail-closed gate: positive alpha alone is not enough for promotion."""
    blocking: List[str] = []

    def _number(key: str) -> Optional[float]:
        value = metrics.get(key)
        try:
            if value is None:
                return None
            out = float(value)
            if math.isnan(out) or math.isinf(out):
                return None
            return out
        except Exception:
            return None

    def _require_min(key: str, threshold_key: str) -> None:
        value = _number(key)
        minimum = float(thresholds[threshold_key])
        if value is None:
            blocking.append(f"missing_{key}")
        elif value < minimum:
            blocking.append(f"{key}_below_min:{value:.6g}<{minimum:.6g}")

    def _require_max(key: str, threshold_key: str) -> None:
        value = _number(key)
        maximum = float(thresholds[threshold_key])
        if value is None:
            blocking.append(f"missing_{key}")
        elif value > maximum:
            blocking.append(f"{key}_above_max:{value:.6g}>{maximum:.6g}")

    _require_min("n", "min_n")
    _require_min("days", "min_days")
    _require_min("ret5", "min_ret5_pct")
    _require_min("alpha5_net_cost_0_2", "min_alpha5_net_cost_0_2_pct")
    ci = metrics.get("alpha5_net_cost_0_2_ci95")
    ci_lo = ci[0] if isinstance(ci, list) and ci else None
    if ci_lo is None:
        blocking.append("missing_alpha5_net_cost_0_2_ci95_lo")
    else:
        try:
            ci_lo_f = float(ci_lo)
        except Exception:
            ci_lo_f = math.nan
        threshold = float(thresholds["min_alpha5_net_cost_0_2_ci95_lo_pct"])
        if math.isnan(ci_lo_f) or ci_lo_f < threshold:
            blocking.append(f"alpha5_net_cost_0_2_ci95_lo_below_min:{ci_lo_f:.6g}<{threshold:.6g}")
    _require_min("ret5_pos_rate", "min_ret5_pos_rate")
    _require_min("alpha5_net_cost_0_2_pos_rate", "min_alpha5_net_cost_0_2_pos_rate")
    _require_min("touch3", "min_touch3")
    _require_min("ft55", "min_ft55")
    _require_max("dd3", "max_dd3")
    _require_min("years_alpha5_net_0_2_pos", "min_years_alpha5_net_0_2_pos")

    ready = not blocking
    return {
        "gate_version": PROMOTION_GATE_VERSION,
        "promotion_ready": ready,
        "status": "promotion_ready" if ready else "research_shadow_only_win_return_gate_blocked",
        "capital_status": (
            "promotion_ready_pending_forward_capital_review"
            if ready
            else "research_shadow_only_win_return_gate_blocked"
        ),
        "blocking_reasons": blocking,
        "thresholds": {key: float(value) for key, value in thresholds.items()},
    }


def _metric_block(picks: pd.DataFrame, *, costs: Sequence[float]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"n": int(len(picks)), "days": int(picks["date"].nunique())}
    if picks.empty:
        return out
    out["symbols"] = int(picks["symbol"].nunique())
    out["median_liq20"] = round(float(picks["liq20"].median()), 2)
    for col, name in [
        ("fwd_close_ret_3d", "ret3"),
        ("fwd_close_ret_5d", "ret5"),
        ("alpha3_liq", "alpha3"),
        ("alpha5_liq", "alpha5"),
        ("touch5_3d", "touch3"),
        ("ft_5_5", "ft55"),
        ("dd5_3d", "dd3"),
    ]:
        vals = pd.to_numeric(picks[col], errors="coerce")
        out[name] = round(float(vals.mean()), 6) if vals.notna().any() else None
        mean, lo, hi = _mean_ci(vals)
        out[f"{name}_ci95"] = [None if lo is None else round(lo, 6), None if hi is None else round(hi, 6)]
        if name in {"ret3", "ret5", "alpha3", "alpha5"}:
            rate = _positive_rate(vals)
            out[f"{name}_pos_rate"] = None if rate is None else round(rate, 6)
    for cost in costs:
        net = pd.to_numeric(picks["alpha5_liq"], errors="coerce") - float(cost)
        mean, lo, hi = _mean_ci(net)
        key = f"alpha5_net_cost_{str(cost).replace('.', '_')}"
        out[key] = None if mean is None else round(mean, 6)
        out[f"{key}_ci95"] = [None if lo is None else round(lo, 6), None if hi is None else round(hi, 6)]
        rate = _positive_rate(net)
        out[f"{key}_pos_rate"] = None if rate is None else round(rate, 6)
    annual = []
    for year, grp in picks.groupby("year", observed=True):
        item = {"year": int(year), "n": int(len(grp)), "days": int(grp["date"].nunique())}
        for col, name in [("alpha3_liq", "alpha3"), ("alpha5_liq", "alpha5"), ("fwd_close_ret_5d", "ret5"), ("touch5_3d", "touch3"), ("ft_5_5", "ft55"), ("dd5_3d", "dd3")]:
            vals = pd.to_numeric(grp[col], errors="coerce")
            item[name] = round(float(vals.mean()), 6) if vals.notna().any() else None
            if name in {"ret5", "alpha5"}:
                rate = _positive_rate(vals)
                item[f"{name}_pos_rate"] = None if rate is None else round(rate, 6)
        for cost in costs:
            net = pd.to_numeric(grp["alpha5_liq"], errors="coerce") - float(cost)
            key = f"alpha5_net_{str(cost).replace('.', '_')}"
            item[key] = round(float(net.mean()), 6)
            rate = _positive_rate(net)
            item[f"{key}_pos_rate"] = None if rate is None else round(rate, 6)
        annual.append(item)
    out["annual"] = annual
    out["years_alpha5_pos"] = int(sum((item.get("alpha5") or 0.0) > 0 for item in annual))
    for cost in costs:
        key = f"alpha5_net_{str(cost).replace('.', '_')}"
        out[f"years_{key}_pos"] = int(sum((item.get(key) or 0.0) > 0 for item in annual))
    return out


def evaluate_policies(
    df: pd.DataFrame,
    *,
    score_cols: Sequence[str],
    floors: Sequence[float],
    topn_values: Sequence[int],
    costs: Sequence[float],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for guard_name, guard_fn in REGIME_GUARDS.items():
        guarded = df.loc[guard_fn(df)].copy()
        if guarded.empty:
            continue
        for gate_name, gate_fn in ENTRY_GATES.items():
            gated = guarded.loc[gate_fn(guarded)].copy()
            if gated.empty:
                continue
            for floor in floors:
                pool = gated[gated["liq20"].ge(float(floor))]
                if pool.empty:
                    continue
                for score_col in score_cols:
                    if score_col not in pool.columns:
                        continue
                    score = pd.to_numeric(pool[score_col], errors="coerce")
                    valid = score.notna()
                    if not bool(valid.any()):
                        continue
                    rank = score.loc[valid].groupby(pool.loc[valid, "date"], observed=True).rank(method="first", ascending=False)
                    for topn in topn_values:
                        picks = pool.loc[rank[rank.le(int(topn))].index]
                        if len(picks) < 250:
                            continue
                        metrics = _metric_block(picks, costs=costs)
                        metrics.update(
                            {
                                "guard": guard_name,
                                "entry_gate": gate_name,
                                "liq20_floor": float(floor),
                                "score": score_col,
                                "topn": int(topn),
                            }
                        )
                        metrics["promotion_gate"] = evaluate_nasdaq_promotion_gate(metrics)
                        metrics["promotion_ready"] = bool(metrics["promotion_gate"]["promotion_ready"])
                        metrics["promotion_blocking_reasons"] = list(metrics["promotion_gate"]["blocking_reasons"])
                        metrics["selection_key"] = _selection_key(metrics)
                        rows.append(metrics)
    return sorted(rows, key=lambda r: r.get("selection_key", -999), reverse=True)


def _selection_key(row: Mapping[str, Any]) -> float:
    alpha5 = float(row.get("alpha5") or 0.0)
    alpha3 = float(row.get("alpha3") or 0.0)
    net02 = float(row.get("alpha5_net_cost_0_2") or 0.0)
    touch = float(row.get("touch3") or 0.0)
    dd = float(row.get("dd3") or 0.0)
    years = float(row.get("years_alpha5_net_0_2_pos") or 0.0)
    total_years = max(1.0, float(len(row.get("annual") or [])))
    return round(alpha5 + 0.5 * alpha3 + net02 + (touch - dd) + 0.35 * (years / total_years), 6)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_md(path: Path, report: Mapping[str, Any]) -> None:
    def _fmt_rate(value: Any) -> str:
        try:
            if value is None:
                return "-"
            return f"{float(value):.2%}"
        except Exception:
            return "-"

    lines = [
        "# NASDAQ Promotion-Gated Edge Search",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- panel_path: `{report.get('panel_path')}`",
        f"- rows_eligible: `{report.get('rows_eligible')}`",
        f"- symbols_eligible: `{report.get('symbols_eligible')}`",
        f"- date_range: `{report.get('date_min')}` ~ `{report.get('date_max')}`",
        f"- research_liq_floor: `{report.get('research_liq_floor')}`",
        f"- cost_grid_pct: `{report.get('costs_pct')}`",
        "",
        "## Best Policies",
        "",
    ]
    for row in report.get("top_policies", [])[:25]:
        lines.append(
            f"- `{row['score']}` guard `{row['guard']}` gate `{row.get('entry_gate', 'none')}` "
            f"floor `{row['liq20_floor']:,.0f}` top{row['topn']} "
            f"n `{row['n']}` alpha5 `{row.get('alpha5', 0):+.3f}%` "
            f"net@0.2 `{row.get('alpha5_net_cost_0_2', 0):+.3f}%` "
            f"ret5_pos `{_fmt_rate(row.get('ret5_pos_rate'))}` "
            f"net_pos `{_fmt_rate(row.get('alpha5_net_cost_0_2_pos_rate'))}` "
            f"alpha3 `{row.get('alpha3', 0):+.3f}%` touch3 `{row.get('touch3', 0):.2%}` "
            f"ft55 `{row.get('ft55', 0):.2%}` "
            f"dd3 `{row.get('dd3', 0):.2%}` years_net_pos `{row.get('years_alpha5_net_0_2_pos')}/{len(row.get('annual') or [])}`"
            f" gate `{'PASS' if row.get('promotion_ready') else 'BLOCK'}`"
        )
        reasons = row.get("promotion_blocking_reasons") or []
        if reasons:
            lines.append(f"  - promotion_blocking_reasons: `{', '.join(str(reason) for reason in reasons[:8])}`")
    lines.extend(["", "## Fold Summary", ""])
    for fold in report.get("folds", []):
        lines.append(
            f"- `{fold.get('year')}` train `{fold.get('train_available')}` test `{fold.get('test_rows')}` "
            f"alpha5_mean `{(fold.get('alpha5_liq') or {}).get('target_mean')}`"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search promotion-gated NASDAQ daily edge.")
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--min-price", type=float, default=1.0)
    parser.add_argument("--research-liq-floor", type=float, default=10_000_000.0)
    parser.add_argument("--first-test-year", type=int, default=2020)
    parser.add_argument("--embargo-days", type=int, default=20)
    parser.add_argument("--min-train-rows", type=int, default=100_000)
    parser.add_argument("--max-train-rows", type=int, default=160_000)
    parser.add_argument("--lgbm-estimators", type=int, default=110)
    parser.add_argument("--liquidity-floors", default="30000000,100000000")
    parser.add_argument("--topn", default="1,2,3,5,10")
    parser.add_argument("--costs", default="0.1,0.2,0.35")
    parser.add_argument("--seed", type=int, default=20260629)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    panel_path = Path(args.panel).expanduser()
    raw = _read_panel(panel_path)
    eligible = raw[
        raw["feature_ready"].eq(1)
        & raw["close"].ge(float(args.min_price))
        & raw["liq20"].ge(float(args.research_liq_floor))
        & raw["fwd_close_ret_5d"].notna()
        & raw["touch5_3d"].notna()
        & raw["ft_5_5"].notna()
    ].copy()
    eligible = _add_context_and_targets(eligible, cost_pct=0.2)
    model_features = [
        col
        for col in FEATURES
        + [
            "mkt_ret1_mean",
            "mkt_ret5_mean",
            "mkt_ret20_mean",
            "mkt_ret60_mean",
            "mkt_breadth1",
            "mkt_breadth5",
            "mkt_vol20_mean",
            "mkt_atr_mean",
        ]
        + [c for c in eligible.columns if c.startswith("xrank_")]
        if col in eligible.columns
    ]
    scored, folds = add_walk_forward_predictions(
        eligible,
        features=model_features,
        first_test_year=int(args.first_test_year),
        embargo_days=int(args.embargo_days),
        max_train_rows=int(args.max_train_rows),
        min_train_rows=int(args.min_train_rows),
        estimators=int(args.lgbm_estimators),
        seed=int(args.seed),
    )
    floors = [float(x) for x in str(args.liquidity_floors).split(",") if x.strip()]
    floors = sorted({float(f) for f in floors if float(f) >= float(args.research_liq_floor)})
    topn_values = [int(x) for x in str(args.topn).split(",") if x.strip()]
    costs = [float(x) for x in str(args.costs).split(",") if x.strip()]
    score_cols = ["score_prod_combo", "score_prod_return_only", "score_prod_path_safe", "score_alpha5", "score_alpha3"]
    policies = evaluate_policies(scored, score_cols=score_cols, floors=floors, topn_values=topn_values, costs=costs)

    report = {
        "generated_at": _utc_now(),
        "panel_path": str(panel_path),
        "gate_version": PROMOTION_GATE_VERSION,
        "promotion_gate_thresholds": dict(PROMOTION_GATE_THRESHOLDS),
        "caveat": "Research search only; capital promotion requires the win-rate, touch, drawdown, return, and forward-shadow gates.",
        "rows_loaded": int(len(raw)),
        "rows_eligible": int(len(eligible)),
        "symbols_eligible": int(eligible["symbol"].nunique()),
        "date_min": str(eligible["date"].min().date()) if not eligible.empty else None,
        "date_max": str(eligible["date"].max().date()) if not eligible.empty else None,
        "research_liq_floor": float(args.research_liq_floor),
        "features": model_features,
        "costs_pct": costs,
        "folds": folds,
        "top_policies": policies[:100],
        "all_policy_count": int(len(policies)),
    }
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"nasdaq_production_edge_search_{stamp}.json"
    md_path = out_dir / f"nasdaq_production_edge_search_{stamp}.md"
    _write_json(json_path, report)
    _write_md(md_path, report)
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "rows_eligible": report["rows_eligible"],
                "top_policy": policies[0] if policies else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
