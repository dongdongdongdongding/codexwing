#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
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

REPORT_VERSION = "significant_feature_combo_mining_v1"

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


def _build_numeric_predicates(df: pd.DataFrame, col: str, *, min_support: int, max_support_ratio: float) -> List[Predicate]:
    values = pd.to_numeric(df[col], errors="coerce")
    if values.notna().sum() < min_support:
        return []
    thresholds = set()
    for q in [0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85]:
        val = values.quantile(q)
        if pd.notna(val):
            thresholds.add(round(float(val), 6))
    if col == "priority_rank":
        thresholds.update([1.0, 3.0, 5.0, 10.0, 20.0])
    if col == "volume_ratio":
        thresholds.update([0.8, 1.0, 1.2, 1.5, 2.0, 3.0])
    if col in {"foreigner", "institution", "retail", "foreign_flow", "institution_flow", "retail_flow", "foreigner_1d", "institution_1d", "foreigner_3d", "institution_3d", "foreigner_10d", "institution_10d", "whale_flow_1d", "whale_flow_3d", "whale_flow_10d"}:
        thresholds.add(0.0)
    predicates: List[Predicate] = []
    max_support = max(min_support, int(len(df) * max_support_ratio))
    for threshold in sorted(thresholds):
        for direction, op in [(">=", values.ge), ("<=", values.le)]:
            mask = op(threshold).fillna(False)
            mask_values = mask.to_numpy(dtype=bool)
            support = int(mask_values.sum())
            if min_support <= support <= max_support:
                label = f"{col} {direction} {threshold:g}"
                predicates.append(Predicate(_predicate_key(col, direction, threshold), col, label, direction, threshold, mask_values))
    return predicates


def _build_categorical_predicates(df: pd.DataFrame, col: str, *, min_support: int, max_support_ratio: float) -> List[Predicate]:
    series = df[col].fillna("UNKNOWN").astype(str).str.strip()
    counts = series.value_counts(dropna=False)
    max_support = max(min_support, int(len(df) * max_support_ratio))
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


def _build_predicates(df: pd.DataFrame, *, min_support: int, max_support_ratio: float, include_primary_theme: bool) -> List[Predicate]:
    predicates: List[Predicate] = []
    for col in _candidate_numeric_columns(df):
        predicates.extend(_build_numeric_predicates(df, col, min_support=min_support, max_support_ratio=max_support_ratio))
    for col in _candidate_categorical_columns(df, include_primary_theme=include_primary_theme):
        predicates.extend(_build_categorical_predicates(df, col, min_support=min_support, max_support_ratio=max_support_ratio))

    unique: Dict[str, Predicate] = {}
    for pred in predicates:
        unique.setdefault(pred.key, pred)
    return list(unique.values())


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
        "holdout_safe": _is_production_safe(test, horizon=horizon, min_n=10, min_days=5),
        "train_stable": _is_train_stable(train, horizon=horizon, min_n=18, min_days=5),
        "production_safe": _is_production_safe(test, horizon=horizon, min_n=10, min_days=5)
        and _is_train_stable(train, horizon=horizon, min_n=18, min_days=5),
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
) -> List[Dict[str, Any]]:
    scoped = df.copy()
    train_mask, test_mask, cut_day = _split_days(scoped, train_ratio)
    train_values = train_mask.to_numpy(dtype=bool)
    test_values = test_mask.to_numpy(dtype=bool)
    if train_values.sum() < min_train or test_values.sum() < min_test:
        return []

    predicate_support = max(3, min_support)
    predicates = _build_predicates(scoped.copy(), min_support=predicate_support, max_support_ratio=0.92, include_primary_theme=include_primary_theme)
    scoped_predicates = []
    for pred in predicates:
        mask = np.asarray(pred.mask, dtype=bool)
        if int((mask & train_values).sum()) >= min_train and int((mask & test_values).sum()) >= min_test:
            scoped_predicates.append(Predicate(pred.key, pred.feature, pred.label, pred.direction, pred.value, mask))

    results: List[Dict[str, Any]] = []
    combo_counter = count(1)
    seen = set()
    for horizon in horizons:
        singleton_rows = []
        for pred in scoped_predicates:
            train, test, _mask = _combo_metrics(scoped, [pred], train_values, test_values)
            if int(train.get(f"n_{horizon}") or 0) >= min_train and int(train.get(f"active_days_{horizon}") or 0) >= min_days:
                singleton_rows.append((_score(train, horizon=horizon), (pred,), train, test))
        singleton_rows.sort(key=lambda row: row[0], reverse=True)
        base_pool = [row[1][0] for row in singleton_rows[: max(beam_width * 2, beam_width)]]
        beam = singleton_rows[:beam_width]

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
                    )
                )

        for term_count in range(2, max_terms + 1):
            expanded = []
            for _score_value, preds, _train, _test in beam:
                existing_keys = {pred.key for pred in preds}
                for candidate in base_pool:
                    if candidate.key in existing_keys or _feature_conflict(preds, candidate):
                        continue
                    combo = tuple(sorted((*preds, candidate), key=lambda pred: pred.key))
                    key = tuple(pred.key for pred in combo)
                    if key in seen:
                        continue
                    train, test, _mask = _combo_metrics(scoped, combo, train_values, test_values)
                    if int(train.get(f"n_{horizon}") or 0) < min_train or int(test.get(f"n_{horizon}") or 0) < min_test:
                        continue
                    if int(train.get(f"active_days_{horizon}") or 0) < min_days or int(test.get(f"active_days_{horizon}") or 0) < min_days:
                        continue
                    train_score = _score(train, horizon=horizon)
                    expanded.append((train_score, combo, train, test))
                    seen.add(key)
            expanded.sort(key=lambda row: row[0], reverse=True)
            beam = expanded[:beam_width]
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
                    )
                )
            if not beam:
                break
    return results


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


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Significant Feature Combination Mining",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- input_rows: `{report.get('input_rows')}`",
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
) -> Dict[str, Any]:
    horizons = [h.strip().lower() for h in horizons if h.strip()]
    all_results: List[Dict[str, Any]] = []
    market_list = [market.strip().upper() for market in markets if market.strip()]
    scope_allow = {scope.strip() for scope in scopes if scope.strip()}
    for market in market_list:
        for scope, frame in _scope_frames(df, market).items():
            if scope_allow and scope not in scope_allow:
                continue
            all_results.extend(
                _mine_scope(
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
                )
            )
    all_results.sort(key=_sort_key, reverse=True)
    safe = [row for row in all_results if row.get("production_safe")]
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": int(len(df)),
        "markets": df["market2"].value_counts().to_dict() if "market2" in df.columns else {},
        "search_config": {
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
        },
        "baseline_summary": _baseline_summary(df),
        "mined_combinations": int(len(all_results)),
        "production_safe_count": int(len(safe)),
        "production_safe_combinations": safe[:120],
        "top_combinations": all_results[:240],
        "notes": [
            "Internal research only; production scanner/model artifacts are unchanged.",
            "Beam expansion is ranked by train metrics only; holdout metrics are used for validation/reporting.",
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
