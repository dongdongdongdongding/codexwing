#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate
from modules.tradable_pnl import TradableCostModel, compute_net_return_pct
from multi_agent.tools.train_kis_historical_best_effort_suite import (
    BUY_PREMIUM_PCT,
    DEFAULT_END,
    DEFAULT_START,
    REPORT_VERSION as BEST_EFFORT_REPORT_VERSION,
    STOP_PCT,
    TARGET_PCT,
    Window,
    _filter_valid_labels,
    _load_market_frame,
    _metric_summary,
    _quality_score,
    _round,
    _utc_now,
    _walk_windows,
)


REPORT_VERSION = "kis_tail_safe_policy_search_v1"
DEFAULT_REPORT_STEM = "kis_tail_safe_policy_search_20260101_20260610"


@dataclass(frozen=True)
class PolicyRule:
    r5_min: float
    r5_max: float
    close_location_min: float
    volume_ratio_min: float
    ticker_risk_max: float
    theme_stop_max: float
    ticker_avg_mae_min: float
    pct_from_52w_high_min: float

    def name(self) -> str:
        return (
            f"r5[{self.r5_min:g},{self.r5_max:g}]"
            f"|loc>={self.close_location_min:g}"
            f"|vol>={self.volume_ratio_min:g}"
            f"|tickerRisk<={self.ticker_risk_max:g}"
            f"|themeStop<={self.theme_stop_max:g}"
            f"|tickerMae>={self.ticker_avg_mae_min:g}"
            f"|from52w>={self.pct_from_52w_high_min:g}"
        )


@dataclass(frozen=True)
class ScoreSpec:
    name: str
    weights: Mapping[str, float]
    center_target: str | None = None
    center_value: float = 0.0
    center_weight: float = 0.0


SCORE_SPECS: Dict[str, ScoreSpec] = {
    "risk_adjusted_momentum": ScoreSpec(
        name="risk_adjusted_momentum",
        weights={
            "_r5": 0.70,
            "_volume_ratio": 0.38,
            "_close_location": 0.28,
            "_whale": 0.16,
            "_pct_from_52w_high": 0.24,
            "_news_evidence": 0.12,
            "_ticker_risk": -0.66,
            "_theme_stop": -0.46,
            "_theme_risk": -0.28,
            "_news_risk": -0.20,
        },
    ),
    "volume_leadership_defense": ScoreSpec(
        name="volume_leadership_defense",
        weights={
            "_volume_ratio": 0.75,
            "_rank_volume_power_inverse": 0.35,
            "_whale": 0.22,
            "_close_location": 0.25,
            "_ticker_risk": -0.55,
            "_theme_stop": -0.38,
            "_ticker_avg_mae": 0.24,
        },
    ),
    "moderated_momentum": ScoreSpec(
        name="moderated_momentum",
        weights={
            "_volume_ratio": 0.42,
            "_close_location": 0.32,
            "_pct_from_52w_high": 0.18,
            "_ticker_risk": -0.70,
            "_theme_stop": -0.42,
            "_theme_risk": -0.28,
        },
        center_target="_r5",
        center_value=3.0,
        center_weight=0.72,
    ),
}


def _pct(value: Any) -> float | None:
    rounded = _round(value, 6)
    return None if rounded is None else round(rounded * 100.0, 4)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").astype(float)


def _first_numeric(frame: pd.DataFrame, columns: Sequence[str], default: float = 0.0) -> pd.Series:
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    for column in columns:
        if column not in frame.columns:
            continue
        out = out.combine_first(pd.to_numeric(frame[column], errors="coerce"))
    return out.fillna(default).astype(float)


def _prepare_policy_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_r5"] = _first_numeric(out, ["kis_daily_return_5d_pct", "day_return_pct"], 0.0)
    out["_volume_ratio"] = _first_numeric(out, ["kis_daily_volume_ratio_20d", "volume_ratio", "kis_prev_volume_ratio"], 0.0)
    out["_close_location"] = _first_numeric(out, ["kis_daily_close_location_pct"], 50.0)
    out["_whale"] = _first_numeric(out, ["kis_whale_score", "kis_prefilter_flow_whale_score"], 0.0)
    out["_pct_from_52w_high"] = _first_numeric(out, ["kis_daily_pct_from_52w_high"], -100.0)
    out["_ticker_risk"] = _first_numeric(out, ["close_failure_prior_ticker_risk_score"], 50.0)
    out["_theme_stop"] = _first_numeric(
        out,
        ["close_failure_prior_kis_theme_stop5_rate_pct", "close_failure_prior_theme_stop5_rate_pct"],
        50.0,
    )
    out["_theme_risk"] = _first_numeric(
        out,
        ["close_failure_prior_kis_theme_risk_score", "close_failure_prior_theme_risk_score"],
        50.0,
    )
    out["_ticker_avg_mae"] = _first_numeric(out, ["close_failure_prior_ticker_avg_mae_5d_pct"], -100.0)
    out["_news_evidence"] = _first_numeric(out, ["kis_theme_news_evidence_score"], 0.0)
    out["_news_risk"] = _first_numeric(out, ["kis_theme_news_risk_tag_count"], 0.0)
    rank_power = _first_numeric(out, ["kis_rank_volume_power", "kis_prefilter_rank_volume_power"], 9999.0)
    out["_rank_volume_power_inverse"] = -rank_power
    return out


def _robust_stats(frame: pd.DataFrame, columns: Iterable[str]) -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {}
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce").dropna() if column in frame.columns else pd.Series(dtype=float)
        if values.empty:
            stats[column] = {"lo": 0.0, "hi": 1.0, "median": 0.0}
            continue
        lo = float(values.quantile(0.05))
        hi = float(values.quantile(0.95))
        if not math.isfinite(lo):
            lo = float(values.min())
        if not math.isfinite(hi):
            hi = float(values.max())
        if hi == lo:
            hi = lo + 1.0
        stats[column] = {"lo": lo, "hi": hi, "median": float(values.median())}
    return stats


def _normalized(frame: pd.DataFrame, column: str, stats: Mapping[str, Mapping[str, float]]) -> pd.Series:
    value = pd.to_numeric(frame[column], errors="coerce") if column in frame.columns else pd.Series(0.0, index=frame.index)
    stat = stats.get(column, {})
    lo = _safe_float(stat.get("lo"), 0.0)
    hi = _safe_float(stat.get("hi"), lo + 1.0)
    median = _safe_float(stat.get("median"), 0.0)
    denom = hi - lo if hi != lo else 1.0
    return ((value.fillna(median).clip(lo, hi) - lo) / denom).astype(float)


def _score(frame: pd.DataFrame, spec: ScoreSpec, stats: Mapping[str, Mapping[str, float]]) -> pd.Series:
    result = pd.Series(0.0, index=frame.index, dtype=float)
    for column, weight in spec.weights.items():
        result = result + _normalized(frame, column, stats) * float(weight)
    if spec.center_target:
        value = pd.to_numeric(frame[spec.center_target], errors="coerce") if spec.center_target in frame.columns else pd.Series(spec.center_value, index=frame.index)
        stat = stats.get(spec.center_target, {"lo": spec.center_value - 1.0, "hi": spec.center_value + 1.0})
        lo = _safe_float(stat.get("lo"), spec.center_value - 1.0)
        hi = _safe_float(stat.get("hi"), spec.center_value + 1.0)
        denom = hi - lo if hi != lo else 1.0
        distance = (value.fillna(spec.center_value) - spec.center_value).abs().clip(upper=denom) / denom
        result = result - distance.astype(float) * float(spec.center_weight)
    return result


def _rule_mask(frame: pd.DataFrame, rule: PolicyRule) -> pd.Series:
    return (
        frame["_r5"].between(rule.r5_min, rule.r5_max, inclusive="both")
        & frame["_close_location"].ge(rule.close_location_min)
        & frame["_volume_ratio"].ge(rule.volume_ratio_min)
        & frame["_ticker_risk"].le(rule.ticker_risk_max)
        & frame["_theme_stop"].le(rule.theme_stop_max)
        & frame["_ticker_avg_mae"].ge(rule.ticker_avg_mae_min)
        & frame["_pct_from_52w_high"].ge(rule.pct_from_52w_high_min)
    ).fillna(False)


def _selected_indices(frame: pd.DataFrame, score: pd.Series, rule: PolicyRule, *, topn: int) -> pd.Index:
    mask = _rule_mask(frame, rule)
    if not bool(mask.any()):
        return pd.Index([])
    scored = frame.loc[mask, ["base_trade_date", "ticker"]].copy()
    scored["_score"] = pd.to_numeric(score.reindex(scored.index), errors="coerce")
    scored = scored.dropna(subset=["_score"])
    if scored.empty:
        return pd.Index([])
    ordered = scored.sort_values(["base_trade_date", "_score", "ticker"], ascending=[True, False, True])
    selected = ordered.groupby("base_trade_date", sort=False).head(int(topn))
    return selected.index


def _rank_context(frame: pd.DataFrame, score: pd.Series) -> Dict[str, Any]:
    score_values = pd.to_numeric(score.reindex(frame.index), errors="coerce").to_numpy(dtype=float)
    ranked = pd.DataFrame(
        {
            "_pos": np.arange(len(frame), dtype=np.int64),
            "_index": frame.index.to_numpy(),
            "_day": frame["base_trade_date"].astype(str).to_numpy(),
            "_ticker": frame.get("ticker", pd.Series("", index=frame.index)).astype(str).to_numpy(),
            "_score": score_values,
        }
    )
    ranked = ranked[np.isfinite(ranked["_score"].to_numpy(dtype=float))]
    ranked = ranked.sort_values(["_day", "_score", "_ticker"], ascending=[True, False, True], kind="mergesort")
    ordered_pos = ranked["_pos"].to_numpy(dtype=np.int64)
    target_net = compute_net_return_pct(TARGET_PCT, TradableCostModel())
    arrays = {
        "_r5": frame["_r5"].to_numpy(dtype=float),
        "_close_location": frame["_close_location"].to_numpy(dtype=float),
        "_volume_ratio": frame["_volume_ratio"].to_numpy(dtype=float),
        "_ticker_risk": frame["_ticker_risk"].to_numpy(dtype=float),
        "_theme_stop": frame["_theme_stop"].to_numpy(dtype=float),
        "_ticker_avg_mae": frame["_ticker_avg_mae"].to_numpy(dtype=float),
        "_pct_from_52w_high": frame["_pct_from_52w_high"].to_numpy(dtype=float),
        "_success": frame["_label_success"].fillna(False).astype(bool).to_numpy(),
        "_target_hit": frame["_label_target_hit"].fillna(False).astype(bool).to_numpy(),
        "_target_before_stop": frame["_label_target_before_stop"].fillna(False).astype(bool).to_numpy(),
        "_stop_hit": frame["_label_stop_hit"].fillna(False).astype(bool).to_numpy(),
        "_stop_before": frame["_label_stop_before_target"].fillna(False).astype(bool).to_numpy(),
        "_hit10": frame["_label_hit10"].fillna(False).astype(bool).to_numpy(),
        "_close5": frame["_close_5d"].astype(float).to_numpy(),
        "_mfe5": frame["_mfe_5d"].astype(float).to_numpy(),
        "_mae5": frame["_mae_5d"].astype(float).to_numpy(),
        "_day": frame["base_trade_date"].astype(str).to_numpy(),
        "_run": frame["run_id"].astype(str).to_numpy() if "run_id" in frame.columns else frame["base_trade_date"].astype(str).to_numpy(),
    }
    return {
        "frame_index": frame.index.to_numpy(),
        "ordered_pos": ordered_pos,
        "ordered_index": ranked["_index"].to_numpy(),
        "ordered_day": ranked["_day"].to_numpy(),
        "ordered_values": {name: values[ordered_pos] for name, values in arrays.items() if name.startswith("_") and name not in {"_day", "_run"}},
        "arrays": arrays,
        "target_net": target_net,
    }


def _selected_positions_from_context(context: Mapping[str, Any], rule: PolicyRule, *, topn: int) -> np.ndarray:
    values = context["ordered_values"]
    mask = (
        (values["_r5"] >= rule.r5_min)
        & (values["_r5"] <= rule.r5_max)
        & (values["_close_location"] >= rule.close_location_min)
        & (values["_volume_ratio"] >= rule.volume_ratio_min)
        & (values["_ticker_risk"] <= rule.ticker_risk_max)
        & (values["_theme_stop"] <= rule.theme_stop_max)
        & (values["_ticker_avg_mae"] >= rule.ticker_avg_mae_min)
        & (values["_pct_from_52w_high"] >= rule.pct_from_52w_high_min)
    )
    if not bool(mask.any()):
        return np.array([], dtype=np.int64)
    positions = context["ordered_pos"][mask]
    days = context["ordered_day"][mask]
    if not len(positions):
        return np.array([], dtype=np.int64)
    changes = np.empty(len(days), dtype=bool)
    changes[0] = True
    changes[1:] = days[1:] != days[:-1]
    starts = np.maximum.accumulate(np.where(changes, np.arange(len(days)), 0))
    ranks = np.arange(len(days)) - starts
    return positions[ranks < int(topn)]


def _fast_metric_summary(context: Mapping[str, Any], positions: np.ndarray) -> Dict[str, Any]:
    if positions.size == 0:
        return {"n": 0, "active_days": 0, "active_runs": 0}
    arrays = context["arrays"]
    success = arrays["_success"][positions]
    target_hit = arrays["_target_hit"][positions]
    target_before_stop = arrays["_target_before_stop"][positions]
    stop_hit = arrays["_stop_hit"][positions]
    stop_before = arrays["_stop_before"][positions]
    hit10 = arrays["_hit10"][positions]
    close5 = arrays["_close5"][positions].astype(float)
    mfe5 = arrays["_mfe5"][positions].astype(float)
    mae5 = arrays["_mae5"][positions].astype(float)
    exit_returns = close5.copy()
    target_net = context.get("target_net")
    if target_net is not None:
        exit_returns[success] = float(target_net)
    exit_returns[stop_before] = -abs(STOP_PCT)
    return {
        "n": int(positions.size),
        "active_days": int(pd.unique(arrays["_day"][positions]).size),
        "active_runs": int(pd.unique(arrays["_run"][positions]).size),
        "hit5_dd10_5d_pct": _pct(float(success.mean())),
        "target_before_stop_5d_pct": _pct(float(target_before_stop.mean())),
        "win_5d_pct": _pct(float(target_hit.mean())),
        "hit10_5d_pct": _pct(float(hit10.mean())),
        "stop5_pct": _pct(float(stop_hit.mean())),
        "stop_before_target_5d_pct": _pct(float(stop_before.mean())),
        "bad_path_pct": _pct(float((stop_before | (close5 < 0.0)).mean())),
        "avg_5d_pct": _round(float(close5.mean()), 6),
        "median_5d_pct": _round(float(np.median(close5)), 6),
        "min_5d_pct": _round(float(close5.min()), 6),
        "max_5d_pct": _round(float(close5.max()), 6),
        "avg_mfe_5d_pct": _round(float(mfe5.mean()), 6),
        "avg_mae_5d_pct": _round(float(mae5.mean()), 6),
        "min_min_low_5d_pct": _round(float(mae5.min()), 6),
        "max_mfe_5d_pct": _round(float(mfe5.max()), 6),
        "avg_ordered_exit_5d_pct": _round(float(exit_returns.mean()), 6),
        "min_ordered_exit_5d_pct": _round(float(exit_returns.min()), 6),
        "buy_premium_pct": BUY_PREMIUM_PCT,
    }


def _index_from_positions(context: Mapping[str, Any], positions: np.ndarray) -> pd.Index:
    if positions.size == 0:
        return pd.Index([])
    return pd.Index(context["frame_index"][positions])


def _rules_for_market(market: str, *, profile: str = "exhaustive") -> List[PolicyRule]:
    if market.upper() == "KOSDAQ":
        r5_ranges = [(-18.0, 0.0), (-10.0, 6.0), (-5.0, 12.0), (0.0, 20.0), (5.0, 45.0)]
    else:
        r5_ranges = [(-14.0, 0.0), (-8.0, 5.0), (-4.0, 10.0), (0.0, 16.0), (4.0, 35.0)]
    if profile == "fast":
        close_locs = [50.0, 70.0]
        volume_mins = [0.9, 1.5]
        ticker_risk_maxes = [30.0, 45.0, 999.0]
        theme_stop_maxes = [30.0, 999.0]
        ticker_mae_mins = [-5.5, -999.0]
        high_mins = [-45.0, -20.0]
    else:
        close_locs = [30.0, 50.0, 70.0]
        volume_mins = [0.0, 0.9, 1.5]
        ticker_risk_maxes = [30.0, 45.0, 999.0]
        theme_stop_maxes = [30.0, 45.0, 999.0]
        ticker_mae_mins = [-8.0, -5.5, -999.0]
        high_mins = [-45.0, -20.0]
    return [
        PolicyRule(
            r5_min=r5_min,
            r5_max=r5_max,
            close_location_min=loc,
            volume_ratio_min=volume_min,
            ticker_risk_max=ticker_risk,
            theme_stop_max=theme_stop,
            ticker_avg_mae_min=ticker_mae,
            pct_from_52w_high_min=high_min,
        )
        for r5_min, r5_max in r5_ranges
        for loc in close_locs
        for volume_min in volume_mins
        for ticker_risk in ticker_risk_maxes
        for theme_stop in theme_stop_maxes
        for ticker_mae in ticker_mae_mins
        for high_min in high_mins
    ]


def _policy_objective(metrics: Mapping[str, Any], gate: Mapping[str, Any]) -> float:
    hit = float(metrics.get("hit5_dd10_5d_pct") or 0.0)
    hit10 = float(metrics.get("hit10_5d_pct") or 0.0)
    avg_exit = float(metrics.get("avg_ordered_exit_5d_pct") or -20.0)
    avg_close = float(metrics.get("avg_5d_pct") or -20.0)
    stop = float(metrics.get("stop5_pct") or 100.0)
    bad = float(metrics.get("bad_path_pct") or 100.0)
    min_low = float(metrics.get("min_min_low_5d_pct") or -100.0)
    days = int(metrics.get("active_days") or 0)
    n = int(metrics.get("n") or 0)
    production_bonus = 600.0 if gate.get("production_ready") else 0.0
    shadow_bonus = 180.0 if gate.get("shadow_display_allowed") else 0.0
    hard_tail_penalty = max(0.0, -abs(STOP_PCT) - min_low) * 26.0
    return (
        production_bonus
        + shadow_bonus
        + hit * 4.0
        + hit10 * 0.65
        + avg_exit * 18.0
        + avg_close * 1.2
        - stop * 2.1
        - bad * 1.55
        - hard_tail_penalty
        + min(days, 45) * 0.55
        + min(n, 180) * 0.045
    )


def _gate_identity(*, market: str, score_name: str, topn: int, fold_count: int) -> Dict[str, Any]:
    return {
        "suite_version": REPORT_VERSION,
        "upstream_suite_version": BEST_EFFORT_REPORT_VERSION,
        "model": "kis_tail_safe_policy",
        "score_mode": score_name,
        "feature_set": "kis_tail_safe_filters",
        "market": market,
        "label": "touch5_dd10_5d",
        "topn": int(topn),
        "fold_count": int(fold_count),
        "buy_premium_pct": BUY_PREMIUM_PCT,
        "target_pct": TARGET_PCT,
        "stop_pct": STOP_PCT,
    }


def _choose_rule(
    *,
    market: str,
    train: pd.DataFrame,
    train_score: pd.Series,
    rules: Sequence[PolicyRule],
    topn: int,
    min_train_n: int,
    min_train_active_days: int,
) -> Dict[str, Any] | None:
    best: Dict[str, Any] | None = None
    context = _rank_context(train, train_score)
    for rule in rules:
        positions = _selected_positions_from_context(context, rule, topn=topn)
        metrics = _fast_metric_summary(context, positions)
        if int(metrics.get("n") or 0) < min_train_n:
            continue
        if int(metrics.get("active_days") or 0) < min_train_active_days:
            continue
        identity = _gate_identity(market=market, score_name="train_rule_search", topn=topn, fold_count=0)
        gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
        objective = _policy_objective(metrics, gate)
        if best is None or objective > float(best["objective"]):
            best = {
                "rule": asdict(rule),
                "rule_name": rule.name(),
                "metrics": metrics,
                "gate": gate,
                "objective": _round(objective, 6),
            }
    return best


def _aggregate_selected_indices(indices: Sequence[pd.Index]) -> pd.Index:
    nonempty = [idx for idx in indices if len(idx)]
    if not nonempty:
        return pd.Index([])
    out = nonempty[0]
    for idx in nonempty[1:]:
        out = out.append(idx)
    return out.drop_duplicates()


def evaluate_adaptive_policy(
    *,
    market: str,
    frame: pd.DataFrame,
    windows: Sequence[Window],
    topn_values: Sequence[int],
    score_names: Sequence[str],
    min_train_n: int,
    min_train_active_days: int,
    grid_profile: str = "exhaustive",
) -> List[Dict[str, Any]]:
    rules = _rules_for_market(market, profile=grid_profile)
    rows: List[Dict[str, Any]] = []
    score_columns = sorted({column for name in score_names for column in SCORE_SPECS[name].weights.keys()} | {"_r5"})
    for score_name in score_names:
        spec = SCORE_SPECS[score_name]
        for topn in topn_values:
            selected_by_fold: List[pd.Index] = []
            fold_rows: List[Dict[str, Any]] = []
            for window in windows:
                train = frame[frame["base_trade_date"].isin(window.train_days)].copy()
                test = frame[frame["base_trade_date"].isin(window.test_days)].copy()
                if train.empty or test.empty:
                    continue
                stats = _robust_stats(train, score_columns)
                train_score = _score(train, spec, stats)
                test_score = _score(test, spec, stats)
                chosen = _choose_rule(
                    market=market,
                    train=train,
                    train_score=train_score,
                    rules=rules,
                    topn=int(topn),
                    min_train_n=min_train_n,
                    min_train_active_days=min_train_active_days,
                )
                if chosen is None:
                    fold_rows.append(
                        {
                            "fold": int(window.fold),
                            "train_days": len(window.train_days),
                            "test_days": len(window.test_days),
                            "embargo_days": len(window.embargo_days),
                            "test_start": window.test_days[0] if window.test_days else None,
                            "test_end": window.test_days[-1] if window.test_days else None,
                            "selected_rule": None,
                            "reason": "no_rule_met_train_sample_floor",
                        }
                    )
                    continue
                rule = PolicyRule(**chosen["rule"])
                test_context = _rank_context(test, test_score)
                positions = _selected_positions_from_context(test_context, rule, topn=int(topn))
                idx = _index_from_positions(test_context, positions)
                test_metrics = _fast_metric_summary(test_context, positions)
                selected_by_fold.append(idx)
                fold_rows.append(
                    {
                        "fold": int(window.fold),
                        "train_days": len(window.train_days),
                        "test_days": len(window.test_days),
                        "embargo_days": len(window.embargo_days),
                        "test_start": window.test_days[0] if window.test_days else None,
                        "test_end": window.test_days[-1] if window.test_days else None,
                        "selected_rule": chosen,
                        "test_metrics": test_metrics,
                    }
                )
            idx = _aggregate_selected_indices(selected_by_fold)
            metrics = _metric_summary(frame, idx)
            identity = _gate_identity(market=market, score_name=score_name, topn=int(topn), fold_count=len(fold_rows))
            gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
            rows.append(
                {
                    "identity": identity,
                    "metrics": metrics,
                    "gate": gate,
                    "quality_score": _round(_quality_score(metrics, gate), 6),
                    "policy_objective": _round(_policy_objective(metrics, gate), 6),
                    "folds": fold_rows,
                    "latest_recommended_rule": next(
                        (
                            fold.get("selected_rule")
                            for fold in reversed(fold_rows)
                            if isinstance(fold.get("selected_rule"), Mapping)
                        ),
                        None,
                    ),
                }
            )
    return rows


def _market_cache_path(market: str, start: str, end: str, override: str | None = None) -> Path:
    if override:
        return Path(override)
    compact_start = start.replace("-", "")
    compact_end = end.replace("-", "")
    return PROJECT_ROOT / f"runtime_state/reports/learning/kis_historical_universe_prepared_{market.lower()}_{compact_start}_{compact_end}.pkl"


def _market_report(
    *,
    market: str,
    cache_path: Path,
    start: str,
    end: str,
    topn_values: Sequence[int],
    score_names: Sequence[str],
    min_train_days: int,
    test_days: int,
    max_folds: int,
    embargo_days: int,
    min_train_n: int,
    min_train_active_days: int,
    grid_profile: str,
) -> Dict[str, Any]:
    started = perf_counter()
    frame = _load_market_frame(cache_path, market)
    frame = _filter_valid_labels(frame, start=start, end=end)
    frame = _prepare_policy_columns(frame)
    days = sorted(frame["base_trade_date"].dropna().astype(str).unique().tolist())
    windows = _walk_windows(days, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds, embargo_days=embargo_days)
    candidates = evaluate_adaptive_policy(
        market=market,
        frame=frame,
        windows=windows,
        topn_values=topn_values,
        score_names=score_names,
        min_train_n=min_train_n,
        min_train_active_days=min_train_active_days,
        grid_profile=grid_profile,
    )
    ranked = sorted(
        candidates,
        key=lambda item: (
            bool(item.get("gate", {}).get("production_ready")),
            bool(item.get("gate", {}).get("shadow_display_allowed")),
            float(item.get("policy_objective") or -999999.0),
            float(item.get("quality_score") or -999999.0),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    return {
        "market": market,
        "cache_path": str(cache_path),
        "rows": int(len(frame)),
        "days": int(len(days)),
        "date_min": days[0] if days else None,
        "date_max": days[-1] if days else None,
        "windows": [
            {
                "fold": int(window.fold),
                "train_days": len(window.train_days),
                "test_days": len(window.test_days),
                "embargo_days": len(window.embargo_days),
                "test_start": window.test_days[0] if window.test_days else None,
                "test_end": window.test_days[-1] if window.test_days else None,
            }
            for window in windows
        ],
        "grid_profile": grid_profile,
        "rules_tested_per_fold": len(_rules_for_market(market, profile=grid_profile)),
        "score_modes": list(score_names),
        "topn_values": [int(value) for value in topn_values],
        "best": best,
        "ranked": ranked,
        "elapsed_sec": _round(perf_counter() - started, 3),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    reports: List[Dict[str, Any]] = []
    for market in args.markets:
        market_key = market.upper()
        override = args.kospi_cache if market_key == "KOSPI" else args.kosdaq_cache if market_key == "KOSDAQ" else None
        reports.append(
            _market_report(
                market=market_key,
                cache_path=_market_cache_path(market_key, args.start, args.end, override),
                start=args.start,
                end=args.end,
                topn_values=args.topn,
                score_names=args.score_modes,
                min_train_days=args.min_train_days,
                test_days=args.test_days,
                max_folds=args.max_folds,
                embargo_days=args.embargo_days,
                min_train_n=args.min_train_n,
                min_train_active_days=args.min_train_active_days,
                grid_profile=args.grid_profile,
            )
        )
    production_ready = [report for report in reports if (report.get("best") or {}).get("gate", {}).get("production_ready")]
    shadow_ready = [report for report in reports if (report.get("best") or {}).get("gate", {}).get("shadow_display_allowed")]
    status = "production_ready" if len(production_ready) == len(reports) and reports else "shadow_ready" if shadow_ready else "blocked"
    return {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "status": status,
        "date_range": {"start": args.start, "end": args.end},
        "assumptions": {
            "real_data_only": True,
            "buy_premium_pct": BUY_PREMIUM_PCT,
            "target_pct": TARGET_PCT,
            "stop_pct": STOP_PCT,
            "success_label": "buy_premium_target_hit_5d == true AND buy_premium_min_low_return_5d_pct >= -10",
            "validation": "walk-forward adaptive rule selection: train window chooses rule, next test window evaluates it",
        },
        "markets": reports,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# KIS Tail-Safe Policy Search",
        "",
        f"- status: `{report.get('status')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- date_range: `{report.get('date_range', {}).get('start')}`..`{report.get('date_range', {}).get('end')}`",
        f"- success_label: `{report.get('assumptions', {}).get('success_label')}`",
        f"- validation: `{report.get('assumptions', {}).get('validation')}`",
        "",
    ]
    for market_report in report.get("markets", []):
        best = market_report.get("best") or {}
        metrics = best.get("metrics") or {}
        gate = best.get("gate") or {}
        identity = best.get("identity") or {}
        lines.extend(
            [
                f"## {market_report.get('market')}",
                "",
                f"- source: `{market_report.get('cache_path')}`",
                f"- rows/days: `{market_report.get('rows')}` / `{market_report.get('days')}`",
                f"- windows: `{len(market_report.get('windows') or [])}`",
                f"- best: `{identity.get('score_mode')}` topN=`{identity.get('topn')}` status=`{gate.get('status')}`",
                f"- blockers: `{gate.get('production_blocking_reasons')}`",
                f"- metrics: n=`{metrics.get('n')}`, active_days=`{metrics.get('active_days')}`, hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}`, target_before_stop=`{metrics.get('target_before_stop_5d_pct')}`, win5=`{metrics.get('win_5d_pct')}`, hit10=`{metrics.get('hit10_5d_pct')}`, stop5=`{metrics.get('stop5_pct')}`, bad_path=`{metrics.get('bad_path_pct')}`, avg5=`{metrics.get('avg_5d_pct')}`, avg_exit=`{metrics.get('avg_ordered_exit_5d_pct')}`, min_low=`{metrics.get('min_min_low_5d_pct')}`",
                "",
                "| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |",
                "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for rank, row in enumerate((market_report.get("ranked") or [])[:8], start=1):
            row_metrics = row.get("metrics") or {}
            row_gate = row.get("gate") or {}
            row_identity = row.get("identity") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(rank),
                        str(row_identity.get("score_mode")),
                        _fmt(row_identity.get("topn")),
                        str(row_gate.get("status")),
                        _fmt(row_metrics.get("n")),
                        _fmt(row_metrics.get("active_days")),
                        _fmt(row_metrics.get("hit5_dd10_5d_pct")),
                        _fmt(row_metrics.get("hit10_5d_pct")),
                        _fmt(row_metrics.get("stop5_pct")),
                        _fmt(row_metrics.get("bad_path_pct")),
                        _fmt(row_metrics.get("avg_ordered_exit_5d_pct")),
                        _fmt(row_metrics.get("min_min_low_5d_pct")),
                    ]
                )
                + " |"
            )
        latest_rule = best.get("latest_recommended_rule") or {}
        if latest_rule:
            lines.extend(
                [
                    "",
                    "### Latest Recommended Rule",
                    "",
                    f"- rule: `{latest_rule.get('rule_name')}`",
                    f"- train_objective: `{latest_rule.get('objective')}`",
                    f"- train_metrics: `{json.dumps(latest_rule.get('metrics') or {}, ensure_ascii=False)}`",
                ]
            )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search KIS tail-safe daily topN policies on real historical universe caches.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"])
    parser.add_argument("--kospi-cache")
    parser.add_argument("--kosdaq-cache")
    parser.add_argument("--topn", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--score-modes", nargs="+", choices=sorted(SCORE_SPECS), default=sorted(SCORE_SPECS))
    parser.add_argument("--min-train-days", type=int, default=35)
    parser.add_argument("--test-days", type=int, default=12)
    parser.add_argument("--max-folds", type=int, default=4)
    parser.add_argument("--embargo-days", type=int, default=5)
    parser.add_argument("--min-train-n", type=int, default=18)
    parser.add_argument("--min-train-active-days", type=int, default=8)
    parser.add_argument("--grid-profile", choices=["exhaustive", "fast"], default="exhaustive")
    parser.add_argument(
        "--output-json",
        default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_REPORT_STEM}.json"),
    )
    parser.add_argument(
        "--output-md",
        default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_REPORT_STEM}.md"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run(args)
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": report.get("status"), "output_json": str(output_json), "output_md": args.output_md}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
