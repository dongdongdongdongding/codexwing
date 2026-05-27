#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from pandas.errors import PerformanceWarning

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_agent.tools.mine_significant_feature_combinations import (  # noqa: E402
    Predicate,
    _build_predicates_with_diagnostics,
    _metric_value,
)
from multi_agent.tools.run_internal_retrain_sweep import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_OUTPUT_DIR,
    _cohort_masks,
    _json_default,
    _load_dataset,
    _round,
    _split_days,
)

REPORT_VERSION = "loss_exclusion_guard_mining_v1"


@dataclass(frozen=True)
class ScopeFrame:
    market: str
    scope: str
    frame: pd.DataFrame


def _safe_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == "bool":
        return series.fillna(False)
    return series.fillna("").astype(str).str.lower().isin({"1", "true", "yes"})


def _parse_trade_date(df: pd.DataFrame) -> pd.Series:
    def parse_col(name: str) -> pd.Series:
        raw = df.get(name, pd.Series(index=df.index, dtype=object))
        text = raw.where(raw.notna(), "").astype(str).str.strip()
        cleaned = raw.where(text.ne(""), pd.NA)
        return pd.to_datetime(cleaned, errors="coerce", utc=True)

    base = parse_col("base_trade_date")
    recommended = parse_col("recommended_at")
    created = parse_col("created_at")
    return base.combine_first(recommended).combine_first(created).dt.strftime("%Y-%m-%d")


def _load_guard_dataset(path: Path, scan_mode: str) -> pd.DataFrame:
    mode = str(scan_mode or "SWING").upper()
    if mode == "SWING":
        return _load_dataset(path)
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in [
        "priority_rank",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "min_return_observed_pct",
        "max_high_return_5d_pct",
        "mfe_intraday_pct",
        "mae_intraday_pct",
        "feature_completeness",
        "conviction_score",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in [
        "is_dummy_data",
        "validation_excluded",
        "label_stop_loss_5pct",
        "explosive_leader_flag",
        "core_trend_flag",
        "target_before_stop_5d",
        "stop_before_target_5d",
    ]:
        if col in df.columns:
            df[f"{col}_bool"] = _safe_bool_series(df[col])

    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    scan_mode_col = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market_col = df.get("market", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market_type = df.get("market_type", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    mask = scan_mode_col.eq(mode) & (
        ticker.str.endswith(".KS")
        | ticker.str.endswith(".KQ")
        | market_col.isin(["KOSPI", "KOSDAQ"])
        | market_type.isin(["KOSPI", "KOSDAQ"])
    )
    if "is_dummy_data_bool" in df.columns:
        mask &= ~df["is_dummy_data_bool"]
    out = df.loc[mask].copy()
    out["market2"] = ""
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    out.loc[ticker.loc[out.index].str.endswith(".KQ"), "market2"] = "KOSDAQ"
    out.loc[out["market2"].eq("") & market_col.loc[out.index].isin(["KOSPI", "KOSDAQ"]), "market2"] = market_col.loc[out.index]
    out.loc[out["market2"].eq("") & market_type.loc[out.index].isin(["KOSPI", "KOSDAQ"]), "market2"] = market_type.loc[out.index]
    out["trade_date"] = _parse_trade_date(out)
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    if "recommended_at" not in out.columns:
        out["recommended_at"] = out["trade_date"]
    out = out.sort_values(["trade_date", "ticker", "priority_rank", "recommended_at"], na_position="last")
    out = out.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PerformanceWarning)
        out = out.groupby(["trade_date", "ticker"], as_index=False, sort=False).first()

    stop = pd.Series(False, index=out.index)
    if "stop_before_target_5d_bool" in out.columns:
        stop |= out["stop_before_target_5d_bool"].fillna(False)
    if "min_return_observed_pct" in out.columns:
        stop |= out["min_return_observed_pct"].le(-5.0).fillna(False)
    if "label_stop_loss_5pct_bool" in out.columns:
        stop |= out["label_stop_loss_5pct_bool"].fillna(False)
    out["stop5_proxy"] = stop
    out["bad_path"] = (
        stop
        | out.get("return_1d_pct", pd.Series(index=out.index)).lt(-3.0).fillna(False)
        | out.get("return_5d_pct", pd.Series(index=out.index)).lt(0.0).fillna(False)
    )
    out["exception_leader"] = (
        out.get("decision_bucket", pd.Series("", index=out.index)).fillna("").astype(str).str.lower().eq("exception_leader")
        | out.get("decision", pd.Series("", index=out.index)).fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
    )
    return out


def _pct(value: Any) -> float | None:
    rounded = _round(value, 6)
    return round(rounded * 100.0, 3) if rounded is not None else None


def _metrics_for_horizon(df: pd.DataFrame, mask: np.ndarray | pd.Series, horizon: str) -> Dict[str, Any]:
    if isinstance(mask, pd.Series):
        mask_values = mask.reindex(df.index).fillna(False).to_numpy(dtype=bool)
    else:
        mask_values = np.asarray(mask, dtype=bool)
    sub = df.loc[mask_values]
    return_col = f"return_{horizon}_pct"
    raw = pd.to_numeric(sub.get(return_col, pd.Series(index=sub.index, dtype=float)), errors="coerce")
    valid = raw.notna()
    horizon_sub = sub.loc[valid]
    values = raw.loc[valid]
    bad = horizon_sub.get("bad_path", pd.Series(False, index=horizon_sub.index)).fillna(False)
    stop = horizon_sub.get("stop5_proxy", pd.Series(False, index=horizon_sub.index)).fillna(False)
    return {
        "n": int(len(sub)),
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).fillna(False).mean()) if len(sub) else None,
        "stop5_pct": _pct(sub.get("stop5_proxy", pd.Series(False, index=sub.index)).fillna(False).mean()) if len(sub) else None,
        f"n_{horizon}": int(len(values)),
        f"active_days_{horizon}": int(horizon_sub["trade_date"].nunique()) if len(horizon_sub) and "trade_date" in horizon_sub.columns else 0,
        f"bad_path_{horizon}_pct": _pct(bad.mean()) if len(horizon_sub) else None,
        f"stop5_{horizon}_pct": _pct(stop.mean()) if len(horizon_sub) else None,
        f"win_{horizon}_pct": _pct(values.gt(0).mean()) if len(values) else None,
        f"avg_{horizon}_pct": _round(values.mean()) if len(values) else None,
        f"median_{horizon}_pct": _round(values.median()) if len(values) else None,
        f"min_{horizon}_pct": _round(values.min()) if len(values) else None,
        f"max_{horizon}_pct": _round(values.max()) if len(values) else None,
    }


def _scope_frames(df: pd.DataFrame, market: str, scopes: Sequence[str]) -> List[ScopeFrame]:
    market_df = df.loc[df["market2"].eq(market)].copy()
    masks = _cohort_masks(market_df)
    allowed = {scope.strip() for scope in scopes if scope.strip()}
    frames: List[ScopeFrame] = []
    for scope in ["top5", "exception_leader", "top5_exception", "ranked_top20", "core_trend", "explosive_leader"]:
        if allowed and scope not in allowed:
            continue
        mask = masks.get(scope)
        if mask is None:
            continue
        frame = market_df.loc[mask].copy()
        if len(frame) >= 24 and frame["trade_date"].nunique() >= 6:
            frames.append(ScopeFrame(market=market, scope=scope, frame=frame))
    return frames


def _combine_exclusion(predicates: Sequence[Predicate], size: int) -> np.ndarray:
    if not predicates:
        return np.zeros(size, dtype=bool)
    mask = np.zeros(size, dtype=bool)
    for pred in predicates:
        mask |= np.asarray(pred.mask, dtype=bool)
    return mask


def _feature_conflict(existing: Sequence[Predicate], candidate: Predicate) -> bool:
    return any(pred.feature == candidate.feature for pred in existing)


def _retention(base: Dict[str, Any], kept: Dict[str, Any], horizon: str) -> float | None:
    base_n = int(base.get(f"n_{horizon}") or 0)
    kept_n = int(kept.get(f"n_{horizon}") or 0)
    if base_n <= 0:
        return None
    return round(kept_n / base_n, 4)


def _delta(base: Dict[str, Any], kept: Dict[str, Any], key: str, default: float = 0.0) -> float | None:
    base_val = base.get(key)
    kept_val = kept.get(key)
    if base_val is None or kept_val is None:
        return None
    return _round(_metric_value(kept, key, default) - _metric_value(base, key, default), 4)


def _inverse_delta(base: Dict[str, Any], kept: Dict[str, Any], key: str, default: float = 100.0) -> float | None:
    base_val = base.get(key)
    kept_val = kept.get(key)
    if base_val is None or kept_val is None:
        return None
    return _round(_metric_value(base, key, default) - _metric_value(kept, key, default), 4)


def _score(
    *,
    base_test: Dict[str, Any],
    kept_test: Dict[str, Any],
    excluded_test: Dict[str, Any],
    horizon: str,
) -> float:
    win_delta = _delta(base_test, kept_test, f"win_{horizon}_pct", 0.0) or 0.0
    avg_delta = _delta(base_test, kept_test, f"avg_{horizon}_pct", -20.0) or 0.0
    bad_delta = _inverse_delta(base_test, kept_test, f"bad_path_{horizon}_pct", 100.0) or 0.0
    stop_delta = _inverse_delta(base_test, kept_test, f"stop5_{horizon}_pct", 100.0) or 0.0
    min_delta = _delta(base_test, kept_test, f"min_{horizon}_pct", -50.0) or 0.0
    retention = _retention(base_test, kept_test, horizon) or 0.0
    excluded_bad = _metric_value(excluded_test, f"bad_path_{horizon}_pct", 0.0)
    excluded_stop = _metric_value(excluded_test, f"stop5_{horizon}_pct", 0.0)
    return round(
        win_delta * 1.4
        + avg_delta * 3.0
        + bad_delta * 0.65
        + stop_delta * 0.45
        + min_delta * 0.25
        + retention * 10.0
        + min(excluded_bad, 100.0) * 0.08
        + min(excluded_stop, 100.0) * 0.05,
        4,
    )


def _guard_level(
    *,
    base_train: Dict[str, Any],
    base_test: Dict[str, Any],
    kept_train: Dict[str, Any],
    kept_test: Dict[str, Any],
    horizon: str,
    min_train: int,
    min_test: int,
    min_days: int,
    min_retention: float,
    production_horizons: set[str],
) -> str:
    train_n = int(kept_train.get(f"n_{horizon}") or 0)
    test_n = int(kept_test.get(f"n_{horizon}") or 0)
    train_days = int(kept_train.get(f"active_days_{horizon}") or 0)
    test_days = int(kept_test.get(f"active_days_{horizon}") or 0)
    test_retention = _retention(base_test, kept_test, horizon) or 0.0
    if train_n < min_train or test_n < min_test or train_days < min_days or test_days < min_days:
        return "sample_fail"
    if test_retention < min_retention:
        return "coverage_fail"

    train_win_delta = _delta(base_train, kept_train, f"win_{horizon}_pct") or -999.0
    test_win_delta = _delta(base_test, kept_test, f"win_{horizon}_pct") or -999.0
    train_avg_delta = _delta(base_train, kept_train, f"avg_{horizon}_pct", -20.0) or -999.0
    test_avg_delta = _delta(base_test, kept_test, f"avg_{horizon}_pct", -20.0) or -999.0
    test_bad_delta = _inverse_delta(base_test, kept_test, f"bad_path_{horizon}_pct", 100.0) or -999.0
    test_stop_delta = _inverse_delta(base_test, kept_test, f"stop5_{horizon}_pct", 100.0) or -999.0
    kept_test_win = _metric_value(kept_test, f"win_{horizon}_pct")
    kept_test_avg = _metric_value(kept_test, f"avg_{horizon}_pct", -999.0)
    kept_test_bad = _metric_value(kept_test, f"bad_path_{horizon}_pct", 100.0)
    kept_test_stop = _metric_value(kept_test, f"stop5_{horizon}_pct", 100.0)
    kept_test_min = _metric_value(kept_test, f"min_{horizon}_pct", -999.0)

    if (
        train_win_delta >= 3.0
        and test_win_delta >= 5.0
        and train_avg_delta >= 0.5
        and test_avg_delta >= 1.0
        and test_bad_delta >= 5.0
        and test_stop_delta >= 3.0
        and kept_test_win >= 70.0
        and kept_test_avg > 0.0
        and kept_test_bad <= 35.0
        and kept_test_stop <= 25.0
        and kept_test_min >= -12.0
    ):
        if horizon in production_horizons:
            return "production_candidate"
        return "shadow_candidate"
    if train_win_delta >= 2.0 and test_win_delta >= 3.0 and test_avg_delta >= 0.5 and test_bad_delta >= 2.0:
        return "shadow_candidate"
    return "diagnostic"


def _payload(
    *,
    guard_id: int,
    market: str,
    scope: str,
    cut_day: str | None,
    horizon: str,
    predicates: Sequence[Predicate],
    base_train: Dict[str, Any],
    base_test: Dict[str, Any],
    kept_train: Dict[str, Any],
    kept_test: Dict[str, Any],
    excluded_train: Dict[str, Any],
    excluded_test: Dict[str, Any],
    min_train: int,
    min_test: int,
    min_days: int,
    min_retention: float,
    production_horizons: set[str],
) -> Dict[str, Any]:
    level = _guard_level(
        base_train=base_train,
        base_test=base_test,
        kept_train=kept_train,
        kept_test=kept_test,
        horizon=horizon,
        min_train=min_train,
        min_test=min_test,
        min_days=min_days,
        min_retention=min_retention,
        production_horizons=production_horizons,
    )
    return {
        "guard_id": guard_id,
        "market": market,
        "scope": scope,
        "cut_day": cut_day,
        "horizon": horizon,
        "term_count": len(predicates),
        "exclude_conditions": [pred.label for pred in predicates],
        "features": [pred.feature for pred in predicates],
        "base_train": base_train,
        "base_test": base_test,
        "kept_train": kept_train,
        "kept_test": kept_test,
        "excluded_train": excluded_train,
        "excluded_test": excluded_test,
        "test_retention": _retention(base_test, kept_test, horizon),
        "test_win_delta": _delta(base_test, kept_test, f"win_{horizon}_pct"),
        "test_avg_delta": _delta(base_test, kept_test, f"avg_{horizon}_pct", -20.0),
        "test_bad_path_reduction": _inverse_delta(base_test, kept_test, f"bad_path_{horizon}_pct", 100.0),
        "test_stop5_reduction": _inverse_delta(base_test, kept_test, f"stop5_{horizon}_pct", 100.0),
        "test_min_return_delta": _delta(base_test, kept_test, f"min_{horizon}_pct", -50.0),
        "score": _score(base_test=base_test, kept_test=kept_test, excluded_test=excluded_test, horizon=horizon),
        "guard_level": level,
        "production_candidate": level == "production_candidate",
        "shadow_candidate": level in {"production_candidate", "shadow_candidate"},
    }


def _candidate_sort_key(row: Dict[str, Any]) -> Tuple[int, int, float, float, float, float, int]:
    horizon = str(row.get("horizon") or "5d")
    kept = row.get("kept_test") or {}
    return (
        1 if row.get("production_candidate") else 0,
        1 if row.get("shadow_candidate") else 0,
        float(row.get("score") or -999.0),
        _metric_value(kept, f"win_{horizon}_pct"),
        _metric_value(kept, f"avg_{horizon}_pct", -999.0),
        _metric_value(kept, f"min_{horizon}_pct", -999.0),
        int(kept.get(f"n_{horizon}") or 0),
    )


def _mine_scope(
    frame: pd.DataFrame,
    *,
    market: str,
    scope: str,
    horizons: Sequence[str],
    train_ratio: float,
    min_train: int,
    min_test: int,
    min_days: int,
    min_excluded: int,
    min_retention: float,
    beam_width: int,
    max_terms: int,
    include_primary_theme: bool,
    production_horizons: set[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    scoped = frame.copy()
    train_mask, test_mask, cut_day = _split_days(scoped, train_ratio)
    train_values = train_mask.to_numpy(dtype=bool)
    test_values = test_mask.to_numpy(dtype=bool)
    diagnostics: Dict[str, Any] = {
        "market": market,
        "scope": scope,
        "rows": int(len(scoped)),
        "trade_days": int(scoped["trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
        "cut_day": cut_day,
        "train_rows": int(train_values.sum()),
        "test_rows": int(test_values.sum()),
        "predicate_counts": {},
        "predicate_support_screen": {},
        "beam": {},
        "guard_levels": Counter(),
    }
    if train_values.sum() < min_train or test_values.sum() < min_test:
        diagnostics["skip_reason"] = "split_below_min_rows"
        return [], diagnostics

    predicates, predicate_diag = _build_predicates_with_diagnostics(
        scoped,
        basis_mask=train_values,
        min_support=max(3, min_excluded),
        max_support_ratio=0.75,
        include_primary_theme=include_primary_theme,
    )
    diagnostics.update(predicate_diag)

    screened: List[Predicate] = []
    support_counter = Counter()
    for pred in predicates:
        mask = np.asarray(pred.mask, dtype=bool)
        train_excluded = int((mask & train_values).sum())
        test_excluded = int((mask & test_values).sum())
        train_kept = int((~mask & train_values).sum())
        test_kept = int((~mask & test_values).sum())
        if train_excluded < min_excluded:
            support_counter["rejected_train_excluded"] += 1
            continue
        if test_excluded < max(2, min_excluded // 2):
            support_counter["rejected_test_excluded"] += 1
            continue
        if train_kept < min_train:
            support_counter["rejected_train_kept"] += 1
            continue
        if test_kept < min_test:
            support_counter["rejected_test_kept"] += 1
            continue
        screened.append(pred)
        support_counter["kept"] += 1
    diagnostics["predicate_counts"]["after_exclusion_screen"] = len(screened)
    diagnostics["predicate_support_screen"] = dict(support_counter.most_common())

    rows: List[Dict[str, Any]] = []
    guard_counter = count(1)
    for horizon in horizons:
        base_train = _metrics_for_horizon(scoped, train_values, horizon)
        base_test = _metrics_for_horizon(scoped, test_values, horizon)
        singleton_rows: List[Tuple[float, Tuple[Predicate, ...], Dict[str, Any]]] = []
        singleton_counter = Counter({"evaluated": len(screened)})

        for pred in screened:
            exclusion = np.asarray(pred.mask, dtype=bool)
            keep = ~exclusion
            kept_train = _metrics_for_horizon(scoped, keep & train_values, horizon)
            kept_test = _metrics_for_horizon(scoped, keep & test_values, horizon)
            excluded_train = _metrics_for_horizon(scoped, exclusion & train_values, horizon)
            excluded_test = _metrics_for_horizon(scoped, exclusion & test_values, horizon)
            payload = _payload(
                guard_id=next(guard_counter),
                market=market,
                scope=scope,
                cut_day=cut_day,
                horizon=horizon,
                predicates=[pred],
                base_train=base_train,
                base_test=base_test,
                kept_train=kept_train,
                kept_test=kept_test,
                excluded_train=excluded_train,
                excluded_test=excluded_test,
                min_train=min_train,
                min_test=min_test,
                min_days=min_days,
                min_retention=min_retention,
                production_horizons=production_horizons,
            )
            rows.append(payload)
            diagnostics["guard_levels"][payload["guard_level"]] += 1
            if payload["guard_level"] != "sample_fail":
                singleton_rows.append((float(payload["score"] or -999.0), (pred,), payload))
                singleton_counter["passed_sample"] += 1
            else:
                singleton_counter["sample_fail"] += 1

        singleton_rows.sort(key=lambda item: item[0], reverse=True)
        base_pool = [row[1][0] for row in singleton_rows[: max(beam_width * 2, beam_width)]]
        beam = singleton_rows[:beam_width]
        diagnostics["beam"][horizon] = [dict(singleton_counter, base_pool=len(base_pool), initial_beam=len(beam))]
        seen = {tuple(pred.key for pred in preds) for _score_value, preds, _payload_row in beam}

        for term_count in range(2, max_terms + 1):
            expanded: List[Tuple[float, Tuple[Predicate, ...], Dict[str, Any]]] = []
            counter = Counter({"term_count": term_count, "parent_beam": len(beam), "base_pool": len(base_pool)})
            for _score_value, preds, _row in beam:
                existing_keys = {pred.key for pred in preds}
                for candidate in base_pool:
                    counter["attempted"] += 1
                    if candidate.key in existing_keys or _feature_conflict(preds, candidate):
                        counter["skipped_feature_conflict"] += 1
                        continue
                    combo = tuple(sorted((*preds, candidate), key=lambda item: item.key))
                    key = tuple(pred.key for pred in combo)
                    if key in seen:
                        counter["skipped_duplicate"] += 1
                        continue
                    seen.add(key)
                    exclusion = _combine_exclusion(combo, len(scoped))
                    keep = ~exclusion
                    kept_train = _metrics_for_horizon(scoped, keep & train_values, horizon)
                    kept_test = _metrics_for_horizon(scoped, keep & test_values, horizon)
                    if int(kept_train.get(f"n_{horizon}") or 0) < min_train:
                        counter["rejected_train_kept"] += 1
                        continue
                    if int(kept_test.get(f"n_{horizon}") or 0) < min_test:
                        counter["rejected_test_kept"] += 1
                        continue
                    excluded_train = _metrics_for_horizon(scoped, exclusion & train_values, horizon)
                    excluded_test = _metrics_for_horizon(scoped, exclusion & test_values, horizon)
                    payload = _payload(
                        guard_id=next(guard_counter),
                        market=market,
                        scope=scope,
                        cut_day=cut_day,
                        horizon=horizon,
                        predicates=combo,
                        base_train=base_train,
                        base_test=base_test,
                        kept_train=kept_train,
                        kept_test=kept_test,
                        excluded_train=excluded_train,
                        excluded_test=excluded_test,
                        min_train=min_train,
                        min_test=min_test,
                        min_days=min_days,
                        min_retention=min_retention,
                        production_horizons=production_horizons,
                    )
                    rows.append(payload)
                    diagnostics["guard_levels"][payload["guard_level"]] += 1
                    expanded.append((float(payload["score"] or -999.0), combo, payload))
                    counter["emitted"] += 1
            expanded.sort(key=lambda item: item[0], reverse=True)
            counter["expanded_survivors"] = len(expanded)
            counter["pruned_by_beam"] = max(0, len(expanded) - beam_width)
            beam = expanded[:beam_width]
            counter["next_beam"] = len(beam)
            diagnostics["beam"][horizon].append(dict(counter))
            if not beam:
                break
    diagnostics["guard_levels"] = dict(diagnostics["guard_levels"].most_common())
    return rows, diagnostics


def build_report(
    df: pd.DataFrame,
    *,
    scan_mode: str,
    markets: Sequence[str],
    scopes: Sequence[str],
    horizons: Sequence[str],
    train_ratio: float,
    min_train: int,
    min_test: int,
    min_days: int,
    min_excluded: int,
    min_retention: float,
    beam_width: int,
    max_terms: int,
    include_primary_theme: bool,
    production_horizons: Sequence[str],
) -> Dict[str, Any]:
    market_list = [market.strip().upper() for market in markets if market.strip()]
    horizon_list = [horizon.strip().lower() for horizon in horizons if horizon.strip()]
    production_horizon_set = {horizon.strip().lower() for horizon in production_horizons if horizon.strip()}
    all_rows: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    for market in market_list:
        for scoped in _scope_frames(df, market, scopes):
            rows, diag = _mine_scope(
                scoped.frame,
                market=scoped.market,
                scope=scoped.scope,
                horizons=horizon_list,
                train_ratio=train_ratio,
                min_train=min_train,
                min_test=min_test,
                min_days=min_days,
                min_excluded=min_excluded,
                min_retention=min_retention,
                beam_width=beam_width,
                max_terms=max_terms,
                include_primary_theme=include_primary_theme,
                production_horizons=production_horizon_set,
            )
            all_rows.extend(rows)
            diagnostics.append(diag)
    all_rows.sort(key=_candidate_sort_key, reverse=True)
    production = [row for row in all_rows if row.get("production_candidate")]
    shadow = [row for row in all_rows if row.get("shadow_candidate")]
    guard_levels = Counter(row.get("guard_level") or "unknown" for row in all_rows)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_rows": int(len(df)),
        "markets": df["market2"].value_counts().to_dict() if "market2" in df.columns else {},
        "search_config": {
            "scan_mode": str(scan_mode or "SWING").upper(),
            "markets": market_list,
            "scopes": [scope.strip() for scope in scopes if scope.strip()] or "default",
            "horizons": horizon_list,
            "train_ratio": train_ratio,
            "min_train": min_train,
            "min_test": min_test,
            "min_days": min_days,
            "min_excluded": min_excluded,
            "min_retention": min_retention,
            "beam_width": beam_width,
            "max_terms": max_terms,
            "include_primary_theme": include_primary_theme,
            "production_horizons": sorted(production_horizon_set),
        },
        "guard_count": int(len(all_rows)),
        "production_candidate_count": int(len(production)),
        "shadow_candidate_count": int(len(shadow)),
        "guard_levels": dict(guard_levels.most_common()),
        "top_guards": all_rows[:160],
        "production_candidates": production[:80],
        "shadow_candidates": shadow[:120],
        "diagnostics": diagnostics,
        "notes": [
            "Internal research only; production scanner/model artifacts are unchanged.",
            "Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.",
            "Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.",
            "Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.",
            "Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.",
            "By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.",
        ],
    }


def _metric(row: Dict[str, Any], section: str, horizon: str, key: str) -> Any:
    return (row.get(section) or {}).get(f"{key}_{horizon}_pct")


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Loss Exclusion Guard Mining",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- report_version: `{report.get('report_version')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- guard_count: `{report.get('guard_count')}`",
        f"- production_candidate_count: `{report.get('production_candidate_count')}`",
        f"- shadow_candidate_count: `{report.get('shadow_candidate_count')}`",
        f"- guard_levels: `{report.get('guard_levels')}`",
        "",
        "## Top Exclusion Guards",
        "",
        "| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for idx, row in enumerate(report.get("top_guards", [])[:80], start=1):
        horizon = str(row.get("horizon") or "5d")
        lines.append(
            "| "
            + " | ".join(
                str(v)
                for v in [
                    idx,
                    row.get("guard_level"),
                    row.get("market"),
                    row.get("scope"),
                    horizon,
                    row.get("term_count"),
                    row.get("test_retention"),
                    _metric(row, "base_test", horizon, "win"),
                    _metric(row, "kept_test", horizon, "win"),
                    row.get("test_win_delta"),
                    _metric(row, "base_test", horizon, "avg"),
                    _metric(row, "kept_test", horizon, "avg"),
                    row.get("test_avg_delta"),
                    _metric(row, "kept_test", horizon, "min"),
                    row.get("test_bad_path_reduction"),
                    row.get("test_stop5_reduction"),
                    "<br>".join(row.get("exclude_conditions") or []),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Production Candidates", ""])
    if not report.get("production_candidates"):
        lines.append("- None found under current holdout gate.")
    for row in report.get("production_candidates", [])[:40]:
        horizon = str(row.get("horizon") or "5d")
        lines.append(
            f"- `{row.get('market')}` `{row.get('scope')}` `{horizon}` "
            f"kept_win={_metric(row, 'kept_test', horizon, 'win')} "
            f"kept_avg={_metric(row, 'kept_test', horizon, 'avg')} "
            f"bad_reduction={row.get('test_bad_path_reduction')} "
            f"stop_reduction={row.get('test_stop5_reduction')} :: "
            + " / ".join(row.get("exclude_conditions") or [])
        )
    lines.extend(["", "## Shadow Candidates", ""])
    if not report.get("shadow_candidates"):
        lines.append("- None found under current shadow gate.")
    for row in report.get("shadow_candidates", [])[:30]:
        horizon = str(row.get("horizon") or "5d")
        lines.append(
            f"- `{row.get('market')}` `{row.get('scope')}` `{horizon}` "
            f"level={row.get('guard_level')} retain={row.get('test_retention')} "
            f"win_delta={row.get('test_win_delta')} avg_delta={row.get('test_avg_delta')} :: "
            + " / ".join(row.get("exclude_conditions") or [])
        )
    lines.extend(["", "## Diagnostics", ""])
    for diag in report.get("diagnostics", [])[:20]:
        lines.append(
            f"- `{diag.get('market')}` `{diag.get('scope')}` rows={diag.get('rows')} "
            f"days={diag.get('trade_days')} cut={diag.get('cut_day')} "
            f"predicates={((diag.get('predicate_counts') or {}).get('after_exclusion_screen'))} "
            f"levels={diag.get('guard_levels')}"
        )
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine train/holdout KR scan loss-exclusion guard candidates.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stem", default="loss_exclusion_guards")
    parser.add_argument("--scan-mode", choices=["SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--scopes", default="top5,exception_leader,top5_exception,ranked_top20")
    parser.add_argument("--horizons", default="1d,3d,5d")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--min-train", type=int, default=18)
    parser.add_argument("--min-test", type=int, default=8)
    parser.add_argument("--min-days", type=int, default=5)
    parser.add_argument("--min-excluded", type=int, default=8)
    parser.add_argument("--min-retention", type=float, default=0.35)
    parser.add_argument("--beam-width", type=int, default=32)
    parser.add_argument("--max-terms", type=int, default=3)
    parser.add_argument("--include-primary-theme", action="store_true")
    parser.add_argument("--production-horizons", default="3d,5d")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = _load_guard_dataset(Path(args.input), str(args.scan_mode))
    report = build_report(
        df,
        scan_mode=str(args.scan_mode),
        markets=[part.strip() for part in str(args.markets).split(",")],
        scopes=[part.strip() for part in str(args.scopes).split(",") if part.strip()],
        horizons=[part.strip() for part in str(args.horizons).split(",") if part.strip()],
        train_ratio=float(args.train_ratio),
        min_train=int(args.min_train),
        min_test=int(args.min_test),
        min_days=int(args.min_days),
        min_excluded=int(args.min_excluded),
        min_retention=float(args.min_retention),
        beam_width=int(args.beam_width),
        max_terms=int(args.max_terms),
        include_primary_theme=bool(args.include_primary_theme),
        production_horizons=[part.strip() for part in str(args.production_horizons).split(",") if part.strip()],
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
                "guard_count": report.get("guard_count"),
                "production_candidate_count": report.get("production_candidate_count"),
                "shadow_candidate_count": report.get("shadow_candidate_count"),
                "best": (report.get("top_guards") or [None])[0],
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
