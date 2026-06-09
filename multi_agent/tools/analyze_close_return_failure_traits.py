#!/usr/bin/env python3
"""Analyze traits behind bad 5D close returns after target-touch setups.

The operational admission gate now treats a +5% intraperiod high touch as the
primary win signal. This report deliberately studies the opposite question:
which pre-scan traits repeatedly touch +5% but still finish with a bad close
after the production +2% buy-premium assumption?
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from modules.operational_candidate_scoring import (  # noqa: E402
    DEFAULT_BUY_PREMIUM_PCT,
    adjust_return_for_buy_premium,
)


REPORT_VERSION = "close_return_failure_traits_v1"
DEFAULT_PREPARED_CACHE = Path(
    "runtime_state/reports/learning/"
    "scan_universe_admission_challenger_buy_premium_v2_idscan_20260401_20260528.pkl"
)
DEFAULT_OUTPUT = Path("runtime_state/reports/learning/close_return_failure_traits_20260401_20260528.json")

TARGET_TOUCH_PCT = 5.0
EXTENDED_TOUCH_PCT = 10.0
STOP_PCT = -5.0
EARLY_WEAK_CLOSE_1D_PCT = -3.0

OUTCOME_COLUMNS = {
    "return_1d_pct",
    "return_2d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "return_14d_pct",
    "return_30d_pct",
    "max_high_return_1d_pct",
    "max_high_return_2d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
    "max_high_return_7d_pct",
    "min_low_return_1d_pct",
    "min_low_return_2d_pct",
    "min_low_return_3d_pct",
    "min_low_return_5d_pct",
    "min_low_return_7d_pct",
    "latest_return_pct",
    "return_close_pct",
    "bad_path",
    "stop5_proxy",
}

OUTCOME_PREFIXES = (
    "_adj_",
    "buy_premium_return_",
    "buy_premium_max_high_return_",
    "buy_premium_min_low_return_",
    "target_before_stop_",
    "stop_before_target_",
    "first_touch_",
    "target_touch_",
    "target_hit_",
    "hit5_",
    "hit10_",
    "ordered_path_",
)

IDENTITY_COLUMNS = {
    "id",
    "run_id",
    "ticker",
    "symbol",
    "stock_name",
    "name",
    "base_trade_date",
    "trade_date",
    "scanned_at",
    "created_at",
    "updated_at",
    "source_ref",
    "artifact_path",
}

NUMERIC_FEATURE_HINTS = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "priority_rank",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "feature_coverage_score",
    "entry_reference_price",
    "total_scans",
    "filtered_count",
    "kis_value_traded",
    "kis_prev_volume_ratio",
    "kis_whale_score",
    "kis_daily_return_5d_pct",
    "kis_daily_return_20d_pct",
    "kis_daily_return_60d_pct",
    "kis_daily_volume_ratio_20d",
    "kis_daily_close_location_pct",
    "kis_daily_pct_from_52w_high",
    "kis_daily_pct_from_52w_low",
    "kis_market_cap",
    "kis_per",
    "kis_pbr",
    "kis_eps",
    "kis_bps",
    "kis_foreigner_ratio",
    "kis_news_title_count",
    "kis_theme_news_positive_count",
    "kis_theme_news_risk_count",
    "kis_theme_news_title_count",
    "theme_confidence",
    "valuechain_confidence",
    "valuechain_source_count",
]

CATEGORICAL_FEATURE_HINTS = [
    "market",
    "market_subtype",
    "row_role",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "has_actual_flow",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
    "market_gate",
    "kis_stock_market_code",
    "kis_stock_market_name",
    "kis_stock_type",
    "kis_stock_sector_name",
    "kis_stock_standard_industry_code",
    "kis_stock_kospi200_item",
    "kis_stock_trade_stop",
    "kis_stock_admin_item",
    "kis_theme_news_level",
    "kis_theme_news_primary_theme",
    "kis_theme_news_kis_sector_name",
    "kis_theme_news_source_scope",
    "kis_theme_news_top_positive_tag",
    "kis_theme_news_top_risk_tag",
    "valuechain_primary_node",
    "valuechain_primary_role",
    "valuechain_cluster",
]


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def _pct(value: Any) -> float | None:
    number = _round(value, 8)
    return round(number * 100.0, 4) if number is not None else None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    clean = series.astype("object").where(series.notna(), "")
    return clean.astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def _premium_col(column: str) -> str:
    return f"buy_premium_{column}"


def _adjusted_return_series(df: pd.DataFrame, column: str, *, buy_premium_pct: float) -> pd.Series:
    premium_col = _premium_col(column)
    if premium_col in df.columns:
        return pd.to_numeric(df[premium_col], errors="coerce")
    raw = _numeric_series(df, column)
    return raw.map(lambda value: adjust_return_for_buy_premium(value, buy_premium_pct))


def _cohens_d(left: pd.Series, right: pd.Series) -> float | None:
    x = pd.to_numeric(left, errors="coerce").dropna().to_numpy(dtype=float)
    y = pd.to_numeric(right, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) < 2 or len(y) < 2:
        return None
    vx = float(np.nanvar(x, ddof=1))
    vy = float(np.nanvar(y, ddof=1))
    pooled = math.sqrt(((len(x) - 1) * vx + (len(y) - 1) * vy) / max(len(x) + len(y) - 2, 1))
    if not math.isfinite(pooled) or pooled == 0.0:
        return None
    return (float(np.nanmean(x)) - float(np.nanmean(y))) / pooled


def _is_outcome_column(column: str) -> bool:
    if column in OUTCOME_COLUMNS:
        return True
    return any(column.startswith(prefix) for prefix in OUTCOME_PREFIXES)


def _append_unique(items: List[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _clean_category(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return "UNKNOWN"
    return text[:120]


def prepare_failure_frame(
    df: pd.DataFrame,
    *,
    buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT,
    target_pct: float = TARGET_TOUCH_PCT,
    extended_target_pct: float = EXTENDED_TOUCH_PCT,
    stop_pct: float = STOP_PCT,
    early_weak_1d_pct: float = EARLY_WEAK_CLOSE_1D_PCT,
) -> pd.DataFrame:
    out = df.copy()
    out["_adj_return_1d_pct"] = _adjusted_return_series(out, "return_1d_pct", buy_premium_pct=buy_premium_pct)
    out["_adj_return_3d_pct"] = _adjusted_return_series(out, "return_3d_pct", buy_premium_pct=buy_premium_pct)
    out["_adj_return_5d_pct"] = _adjusted_return_series(out, "return_5d_pct", buy_premium_pct=buy_premium_pct)
    out["_adj_max_high_return_5d_pct"] = _adjusted_return_series(
        out, "max_high_return_5d_pct", buy_premium_pct=buy_premium_pct
    )
    out["_adj_min_low_return_5d_pct"] = _adjusted_return_series(
        out, "min_low_return_5d_pct", buy_premium_pct=buy_premium_pct
    )

    if "target_before_stop_5d" in out.columns:
        ordered_target = _bool_series(out["target_before_stop_5d"])
    else:
        ordered_target = pd.Series(False, index=out.index)
    if "stop_before_target_5d" in out.columns:
        ordered_stop = _bool_series(out["stop_before_target_5d"])
    elif "stop_before_target_5d_bool" in out.columns:
        ordered_stop = _bool_series(out["stop_before_target_5d_bool"])
    else:
        ordered_stop = pd.Series(False, index=out.index)

    out["_touch5_5d_bool"] = out["_adj_max_high_return_5d_pct"].ge(target_pct).fillna(False)
    out["_touch10_5d_bool"] = out["_adj_max_high_return_5d_pct"].ge(extended_target_pct).fillna(False)
    out["_close_loss_5d_bool"] = out["_adj_return_5d_pct"].lt(0.0).fillna(False)
    out["_close_defense_5d_bool"] = out["_adj_return_5d_pct"].gt(0.0).fillna(False)
    out["_stop5_5d_bool"] = ordered_stop | out["_adj_min_low_return_5d_pct"].le(stop_pct).fillna(False)
    out["_early_weak_1d_bool"] = out["_adj_return_1d_pct"].lt(early_weak_1d_pct).fillna(False)
    out["_target_before_stop_5d_bool"] = ordered_target & out["_touch5_5d_bool"]
    out["_bad_path_5d_bool"] = out["_stop5_5d_bool"] | out["_early_weak_1d_bool"] | out["_close_loss_5d_bool"]
    out["_touch5_close_loss_bool"] = out["_touch5_5d_bool"] & out["_close_loss_5d_bool"]
    out["_touch5_close_defense_bool"] = out["_touch5_5d_bool"] & out["_close_defense_5d_bool"]
    out["_clean_touch5_close_defense_bool"] = (
        out["_touch5_close_defense_bool"] & ~out["_stop5_5d_bool"] & ~out["_early_weak_1d_bool"]
    )
    out["_no_touch_close_loss_bool"] = ~out["_touch5_5d_bool"] & out["_close_loss_5d_bool"]
    out["_operational_buy_premium_pct"] = float(buy_premium_pct)
    return out


def _active_base_mask(df: pd.DataFrame) -> pd.Series:
    ret_known = df["_adj_return_5d_pct"].notna()
    mfe_known = df["_adj_max_high_return_5d_pct"].notna()
    return ret_known & mfe_known & df["_touch5_5d_bool"]


def _summary_metrics(df: pd.DataFrame, mask: pd.Series) -> Dict[str, Any]:
    sub = df.loc[mask].copy()
    if sub.empty:
        return {
            "n": 0,
            "active_days": 0,
            "active_runs": 0,
        }
    date_col = "trade_date" if "trade_date" in sub.columns else "base_trade_date"
    return {
        "n": int(len(sub)),
        "active_days": int(sub[date_col].nunique()) if date_col in sub.columns else 0,
        "active_runs": int(sub["run_id"].nunique()) if "run_id" in sub.columns else 0,
        "touch5_5d_pct": _pct(sub["_touch5_5d_bool"].mean()),
        "touch10_5d_pct": _pct(sub["_touch10_5d_bool"].mean()),
        "touch5_close_loss_pct": _pct(sub["_touch5_close_loss_bool"].mean()),
        "touch5_close_defense_pct": _pct(sub["_touch5_close_defense_bool"].mean()),
        "clean_touch5_close_defense_pct": _pct(sub["_clean_touch5_close_defense_bool"].mean()),
        "stop5_5d_pct": _pct(sub["_stop5_5d_bool"].mean()),
        "bad_path_5d_pct": _pct(sub["_bad_path_5d_bool"].mean()),
        "avg_close_5d_pct": _round(sub["_adj_return_5d_pct"].mean()),
        "median_close_5d_pct": _round(sub["_adj_return_5d_pct"].median()),
        "avg_mfe_5d_pct": _round(sub["_adj_max_high_return_5d_pct"].mean()),
        "avg_mae_5d_pct": _round(sub["_adj_min_low_return_5d_pct"].mean()),
        "min_close_5d_pct": _round(sub["_adj_return_5d_pct"].min()),
        "min_mae_5d_pct": _round(sub["_adj_min_low_return_5d_pct"].min()),
    }


def _cohort_overview(df: pd.DataFrame) -> Dict[str, Any]:
    cohorts = {
        "all_resolved": df["_adj_return_5d_pct"].notna() & df["_adj_max_high_return_5d_pct"].notna(),
        "touch5_base": _active_base_mask(df),
        "touch5_close_loss": df["_touch5_close_loss_bool"],
        "touch5_close_defense": df["_touch5_close_defense_bool"],
        "clean_touch5_close_defense": df["_clean_touch5_close_defense_bool"],
        "no_touch_close_loss": df["_no_touch_close_loss_bool"],
    }
    out = {name: _summary_metrics(df, mask) for name, mask in cohorts.items()}
    touch_base = cohorts["touch5_base"]
    if touch_base.any():
        out["conditional_rates"] = {
            "close_loss_given_touch5_pct": _pct(df.loc[touch_base, "_close_loss_5d_bool"].mean()),
            "close_defense_given_touch5_pct": _pct(df.loc[touch_base, "_close_defense_5d_bool"].mean()),
            "stop5_given_touch5_pct": _pct(df.loc[touch_base, "_stop5_5d_bool"].mean()),
            "bad_path_given_touch5_pct": _pct(df.loc[touch_base, "_bad_path_5d_bool"].mean()),
            "touch10_given_touch5_pct": _pct(df.loc[touch_base, "_touch10_5d_bool"].mean()),
        }
    else:
        out["conditional_rates"] = {}
    return out


def _market_overview(df: pd.DataFrame) -> Dict[str, Any]:
    if "market" not in df.columns:
        return {}
    markets: Dict[str, Any] = {}
    for market in sorted(df["market"].fillna("UNKNOWN").astype(str).unique()):
        sub = df[df["market"].fillna("UNKNOWN").astype(str) == market]
        markets[market] = _cohort_overview(sub)
    return markets


def _numeric_feature_candidates(df: pd.DataFrame, *, min_non_null: int) -> List[str]:
    features: List[str] = []
    for column in NUMERIC_FEATURE_HINTS:
        if column in df.columns and not _is_outcome_column(column):
            values = pd.to_numeric(df[column], errors="coerce")
            if int(values.notna().sum()) >= min_non_null:
                _append_unique(features, column)
    for column in df.columns:
        if column in features or column in IDENTITY_COLUMNS or _is_outcome_column(column):
            continue
        if column.startswith("_"):
            continue
        if column.startswith(("kis_", "theme_", "valuechain_", "profile_", "scanner_", "market_gate_")):
            values = pd.to_numeric(df[column], errors="coerce")
            if int(values.notna().sum()) >= min_non_null:
                _append_unique(features, column)
    return features


def _categorical_feature_candidates(
    df: pd.DataFrame,
    *,
    min_non_null: int,
    max_cardinality: int,
) -> List[str]:
    features: List[str] = []
    for column in CATEGORICAL_FEATURE_HINTS:
        if column in df.columns and column not in IDENTITY_COLUMNS and not _is_outcome_column(column):
            series = df[column]
            if int(series.notna().sum()) >= min_non_null and int(series.astype(str).nunique(dropna=True)) <= max_cardinality:
                _append_unique(features, column)
    for column in df.columns:
        if column in features or column in IDENTITY_COLUMNS or _is_outcome_column(column):
            continue
        if column.startswith("_"):
            continue
        series = df[column]
        if series.dtype.kind not in ("O", "b", "U", "S", "c"):
            continue
        if int(series.notna().sum()) < min_non_null:
            continue
        if int(series.astype(str).nunique(dropna=True)) > max_cardinality:
            continue
        _append_unique(features, column)
    return features


def _failure_rate_by_numeric_bins(values: pd.Series, failure: pd.Series, *, min_support: int) -> List[Dict[str, Any]]:
    frame = pd.DataFrame({"value": pd.to_numeric(values, errors="coerce"), "failure": failure.astype(bool)}).dropna()
    if len(frame) < max(min_support * 3, 6):
        return []
    try:
        frame["bin"] = pd.qcut(frame["value"], q=3, duplicates="drop")
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for interval, sub in frame.groupby("bin", observed=True):
        if len(sub) < min_support:
            continue
        rows.append(
            {
                "bin": str(interval),
                "n": int(len(sub)),
                "min": _round(sub["value"].min()),
                "max": _round(sub["value"].max()),
                "failure_rate_pct": _pct(sub["failure"].mean()),
                "failure_count": int(sub["failure"].sum()),
            }
        )
    return rows


def _top_numeric_traits(
    df: pd.DataFrame,
    *,
    base_mask: pd.Series,
    failure_mask: pd.Series,
    control_mask: pd.Series,
    min_support: int,
    max_traits: int,
) -> List[Dict[str, Any]]:
    features = _numeric_feature_candidates(df.loc[base_mask], min_non_null=min_support)
    rows: List[Dict[str, Any]] = []
    base_failure_rate = float(failure_mask.loc[base_mask].mean()) if int(base_mask.sum()) else 0.0
    for feature in features:
        failure_values = pd.to_numeric(df.loc[failure_mask, feature], errors="coerce").dropna()
        control_values = pd.to_numeric(df.loc[control_mask, feature], errors="coerce").dropna()
        if len(failure_values) < min_support or len(control_values) < min_support:
            continue
        d_value = _cohens_d(failure_values, control_values)
        bins = _failure_rate_by_numeric_bins(df.loc[base_mask, feature], failure_mask.loc[base_mask], min_support=min_support)
        worst_bin = None
        if bins:
            worst_bin = max(bins, key=lambda item: _safe_float(item.get("failure_rate_pct"), -1.0) or -1.0)
        worst_rate = _safe_float((worst_bin or {}).get("failure_rate_pct"), None)
        lift = (worst_rate / 100.0 / base_failure_rate) if worst_rate is not None and base_failure_rate > 0 else None
        missing_failure = df.loc[failure_mask, feature].isna().mean()
        missing_control = df.loc[control_mask, feature].isna().mean()
        score = abs(float(d_value or 0.0)) * 2.0
        if lift is not None:
            score += abs(lift - 1.0)
        score += abs(float(missing_failure - missing_control))
        rows.append(
            {
                "feature": feature,
                "n_failure": int(len(failure_values)),
                "n_control": int(len(control_values)),
                "failure_mean": _round(failure_values.mean()),
                "control_mean": _round(control_values.mean()),
                "failure_median": _round(failure_values.median()),
                "control_median": _round(control_values.median()),
                "delta_mean_failure_minus_control": _round(failure_values.mean() - control_values.mean()),
                "cohens_d_failure_vs_control": _round(d_value, 6),
                "missing_failure_pct": _pct(missing_failure),
                "missing_control_pct": _pct(missing_control),
                "worst_bin": worst_bin,
                "worst_bin_failure_lift": _round(lift, 4),
                "bins": bins,
                "direction": "higher_in_failures"
                if (d_value or 0.0) > 0
                else "lower_in_failures"
                if (d_value or 0.0) < 0
                else "similar",
                "trait_score": _round(score, 6),
            }
        )
    rows.sort(
        key=lambda item: (
            _safe_float(item.get("trait_score"), 0.0) or 0.0,
            abs(_safe_float(item.get("cohens_d_failure_vs_control"), 0.0) or 0.0),
            int(item.get("n_failure") or 0),
        ),
        reverse=True,
    )
    return rows[:max_traits]


def _categorical_rows_for_feature(
    df: pd.DataFrame,
    feature: str,
    *,
    base_mask: pd.Series,
    failure_mask: pd.Series,
    min_support: int,
) -> List[Dict[str, Any]]:
    base = df.loc[base_mask, [feature]].copy()
    if base.empty:
        return []
    base["category"] = base[feature].map(_clean_category)
    base["failure"] = failure_mask.loc[base.index].astype(bool).values
    base["close5"] = df.loc[base.index, "_adj_return_5d_pct"].values
    base["mfe5"] = df.loc[base.index, "_adj_max_high_return_5d_pct"].values
    base["mae5"] = df.loc[base.index, "_adj_min_low_return_5d_pct"].values
    base["touch10"] = df.loc[base.index, "_touch10_5d_bool"].astype(bool).values
    base["stop5"] = df.loc[base.index, "_stop5_5d_bool"].astype(bool).values
    global_failure_rate = float(base["failure"].mean()) if len(base) else 0.0
    rows: List[Dict[str, Any]] = []
    for category, sub in base.groupby("category", dropna=False):
        if len(sub) < min_support:
            continue
        rate = float(sub["failure"].mean())
        lift = rate / global_failure_rate if global_failure_rate > 0 else None
        rows.append(
            {
                "feature": feature,
                "category": str(category),
                "n": int(len(sub)),
                "failure_count": int(sub["failure"].sum()),
                "failure_rate_pct": _pct(rate),
                "failure_lift": _round(lift, 4),
                "avg_close_5d_pct": _round(pd.to_numeric(sub["close5"], errors="coerce").mean()),
                "avg_mfe_5d_pct": _round(pd.to_numeric(sub["mfe5"], errors="coerce").mean()),
                "avg_mae_5d_pct": _round(pd.to_numeric(sub["mae5"], errors="coerce").mean()),
                "touch10_rate_pct": _pct(sub["touch10"].mean()),
                "stop5_rate_pct": _pct(sub["stop5"].mean()),
            }
        )
    return rows


def _top_categorical_traits(
    df: pd.DataFrame,
    *,
    base_mask: pd.Series,
    failure_mask: pd.Series,
    min_support: int,
    max_categories: int,
    max_traits: int,
) -> Dict[str, Any]:
    features = _categorical_feature_candidates(
        df.loc[base_mask], min_non_null=min_support, max_cardinality=max_categories
    )
    rows: List[Dict[str, Any]] = []
    for feature in features:
        rows.extend(
            _categorical_rows_for_feature(
                df,
                feature,
                base_mask=base_mask,
                failure_mask=failure_mask,
                min_support=min_support,
            )
        )
    risky = sorted(
        rows,
        key=lambda item: (
            _safe_float(item.get("failure_lift"), 0.0) or 0.0,
            _safe_float(item.get("failure_rate_pct"), 0.0) or 0.0,
            int(item.get("n") or 0),
        ),
        reverse=True,
    )
    defensive = sorted(
        rows,
        key=lambda item: (
            _safe_float(item.get("failure_lift"), 999.0) or 999.0,
            _safe_float(item.get("failure_rate_pct"), 100.0) or 100.0,
            -int(item.get("n") or 0),
        ),
    )
    return {
        "features_evaluated": features,
        "risky_categories": risky[:max_traits],
        "defensive_categories": defensive[:max_traits],
    }


def _ticker_traits(
    df: pd.DataFrame,
    *,
    base_mask: pd.Series,
    failure_mask: pd.Series,
    min_support: int,
    max_rows: int,
) -> List[Dict[str, Any]]:
    if "ticker" not in df.columns:
        return []
    base = df.loc[base_mask].copy()
    if base.empty:
        return []
    base_failure_rate = float(failure_mask.loc[base.index].mean()) if len(base) else 0.0
    rows: List[Dict[str, Any]] = []
    for ticker, sub in base.groupby(base["ticker"].astype(str), dropna=False):
        if len(sub) < min_support:
            continue
        failures = failure_mask.loc[sub.index].astype(bool)
        rate = float(failures.mean())
        row = {
            "ticker": str(ticker),
            "n": int(len(sub)),
            "failure_count": int(failures.sum()),
            "failure_rate_pct": _pct(rate),
            "failure_lift": _round(rate / base_failure_rate, 4) if base_failure_rate > 0 else None,
            "avg_close_5d_pct": _round(sub["_adj_return_5d_pct"].mean()),
            "avg_mfe_5d_pct": _round(sub["_adj_max_high_return_5d_pct"].mean()),
            "avg_mae_5d_pct": _round(sub["_adj_min_low_return_5d_pct"].mean()),
            "touch10_rate_pct": _pct(sub["_touch10_5d_bool"].mean()),
            "stop5_rate_pct": _pct(sub["_stop5_5d_bool"].mean()),
        }
        for col in ("market", "primary_theme", "kis_stock_sector_name", "kis_theme_news_primary_theme"):
            if col in sub.columns:
                values = [_clean_category(value) for value in sub[col].dropna().tolist()]
                row[col] = values[0] if values else None
        rows.append(row)
    rows.sort(
        key=lambda item: (
            _safe_float(item.get("failure_lift"), 0.0) or 0.0,
            _safe_float(item.get("failure_rate_pct"), 0.0) or 0.0,
            int(item.get("n") or 0),
        ),
        reverse=True,
    )
    return rows[:max_rows]


def _segment_report(
    df: pd.DataFrame,
    *,
    label: str,
    mask: pd.Series,
    min_support: int,
    max_traits: int,
    max_categories: int,
) -> Dict[str, Any]:
    sub = df.loc[mask].copy()
    if sub.empty:
        return {
            "segment": label,
            "overview": {},
            "skipped": True,
            "reason": "empty_segment",
        }
    base_mask = _active_base_mask(sub)
    failure_mask = sub["_touch5_close_loss_bool"] & base_mask
    control_mask = sub["_clean_touch5_close_defense_bool"] & base_mask
    overview = _cohort_overview(sub)
    if int(failure_mask.sum()) < min_support or int(control_mask.sum()) < min_support:
        return {
            "segment": label,
            "overview": overview,
            "skipped": True,
            "reason": "insufficient_failure_or_control_sample",
            "n_failure": int(failure_mask.sum()),
            "n_control": int(control_mask.sum()),
            "min_support": int(min_support),
        }
    return {
        "segment": label,
        "overview": overview,
        "n_failure": int(failure_mask.sum()),
        "n_control": int(control_mask.sum()),
        "numeric_failure_traits": _top_numeric_traits(
            sub,
            base_mask=base_mask,
            failure_mask=failure_mask,
            control_mask=control_mask,
            min_support=min_support,
            max_traits=max_traits,
        ),
        "categorical_failure_traits": _top_categorical_traits(
            sub,
            base_mask=base_mask,
            failure_mask=failure_mask,
            min_support=min_support,
            max_categories=max_categories,
            max_traits=max_traits,
        ),
        "ticker_failure_traits": _ticker_traits(
            sub,
            base_mask=base_mask,
            failure_mask=failure_mask,
            min_support=max(2, min_support // 4),
            max_rows=max_traits,
        ),
    }


def _actionable_hypotheses(report: Mapping[str, Any], *, max_items: int = 10) -> List[Dict[str, Any]]:
    hypotheses: List[Dict[str, Any]] = []
    segments = report.get("segments") if isinstance(report.get("segments"), list) else []
    for segment in segments:
        if not isinstance(segment, Mapping) or segment.get("skipped"):
            continue
        seg_name = str(segment.get("segment") or "")
        for trait in (segment.get("numeric_failure_traits") or [])[:5]:
            if not isinstance(trait, Mapping):
                continue
            lift = _safe_float(trait.get("worst_bin_failure_lift"), 0.0) or 0.0
            effect = abs(_safe_float(trait.get("cohens_d_failure_vs_control"), 0.0) or 0.0)
            if lift < 1.15 and effect < 0.25:
                continue
            hypotheses.append(
                {
                    "segment": seg_name,
                    "type": "numeric_feature",
                    "feature": trait.get("feature"),
                    "direction": trait.get("direction"),
                    "evidence": {
                        "cohens_d_failure_vs_control": trait.get("cohens_d_failure_vs_control"),
                        "worst_bin_failure_lift": trait.get("worst_bin_failure_lift"),
                        "worst_bin": trait.get("worst_bin"),
                    },
                    "dynamic_exit_implication": (
                        "Use as a TP/SL profile splitter; high-risk bin should prefer earlier +5% realization or tighter trailing stop."
                    ),
                }
            )
        for trait in ((segment.get("categorical_failure_traits") or {}).get("risky_categories") or [])[:5]:
            if not isinstance(trait, Mapping):
                continue
            lift = _safe_float(trait.get("failure_lift"), 0.0) or 0.0
            if lift < 1.15:
                continue
            hypotheses.append(
                {
                    "segment": seg_name,
                    "type": "category",
                    "feature": trait.get("feature"),
                    "category": trait.get("category"),
                    "evidence": {
                        "n": trait.get("n"),
                        "failure_rate_pct": trait.get("failure_rate_pct"),
                        "failure_lift": trait.get("failure_lift"),
                        "avg_close_5d_pct": trait.get("avg_close_5d_pct"),
                        "stop5_rate_pct": trait.get("stop5_rate_pct"),
                    },
                    "dynamic_exit_implication": (
                        "Treat this category as a separate exit regime before allowing +10% hold targets."
                    ),
                }
            )
    hypotheses.sort(
        key=lambda item: (
            _safe_float((item.get("evidence") or {}).get("failure_lift"), 0.0)
            or _safe_float((item.get("evidence") or {}).get("worst_bin_failure_lift"), 0.0)
            or 0.0,
            _safe_float((item.get("evidence") or {}).get("cohens_d_failure_vs_control"), 0.0) or 0.0,
        ),
        reverse=True,
    )
    return hypotheses[:max_items]


def build_report(
    df: pd.DataFrame,
    *,
    source_path: str | None = None,
    buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT,
    min_support: int = 20,
    max_traits: int = 40,
    max_categories: int = 80,
) -> Dict[str, Any]:
    prepared = prepare_failure_frame(df, buy_premium_pct=buy_premium_pct)
    segments: List[Dict[str, Any]] = [
        _segment_report(
            prepared,
            label="ALL",
            mask=pd.Series(True, index=prepared.index),
            min_support=min_support,
            max_traits=max_traits,
            max_categories=max_categories,
        )
    ]
    if "market" in prepared.columns:
        for market in sorted(prepared["market"].fillna("UNKNOWN").astype(str).unique()):
            segments.append(
                _segment_report(
                    prepared,
                    label=str(market),
                    mask=prepared["market"].fillna("UNKNOWN").astype(str).eq(str(market)),
                    min_support=min_support,
                    max_traits=max_traits,
                    max_categories=max_categories,
                )
            )
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_version": REPORT_VERSION,
        "source_path": source_path,
        "buy_premium_pct": float(buy_premium_pct),
        "target_touch_pct": TARGET_TOUCH_PCT,
        "extended_touch_pct": EXTENDED_TOUCH_PCT,
        "stop_pct": STOP_PCT,
        "early_weak_close_1d_pct": EARLY_WEAK_CLOSE_1D_PCT,
        "input_rows": int(len(df)),
        "overall": _cohort_overview(prepared),
        "markets": _market_overview(prepared),
        "segments": segments,
        "notes": [
            "Primary failure cohort is touch5_close_loss: +5% MFE after buy premium, then 5D close < 0%.",
            "Control cohort is clean_touch5_close_defense: +5% MFE, 5D close > 0%, no -5% stop proxy and no 1D <-3% early weakness.",
            "Numeric/categorical traits exclude realized outcome columns so they can feed future admission and TP/SL profiles.",
            "Ticker traits are evidence for watch/profile routing, not standalone promotion rules when support is small.",
        ],
    }
    report["actionable_hypotheses"] = _actionable_hypotheses(report)
    return report


def render_markdown(report: Mapping[str, Any]) -> str:
    overall = report.get("overall") if isinstance(report.get("overall"), Mapping) else {}
    conditional = (overall.get("conditional_rates") or {}) if isinstance(overall.get("conditional_rates"), Mapping) else {}
    lines = [
        "# Close Return Failure Traits",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- source_path: `{report.get('source_path')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- buy_premium_pct: `{report.get('buy_premium_pct')}`",
        f"- target_touch_pct: `{report.get('target_touch_pct')}`",
        "",
        "## Overall",
        "",
        f"- touch5_base_n: `{(overall.get('touch5_base') or {}).get('n')}`",
        f"- close_loss_given_touch5_pct: `{conditional.get('close_loss_given_touch5_pct')}`",
        f"- close_defense_given_touch5_pct: `{conditional.get('close_defense_given_touch5_pct')}`",
        f"- bad_path_given_touch5_pct: `{conditional.get('bad_path_given_touch5_pct')}`",
        f"- touch10_given_touch5_pct: `{conditional.get('touch10_given_touch5_pct')}`",
        "",
        "## Segment Highlights",
        "",
    ]
    for segment in report.get("segments") or []:
        if not isinstance(segment, Mapping):
            continue
        name = segment.get("segment")
        overview = segment.get("overview") if isinstance(segment.get("overview"), Mapping) else {}
        cond = (overview.get("conditional_rates") or {}) if isinstance(overview.get("conditional_rates"), Mapping) else {}
        lines.extend(
            [
                f"### {name}",
                "",
                f"- skipped: `{segment.get('skipped', False)}`",
                f"- touch5_base_n: `{(overview.get('touch5_base') or {}).get('n')}`",
                f"- n_failure/n_control: `{segment.get('n_failure')}` / `{segment.get('n_control')}`",
                f"- close_loss_given_touch5_pct: `{cond.get('close_loss_given_touch5_pct')}`",
                f"- bad_path_given_touch5_pct: `{cond.get('bad_path_given_touch5_pct')}`",
                "",
                "| rank | numeric feature | direction | d | worst bin lift | failure mean | control mean |",
                "|---:|---|---|---:|---:|---:|---:|",
            ]
        )
        for i, row in enumerate(segment.get("numeric_failure_traits") or [], start=1):
            if i > 10:
                break
            lines.append(
                "| {rank} | `{feature}` | {direction} | `{d}` | `{lift}` | `{fm}` | `{cm}` |".format(
                    rank=i,
                    feature=row.get("feature"),
                    direction=row.get("direction"),
                    d=row.get("cohens_d_failure_vs_control"),
                    lift=row.get("worst_bin_failure_lift"),
                    fm=row.get("failure_mean"),
                    cm=row.get("control_mean"),
                )
            )
        lines.extend(
            [
                "",
                "| rank | category feature | category | n | failure % | lift | avg close | stop5 % |",
                "|---:|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        cat = segment.get("categorical_failure_traits") if isinstance(segment.get("categorical_failure_traits"), Mapping) else {}
        for i, row in enumerate(cat.get("risky_categories") or [], start=1):
            if i > 10:
                break
            lines.append(
                "| {rank} | `{feature}` | `{category}` | `{n}` | `{rate}` | `{lift}` | `{close}` | `{stop}` |".format(
                    rank=i,
                    feature=row.get("feature"),
                    category=row.get("category"),
                    n=row.get("n"),
                    rate=row.get("failure_rate_pct"),
                    lift=row.get("failure_lift"),
                    close=row.get("avg_close_5d_pct"),
                    stop=row.get("stop5_rate_pct"),
                )
            )
        lines.extend(["", "| rank | ticker | n | failure % | lift | avg close | avg MFE | avg MAE |", "|---:|---|---:|---:|---:|---:|---:|---:|"])
        for i, row in enumerate(segment.get("ticker_failure_traits") or [], start=1):
            if i > 10:
                break
            lines.append(
                "| {rank} | `{ticker}` | `{n}` | `{rate}` | `{lift}` | `{close}` | `{mfe}` | `{mae}` |".format(
                    rank=i,
                    ticker=row.get("ticker"),
                    n=row.get("n"),
                    rate=row.get("failure_rate_pct"),
                    lift=row.get("failure_lift"),
                    close=row.get("avg_close_5d_pct"),
                    mfe=row.get("avg_mfe_5d_pct"),
                    mae=row.get("avg_mae_5d_pct"),
                )
            )
        lines.append("")
    lines.extend(["## Actionable Hypotheses", ""])
    for item in report.get("actionable_hypotheses") or []:
        evidence = item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {}
        lines.append(
            "- `{segment}` `{type}` `{feature}`: lift=`{lift}` d=`{d}` implication={implication}".format(
                segment=item.get("segment"),
                type=item.get("type"),
                feature=item.get("feature"),
                lift=evidence.get("failure_lift") or evidence.get("worst_bin_failure_lift"),
                d=evidence.get("cohens_d_failure_vs_control"),
                implication=item.get("dynamic_exit_implication"),
            )
        )
    lines.extend(["", "## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _load_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input format: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", type=Path, default=DEFAULT_PREPARED_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--buy-premium-pct", type=float, default=DEFAULT_BUY_PREMIUM_PCT)
    parser.add_argument("--min-support", type=int, default=20)
    parser.add_argument("--max-traits", type=int, default=40)
    parser.add_argument("--max-categories", type=int, default=80)
    args = parser.parse_args(argv)

    if not args.prepared_cache.exists():
        raise FileNotFoundError(f"Prepared cache not found: {args.prepared_cache}")
    df = _load_frame(args.prepared_cache)
    report = build_report(
        df,
        source_path=str(args.prepared_cache),
        buy_premium_pct=args.buy_premium_pct,
        min_support=args.min_support,
        max_traits=args.max_traits,
        max_categories=args.max_categories,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = args.output.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "markdown": str(md_path), "report_version": REPORT_VERSION}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
