#!/usr/bin/env python3
"""Search drawdown filters for KIS touch5/dd10 sidecar candidates.

This is a research/audit tool, not a deployment switch. It uses real
walk-forward predictions from the KIS sidecar prepared cache, then sweeps
simple pre-selection filters that can be evaluated at scan time. The output
keeps production-gate pass candidates separate from deployment readiness so
operator reports can inspect the evidence without silently promoting an
overfit threshold sweep.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate
from multi_agent.tools.sweep_kis_sidecar_thresholds import _fit_predict_folds, _score_predictions
from multi_agent.tools.train_scan_universe_admission_challenger import (
    LABEL_SPECS,
    feature_sets,
    kis_presence_mask,
    label_series,
    metrics,
    tail_safe_series,
    top_indices_by_run,
    usable_features,
)


REPORT_VERSION = "kis_touch5_drawdown_filter_research_v1"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_touch5_dd10_drawdown_filter_research_kospi_20260101_20260610.json"
)
DEFAULT_PREPARED_CACHE = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_FEATURE_SET = "kis_sidecar_failure_risk_augmented"
DEFAULT_LABEL = "touch5_dd10_5d"
DEFAULT_MODEL = "lightgbm"
DEFAULT_MARKET = "KOSPI"
DEFAULT_SCORE_MODE = "prob"
DEFAULT_PROB_THRESHOLD = None
DEFAULT_TAIL_THRESHOLD = 0.85
DEFAULT_TOPN = 1

MANUAL_FILTER_FEATURES = (
    "close_failure_prior_kis_sector_failure_rate_pct",
    "close_failure_prior_theme_avg_close_5d_pct",
    "close_failure_prior_kis_theme_avg_close_5d_pct",
    "close_failure_prior_kis_sector_touch5_n",
    "close_failure_prior_ticker_failure_rate_pct",
    "close_failure_prior_ticker_risk_score",
    "close_failure_prior_theme_stop5_rate_pct",
    "close_failure_prior_kis_theme_stop5_rate_pct",
    "close_failure_prior_theme_clean_defense_rate_pct",
    "close_failure_prior_kis_theme_clean_defense_rate_pct",
    "kis_prev_volume_ratio",
    "kis_daily_volume_ratio_20d",
    "volume_ratio",
    "tech_score",
    "alpha_score",
    "kis_daily_return_20d_pct",
    "kis_daily_return_5d_pct",
    "kis_daily_close_location_pct",
    "kis_theme_news_evidence_score",
    "feature_coverage_score",
)
AUTO_FEATURE_NAME_PARTS = (
    "failure",
    "risk",
    "stop5",
    "defense",
    "volume_ratio",
    "return_20d",
    "return_5d",
    "close_location",
    "theme",
    "score",
    "coverage",
)
QUANTILES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, 6)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _metric_subset(row: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "n",
        "active_runs",
        "active_days",
        "hit5_dd10_5d_pct",
        "target_before_stop_5d_pct",
        "stop_before_target_5d_pct",
        "hit10_5d_pct",
        "avg_5d_pct",
        "median_5d_pct",
        "min_5d_pct",
        "avg_max_high_5d_pct",
        "avg_min_low_5d_pct",
        "min_min_low_5d_pct",
        "buy_premium_pct",
    )
    return {key: row.get(key) for key in keys if key in row}


def _filter_rule_name(feature: str, op: str, threshold: float) -> str:
    value = f"{threshold:g}".replace("-", "neg").replace(".", "p")
    return f"{feature}_{op}_{value}"


def _filter_signature(filter_payload: Mapping[str, Any]) -> str:
    feature = str(filter_payload.get("feature") or "")
    op = str(filter_payload.get("op") or "")
    threshold = _round(filter_payload.get("threshold"))
    return f"{feature}|{op}|{threshold}"


def _compound_filter_name(conditions: Sequence[Mapping[str, Any]]) -> str:
    signature = "&&".join(_filter_signature(condition) for condition in conditions)
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:10]
    return f"compound{len(conditions)}_{digest}"


def _filter_payload_name(filter_payload: Mapping[str, Any]) -> str:
    if str(filter_payload.get("type") or "") == "compound_and":
        conditions = filter_payload.get("conditions")
        if isinstance(conditions, Sequence) and not isinstance(conditions, (str, bytes)):
            valid_conditions = [condition for condition in conditions if isinstance(condition, Mapping)]
            if valid_conditions:
                return _compound_filter_name(valid_conditions)
    return _filter_rule_name(
        str(filter_payload.get("feature") or "unknown"),
        str(filter_payload.get("op") or "le"),
        float(filter_payload.get("threshold") or 0.0),
    )


def _selection_rule(
    *,
    topn: int,
    score_mode: str,
    tail_threshold: float,
    prob_threshold: float | None = None,
    filter_name: str | None = None,
) -> str:
    base = f"top{int(topn)}_{score_mode}".replace(".", "p")
    if prob_threshold is not None:
        base = f"{base}_p{prob_threshold:g}".replace(".", "p")
    base = f"{base}_tail{tail_threshold:g}".replace(".", "p")
    return f"{base}_{filter_name}" if filter_name else base


def _candidate_identity(
    *,
    market: str,
    feature_set: str,
    model: str,
    selection_rule: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None = None,
    filter_payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "market": market,
        "label": DEFAULT_LABEL,
        "feature_set": feature_set,
        "model": model,
        "selection_rule": selection_rule,
        "score_mode": score_mode,
        "topn": int(topn),
        "prob_threshold": _round(prob_threshold) if prob_threshold is not None else None,
        "tail_risk_prob_threshold": float(tail_threshold),
        "drawdown_filter": dict(filter_payload or {}),
        "validation_mode": "research_sweep_only_walk_forward_predictions",
        "deployment_ready": False,
    }


def _gate_row(
    *,
    market: str,
    feature_set: str,
    model: str,
    selection_rule: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None = None,
    selected: pd.Index,
    scoped: pd.DataFrame,
    label: pd.Series,
    filter_payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any] | None:
    if selected.empty:
        return None
    row_metrics = metrics(scoped, selected, label)
    identity = _candidate_identity(
        market=market,
        feature_set=feature_set,
        model=model,
        selection_rule=selection_rule,
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        filter_payload=filter_payload,
    )
    gate = evaluate_kis_model_gate(identity=identity, metrics=row_metrics, market=market)
    return {
        "identity": identity,
        "metrics": row_metrics,
        "gate": gate,
        "kis_model_gate": gate,
        "quality_score": _quality_score(row_metrics, gate),
        "selected_count": int(len(selected)),
    }


def _quality_score(row_metrics: Mapping[str, Any], gate: Mapping[str, Any]) -> float:
    hit = float(row_metrics.get("hit5_dd10_5d_pct") or 0.0)
    avg5 = float(row_metrics.get("avg_5d_pct") or -999.0)
    min_low = float(row_metrics.get("min_min_low_5d_pct") or -999.0)
    active_days = int(row_metrics.get("active_days") or 0)
    n = int(row_metrics.get("n") or 0)
    production_bonus = 1000.0 if gate.get("production_ready") else 0.0
    shadow_bonus = 120.0 if gate.get("shadow_display_allowed") else 0.0
    low_penalty = max(0.0, -10.0 - min_low) * 40.0
    return round(production_bonus + shadow_bonus + hit * 8.0 + avg5 * 1.6 + min_low * 2.0 + active_days + n * 0.05 - low_penalty, 6)


def _sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    row_metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
    return (
        bool(gate.get("production_ready")),
        bool(gate.get("shadow_display_allowed")),
        float(row.get("quality_score") or -999999.0),
        float(row_metrics.get("hit5_dd10_5d_pct") or 0.0),
        float(row_metrics.get("avg_5d_pct") or -999.0),
        float(row_metrics.get("min_min_low_5d_pct") or -999.0),
        int(row_metrics.get("active_days") or 0),
        int(row_metrics.get("n") or 0),
    )


def _candidate_filter_features(numeric: Sequence[str]) -> List[str]:
    out: List[str] = []
    for feature in MANUAL_FILTER_FEATURES:
        if feature in numeric and feature not in out:
            out.append(feature)
    for feature in numeric:
        if feature in out:
            continue
        if any(part in feature for part in AUTO_FEATURE_NAME_PARTS):
            out.append(feature)
    return out


def _prediction_pool(predictions: pd.DataFrame, *, prob_threshold: float | None, tail_threshold: float) -> pd.Index:
    pool = predictions.index[predictions["tail_prob"].ge(float(tail_threshold))]
    if prob_threshold is not None:
        pool = pool.intersection(predictions.index[predictions["prob"].ge(float(prob_threshold))])
    return pool


def _thresholds(values: pd.Series) -> List[float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 100:
        return []
    out = []
    for quantile in QUANTILES:
        value = float(clean.quantile(quantile))
        if not math.isnan(value) and not math.isinf(value):
            out.append(round(value, 6))
    return sorted(set(out))


def _single_feature_results(
    *,
    scoped: pd.DataFrame,
    base_pool: pd.Index,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    numeric: Sequence[str],
    min_pool_rows: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for feature in _candidate_filter_features(numeric):
        if feature not in scoped.columns:
            continue
        values = pd.to_numeric(scoped.loc[base_pool, feature], errors="coerce")
        for threshold in _thresholds(values):
            for op in ("le", "ge"):
                mask = values.le(threshold) if op == "le" else values.ge(threshold)
                pool = base_pool[mask.fillna(False)]
                if len(pool) < int(min_pool_rows):
                    continue
                filter_name = _filter_rule_name(feature, op, threshold)
                selected = top_indices_by_run(scoped.loc[pool], score.loc[pool], int(topn))
                row = _gate_row(
                    market=market,
                    feature_set=feature_set,
                    model=model,
                    selection_rule=_selection_rule(
                        topn=topn,
                        score_mode=score_mode,
                        tail_threshold=tail_threshold,
                        prob_threshold=prob_threshold,
                        filter_name=filter_name,
                    ),
                    score_mode=score_mode,
                    topn=topn,
                    tail_threshold=tail_threshold,
                    prob_threshold=prob_threshold,
                    selected=selected,
                    scoped=scoped,
                    label=label,
                    filter_payload={
                        "type": "single_feature_threshold",
                        "feature": feature,
                        "op": op,
                        "threshold": _round(threshold),
                        "pool_rows": int(len(pool)),
                    },
                )
                if row:
                    rows.append(row)
    return rows


def _apply_filter(scoped: pd.DataFrame, base_pool: pd.Index, filter_payload: Mapping[str, Any] | None) -> pd.Index:
    if not filter_payload:
        return base_pool
    if str(filter_payload.get("type") or "") == "compound_and":
        pool = base_pool
        conditions = filter_payload.get("conditions")
        if not isinstance(conditions, Sequence) or isinstance(conditions, (str, bytes)):
            return pd.Index([])
        for condition in conditions:
            if not isinstance(condition, Mapping):
                return pd.Index([])
            pool = _apply_filter(scoped, pool, condition)
            if pool.empty:
                break
        return pool
    feature = str(filter_payload.get("feature") or "")
    op = str(filter_payload.get("op") or "")
    threshold = filter_payload.get("threshold")
    if feature not in scoped.columns or op not in {"le", "ge"} or threshold is None:
        return pd.Index([])
    values = pd.to_numeric(scoped.loc[base_pool, feature], errors="coerce")
    number = float(threshold)
    mask = values.le(number) if op == "le" else values.ge(number)
    return base_pool[mask.fillna(False)]


def _candidate_filter_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    payload = identity.get("drawdown_filter") if isinstance(identity.get("drawdown_filter"), Mapping) else {}
    if str(payload.get("type") or "") != "single_feature_threshold":
        return {}
    return {
        "type": "single_feature_threshold",
        "feature": payload.get("feature"),
        "op": payload.get("op"),
        "threshold": _round(payload.get("threshold")),
    }


def _unique_single_filter_payloads(
    single_candidates: Sequence[Mapping[str, Any]],
    *,
    max_filters: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(single_candidates, key=_sort_key, reverse=True):
        payload = _candidate_filter_payload(row)
        if not payload:
            continue
        signature = _filter_signature(payload)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(payload)
        if int(max_filters) > 0 and len(out) >= int(max_filters):
            break
    return out


def _compound_feature_results(
    *,
    scoped: pd.DataFrame,
    base_pool: pd.Index,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    single_candidates: Sequence[Mapping[str, Any]],
    min_pool_rows: int,
    max_single_filters: int,
    max_compound_candidates: int,
) -> List[Dict[str, Any]]:
    filters = _unique_single_filter_payloads(single_candidates, max_filters=max_single_filters)
    rows: List[Dict[str, Any]] = []
    evaluated = 0
    for left, right in combinations(filters, 2):
        conditions = [left, right]
        pool = _apply_filter(
            scoped,
            base_pool,
            {
                "type": "compound_and",
                "conditions": conditions,
            },
        )
        if len(pool) < int(min_pool_rows):
            continue
        evaluated += 1
        if int(max_compound_candidates) > 0 and evaluated > int(max_compound_candidates):
            break
        filter_name = _compound_filter_name(conditions)
        selected = top_indices_by_run(scoped.loc[pool], score.loc[pool], int(topn))
        row = _gate_row(
            market=market,
            feature_set=feature_set,
            model=model,
            selection_rule=_selection_rule(
                topn=topn,
                score_mode=score_mode,
                tail_threshold=tail_threshold,
                prob_threshold=prob_threshold,
                filter_name=filter_name,
            ),
            score_mode=score_mode,
            topn=topn,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            selected=selected,
            scoped=scoped,
            label=label,
            filter_payload={
                "type": "compound_and",
                "conditions": conditions,
                "pool_rows": int(len(pool)),
            },
        )
        if row:
            rows.append(row)
    return rows


def _filter_results(
    *,
    scoped: pd.DataFrame,
    base_pool: pd.Index,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    numeric: Sequence[str],
    min_pool_rows: int,
    compound_filter_depth: int,
    compound_single_limit: int,
    compound_candidate_limit: int,
) -> List[Dict[str, Any]]:
    single_results = _single_feature_results(
        scoped=scoped,
        base_pool=base_pool,
        score=score,
        label=label,
        market=market,
        feature_set=feature_set,
        model=model,
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        numeric=numeric,
        min_pool_rows=min_pool_rows,
    )
    if int(compound_filter_depth) < 2:
        return single_results
    compound_results = _compound_feature_results(
        scoped=scoped,
        base_pool=base_pool,
        score=score,
        label=label,
        market=market,
        feature_set=feature_set,
        model=f"{model}_compound",
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        single_candidates=single_results,
        min_pool_rows=min_pool_rows,
        max_single_filters=compound_single_limit,
        max_compound_candidates=compound_candidate_limit,
    )
    return single_results + compound_results


def _copy_with_validation(row: Dict[str, Any] | None, validation_mode: str) -> Dict[str, Any] | None:
    if not row:
        return row
    identity = row.get("identity")
    if isinstance(identity, dict):
        identity["validation_mode"] = validation_mode
        identity["deployment_ready"] = False
    return row


def _fold_slices(predictions: pd.DataFrame, selection_folds: int) -> Dict[str, Any]:
    folds = sorted({int(value) for value in pd.to_numeric(predictions.get("fold"), errors="coerce").dropna().tolist()})
    selection = folds[: max(0, min(int(selection_folds), len(folds)))]
    holdout = folds[len(selection) :]
    selection_idx = predictions.index[predictions["fold"].isin(selection)]
    holdout_idx = predictions.index[predictions["fold"].isin(holdout)]
    return {
        "folds": folds,
        "selection_folds": selection,
        "holdout_folds": holdout,
        "selection_index": selection_idx,
        "holdout_index": holdout_idx,
    }


def _evaluate_fixed_filter(
    *,
    scoped: pd.DataFrame,
    prediction_slice: pd.DataFrame,
    base_pool: pd.Index,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    filter_payload: Mapping[str, Any],
    validation_mode: str,
) -> Dict[str, Any] | None:
    filtered_pool = _apply_filter(scoped, base_pool, filter_payload)
    filtered_pool = filtered_pool.intersection(prediction_slice.index)
    selected = top_indices_by_run(scoped.loc[filtered_pool], score.loc[filtered_pool], int(topn))
    filter_name = _filter_payload_name(filter_payload)
    row = _gate_row(
        market=market,
        feature_set=feature_set,
        model=model,
        selection_rule=_selection_rule(
            topn=topn,
            score_mode=score_mode,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            filter_name=filter_name,
        ),
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        selected=selected,
        scoped=scoped,
        label=label,
        filter_payload={**dict(filter_payload), "pool_rows": int(len(filtered_pool))},
    )
    return _copy_with_validation(row, validation_mode)


def _holdout_validation(
    *,
    scoped: pd.DataFrame,
    predictions: pd.DataFrame,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    numeric: Sequence[str],
    selection_folds: int,
    min_pool_rows: int,
    holdout_candidate_limit: int,
    compound_filter_depth: int,
    compound_single_limit: int,
    compound_candidate_limit: int,
    top_results: int,
) -> Dict[str, Any]:
    split = _fold_slices(predictions, selection_folds)
    if not split["selection_folds"] or not split["holdout_folds"]:
        return {"status": "skipped_insufficient_folds", "deployment_ready": False}
    selection_predictions = predictions.loc[split["selection_index"]]
    holdout_predictions = predictions.loc[split["holdout_index"]]
    selection_base_pool = _prediction_pool(
        selection_predictions, prob_threshold=prob_threshold, tail_threshold=tail_threshold
    )
    holdout_base_pool = _prediction_pool(
        holdout_predictions, prob_threshold=prob_threshold, tail_threshold=tail_threshold
    )
    selection_candidates = _filter_results(
        scoped=scoped,
        base_pool=selection_base_pool,
        score=score,
        label=label,
        market=market,
        feature_set=feature_set,
        model=f"{model}_drawdown_filter_selection",
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        numeric=numeric,
        min_pool_rows=min_pool_rows,
        compound_filter_depth=compound_filter_depth,
        compound_single_limit=compound_single_limit,
        compound_candidate_limit=compound_candidate_limit,
    )
    selection_ranked = sorted(selection_candidates, key=_sort_key, reverse=True)
    if not selection_ranked:
        return {
            "status": "skipped_no_selection_candidate",
            "deployment_ready": False,
            "selection_folds": split["selection_folds"],
            "holdout_folds": split["holdout_folds"],
            "selection_base_pool_rows": int(len(selection_base_pool)),
            "holdout_base_pool_rows": int(len(holdout_base_pool)),
        }
    fixed_results: List[Dict[str, Any]] = []
    candidates_for_holdout = (
        selection_ranked[: int(holdout_candidate_limit)]
        if int(holdout_candidate_limit) > 0
        else selection_ranked
    )
    for candidate in candidates_for_holdout:
        identity = candidate.get("identity") if isinstance(candidate.get("identity"), Mapping) else {}
        filter_payload = identity.get("drawdown_filter") if isinstance(identity.get("drawdown_filter"), Mapping) else {}
        if not filter_payload:
            continue
        fixed = _evaluate_fixed_filter(
            scoped=scoped,
            prediction_slice=holdout_predictions,
            base_pool=holdout_base_pool,
            score=score,
            label=label,
            market=market,
            feature_set=feature_set,
            model=f"{model}_drawdown_filter_fixed_holdout",
            score_mode=score_mode,
            topn=topn,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            filter_payload=filter_payload,
            validation_mode="selection_fixed_rule_holdout_walk_forward_predictions",
        )
        if not fixed:
            continue
        fixed["selection_candidate"] = candidate
        fixed_results.append(fixed)
    fixed_ranked = sorted(fixed_results, key=_sort_key, reverse=True)
    survivors = [row for row in fixed_ranked if (row.get("gate") or {}).get("production_ready")]
    selection_best = selection_ranked[0]
    selection_best_identity = (
        selection_best.get("identity") if isinstance(selection_best.get("identity"), Mapping) else {}
    )
    selection_best_filter = (
        selection_best_identity.get("drawdown_filter")
        if isinstance(selection_best_identity.get("drawdown_filter"), Mapping)
        else {}
    )
    fixed_selection_best = (
        _evaluate_fixed_filter(
            scoped=scoped,
            prediction_slice=holdout_predictions,
            base_pool=holdout_base_pool,
            score=score,
            label=label,
            market=market,
            feature_set=feature_set,
            model=f"{model}_drawdown_filter_selection_best_holdout",
            score_mode=score_mode,
            topn=topn,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            filter_payload=selection_best_filter,
            validation_mode="selection_best_fixed_rule_holdout_walk_forward_predictions",
        )
        if selection_best_filter
        else None
    )
    status = (
        "selection_best_holdout_gate_pass"
        if fixed_selection_best and (fixed_selection_best.get("gate") or {}).get("production_ready")
        else "holdout_gate_pass_survivor_found"
        if survivors
        else "no_holdout_gate_pass"
    )
    return {
        "status": status,
        "deployment_ready": False,
        "validation_mode": "selection_fixed_rule_holdout_walk_forward_predictions",
        "selection_folds": split["selection_folds"],
        "holdout_folds": split["holdout_folds"],
        "selection_test_days": sorted(scoped.loc[split["selection_index"], "trade_date"].astype(str).unique().tolist()),
        "holdout_test_days": sorted(scoped.loc[split["holdout_index"], "trade_date"].astype(str).unique().tolist()),
        "selection_base_pool_rows": int(len(selection_base_pool)),
        "holdout_base_pool_rows": int(len(holdout_base_pool)),
        "selection_candidates_tested": int(len(selection_candidates)),
        "holdout_candidates_evaluated": int(len(candidates_for_holdout)),
        "selection_best_candidate": _copy_with_validation(
            selection_best,
            "selection_sweep_only_walk_forward_predictions",
        ),
        "selection_best_holdout_evaluation": fixed_selection_best,
        "holdout_gate_pass_count": int(len(survivors)),
        "best_holdout_gate_pass_candidate": survivors[0] if survivors else None,
        "top_holdout_evaluations": fixed_ranked[: int(top_results)],
        "decision": {
            "holdout_gate_pass_observed": bool(survivors),
            "selection_best_holdout_gate_pass": bool(
                fixed_selection_best and (fixed_selection_best.get("gate") or {}).get("production_ready")
            ),
            "deployment_ready": False,
            "reason": "fixed-rule holdout reduces post-hoc threshold risk but still requires live forward shadow before production replacement.",
        },
    }


def _rolling_prior_validation(
    *,
    scoped: pd.DataFrame,
    predictions: pd.DataFrame,
    score: pd.Series,
    label: pd.Series,
    market: str,
    feature_set: str,
    model: str,
    score_mode: str,
    topn: int,
    tail_threshold: float,
    prob_threshold: float | None,
    numeric: Sequence[str],
    min_prior_folds: int,
    min_pool_rows: int,
    compound_filter_depth: int,
    compound_single_limit: int,
    compound_candidate_limit: int,
    top_results: int,
) -> Dict[str, Any]:
    folds = sorted({int(value) for value in pd.to_numeric(predictions.get("fold"), errors="coerce").dropna().tolist()})
    if len(folds) <= int(min_prior_folds):
        return {"status": "skipped_insufficient_folds", "deployment_ready": False}
    selected_indices: List[pd.Index] = []
    steps: List[Dict[str, Any]] = []
    for fold in folds:
        prior_folds = [item for item in folds if item < fold]
        if len(prior_folds) < int(min_prior_folds):
            continue
        prior_predictions = predictions.loc[predictions["fold"].isin(prior_folds)]
        current_predictions = predictions.loc[predictions["fold"].eq(fold)]
        if prior_predictions.empty or current_predictions.empty:
            continue
        prior_base_pool = _prediction_pool(
            prior_predictions, prob_threshold=prob_threshold, tail_threshold=tail_threshold
        )
        current_base_pool = _prediction_pool(
            current_predictions, prob_threshold=prob_threshold, tail_threshold=tail_threshold
        )
        prior_candidates = _filter_results(
            scoped=scoped,
            base_pool=prior_base_pool,
            score=score,
            label=label,
            market=market,
            feature_set=feature_set,
            model=f"{model}_drawdown_filter_rolling_prior_selection",
            score_mode=score_mode,
            topn=topn,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            numeric=numeric,
            min_pool_rows=min_pool_rows,
            compound_filter_depth=compound_filter_depth,
            compound_single_limit=compound_single_limit,
            compound_candidate_limit=compound_candidate_limit,
        )
        prior_ranked = sorted(prior_candidates, key=_sort_key, reverse=True)
        if not prior_ranked:
            steps.append(
                {
                    "fold": int(fold),
                    "status": "skipped_no_prior_candidate",
                    "prior_folds": prior_folds,
                    "current_test_days": sorted(scoped.loc[current_predictions.index, "trade_date"].astype(str).unique().tolist()),
                    "prior_base_pool_rows": int(len(prior_base_pool)),
                    "current_base_pool_rows": int(len(current_base_pool)),
                }
            )
            continue
        chosen = prior_ranked[0]
        chosen_identity = chosen.get("identity") if isinstance(chosen.get("identity"), Mapping) else {}
        filter_payload = (
            chosen_identity.get("drawdown_filter")
            if isinstance(chosen_identity.get("drawdown_filter"), Mapping)
            else {}
        )
        fixed = (
            _evaluate_fixed_filter(
                scoped=scoped,
                prediction_slice=current_predictions,
                base_pool=current_base_pool,
                score=score,
                label=label,
                market=market,
                feature_set=feature_set,
                model=f"{model}_drawdown_filter_rolling_prior_step",
                score_mode=score_mode,
                topn=topn,
                tail_threshold=tail_threshold,
                prob_threshold=prob_threshold,
                filter_payload=filter_payload,
                validation_mode="rolling_prior_oos_next_fold_step",
            )
            if filter_payload
            else None
        )
        chosen_metrics = chosen.get("metrics") if isinstance(chosen.get("metrics"), Mapping) else {}
        chosen_gate = chosen.get("gate") if isinstance(chosen.get("gate"), Mapping) else {}
        fixed_metrics = fixed.get("metrics") if fixed and isinstance(fixed.get("metrics"), Mapping) else {}
        fixed_gate = fixed.get("gate") if fixed and isinstance(fixed.get("gate"), Mapping) else {}
        selected = pd.Index([])
        if fixed:
            fixed_identity = fixed.get("identity") if isinstance(fixed.get("identity"), Mapping) else {}
            fixed_filter = (
                fixed_identity.get("drawdown_filter")
                if isinstance(fixed_identity.get("drawdown_filter"), Mapping)
                else {}
            )
            filtered_pool = _apply_filter(scoped, current_base_pool, fixed_filter)
            selected = top_indices_by_run(scoped.loc[filtered_pool], score.loc[filtered_pool], int(topn))
            if len(selected) > 0:
                selected_indices.append(selected)
        steps.append(
            {
                "fold": int(fold),
                "status": "evaluated",
                "prior_folds": prior_folds,
                "current_test_days": sorted(scoped.loc[current_predictions.index, "trade_date"].astype(str).unique().tolist()),
                "prior_base_pool_rows": int(len(prior_base_pool)),
                "current_base_pool_rows": int(len(current_base_pool)),
                "prior_candidates_tested": int(len(prior_candidates)),
                "chosen_rule": chosen_identity.get("selection_rule"),
                "chosen_filter": chosen_identity.get("drawdown_filter") or {},
                "chosen_prior_gate": chosen_gate.get("status"),
                "chosen_prior_metrics": _metric_subset(chosen_metrics),
                "current_gate": fixed_gate.get("status"),
                "current_metrics": _metric_subset(fixed_metrics),
                "selected_count": int(len(selected)),
            }
        )
    combined = pd.Index([])
    if selected_indices:
        combined = selected_indices[0]
        for idx in selected_indices[1:]:
            combined = combined.append(idx)
        combined = pd.Index(sorted(set(combined)))
    aggregate = _gate_row(
        market=market,
        feature_set=feature_set,
        model=f"{model}_drawdown_filter_rolling_prior",
        selection_rule=_selection_rule(
            topn=topn,
            score_mode=score_mode,
            tail_threshold=tail_threshold,
            prob_threshold=prob_threshold,
            filter_name="rolling_prior_oos",
        ),
        score_mode=score_mode,
        topn=topn,
        tail_threshold=tail_threshold,
        prob_threshold=prob_threshold,
        selected=combined,
        scoped=scoped,
        label=label,
        filter_payload={
            "type": "rolling_prior_oos",
            "min_prior_folds": int(min_prior_folds),
            "steps": len(steps),
        },
    )
    aggregate = _copy_with_validation(
        aggregate,
        "rolling_prior_oos_next_fold_walk_forward_predictions",
    )
    gate = aggregate.get("gate") if aggregate and isinstance(aggregate.get("gate"), Mapping) else {}
    metrics_payload = aggregate.get("metrics") if aggregate and isinstance(aggregate.get("metrics"), Mapping) else {}
    status = (
        "rolling_prior_gate_pass"
        if gate.get("production_ready")
        else "rolling_prior_shadow_ready"
        if gate.get("shadow_display_allowed")
        else "rolling_prior_blocked"
    )
    return {
        "status": status,
        "validation_mode": "rolling_prior_oos_next_fold_walk_forward_predictions",
        "deployment_ready": False,
        "min_prior_folds": int(min_prior_folds),
        "folds": folds,
        "evaluated_steps": int(len([step for step in steps if step.get("status") == "evaluated"])),
        "skipped_steps": int(len([step for step in steps if step.get("status") != "evaluated"])),
        "selected_count": int(len(combined)),
        "aggregate_candidate": aggregate,
        "top_steps": steps[-int(top_results) :],
        "decision": {
            "production_gate_pass_observed": bool(gate.get("production_ready")),
            "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
            "deployment_ready": False,
            "metrics": _metric_subset(metrics_payload),
            "reason": "rolling prior uses only previous OOS folds for rule choice; production promotion still requires passing gate and live forward tracking.",
        },
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    cache_path = Path(args.prepared_cache)
    data = pd.read_pickle(cache_path)
    label_spec = next(spec for spec in LABEL_SPECS if spec.name == args.label)
    label, valid = label_series(data, label_spec)
    tail_label, tail_valid = tail_safe_series(data)
    valid &= tail_valid
    market = str(args.market).upper()
    scoped = data.loc[valid & data["market"].eq(market)].copy()
    scoped = scoped.loc[kis_presence_mask(scoped, args.feature_set)].copy()
    y = label.loc[scoped.index].astype(int)
    y_tail = tail_label.loc[scoped.index].astype(int)
    numeric, categorical = feature_sets(data)[args.feature_set]
    numeric, categorical = usable_features(scoped, numeric, categorical)
    fold_payload = _fit_predict_folds(
        scoped,
        y=y,
        y_tail=y_tail,
        numeric=numeric,
        categorical=categorical,
        model_name=args.model,
        min_train_rows=int(args.min_train_rows),
        min_test_rows=int(args.min_test_rows),
        min_train_days=int(args.min_train_days),
        test_days=int(args.test_days),
        max_folds=int(args.max_folds),
        need_tail=True,
        progress=not bool(args.quiet),
    )
    predictions = fold_payload.pop("predictions")
    score = _score_predictions(predictions, args.score_mode)
    prob_threshold = args.prob_threshold
    base_pool = _prediction_pool(predictions, prob_threshold=prob_threshold, tail_threshold=float(args.tail_threshold))
    base_selected = top_indices_by_run(scoped.loc[base_pool], score.loc[base_pool], int(args.topn))
    base = _gate_row(
        market=market,
        feature_set=args.feature_set,
        model=args.model,
        selection_rule=_selection_rule(
            topn=args.topn,
            score_mode=args.score_mode,
            tail_threshold=args.tail_threshold,
            prob_threshold=prob_threshold,
        ),
        score_mode=args.score_mode,
        topn=args.topn,
        tail_threshold=args.tail_threshold,
        prob_threshold=prob_threshold,
        selected=base_selected,
        scoped=scoped,
        label=label,
    )
    candidates = _filter_results(
        scoped=scoped,
        base_pool=base_pool,
        score=score,
        label=label,
        market=market,
        feature_set=args.feature_set,
        model=f"{args.model}_drawdown_filter",
        score_mode=args.score_mode,
        topn=int(args.topn),
        tail_threshold=float(args.tail_threshold),
        prob_threshold=prob_threshold,
        numeric=numeric,
        min_pool_rows=int(args.min_pool_rows),
        compound_filter_depth=int(args.compound_filter_depth),
        compound_single_limit=int(args.compound_single_limit),
        compound_candidate_limit=int(args.compound_candidate_limit),
    )
    ranked = sorted(candidates, key=_sort_key, reverse=True)
    production = [row for row in ranked if (row.get("gate") or {}).get("production_ready")]
    holdout = _holdout_validation(
        scoped=scoped,
        predictions=predictions,
        score=score,
        label=label,
        market=market,
        feature_set=args.feature_set,
        model=args.model,
        score_mode=args.score_mode,
        topn=int(args.topn),
        tail_threshold=float(args.tail_threshold),
        prob_threshold=prob_threshold,
        numeric=numeric,
        selection_folds=int(args.selection_folds),
        min_pool_rows=int(args.min_pool_rows),
        holdout_candidate_limit=int(args.holdout_candidate_limit),
        compound_filter_depth=int(args.compound_filter_depth),
        compound_single_limit=int(args.compound_single_limit),
        compound_candidate_limit=int(args.compound_candidate_limit),
        top_results=int(args.top_results),
    )
    holdout_gate_pass = bool((holdout.get("decision") or {}).get("holdout_gate_pass_observed"))
    rolling_prior = (
        {"status": "skipped_by_operator", "deployment_ready": False}
        if bool(args.skip_rolling_prior)
        else _rolling_prior_validation(
            scoped=scoped,
            predictions=predictions,
            score=score,
            label=label,
            market=market,
            feature_set=args.feature_set,
            model=args.model,
            score_mode=args.score_mode,
            topn=int(args.topn),
            tail_threshold=float(args.tail_threshold),
            prob_threshold=prob_threshold,
            numeric=numeric,
            min_prior_folds=int(args.rolling_prior_min_folds),
            min_pool_rows=int(args.min_pool_rows),
            compound_filter_depth=int(args.compound_filter_depth),
            compound_single_limit=int(args.compound_single_limit),
            compound_candidate_limit=int(args.compound_candidate_limit),
            top_results=int(args.top_results),
        )
    )
    rolling_gate_pass = bool((rolling_prior.get("decision") or {}).get("production_gate_pass_observed"))
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "status": "production_gate_pass_research_candidate_found" if production else "no_production_gate_pass_candidate",
        "validation_mode": "research_sweep_only_walk_forward_predictions",
        "deployment_ready": False,
        "recommended_action": (
            "run live forward shadow validation for rolling prior drawdown filter"
            if rolling_gate_pass
            else
            "run live forward shadow validation for fixed drawdown filter"
            if holdout_gate_pass
            else
            "run controlled shadow and forward validation before promotion"
            if production
            else "continue drawdown-filter research"
        ),
        "objective": "Find scan-time drawdown filters that can satisfy touch5_dd10 KIS production gates on real walk-forward predictions.",
        "prepared_cache": str(cache_path),
        "market": market,
        "feature_set": args.feature_set,
        "model": args.model,
        "score_mode": args.score_mode,
        "topn": int(args.topn),
        "prob_threshold": _round(prob_threshold) if prob_threshold is not None else None,
        "tail_threshold": float(args.tail_threshold),
        "compound_filter_depth": int(args.compound_filter_depth),
        "compound_single_limit": int(args.compound_single_limit),
        "compound_candidate_limit": int(args.compound_candidate_limit),
        "scope": {
            "rows": int(len(scoped)),
            "unique_days": int(scoped["trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
            "unique_runs": int(scoped["run_id"].nunique()) if "run_id" in scoped.columns else 0,
            "base_pool_rows": int(len(base_pool)),
            "usable_numeric": int(len(numeric)),
            "usable_categorical": int(len(categorical)),
        },
        "fold_meta": fold_payload,
        "base_candidate": base,
        "filters_tested": int(len(candidates)),
        "production_ready_count": int(len(production)),
        "best_production_candidate": production[0] if production else None,
        "production_candidates": production[: int(args.top_results)],
        "top_results": ranked[: int(args.top_results)],
        "holdout_validation": holdout,
        "rolling_prior_validation": rolling_prior,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    base = report.get("base_candidate") if isinstance(report.get("base_candidate"), Mapping) else {}
    base_metrics = base.get("metrics") if isinstance(base.get("metrics"), Mapping) else {}
    base_gate = base.get("gate") if isinstance(base.get("gate"), Mapping) else {}
    best = report.get("best_production_candidate") if isinstance(report.get("best_production_candidate"), Mapping) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
    best_gate = best.get("gate") if isinstance(best.get("gate"), Mapping) else {}
    best_identity = best.get("identity") if isinstance(best.get("identity"), Mapping) else {}
    best_filter = best_identity.get("drawdown_filter") if isinstance(best_identity.get("drawdown_filter"), Mapping) else {}
    holdout = report.get("holdout_validation") if isinstance(report.get("holdout_validation"), Mapping) else {}
    holdout_best = (
        holdout.get("best_holdout_gate_pass_candidate")
        if isinstance(holdout.get("best_holdout_gate_pass_candidate"), Mapping)
        else {}
    )
    holdout_best_metrics = holdout_best.get("metrics") if isinstance(holdout_best.get("metrics"), Mapping) else {}
    holdout_best_gate = holdout_best.get("gate") if isinstance(holdout_best.get("gate"), Mapping) else {}
    holdout_best_econ = (
        holdout_best_gate.get("production_economics")
        if isinstance(holdout_best_gate.get("production_economics"), Mapping)
        else {}
    )
    selection_best_holdout = (
        holdout.get("selection_best_holdout_evaluation")
        if isinstance(holdout.get("selection_best_holdout_evaluation"), Mapping)
        else {}
    )
    selection_best_metrics = (
        selection_best_holdout.get("metrics") if isinstance(selection_best_holdout.get("metrics"), Mapping) else {}
    )
    selection_best_gate = (
        selection_best_holdout.get("gate") if isinstance(selection_best_holdout.get("gate"), Mapping) else {}
    )
    rolling = report.get("rolling_prior_validation") if isinstance(report.get("rolling_prior_validation"), Mapping) else {}
    rolling_candidate = (
        rolling.get("aggregate_candidate") if isinstance(rolling.get("aggregate_candidate"), Mapping) else {}
    )
    rolling_metrics = rolling_candidate.get("metrics") if isinstance(rolling_candidate.get("metrics"), Mapping) else {}
    rolling_gate = rolling_candidate.get("gate") if isinstance(rolling_candidate.get("gate"), Mapping) else {}
    rolling_econ = (
        rolling_gate.get("production_economics")
        if isinstance(rolling_gate.get("production_economics"), Mapping)
        else {}
    )
    lines = [
        "# KIS Touch5 Drawdown Filter Research",
        "",
        f"- version: `{report.get('version')}`",
        f"- status: `{report.get('status')}`",
        f"- validation_mode: `{report.get('validation_mode')}`",
        f"- deployment_ready: `{report.get('deployment_ready')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}`",
        f"- market: `{report.get('market')}`",
        f"- selection: score_mode=`{report.get('score_mode')}` topn=`{report.get('topn')}` prob_threshold=`{report.get('prob_threshold')}` tail_threshold=`{report.get('tail_threshold')}`",
        f"- compound_filter: depth=`{report.get('compound_filter_depth')}` single_limit=`{report.get('compound_single_limit')}` candidate_limit=`{report.get('compound_candidate_limit')}`",
        f"- base: status=`{base_gate.get('status')}` blockers=`{base_gate.get('production_blocking_reasons')}` n=`{base_metrics.get('n')}` days=`{base_metrics.get('active_days')}` hit5=`{base_metrics.get('hit5_dd10_5d_pct')}` avg5=`{base_metrics.get('avg_5d_pct')}` min_low=`{base_metrics.get('min_min_low_5d_pct')}`",
        f"- filters_tested: `{report.get('filters_tested')}`",
        f"- production_ready_count: `{report.get('production_ready_count')}`",
        f"- best_filter: `{best_filter}`",
        f"- best: status=`{best_gate.get('status')}` n=`{best_metrics.get('n')}` days=`{best_metrics.get('active_days')}` hit5=`{best_metrics.get('hit5_dd10_5d_pct')}` avg5=`{best_metrics.get('avg_5d_pct')}` min_low=`{best_metrics.get('min_min_low_5d_pct')}` expected_net=`{((best_gate.get('production_economics') or {}) if isinstance(best_gate.get('production_economics'), Mapping) else {}).get('expected_touch_policy_net_5d_pct')}`",
        f"- holdout: status=`{holdout.get('status')}` validation=`{holdout.get('validation_mode')}` selection_folds=`{holdout.get('selection_folds')}` holdout_folds=`{holdout.get('holdout_folds')}` selection_candidates=`{holdout.get('selection_candidates_tested')}` holdout_evaluated=`{holdout.get('holdout_candidates_evaluated')}` gate_pass_count=`{holdout.get('holdout_gate_pass_count')}` deployment_ready=`{holdout.get('deployment_ready')}`",
        f"- selection_best_holdout: status=`{selection_best_gate.get('status')}` n=`{selection_best_metrics.get('n')}` days=`{selection_best_metrics.get('active_days')}` hit5=`{selection_best_metrics.get('hit5_dd10_5d_pct')}` avg5=`{selection_best_metrics.get('avg_5d_pct')}` min_low=`{selection_best_metrics.get('min_min_low_5d_pct')}`",
        f"- best_holdout_gate_pass: status=`{holdout_best_gate.get('status')}` n=`{holdout_best_metrics.get('n')}` days=`{holdout_best_metrics.get('active_days')}` hit5=`{holdout_best_metrics.get('hit5_dd10_5d_pct')}` avg5=`{holdout_best_metrics.get('avg_5d_pct')}` min_low=`{holdout_best_metrics.get('min_min_low_5d_pct')}` expected_net=`{holdout_best_econ.get('expected_touch_policy_net_5d_pct')}`",
        f"- rolling_prior: status=`{rolling.get('status')}` validation=`{rolling.get('validation_mode')}` min_prior_folds=`{rolling.get('min_prior_folds')}` evaluated_steps=`{rolling.get('evaluated_steps')}` selected=`{rolling.get('selected_count')}` deployment_ready=`{rolling.get('deployment_ready')}`",
        f"- rolling_prior_aggregate: status=`{rolling_gate.get('status')}` n=`{rolling_metrics.get('n')}` days=`{rolling_metrics.get('active_days')}` runs=`{rolling_metrics.get('active_runs')}` hit5=`{rolling_metrics.get('hit5_dd10_5d_pct')}` avg5=`{rolling_metrics.get('avg_5d_pct')}` min_low=`{rolling_metrics.get('min_min_low_5d_pct')}` expected_net=`{rolling_econ.get('expected_touch_policy_net_5d_pct')}` blockers=`{rolling_gate.get('production_blocking_reasons')}`",
        "",
        "| rank | status | rule | n | days | runs | hit5 | avg5 | min_low | expected_net |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(report.get("top_results") or [], start=1):
        row_metrics = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
        row_gate = row.get("gate") if isinstance(row.get("gate"), Mapping) else {}
        identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
        econ = row_gate.get("production_economics") if isinstance(row_gate.get("production_economics"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(idx),
                    str(row_gate.get("status")),
                    str(identity.get("selection_rule")),
                    str(row_metrics.get("n")),
                    str(row_metrics.get("active_days")),
                    str(row_metrics.get("active_runs")),
                    str(row_metrics.get("hit5_dd10_5d_pct")),
                    str(row_metrics.get("avg_5d_pct")),
                    str(row_metrics.get("min_min_low_5d_pct")),
                    str(econ.get("expected_touch_policy_net_5d_pct")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report).rstrip() + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--feature-set", default=DEFAULT_FEATURE_SET)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--score-mode", default=DEFAULT_SCORE_MODE)
    parser.add_argument("--topn", type=int, default=DEFAULT_TOPN)
    parser.add_argument("--prob-threshold", type=float, default=DEFAULT_PROB_THRESHOLD)
    parser.add_argument("--tail-threshold", type=float, default=DEFAULT_TAIL_THRESHOLD)
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=1)
    parser.add_argument("--min-train-days", type=int, default=7)
    parser.add_argument("--test-days", type=int, default=1)
    parser.add_argument("--max-folds", type=int, default=20)
    parser.add_argument("--selection-folds", type=int, default=5)
    parser.add_argument("--rolling-prior-min-folds", type=int, default=5)
    parser.add_argument("--skip-rolling-prior", action="store_true")
    parser.add_argument("--min-pool-rows", type=int, default=30)
    parser.add_argument("--holdout-candidate-limit", type=int, default=0, help="0 evaluates all selection candidates.")
    parser.add_argument("--compound-filter-depth", type=int, choices=[1, 2], default=1)
    parser.add_argument("--compound-single-limit", type=int, default=60)
    parser.add_argument("--compound-candidate-limit", type=int, default=0, help="0 evaluates all viable compound candidates.")
    parser.add_argument("--top-results", type=int, default=30)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    write_report(report, Path(args.output))
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "production_ready_count": report.get("production_ready_count"),
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
