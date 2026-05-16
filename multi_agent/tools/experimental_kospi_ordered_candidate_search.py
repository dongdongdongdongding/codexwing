#!/usr/bin/env python3
"""Search KR admission candidates using ordered OHLCV labels.

Internal-only research tool. It labels KR scan archive rows with actual
daily OHLCV target-before-stop outcomes, then searches pre-entry feature rules
that improve ordered win rate without changing production scanner behavior.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.experimental_admission_cycle import DEFAULT_INPUT, _decision_masks, _load_dataset
from multi_agent.tools.experimental_kospi_admission_robust_search import _parse_condition
from multi_agent.tools.experimental_kospi_ordered_revalidation import label_selected_rows


REPORT_VERSION = "kr_ordered_candidate_search_v2"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/experimental/kospi_ordered_candidate_search.json"
DEFAULT_CACHED_LABELS = PROJECT_ROOT / "runtime_state/reports/experimental/kospi_ordered_candidate_search.rows.csv"
DEFAULT_KOSDAQ_CACHED_LABELS = PROJECT_ROOT / "runtime_state/reports/experimental/kosdaq_ordered_candidate_search_latest.rows.csv"


@dataclass(frozen=True)
class OrderedProfile:
    name: str
    horizon_days: int
    target_pct: float
    stop_pct: float


PROFILES: Tuple[OrderedProfile, ...] = (
    OrderedProfile("5D_ordered_8v4", 5, 8.0, 4.0),
    OrderedProfile("5D_ordered_10v5", 5, 10.0, 5.0),
    OrderedProfile("5D_ordered_12v5", 5, 12.0, 5.0),
)

KOSDAQ_PROFILES: Tuple[OrderedProfile, ...] = (
    OrderedProfile("5D_ordered_5v5", 5, 5.0, 5.0),
    OrderedProfile("5D_ordered_8v5", 5, 8.0, 5.0),
    OrderedProfile("5D_ordered_10v5", 5, 10.0, 5.0),
    OrderedProfile("5D_ordered_12v5", 5, 12.0, 5.0),
)

NUMERIC_FEATURES: Tuple[str, ...] = (
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "decision_score",
    "whale_score",
    "volume_ratio",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "relative_rank_score",
    "relative_rank_pct",
    "loss_risk_score",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
    "day_return_pct",
    "conviction_score",
    "regime_breadth_pct",
    "regime_avg_chg",
    "regime_volatility_20d",
    "model_prob_mean",
    "phase25_prob",
)

STRUCTURAL_CATEGORICAL_FEATURES: Tuple[str, ...] = (
    "kr_universe_role",
    "selection_lane",
    "scanner_timeframe_profile",
    "theme_routing_path",
    "trend",
    "position",
    "tier",
    "market_gate",
    "volume_confirmed",
    "core_trend_flag",
    "explosive_leader_flag",
    "explosive_eligible",
)

THEME_CATEGORICAL_FEATURES: Tuple[str, ...] = ("primary_theme",)
COHORT_CONDITIONS: Tuple[str, ...] = ("cohort=Top1", "cohort=Top3", "cohort=Top5", "cohort=Exception Leader")
CURATED_RULES: Tuple[Dict[str, Any], ...] = (
    {
        "rule_id": "ordered_prob_band_top3_10v5",
        "profile": "5D_ordered_10v5",
        "conditions": ["cohort=Top3", "prob_clean=[28.1,31.8]", "decision_score>=100", "explosive_leader_flag=0"],
        "markets": ["KOSPI"],
        "note": "Current robust KOSPI ordered shadow baseline.",
    },
    {
        "rule_id": "ordered_prob_band_top3_ml_cap_10v5",
        "profile": "5D_ordered_10v5",
        "conditions": [
            "cohort=Top3",
            "prob_clean=[28.1,31.8]",
            "decision_score>=100",
            "explosive_leader_flag=0",
            "ml_prob<=38.6",
        ],
        "markets": ["KOSPI"],
        "note": "Best non-theme stop-reduction refinement; smaller test sample.",
    },
    {
        "rule_id": "ordered_prob_band_top3_core_route_10v5",
        "profile": "5D_ordered_10v5",
        "conditions": [
            "cohort=Top3",
            "prob_clean=[28.1,31.8]",
            "decision_score>=100",
            "explosive_leader_flag=0",
            "theme_routing_path=core_only",
        ],
        "markets": ["KOSPI"],
        "note": "Dynamic theme-routing refinement, not a static theme name.",
    },
    {
        "rule_id": "ordered_prob_band_top3_edge_cap_10v5",
        "profile": "5D_ordered_10v5",
        "conditions": [
            "cohort=Top3",
            "prob_clean=[28.1,31.8]",
            "decision_score>=100",
            "explosive_leader_flag=0",
            "expected_return_3d_pct<=0.458",
        ],
        "markets": ["KOSPI"],
        "note": "Recent-regime high win but weaker train sample.",
    },
    {
        "rule_id": "ordered_prob_band_top3_phase_low_10v5",
        "profile": "5D_ordered_10v5",
        "conditions": [
            "cohort=Top3",
            "prob_clean=[28.1,31.8]",
            "decision_score>=100",
            "explosive_leader_flag=0",
            "phase25_prob<=40.6",
        ],
        "markets": ["KOSPI"],
        "note": "Highest small-sample balance; diagnostic until more rows arrive.",
    },
    {
        "rule_id": "kosdaq_validated_touch_exception_5v5",
        "profile": "5D_ordered_5v5",
        "conditions": [
            "cohort=Top5",
            "trend=UP",
            "alpha_score>=90",
            "volume_ratio>=2",
        ],
        "markets": ["KOSDAQ"],
        "note": "KOSDAQ validated-touch exception rechecked with stop-first ordered OHLCV.",
    },
)


def profiles_for_market(market: str) -> Tuple[OrderedProfile, ...]:
    return KOSDAQ_PROFILES if str(market).upper() == "KOSDAQ" else PROFILES


def curated_rules_for_market(market: str) -> Tuple[Dict[str, Any], ...]:
    market = str(market).upper()
    return tuple(rule for rule in CURATED_RULES if market in {str(item).upper() for item in rule.get("markets", [])})


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 4) -> float | None:
    number = _safe_float(value)
    return round(number, digits) if number is not None else None


def _feature_name(condition: str) -> str:
    if "=[" in condition:
        return condition.split("=[", 1)[0]
    for op in ("<=", ">=", "="):
        if op in condition:
            return condition.split(op, 1)[0]
    return condition


def _has_static_theme(conditions: Sequence[str]) -> bool:
    return any(_feature_name(condition) in THEME_CATEGORICAL_FEATURES for condition in conditions)


def _condition_to_mask(df: pd.DataFrame, condition: str) -> pd.Series | None:
    text = str(condition)
    if text.startswith("cohort="):
        cohort = text.split("=", 1)[1]
        rank = pd.to_numeric(df.get("priority_rank", pd.Series(float("nan"), index=df.index)), errors="coerce")
        decision = df.get("decision", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
        bucket = df.get("decision_bucket", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
        exception = bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")
        if cohort == "Top1":
            return rank.eq(1).fillna(False) & ~exception
        if cohort == "Top3":
            return rank.between(1, 3, inclusive="both").fillna(False) & ~exception
        if cohort == "Top5":
            return rank.between(1, 5, inclusive="both").fillna(False) & ~exception
        if cohort == "Exception Leader":
            return exception
        return None
    if "=[" in text and text.endswith("]"):
        col, raw = text.split("=[", 1)
        if col not in df.columns:
            return None
        try:
            low_raw, high_raw = raw[:-1].split(",", 1)
            low = float(low_raw)
            high = float(high_raw)
        except Exception:
            return None
        numeric = pd.to_numeric(df[col], errors="coerce")
        return numeric.ge(low).fillna(False) & numeric.le(high).fillna(False)
    return _parse_condition(df, text)


def prepare_profile_rows(
    df: pd.DataFrame,
    profiles: Sequence[OrderedProfile],
    *,
    market: str = "KOSPI",
) -> pd.DataFrame:
    market = str(market).upper()
    market_rows = df[df.get("market2", pd.Series("", index=df.index)).eq(market)].copy()
    if market_rows.empty:
        return market_rows
    rows: List[pd.DataFrame] = []
    for profile in profiles:
        sub = market_rows.copy()
        sub["candidate_id"] = profile.name
        sub["candidate_description"] = f"full_{market.lower()}_ordered_search"
        sub["candidate_cohort"] = f"{market}_ALL"
        sub["target_pct"] = float(profile.target_pct)
        sub["stop_pct"] = float(profile.stop_pct)
        sub["horizon_days"] = int(profile.horizon_days)
        sub["source_proxy"] = "{}"
        rows.append(sub)
    out = pd.concat(rows, ignore_index=True)
    if "priority_rank" in out.columns:
        out["_priority_rank_sort"] = pd.to_numeric(out["priority_rank"], errors="coerce")
    else:
        out["_priority_rank_sort"] = float("inf")
    if "decision_score" in out.columns:
        out["_decision_score_sort"] = pd.to_numeric(out["decision_score"], errors="coerce")
    else:
        out["_decision_score_sort"] = float("-inf")
    out = out.sort_values(
        ["candidate_id", "trade_date", "ticker", "_priority_rank_sort", "_decision_score_sort"],
        ascending=[True, True, True, True, False],
        na_position="last",
    )
    out = out.drop_duplicates(["candidate_id", "trade_date", "ticker"], keep="first").copy()
    return out.drop(columns=["_priority_rank_sort", "_decision_score_sort"]).reset_index(drop=True)


def add_search_columns(labeled: pd.DataFrame) -> pd.DataFrame:
    out = labeled.copy()
    cohort_masks = _decision_masks(out)
    out["cohort"] = "Other"
    for name in ("Top5", "Top3", "Top1", "Exception Leader"):
        mask = cohort_masks.get(name)
        if mask is not None:
            out.loc[mask.fillna(False), "cohort"] = name
    out["ordered_label_ready"] = out["ordered_target_before_stop"].isin([True, False])
    no_touch = out.get("ordered_terminal_status", pd.Series("", index=out.index)).fillna("").astype(str).eq("no_touch")
    bars = pd.to_numeric(out.get("ordered_bars_observed", pd.Series(0, index=out.index)), errors="coerce")
    horizon = pd.to_numeric(out.get("horizon_days", pd.Series(5, index=out.index)), errors="coerce").fillna(5)
    out.loc[no_touch & bars.lt(horizon), "ordered_label_ready"] = False
    out["ordered_win"] = out["ordered_target_before_stop"].eq(True) & out["ordered_label_ready"]
    out["ordered_stop"] = out["ordered_stop_before_target"].eq(True) & out["ordered_label_ready"]
    return out


def build_condition_masks(
    df: pd.DataFrame,
    *,
    train_mask: pd.Series,
    include_static_themes: bool,
    max_conditions: int,
) -> List[Tuple[str, pd.Series]]:
    rows: List[Tuple[str, pd.Series]] = []

    def add(name: str, mask: pd.Series) -> None:
        clean = mask.fillna(False)
        if int((clean & train_mask).sum()) > 0:
            rows.append((name, clean))

    for condition in COHORT_CONDITIONS:
        parsed = _condition_to_mask(df, condition)
        if parsed is not None:
            add(condition, parsed)

    fixed_specs = (
        ("prob_clean", ">=", 28.1),
        ("prob_clean", "<=", 31.8),
        ("prob_clean", "<=", 35.225),
        ("decision_score", ">=", 92.0),
        ("decision_score", ">=", 100.0),
        ("ml_prob", "<=", 20.84),
        ("whale_score", ">=", 73.0),
        ("loss_risk_score", "<=", 55.0),
        ("loss_risk_score", "<=", 70.0),
    )
    for col, op, threshold in fixed_specs:
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        add(f"{col}{op}{threshold:g}", numeric.ge(threshold) if op == ">=" else numeric.le(threshold))

    fixed_ranges = (
        ("prob_clean", 28.1, 31.8),
        ("prob_clean", 28.1, 35.225),
        ("prob_clean", 25.0, 35.225),
        ("ml_prob", 10.0, 20.84),
        ("ml_prob", 18.0, 35.0),
        ("loss_risk_score", 0.0, 55.0),
        ("loss_risk_score", 0.0, 70.0),
    )
    for col, low, high in fixed_ranges:
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        add(f"{col}=[{low:g},{high:g}]", numeric.ge(low) & numeric.le(high))

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        values = numeric.loc[train_mask].dropna()
        if len(values) < 12:
            continue
        quantiles = values.quantile([0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85]).tolist()
        thresholds = sorted(set(round(float(v), 6) for v in quantiles if not math.isnan(float(v))))
        for threshold in thresholds:
            add(f"{col}>={threshold:g}", numeric.ge(threshold))
            add(f"{col}<={threshold:g}", numeric.le(threshold))
        if col in {"prob_clean", "ml_prob", "loss_risk_score", "relative_rank_pct"} and len(thresholds) >= 2:
            for low_idx, low in enumerate(thresholds[:-1]):
                for high in thresholds[low_idx + 1 :]:
                    add(f"{col}=[{low:g},{high:g}]", numeric.ge(low) & numeric.le(high))

    categorical = list(STRUCTURAL_CATEGORICAL_FEATURES)
    if include_static_themes:
        categorical.extend(THEME_CATEGORICAL_FEATURES)
    for col in categorical:
        if col not in df.columns:
            continue
        text = df[col].fillna("").astype(str)
        for value, count in text.loc[train_mask].value_counts().head(12).items():
            value = str(value)
            if count < 5 or not value or value.lower() in {"nan", "none", "null", "unknown"}:
                continue
            add(f"{col}={value}", text.eq(value))
    rows = rows[:max_conditions]
    return rows


def _metrics(df: pd.DataFrame, mask: pd.Series) -> Dict[str, Any]:
    sub = df.loc[mask & df["ordered_label_ready"]].copy()
    n = int(len(sub))
    if n == 0:
        return {
            "n": 0,
            "win_pct": None,
            "stop_pct": None,
            "no_touch_pct": None,
            "avg_mfe_pct": None,
            "avg_mae_pct": None,
            "avg_close_5d_pct": None,
            "median_mfe_pct": None,
            "min_mfe_pct": None,
            "max_mfe_pct": None,
            "median_mae_pct": None,
            "min_mae_pct": None,
            "max_mae_pct": None,
            "median_close_5d_pct": None,
            "min_close_5d_pct": None,
            "max_close_5d_pct": None,
            "close_loss_5pct_or_worse_pct": None,
            "close_hit_5pct_or_better_pct": None,
        }
    no_touch = sub.get("ordered_terminal_status", pd.Series("", index=sub.index)).fillna("").astype(str).eq("no_touch")
    mfe = pd.to_numeric(sub["ordered_mfe_pct"], errors="coerce").dropna()
    mae = pd.to_numeric(sub["ordered_mae_pct"], errors="coerce").dropna()
    close_5d = pd.to_numeric(sub.get("return_5d_pct", pd.Series(index=sub.index)), errors="coerce").dropna()
    return {
        "n": n,
        "win_pct": _round(sub["ordered_win"].mean() * 100.0),
        "stop_pct": _round(sub["ordered_stop"].mean() * 100.0),
        "no_touch_pct": _round(no_touch.mean() * 100.0),
        "avg_mfe_pct": _round(mfe.mean()) if len(mfe) else None,
        "avg_mae_pct": _round(mae.mean()) if len(mae) else None,
        "avg_close_5d_pct": _round(close_5d.mean()) if len(close_5d) else None,
        "median_mfe_pct": _round(mfe.median()) if len(mfe) else None,
        "min_mfe_pct": _round(mfe.min()) if len(mfe) else None,
        "max_mfe_pct": _round(mfe.max()) if len(mfe) else None,
        "median_mae_pct": _round(mae.median()) if len(mae) else None,
        "min_mae_pct": _round(mae.min()) if len(mae) else None,
        "max_mae_pct": _round(mae.max()) if len(mae) else None,
        "median_close_5d_pct": _round(close_5d.median()) if len(close_5d) else None,
        "min_close_5d_pct": _round(close_5d.min()) if len(close_5d) else None,
        "max_close_5d_pct": _round(close_5d.max()) if len(close_5d) else None,
        "close_loss_5pct_or_worse_pct": _round(close_5d.le(-5.0).mean() * 100.0) if len(close_5d) else None,
        "close_hit_5pct_or_better_pct": _round(close_5d.ge(5.0).mean() * 100.0) if len(close_5d) else None,
    }


def _rolling_folds(df: pd.DataFrame, *, min_train_days: int, fold_count: int) -> List[Dict[str, Any]]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) <= min_train_days:
        return []
    remaining = days[min_train_days:]
    fold_size = max(1, math.ceil(len(remaining) / max(1, fold_count)))
    folds: List[Dict[str, Any]] = []
    for idx in range(fold_count):
        test_days = remaining[idx * fold_size : (idx + 1) * fold_size]
        if not test_days:
            continue
        train_days = [day for day in days if day < test_days[0]]
        if len(train_days) < min_train_days:
            continue
        folds.append(
            {
                "fold": idx + 1,
                "train_range": [train_days[0], train_days[-1]],
                "test_range": [test_days[0], test_days[-1]],
                "train_mask": df["trade_date"].isin(train_days),
                "test_mask": df["trade_date"].isin(test_days),
            }
        )
    return folds


def evaluate_rule(
    df: pd.DataFrame,
    *,
    profile: str,
    conditions: Sequence[str],
    mask: pd.Series,
    train_mask: pd.Series,
    test_mask: pd.Series,
    folds: Sequence[Dict[str, Any]],
    min_train: int,
    min_test: int,
    min_fold_test: int,
) -> Dict[str, Any] | None:
    all_metrics = _metrics(df, mask)
    train_metrics = _metrics(df, mask & train_mask)
    test_metrics = _metrics(df, mask & test_mask)
    if int(train_metrics["n"]) < min_train or int(test_metrics["n"]) < min_test:
        return None
    fold_rows: List[Dict[str, Any]] = []
    total_n = 0
    total_wins = 0.0
    for fold in folds:
        fold_test = _metrics(df, mask & fold["test_mask"])
        fold_train = _metrics(df, mask & fold["train_mask"])
        if int(fold_test["n"]) < min_fold_test:
            continue
        total_n += int(fold_test["n"])
        total_wins += (float(fold_test["win_pct"] or 0.0) / 100.0) * int(fold_test["n"])
        fold_rows.append(
            {
                "fold": fold["fold"],
                "train_range": fold["train_range"],
                "test_range": fold["test_range"],
                "train": fold_train,
                "test": fold_test,
            }
        )
    if not fold_rows:
        return None
    fold_wins = [float(row["test"]["win_pct"] or 0.0) for row in fold_rows]
    fold_stops = [float(row["test"]["stop_pct"] or 0.0) for row in fold_rows]
    return {
        "profile": profile,
        "conditions": list(conditions),
        "depth": len(conditions),
        "uses_static_theme": _has_static_theme(conditions),
        "all": all_metrics,
        "train": train_metrics,
        "test": test_metrics,
        "fold_count": len(fold_rows),
        "fold_test_n_total": total_n,
        "fold_weighted_win_pct": _round((total_wins / total_n) * 100.0) if total_n else None,
        "fold_min_win_pct": _round(min(fold_wins)) if fold_wins else None,
        "fold_max_stop_pct": _round(max(fold_stops)) if fold_stops else None,
        "folds": fold_rows,
    }


def evaluate_curated_rules(
    df: pd.DataFrame,
    *,
    market: str,
    train_mask: pd.Series,
    test_mask: pd.Series,
    min_fold_test: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rule in curated_rules_for_market(market):
        prof = df[df["candidate_id"].eq(str(rule["profile"]))].copy()
        if prof.empty:
            continue
        mask = pd.Series(True, index=prof.index)
        ok = True
        for condition in rule["conditions"]:
            parsed = _condition_to_mask(prof, str(condition))
            if parsed is None:
                ok = False
                break
            mask &= parsed.fillna(False)
        if not ok:
            continue
        folds = _rolling_folds(prof, min_train_days=10, fold_count=4)
        row = evaluate_rule(
            prof,
            profile=str(rule["profile"]),
            conditions=list(rule["conditions"]),
            mask=mask,
            train_mask=train_mask.loc[prof.index],
            test_mask=test_mask.loc[prof.index],
            folds=folds,
            min_train=1,
            min_test=1,
            min_fold_test=min_fold_test,
        )
        if row is None:
            continue
        row["rule_id"] = rule["rule_id"]
        row["note"] = rule["note"]
        rows.append(row)
    return sorted(rows, key=_candidate_sort_key)


def search_profile(
    df: pd.DataFrame,
    *,
    profile: OrderedProfile,
    train_mask: pd.Series,
    test_mask: pd.Series,
    max_conditions: int,
    beam_width: int,
    min_train: int,
    min_test: int,
    min_fold_test: int,
    include_static_themes: bool,
) -> List[Dict[str, Any]]:
    prof = df[df["candidate_id"].eq(profile.name)].copy()
    if prof.empty:
        return []
    train = train_mask.loc[prof.index]
    test = test_mask.loc[prof.index]
    folds = _rolling_folds(prof, min_train_days=10, fold_count=4)
    conditions = build_condition_masks(
        prof,
        train_mask=train,
        include_static_themes=include_static_themes,
        max_conditions=max_conditions,
    )
    condition_map = {name: mask for name, mask in conditions}
    seen: set[Tuple[str, ...]] = set()
    evaluated: List[Dict[str, Any]] = []

    def maybe_add(names: Tuple[str, ...], mask: pd.Series) -> None:
        key = tuple(sorted(names))
        if key in seen:
            return
        seen.add(key)
        row = evaluate_rule(
            prof,
            profile=profile.name,
            conditions=list(names),
            mask=mask,
            train_mask=train,
            test_mask=test,
            folds=folds,
            min_train=min_train,
            min_test=min_test,
            min_fold_test=min_fold_test,
        )
        if row is not None:
            evaluated.append(row)

    for name, mask in conditions:
        maybe_add((name,), mask)

    useful = [
        (name, mask)
        for name, mask in conditions
        if int((mask & train).sum()) >= max(3, min_train // 2) and int((mask & test).sum()) >= max(2, min_test // 2)
    ]
    ranked_base = sorted(
        [
            row
            for row in evaluated
            if row["depth"] == 1 and int(row["train"]["n"]) >= min_train and int(row["test"]["n"]) >= min_test
        ],
        key=_candidate_sort_key,
    )[:beam_width]
    base_names = {tuple(row["conditions"])[0] for row in ranked_base}
    beam = [(name, condition_map[name]) for name in base_names if name in condition_map]

    for (name_a, mask_a), (name_b, mask_b) in combinations(useful, 2):
        if _feature_name(name_a) == _feature_name(name_b):
            continue
        if name_a not in base_names and name_b not in base_names:
            continue
        maybe_add((name_a, name_b), mask_a & mask_b)

    ranked_pairs = sorted(
        [row for row in evaluated if row["depth"] == 2],
        key=_candidate_sort_key,
    )[:beam_width]
    pair_sets = [tuple(row["conditions"]) for row in ranked_pairs]
    for pair in pair_sets:
        pair_features = {_feature_name(name) for name in pair}
        pair_mask = condition_map[pair[0]] & condition_map[pair[1]]
        for name_c, mask_c in beam:
            if name_c in pair or _feature_name(name_c) in pair_features:
                continue
            maybe_add(tuple(list(pair) + [name_c]), pair_mask & mask_c)

    ranked_triples = sorted(
        [row for row in evaluated if row["depth"] == 3],
        key=_candidate_sort_key,
    )[: max(10, beam_width // 2)]
    for triple_row in ranked_triples:
        triple = tuple(triple_row["conditions"])
        triple_features = {_feature_name(name) for name in triple}
        triple_mask = condition_map[triple[0]] & condition_map[triple[1]] & condition_map[triple[2]]
        for name_d, mask_d in beam:
            if name_d in triple or _feature_name(name_d) in triple_features:
                continue
            maybe_add(tuple(list(triple) + [name_d]), triple_mask & mask_d)

    return sorted(evaluated, key=_candidate_sort_key)


def _candidate_sort_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
    test = row.get("test") or {}
    train = row.get("train") or {}
    all_m = row.get("all") or {}
    return (
        -_metric_float(test.get("win_pct"), 0.0),
        -_metric_float(row.get("fold_weighted_win_pct"), 0.0),
        _metric_float(test.get("stop_pct"), 100.0),
        _metric_float(test.get("close_loss_5pct_or_worse_pct"), 100.0),
        -_metric_float(test.get("median_close_5d_pct"), -999.0),
        -_metric_float(all_m.get("avg_mfe_pct"), 0.0),
        -(int(test.get("n") or 0)),
        -_metric_float(train.get("win_pct"), 0.0),
    )


def _metric_float(value: Any, default: float) -> float:
    number = _safe_float(value)
    return default if number is None else float(number)


def classify_candidates(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    practical_watch: List[Dict[str, Any]] = []
    practical: List[Dict[str, Any]] = []
    strong_practical: List[Dict[str, Any]] = []
    recent_regime: List[Dict[str, Any]] = []
    promotion_ready: List[Dict[str, Any]] = []
    release_like: List[Dict[str, Any]] = []
    theme_dependent: List[Dict[str, Any]] = []
    high_win_small_n: List[Dict[str, Any]] = []
    for row in rows:
        all_m = row["all"]
        train = row["train"]
        test = row["test"]
        test_win = _metric_float(test.get("win_pct"), 0.0)
        test_stop = _metric_float(test.get("stop_pct"), 100.0)
        test_loss5 = _metric_float(test.get("close_loss_5pct_or_worse_pct"), 100.0)
        test_median_close = _metric_float(test.get("median_close_5d_pct"), -999.0)
        train_win = _metric_float(train.get("win_pct"), 0.0)
        all_win = _metric_float(all_m.get("win_pct"), 0.0)
        fold_win = _metric_float(row.get("fold_weighted_win_pct"), 0.0)
        min_fold = _metric_float(row.get("fold_min_win_pct"), 0.0)
        non_theme = not row["uses_static_theme"]

        if (
            non_theme
            and int(all_m["n"]) >= 10
            and int(test["n"]) >= 5
            and test_win >= 75.0
        ):
            practical_watch.append(row)
        if (
            non_theme
            and int(all_m["n"]) >= 18
            and int(train["n"]) >= 8
            and int(test["n"]) >= 8
            and all_win >= 60.0
            and train_win >= 55.0
            and test_win >= 75.0
            and test_stop <= 25.0
            and test_loss5 <= 15.0
            and test_median_close > 0.0
            and fold_win >= 65.0
            and min_fold >= 55.0
        ):
            practical.append(row)
        if (
            non_theme
            and int(all_m["n"]) >= 18
            and int(train["n"]) >= 8
            and int(test["n"]) >= 8
            and all_win >= 60.0
            and train_win >= 55.0
            and test_win >= 80.0
            and test_stop <= 20.0
            and test_loss5 <= 10.0
            and test_median_close > 0.0
            and fold_win >= 70.0
            and min_fold >= 60.0
        ):
            strong_practical.append(row)
        if (
            non_theme
            and int(all_m["n"]) >= 18
            and int(train["n"]) >= 8
            and int(test["n"]) >= 8
            and (all_win < 60.0 or train_win < 55.0)
            and test_win >= 75.0
            and test_stop <= 25.0
            and test_loss5 <= 15.0
            and test_median_close > 0.0
            and fold_win >= 65.0
            and min_fold >= 55.0
        ):
            recent_regime.append(row)
        if (
            not row["uses_static_theme"]
            and int(all_m["n"]) >= 18
            and int(train["n"]) >= 8
            and int(test["n"]) >= 8
            and all_win >= 70.0
            and train_win >= 65.0
            and test_win >= 70.0
            and fold_win >= 65.0
            and min_fold >= 50.0
            and test_stop <= 30.0
        ):
            release_like.append(row)
        if (
            non_theme
            and int(all_m["n"]) >= 30
            and int(train["n"]) >= 12
            and int(test["n"]) >= 12
            and int(row.get("fold_count") or 0) >= 3
            and all_win >= 75.0
            and train_win >= 75.0
            and test_win >= 80.0
            and fold_win >= 75.0
            and min_fold >= 65.0
            and test_stop <= 12.0
            and test_loss5 <= 5.0
            and test_median_close > 0.0
        ):
            promotion_ready.append(row)
        if row["uses_static_theme"] and test_win >= 75.0 and int(test["n"]) >= 5:
            theme_dependent.append(row)
        if (
            non_theme
            and int(all_m["n"]) >= 10
            and test_win >= 80.0
            and test_stop <= 20.0
        ):
            high_win_small_n.append(row)
    return {
        "practical_watch_75pct_non_theme": sorted(practical_watch, key=_candidate_sort_key)[:30],
        "practical_candidates_75pct_non_theme": sorted(practical, key=_candidate_sort_key)[:30],
        "strong_practical_80pct_non_theme": sorted(strong_practical, key=_candidate_sort_key)[:30],
        "recent_regime_75pct_non_theme": sorted(recent_regime, key=_candidate_sort_key)[:30],
        "promotion_ready_non_theme": sorted(promotion_ready, key=_candidate_sort_key)[:30],
        "release_like_non_theme": sorted(release_like, key=_candidate_sort_key)[:30],
        "high_win_small_n_non_theme": sorted(high_win_small_n, key=_candidate_sort_key)[:30],
        "theme_dependent_diagnostics": sorted(theme_dependent, key=_candidate_sort_key)[:30],
    }


def _cohort_baseline_by_profile(labeled: pd.DataFrame, profiles: Sequence[OrderedProfile]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    cohort_masks = _decision_masks(labeled)
    cohorts = ("Top1", "Top3", "Top5", "Exception Leader", "Top5+Exception")
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for profile in profiles:
        profile_mask = labeled["candidate_id"].eq(profile.name)
        out[profile.name] = {}
        for cohort in cohorts:
            cohort_mask = cohort_masks.get(cohort)
            if cohort_mask is None:
                continue
            out[profile.name][cohort] = _metrics(labeled, profile_mask & cohort_mask)
    return out


def build_report(
    input_path: Path,
    *,
    market: str,
    max_conditions: int,
    beam_width: int,
    min_train: int,
    min_test: int,
    min_fold_test: int,
    include_static_themes: bool,
    use_cached_labels: bool,
    cached_labels_path: Path,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    market = str(market).upper()
    profiles = profiles_for_market(market)
    if use_cached_labels and cached_labels_path.exists():
        labeled = pd.read_csv(cached_labels_path, low_memory=False)
    else:
        df = _load_dataset(input_path)
        profile_rows = prepare_profile_rows(df, profiles, market=market)
        labeled = label_selected_rows(profile_rows)
        labeled = add_search_columns(labeled)
        cached_labels_path.parent.mkdir(parents=True, exist_ok=True)
        labeled.to_csv(cached_labels_path, index=False)
    if "ordered_label_ready" not in labeled.columns:
        labeled = add_search_columns(labeled)
    labeled["trade_date"] = labeled["trade_date"].fillna("").astype(str)
    days = sorted(labeled["trade_date"].dropna().astype(str).unique().tolist())
    split_day = days[max(1, min(len(days) - 1, int(len(days) * 0.58)))] if len(days) >= 3 else None
    train_mask = labeled["trade_date"].lt(split_day) if split_day else pd.Series(False, index=labeled.index)
    test_mask = labeled["trade_date"].ge(split_day) if split_day else pd.Series(False, index=labeled.index)

    all_rows: List[Dict[str, Any]] = []
    for profile in profiles:
        all_rows.extend(
            search_profile(
                labeled,
                profile=profile,
                train_mask=train_mask,
                test_mask=test_mask,
                max_conditions=max_conditions,
                beam_width=beam_width,
                min_train=min_train,
                min_test=min_test,
                min_fold_test=min_fold_test,
                include_static_themes=include_static_themes,
            )
        )
    all_rows = sorted(all_rows, key=_candidate_sort_key)
    buckets = classify_candidates(all_rows)
    curated = evaluate_curated_rules(
        labeled,
        market=market,
        train_mask=train_mask,
        test_mask=test_mask,
        min_fold_test=min_fold_test,
    )
    report = {
        "report_version": REPORT_VERSION,
        "market": market,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "cached_labels_path": str(cached_labels_path),
        "profiles": [asdict(profile) for profile in profiles],
        "rows_labeled": int(len(labeled)),
        "ordered_label_ready_rows": int(labeled["ordered_label_ready"].sum()),
        "unique_ticker_dates": int(labeled[["ticker", "trade_date"]].drop_duplicates().shape[0])
        if {"ticker", "trade_date"}.issubset(labeled.columns)
        else None,
        "split_day": split_day,
        "search_config": {
            "max_conditions": max_conditions,
            "beam_width": beam_width,
            "min_train": min_train,
            "min_test": min_test,
            "min_fold_test": min_fold_test,
            "include_static_themes": include_static_themes,
            "static_theme_candidates_are_diagnostic_only": True,
        },
        "baseline_by_profile": {
            profile.name: {
                "all": _metrics(labeled, labeled["candidate_id"].eq(profile.name)),
                "train": _metrics(labeled, labeled["candidate_id"].eq(profile.name) & train_mask),
                "test": _metrics(labeled, labeled["candidate_id"].eq(profile.name) & test_mask),
            }
            for profile in profiles
        },
        "baseline_by_profile_cohort": _cohort_baseline_by_profile(labeled, profiles),
        "candidate_counts": {
            "evaluated": len(all_rows),
            "curated": len(curated),
            **{key: len(value) for key, value in buckets.items()},
        },
        "curated_ordered_candidates": curated,
        **buckets,
        "best_overall": all_rows[:50],
        "notes": [
            "Production scanner ranking is unchanged.",
            "Practical watch starts at ordered test win >=75%.",
            "Practical candidates require ordered test win >=75%, all win >=60%, train win >=55%, and stop/loss-tail/fold safeguards.",
            "Recent-regime candidates pass the latest test window but fail the all/train stability floor, so they are not promotion candidates.",
            "Strong practical candidates use ordered test win >=80%; promotion-ready remains stricter and requires larger samples.",
            "feature_quality is excluded from searched categorical conditions because it is a data completeness marker, not a trading signal.",
            "Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.",
            "Rows with immature no-touch labels are excluded from win-rate denominators.",
            "Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.",
        ],
    }
    return report, labeled


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    market = report.get("market") or "KOSPI"
    lines = [
        f"# {market} Ordered Candidate Search",
        "",
        f"- market: `{market}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- rows_labeled: `{report['rows_labeled']}`",
        f"- ordered_label_ready_rows: `{report['ordered_label_ready_rows']}`",
        f"- unique_ticker_dates: `{report['unique_ticker_dates']}`",
        f"- split_day: `{report['split_day']}`",
        "",
        "## Baseline",
        "",
    ]
    for profile, metrics in report["baseline_by_profile"].items():
        lines.append(
            f"- `{profile}`: all n={metrics['all']['n']} win={metrics['all']['win_pct']}%, "
            f"test n={metrics['test']['n']} win={metrics['test']['win_pct']}%, "
            f"test_stop={metrics['test']['stop_pct']}%"
        )
    lines.extend(["", "## Practical Watch 75pct Non-Theme", ""])
    if not report.get("practical_watch_75pct_non_theme"):
        lines.append("- none")
    for row in report.get("practical_watch_75pct_non_theme") or []:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Practical Candidates 75pct Non-Theme", ""])
    if not report.get("practical_candidates_75pct_non_theme"):
        lines.append("- none")
    for row in report.get("practical_candidates_75pct_non_theme") or []:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Strong Practical 80pct Non-Theme", ""])
    if not report.get("strong_practical_80pct_non_theme"):
        lines.append("- none")
    for row in report.get("strong_practical_80pct_non_theme") or []:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Recent-Regime 75pct Non-Theme Diagnostics", ""])
    if not report.get("recent_regime_75pct_non_theme"):
        lines.append("- none")
    for row in report.get("recent_regime_75pct_non_theme") or []:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Promotion-Ready Non-Theme Candidates", ""])
    if not report.get("promotion_ready_non_theme"):
        lines.append("- none")
    for row in report.get("promotion_ready_non_theme") or []:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Release-Like Non-Theme Candidates", ""])
    if not report["release_like_non_theme"]:
        lines.append("- none")
    for row in report["release_like_non_theme"][:15]:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Current Cohort Baseline", ""])
    cohort_report = report.get("baseline_by_profile_cohort") or {}
    for profile, cohorts in cohort_report.items():
        lines.append(f"### {profile}")
        lines.append("| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for cohort, metrics in cohorts.items():
            lines.append(
                "| "
                + " | ".join(
                    str(value)
                    for value in (
                        cohort,
                        metrics.get("n"),
                        metrics.get("win_pct"),
                        metrics.get("stop_pct"),
                        metrics.get("median_close_5d_pct"),
                        metrics.get("min_close_5d_pct"),
                        metrics.get("max_close_5d_pct"),
                        metrics.get("close_loss_5pct_or_worse_pct"),
                        metrics.get("avg_mfe_pct"),
                        metrics.get("min_mae_pct"),
                    )
                )
                + " |"
            )
        lines.append("")
    lines.extend(["", "## Curated Ordered Candidates", ""])
    if not report.get("curated_ordered_candidates"):
        lines.append("- none")
    for row in report.get("curated_ordered_candidates") or []:
        lines.append(_candidate_line(row, prefix=f"`{row['rule_id']}` "))
    lines.extend(["", "## High-Win Small-N Non-Theme Candidates", ""])
    if not report["high_win_small_n_non_theme"]:
        lines.append("- none")
    for row in report["high_win_small_n_non_theme"][:15]:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Theme-Dependent Diagnostics", ""])
    if not report["theme_dependent_diagnostics"]:
        lines.append("- none")
    for row in report["theme_dependent_diagnostics"][:10]:
        lines.append(_candidate_line(row))
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _candidate_line(row: Dict[str, Any], *, prefix: str = "") -> str:
    return (
        f"- {prefix}`{row['profile']}` {row['conditions']}: "
        f"all n={row['all']['n']} win={row['all']['win_pct']}%, "
        f"train n={row['train']['n']} win={row['train']['win_pct']}%, "
        f"test n={row['test']['n']} win={row['test']['win_pct']}%, "
        f"test_stop={row['test']['stop_pct']}%, "
        f"test_med_close={row['test'].get('median_close_5d_pct')}%, "
        f"test_min_close={row['test'].get('min_close_5d_pct')}%, "
        f"test_loss5={row['test'].get('close_loss_5pct_or_worse_pct')}%, "
        f"fold_win={row['fold_weighted_win_pct']}%, min_fold={row['fold_min_win_pct']}%, "
        f"avg_mfe={row['all']['avg_mfe_pct']}%, avg_mae={row['all']['avg_mae_pct']}%, "
        f"min_mae={row['all'].get('min_mae_pct')}%"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["KOSPI", "KOSDAQ"], default="KOSPI")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-conditions", type=int, default=240)
    parser.add_argument("--beam-width", type=int, default=70)
    parser.add_argument("--min-train", type=int, default=8)
    parser.add_argument("--min-test", type=int, default=8)
    parser.add_argument("--min-fold-test", type=int, default=3)
    parser.add_argument("--include-static-themes", action="store_true")
    parser.add_argument("--use-cached-labels", action="store_true")
    parser.add_argument(
        "--cached-labels",
        type=Path,
        default=DEFAULT_CACHED_LABELS,
    )
    args = parser.parse_args()
    if args.market == "KOSDAQ" and args.cached_labels == DEFAULT_CACHED_LABELS:
        args.cached_labels = DEFAULT_KOSDAQ_CACHED_LABELS

    report, labeled = build_report(
        args.input,
        market=args.market,
        max_conditions=args.max_conditions,
        beam_width=args.beam_width,
        min_train=args.min_train,
        min_test=args.min_test,
        min_fold_test=args.min_fold_test,
        include_static_themes=bool(args.include_static_themes),
        use_cached_labels=bool(args.use_cached_labels),
        cached_labels_path=args.cached_labels,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(report, args.output.with_suffix(".md"))
    if not args.cached_labels.exists():
        labeled.to_csv(args.cached_labels, index=False)
    print(
        json.dumps(
            {
                "json": str(args.output),
                "md": str(args.output.with_suffix(".md")),
                "rows_csv": str(args.cached_labels),
                "release_like": len(report["release_like_non_theme"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
