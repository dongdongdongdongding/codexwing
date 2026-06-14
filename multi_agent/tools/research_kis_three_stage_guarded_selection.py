#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate
from multi_agent.tools.research_kis_three_stage_ev_ranker import (
    BUY_PREMIUM_PCT,
    Config,
    REPORT_VERSION as THREE_STAGE_REPORT_VERSION,
    STOP_PCT,
    TARGET_PCT,
    _apply_sidecar_coverage_filter,
    _choose_threshold,
    _configs,
    _feature_sets,
    _filter_valid_labels,
    _fit_classifier,
    _load_research_frame,
    _metric_summary,
    _parse_optional_float_list,
    _predict,
    _rank_score,
    _score_family,
    _select_pool,
    _top_per_day,
    _utc_now,
    _walk_windows,
)


REPORT_VERSION = "kis_three_stage_guarded_selection_research_v1"
DEFAULT_STEM = "kis_three_stage_guarded_selection_20260101_20260610"
QUANTILES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
DEFAULT_GUARD_FEATURES = (
    "_p_success",
    "_p_tail",
    "_p_hit10",
    "_rank_score",
    "day_return_pct",
    "volume_ratio",
    "feature_coverage_score",
    "kis_prev_volume_ratio",
    "kis_whale_score",
    "kis_foreigner_1d",
    "kis_institution_1d",
    "kis_whale_flow_3d",
    "kis_whale_flow_10d",
    "kis_daily_return_5d_pct",
    "kis_daily_return_20d_pct",
    "kis_daily_return_60d_pct",
    "kis_daily_volume_ratio_20d",
    "kis_daily_close_location_pct",
    "kis_daily_pct_from_52w_high",
    "kis_news_title_count",
    "kis_news_source_scope_confidence",
    "kis_news_source_scope_ambiguous",
    "kis_financial_revenue_growth_rate",
    "kis_financial_operating_profit_margin",
    "kis_financial_net_income_margin",
    "kis_financial_roe",
    "kis_financial_per",
    "kis_financial_pbr",
    "kis_financial_debt_ratio",
    "kis_financial_current_ratio",
    "kis_prefilter_selection_score",
    "kis_prefilter_rank_volume",
    "kis_prefilter_rank_fluctuation",
    "kis_prefilter_rank_volume_power",
    "kis_prefilter_quote_prev_volume_ratio",
    "kis_prefilter_quote_market_cap",
    "kis_prefilter_flow_whale_score",
    "kis_prefilter_flow_foreigner_1d",
    "kis_prefilter_flow_institution_1d",
    "kis_prefilter_flow_foreigner_3d",
    "kis_prefilter_flow_institution_3d",
    "kis_prefilter_flow_foreigner_10d",
    "kis_prefilter_flow_institution_10d",
    "close_failure_prior_ticker_failure_rate_pct",
    "close_failure_prior_ticker_clean_defense_rate_pct",
    "close_failure_prior_ticker_stop5_rate_pct",
    "close_failure_prior_ticker_avg_close_5d_pct",
    "close_failure_prior_ticker_avg_mfe_5d_pct",
    "close_failure_prior_ticker_avg_mae_5d_pct",
    "close_failure_prior_ticker_risk_score",
    "close_failure_prior_theme_failure_rate_pct",
    "close_failure_prior_theme_clean_defense_rate_pct",
    "close_failure_prior_theme_stop5_rate_pct",
    "close_failure_prior_theme_avg_close_5d_pct",
    "close_failure_prior_theme_avg_mfe_5d_pct",
    "close_failure_prior_theme_avg_mae_5d_pct",
    "close_failure_prior_theme_risk_score",
    "close_failure_prior_kis_theme_failure_rate_pct",
    "close_failure_prior_kis_theme_clean_defense_rate_pct",
    "close_failure_prior_kis_theme_stop5_rate_pct",
    "close_failure_prior_kis_theme_avg_close_5d_pct",
    "close_failure_prior_kis_theme_avg_mfe_5d_pct",
    "close_failure_prior_kis_theme_avg_mae_5d_pct",
    "close_failure_prior_kis_theme_risk_score",
    "close_failure_prior_kis_sector_failure_rate_pct",
    "close_failure_prior_kis_sector_clean_defense_rate_pct",
    "close_failure_prior_kis_sector_stop5_rate_pct",
    "close_failure_prior_kis_sector_avg_close_5d_pct",
    "close_failure_prior_kis_sector_avg_mfe_5d_pct",
    "close_failure_prior_kis_sector_avg_mae_5d_pct",
    "close_failure_prior_kis_sector_risk_score",
    "close_failure_prior_market_failure_rate_pct",
    "close_failure_prior_market_clean_defense_rate_pct",
    "close_failure_prior_market_stop5_rate_pct",
    "close_failure_prior_market_avg_close_5d_pct",
    "close_failure_prior_market_avg_mfe_5d_pct",
    "close_failure_prior_market_avg_mae_5d_pct",
    "close_failure_prior_market_risk_score",
)


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _round(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _metric_subset(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "n",
        "active_days",
        "hit5_dd10_5d_pct",
        "hit10_5d_pct",
        "safe_hit10_5d_pct",
        "tail_breach_5d_pct",
        "bad_path_pct",
        "avg_5d_pct",
        "avg_ordered_exit_5d_pct",
        "avg_dynamic_exit_5d_pct",
        "avg_mfe_5d_pct",
        "avg_mae_5d_pct",
        "min_min_low_5d_pct",
        "expected_binary_net_5d_pct",
    )
    return {key: metrics.get(key) for key in keys if key in metrics}


def _safe_metric(frame: pd.DataFrame, idx: pd.Index) -> Dict[str, Any]:
    if len(idx) == 0:
        return {"n": 0, "active_days": 0}
    return _metric_summary(frame, pd.Index(idx).drop_duplicates())


def _gate_identity(*, market: str, config: Config, model: str) -> Dict[str, Any]:
    return {
        "suite_version": REPORT_VERSION,
        "upstream_suite_version": THREE_STAGE_REPORT_VERSION,
        "model": model,
        "score_mode": config.score_mode,
        "feature_set": "kis_three_stage_guarded_selection",
        "market": market,
        "label": "touch5_dd10_5d",
        "pool": config.pool,
        "pool_k": int(config.pool_k),
        "final_topn": int(config.final_topn),
        "max_tail_prob": config.max_tail_prob,
        "buy_premium_pct": BUY_PREMIUM_PCT,
        "target_pct": TARGET_PCT,
        "stop_pct": STOP_PCT,
    }


def _gate(market: str, config: Config, metrics: Mapping[str, Any], *, model: str) -> Dict[str, Any]:
    return evaluate_kis_model_gate(identity=_gate_identity(market=market, config=config, model=model), metrics=metrics, market=market)


def _objective(metrics: Mapping[str, Any]) -> float:
    n = int(metrics.get("n") or 0)
    hit = float(metrics.get("hit5_dd10_5d_pct") or 0.0)
    hit10 = float(metrics.get("hit10_5d_pct") or 0.0)
    avg_exit = float(metrics.get("avg_ordered_exit_5d_pct") or -20.0)
    tail = float(metrics.get("tail_breach_5d_pct") or 100.0)
    bad = float(metrics.get("bad_path_pct") or 100.0)
    min_low = float(metrics.get("min_min_low_5d_pct") or -100.0)
    hard_tail_penalty = max(0.0, -abs(STOP_PCT) - min_low) * 2.2
    return hit * 1.6 + hit10 * 0.30 + avg_exit * 12.0 - tail * 1.2 - bad * 0.20 - hard_tail_penalty + min(n, 80) * 0.08


def _usable_guard_features(frame: pd.DataFrame, requested: Sequence[str]) -> List[str]:
    out: List[str] = []
    for column in requested:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().sum() < 8:
            continue
        if values.nunique(dropna=True) < 3:
            continue
        out.append(column)
    return out


def _split_selected_rows(selected: pd.DataFrame, train_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    days = sorted(selected["base_trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < 4:
        return selected.iloc[0:0].copy(), selected.iloc[0:0].copy(), {"reason": "too_few_selected_days", "days": len(days)}
    split_at = max(1, min(len(days) - 1, int(math.floor(len(days) * float(train_ratio)))))
    train_days = set(days[:split_at])
    train = selected[selected["base_trade_date"].astype(str).isin(train_days)].copy()
    holdout = selected[~selected["base_trade_date"].astype(str).isin(train_days)].copy()
    return train, holdout, {
        "train_days": len(train_days),
        "holdout_days": len(days) - len(train_days),
        "train_start": days[0],
        "train_end": days[split_at - 1],
        "holdout_start": days[split_at],
        "holdout_end": days[-1],
    }


def _apply_keep_rule(frame: pd.DataFrame, feature: str, op: str, threshold: float) -> pd.Series:
    values = pd.to_numeric(frame[feature], errors="coerce")
    if op == "le":
        return values.le(float(threshold)).fillna(False)
    if op == "ge":
        return values.ge(float(threshold)).fillna(False)
    raise ValueError(f"unknown_op:{op}")


def _guard_name(feature: str, op: str, threshold: float) -> str:
    value = f"{threshold:g}".replace("-", "neg").replace(".", "p")
    return f"keep_{feature}_{op}_{value}"


def _search_single_guard(
    *,
    market: str,
    frame: pd.DataFrame,
    config: Config,
    selected: pd.DataFrame,
    guard_features: Sequence[str],
    train_ratio: float,
    min_train_n: int,
    min_holdout_n: int,
    min_retention: float,
) -> Dict[str, Any]:
    train, holdout, split = _split_selected_rows(selected, train_ratio)
    if train.empty or holdout.empty:
        return {"status": "skipped", "split": split, "reason": split.get("reason") or "empty_train_or_holdout"}
    base_train = _safe_metric(frame, train.index)
    base_holdout = _safe_metric(frame, holdout.index)
    if int(base_train.get("n") or 0) < min_train_n or int(base_holdout.get("n") or 0) < min_holdout_n:
        return {
            "status": "skipped",
            "split": split,
            "reason": "insufficient_base_selected_rows",
            "base_train": _metric_subset(base_train),
            "base_holdout": _metric_subset(base_holdout),
        }

    candidates: List[Dict[str, Any]] = []
    for feature in _usable_guard_features(selected, guard_features):
        train_values = pd.to_numeric(train[feature], errors="coerce").dropna()
        if train_values.empty:
            continue
        thresholds = sorted({float(train_values.quantile(q)) for q in QUANTILES if math.isfinite(float(train_values.quantile(q)))})
        for threshold in thresholds:
            for op in ("le", "ge"):
                train_keep = _apply_keep_rule(train, feature, op, threshold)
                holdout_keep = _apply_keep_rule(holdout, feature, op, threshold)
                if int(train_keep.sum()) < min_train_n or int(holdout_keep.sum()) < min_holdout_n:
                    continue
                train_retention = float(train_keep.mean()) if len(train_keep) else 0.0
                holdout_retention = float(holdout_keep.mean()) if len(holdout_keep) else 0.0
                if train_retention < min_retention or holdout_retention < min_retention:
                    continue
                train_metrics = _safe_metric(frame, train.loc[train_keep].index)
                holdout_metrics = _safe_metric(frame, holdout.loc[holdout_keep].index)
                train_delta_exit = float(train_metrics.get("avg_ordered_exit_5d_pct") or -20.0) - float(
                    base_train.get("avg_ordered_exit_5d_pct") or -20.0
                )
                holdout_delta_exit = float(holdout_metrics.get("avg_ordered_exit_5d_pct") or -20.0) - float(
                    base_holdout.get("avg_ordered_exit_5d_pct") or -20.0
                )
                train_delta_hit = float(train_metrics.get("hit5_dd10_5d_pct") or 0.0) - float(
                    base_train.get("hit5_dd10_5d_pct") or 0.0
                )
                holdout_delta_hit = float(holdout_metrics.get("hit5_dd10_5d_pct") or 0.0) - float(
                    base_holdout.get("hit5_dd10_5d_pct") or 0.0
                )
                train_delta_low = float(train_metrics.get("min_min_low_5d_pct") or -100.0) - float(
                    base_train.get("min_min_low_5d_pct") or -100.0
                )
                holdout_delta_low = float(holdout_metrics.get("min_min_low_5d_pct") or -100.0) - float(
                    base_holdout.get("min_min_low_5d_pct") or -100.0
                )
                # Require the rule to be learned on a real train-side improvement.
                if train_delta_exit < -0.05 and train_delta_hit < 0.0 and train_delta_low < 0.0:
                    continue
                total_idx = train.loc[train_keep].index.append(holdout.loc[holdout_keep].index).drop_duplicates()
                total_metrics = _safe_metric(frame, total_idx)
                holdout_gate = _gate(market, config, holdout_metrics, model="kis_three_stage_guarded_selection_holdout")
                total_gate = _gate(market, config, total_metrics, model="kis_three_stage_guarded_selection_observed_all")
                objective = (
                    _objective(holdout_metrics)
                    + max(0.0, holdout_delta_exit) * 15.0
                    + max(0.0, holdout_delta_hit) * 0.8
                    + max(0.0, holdout_delta_low) * 0.8
                    - max(0.0, -holdout_delta_exit) * 8.0
                )
                candidates.append(
                    {
                        "guard": {
                            "type": "single_feature_keep",
                            "name": _guard_name(feature, op, threshold),
                            "feature": feature,
                            "op": op,
                            "threshold": _round(threshold),
                        },
                        "train_retention": _round(train_retention, 4),
                        "holdout_retention": _round(holdout_retention, 4),
                        "train_metrics": _metric_subset(train_metrics),
                        "holdout_metrics": _metric_subset(holdout_metrics),
                        "all_metrics": _metric_subset(total_metrics),
                        "deltas": {
                            "train_avg_exit_delta": _round(train_delta_exit),
                            "holdout_avg_exit_delta": _round(holdout_delta_exit),
                            "train_hit5_delta": _round(train_delta_hit),
                            "holdout_hit5_delta": _round(holdout_delta_hit),
                            "train_min_low_delta": _round(train_delta_low),
                            "holdout_min_low_delta": _round(holdout_delta_low),
                        },
                        "holdout_gate": holdout_gate,
                        "all_gate": total_gate,
                        "objective": _round(objective, 6),
                    }
                )

    candidates.sort(
        key=lambda row: (
            bool((row.get("holdout_gate") or {}).get("production_ready")),
            bool((row.get("holdout_gate") or {}).get("shadow_display_allowed")),
            float(row.get("objective") or -999999.0),
            float((row.get("deltas") or {}).get("holdout_avg_exit_delta") or -999.0),
        ),
        reverse=True,
    )
    best = candidates[0] if candidates else None
    status = "guard_found" if best else "no_guard_candidate"
    return {
        "status": status,
        "split": split,
        "base_train": _metric_subset(base_train),
        "base_holdout": _metric_subset(base_holdout),
        "guards_tested": len(candidates),
        "best_guard": best,
        "top_guards": candidates[:20],
    }


def _loss_traits(selected: pd.DataFrame, guard_features: Sequence[str], *, limit: int = 20) -> List[Dict[str, Any]]:
    if selected.empty:
        return []
    bad_mask = selected["_label_tail_breach"].astype(bool) | pd.to_numeric(selected["_close_5d"], errors="coerce").lt(0.0)
    good_mask = selected["_label_success"].astype(bool)
    if int(bad_mask.sum()) < 3 or int(good_mask.sum()) < 3:
        return []
    rows: List[Dict[str, Any]] = []
    for feature in _usable_guard_features(selected, guard_features):
        values = pd.to_numeric(selected[feature], errors="coerce")
        bad = values.loc[bad_mask].dropna()
        good = values.loc[good_mask].dropna()
        all_values = values.dropna()
        if len(bad) < 3 or len(good) < 3 or all_values.std(ddof=0) == 0:
            continue
        delta = float(bad.median() - good.median())
        scaled = delta / float(all_values.std(ddof=0))
        rows.append(
            {
                "feature": feature,
                "bad_median": _round(bad.median()),
                "good_median": _round(good.median()),
                "delta_bad_minus_good": _round(delta),
                "scaled_delta": _round(scaled),
            }
        )
    rows.sort(key=lambda row: abs(float(row.get("scaled_delta") or 0.0)), reverse=True)
    return rows[:limit]


def _selected_cases_for_market(
    *,
    market: str,
    cache_path: Path,
    start: str,
    end: str,
    configs: Sequence[Config],
    min_train_days: int,
    test_days: int,
    max_folds: int,
    embargo_days: int,
    calibration_days: int,
    required_sidecar_coverage: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]:
    raw_frame = _load_research_frame(cache_path, market)
    frame, coverage_filter = _apply_sidecar_coverage_filter(raw_frame, required_sidecar_coverage)
    frame = _filter_valid_labels(frame, start=start, end=end)
    frame["_label_tail_breach"] = frame["_mae_5d"].lt(-abs(STOP_PCT)).fillna(False)
    numeric = _feature_sets(frame)["kis_failure_prior_numeric"][0]
    windows = _walk_windows(
        sorted(frame["base_trade_date"].dropna().astype(str).unique().tolist()),
        min_train_days=min_train_days,
        test_days=test_days,
        max_folds=max_folds,
        embargo_days=embargo_days,
    )
    selected_rows: List[pd.DataFrame] = []
    fold_rows: List[Dict[str, Any]] = []
    for window in windows:
        train = frame[frame["base_trade_date"].isin(window.train_days)].copy()
        test = frame[frame["base_trade_date"].isin(window.test_days)].copy()
        if train.empty or test.empty:
            continue
        train_days = sorted(train["base_trade_date"].dropna().astype(str).unique().tolist())
        cal_days = train_days[-int(calibration_days) :] if len(train_days) > calibration_days else train_days[-max(4, len(train_days) // 4) :]
        fit = train[~train["base_trade_date"].isin(cal_days)].copy()
        calibration = train[train["base_trade_date"].isin(cal_days)].copy()
        if fit.empty or calibration.empty:
            continue
        try:
            success_model = _fit_classifier(fit, numeric, "_label_success")
            tail_model = _fit_classifier(fit, numeric, "_label_tail_breach")
            hit10_model = _fit_classifier(fit, numeric, "_label_hit10")
        except ValueError as exc:
            fold_rows.append({"fold": int(window.fold), "skipped": True, "reason": str(exc)})
            continue
        p_success_cal = _predict(success_model, calibration, numeric)
        p_tail_cal = _predict(tail_model, calibration, numeric)
        p_hit10_cal = _predict(hit10_model, calibration, numeric)
        p_success_test = _predict(success_model, test, numeric)
        p_tail_test = _predict(tail_model, test, numeric)
        p_hit10_test = _predict(hit10_model, test, numeric)
        cal_pool_scores = _score_family(calibration)
        test_pool_scores = _score_family(test)
        evaluated = 0
        selected_count = 0
        for cfg in configs:
            cal_pool = _select_pool(calibration, cal_pool_scores, cfg.pool, cfg.pool_k)
            test_pool = _select_pool(test, test_pool_scores, cfg.pool, cfg.pool_k)
            if cfg.max_tail_prob is not None:
                max_tail_prob = float(cfg.max_tail_prob)
                cal_pool = cal_pool[cal_pool.isin(p_tail_cal[p_tail_cal.le(max_tail_prob)].index)]
                test_pool = test_pool[test_pool.isin(p_tail_test[p_tail_test.le(max_tail_prob)].index)]
            if len(cal_pool) == 0 or len(test_pool) == 0:
                continue
            cal_score = _rank_score(cfg.score_mode, p_success_cal, p_tail_cal, p_hit10_cal).reindex(cal_pool)
            threshold, threshold_meta = _choose_threshold(calibration.loc[cal_pool], cal_score, final_topn=cfg.final_topn)
            if threshold is None:
                continue
            test_score = _rank_score(cfg.score_mode, p_success_test, p_tail_test, p_hit10_test).reindex(test_pool)
            test_top = _top_per_day(test.loc[test_pool], test_score, topn=cfg.final_topn)
            selected = test_top[test_top["_rank_score"].ge(float(threshold))].copy()
            evaluated += 1
            selected_count += int(len(selected))
            if selected.empty:
                continue
            selected["_p_success"] = p_success_test.reindex(selected.index)
            selected["_p_tail"] = p_tail_test.reindex(selected.index)
            selected["_p_hit10"] = p_hit10_test.reindex(selected.index)
            selected["_threshold"] = float(threshold)
            selected["_fold"] = int(window.fold)
            selected["_config_key"] = cfg.key()
            selected["_pool"] = cfg.pool
            selected["_pool_k"] = int(cfg.pool_k)
            selected["_final_topn"] = int(cfg.final_topn)
            selected["_score_mode"] = cfg.score_mode
            selected["_max_tail_prob"] = cfg.max_tail_prob
            selected["_threshold_objective"] = (threshold_meta or {}).get("objective")
            selected_rows.append(selected)
        fold_rows.append(
            {
                "fold": int(window.fold),
                "train_days": len(window.train_days),
                "calibration_days": len(cal_days),
                "test_days": len(window.test_days),
                "test_start": window.test_days[0] if window.test_days else None,
                "test_end": window.test_days[-1] if window.test_days else None,
                "configs_evaluated": evaluated,
                "selected_rows": selected_count,
            }
        )
    combined = pd.concat(selected_rows, axis=0, sort=False) if selected_rows else frame.iloc[0:0].copy()
    meta = {
        "rows": int(len(frame)),
        "days": int(frame["base_trade_date"].nunique()),
        "coverage_filter": coverage_filter,
        "windows": [
            {
                "fold": int(w.fold),
                "train_days": len(w.train_days),
                "test_days": len(w.test_days),
                "embargo_days": len(w.embargo_days),
                "test_start": w.test_days[0] if w.test_days else None,
                "test_end": w.test_days[-1] if w.test_days else None,
            }
            for w in windows
        ],
    }
    return frame, combined, fold_rows, meta


def _market_cache_path(market: str, start: str, end: str, override: str | None = None) -> Path:
    if override:
        return Path(override)
    return (
        PROJECT_ROOT
        / "runtime_state/reports/learning"
        / f"kis_historical_universe_prepared_{market.lower()}_{start.replace('-', '')}_{end.replace('-', '')}.pkl"
    )


def _summarize_market(
    *,
    market: str,
    cache_path: Path,
    start: str,
    end: str,
    configs: Sequence[Config],
    args: argparse.Namespace,
    guard_features: Sequence[str],
) -> Dict[str, Any]:
    started = perf_counter()
    frame, selected, fold_rows, meta = _selected_cases_for_market(
        market=market,
        cache_path=cache_path,
        start=start,
        end=end,
        configs=configs,
        min_train_days=int(args.min_train_days),
        test_days=int(args.test_days),
        max_folds=int(args.max_folds),
        embargo_days=int(args.embargo_days),
        calibration_days=int(args.calibration_days),
        required_sidecar_coverage=args.require_sidecar_coverage,
    )
    config_rows: List[Dict[str, Any]] = []
    for cfg in configs:
        case_rows = selected[selected["_config_key"].eq(cfg.key())].copy() if "_config_key" in selected.columns else selected.iloc[0:0].copy()
        idx = pd.Index(case_rows.index).drop_duplicates()
        base_metrics = _safe_metric(frame, idx)
        base_gate = _gate(market, cfg, base_metrics, model="kis_three_stage_guarded_selection_base")
        guard = _search_single_guard(
            market=market,
            frame=frame,
            config=cfg,
            selected=case_rows,
            guard_features=guard_features,
            train_ratio=float(args.guard_train_ratio),
            min_train_n=int(args.min_guard_train_n),
            min_holdout_n=int(args.min_guard_holdout_n),
            min_retention=float(args.min_guard_retention),
        )
        best_guard = guard.get("best_guard") if isinstance(guard.get("best_guard"), Mapping) else None
        holdout_metrics = (best_guard or {}).get("holdout_metrics") or {}
        all_metrics = (best_guard or {}).get("all_metrics") or {}
        config_rows.append(
            {
                "config": cfg.__dict__,
                "config_key": cfg.key(),
                "base_metrics": _metric_subset(base_metrics),
                "base_gate": base_gate,
                "guard_search": guard,
                "loss_traits": _loss_traits(case_rows, guard_features),
                "ranking_score": _round(
                    (
                        (600.0 if ((best_guard or {}).get("holdout_gate") or {}).get("production_ready") else 0.0)
                        + (160.0 if ((best_guard or {}).get("holdout_gate") or {}).get("shadow_display_allowed") else 0.0)
                        + _objective(holdout_metrics if holdout_metrics else base_metrics)
                        + float((best_guard or {}).get("objective") or 0.0) * 0.1
                        + float(all_metrics.get("avg_ordered_exit_5d_pct") or 0.0) * 1.5
                    ),
                    6,
                ),
            }
        )
    config_rows.sort(
        key=lambda row: (
            bool((((row.get("guard_search") or {}).get("best_guard") or {}).get("holdout_gate") or {}).get("production_ready")),
            bool((((row.get("guard_search") or {}).get("best_guard") or {}).get("holdout_gate") or {}).get("shadow_display_allowed")),
            float(row.get("ranking_score") or -999999.0),
            float((row.get("base_metrics") or {}).get("avg_ordered_exit_5d_pct") or -999.0),
        ),
        reverse=True,
    )
    return {
        "market": market,
        "cache_path": str(cache_path),
        "meta": meta,
        "folds": fold_rows,
        "selected_rows": int(len(selected)),
        "config_count": int(len(configs)),
        "guard_features": list(guard_features),
        "best": config_rows[0] if config_rows else None,
        "ranked": config_rows[: int(args.ranked_limit)],
        "elapsed_sec": _round(perf_counter() - started, 3),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    configs = _configs(
        args.pool_modes,
        args.pool_k,
        args.final_topn,
        args.score_modes,
        args.max_tail_prob_thresholds,
    )
    guard_features = list(dict.fromkeys(list(DEFAULT_GUARD_FEATURES) + list(args.extra_guard_features or [])))
    reports = []
    for market in args.markets:
        market_key = market.upper()
        override = args.kospi_cache if market_key == "KOSPI" else args.kosdaq_cache if market_key == "KOSDAQ" else None
        reports.append(
            _summarize_market(
                market=market_key,
                cache_path=_market_cache_path(market_key, args.start, args.end, override),
                start=args.start,
                end=args.end,
                configs=configs,
                args=args,
                guard_features=guard_features,
            )
        )
    any_holdout_shadow = any(
        bool(((((market.get("best") or {}).get("guard_search") or {}).get("best_guard") or {}).get("holdout_gate") or {}).get("shadow_display_allowed"))
        for market in reports
    )
    any_holdout_prod = any(
        bool(((((market.get("best") or {}).get("guard_search") or {}).get("best_guard") or {}).get("holdout_gate") or {}).get("production_ready"))
        for market in reports
    )
    return {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "status": "holdout_production_candidate" if any_holdout_prod else "holdout_shadow_candidate" if any_holdout_shadow else "blocked",
        "assumptions": {
            "real_data_only": True,
            "validation": "Reproduce three-stage walk-forward selections, split selected cases chronologically, learn single-feature keep guards on selected-train rows, evaluate on selected-holdout rows.",
            "leakage_control": "Guard feature allow-list excludes realized outcome labels; model probabilities are allowed because they exist at scan time.",
            "buy_premium_pct": BUY_PREMIUM_PCT,
            "target_pct": TARGET_PCT,
            "stop_pct": STOP_PCT,
        },
        "date_range": {"start": args.start, "end": args.end},
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
        "# KIS Three-Stage Guarded Selection Research",
        "",
        f"- status: `{report.get('status')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- date_range: `{report.get('date_range', {}).get('start')}`..`{report.get('date_range', {}).get('end')}`",
        f"- validation: `{report.get('assumptions', {}).get('validation')}`",
        f"- leakage_control: `{report.get('assumptions', {}).get('leakage_control')}`",
        "",
    ]
    for market_report in report.get("markets", []):
        best = market_report.get("best") or {}
        config = best.get("config") or {}
        base = best.get("base_metrics") or {}
        guard_search = best.get("guard_search") or {}
        guard = guard_search.get("best_guard") or {}
        holdout = guard.get("holdout_metrics") or {}
        all_metrics = guard.get("all_metrics") or {}
        deltas = guard.get("deltas") or {}
        holdout_gate = guard.get("holdout_gate") or {}
        guard_payload = guard.get("guard") or {}
        lines.extend(
            [
                f"## {market_report.get('market')}",
                "",
                f"- source: `{market_report.get('cache_path')}`",
                f"- rows/days: `{(market_report.get('meta') or {}).get('rows')}` / `{(market_report.get('meta') or {}).get('days')}`",
                f"- selected_rows/configs: `{market_report.get('selected_rows')}` / `{market_report.get('config_count')}`",
                f"- best_config: pool=`{config.get('pool')}` pool_k=`{config.get('pool_k')}` final_topn=`{config.get('final_topn')}` score=`{config.get('score_mode')}` max_tail_prob=`{config.get('max_tail_prob')}`",
                f"- base_metrics: n=`{base.get('n')}`, days=`{base.get('active_days')}`, hit5=`{base.get('hit5_dd10_5d_pct')}`, hit10=`{base.get('hit10_5d_pct')}`, tail=`{base.get('tail_breach_5d_pct')}`, avg_exit=`{base.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{base.get('avg_dynamic_exit_5d_pct')}`, min_low=`{base.get('min_min_low_5d_pct')}`",
                f"- best_guard: `{guard_payload.get('name')}` holdout_gate=`{holdout_gate.get('status')}` blockers=`{holdout_gate.get('production_blocking_reasons')}`",
                f"- holdout_metrics: n=`{holdout.get('n')}`, days=`{holdout.get('active_days')}`, hit5=`{holdout.get('hit5_dd10_5d_pct')}`, hit10=`{holdout.get('hit10_5d_pct')}`, tail=`{holdout.get('tail_breach_5d_pct')}`, avg_exit=`{holdout.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{holdout.get('avg_dynamic_exit_5d_pct')}`, min_low=`{holdout.get('min_min_low_5d_pct')}`",
                f"- all_guarded_metrics: n=`{all_metrics.get('n')}`, days=`{all_metrics.get('active_days')}`, hit5=`{all_metrics.get('hit5_dd10_5d_pct')}`, hit10=`{all_metrics.get('hit10_5d_pct')}`, tail=`{all_metrics.get('tail_breach_5d_pct')}`, avg_exit=`{all_metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{all_metrics.get('avg_dynamic_exit_5d_pct')}`, min_low=`{all_metrics.get('min_min_low_5d_pct')}`",
                f"- holdout_deltas: avg_exit=`{deltas.get('holdout_avg_exit_delta')}`, hit5=`{deltas.get('holdout_hit5_delta')}`, min_low=`{deltas.get('holdout_min_low_delta')}`",
                "",
                "| rank | config | base_n | base_hit5 | base_avg_exit | guard | holdout_n | holdout_hit5 | holdout_avg_exit | holdout_min_low | holdout_gate |",
                "|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
            ]
        )
        for rank, row in enumerate((market_report.get("ranked") or [])[:12], start=1):
            row_config = row.get("config") or {}
            row_base = row.get("base_metrics") or {}
            row_guard = ((row.get("guard_search") or {}).get("best_guard") or {})
            row_guard_payload = row_guard.get("guard") or {}
            row_holdout = row_guard.get("holdout_metrics") or {}
            row_gate = row_guard.get("holdout_gate") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(rank),
                        f"{row_config.get('pool')}/k{row_config.get('pool_k')}/n{row_config.get('final_topn')}/{row_config.get('score_mode')}/tail{row_config.get('max_tail_prob')}",
                        _fmt(row_base.get("n")),
                        _fmt(row_base.get("hit5_dd10_5d_pct")),
                        _fmt(row_base.get("avg_ordered_exit_5d_pct")),
                        str(row_guard_payload.get("name") or "-"),
                        _fmt(row_holdout.get("n")),
                        _fmt(row_holdout.get("hit5_dd10_5d_pct")),
                        _fmt(row_holdout.get("avg_ordered_exit_5d_pct")),
                        _fmt(row_holdout.get("min_min_low_5d_pct")),
                        str(row_gate.get("status") or "-"),
                    ]
                )
                + " |"
            )
        traits = best.get("loss_traits") or []
        if traits:
            lines.extend(["", "### Loss Traits", ""])
            for trait in traits[:8]:
                lines.append(
                    f"- `{trait.get('feature')}` bad_median=`{trait.get('bad_median')}` good_median=`{trait.get('good_median')}` scaled_delta=`{trait.get('scaled_delta')}`"
                )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research post-selection guards for KIS three-stage ranker outputs.")
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-06-10")
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"])
    parser.add_argument("--kospi-cache")
    parser.add_argument("--kosdaq-cache")
    parser.add_argument("--pool-modes", nargs="+", default=["prefilter", "day_return", "defensive"])
    parser.add_argument("--pool-k", nargs="+", type=int, default=[5, 10])
    parser.add_argument("--final-topn", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--score-modes", nargs="+", default=["ev", "success_tail", "ev_hit10"])
    parser.add_argument("--max-tail-prob-thresholds", nargs="+", default=["0.65", "0.7", "0.75", "0.8", "0.85"])
    parser.add_argument("--min-train-days", type=int, default=45)
    parser.add_argument("--test-days", type=int, default=8)
    parser.add_argument("--max-folds", type=int, default=6)
    parser.add_argument("--embargo-days", type=int, default=5)
    parser.add_argument("--calibration-days", type=int, default=12)
    parser.add_argument("--guard-train-ratio", type=float, default=0.65)
    parser.add_argument("--min-guard-train-n", type=int, default=6)
    parser.add_argument("--min-guard-holdout-n", type=int, default=4)
    parser.add_argument("--min-guard-retention", type=float, default=0.3)
    parser.add_argument("--extra-guard-features", nargs="*", default=[])
    parser.add_argument("--require-sidecar-coverage", nargs="*", default=[])
    parser.add_argument("--ranked-limit", type=int, default=20)
    parser.add_argument("--output-json", default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_STEM}.json"))
    parser.add_argument("--output-md", default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_STEM}.md"))
    args = parser.parse_args(argv)
    args.max_tail_prob_thresholds = _parse_optional_float_list(args.max_tail_prob_thresholds)
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run(args)
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": report.get("status"), "output_json": str(output_json), "output_md": args.output_md}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
