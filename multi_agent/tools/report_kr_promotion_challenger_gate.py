#!/usr/bin/env python3
"""Compare KR scanner promotion challengers under one release gate.

This report is intentionally non-operational. It normalizes the current
operator cohorts and shadow/watch candidates into one promotion-review table so
we can decide whether a challenger is mature enough to be proposed for
production. It does not change scanner ranking, UI admission, Discord output,
or model artifacts.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.practical_entry_gate import evaluate_practical_entry_gate
from multi_agent.tools.experimental_kospi_ordered_candidate_search import add_search_columns
from multi_agent.tools.report_ordered_shadow_watch import (
    EXTRA_WATCH_RULES as ORDERED_EXTRA_WATCH_RULES,
    _default_cache_path as _ordered_cache_path,
    _rule_mask as _ordered_rule_mask,
    _watch_rules_for_market as _ordered_watch_rules_for_market,
)
from multi_agent.tools.run_internal_retrain_sweep import (
    DEFAULT_INPUT,
    _cohort_masks,
    _json_default,
    _load_dataset,
    _split_days,
)


REPORT_VERSION = "kr_promotion_challenger_gate_v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/validation/kr_promotion_challenger_gate.json"
DEFAULT_DYNAMIC_COMBO_GLOB = str(PROJECT_ROOT / "runtime_state/reports/experimental/significant_feature_combinations*.json")
DEFAULT_MODEL_SWEEP_GLOB = str(PROJECT_ROOT / "runtime_state/reports/experimental/internal_retrain_sweep*.json")

PROMOTION_GATE: Dict[str, Any] = {
    "min_train_n": 18,
    "min_train_days": 6,
    "min_train_effective_win_5d_pct": 70.0,
    "min_test_n": 8,
    "min_test_days": 5,
    "min_test_effective_win_5d_pct": 73.0,
    "min_test_win_3d_pct": 60.0,
    "min_test_avg_5d_pct": 3.0,
    "min_test_min_5d_pct": -15.0,
    "max_test_bad_path_pct": 25.0,
    "max_test_stop5_pct": 10.0,
    "max_test_early_drop_1d_pct": 20.0,
}


@dataclass(frozen=True)
class CloseCandidateSpec:
    candidate_id: str
    market: str
    candidate_type: str
    source: str
    description: str
    mask_fn: Callable[[pd.DataFrame], pd.Series]
    conditions: Tuple[str, ...] = ()


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default


def _round(value: Any, digits: int = 4) -> Optional[float]:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number, digits)


def _pct(value: Any) -> Optional[float]:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number * 100.0, 3)


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype("string").fillna("").str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _series(df: pd.DataFrame, column: str, default: Any = None) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(default, index=df.index)


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(_series(df, column), errors="coerce")


def _wilson_lower_pct(successes: int, total: int, z: float = 1.96) -> Optional[float]:
    if total <= 0:
        return None
    phat = successes / total
    denom = 1.0 + z * z / total
    centre = phat + z * z / (2.0 * total)
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * total)) / total)
    return round(max(0.0, (centre - margin) / denom) * 100.0, 3)


def _posterior_pct(successes: int, total: int, *, prior_pct: float = 60.0, prior_n: int = 8) -> Optional[float]:
    if total <= 0:
        return None
    posterior = (successes + prior_n * (prior_pct / 100.0)) / (total + prior_n)
    return round(posterior * 100.0, 3)


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "market2" not in out.columns:
        ticker = _series(out, "ticker", "").fillna("").astype(str).str.upper()
        market = _series(out, "market", "").fillna("").astype(str).str.upper()
        out["market2"] = ""
        out.loc[ticker.str.endswith(".KS"), "market2"] = "KOSPI"
        out.loc[ticker.str.endswith(".KQ"), "market2"] = "KOSDAQ"
        out.loc[out["market2"].eq("") & market.isin(["KOSPI", "KOSDAQ"]), "market2"] = market
    if "trade_date" not in out.columns:
        rec = _series(out, "base_trade_date")
        created = _series(out, "recommended_at")
        rec = rec.where(rec.notna() & rec.astype(str).str.strip().ne(""), created)
        out["trade_date"] = pd.to_datetime(rec, errors="coerce", utc=True, format="mixed").dt.strftime("%Y-%m-%d")
    if "exception_leader" not in out.columns:
        out["exception_leader"] = (
            _series(out, "decision_bucket", "").fillna("").astype(str).str.lower().eq("exception_leader")
            | _series(out, "decision", "").fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
        )
    if "ordered_path_exact" not in out.columns:
        out["ordered_path_exact"] = _series(out, "outcome_path_label_version", "").fillna("").astype(str).str.contains("stop_first", case=False)
    if "stop5_proxy" not in out.columns:
        stop = pd.Series(False, index=out.index)
        if "stop_before_target_5d" in out.columns:
            stop |= _bool_series(out["stop_before_target_5d"])
        if "label_stop_loss_5pct" in out.columns:
            stop |= _bool_series(out["label_stop_loss_5pct"])
        if "min_return_observed_pct" in out.columns:
            stop |= _numeric(out, "min_return_observed_pct").le(-5.0).fillna(False)
        out["stop5_proxy"] = stop
    if "bad_path" not in out.columns:
        out["bad_path"] = (
            _bool_series(_series(out, "stop5_proxy", False))
            | _numeric(out, "return_1d_pct").lt(-3.0).fillna(False)
            | _numeric(out, "return_5d_pct").lt(0.0).fillna(False)
        )
    if "practical_gate_level" not in out.columns:
        out["practical_gate_level"] = [evaluate_practical_entry_gate(row).get("level") for row in out.to_dict("records")]
    return out


def _close_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "n": 0,
            "active_days": 0,
            "effective_win_5d_pct": None,
            "calibrated_effective_win_5d_pct": None,
            "wilson_lower_effective_win_5d_pct": None,
        }
    ret1 = _numeric(df, "return_1d_pct")
    ret3 = _numeric(df, "return_3d_pct")
    ret5 = _numeric(df, "return_5d_pct")
    valid5 = ret5.notna()
    sub = df.loc[valid5].copy()
    if sub.empty:
        return {
            "n": 0,
            "active_days": 0,
            "effective_win_5d_pct": None,
            "calibrated_effective_win_5d_pct": None,
            "wilson_lower_effective_win_5d_pct": None,
        }
    ret1 = ret1.loc[sub.index]
    ret3 = ret3.loc[sub.index]
    ret5 = ret5.loc[sub.index]
    stop = _bool_series(_series(sub, "stop5_proxy", False))
    bad = _bool_series(_series(sub, "bad_path", False))
    early_drop = ret1.lt(-3.0).fillna(False)
    loss5 = ret5.lt(0.0).fillna(False)
    practical_win5 = ret5.gt(0.0).fillna(False) & ret1.ge(-3.0).fillna(False) & ~stop
    target_before_stop = pd.Series(False, index=sub.index)
    if "target_before_stop_5d" in sub.columns:
        target_before_stop = _bool_series(sub["target_before_stop_5d"])
    elif "max_high_return_5d_pct" in sub.columns:
        target_before_stop = _numeric(sub, "max_high_return_5d_pct").ge(5.0).fillna(False) & ~stop
    successes = int(practical_win5.sum())
    n = int(len(sub))
    out: Dict[str, Any] = {
        "n": n,
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "effective_win_5d_pct": _pct(practical_win5.mean()),
        "practical_win_5d_pct": _pct(practical_win5.mean()),
        "calibrated_effective_win_5d_pct": _posterior_pct(successes, n),
        "wilson_lower_effective_win_5d_pct": _wilson_lower_pct(successes, n),
        "target_before_stop_5d_pct": _pct(target_before_stop.mean()),
        "bad_path_pct": _pct(bad.mean()),
        "early_drop_1d_pct": _pct(early_drop.mean()),
        "loss_5d_pct": _pct(loss5.mean()),
        "stop5_pct": _pct(stop.mean()),
    }
    for horizon, values in [("1d", ret1), ("3d", ret3), ("5d", ret5)]:
        valid = values.dropna()
        out[f"n_{horizon}"] = int(len(valid))
        out[f"win_{horizon}_pct"] = _pct(valid.gt(0).mean()) if len(valid) else None
        out[f"avg_{horizon}_pct"] = _round(valid.mean()) if len(valid) else None
        out[f"median_{horizon}_pct"] = _round(valid.median()) if len(valid) else None
        out[f"min_{horizon}_pct"] = _round(valid.min()) if len(valid) else None
        out[f"max_{horizon}_pct"] = _round(valid.max()) if len(valid) else None
    return out


def _split_eval(df: pd.DataFrame, selected: pd.Series, *, train_ratio: float) -> Tuple[str | None, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    selected = selected.reindex(df.index).fillna(False)
    scoped = df.loc[selected].copy()
    if scoped.empty:
        return None, _close_metrics(scoped), _close_metrics(scoped), _close_metrics(scoped)
    train_mask, test_mask, cut_day = _split_days(scoped, train_ratio)
    return cut_day, _close_metrics(scoped), _close_metrics(scoped.loc[train_mask]), _close_metrics(scoped.loc[test_mask])


def _check(name: str, actual: Any, expected: str, passed: bool) -> Dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": bool(passed)}


def _num_metric(metrics: Mapping[str, Any], key: str, default: float) -> float:
    value = _safe_float(metrics.get(key))
    return default if value is None else value


def _gate_checks(train: Mapping[str, Any], test: Mapping[str, Any], gate: Mapping[str, Any] = PROMOTION_GATE) -> List[Dict[str, Any]]:
    return [
        _check("train_n", train.get("n"), f">={gate['min_train_n']}", int(train.get("n") or 0) >= int(gate["min_train_n"])),
        _check("train_days", train.get("active_days"), f">={gate['min_train_days']}", int(train.get("active_days") or 0) >= int(gate["min_train_days"])),
        _check(
            "train_effective_win_5d",
            train.get("effective_win_5d_pct"),
            f">={gate['min_train_effective_win_5d_pct']}%",
            _num_metric(train, "effective_win_5d_pct", 0.0) >= float(gate["min_train_effective_win_5d_pct"]),
        ),
        _check("test_n", test.get("n"), f">={gate['min_test_n']}", int(test.get("n") or 0) >= int(gate["min_test_n"])),
        _check("test_days", test.get("active_days"), f">={gate['min_test_days']}", int(test.get("active_days") or 0) >= int(gate["min_test_days"])),
        _check(
            "test_effective_win_5d",
            test.get("effective_win_5d_pct"),
            f">={gate['min_test_effective_win_5d_pct']}%",
            _num_metric(test, "effective_win_5d_pct", 0.0) >= float(gate["min_test_effective_win_5d_pct"]),
        ),
        _check(
            "test_win_3d",
            test.get("win_3d_pct"),
            f">={gate['min_test_win_3d_pct']}%",
            _num_metric(test, "win_3d_pct", 0.0) >= float(gate["min_test_win_3d_pct"]),
        ),
        _check(
            "test_avg_5d",
            test.get("avg_5d_pct"),
            f">={gate['min_test_avg_5d_pct']}%",
            _num_metric(test, "avg_5d_pct", -999.0) >= float(gate["min_test_avg_5d_pct"]),
        ),
        _check(
            "test_min_5d",
            test.get("min_5d_pct"),
            f">={gate['min_test_min_5d_pct']}%",
            _num_metric(test, "min_5d_pct", -999.0) >= float(gate["min_test_min_5d_pct"]),
        ),
        _check(
            "test_bad_path",
            test.get("bad_path_pct"),
            f"<={gate['max_test_bad_path_pct']}%",
            _num_metric(test, "bad_path_pct", 100.0) <= float(gate["max_test_bad_path_pct"]),
        ),
        _check(
            "test_stop5",
            test.get("stop5_pct"),
            f"<={gate['max_test_stop5_pct']}%",
            _num_metric(test, "stop5_pct", 100.0) <= float(gate["max_test_stop5_pct"]),
        ),
        _check(
            "test_early_drop_1d",
            test.get("early_drop_1d_pct"),
            f"<={gate['max_test_early_drop_1d_pct']}%",
            _num_metric(test, "early_drop_1d_pct", 100.0) <= float(gate["max_test_early_drop_1d_pct"]),
        ),
    ]


def _status_from_checks(checks: Sequence[Mapping[str, Any]], train: Mapping[str, Any], test: Mapping[str, Any]) -> str:
    if all(check.get("passed") for check in checks):
        return "promotion_review_candidate"
    if int(test.get("n") or 0) < PROMOTION_GATE["min_test_n"] or int(test.get("active_days") or 0) < PROMOTION_GATE["min_test_days"]:
        return "watch_insufficient_forward_sample"
    if _num_metric(test, "effective_win_5d_pct", 0.0) >= PROMOTION_GATE["min_test_effective_win_5d_pct"]:
        return "near_73_failed_risk_or_return_gate"
    if _num_metric(test, "effective_win_5d_pct", 0.0) >= 68.0:
        return "watch_near_73"
    return "reference_or_rejected"


def _score_row(row: Mapping[str, Any]) -> Tuple[int, int, float, float, float, float, float, int]:
    test = row.get("test") or {}
    status_rank = 3 if row.get("status") == "promotion_review_candidate" else 2 if row.get("status") == "near_73_failed_risk_or_return_gate" else 1
    sample_rank = 1 if int(test.get("n") or 0) >= PROMOTION_GATE["min_test_n"] and int(test.get("active_days") or 0) >= PROMOTION_GATE["min_test_days"] else 0
    return (
        status_rank,
        sample_rank,
        _num_metric(test, "effective_win_5d_pct", 0.0),
        _num_metric(test, "avg_5d_pct", -999.0),
        -_num_metric(test, "bad_path_pct", 100.0),
        -_num_metric(test, "stop5_pct", 100.0),
        _num_metric(test, "wilson_lower_effective_win_5d_pct", 0.0),
        int(test.get("n") or 0),
    )


def _candidate_payload(
    *,
    candidate_id: str,
    candidate_type: str,
    source: str,
    market: str,
    description: str,
    cut_day: str | None,
    all_metrics: Dict[str, Any],
    train_metrics: Dict[str, Any],
    test_metrics: Dict[str, Any],
    conditions: Sequence[str],
    notes: Sequence[str] = (),
) -> Dict[str, Any]:
    checks = _gate_checks(train_metrics, test_metrics)
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "source": source,
        "market": str(market).upper(),
        "description": description,
        "cut_day": cut_day,
        "conditions": list(conditions),
        "all": all_metrics,
        "train": train_metrics,
        "test": test_metrics,
        "gate_checks": checks,
        "status": _status_from_checks(checks, train_metrics, test_metrics),
        "notes": list(notes),
    }


def _close_candidate_specs() -> List[CloseCandidateSpec]:
    def market_scope(market: str, key: str) -> Callable[[pd.DataFrame], pd.Series]:
        def _mask(df: pd.DataFrame) -> pd.Series:
            market_df = df.loc[df["market2"].eq(market)]
            masks = _cohort_masks(market_df)
            base = pd.Series(False, index=df.index)
            base.loc[market_df.index] = masks[key].reindex(market_df.index).fillna(False)
            return base

        return _mask

    def practical_gate(market: str) -> Callable[[pd.DataFrame], pd.Series]:
        def _mask(df: pd.DataFrame) -> pd.Series:
            return df["market2"].eq(market) & df["practical_gate_level"].isin(["pass", "near", "small_sample"])

        return _mask

    def kospi_exact(refined: bool) -> Callable[[pd.DataFrame], pd.Series]:
        def _mask(df: pd.DataFrame) -> pd.Series:
            market_df = df.loc[df["market2"].eq("KOSPI")]
            masks = _cohort_masks(market_df)
            out = pd.Series(False, index=df.index)
            selected = (
                masks["top5_exception"].reindex(market_df.index).fillna(False)
                & _bool_series(_series(market_df, "ordered_path_exact", False))
                & _numeric(market_df, "alpha_score").le(67.0).fillna(False)
                & _numeric(market_df, "ml_prob").le(30.45).fillna(False)
            )
            if refined:
                selected &= _numeric(market_df, "decision_score").ge(60.5).fillna(False)
            out.loc[market_df.index] = selected
            return out

        return _mask

    return [
        CloseCandidateSpec("current_kospi_top5", "KOSPI", "current_operating", "archive", "현재 KOSPI Top5 원본 후보", market_scope("KOSPI", "top5"), ("priority_rank 1-5 excluding exception_leader",)),
        CloseCandidateSpec("current_kospi_exception_leader", "KOSPI", "current_operating", "archive", "현재 KOSPI Exception Leader", market_scope("KOSPI", "exception_leader"), ("exception_leader",)),
        CloseCandidateSpec("current_kospi_top5_exception", "KOSPI", "current_operating", "archive", "현재 KOSPI Top5 + Exception", market_scope("KOSPI", "top5_exception"), ("priority_rank 1-5 OR exception_leader",)),
        CloseCandidateSpec("current_kospi_practical_80_gate", "KOSPI", "current_operating", "archive", "현재 KOSPI Practical 80 Gate 표시 계약", practical_gate("KOSPI"), ("practical_entry_gate level in pass/near/small_sample",)),
        CloseCandidateSpec("kospi_exact_path_low_alpha_low_ml_top5_exception", "KOSPI", "pinned_challenger", "feature_combo_watchlist", "KOSPI exact-path low-alpha/low-ML Top5+Exception 후보", kospi_exact(False), ("ordered_path_exact", "top5_exception", "alpha_score <= 67", "ml_prob <= 30.45")),
        CloseCandidateSpec("kospi_exact_path_low_alpha_low_ml_decision_refined", "KOSPI", "pinned_challenger_refinement", "feature_combo_watchlist", "KOSPI exact-path 후보의 decision_score refinement", kospi_exact(True), ("ordered_path_exact", "top5_exception", "alpha_score <= 67", "ml_prob <= 30.45", "decision_score >= 60.5")),
        CloseCandidateSpec("current_kosdaq_top5", "KOSDAQ", "current_operating", "archive", "현재 KOSDAQ Top5 원본 후보", market_scope("KOSDAQ", "top5"), ("priority_rank 1-5 excluding exception_leader",)),
        CloseCandidateSpec("current_kosdaq_exception_leader", "KOSDAQ", "current_operating", "archive", "현재 KOSDAQ Exception Leader", market_scope("KOSDAQ", "exception_leader"), ("exception_leader",)),
        CloseCandidateSpec("current_kosdaq_top5_exception", "KOSDAQ", "current_operating", "archive", "현재 KOSDAQ Top5 + Exception", market_scope("KOSDAQ", "top5_exception"), ("priority_rank 1-5 OR exception_leader",)),
        CloseCandidateSpec("current_kosdaq_practical_80_gate", "KOSDAQ", "current_operating", "archive", "현재 KOSDAQ Practical 80 Gate 표시 계약", practical_gate("KOSDAQ"), ("practical_entry_gate level in pass/near/small_sample",)),
    ]


def evaluate_close_candidates(df: pd.DataFrame, *, train_ratio: float = 0.65, specs: Optional[Sequence[CloseCandidateSpec]] = None) -> List[Dict[str, Any]]:
    prepared = _prepare_frame(df)
    rows: List[Dict[str, Any]] = []
    for spec in specs or _close_candidate_specs():
        selected = spec.mask_fn(prepared)
        cut_day, all_m, train_m, test_m = _split_eval(prepared.loc[prepared["market2"].eq(spec.market)].copy(), selected, train_ratio=train_ratio)
        rows.append(
            _candidate_payload(
                candidate_id=spec.candidate_id,
                candidate_type=spec.candidate_type,
                source=spec.source,
                market=spec.market,
                description=spec.description,
                cut_day=cut_day,
                all_metrics=all_m,
                train_metrics=train_m,
                test_metrics=test_m,
                conditions=spec.conditions,
            )
        )
    return rows


def _ordered_metric_frame_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    ready = _bool_series(_series(df, "ordered_label_ready", False))
    sub = df.loc[ready].copy()
    if sub.empty:
        return _close_metrics(sub)
    base = _close_metrics(sub)
    ordered_win = _bool_series(_series(sub, "ordered_win", False))
    ordered_stop = _bool_series(_series(sub, "ordered_stop", False))
    successes = int(ordered_win.sum())
    n = int(len(sub))
    base.update(
        {
            "n": n,
            "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
            "effective_win_5d_pct": _pct(ordered_win.mean()),
            "ordered_win_5d_pct": _pct(ordered_win.mean()),
            "calibrated_effective_win_5d_pct": _posterior_pct(successes, n),
            "wilson_lower_effective_win_5d_pct": _wilson_lower_pct(successes, n),
            "stop5_pct": _pct(ordered_stop.mean()),
        }
    )
    return base


def evaluate_ordered_watch_candidates(
    *,
    markets: Sequence[str] = ("KOSPI", "KOSDAQ"),
    train_ratio: float = 0.58,
    rule_ids: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    wanted = {str(item) for item in rule_ids or []}
    rows: List[Dict[str, Any]] = []
    for market in markets:
        cache_path = _ordered_cache_path(market)
        if not cache_path.exists():
            continue
        labeled = pd.read_csv(cache_path, low_memory=False)
        labeled = add_search_columns(labeled)
        if "trade_date" not in labeled.columns:
            continue
        full_train_mask, full_test_mask, full_cut_day = _split_days(labeled, train_ratio)
        for rule in _ordered_watch_rules_for_market(market):
            rule_id = str(rule.get("rule_id") or "")
            if wanted and rule_id not in wanted:
                continue
            selected = _ordered_rule_mask(labeled, rule)
            scoped = labeled.loc[selected.fillna(False)].copy()
            if scoped.empty:
                cut_day = None
                all_m = train_m = test_m = _ordered_metric_frame_metrics(scoped)
            else:
                cut_day = full_cut_day
                all_m = _ordered_metric_frame_metrics(scoped)
                train_m = _ordered_metric_frame_metrics(labeled.loc[selected.fillna(False) & full_train_mask.fillna(False)])
                test_m = _ordered_metric_frame_metrics(labeled.loc[selected.fillna(False) & full_test_mask.fillna(False)])
            rows.append(
                _candidate_payload(
                    candidate_id=rule_id,
                    candidate_type="ordered_shadow_watch",
                    source=_display_path(cache_path),
                    market=market,
                    description=str(rule.get("note") or "Ordered target-before-stop watch rule"),
                    cut_day=cut_day,
                    all_metrics=all_m,
                    train_metrics=train_m,
                    test_metrics=test_m,
                    conditions=[str(item) for item in rule.get("conditions") or []],
                    notes=["ordered_win is used as effective 5D win because the profile is target-before-stop."],
                )
            )
    return rows


def _combo_effective_metrics(raw: Mapping[str, Any], horizon: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "n": int(raw.get("n_5d") or raw.get("n") or 0),
        "active_days": int(raw.get("active_days_5d") or raw.get("active_days") or 0),
        "selected_horizon": horizon,
        "selected_horizon_win_pct": _round(raw.get(f"win_{horizon}_pct")),
        "effective_win_5d_pct": _round(raw.get("win_5d_pct")),
        "calibrated_effective_win_5d_pct": None,
        "wilson_lower_effective_win_5d_pct": None,
        "bad_path_pct": _round(raw.get("bad_path_5d_pct", raw.get("bad_path_pct"))),
        "stop5_pct": _round(raw.get("stop5_5d_pct", raw.get("stop5_pct"))),
    }
    for key in ["win_1d_pct", "avg_1d_pct", "min_1d_pct", "max_1d_pct", "win_3d_pct", "avg_3d_pct", "min_3d_pct", "max_3d_pct", "win_5d_pct", "avg_5d_pct", "min_5d_pct", "max_5d_pct"]:
        out[key] = _round(raw.get(key))
    if horizon == "3d":
        out.setdefault("win_3d_pct", _round(raw.get("win_3d_pct")))
    successes_pct = _safe_float(out.get("effective_win_5d_pct"))
    n = int(out.get("n") or 0)
    if successes_pct is not None and n > 0:
        successes = int(round(n * successes_pct / 100.0))
        out["calibrated_effective_win_5d_pct"] = _posterior_pct(successes, n)
        out["wilson_lower_effective_win_5d_pct"] = _wilson_lower_pct(successes, n)
    if out.get("early_drop_1d_pct") is None:
        out["early_drop_1d_pct"] = None
    return out


def _combo_paths(paths: Optional[Sequence[str]]) -> List[Path]:
    if paths:
        raw = [Path(path) for path in paths]
    else:
        raw = [Path(path) for path in glob.glob(DEFAULT_DYNAMIC_COMBO_GLOB)]
    return [path for path in raw if path.exists() and path.name.startswith("significant_feature_combinations")]


def _model_sweep_paths(paths: Optional[Sequence[str]]) -> List[Path]:
    if paths:
        raw = [Path(path) for path in paths]
    else:
        raw = [Path(path) for path in glob.glob(DEFAULT_MODEL_SWEEP_GLOB)]
    return [path for path in raw if path.exists() and path.name.startswith("internal_retrain_sweep") and path.suffix == ".json"]


def evaluate_dynamic_combo_candidates(paths: Optional[Sequence[str]] = None, *, per_file_limit: int = 25) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str, Tuple[str, ...]]] = set()
    for path in _combo_paths(paths):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in (payload.get("production_safe_combinations") or []) + (payload.get("top_combinations") or [])[:per_file_limit]:
            horizon = str(item.get("horizon") or "5d").lower()
            if horizon not in {"3d", "5d"}:
                continue
            conditions = tuple(str(cond) for cond in item.get("conditions") or [])
            key = (str(item.get("market")), str(item.get("scope")), horizon, conditions)
            if key in seen:
                continue
            seen.add(key)
            train = _combo_effective_metrics(item.get("train") or {}, horizon)
            test = _combo_effective_metrics(item.get("test") or {}, horizon)
            all_m = test
            rows.append(
                _candidate_payload(
                    candidate_id=f"dynamic_combo::{path.stem}::{item.get('market')}::{item.get('scope')}::{horizon}::{item.get('combo_id')}",
                    candidate_type="dynamic_feature_combo",
                    source=_display_path(path),
                    market=str(item.get("market") or ""),
                    description="최근 significant feature-combination miner 후보",
                    cut_day=item.get("cut_day"),
                    all_metrics=all_m,
                    train_metrics=train,
                    test_metrics=test,
                    conditions=conditions,
                    notes=["precomputed miner metrics; effective win follows the candidate horizon close-return win."],
                )
            )
    rows.sort(key=_score_row, reverse=True)
    return rows


def evaluate_model_sweep_candidates(paths: Optional[Sequence[str]] = None, *, limit: int = 80) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str, str, int]] = set()
    for path in _model_sweep_paths(paths):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in (payload.get("champions") or [])[:limit]:
            market = str(item.get("market") or "").upper()
            if market not in {"KOSPI", "KOSDAQ"}:
                continue
            key = (
                market,
                str(item.get("cohort") or ""),
                str(item.get("label") or ""),
                str(item.get("model") or ""),
                int(item.get("best_topn") or 0),
            )
            if key in seen:
                continue
            seen.add(key)
            train = _combo_effective_metrics(item.get("train") or {}, "5d")
            test = _combo_effective_metrics(item.get("test") or {}, "5d")
            rows.append(
                _candidate_payload(
                    candidate_id=(
                        f"model_sweep::{path.stem}::{market}::{item.get('cohort')}::"
                        f"{item.get('label')}::{item.get('feature_set')}::{item.get('model')}::top{item.get('best_topn')}"
                    ),
                    candidate_type="ml_model_sweep",
                    source=_display_path(path),
                    market=market,
                    description="내부 재학습 스윕 후보의 daily topN 검증 결과",
                    cut_day=item.get("cut_day"),
                    all_metrics=test,
                    train_metrics=train,
                    test_metrics=test,
                    conditions=[
                        f"cohort={item.get('cohort')}",
                        f"label={item.get('label')}",
                        f"feature_set={item.get('feature_set')}",
                        f"model={item.get('model')}",
                        f"best_topn={item.get('best_topn')}",
                        f"auc={item.get('auc')}",
                    ],
                    notes=["precomputed chronological model-sweep metrics; no model artifact is promoted by this report."],
                )
            )
    rows.sort(key=_score_row, reverse=True)
    return rows


def _candidate_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    promotion = [row for row in rows if row.get("status") == "promotion_review_candidate"]
    near = [row for row in rows if row.get("status") in {"near_73_failed_risk_or_return_gate", "watch_near_73", "watch_insufficient_forward_sample"}]
    by_market: Dict[str, Dict[str, Any]] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        market_rows = [row for row in rows if str(row.get("market")).upper() == market]
        by_market[market] = {
            "candidate_count": len(market_rows),
            "promotion_review_candidate_count": sum(1 for row in market_rows if row.get("status") == "promotion_review_candidate"),
            "best_candidate_id": (market_rows[0].get("candidate_id") if market_rows else None),
            "best_status": (market_rows[0].get("status") if market_rows else None),
            "best_test_effective_win_5d_pct": ((market_rows[0].get("test") or {}).get("effective_win_5d_pct") if market_rows else None),
            "best_test_avg_5d_pct": ((market_rows[0].get("test") or {}).get("avg_5d_pct") if market_rows else None),
            "best_test_bad_path_pct": ((market_rows[0].get("test") or {}).get("bad_path_pct") if market_rows else None),
        }
    return {
        "total_candidate_count": len(rows),
        "promotion_review_candidate_count": len(promotion),
        "near_candidate_count": len(near),
        "best_candidate_id": rows[0].get("candidate_id") if rows else None,
        "best_status": rows[0].get("status") if rows else None,
        "by_market": by_market,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_report(
    input_path: Path = DEFAULT_INPUT,
    *,
    output_path: Path = DEFAULT_OUTPUT,
    train_ratio: float = 0.65,
    include_dynamic_combos: bool = True,
    dynamic_combo_paths: Optional[Sequence[str]] = None,
    include_model_sweeps: bool = True,
    model_sweep_paths: Optional[Sequence[str]] = None,
    ordered_rule_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    df = _load_dataset(input_path)
    close_rows = evaluate_close_candidates(df, train_ratio=train_ratio)
    ordered_rows = evaluate_ordered_watch_candidates(rule_ids=ordered_rule_ids)
    combo_rows = evaluate_dynamic_combo_candidates(dynamic_combo_paths) if include_dynamic_combos else []
    model_rows = evaluate_model_sweep_candidates(model_sweep_paths) if include_model_sweeps else []
    candidates = close_rows + ordered_rows + combo_rows + model_rows
    candidates.sort(key=_score_row, reverse=True)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "production_scanner_changed": False,
        "promotion_gate": PROMOTION_GATE,
        "summary": _candidate_summary(candidates),
        "candidates": candidates,
        "notes": [
            "This is a promotion-review testbed only. It does not alter scanner/model/runtime behavior.",
            "Current Top5, Exception Leader, Practical 80, KOSPI exact-path, ordered shadow rules, and mined dynamic combos are compared under one gate.",
            "If internal retrain sweep artifacts exist, model-sweep candidates are included as challengers but never auto-promoted.",
            "effective_win_5d_pct is practical close-return win for archive cohorts and ordered target-before-stop win for ordered profiles.",
            "promotion_review_candidate means report-to-operator before any code promotion, not automatic deployment.",
            "Primary theme identities are not required for promotion; dynamic theme context is allowed only when backed by same-day theme profile metrics.",
        ],
    }


def _fmt_metric(row: Mapping[str, Any]) -> str:
    if not row or not row.get("n"):
        return "n=0"
    return (
        f"n={row.get('n')} days={row.get('active_days')} "
        f"eff5={row.get('effective_win_5d_pct')}% cal={row.get('calibrated_effective_win_5d_pct')}% "
        f"w3={row.get('win_3d_pct')}% avg5={row.get('avg_5d_pct')}% "
        f"min5={row.get('min_5d_pct')}% max5={row.get('max_5d_pct')}% "
        f"bad={row.get('bad_path_pct')}% stop={row.get('stop5_pct')}% drop1={row.get('early_drop_1d_pct')}%"
    )


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# KR Promotion Challenger Gate",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        "- production_scanner_changed: `False`",
        f"- total_candidate_count: `{(report.get('summary') or {}).get('total_candidate_count')}`",
        f"- promotion_review_candidate_count: `{(report.get('summary') or {}).get('promotion_review_candidate_count')}`",
        "",
        "## Promotion Gate",
        "",
    ]
    for key, value in (report.get("promotion_gate") or {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Ranked Candidates",
            "",
            "| Rank | Market | Candidate | Type | Status | Test | Train | Conditions |",
            "|---:|---|---|---|---|---:|---:|---|",
        ]
    )
    for idx, row in enumerate(report.get("candidates") or [], start=1):
        conditions = "<br>".join(str(item) for item in row.get("conditions") or [])
        lines.append(
            "| "
            f"{idx} | {row.get('market')} | {row.get('candidate_id')} | {row.get('candidate_type')} | "
            f"{row.get('status')} | {_fmt_metric(row.get('test') or {})} | "
            f"{_fmt_metric(row.get('train') or {})} | {conditions} |"
        )
    lines.extend(["", "## Gate Failures For Top Candidates", ""])
    for row in (report.get("candidates") or [])[:20]:
        failed = [check for check in row.get("gate_checks") or [] if not check.get("passed")]
        lines.append(f"### {row.get('candidate_id')}")
        if not failed:
            lines.append("- all checks passed")
        for check in failed:
            lines.append(f"- {check.get('name')}: actual `{check.get('actual')}` expected `{check.get('expected')}`")
        lines.append("")
    lines.extend(["## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare KR scanner promotion challengers under one gate.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-ratio", type=float, default=0.65)
    parser.add_argument("--no-dynamic-combos", action="store_true")
    parser.add_argument("--no-model-sweeps", action="store_true")
    parser.add_argument("--combo-report", action="append", default=None)
    parser.add_argument("--model-sweep-report", action="append", default=None)
    parser.add_argument("--ordered-rule-id", action="append", default=None)
    args = parser.parse_args()

    report = build_report(
        args.input,
        output_path=args.output,
        train_ratio=float(args.train_ratio),
        include_dynamic_combos=not bool(args.no_dynamic_combos),
        dynamic_combo_paths=args.combo_report,
        include_model_sweeps=not bool(args.no_model_sweeps),
        model_sweep_paths=args.model_sweep_report,
        ordered_rule_ids=args.ordered_rule_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    md_path = args.output.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(args.output),
                "md": str(md_path),
                "summary": report.get("summary"),
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
