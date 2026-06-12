#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_model_features import (
    KIS_CATEGORICAL_FEATURES,
    KIS_NUMERIC_FEATURES,
    KIS_SIDECAR_CATEGORICAL_FEATURES,
    KIS_SIDECAR_MODEL_NUMERIC_FEATURES,
    KIS_THEME_NEWS_CATEGORICAL_FEATURES,
    KIS_THEME_NEWS_NUMERIC_FEATURES,
)
from modules.kis_model_gate import evaluate_kis_model_gate
from modules.tradable_pnl import TradableCostModel, compute_net_return_pct
from multi_agent.tools.train_scan_universe_admission_challenger import (
    CLOSE_FAILURE_RISK_CATEGORICAL,
    CLOSE_FAILURE_RISK_NUMERIC,
)

try:
    from lightgbm import LGBMClassifier, LGBMRanker
except Exception:  # pragma: no cover - optional dependency
    LGBMClassifier = None
    LGBMRanker = None

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover - optional dependency
    CatBoostClassifier = None


REPORT_VERSION = "kis_historical_best_effort_suite_v1"
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-06-10"
TARGET_PCT = 5.0
STOP_PCT = 10.0
BUY_PREMIUM_PCT = 2.0

LABEL_COLUMNS = {
    "success": "buy_premium_target_before_stop_5d",
    "target_hit": "buy_premium_target_hit_5d",
    "stop_hit": "buy_premium_stop_hit_5d",
    "stop_before_target": "buy_premium_stop_before_target_5d",
    "close_5d": "buy_premium_return_5d_pct",
    "mfe_5d": "buy_premium_max_high_return_5d_pct",
    "mae_5d": "buy_premium_min_low_return_5d_pct",
}

LEAK_PREFIXES = (
    "buy_premium_",
    "return_",
    "max_high_return_",
    "min_low_return_",
    "target_hit_",
    "stop_hit_",
    "target_before_stop_",
    "stop_before_target_",
    "days_to_",
    "first_touch_",
    "path_label_",
    "label_",
    "outcome_",
)

LEAK_CONTAINS = (
    "_return_1d",
    "_return_3d",
    "_return_5d",
    "_hit_at_",
    "future",
    "target_before_stop",
    "stop_before_target",
)


@dataclass(frozen=True)
class Window:
    fold: int
    train_days: List[str]
    test_days: List[str]
    embargo_days: List[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _pct(value: Any) -> float | None:
    rounded = _round(value, 6)
    return None if rounded is None else round(rounded * 100.0, 4)


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    text = series.fillna(False).astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "t", "yes", "y"})


def _onehot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True, min_frequency=10)
    except TypeError:  # pragma: no cover - sklearn <1.2
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _round(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _unique_existing(columns: Iterable[str], frame: pd.DataFrame) -> List[str]:
    seen: Dict[str, None] = {}
    for col in columns:
        if col in frame.columns and col not in seen:
            seen[col] = None
    return list(seen)


def _nonempty_columns(columns: Iterable[str], frame: pd.DataFrame) -> List[str]:
    out: List[str] = []
    for col in _unique_existing(columns, frame):
        if frame[col].notna().any():
            out.append(col)
    return out


def _is_leaky_feature(column: str) -> bool:
    name = str(column)
    if name.startswith("kis_daily_return_"):
        return False
    if name in {
        "base_trade_date",
        "trade_date",
        "scanned_at",
        "run_id",
        "snapshot_key",
        "source_ref",
        "feature_snapshot",
        "validation_excluded_reason",
        "outcome_available",
        "outcome_source",
        "backfill_version",
    }:
        return True
    if name.startswith(LEAK_PREFIXES):
        return True
    return any(token in name for token in LEAK_CONTAINS)


def _load_market_frame(path: Path, market: str) -> pd.DataFrame:
    frame = pd.read_pickle(path)
    out = frame.copy()
    if "base_trade_date" not in out.columns:
        if "trade_date" not in out.columns:
            raise ValueError(f"{path} has no base_trade_date/trade_date")
        out["base_trade_date"] = out["trade_date"]
    out["base_trade_date"] = pd.to_datetime(out["base_trade_date"], errors="coerce").dt.date.astype(str)
    out["trade_date"] = out["base_trade_date"]
    out["market"] = market.upper()
    return out


def _filter_valid_labels(frame: pd.DataFrame, *, start: str, end: str) -> pd.DataFrame:
    required = [LABEL_COLUMNS[key] for key in ("success", "target_hit", "stop_hit", "close_5d", "mfe_5d", "mae_5d")]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"required label columns missing: {missing}")
    date_mask = frame["base_trade_date"].between(start, end)
    label_mask = pd.Series(True, index=frame.index)
    for col in required:
        label_mask &= frame[col].notna()
    out = frame.loc[date_mask & label_mask].copy()
    out["_label_success"] = _as_bool(out[LABEL_COLUMNS["success"]])
    out["_label_target_hit"] = _as_bool(out[LABEL_COLUMNS["target_hit"]])
    out["_label_stop_hit"] = _as_bool(out[LABEL_COLUMNS["stop_hit"]])
    if LABEL_COLUMNS["stop_before_target"] in out.columns:
        out["_label_stop_before_target"] = _as_bool(out[LABEL_COLUMNS["stop_before_target"]])
    else:
        out["_label_stop_before_target"] = out["_label_stop_hit"] & ~out["_label_success"]
    out["_label_hit10"] = pd.to_numeric(out[LABEL_COLUMNS["mfe_5d"]], errors="coerce").ge(10.0).fillna(False)
    out["_close_5d"] = pd.to_numeric(out[LABEL_COLUMNS["close_5d"]], errors="coerce")
    out["_mfe_5d"] = pd.to_numeric(out[LABEL_COLUMNS["mfe_5d"]], errors="coerce")
    out["_mae_5d"] = pd.to_numeric(out[LABEL_COLUMNS["mae_5d"]], errors="coerce")
    return out.dropna(subset=["_close_5d", "_mfe_5d", "_mae_5d"]).copy()


def _feature_sets(frame: pd.DataFrame) -> Dict[str, Tuple[List[str], List[str]]]:
    safe_kis_num = _nonempty_columns([col for col in KIS_NUMERIC_FEATURES if not _is_leaky_feature(col)], frame)
    safe_kis_cat = _nonempty_columns([col for col in KIS_CATEGORICAL_FEATURES if not _is_leaky_feature(col)], frame)
    sidecar_num = _nonempty_columns(
        [
        col
        for col in list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES) + list(KIS_THEME_NEWS_NUMERIC_FEATURES)
        if not _is_leaky_feature(col)
        ],
        frame,
    )
    sidecar_cat = _nonempty_columns(
        [
        col
        for col in list(KIS_SIDECAR_CATEGORICAL_FEATURES) + list(KIS_THEME_NEWS_CATEGORICAL_FEATURES)
        if not _is_leaky_feature(col)
        ],
        frame,
    )
    prior_num = _nonempty_columns([col for col in CLOSE_FAILURE_RISK_NUMERIC if not _is_leaky_feature(col)], frame)
    prior_cat = _nonempty_columns([col for col in CLOSE_FAILURE_RISK_CATEGORICAL if not _is_leaky_feature(col)], frame)
    structural_cat = _nonempty_columns(
        [
            "ticker",
            "market",
            "primary_theme",
            "theme_source",
            "theme_inference_status",
            "scanner_timeframe_profile",
            "kr_universe_role",
        ],
        frame,
    )
    current_num = _nonempty_columns(
        [
            "day_return_pct",
            "volume_ratio",
            "turnover",
            "entry_reference_price",
            "feature_coverage_score",
        ],
        frame,
    )
    current_num = [col for col in current_num if not _is_leaky_feature(col)]
    return {
        "kis_daily_numeric": (_unique_existing(safe_kis_num + current_num, frame), []),
        "kis_daily_category": (_unique_existing(safe_kis_num + current_num, frame), _unique_existing(safe_kis_cat + structural_cat, frame)),
        "kis_sidecar_category": (_unique_existing(sidecar_num + current_num, frame), _unique_existing(sidecar_cat + structural_cat, frame)),
        "kis_failure_prior_numeric": (_unique_existing(safe_kis_num + current_num + prior_num, frame), []),
        "kis_failure_prior_category": (
            _unique_existing(safe_kis_num + current_num + prior_num, frame),
            _unique_existing(safe_kis_cat + structural_cat + prior_cat, frame),
        ),
    }


def _walk_windows(days: Sequence[str], *, min_train_days: int, test_days: int, max_folds: int, embargo_days: int) -> List[Window]:
    unique = sorted(dict.fromkeys(str(day) for day in days if str(day) and str(day) != "NaT"))
    windows: List[Window] = []
    end = len(unique)
    while end > min_train_days and len(windows) < max_folds:
        start = max(min_train_days, end - test_days)
        train_end = max(0, start - embargo_days)
        train = unique[:train_end]
        embargo = unique[train_end:start]
        test = unique[start:end]
        if train and test:
            windows.append(Window(fold=len(windows) + 1, train_days=train, test_days=test, embargo_days=embargo))
        end = start
    windows.reverse()
    return [Window(fold=i + 1, train_days=w.train_days, test_days=w.test_days, embargo_days=w.embargo_days) for i, w in enumerate(windows)]


def _sk_preprocessor(numeric: Sequence[str], categorical: Sequence[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", SimpleImputer(strategy="median"), list(numeric)),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", _onehot_encoder()),
                    ]
                ),
                list(categorical),
            ),
        ],
        remainder="drop",
    )


def _frame_for_native(frame: pd.DataFrame, numeric: Sequence[str], categorical: Sequence[str], *, backend: str) -> pd.DataFrame:
    cols = list(numeric) + list(categorical)
    out = frame.loc[:, cols].copy()
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in categorical:
        values = out[col].fillna("UNKNOWN").astype(str).replace("", "UNKNOWN")
        if backend == "lightgbm":
            out[col] = values.astype("category")
        else:
            out[col] = values
    return out


def _make_success_model(name: str, numeric: Sequence[str], categorical: Sequence[str]) -> Any | None:
    if name == "hist_gb":
        if categorical:
            return Pipeline(
                [
                    ("pre", _sk_preprocessor(numeric, categorical)),
                    (
                        "model",
                        HistGradientBoostingClassifier(
                            max_iter=160,
                            max_depth=4,
                            learning_rate=0.045,
                            l2_regularization=0.2,
                            random_state=42,
                        ),
                    ),
                ]
            )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_iter=160,
                        max_depth=4,
                        learning_rate=0.045,
                        l2_regularization=0.2,
                        random_state=42,
                    ),
                ),
            ]
        )
    if name == "lightgbm" and LGBMClassifier is not None:
        return LGBMClassifier(
            objective="binary",
            n_estimators=220,
            max_depth=5,
            num_leaves=24,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            min_child_samples=30,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    if name == "catboost" and CatBoostClassifier is not None:
        return CatBoostClassifier(
            iterations=220,
            depth=5,
            learning_rate=0.04,
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=42,
            allow_writing_files=False,
            verbose=False,
            thread_count=-1,
            auto_class_weights="Balanced",
        )
    return None


def _fit_predict_classifier(
    *,
    name: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    numeric: Sequence[str],
    categorical: Sequence[str],
    target: pd.Series,
) -> Tuple[pd.Series, Dict[str, Any]]:
    model = _make_success_model(name, numeric, categorical)
    if model is None:
        return pd.Series(np.nan, index=test.index), {"skipped": True, "reason": f"{name}_unavailable"}
    y = target.loc[train.index].astype(int)
    if y.nunique() < 2:
        return pd.Series(np.nan, index=test.index), {"skipped": True, "reason": "single_class_train"}
    started = perf_counter()
    if name == "lightgbm":
        x_train = _frame_for_native(train, numeric, categorical, backend="lightgbm")
        x_test = _frame_for_native(test, numeric, categorical, backend="lightgbm")
        model.fit(x_train, y, categorical_feature=list(categorical) if categorical else "auto")
        pred = model.predict_proba(x_test)[:, 1]
        importance = _feature_importance(model, list(numeric) + list(categorical))
    elif name == "catboost":
        x_train = _frame_for_native(train, numeric, categorical, backend="catboost")
        x_test = _frame_for_native(test, numeric, categorical, backend="catboost")
        model.fit(x_train, y, cat_features=list(categorical) if categorical else None)
        pred = model.predict_proba(x_test)[:, 1]
        importance = _feature_importance(model, list(numeric) + list(categorical))
    else:
        x_train = train.loc[:, list(numeric) + list(categorical)]
        x_test = test.loc[:, list(numeric) + list(categorical)]
        model.fit(x_train, y)
        pred = model.predict_proba(x_test)[:, 1]
        importance = {}
    elapsed = perf_counter() - started
    try:
        auc = roc_auc_score(test["_label_success"].astype(int), pred)
    except Exception:
        auc = None
    return pd.Series(pred, index=test.index), {"skipped": False, "elapsed_sec": _round(elapsed, 3), "test_auc": _round(auc, 6), "feature_importance_top": importance}


def _feature_importance(model: Any, features: Sequence[str], limit: int = 15) -> Dict[str, float]:
    try:
        values = model.feature_importances_
    except Exception:
        try:
            values = model.get_feature_importance()
        except Exception:
            return {}
    pairs = sorted(zip(features, values), key=lambda item: float(item[1]), reverse=True)[:limit]
    return {str(name): _round(value, 6) for name, value in pairs if _round(value, 6) is not None}


def _fit_predict_lgbm_ranker(
    *,
    train: pd.DataFrame,
    test: pd.DataFrame,
    numeric: Sequence[str],
    categorical: Sequence[str],
) -> Tuple[pd.Series, Dict[str, Any]]:
    if LGBMRanker is None:
        return pd.Series(np.nan, index=test.index), {"skipped": True, "reason": "lightgbm_ranker_unavailable"}
    ordered = train.sort_values(["base_trade_date", "ticker"]).copy()
    relevance = (
        ordered["_label_success"].astype(int) * 3
        + ordered["_label_hit10"].astype(int)
        - ordered["_label_stop_before_target"].astype(int)
    ).clip(lower=0)
    if relevance.nunique() < 2:
        return pd.Series(np.nan, index=test.index), {"skipped": True, "reason": "single_relevance_train"}
    groups = ordered.groupby("base_trade_date", sort=False).size().astype(int).tolist()
    model = LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=180,
        max_depth=5,
        num_leaves=24,
        learning_rate=0.04,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_samples=20,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    started = perf_counter()
    x_train = _frame_for_native(ordered, numeric, categorical, backend="lightgbm")
    x_test = _frame_for_native(test, numeric, categorical, backend="lightgbm")
    model.fit(x_train, relevance, group=groups, categorical_feature=list(categorical) if categorical else "auto")
    pred = model.predict(x_test)
    elapsed = perf_counter() - started
    return pd.Series(pred, index=test.index), {
        "skipped": False,
        "elapsed_sec": _round(elapsed, 3),
        "feature_importance_top": _feature_importance(model, list(numeric) + list(categorical)),
    }


def _selected_indices(frame: pd.DataFrame, score: pd.Series, *, topn: int, min_score: float | None = None) -> pd.Index:
    scored = frame.copy()
    scored["_score"] = pd.to_numeric(score.reindex(frame.index), errors="coerce")
    chunks: List[pd.Index] = []
    for _day, day_df in scored.groupby("base_trade_date", dropna=False):
        if min_score is not None:
            day_df = day_df[day_df["_score"].ge(min_score)]
        if day_df.empty:
            continue
        ordered = day_df.sort_values(["_score", "ticker"], ascending=[False, True], na_position="last").head(topn)
        if not ordered.empty:
            chunks.append(ordered.index)
    if not chunks:
        return pd.Index([])
    return chunks[0].append(chunks[1:]) if len(chunks) > 1 else chunks[0]


def _metric_summary(frame: pd.DataFrame, idx: pd.Index) -> Dict[str, Any]:
    sub = frame.loc[idx]
    if sub.empty:
        return {"n": 0, "active_days": 0, "active_runs": 0}
    success = sub["_label_success"].astype(bool)
    target_hit = sub["_label_target_hit"].astype(bool)
    stop_hit = sub["_label_stop_hit"].astype(bool)
    stop_before = sub["_label_stop_before_target"].astype(bool)
    hit10 = sub["_label_hit10"].astype(bool)
    close5 = sub["_close_5d"].astype(float)
    mfe5 = sub["_mfe_5d"].astype(float)
    mae5 = sub["_mae_5d"].astype(float)
    target_net = compute_net_return_pct(TARGET_PCT, TradableCostModel())
    exit_returns = close5.copy()
    if target_net is not None:
        exit_returns.loc[success[success].index] = float(target_net)
    exit_returns.loc[stop_before[stop_before].index] = -abs(STOP_PCT)
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "active_days": int(sub["base_trade_date"].nunique()),
        "active_runs": int(sub["run_id"].nunique()) if "run_id" in sub.columns else int(sub["base_trade_date"].nunique()),
        "hit5_dd10_5d_pct": _pct(success.mean()),
        "target_before_stop_5d_pct": _pct(success.mean()),
        "win_5d_pct": _pct(target_hit.mean()),
        "hit10_5d_pct": _pct(hit10.mean()),
        "stop5_pct": _pct(stop_hit.mean()),
        "stop_before_target_5d_pct": _pct(stop_before.mean()),
        "bad_path_pct": _pct((stop_before | close5.lt(0.0)).mean()),
        "avg_5d_pct": _round(close5.mean(), 6),
        "median_5d_pct": _round(close5.median(), 6),
        "min_5d_pct": _round(close5.min(), 6),
        "max_5d_pct": _round(close5.max(), 6),
        "avg_mfe_5d_pct": _round(mfe5.mean(), 6),
        "avg_mae_5d_pct": _round(mae5.mean(), 6),
        "min_min_low_5d_pct": _round(mae5.min(), 6),
        "max_mfe_5d_pct": _round(mfe5.max(), 6),
        "avg_ordered_exit_5d_pct": _round(exit_returns.mean(), 6),
        "min_ordered_exit_5d_pct": _round(exit_returns.min(), 6),
        "buy_premium_pct": BUY_PREMIUM_PCT,
    }
    return out


def _quality_score(metrics: Mapping[str, Any], gate: Mapping[str, Any]) -> float:
    hit = float(metrics.get("hit5_dd10_5d_pct") or 0.0)
    hit10 = float(metrics.get("hit10_5d_pct") or 0.0)
    avg_exit = float(metrics.get("avg_ordered_exit_5d_pct") or -20.0)
    avg_close = float(metrics.get("avg_5d_pct") or -20.0)
    stop = float(metrics.get("stop5_pct") or 100.0)
    bad = float(metrics.get("bad_path_pct") or 100.0)
    min_low = float(metrics.get("min_min_low_5d_pct") or -100.0)
    days = int(metrics.get("active_days") or 0)
    n = int(metrics.get("n") or 0)
    gate_bonus = 0.0
    if gate.get("production_ready"):
        gate_bonus += 500.0
    elif gate.get("shadow_display_allowed"):
        gate_bonus += 180.0
    tail_penalty = max(0.0, -10.0 - min_low) * 6.0
    return (
        gate_bonus
        + hit * 2.4
        + hit10 * 0.4
        + avg_exit * 8.0
        + avg_close * 1.2
        - stop * 1.0
        - bad * 0.7
        - tail_penalty
        + min(days, 30) * 0.8
        + min(n, 120) * 0.08
    )


def _baseline_scores(frame: pd.DataFrame) -> Dict[str, pd.Series]:
    scores: Dict[str, pd.Series] = {}
    candidates = {
        "baseline_momentum_volume": [
            ("kis_daily_return_5d_pct", 1.0),
            ("kis_day_change_pct", 0.4),
            ("kis_daily_close_location_pct", 0.03),
            ("kis_daily_volume_ratio_20d", 0.6),
            ("kis_whale_score", 0.05),
        ],
        "baseline_failure_prior_inverse": [
            ("close_failure_prior_ticker_risk_score", -1.0),
            ("close_failure_prior_theme_risk_score", -0.45),
            ("kis_daily_return_5d_pct", 0.6),
            ("kis_daily_volume_ratio_20d", 0.4),
        ],
    }
    for name, weights in candidates.items():
        score = pd.Series(0.0, index=frame.index, dtype=float)
        used = 0
        for col, weight in weights:
            if col not in frame.columns:
                continue
            value = pd.to_numeric(frame[col], errors="coerce")
            sample = value.dropna()
            if sample.empty:
                continue
            lo = float(sample.quantile(0.05))
            hi = float(sample.quantile(0.95))
            denom = hi - lo if hi != lo else 1.0
            score += ((value.clip(lo, hi) - lo) / denom).fillna(0.0) * float(weight)
            used += 1
        if used:
            scores[name] = score
    return scores


def _evaluate_score(
    *,
    market: str,
    frame: pd.DataFrame,
    score: pd.Series,
    identity: Dict[str, Any],
    topn_values: Sequence[int],
    min_score: float | None = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for topn in topn_values:
        idx = _selected_indices(frame, score, topn=int(topn), min_score=min_score)
        metrics = _metric_summary(frame, idx)
        gate_identity = {
            **identity,
            "market": market,
            "label": "touch5_dd10_5d",
            "feature_set": identity.get("feature_set") or "kis_best_effort",
            "topn": int(topn),
        }
        gate = evaluate_kis_model_gate(identity=gate_identity, metrics=metrics, market=market)
        rows.append(
            {
                "identity": gate_identity,
                "metrics": metrics,
                "gate": gate,
                "quality_score": _round(_quality_score(metrics, gate), 6),
            }
        )
    return rows


def _evaluate_model(
    *,
    market: str,
    frame: pd.DataFrame,
    model_name: str,
    feature_set_name: str,
    numeric: Sequence[str],
    categorical: Sequence[str],
    windows: Sequence[Window],
    topn_values: Sequence[int],
    two_stage_lambdas: Sequence[float],
) -> List[Dict[str, Any]]:
    effective_categorical = [] if model_name == "hist_gb" else list(categorical)
    predictions = pd.Series(np.nan, index=frame.index, dtype=float)
    stop_predictions = pd.Series(np.nan, index=frame.index, dtype=float)
    fold_rows: List[Dict[str, Any]] = []
    for window in windows:
        train = frame[frame["base_trade_date"].isin(window.train_days)].copy()
        test = frame[frame["base_trade_date"].isin(window.test_days)].copy()
        if train.empty or test.empty:
            continue
        pred, meta = _fit_predict_classifier(
            name=model_name,
            train=train,
            test=test,
            numeric=numeric,
            categorical=effective_categorical,
            target=frame["_label_success"],
        )
        if not bool(meta.get("skipped")):
            predictions.loc[pred.index] = pred
        stop_pred, stop_meta = _fit_predict_classifier(
            name=model_name,
            train=train,
            test=test,
            numeric=numeric,
            categorical=effective_categorical,
            target=frame["_label_stop_before_target"],
        )
        if not bool(stop_meta.get("skipped")):
            stop_predictions.loc[stop_pred.index] = stop_pred
        fold_rows.append(
            {
                "fold": int(window.fold),
                "train_days": len(window.train_days),
                "test_days": len(window.test_days),
                "embargo_days": len(window.embargo_days),
                "test_start": window.test_days[0] if window.test_days else None,
                "test_end": window.test_days[-1] if window.test_days else None,
                "success_model": meta,
                "stop_model": stop_meta,
            }
        )
    test_frame = frame.loc[predictions.dropna().index].copy()
    rows: List[Dict[str, Any]] = []
    if not test_frame.empty:
        identity = {
            "suite_version": REPORT_VERSION,
            "model": model_name,
            "score_mode": "success_probability",
            "feature_set": feature_set_name,
            "feature_count_numeric": len(numeric),
            "feature_count_categorical": len(effective_categorical),
            "fold_count": len(fold_rows),
        }
        rows.extend(
            _evaluate_score(
                market=market,
                frame=test_frame,
                score=predictions.loc[test_frame.index],
                identity=identity,
                topn_values=topn_values,
            )
        )
    risk_frame = frame.loc[predictions.dropna().index.intersection(stop_predictions.dropna().index)].copy()
    if not risk_frame.empty:
        for penalty in two_stage_lambdas:
            score = predictions.loc[risk_frame.index] - float(penalty) * stop_predictions.loc[risk_frame.index]
            identity = {
                "suite_version": REPORT_VERSION,
                "model": model_name,
                "score_mode": "success_minus_stop_risk",
                "stop_penalty_lambda": float(penalty),
                "feature_set": feature_set_name,
                "feature_count_numeric": len(numeric),
                "feature_count_categorical": len(effective_categorical),
                "fold_count": len(fold_rows),
            }
            rows.extend(
                _evaluate_score(
                    market=market,
                    frame=risk_frame,
                    score=score,
                    identity=identity,
                    topn_values=topn_values,
                )
            )
    for row in rows:
        row["folds"] = fold_rows
    return rows


def _evaluate_ranker(
    *,
    market: str,
    frame: pd.DataFrame,
    feature_set_name: str,
    numeric: Sequence[str],
    categorical: Sequence[str],
    windows: Sequence[Window],
    topn_values: Sequence[int],
) -> List[Dict[str, Any]]:
    predictions = pd.Series(np.nan, index=frame.index, dtype=float)
    fold_rows: List[Dict[str, Any]] = []
    for window in windows:
        train = frame[frame["base_trade_date"].isin(window.train_days)].copy()
        test = frame[frame["base_trade_date"].isin(window.test_days)].copy()
        pred, meta = _fit_predict_lgbm_ranker(train=train, test=test, numeric=numeric, categorical=categorical)
        if not bool(meta.get("skipped")):
            predictions.loc[pred.index] = pred
        fold_rows.append(
            {
                "fold": int(window.fold),
                "train_days": len(window.train_days),
                "test_days": len(window.test_days),
                "embargo_days": len(window.embargo_days),
                "test_start": window.test_days[0] if window.test_days else None,
                "test_end": window.test_days[-1] if window.test_days else None,
                "ranker": meta,
            }
        )
    test_frame = frame.loc[predictions.dropna().index].copy()
    if test_frame.empty:
        return []
    identity = {
        "suite_version": REPORT_VERSION,
        "model": "lightgbm_ranker",
        "score_mode": "daily_lambdarank",
        "feature_set": feature_set_name,
        "feature_count_numeric": len(numeric),
        "feature_count_categorical": len(categorical),
        "fold_count": len(fold_rows),
    }
    rows = _evaluate_score(
        market=market,
        frame=test_frame,
        score=predictions.loc[test_frame.index],
        identity=identity,
        topn_values=topn_values,
    )
    for row in rows:
        row["folds"] = fold_rows
    return rows


def _market_report(
    *,
    market: str,
    frame: pd.DataFrame,
    models: Sequence[str],
    feature_set_names: Sequence[str],
    topn_values: Sequence[int],
    min_train_days: int,
    test_days: int,
    max_folds: int,
    embargo_days: int,
    two_stage_lambdas: Sequence[float],
) -> Dict[str, Any]:
    days = sorted(frame["base_trade_date"].dropna().astype(str).unique().tolist())
    windows = _walk_windows(days, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds, embargo_days=embargo_days)
    features = _feature_sets(frame)
    valid_feature_sets = {name: value for name, value in features.items() if name in set(feature_set_names)}
    baseline_rows: List[Dict[str, Any]] = []
    for score_name, score in _baseline_scores(frame).items():
        baseline_rows.extend(
            _evaluate_score(
                market=market,
                frame=frame,
                score=score,
                identity={
                    "suite_version": REPORT_VERSION,
                    "model": score_name,
                    "score_mode": "deterministic_baseline",
                    "feature_set": "kis_manual_score",
                    "fold_count": 0,
                },
                topn_values=topn_values,
            )
        )
    candidates: List[Dict[str, Any]] = baseline_rows[:]
    for feature_set_name, (numeric, categorical) in valid_feature_sets.items():
        if not numeric and not categorical:
            continue
        for model_name in models:
            if model_name == "lightgbm_ranker":
                candidates.extend(
                    _evaluate_ranker(
                        market=market,
                        frame=frame,
                        feature_set_name=feature_set_name,
                        numeric=numeric,
                        categorical=categorical,
                        windows=windows,
                        topn_values=topn_values,
                    )
                )
            else:
                candidates.extend(
                    _evaluate_model(
                        market=market,
                        frame=frame,
                        model_name=model_name,
                        feature_set_name=feature_set_name,
                        numeric=numeric,
                        categorical=categorical,
                        windows=windows,
                        topn_values=topn_values,
                        two_stage_lambdas=two_stage_lambdas,
                    )
                )
    ranked = sorted(candidates, key=lambda item: float(item.get("quality_score") or -999999.0), reverse=True)
    best = ranked[0] if ranked else None
    return {
        "market": market,
        "rows": int(len(frame)),
        "days": int(len(days)),
        "date_min": days[0] if days else None,
        "date_max": days[-1] if days else None,
        "windows": [
            {
                "fold": w.fold,
                "train_days": len(w.train_days),
                "test_days": len(w.test_days),
                "embargo_days": len(w.embargo_days),
                "test_start": w.test_days[0] if w.test_days else None,
                "test_end": w.test_days[-1] if w.test_days else None,
            }
            for w in windows
        ],
        "feature_sets": {
            name: {"numeric": len(cols[0]), "categorical": len(cols[1])}
            for name, cols in valid_feature_sets.items()
        },
        "baseline_count": len(baseline_rows),
        "candidate_count": len(ranked),
        "best": best,
        "top_candidates": ranked[:20],
        "production_ready": bool(best and best.get("gate", {}).get("production_ready")),
        "shadow_display_allowed": bool(best and best.get("gate", {}).get("shadow_display_allowed")),
    }


def _write_markdown(report: Mapping[str, Any], path: Path) -> None:
    lines = [
        f"# KIS historical best-effort suite",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source: `{report.get('source')}`",
        f"- label: `+{TARGET_PCT:g}% target touch within 5D after +{BUY_PREMIUM_PCT:g}% buy premium, with -{STOP_PCT:g}% stop path risk`",
        f"- validation: walk-forward with `{report.get('embargo_days')}` trading-day embargo",
        "",
    ]
    for market, item in (report.get("markets") or {}).items():
        best = item.get("best") or {}
        ident = best.get("identity") or {}
        metrics = best.get("metrics") or {}
        gate = best.get("gate") or {}
        lines.extend(
            [
                f"## {market}",
                "",
                f"- rows/days: `{item.get('rows')}` / `{item.get('days')}` (`{item.get('date_min')}`..`{item.get('date_max')}`)",
                f"- candidates: `{item.get('candidate_count')}`",
                f"- best: `{ident.get('model')}` / `{ident.get('score_mode')}` / `{ident.get('feature_set')}` / topN `{ident.get('topn')}`",
                f"- gate: `{gate.get('status')}` production=`{gate.get('production_ready')}` shadow=`{gate.get('shadow_display_allowed')}`",
                f"- hit5_dd10: `{metrics.get('hit5_dd10_5d_pct')}`",
                f"- hit10: `{metrics.get('hit10_5d_pct')}`",
                f"- stop5: `{metrics.get('stop5_pct')}`",
                f"- bad_path: `{metrics.get('bad_path_pct')}`",
                f"- avg close 5D: `{metrics.get('avg_5d_pct')}`",
                f"- avg exit-policy 5D: `{metrics.get('avg_ordered_exit_5d_pct')}`",
                f"- min low 5D: `{metrics.get('min_min_low_5d_pct')}`",
                f"- blockers: `{gate.get('blocking_reasons')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Decision",
            "",
            f"- status: `{report.get('decision', {}).get('status')}`",
            f"- action: `{report.get('decision', {}).get('recommended_action')}`",
            f"- reason: `{report.get('decision', {}).get('reason')}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    started = perf_counter()
    markets: Dict[str, Any] = {}
    for market in args.markets:
        market_key = market.upper()
        default_path = (
            PROJECT_ROOT
            / "runtime_state"
            / "reports"
            / "learning"
            / f"kis_historical_universe_prepared_{market_key.lower()}_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}.pkl"
        )
        path = Path(args.input_paths.get(market_key, default_path)) if isinstance(args.input_paths, dict) else default_path
        frame = _load_market_frame(path, market_key)
        valid = _filter_valid_labels(frame, start=args.start_date, end=args.end_date)
        markets[market_key] = _market_report(
            market=market_key,
            frame=valid,
            models=args.models,
            feature_set_names=args.feature_sets,
            topn_values=args.topn,
            min_train_days=args.min_train_days,
            test_days=args.test_days,
            max_folds=args.max_folds,
            embargo_days=args.embargo_days,
            two_stage_lambdas=args.stop_penalty_lambdas,
        )
    all_shadow = bool(markets) and all(bool(item.get("shadow_display_allowed")) for item in markets.values())
    all_prod = bool(markets) and all(bool(item.get("production_ready")) for item in markets.values())
    if all_prod:
        status = "production_ready"
        action = "eligible_for_controlled_production_promotion"
        reason = "all required markets passed KIS production gates under walk-forward validation"
    elif all_shadow:
        status = "shadow_ready"
        action = "show_shadow_only_with_risk_review"
        reason = "all required markets cleared shadow gates but at least one production gate remains blocked"
    else:
        status = "blocked"
        action = "do_not_show_as_trade_candidate"
        reason = "one or more required markets failed shadow or production gates under best-effort validation"
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "source": "actual_kis_historical_universe_prepared_cache",
        "dummy_data_used": False,
        "markets_requested": list(args.markets),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "target_pct": TARGET_PCT,
        "stop_pct": STOP_PCT,
        "buy_premium_pct": BUY_PREMIUM_PCT,
        "min_train_days": args.min_train_days,
        "test_days": args.test_days,
        "max_folds": args.max_folds,
        "embargo_days": args.embargo_days,
        "models": list(args.models),
        "feature_sets": list(args.feature_sets),
        "topn": list(args.topn),
        "stop_penalty_lambdas": list(args.stop_penalty_lambdas),
        "elapsed_sec": _round(perf_counter() - started, 3),
        "markets": markets,
        "decision": {
            "status": status,
            "recommended_action": action,
            "reason": reason,
            "all_required_markets_shadow_display_allowed": all_shadow,
            "all_required_markets_production_ready": all_prod,
        },
        "research_basis": {
            "lightgbm_docs": "https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMClassifier.html",
            "lightgbm_ranker_docs": "https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMRanker.html",
            "catboost_docs": "https://catboost.ai/docs/en/concepts/python-reference_catboostclassifier",
            "sklearn_histgb_docs": "https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default=DEFAULT_START)
    parser.add_argument("--end-date", default=DEFAULT_END)
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"])
    parser.add_argument("--models", nargs="+", default=["hist_gb", "lightgbm", "catboost", "lightgbm_ranker"])
    parser.add_argument(
        "--feature-sets",
        nargs="+",
        default=["kis_daily_numeric", "kis_daily_category", "kis_sidecar_category", "kis_failure_prior_numeric", "kis_failure_prior_category"],
    )
    parser.add_argument("--topn", nargs="+", type=int, default=[1, 3, 5])
    parser.add_argument("--min-train-days", type=int, default=35)
    parser.add_argument("--test-days", type=int, default=12)
    parser.add_argument("--max-folds", type=int, default=5)
    parser.add_argument("--embargo-days", type=int, default=5)
    parser.add_argument("--stop-penalty-lambdas", nargs="+", type=float, default=[0.5, 1.0, 1.5, 2.0])
    parser.add_argument("--output-json", default="runtime_state/reports/learning/kis_historical_best_effort_suite_20260101_20260610.json")
    parser.add_argument("--output-md", default="runtime_state/reports/learning/kis_historical_best_effort_suite_20260101_20260610.md")
    parser.add_argument("--input-path", action="append", default=[], help="MARKET=path override")
    args = parser.parse_args()
    args.input_paths = {}
    for raw in args.input_path:
        if "=" not in str(raw):
            raise ValueError("--input-path must be MARKET=path")
        market, path = str(raw).split("=", 1)
        args.input_paths[market.strip().upper()] = path.strip()
    return args


def main() -> None:
    args = parse_args()
    report = run(args)
    out_json = PROJECT_ROOT / args.output_json
    out_md = PROJECT_ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    _write_markdown(report, out_md)
    print(json.dumps({"output_json": str(out_json), "output_md": str(out_md), "decision": report.get("decision")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
