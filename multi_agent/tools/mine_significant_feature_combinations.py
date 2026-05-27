#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations, count
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

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
    _split_days,
)

REPORT_VERSION = "significant_feature_combo_mining_v2"

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
]

OUTCOME_OR_ID_COLUMNS = {
    "id",
    "ticker",
    "stock_name",
    "created_at",
    "recommended_at",
    "outcome_recorded_at",
    "base_trade_date",
    "source_ref",
    "rationale",
    "strategy",
    "return_1d_pct",
    "return_2d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "return_14d_pct",
    "return_30d_pct",
    "return_10m_pct",
    "return_30m_pct",
    "return_1h_pct",
    "return_close_pct",
    "max_high_return_5d_pct",
    "max_return_observed_pct",
    "min_return_observed_pct",
    "mfe_intraday_pct",
    "mae_intraday_pct",
    "mfe_5d_pct",
    "mae_5d_pct",
    "hit_5pct_within_5d",
    "hit_5pct_within_5d_at",
    "target_before_stop_5d",
    "stop_before_target_5d",
    "target_hit_at_5d",
    "stop_hit_at_5d",
    "label_win_close",
    "label_win_1d",
    "label_win_3d",
    "label_hit_5pct",
    "label_hit_10pct",
    "label_hit_20pct",
    "label_hit_50pct",
    "label_hit_100pct",
    "label_hit_5pct_within_5d",
    "label_stop_loss_3pct",
    "label_stop_loss_5pct",
    "latest_return_pct",
    "outcome_status",
    "outcome_path_terminal_status",
    "outcome_path_label_version",
    "swing_target_label_version",
    "target_definition",
    "target_return_source",
    "performance_updated_at",
}


@dataclass(frozen=True)
class Predicate:
    key: str
    feature: str
    label: str
    direction: str
    value: Any
    mask: np.ndarray


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def _metric_value(metrics: Dict[str, Any], key: str, default: float = 0.0) -> float:
    return _safe_float(metrics.get(key), default)


def _metrics(df: pd.DataFrame, mask: pd.Series) -> Dict[str, Any]:
    if isinstance(mask, pd.Series):
        mask_values = mask.reindex(df.index).fillna(False).to_numpy(dtype=bool)
    else:
        mask_values = np.asarray(mask, dtype=bool)
    sub = df.loc[mask_values]
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).mean()) if len(sub) else None,
        "stop5_pct": _pct(sub.get("stop5_proxy", pd.Series(False, index=sub.index)).mean()) if len(sub) else None,
    }
    for horizon, col in [("1d", "return_1d_pct"), ("3d", "return_3d_pct"), ("5d", "return_5d_pct")]:
        raw = pd.to_numeric(sub.get(col, pd.Series(index=sub.index, dtype=float)), errors="coerce")
        valid = raw.notna()
        horizon_sub = sub.loc[valid]
        values = raw.loc[valid]
        out[f"n_{horizon}"] = int(len(values))
        out[f"active_days_{horizon}"] = int(horizon_sub["trade_date"].nunique()) if len(horizon_sub) and "trade_date" in horizon_sub.columns else 0
        out[f"bad_path_{horizon}_pct"] = _pct(horizon_sub.get("bad_path", pd.Series(False, index=horizon_sub.index)).mean()) if len(horizon_sub) else None
        out[f"stop5_{horizon}_pct"] = _pct(horizon_sub.get("stop5_proxy", pd.Series(False, index=horizon_sub.index)).mean()) if len(horizon_sub) else None
        out[f"win_{horizon}_pct"] = _pct(values.gt(0).mean()) if len(values) else None
        out[f"avg_{horizon}_pct"] = _round(values.mean()) if len(values) else None
        out[f"median_{horizon}_pct"] = _round(values.median()) if len(values) else None
        out[f"min_{horizon}_pct"] = _round(values.min()) if len(values) else None
        out[f"max_{horizon}_pct"] = _round(values.max()) if len(values) else None
    return out


def _score(metrics: Dict[str, Any], *, horizon: str) -> float:
    n = int(metrics.get(f"n_{horizon}") or 0)
    days = int(metrics.get(f"active_days_{horizon}") or 0)
    win = _metric_value(metrics, f"win_{horizon}_pct")
    avg = _metric_value(metrics, f"avg_{horizon}_pct", -20.0)
    min_ret = _metric_value(metrics, f"min_{horizon}_pct", -30.0)
    bad = _metric_value(metrics, f"bad_path_{horizon}_pct", _metric_value(metrics, "bad_path_pct", 100.0))
    stop = _metric_value(metrics, f"stop5_{horizon}_pct", _metric_value(metrics, "stop5_pct", 100.0))
    support_bonus = min(n, 80) * 0.04 + min(days, 25) * 0.25
    drawdown_penalty = max(0.0, -min_ret - 8.0) * 0.25
    return win + avg * 2.0 - bad * 0.75 - stop * 0.45 - drawdown_penalty + support_bonus


def _is_production_safe(metrics: Dict[str, Any], *, horizon: str, min_n: int, min_days: int) -> bool:
    return (
        int(metrics.get(f"n_{horizon}") or 0) >= min_n
        and int(metrics.get(f"active_days_{horizon}") or 0) >= min_days
        and _metric_value(metrics, f"win_{horizon}_pct") >= 70.0
        and _metric_value(metrics, f"avg_{horizon}_pct", -999.0) > 0.0
        and _metric_value(metrics, f"bad_path_{horizon}_pct", 100.0) <= 35.0
        and _metric_value(metrics, f"stop5_{horizon}_pct", 100.0) <= 25.0
    )


def _is_train_stable(metrics: Dict[str, Any], *, horizon: str, min_n: int, min_days: int) -> bool:
    return (
        int(metrics.get(f"n_{horizon}") or 0) >= min_n
        and int(metrics.get(f"active_days_{horizon}") or 0) >= min_days
        and _metric_value(metrics, f"win_{horizon}_pct") >= 60.0
        and _metric_value(metrics, f"avg_{horizon}_pct", -999.0) > 0.0
        and _metric_value(metrics, f"bad_path_{horizon}_pct", 100.0) <= 45.0
        and _metric_value(metrics, f"stop5_{horizon}_pct", 100.0) <= 40.0
    )


def _candidate_numeric_columns(df: pd.DataFrame) -> List[str]:
    columns = []
    for col in BASE_NUMERIC + REGIME_NUMERIC + FLOW_NUMERIC + EXTRA_NUMERIC:
        if col in df.columns and col not in OUTCOME_OR_ID_COLUMNS:
            values = pd.to_numeric(df[col], errors="coerce")
            if values.notna().sum() >= 80 and values.nunique(dropna=True) >= 4:
                columns.append(col)
    return list(dict.fromkeys(columns))


def _candidate_categorical_columns(df: pd.DataFrame, *, include_primary_theme: bool) -> List[str]:
    base = BASE_CATEGORICAL + EXTRA_CATEGORICAL + ["volume_confirmed", "flow_consensus_buying", "retail_dominant", "exception_leader", "core_trend_flag_bool", "explosive_leader_flag_bool"]
    if include_primary_theme:
        base += THEME_CATEGORICAL
    else:
        base += [col for col in THEME_CATEGORICAL if col != "primary_theme"]
    columns = []
    for col in base:
        if col in df.columns and col not in OUTCOME_OR_ID_COLUMNS:
            series = df[col]
            if series.notna().sum() >= 80 and 1 < series.nunique(dropna=True) <= 80:
                columns.append(col)
    return list(dict.fromkeys(columns))


def _predicate_key(feature: str, direction: str, value: Any) -> str:
    return f"{feature}|{direction}|{value}"


def _build_numeric_predicates(
    df: pd.DataFrame,
    col: str,
    *,
    basis_mask: np.ndarray,
    min_support: int,
    max_support_ratio: float,
) -> List[Predicate]:
    values = pd.to_numeric(df[col], errors="coerce")
    basis_values = values.loc[basis_mask]
    if basis_values.notna().sum() < min_support:
        return []
    thresholds = set()
    for q in [0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85]:
        val = basis_values.quantile(q)
        if pd.notna(val):
            thresholds.add(round(float(val), 6))
    if col == "priority_rank":
        thresholds.update([1.0, 3.0, 5.0, 10.0, 20.0])
    if col == "volume_ratio":
        thresholds.update([0.8, 1.0, 1.2, 1.5, 2.0, 3.0])
    if col in {"foreigner", "institution", "retail", "foreign_flow", "institution_flow", "retail_flow", "foreigner_1d", "institution_1d", "foreigner_3d", "institution_3d", "foreigner_10d", "institution_10d", "whale_flow_1d", "whale_flow_3d", "whale_flow_10d"}:
        thresholds.add(0.0)
    predicates: List[Predicate] = []
    max_support = max(min_support, int(int(basis_mask.sum()) * max_support_ratio))
    for threshold in sorted(thresholds):
        for direction, op in [(">=", values.ge), ("<=", values.le)]:
            mask = op(threshold).fillna(False)
            mask_values = mask.to_numpy(dtype=bool)
            support = int((mask_values & basis_mask).sum())
            if min_support <= support <= max_support:
                label = f"{col} {direction} {threshold:g}"
                predicates.append(Predicate(_predicate_key(col, direction, threshold), col, label, direction, threshold, mask_values))
    return predicates


def _build_categorical_predicates(
    df: pd.DataFrame,
    col: str,
    *,
    basis_mask: np.ndarray,
    min_support: int,
    max_support_ratio: float,
) -> List[Predicate]:
    series = df[col].fillna("UNKNOWN").astype(str).str.strip()
    basis = series.loc[basis_mask]
    counts = basis.value_counts(dropna=False)
    max_support = max(min_support, int(int(basis_mask.sum()) * max_support_ratio))
    predicates: List[Predicate] = []
    for value, support in counts.items():
        if not value or value.lower() in {"nan", "none", "unknown", ""}:
            continue
        support = int(support)
        if min_support <= support <= max_support:
            mask = series.eq(value).to_numpy(dtype=bool)
            label = f"{col} == {value}"
            predicates.append(Predicate(_predicate_key(col, "==", value), col, label, "==", value, mask))
    return predicates


def _build_predicates(
    df: pd.DataFrame,
    *,
    basis_mask: np.ndarray,
    min_support: int,
    max_support_ratio: float,
    include_primary_theme: bool,
) -> List[Predicate]:
    predicates: List[Predicate] = []
    for col in _candidate_numeric_columns(df):
        predicates.extend(_build_numeric_predicates(df, col, basis_mask=basis_mask, min_support=min_support, max_support_ratio=max_support_ratio))
    for col in _candidate_categorical_columns(df, include_primary_theme=include_primary_theme):
        predicates.extend(_build_categorical_predicates(df, col, basis_mask=basis_mask, min_support=min_support, max_support_ratio=max_support_ratio))

    unique: Dict[str, Predicate] = {}
    for pred in predicates:
        unique.setdefault(pred.key, pred)
    return list(unique.values())


def _build_predicates_with_diagnostics(
    df: pd.DataFrame,
    *,
    basis_mask: np.ndarray,
    min_support: int,
    max_support_ratio: float,
    include_primary_theme: bool,
) -> Tuple[List[Predicate], Dict[str, Any]]:
    numeric_columns = _candidate_numeric_columns(df)
    categorical_columns = _candidate_categorical_columns(df, include_primary_theme=include_primary_theme)
    predicates: List[Predicate] = []
    by_feature: Dict[str, int] = {}
    numeric_counts: Dict[str, int] = {}
    categorical_counts: Dict[str, int] = {}

    for col in numeric_columns:
        built = _build_numeric_predicates(
            df,
            col,
            basis_mask=basis_mask,
            min_support=min_support,
            max_support_ratio=max_support_ratio,
        )
        numeric_counts[col] = len(built)
        by_feature[col] = len(built)
        predicates.extend(built)
    for col in categorical_columns:
        built = _build_categorical_predicates(
            df,
            col,
            basis_mask=basis_mask,
            min_support=min_support,
            max_support_ratio=max_support_ratio,
        )
        categorical_counts[col] = len(built)
        by_feature[col] = len(built)
        predicates.extend(built)

    unique: Dict[str, Predicate] = {}
    for pred in predicates:
        unique.setdefault(pred.key, pred)
    diagnostics = {
        "candidate_feature_counts": {
            "numeric": len(numeric_columns),
            "categorical": len(categorical_columns),
            "total": len(numeric_columns) + len(categorical_columns),
        },
        "candidate_numeric_features": numeric_columns,
        "candidate_categorical_features": categorical_columns,
        "predicate_counts": {
            "raw": len(predicates),
            "unique": len(unique),
            "duplicates": max(0, len(predicates) - len(unique)),
            "numeric": sum(numeric_counts.values()),
            "categorical": sum(categorical_counts.values()),
            "by_feature": by_feature,
        },
    }
    return list(unique.values()), diagnostics


def _combo_metrics(df: pd.DataFrame, predicates: Sequence[Predicate], train_mask: np.ndarray, test_mask: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any], np.ndarray]:
    if not predicates:
        mask = np.ones(len(df), dtype=bool)
    else:
        mask = np.asarray(predicates[0].mask, dtype=bool).copy()
        for pred in predicates[1:]:
            mask &= np.asarray(pred.mask, dtype=bool)
    return _metrics(df, mask & train_mask), _metrics(df, mask & test_mask), mask


def _feature_conflict(existing: Sequence[Predicate], new_predicate: Predicate) -> bool:
    return any(pred.feature == new_predicate.feature for pred in existing)


def _combo_payload(
    *,
    market: str,
    scope: str,
    cut_day: str | None,
    horizon: str,
    combo_id: int,
    predicates: Sequence[Predicate],
    train: Dict[str, Any],
    test: Dict[str, Any],
    min_train: int,
    min_test: int,
    min_days: int,
) -> Dict[str, Any]:
    return {
        "combo_id": combo_id,
        "market": market,
        "scope": scope,
        "cut_day": cut_day,
        "horizon": horizon,
        "term_count": len(predicates),
        "conditions": [pred.label for pred in predicates],
        "features": [pred.feature for pred in predicates],
        "train": train,
        "test": test,
        "train_score": _round(_score(train, horizon=horizon), 4),
        "test_score": _round(_score(test, horizon=horizon), 4),
        "holdout_safe": _is_production_safe(test, horizon=horizon, min_n=min_test, min_days=min_days),
        "train_stable": _is_train_stable(train, horizon=horizon, min_n=min_train, min_days=min_days),
        "production_safe": _is_production_safe(test, horizon=horizon, min_n=min_test, min_days=min_days)
        and _is_train_stable(train, horizon=horizon, min_n=min_train, min_days=min_days),
    }


def _gate_rejection_reasons(payload: Dict[str, Any], *, horizon: str, min_train: int, min_test: int, min_days: int) -> List[str]:
    train = payload.get("train") or {}
    test = payload.get("test") or {}
    reasons: List[str] = []
    if int(train.get(f"n_{horizon}") or 0) < min_train:
        reasons.append("train_n")
    if int(train.get(f"active_days_{horizon}") or 0) < min_days:
        reasons.append("train_days")
    if _metric_value(train, f"win_{horizon}_pct") < 60.0:
        reasons.append("train_win")
    if _metric_value(train, f"avg_{horizon}_pct", -999.0) <= 0.0:
        reasons.append("train_avg")
    if _metric_value(train, f"bad_path_{horizon}_pct", 100.0) > 45.0:
        reasons.append("train_bad_path")
    if _metric_value(train, f"stop5_{horizon}_pct", 100.0) > 40.0:
        reasons.append("train_stop5")
    if int(test.get(f"n_{horizon}") or 0) < min_test:
        reasons.append("test_n")
    if int(test.get(f"active_days_{horizon}") or 0) < min_days:
        reasons.append("test_days")
    if _metric_value(test, f"win_{horizon}_pct") < 70.0:
        reasons.append("test_win")
    if _metric_value(test, f"avg_{horizon}_pct", -999.0) <= 0.0:
        reasons.append("test_avg")
    if _metric_value(test, f"bad_path_{horizon}_pct", 100.0) > 35.0:
        reasons.append("test_bad_path")
    if _metric_value(test, f"stop5_{horizon}_pct", 100.0) > 25.0:
        reasons.append("test_stop5")
    return reasons


def _empty_scope_diagnostics(*, market: str, scope: str, rows: int, trade_days: int, reason: str | None = None) -> Dict[str, Any]:
    return {
        "market": market,
        "scope": scope,
        "rows": int(rows),
        "trade_days": int(trade_days),
        "skip_reason": reason,
        "split": {},
        "candidate_feature_counts": {"numeric": 0, "categorical": 0, "total": 0},
        "predicate_counts": {"raw": 0, "unique": 0, "after_support_screen": 0},
        "singleton_filters": {},
        "beam_pruning": {},
        "gate_rejections": {},
        "exact_exhaustive": {},
    }


def _exact_exhaustive_verifier(
    scoped: pd.DataFrame,
    predicates: Sequence[Predicate],
    train_values: np.ndarray,
    test_values: np.ndarray,
    *,
    market: str,
    scope: str,
    cut_day: str | None,
    horizons: Sequence[str],
    min_train: int,
    min_test: int,
    min_days: int,
    max_terms: int,
    max_predicates: int,
    max_combos: int,
) -> Dict[str, Any]:
    if max_predicates <= 0:
        return {"enabled": False, "reason": "disabled"}
    if len(predicates) > max_predicates:
        return {"enabled": False, "reason": "predicate_count_over_cap", "predicate_count": len(predicates), "cap": max_predicates}
    checked_by_horizon: Dict[str, Dict[str, Any]] = {}
    term_cap = max(1, min(max_terms, 4))
    for horizon in horizons:
        checked = 0
        feature_conflicts = 0
        sample_eligible = 0
        production_safe = 0
        gate_rejections: Counter[str] = Counter()
        best: List[Dict[str, Any]] = []
        stopped_by_cap = False
        for term_count in range(1, term_cap + 1):
            for combo in combinations(predicates, term_count):
                if any(a.feature == b.feature for idx, a in enumerate(combo) for b in combo[idx + 1 :]):
                    feature_conflicts += 1
                    continue
                checked += 1
                train, test, _mask = _combo_metrics(scoped, combo, train_values, test_values)
                if int(train.get(f"n_{horizon}") or 0) >= min_train and int(test.get(f"n_{horizon}") or 0) >= min_test:
                    sample_eligible += 1
                payload = _combo_payload(
                    market=market,
                    scope=scope,
                    cut_day=cut_day,
                    horizon=horizon,
                    combo_id=checked,
                    predicates=combo,
                    train=train,
                    test=test,
                    min_train=min_train,
                    min_test=min_test,
                    min_days=min_days,
                )
                if payload.get("production_safe"):
                    production_safe += 1
                else:
                    gate_rejections.update(_gate_rejection_reasons(payload, horizon=horizon, min_train=min_train, min_test=min_test, min_days=min_days))
                best.append(payload)
                if checked >= max_combos:
                    stopped_by_cap = True
                    break
            if stopped_by_cap:
                break
        best.sort(key=_sort_key, reverse=True)
        checked_by_horizon[horizon] = {
            "checked_combinations": checked,
            "feature_conflict_combinations": feature_conflicts,
            "sample_eligible_combinations": sample_eligible,
            "production_safe_combinations": production_safe,
            "stopped_by_cap": stopped_by_cap,
            "gate_rejections": dict(gate_rejections.most_common()),
            "top_combinations": best[:10],
        }
    return {
        "enabled": True,
        "predicate_count": len(predicates),
        "max_predicates": max_predicates,
        "max_combos": max_combos,
        "max_terms": term_cap,
        "horizons": checked_by_horizon,
    }


def _mine_scope(
    df: pd.DataFrame,
    *,
    market: str,
    scope: str,
    train_ratio: float,
    horizons: Sequence[str],
    min_train: int,
    min_test: int,
    min_days: int,
    min_support: int,
    beam_width: int,
    max_terms: int,
    include_primary_theme: bool,
    exact_exhaustive_max_predicates: int = 0,
    exact_exhaustive_max_combos: int = 50000,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    scoped = df.copy()
    train_mask, test_mask, cut_day = _split_days(scoped, train_ratio)
    train_values = train_mask.to_numpy(dtype=bool)
    test_values = test_mask.to_numpy(dtype=bool)
    diagnostics = _empty_scope_diagnostics(
        market=market,
        scope=scope,
        rows=len(scoped),
        trade_days=scoped["trade_date"].nunique() if "trade_date" in scoped.columns else 0,
    )
    diagnostics["split"] = {
        "cut_day": cut_day,
        "train_rows": int(train_values.sum()),
        "test_rows": int(test_values.sum()),
        "train_days": int(scoped.loc[train_values, "trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
        "test_days": int(scoped.loc[test_values, "trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
    }
    if train_values.sum() < min_train or test_values.sum() < min_test:
        diagnostics["skip_reason"] = "split_below_min_rows"
        return [], diagnostics

    predicate_support = max(3, min_support)
    predicates, predicate_diag = _build_predicates_with_diagnostics(
        scoped.copy(),
        basis_mask=train_values,
        min_support=predicate_support,
        max_support_ratio=0.92,
        include_primary_theme=include_primary_theme,
    )
    diagnostics.update(predicate_diag)
    scoped_predicates = []
    predicate_screen = Counter()
    for pred in predicates:
        mask = np.asarray(pred.mask, dtype=bool)
        train_support = int((mask & train_values).sum())
        test_support = int((mask & test_values).sum())
        if train_support >= min_train and test_support >= min_test:
            scoped_predicates.append(Predicate(pred.key, pred.feature, pred.label, pred.direction, pred.value, mask))
            predicate_screen["kept"] += 1
        else:
            if train_support < min_train:
                predicate_screen["rejected_train_support"] += 1
            if test_support < min_test:
                predicate_screen["rejected_test_support"] += 1
    diagnostics["predicate_counts"]["after_support_screen"] = len(scoped_predicates)
    diagnostics["predicate_support_screen"] = dict(predicate_screen)
    diagnostics["exact_exhaustive"] = _exact_exhaustive_verifier(
        scoped,
        scoped_predicates,
        train_values,
        test_values,
        market=market,
        scope=scope,
        cut_day=cut_day,
        horizons=horizons,
        min_train=min_train,
        min_test=min_test,
        min_days=min_days,
        max_terms=max_terms,
        max_predicates=exact_exhaustive_max_predicates,
        max_combos=exact_exhaustive_max_combos,
    )

    results: List[Dict[str, Any]] = []
    combo_counter = count(1)
    diagnostics["singleton_filters"] = {}
    diagnostics["beam_pruning"] = {}
    for horizon in horizons:
        seen = set()
        singleton_rows = []
        singleton_diag = Counter({"evaluated": len(scoped_predicates)})
        for pred in scoped_predicates:
            train, test, _mask = _combo_metrics(scoped, [pred], train_values, test_values)
            train_n_ok = int(train.get(f"n_{horizon}") or 0) >= min_train
            train_days_ok = int(train.get(f"active_days_{horizon}") or 0) >= min_days
            if train_n_ok and train_days_ok:
                singleton_rows.append((_score(train, horizon=horizon), (pred,), train, test))
                singleton_diag["passed_train_filter"] += 1
            else:
                if not train_n_ok:
                    singleton_diag["rejected_train_n"] += 1
                if not train_days_ok:
                    singleton_diag["rejected_train_days"] += 1
        singleton_rows.sort(key=lambda row: row[0], reverse=True)
        base_pool = [row[1][0] for row in singleton_rows[: max(beam_width * 2, beam_width)]]
        beam = singleton_rows[:beam_width]
        singleton_diag["base_pool"] = len(base_pool)
        singleton_diag["initial_beam"] = len(beam)
        singleton_diag["pruned_by_initial_beam"] = max(0, len(singleton_rows) - len(beam))
        diagnostics["singleton_filters"][horizon] = dict(singleton_diag)
        diagnostics["beam_pruning"][horizon] = []

        for _score_value, preds, train, test in beam:
            key = tuple(sorted(pred.key for pred in preds))
            if key not in seen:
                seen.add(key)
                results.append(
                    _combo_payload(
                        market=market,
                        scope=scope,
                        cut_day=cut_day,
                        horizon=horizon,
                        combo_id=next(combo_counter),
                        predicates=preds,
                        train=train,
                        test=test,
                        min_train=min_train,
                        min_test=min_test,
                        min_days=min_days,
                    )
                )

        for term_count in range(2, max_terms + 1):
            expanded = []
            beam_diag = Counter({"term_count": term_count, "parent_beam": len(beam), "base_pool": len(base_pool)})
            for _score_value, preds, _train, _test in beam:
                existing_keys = {pred.key for pred in preds}
                for candidate in base_pool:
                    beam_diag["attempted"] += 1
                    if candidate.key in existing_keys or _feature_conflict(preds, candidate):
                        beam_diag["skipped_feature_conflict"] += 1
                        continue
                    combo = tuple(sorted((*preds, candidate), key=lambda pred: pred.key))
                    key = tuple(pred.key for pred in combo)
                    if key in seen:
                        beam_diag["skipped_duplicate"] += 1
                        continue
                    train, test, _mask = _combo_metrics(scoped, combo, train_values, test_values)
                    train_n = int(train.get(f"n_{horizon}") or 0)
                    test_n = int(test.get(f"n_{horizon}") or 0)
                    if train_n < min_train or test_n < min_test:
                        if train_n < min_train:
                            beam_diag["rejected_train_n"] += 1
                        if test_n < min_test:
                            beam_diag["rejected_test_n"] += 1
                        continue
                    train_days = int(train.get(f"active_days_{horizon}") or 0)
                    test_days = int(test.get(f"active_days_{horizon}") or 0)
                    if train_days < min_days or test_days < min_days:
                        if train_days < min_days:
                            beam_diag["rejected_train_days"] += 1
                        if test_days < min_days:
                            beam_diag["rejected_test_days"] += 1
                        continue
                    train_score = _score(train, horizon=horizon)
                    expanded.append((train_score, combo, train, test))
                    seen.add(key)
            expanded.sort(key=lambda row: row[0], reverse=True)
            beam_diag["expanded_survivors"] = len(expanded)
            beam_diag["pruned_by_beam"] = max(0, len(expanded) - beam_width)
            beam = expanded[:beam_width]
            beam_diag["next_beam"] = len(beam)
            for _score_value, preds, train, test in beam:
                results.append(
                    _combo_payload(
                        market=market,
                        scope=scope,
                        cut_day=cut_day,
                        horizon=horizon,
                        combo_id=next(combo_counter),
                        predicates=preds,
                        train=train,
                        test=test,
                        min_train=min_train,
                        min_test=min_test,
                        min_days=min_days,
                    )
                )
            beam_diag["emitted"] = len(beam)
            diagnostics["beam_pruning"][horizon].append(dict(beam_diag))
            if not beam:
                break
    gate_rejections: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in results:
        horizon = str(row.get("horizon") or "")
        if row.get("production_safe"):
            continue
        gate_rejections[horizon].update(
            _gate_rejection_reasons(row, horizon=horizon, min_train=min_train, min_test=min_test, min_days=min_days)
        )
    diagnostics["gate_rejections"] = {horizon: dict(counter.most_common()) for horizon, counter in gate_rejections.items()}
    diagnostics["result_counts"] = {
        "mined_combinations": len(results),
        "production_safe": sum(1 for row in results if row.get("production_safe")),
    }
    return results, diagnostics


def _scope_frames(df: pd.DataFrame, market: str) -> Dict[str, pd.DataFrame]:
    market_df = df.loc[df["market2"].eq(market)].copy()
    masks = _cohort_masks(market_df)
    scopes = {
        "market_all": market_df,
        "ranked_top20": market_df.loc[masks["ranked_top20"]].copy(),
        "top5_exception": market_df.loc[masks["top5_exception"]].copy(),
        "core_trend": market_df.loc[masks["core_trend"]].copy(),
        "explosive_leader": market_df.loc[masks["explosive_leader"]].copy(),
    }
    return {name: frame for name, frame in scopes.items() if len(frame) >= 40 and frame["trade_date"].nunique() >= 8}


def _baseline_summary(df: pd.DataFrame) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        out[market] = {}
        for scope, frame in _scope_frames(df, market).items():
            out[market][scope] = _metrics(frame, pd.Series(True, index=frame.index))
    return out


def _aggregate_diagnostics(scope_diagnostics: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "scope_count": len(scope_diagnostics),
        "skipped_scopes": Counter(),
        "candidate_features": {"numeric": 0, "categorical": 0, "total": 0},
        "predicates": Counter(),
        "predicate_support_screen": Counter(),
        "singleton_filters": defaultdict(Counter),
        "beam_pruning": defaultdict(Counter),
        "gate_rejections": defaultdict(Counter),
        "exact_exhaustive": {
            "enabled_scopes": 0,
            "disabled_scopes": Counter(),
            "checked_combinations": 0,
            "production_safe_combinations": 0,
        },
        "result_counts": Counter(),
    }
    for diag in scope_diagnostics:
        if diag.get("skip_reason"):
            summary["skipped_scopes"][str(diag.get("skip_reason"))] += 1
        features = diag.get("candidate_feature_counts") or {}
        for key in ["numeric", "categorical", "total"]:
            summary["candidate_features"][key] += int(features.get(key) or 0)
        predicates = diag.get("predicate_counts") or {}
        for key in ["raw", "unique", "duplicates", "numeric", "categorical", "after_support_screen"]:
            summary["predicates"][key] += int(predicates.get(key) or 0)
        summary["predicate_support_screen"].update(diag.get("predicate_support_screen") or {})
        for horizon, row in (diag.get("singleton_filters") or {}).items():
            summary["singleton_filters"][horizon].update(row or {})
        for horizon, rows in (diag.get("beam_pruning") or {}).items():
            for row in rows or []:
                summary["beam_pruning"][horizon].update(
                    {
                        k: int(v)
                        for k, v in (row or {}).items()
                        if k != "term_count" and isinstance(v, (int, np.integer))
                    }
                )
        for horizon, row in (diag.get("gate_rejections") or {}).items():
            summary["gate_rejections"][horizon].update(row or {})
        result_counts = diag.get("result_counts") or {}
        summary["result_counts"].update(result_counts)
        exhaustive = diag.get("exact_exhaustive") or {}
        if exhaustive.get("enabled"):
            summary["exact_exhaustive"]["enabled_scopes"] += 1
            for horizon_payload in (exhaustive.get("horizons") or {}).values():
                summary["exact_exhaustive"]["checked_combinations"] += int(horizon_payload.get("checked_combinations") or 0)
                summary["exact_exhaustive"]["production_safe_combinations"] += int(horizon_payload.get("production_safe_combinations") or 0)
        else:
            summary["exact_exhaustive"]["disabled_scopes"][str(exhaustive.get("reason") or "unknown")] += 1
    return {
        "scope_count": summary["scope_count"],
        "skipped_scopes": dict(summary["skipped_scopes"].most_common()),
        "candidate_features": summary["candidate_features"],
        "predicates": dict(summary["predicates"].most_common()),
        "predicate_support_screen": dict(summary["predicate_support_screen"].most_common()),
        "singleton_filters": {horizon: dict(counter.most_common()) for horizon, counter in summary["singleton_filters"].items()},
        "beam_pruning": {horizon: dict(counter.most_common()) for horizon, counter in summary["beam_pruning"].items()},
        "gate_rejections": {horizon: dict(counter.most_common()) for horizon, counter in summary["gate_rejections"].items()},
        "exact_exhaustive": {
            "enabled_scopes": summary["exact_exhaustive"]["enabled_scopes"],
            "disabled_scopes": dict(summary["exact_exhaustive"]["disabled_scopes"].most_common()),
            "checked_combinations": summary["exact_exhaustive"]["checked_combinations"],
            "production_safe_combinations": summary["exact_exhaustive"]["production_safe_combinations"],
        },
        "result_counts": dict(summary["result_counts"].most_common()),
    }


def _sort_key(row: Dict[str, Any]) -> Tuple[int, float, float, float, float, int]:
    test = row.get("test") or {}
    safe = 1 if row.get("production_safe") else 0
    horizon = row.get("horizon") or "5d"
    return (
        safe,
        _metric_value(test, f"win_{horizon}_pct"),
        _metric_value(test, f"avg_{horizon}_pct", -999.0),
        -_metric_value(test, f"bad_path_{horizon}_pct", 100.0),
        -_metric_value(test, f"stop5_{horizon}_pct", 100.0),
        int(test.get(f"n_{horizon}") or 0),
    )


def _apply_quality_scope(df: pd.DataFrame, quality_scope: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    scope = str(quality_scope or "all").strip().lower()
    before = int(len(df))
    if scope in {"all", ""}:
        filtered = df.copy()
    elif scope in {"exact_path", "ordered_path_exact"}:
        if "ordered_path_exact" not in df.columns:
            filtered = df.iloc[0:0].copy()
        else:
            filtered = df.loc[df["ordered_path_exact"].fillna(False).astype(bool)].copy()
    else:
        raise ValueError(f"unsupported quality_scope: {quality_scope}")
    return filtered, {
        "quality_scope": scope or "all",
        "input_rows_before_quality_scope": before,
        "input_rows_after_quality_scope": int(len(filtered)),
    }


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Significant Feature Combination Mining",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- quality_scope: `{((report.get('quality_scope') or {}).get('quality_scope'))}`",
        f"- mined_combinations: `{report.get('mined_combinations')}`",
        f"- production_safe_count: `{report.get('production_safe_count')}`",
        "",
        "## Top Validated Combinations",
        "",
        "| Rank | Market | Scope | Horizon | Terms | Valid N | Days | Win | Avg | Min | Max | Bad | Stop | Conditions |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(report.get("top_combinations", [])[:80], start=1):
        test = row.get("test") or {}
        horizon = row.get("horizon") or "5d"
        lines.append(
            "| "
            + " | ".join(
                str(v)
                for v in [
                    idx,
                    row.get("market"),
                    row.get("scope"),
                    horizon,
                    row.get("term_count"),
                    test.get(f"n_{horizon}"),
                    test.get(f"active_days_{horizon}"),
                    test.get(f"win_{horizon}_pct"),
                    test.get(f"avg_{horizon}_pct"),
                    test.get(f"min_{horizon}_pct"),
                    test.get(f"max_{horizon}_pct"),
                    test.get(f"bad_path_{horizon}_pct"),
                    test.get(f"stop5_{horizon}_pct"),
                    "<br>".join(row.get("conditions") or []),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Production Safe Candidates", ""])
    safe_rows = report.get("production_safe_combinations") or []
    if not safe_rows:
        lines.append("- None found under current holdout gate.")
    for row in safe_rows[:40]:
        test = row.get("test") or {}
        horizon = row.get("horizon") or "5d"
        lines.append(
            f"- `{row.get('market')}` `{row.get('scope')}` `{horizon}` "
            f"win={test.get(f'win_{horizon}_pct')} avg={test.get(f'avg_{horizon}_pct')} "
            f"bad={test.get(f'bad_path_{horizon}_pct')} stop={test.get(f'stop5_{horizon}_pct')} :: "
            + " / ".join(row.get("conditions") or [])
        )
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    diag_summary = diagnostics.get("summary") if isinstance(diagnostics.get("summary"), dict) else {}
    lines.extend(["", "## Search Diagnostics", ""])
    if diag_summary:
        lines.extend(
            [
                f"- scopes evaluated: `{diag_summary.get('scope_count')}`",
                f"- candidate features: `{diag_summary.get('candidate_features')}`",
                f"- predicates: `{diag_summary.get('predicates')}`",
                f"- predicate support screen: `{diag_summary.get('predicate_support_screen')}`",
                f"- result counts: `{diag_summary.get('result_counts')}`",
                f"- exact exhaustive: `{diag_summary.get('exact_exhaustive')}`",
            ]
        )
        gate_rejections = diag_summary.get("gate_rejections") if isinstance(diag_summary.get("gate_rejections"), dict) else {}
        if gate_rejections:
            lines.extend(["", "### Gate Rejections"])
            for horizon, reasons in gate_rejections.items():
                lines.append(f"- `{horizon}`: `{reasons}`")
        beam_pruning = diag_summary.get("beam_pruning") if isinstance(diag_summary.get("beam_pruning"), dict) else {}
        if beam_pruning:
            lines.extend(["", "### Beam Pruning"])
            for horizon, row in beam_pruning.items():
                lines.append(f"- `{horizon}`: `{row}`")
    scope_rows = diagnostics.get("scopes") if isinstance(diagnostics.get("scopes"), list) else []
    if scope_rows:
        lines.extend(["", "### Scope Diagnostics"])
        for row in scope_rows[:20]:
            lines.append(
                f"- `{row.get('market')}` `{row.get('scope')}` rows={row.get('rows')} "
                f"days={row.get('trade_days')} predicates={((row.get('predicate_counts') or {}).get('after_support_screen'))} "
                f"results={((row.get('result_counts') or {}).get('mined_combinations', 0))} "
                f"safe={((row.get('result_counts') or {}).get('production_safe', 0))} "
                f"skip={row.get('skip_reason') or '-'}"
            )
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def build_report(
    df: pd.DataFrame,
    *,
    markets: Sequence[str],
    scopes: Sequence[str],
    horizons: Sequence[str],
    train_ratio: float,
    min_train: int,
    min_test: int,
    min_days: int,
    min_support: int,
    beam_width: int,
    max_terms: int,
    include_primary_theme: bool,
    quality_scope: str = "all",
    exact_exhaustive_max_predicates: int = 0,
    exact_exhaustive_max_combos: int = 50000,
) -> Dict[str, Any]:
    df, quality_payload = _apply_quality_scope(df, quality_scope)
    horizons = [h.strip().lower() for h in horizons if h.strip()]
    all_results: List[Dict[str, Any]] = []
    scope_diagnostics: List[Dict[str, Any]] = []
    market_list = [market.strip().upper() for market in markets if market.strip()]
    scope_allow = {scope.strip() for scope in scopes if scope.strip()}
    for market in market_list:
        for scope, frame in _scope_frames(df, market).items():
            if scope_allow and scope not in scope_allow:
                continue
            scope_results, diagnostics = _mine_scope(
                frame,
                market=market,
                scope=scope,
                train_ratio=train_ratio,
                horizons=horizons,
                min_train=min_train,
                min_test=min_test,
                min_days=min_days,
                min_support=min_support,
                beam_width=beam_width,
                max_terms=max_terms,
                include_primary_theme=include_primary_theme,
                exact_exhaustive_max_predicates=exact_exhaustive_max_predicates,
                exact_exhaustive_max_combos=exact_exhaustive_max_combos,
            )
            all_results.extend(scope_results)
            scope_diagnostics.append(diagnostics)
    all_results.sort(key=_sort_key, reverse=True)
    safe = [row for row in all_results if row.get("production_safe")]
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": int(len(df)),
        "quality_scope": quality_payload,
        "markets": df["market2"].value_counts().to_dict() if "market2" in df.columns else {},
        "search_config": {
            "quality_scope": quality_payload["quality_scope"],
            "markets": market_list,
            "scopes": sorted(scope_allow) if scope_allow else "all",
            "train_ratio": train_ratio,
            "min_train": min_train,
            "min_test": min_test,
            "min_days": min_days,
            "min_support": min_support,
            "beam_width": beam_width,
            "max_terms": max_terms,
            "include_primary_theme": include_primary_theme,
            "horizons": horizons,
            "exact_exhaustive_max_predicates": exact_exhaustive_max_predicates,
            "exact_exhaustive_max_combos": exact_exhaustive_max_combos,
        },
        "baseline_summary": _baseline_summary(df),
        "diagnostics": {
            "summary": _aggregate_diagnostics(scope_diagnostics),
            "scopes": scope_diagnostics,
        },
        "mined_combinations": int(len(all_results)),
        "production_safe_count": int(len(safe)),
        "production_safe_combinations": safe[:120],
        "top_combinations": all_results[:240],
        "notes": [
            "Internal research only; production scanner/model artifacts are unchanged.",
            "Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.",
            "Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.",
            "Duplicate-combination tracking is horizon-local so 1D candidates do not suppress 3D/5D validation.",
            "Outcome and future-path columns are excluded from predicates to avoid leakage.",
            "Primary theme identity is excluded by default because fixed-theme rules overfit rotating market themes; source/routing/risk metadata can still participate.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine validated KR swing feature-condition combinations.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stem", default="significant_feature_combinations")
    parser.add_argument("--markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--scopes", default="")
    parser.add_argument("--horizons", default="1d,3d,5d")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--min-train", type=int, default=18)
    parser.add_argument("--min-test", type=int, default=8)
    parser.add_argument("--min-days", type=int, default=5)
    parser.add_argument("--min-support", type=int, default=10)
    parser.add_argument("--beam-width", type=int, default=80)
    parser.add_argument("--max-terms", type=int, default=5)
    parser.add_argument("--include-primary-theme", action="store_true")
    parser.add_argument("--quality-scope", choices=["all", "exact_path", "ordered_path_exact"], default="all")
    parser.add_argument("--exact-exhaustive-max-predicates", type=int, default=0)
    parser.add_argument("--exact-exhaustive-max-combos", type=int, default=50000)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = _load_dataset(Path(args.input))
    report = build_report(
        df,
        markets=[part.strip() for part in str(args.markets).split(",")],
        scopes=[part.strip() for part in str(args.scopes).split(",") if part.strip()],
        horizons=[part.strip() for part in str(args.horizons).split(",") if part.strip()],
        train_ratio=float(args.train_ratio),
        min_train=int(args.min_train),
        min_test=int(args.min_test),
        min_days=int(args.min_days),
        min_support=int(args.min_support),
        beam_width=int(args.beam_width),
        max_terms=int(args.max_terms),
        include_primary_theme=bool(args.include_primary_theme),
        quality_scope=str(args.quality_scope),
        exact_exhaustive_max_predicates=int(args.exact_exhaustive_max_predicates),
        exact_exhaustive_max_combos=int(args.exact_exhaustive_max_combos),
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
                "mined_combinations": report.get("mined_combinations"),
                "production_safe_count": report.get("production_safe_count"),
                "best": (report.get("top_combinations") or [None])[0],
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
