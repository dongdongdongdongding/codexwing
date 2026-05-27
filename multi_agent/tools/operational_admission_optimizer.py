#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/codex_swing_matplotlib")

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover
    CatBoostClassifier = None


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_agent.tools.run_internal_retrain_sweep import (
    BASE_CATEGORICAL,
    BASE_NUMERIC,
    DEFAULT_INPUT,
    DEFAULT_OUTPUT_DIR,
    FLOW_NUMERIC,
    REGIME_NUMERIC,
    THEME_CATEGORICAL,
    _cohort_masks,
    _json_default,
    _load_dataset,
    _pct,
    _round,
    ORDERED_OUTCOME_PATH_LABEL_VERSION,
)


REPORT_VERSION = "operational_admission_optimizer_v2"

EXTRA_NUMERIC = [
    "priority_rank",
    "feature_completeness",
    "conviction_score",
]

EXTRA_CATEGORICAL = [
    "decision",
    "decision_bucket",
    "phase25_variant",
    "phase25_shadow_variant",
    "phase25_signal_direction",
    "regime_adjusted_grade",
    "relative_rank_model",
    "dominant",
    "whale_trend",
    "flow_window",
    "volume_confirmed",
    "flow_consensus_buying",
    "retail_dominant",
    "exception_leader",
]

SCORE_BASELINES = [
    "decision_score",
    "expected_edge_score",
    "prob_clean",
    "phase25_prob",
    "phase25_shadow_prob",
    "relative_rank_score",
    "whale_score",
    "volume_ratio",
]

TOPNS = [1, 3, 5]


@dataclass(frozen=True)
class LabelProfile:
    name: str
    target_pct: float
    stop_pct: float
    kind: str
    description: str


LABEL_PROFILES = [
    LabelProfile("ordered_5d_5v5", 5.0, 5.0, "ordered_touch_5d", "Exact path: scan-time target touched before stop within 5 sessions"),
    LabelProfile("ordered_5d_8v5", 8.0, 5.0, "ordered_touch_5d", "Exact path: target-before-stop plus 5D MFE >= +8%"),
    LabelProfile("ordered_5d_10v5", 10.0, 5.0, "ordered_touch_5d", "Exact path: target-before-stop plus 5D MFE >= +10%"),
    LabelProfile("ordered_5d_5v3_lowmae", 5.0, 3.0, "ordered_low_mae_5d", "Exact path: target-before-stop and MAE before target better than -3%"),
    LabelProfile("fast_1d_2v3", 2.0, 3.0, "close_1d", "1D close >= +2% and 5D path drawdown better than -3%"),
    LabelProfile("clean_3d_4v4", 4.0, 4.0, "close_3d", "3D close >= +4%, 1D not worse than -2%, and drawdown better than -4%"),
    LabelProfile("clean_5d_6v5", 6.0, 5.0, "close_5d", "5D close >= +6% and drawdown better than -5%"),
    LabelProfile("touch_5d_8v5", 8.0, 5.0, "touch_5d", "5D high proxy >= +8% and drawdown better than -5%"),
    LabelProfile("touch_5d_10v5", 10.0, 5.0, "touch_5d", "5D high proxy >= +10% and drawdown better than -5%"),
    LabelProfile("compound_3to5_lowdd", 3.0, 4.0, "compound", "3D positive, 5D close >= +3%, and drawdown better than -4%"),
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _is_ordered_profile(profile: LabelProfile) -> bool:
    return str(profile.kind or "").startswith("ordered_")


def _ordered_path_valid(df: pd.DataFrame) -> pd.Series:
    if "target_before_stop_5d" not in df.columns or "stop_before_target_5d" not in df.columns:
        return pd.Series(False, index=df.index)
    version = df.get("outcome_path_label_version", pd.Series("", index=df.index)).fillna("").astype(str)
    terminal = df.get("outcome_path_terminal_status", pd.Series("", index=df.index)).fillna("").astype(str)
    target_raw = df["target_before_stop_5d"]
    stop_raw = df["stop_before_target_5d"]
    return (
        version.eq(ORDERED_OUTCOME_PATH_LABEL_VERSION)
        & target_raw.notna()
        & stop_raw.notna()
        & ~terminal.eq("insufficient_forward_bars")
    )


def _label(df: pd.DataFrame, profile: LabelProfile) -> Tuple[pd.Series, pd.Series]:
    if profile.kind in {"ordered_touch_5d", "ordered_low_mae_5d"}:
        valid = _ordered_path_valid(df)
        target_first = _bool_series(df.get("target_before_stop_5d", pd.Series(False, index=df.index)))
        stop_first = _bool_series(df.get("stop_before_target_5d", pd.Series(False, index=df.index)))
        mfe = pd.to_numeric(
            df.get("mfe_5d_pct", df.get("max_high_return_5d_pct", pd.Series(index=df.index, dtype=float))),
            errors="coerce",
        )
        label = target_first & ~stop_first
        if profile.target_pct > 5.0:
            valid &= mfe.notna()
            label &= mfe.ge(profile.target_pct)
        if profile.kind == "ordered_low_mae_5d":
            mae_before = pd.to_numeric(
                df.get("ordered_mae_before_target_5d_pct", pd.Series(index=df.index, dtype=float)),
                errors="coerce",
            )
            valid &= mae_before.notna()
            label &= mae_before.ge(-abs(profile.stop_pct))
        return label.fillna(False), valid

    min_path = pd.to_numeric(df.get("min_return_observed_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
    no_stop = min_path.gt(-abs(profile.stop_pct))
    if profile.kind == "close_1d":
        r1 = pd.to_numeric(df.get("return_1d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = r1.notna() & min_path.notna()
        return (r1.ge(profile.target_pct) & no_stop).fillna(False), valid
    if profile.kind == "close_3d":
        r1 = pd.to_numeric(df.get("return_1d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        r3 = pd.to_numeric(df.get("return_3d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = r1.notna() & r3.notna() & min_path.notna()
        return (r3.ge(profile.target_pct) & r1.ge(-2.0) & no_stop).fillna(False), valid
    if profile.kind == "close_5d":
        r5 = pd.to_numeric(df.get("return_5d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = r5.notna() & min_path.notna()
        return (r5.ge(profile.target_pct) & no_stop).fillna(False), valid
    if profile.kind == "touch_5d":
        mfe = pd.to_numeric(df.get("max_high_return_5d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = mfe.notna() & min_path.notna()
        return (mfe.ge(profile.target_pct) & no_stop).fillna(False), valid
    if profile.kind == "compound":
        r1 = pd.to_numeric(df.get("return_1d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        r3 = pd.to_numeric(df.get("return_3d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        r5 = pd.to_numeric(df.get("return_5d_pct", pd.Series(index=df.index, dtype=float)), errors="coerce")
        valid = r1.notna() & r3.notna() & r5.notna() & min_path.notna()
        return (r1.ge(-2.0) & r3.gt(0.0) & r5.ge(profile.target_pct) & no_stop).fillna(False), valid
    raise KeyError(profile.name)


def _feature_sets(df: pd.DataFrame, include_theme: bool) -> Dict[str, Tuple[List[str], List[str]]]:
    numeric_base = [col for col in BASE_NUMERIC + REGIME_NUMERIC + EXTRA_NUMERIC if col in df.columns]
    numeric_flow = [col for col in numeric_base + FLOW_NUMERIC if col in df.columns]
    categorical_base = [col for col in BASE_CATEGORICAL + EXTRA_CATEGORICAL if col in df.columns]
    categorical_theme = [col for col in categorical_base + THEME_CATEGORICAL if col in df.columns] if include_theme else categorical_base
    return {
        "score_no_theme": (numeric_base, categorical_base),
        "score_flow_no_theme": (numeric_flow, categorical_base),
        "score_theme": (numeric_flow, categorical_theme),
    }


def _preprocessor(numeric: Sequence[str], categorical: Sequence[str], *, scale_numeric: bool) -> ColumnTransformer:
    num_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(num_steps), list(numeric)),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=3)),
                    ]
                ),
                list(categorical),
            ),
        ],
        remainder="drop",
    )


def _model(name: str) -> Any | None:
    if name == "logistic":
        return LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")
    if name == "hist_gb":
        return HistGradientBoostingClassifier(max_iter=180, max_depth=3, learning_rate=0.05, l2_regularization=0.2, random_state=42)
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=320, max_depth=7, min_samples_leaf=6, class_weight="balanced", random_state=42, n_jobs=-1)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=320, max_depth=8, min_samples_leaf=5, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    if name == "xgboost" and XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=220,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    if name == "lightgbm" and LGBMClassifier is not None:
        return LGBMClassifier(
            n_estimators=260,
            max_depth=5,
            learning_rate=0.035,
            num_leaves=24,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
            n_jobs=-1,
        )
    if name == "catboost" and CatBoostClassifier is not None:
        return CatBoostClassifier(iterations=220, depth=5, learning_rate=0.04, loss_function="Logloss", eval_metric="AUC", random_seed=42, verbose=False)
    return None


def _walk_windows(days: Sequence[str], *, min_train_days: int, test_days: int, max_folds: int) -> List[Tuple[set[str], set[str]]]:
    unique_days = list(days)
    windows: List[Tuple[set[str], set[str]]] = []
    end = len(unique_days)
    while end > min_train_days and len(windows) < max_folds:
        start = max(min_train_days, end - test_days)
        train_days = set(unique_days[:start])
        holdout_days = set(unique_days[start:end])
        if train_days and holdout_days:
            windows.append((train_days, holdout_days))
        end = start
    windows.reverse()
    return windows


def _daily_top_indices(frame: pd.DataFrame, score: pd.Series, topn: int) -> pd.Index:
    scored = frame.copy()
    scored["_score"] = score.reindex(frame.index)
    chunks = []
    for _day, day_df in scored.groupby("trade_date", dropna=False):
        top = day_df.sort_values("_score", ascending=False, na_position="last").head(topn)
        if not top.empty:
            chunks.append(top.index)
    if not chunks:
        return pd.Index([])
    return chunks[0].append(chunks[1:]) if len(chunks) > 1 else chunks[0]


def _metrics(df: pd.DataFrame, idx: pd.Index, label: pd.Series, profile: LabelProfile | None = None) -> Dict[str, Any]:
    sub = df.loc[idx]
    if sub.empty:
        return {"n": 0, "active_days": 0}
    wins = label.loc[idx].astype(bool)
    ordered_valid = _ordered_path_valid(sub)
    exact_target = _bool_series(sub.get("target_before_stop_5d", pd.Series(False, index=sub.index)))
    exact_stop = _bool_series(sub.get("stop_before_target_5d", pd.Series(False, index=sub.index)))
    ordered_valid_n = int(ordered_valid.sum())
    if ordered_valid_n:
        ordered_target_pct = _pct(exact_target.loc[ordered_valid].mean())
        ordered_stop_pct = _pct(exact_stop.loc[ordered_valid].mean())
        ordered_no_touch_pct = _pct((~exact_target.loc[ordered_valid] & ~exact_stop.loc[ordered_valid]).mean())
    else:
        ordered_target_pct = None
        ordered_stop_pct = None
        ordered_no_touch_pct = None
    stop_series = exact_stop.where(ordered_valid, sub.get("stop5_proxy", pd.Series(False, index=sub.index)).fillna(False))
    bad_series = (
        stop_series
        | sub.get("return_1d_pct", pd.Series(index=sub.index, dtype=float)).lt(-3.0).fillna(False)
        | sub.get("return_5d_pct", pd.Series(index=sub.index, dtype=float)).lt(0.0).fillna(False)
    )
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "label_win_pct": _pct(wins.mean()) if len(wins) else None,
        "bad_path_pct": _pct(bad_series.mean()),
        "stop5_pct": _pct(stop_series.mean()),
        "ordered_path_n": ordered_valid_n,
        "ordered_path_coverage_pct": _pct(ordered_valid_n / len(sub)) if len(sub) else None,
        "target_before_stop_5d_pct": ordered_target_pct,
        "stop_before_target_5d_pct": ordered_stop_pct,
        "no_touch_5d_pct": ordered_no_touch_pct,
        "ordered_path_label_version": ORDERED_OUTCOME_PATH_LABEL_VERSION if ordered_valid_n else None,
    }
    for horizon, col in [("1d", "return_1d_pct"), ("3d", "return_3d_pct"), ("5d", "return_5d_pct")]:
        ret = pd.to_numeric(sub.get(col, pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
        out[f"win_{horizon}_pct"] = _pct(ret.gt(0).mean()) if len(ret) else None
        out[f"avg_{horizon}_pct"] = _round(ret.mean()) if len(ret) else None
        out[f"median_{horizon}_pct"] = _round(ret.median()) if len(ret) else None
        out[f"min_{horizon}_pct"] = _round(ret.min()) if len(ret) else None
        out[f"max_{horizon}_pct"] = _round(ret.max()) if len(ret) else None
    mfe = pd.to_numeric(
        sub.get("mfe_5d_pct", sub.get("max_high_return_5d_pct", pd.Series(index=sub.index, dtype=float))),
        errors="coerce",
    )
    mae = pd.to_numeric(
        sub.get("mae_5d_pct", sub.get("min_return_observed_pct", pd.Series(index=sub.index, dtype=float))),
        errors="coerce",
    )
    terminal_mfe = pd.to_numeric(sub.get("ordered_mfe_until_terminal_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    terminal_mae = pd.to_numeric(sub.get("ordered_mae_until_terminal_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    mae_before_target = pd.to_numeric(sub.get("ordered_mae_before_target_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
    out["avg_mfe_5d_pct"] = _round(mfe.mean()) if len(mfe.dropna()) else None
    out["avg_mae_5d_pct"] = _round(mae.mean()) if len(mae.dropna()) else None
    out["avg_ordered_mfe_until_terminal_5d_pct"] = _round(terminal_mfe.mean()) if len(terminal_mfe.dropna()) else None
    out["avg_ordered_mae_until_terminal_5d_pct"] = _round(terminal_mae.mean()) if len(terminal_mae.dropna()) else None
    out["avg_ordered_mae_before_target_5d_pct"] = _round(mae_before_target.mean()) if len(mae_before_target.dropna()) else None
    if ordered_valid_n:
        valid_idx = ordered_valid[ordered_valid].index
        source_series = sub.get("outcome_path_source", pd.Series(index=sub.index, dtype=object)).loc[valid_idx].fillna("").astype(str)
        sources = source_series[source_series.str.strip().ne("")].value_counts().head(3)
        warning_series = sub.get("outcome_path_warnings", pd.Series(index=sub.index, dtype=object)).loc[valid_idx].fillna("").astype(str)
        warning_mask = warning_series.str.strip().replace({"[]": "", "nan": "", "None": ""}).ne("")
        out["outcome_path_sources"] = {str(key): int(value) for key, value in sources.items()}
        out["outcome_path_warning_rows"] = int(warning_mask.sum())
        out["outcome_path_warning_pct"] = _pct(warning_mask.mean()) if len(warning_mask) else None
    if profile is not None and _is_ordered_profile(profile) and ordered_valid_n:
        no_touch_exit = pd.to_numeric(sub.get("return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce")
        exit_returns = pd.Series(np.nan, index=sub.index, dtype=float)
        valid_idx = ordered_valid[ordered_valid].index
        exit_returns.loc[valid_idx] = no_touch_exit.loc[valid_idx]
        exit_returns.loc[valid_idx.intersection(exact_target[exact_target].index)] = float(profile.target_pct)
        exit_returns.loc[valid_idx.intersection(exact_stop[exact_stop].index)] = -abs(float(profile.stop_pct))
        realized = exit_returns.loc[valid_idx].dropna()
        out["exit_policy_target_pct"] = _round(float(profile.target_pct))
        out["exit_policy_stop_pct"] = _round(-abs(float(profile.stop_pct)))
        out["avg_ordered_exit_5d_pct"] = _round(realized.mean()) if len(realized) else None
        out["win_ordered_exit_5d_pct"] = _pct(realized.gt(0).mean()) if len(realized) else None
        out["min_ordered_exit_5d_pct"] = _round(realized.min()) if len(realized) else None
        out["max_ordered_exit_5d_pct"] = _round(realized.max()) if len(realized) else None
    return out


def _merge_metrics(
    df: pd.DataFrame,
    selected_indices: Sequence[pd.Index],
    label: pd.Series,
    profile: LabelProfile | None = None,
) -> Dict[str, Any]:
    if not selected_indices:
        return {"n": 0, "active_days": 0}
    idx = selected_indices[0].append(selected_indices[1:]) if len(selected_indices) > 1 else selected_indices[0]
    return _metrics(df, idx, label, profile=profile)


def _promotion_flags(
    metrics: Dict[str, Any],
    fold_wins: Sequence[float],
    *,
    min_n: int,
    min_days: int,
    min_folds: int,
    require_ordered: bool,
) -> Dict[str, Any]:
    label_win = _safe_float(metrics.get("label_win_pct"))
    avg5 = _safe_float(metrics.get("avg_5d_pct"), -999.0)
    bad = _safe_float(metrics.get("bad_path_pct"), 100.0)
    stop = _safe_float(metrics.get("stop5_pct"), 100.0)
    min5 = _safe_float(metrics.get("min_5d_pct"), -999.0)
    exit_win = _safe_float(metrics.get("win_ordered_exit_5d_pct"))
    exit_avg = _safe_float(metrics.get("avg_ordered_exit_5d_pct"), -999.0)
    exit_min = _safe_float(metrics.get("min_ordered_exit_5d_pct"), -999.0)
    path_warning = _safe_float(metrics.get("outcome_path_warning_pct"), 100.0)
    folds = len(fold_wins)
    min_fold_win = min(fold_wins) if fold_wins else 0.0
    checks = {
        "exact_label_profile_gate": bool(require_ordered),
        "enough_samples": int(metrics.get("n") or 0) >= min_n,
        "enough_days": int(metrics.get("active_days") or 0) >= min_days,
        "enough_folds": folds >= min_folds,
        "ordered_path_gate": (not require_ordered)
        or (
            _safe_float(metrics.get("ordered_path_coverage_pct")) >= 95.0
            and str(metrics.get("ordered_path_label_version") or "") == ORDERED_OUTCOME_PATH_LABEL_VERSION
        ),
        "path_warning_gate": (not require_ordered) or path_warning <= 25.0,
        "label_win_gate": label_win >= 70.0,
        "avg_return_gate": avg5 >= 3.0,
        "bad_path_gate": bad <= 35.0,
        "stop_gate": stop <= 25.0,
        "tail_loss_gate": min5 >= -12.0,
        "fold_stability_gate": min_fold_win >= 45.0,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    exit_policy_watch = bool(exit_win >= 80.0 and exit_avg >= 3.0 and exit_min >= -5.0 and stop <= 10.0 and path_warning <= 25.0)
    return {
        "checks": checks,
        "failed_checks": failed_checks,
        "exit_policy_watch": exit_policy_watch,
        "promotable": all(checks.values()),
        "folds": int(folds),
        "min_fold_label_win_pct": _round(min_fold_win, 4),
    }


def _quality_score(metrics: Dict[str, Any], flags: Dict[str, Any]) -> float:
    checks = flags.get("checks") or {}
    label_win = _safe_float(metrics.get("label_win_pct"))
    avg5 = _safe_float(metrics.get("avg_5d_pct"), -20.0)
    bad = _safe_float(metrics.get("bad_path_pct"), 100.0)
    stop = _safe_float(metrics.get("stop5_pct"), 100.0)
    min5 = _safe_float(metrics.get("min_5d_pct"), -40.0)
    n = int(metrics.get("n") or 0)
    days = int(metrics.get("active_days") or 0)
    sample_penalty = 0.0
    if not checks.get("enough_samples", False):
        sample_penalty += 80.0
    if not checks.get("enough_days", False):
        sample_penalty += 50.0
    if not checks.get("enough_folds", False):
        sample_penalty += 50.0
    if not checks.get("exact_label_profile_gate", False):
        sample_penalty += 120.0
    if not checks.get("ordered_path_gate", False):
        sample_penalty += 80.0
    passed_gate_bonus = sum(1 for ok in checks.values() if ok) * 4.0
    return (
        (100.0 if flags.get("promotable") else 0.0)
        + passed_gate_bonus
        + label_win
        + avg5 * 2.5
        - bad * 0.7
        - stop * 0.5
        + max(min5, -40.0) * 0.15
        + min(n, 100) * 0.03
        + min(days, 30) * 0.25
        - sample_penalty
    )


def _score_baseline(
    scoped: pd.DataFrame,
    score_col: str,
    windows: Sequence[Tuple[set[str], set[str]]],
    label: pd.Series,
    *,
    profile: LabelProfile,
) -> List[Dict[str, Any]]:
    if score_col not in scoped.columns:
        return []
    rows = []
    for topn in TOPNS:
        selected: List[pd.Index] = []
        fold_wins: List[float] = []
        for _train_days, test_days in windows:
            test = scoped[scoped["trade_date"].isin(test_days)]
            if test.empty:
                continue
            score = pd.to_numeric(test[score_col], errors="coerce")
            if score_col == "loss_risk_score":
                score = -score
            idx = _daily_top_indices(test, score, topn)
            if len(idx):
                selected.append(idx)
                fold_metric = _metrics(scoped, idx, label, profile=profile)
                fold_wins.append(_safe_float(fold_metric.get("label_win_pct")))
        metrics = _merge_metrics(scoped, selected, label, profile=profile)
        flags = _promotion_flags(metrics, fold_wins, min_n=30, min_days=10, min_folds=3, require_ordered=_is_ordered_profile(profile))
        rows.append(
            {
                "policy_type": "score_baseline",
                "model": score_col,
                "feature_set": "score_column",
                "topn": topn,
                "metrics": metrics,
                "promotion": flags,
                "quality_score": _round(_quality_score(metrics, flags), 4),
            }
        )
    return rows


def _fit_model_policies(
    scoped: pd.DataFrame,
    *,
    profile: LabelProfile,
    label: pd.Series,
    windows: Sequence[Tuple[set[str], set[str]]],
    feature_set: str,
    numeric: Sequence[str],
    categorical: Sequence[str],
    model_name: str,
    min_train_rows: int,
) -> List[Dict[str, Any]]:
    clf = _model(model_name)
    if clf is None:
        return []
    selected_by_topn = {topn: [] for topn in TOPNS}
    fold_wins_by_topn = {topn: [] for topn in TOPNS}
    aucs: List[float] = []
    briers: List[float] = []
    used_folds = 0
    for train_days, test_days in windows:
        train = scoped[scoped["trade_date"].isin(train_days)]
        test = scoped[scoped["trade_date"].isin(test_days)]
        if len(train) < min_train_rows or len(test) < 10:
            continue
        y_train = label.loc[train.index].astype(int)
        y_test = label.loc[test.index].astype(int)
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue
        x_train = train[list(numeric) + list(categorical)].copy()
        x_test = test[list(numeric) + list(categorical)].copy()
        for col in categorical:
            x_train[col] = x_train[col].fillna("UNKNOWN").astype(str)
            x_test[col] = x_test[col].fillna("UNKNOWN").astype(str)
        pipe = Pipeline(
            [
                ("pre", _preprocessor(numeric, categorical, scale_numeric=model_name == "logistic")),
                ("model", clf),
            ]
        )
        try:
            pipe.fit(x_train, y_train)
            prob = pd.Series(pipe.predict_proba(x_test)[:, 1], index=test.index)
            if y_test.nunique() > 1:
                aucs.append(float(roc_auc_score(y_test, prob)))
            briers.append(float(brier_score_loss(y_test, prob)))
        except Exception:
            continue
        used_folds += 1
        for topn in TOPNS:
            idx = _daily_top_indices(test, prob, topn)
            if len(idx):
                selected_by_topn[topn].append(idx)
                fold_metric = _metrics(scoped, idx, label, profile=profile)
                fold_wins_by_topn[topn].append(_safe_float(fold_metric.get("label_win_pct")))
    rows: List[Dict[str, Any]] = []
    for topn in TOPNS:
        metrics = _merge_metrics(scoped, selected_by_topn[topn], label, profile=profile)
        flags = _promotion_flags(
            metrics,
            fold_wins_by_topn[topn],
            min_n=30,
            min_days=10,
            min_folds=3,
            require_ordered=_is_ordered_profile(profile),
        )
        rows.append(
            {
                "policy_type": "ml_model",
                "model": model_name,
                "feature_set": feature_set,
                "topn": topn,
                "folds_used": int(used_folds),
                "auc_mean": _round(float(np.mean(aucs)), 6) if aucs else None,
                "brier_mean": _round(float(np.mean(briers)), 6) if briers else None,
                "metrics": metrics,
                "promotion": flags,
                "quality_score": _round(_quality_score(metrics, flags), 4),
            }
        )
    return rows


def _run_scope(
    df: pd.DataFrame,
    *,
    market: str,
    cohort: str,
    profile: LabelProfile,
    model_names: Sequence[str],
    include_theme: bool,
    min_rows: int,
    min_train_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
) -> List[Dict[str, Any]]:
    market_df = df[df["market2"].eq(market)].copy()
    masks = _cohort_masks(market_df)
    if cohort not in masks:
        return []
    scoped = market_df.loc[masks[cohort]].copy()
    label, valid = _label(scoped, profile)
    scoped = scoped.loc[valid].copy()
    label = label.loc[scoped.index]
    ordered_profile = _is_ordered_profile(profile)
    effective_min_rows = min(min_rows, 30) if ordered_profile else min_rows
    effective_min_train_rows = min(min_train_rows, 40) if ordered_profile else min_train_rows
    if len(scoped) < effective_min_rows or scoped["trade_date"].nunique() < min_train_days + test_days:
        return []
    days = sorted(scoped["trade_date"].dropna().astype(str).unique().tolist())
    windows = _walk_windows(days, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds)
    if not windows:
        return []

    rows: List[Dict[str, Any]] = []
    for score_col in SCORE_BASELINES + ["loss_risk_score"]:
        for row in _score_baseline(scoped, score_col, windows, label, profile=profile):
            rows.append({**row, "market": market, "cohort": cohort, "label_profile": asdict(profile)})

    for feature_set, (numeric, categorical) in _feature_sets(scoped, include_theme=include_theme).items():
        if not numeric and not categorical:
            continue
        for model_name in model_names:
            for row in _fit_model_policies(
                scoped,
                profile=profile,
                label=label,
                windows=windows,
                feature_set=feature_set,
                numeric=numeric,
                categorical=categorical,
                model_name=model_name,
                min_train_rows=effective_min_train_rows,
            ):
                rows.append({**row, "market": market, "cohort": cohort, "label_profile": asdict(profile)})
    return rows


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Operational Admission Optimizer",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- evaluated_policies: `{report.get('evaluated_policies')}`",
        f"- promotable_count: `{report.get('promotable_count')}`",
        "",
        "## Top Policies",
        "",
        "| Rank | Promote | Exit Watch | Market | Cohort | Label | Type | Model | Feature Set | TopN | N | Days | Label Win | Avg5 | Min5 | Target<Stop | Stop<Target | Exit Win | Exit Avg | Exit Min | Bad | Stop | Folds | Min Fold Win | Failed Checks | AUC | Score |",
        "|---:|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for idx, row in enumerate(report.get("top_policies", [])[:80], start=1):
        metrics = row.get("metrics") or {}
        promo = row.get("promotion") or {}
        label = (row.get("label_profile") or {}).get("name")
        failed = ",".join(str(item) for item in (promo.get("failed_checks") or [])[:5]) or "-"
        lines.append(
            "| "
            + " | ".join(
                str(v)
                for v in [
                    idx,
                    bool(promo.get("promotable")),
                    bool(promo.get("exit_policy_watch")),
                    row.get("market"),
                    row.get("cohort"),
                    label,
                    row.get("policy_type"),
                    row.get("model"),
                    row.get("feature_set"),
                    row.get("topn"),
                    metrics.get("n"),
                    metrics.get("active_days"),
                    metrics.get("label_win_pct"),
                    metrics.get("avg_5d_pct"),
                    metrics.get("min_5d_pct"),
                    metrics.get("target_before_stop_5d_pct"),
                    metrics.get("stop_before_target_5d_pct"),
                    metrics.get("win_ordered_exit_5d_pct"),
                    metrics.get("avg_ordered_exit_5d_pct"),
                    metrics.get("min_ordered_exit_5d_pct"),
                    metrics.get("bad_path_pct"),
                    metrics.get("stop5_pct"),
                    promo.get("folds"),
                    promo.get("min_fold_label_win_pct"),
                    failed,
                    row.get("auc_mean"),
                    row.get("quality_score"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Promotion Gate", ""])
    lines.append("- `promotable` requires an exact ordered path label profile, enough samples/days/folds, label win >= 70%, 5D avg >= +3%, bad path <= 35%, stop5 <= 25%, 5D tail loss >= -12%, and no fold below 45% label win.")
    lines.append("- `exit_policy_watch` is diagnostic only: ordered exit win >= 80%, ordered exit avg >= +3%, ordered exit min >= -5%, and stop-first <= 10%. It does not replace the production promotion gate.")
    lines.append(f"- Exact path label version: `{ORDERED_OUTCOME_PATH_LABEL_VERSION}`. Proxy labels remain visible for diagnosis but cannot trigger promotion.")
    if not report.get("promotable_policies"):
        lines.extend(
            [
                "",
                "## No-Promotion Diagnosis",
                "",
                "- No policy passed the full release gate. This means current scan-time features and archive path labels do not yet justify replacing production logic.",
                "- Near-misses should be monitored, not deployed. The next data improvement is richer intraday flow/theme acceleration and more exact ordered-label coverage.",
            ]
        )
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def build_report(
    df: pd.DataFrame,
    *,
    markets: Sequence[str],
    cohorts: Sequence[str],
    model_names: Sequence[str],
    include_theme: bool,
    min_rows: int,
    min_train_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
) -> Dict[str, Any]:
    all_rows: List[Dict[str, Any]] = []
    for market in markets:
        for cohort in cohorts:
            for profile in LABEL_PROFILES:
                all_rows.extend(
                    _run_scope(
                        df,
                        market=market,
                        cohort=cohort,
                        profile=profile,
                        model_names=model_names,
                        include_theme=include_theme,
                        min_rows=min_rows,
                        min_train_rows=min_train_rows,
                        min_train_days=min_train_days,
                        test_days=test_days,
                        max_folds=max_folds,
                    )
                )
    all_rows.sort(key=lambda row: _safe_float(row.get("quality_score"), -999.0), reverse=True)
    promotable = [row for row in all_rows if (row.get("promotion") or {}).get("promotable")]
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "internal_shadow_no_production_change",
        "input_rows": int(len(df)),
        "search_config": {
            "markets": list(markets),
            "cohorts": list(cohorts),
            "models": list(model_names),
            "include_theme": include_theme,
            "min_rows": min_rows,
            "min_train_rows": min_train_rows,
            "min_train_days": min_train_days,
            "test_days_per_fold": test_days,
            "max_folds": max_folds,
            "labels": [asdict(profile) for profile in LABEL_PROFILES],
        },
        "evaluated_policies": int(len(all_rows)),
        "promotable_count": int(len(promotable)),
        "promotable_policies": promotable[:80],
        "top_policies": all_rows[:160],
        "notes": [
            "Production scanner/model artifacts are unchanged.",
            "Walk-forward windows validate recent contiguous trade-date blocks, using only prior days for training.",
            "Score baselines are evaluated alongside ML models so scanner logic and learned models compete under the same promotion gate.",
            "Fixed primary theme values are optional because rotating themes can overfit; flow/regime/theme metadata remains available when enabled.",
            f"Promotion requires exact ordered target/stop labels from {ORDERED_OUTCOME_PATH_LABEL_VERSION}; proxy high/low labels are diagnostic only.",
        ],
    }


def main() -> int:
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    parser = argparse.ArgumentParser(description="Run internal operational admission optimizer.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stem", default="operational_admission_optimizer")
    parser.add_argument("--markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--cohorts", default="top5,top5_exception,exception_leader,ranked_top20,core_trend,explosive_leader")
    parser.add_argument("--models", default="logistic,hist_gb,extra_trees,random_forest,xgboost,lightgbm,catboost")
    parser.add_argument("--include-theme", action="store_true")
    parser.add_argument("--min-rows", type=int, default=80)
    parser.add_argument("--min-train-rows", type=int, default=80)
    parser.add_argument("--min-train-days", type=int, default=12)
    parser.add_argument("--test-days", type=int, default=5)
    parser.add_argument("--max-folds", type=int, default=6)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = _load_dataset(Path(args.input))
    report = build_report(
        df,
        markets=[part.strip().upper() for part in str(args.markets).split(",") if part.strip()],
        cohorts=[part.strip() for part in str(args.cohorts).split(",") if part.strip()],
        model_names=[part.strip() for part in str(args.models).split(",") if part.strip()],
        include_theme=bool(args.include_theme),
        min_rows=int(args.min_rows),
        min_train_rows=int(args.min_train_rows),
        min_train_days=int(args.min_train_days),
        test_days=int(args.test_days),
        max_folds=int(args.max_folds),
    )
    json_path = output_dir / f"{args.stem}.json"
    md_path = output_dir / f"{args.stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(json_path),
                "md": str(md_path),
                "evaluated_policies": report.get("evaluated_policies"),
                "promotable_count": report.get("promotable_count"),
                "best": (report.get("top_policies") or [None])[0],
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
