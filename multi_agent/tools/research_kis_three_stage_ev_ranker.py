#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "runtime_state" / "tmp" / "matplotlib"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.tradable_pnl import TradableCostModel, compute_net_return_pct
from multi_agent.tools.train_kis_historical_best_effort_suite import (
    BUY_PREMIUM_PCT,
    DEFAULT_END,
    DEFAULT_START,
    STOP_PCT,
    TARGET_PCT,
    _feature_sets,
    _filter_valid_labels,
    _frame_for_native,
    _load_market_frame,
    _walk_windows,
)

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover - optional dependency
    LGBMClassifier = None


REPORT_VERSION = "kis_three_stage_ev_ranker_research_v1"
DEFAULT_STEM = "kis_three_stage_ev_ranker_20260101_20260610"
DEFAULT_BASELINE_REPORT = (
    PROJECT_ROOT
    / "runtime_state/reports/learning/kis_historical_best_effort_suite_broad_topn_20260101_20260610.json"
)
TARGET_NET_PCT = compute_net_return_pct(TARGET_PCT, TradableCostModel()) or 4.601458
TARGET10_NET_PCT = compute_net_return_pct(10.0, TradableCostModel()) or 9.55


@dataclass(frozen=True)
class Config:
    pool: str
    pool_k: int
    score_mode: str

    def key(self) -> str:
        return f"{self.pool}|top{self.pool_k}|{self.score_mode}"


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
    rounded = _round(value, 8)
    return None if rounded is None else round(rounded * 100.0, 4)


def _safe_numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").astype(float)


def _normalize(values: pd.Series, default: float = 0.5) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    sample = numeric.dropna()
    if sample.empty:
        return pd.Series(default, index=values.index, dtype=float)
    lo = float(sample.quantile(0.05))
    hi = float(sample.quantile(0.95))
    if not math.isfinite(lo):
        lo = float(sample.min())
    if not math.isfinite(hi) or hi == lo:
        hi = lo + 1.0
    return ((numeric.clip(lo, hi) - lo) / (hi - lo)).fillna(default).astype(float)


def _score_family(frame: pd.DataFrame) -> Dict[str, pd.Series]:
    day_return = _safe_numeric(frame, "day_return_pct")
    volume = _safe_numeric(frame, "kis_daily_volume_ratio_20d").combine_first(_safe_numeric(frame, "volume_ratio"))
    r5 = _safe_numeric(frame, "kis_daily_return_5d_pct")
    close_location = _safe_numeric(frame, "kis_daily_close_location_pct", 50.0)
    whale = _safe_numeric(frame, "kis_whale_score")
    ticker_risk = _safe_numeric(frame, "close_failure_prior_ticker_risk_score", 50.0)
    theme_stop = _safe_numeric(frame, "close_failure_prior_theme_stop5_rate_pct", 50.0).combine_first(
        _safe_numeric(frame, "close_failure_prior_kis_theme_stop5_rate_pct", 50.0)
    )
    avg_mae_risk = -_safe_numeric(frame, "close_failure_prior_ticker_avg_mae_5d_pct", -8.0)

    composite = (
        _normalize(day_return) * 0.35
        + _normalize(volume) * 0.20
        + _normalize(r5) * 0.18
        + _normalize(close_location) * 0.12
        + _normalize(whale) * 0.08
        - _normalize(ticker_risk) * 0.15
    )
    defensive = composite - _normalize(theme_stop) * 0.20 - _normalize(avg_mae_risk) * 0.15
    return {
        "prefilter": _safe_numeric(frame, "kis_prefilter_selection_score"),
        "day_return": day_return,
        "coverage": _safe_numeric(frame, "feature_coverage_score"),
        "composite": composite,
        "defensive": defensive,
    }


def _select_pool(frame: pd.DataFrame, scores: Mapping[str, pd.Series], mode: str, top_k: int) -> pd.Index:
    if mode.startswith("union:"):
        pieces: List[Any] = []
        for name in mode.split(":", 1)[1].split("+"):
            pieces.extend(_select_pool(frame, scores, name, top_k).tolist())
        return pd.Index(pieces).drop_duplicates()
    score = scores.get(mode)
    if score is None:
        return pd.Index([])
    scored = frame[["base_trade_date", "ticker"]].copy()
    scored["_score"] = pd.to_numeric(score.reindex(frame.index), errors="coerce")
    scored = scored.dropna(subset=["_score"])
    if scored.empty:
        return pd.Index([])
    ordered = scored.sort_values(["base_trade_date", "_score", "ticker"], ascending=[True, False, True])
    return ordered.groupby("base_trade_date", sort=False).head(int(top_k)).index


def _top_per_day(frame: pd.DataFrame, score: pd.Series) -> pd.DataFrame:
    scored = frame.copy()
    scored["_rank_score"] = pd.to_numeric(score.reindex(frame.index), errors="coerce")
    scored = scored.dropna(subset=["_rank_score"])
    if scored.empty:
        return scored
    ordered = scored.sort_values(["base_trade_date", "_rank_score", "ticker"], ascending=[True, False, True])
    return ordered.groupby("base_trade_date", sort=False).head(1)


def _metric_summary(frame: pd.DataFrame, idx: pd.Index) -> Dict[str, Any]:
    sub = frame.loc[idx]
    if sub.empty:
        return {"n": 0, "active_days": 0}
    success = sub["_label_success"].astype(bool)
    target = sub["_label_target_hit"].astype(bool)
    hit10 = sub["_label_hit10"].astype(bool)
    tail = sub["_label_tail_breach"].astype(bool)
    close5 = sub["_close_5d"].astype(float)
    mfe5 = sub["_mfe_5d"].astype(float)
    mae5 = sub["_mae_5d"].astype(float)
    exit_returns = close5.copy()
    exit_returns.loc[success] = float(TARGET_NET_PCT)
    exit_returns.loc[tail] = -abs(STOP_PCT)
    dynamic_exit_returns = close5.copy()
    dynamic_exit_returns.loc[success] = float(TARGET_NET_PCT)
    dynamic_exit_returns.loc[success & hit10] = float(TARGET10_NET_PCT)
    dynamic_exit_returns.loc[tail] = -abs(STOP_PCT)
    return {
        "n": int(len(sub)),
        "active_days": int(sub["base_trade_date"].nunique()),
        "hit5_dd10_5d_pct": _pct(success.mean()),
        "target_hit_5d_pct": _pct(target.mean()),
        "hit10_5d_pct": _pct(hit10.mean()),
        "safe_hit10_5d_pct": _pct((success & hit10).mean()),
        "tail_breach_5d_pct": _pct(tail.mean()),
        "bad_path_pct": _pct((tail | close5.lt(0.0)).mean()),
        "avg_5d_pct": _round(close5.mean()),
        "avg_ordered_exit_5d_pct": _round(exit_returns.mean()),
        "avg_dynamic_exit_5d_pct": _round(dynamic_exit_returns.mean()),
        "avg_mfe_5d_pct": _round(mfe5.mean()),
        "avg_mae_5d_pct": _round(mae5.mean()),
        "min_min_low_5d_pct": _round(mae5.min()),
        "max_mfe_5d_pct": _round(mfe5.max()),
        "expected_binary_net_5d_pct": _round(success.mean() * TARGET_NET_PCT + (1.0 - success.mean()) * -abs(STOP_PCT)),
        "buy_premium_pct": BUY_PREMIUM_PCT,
        "target_net_pct": _round(TARGET_NET_PCT),
        "target10_net_pct": _round(TARGET10_NET_PCT),
    }


def _fit_classifier(train: pd.DataFrame, numeric: Sequence[str], target_column: str) -> Any:
    if LGBMClassifier is None:
        raise RuntimeError("lightgbm_unavailable")
    y = train[target_column].astype(int)
    if y.nunique() < 2:
        raise ValueError(f"single_class_target:{target_column}")
    model = LGBMClassifier(
        objective="binary",
        n_estimators=120,
        max_depth=4,
        num_leaves=18,
        learning_rate=0.045,
        subsample=0.85,
        colsample_bytree=0.85,
        class_weight="balanced",
        min_child_samples=40,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(_frame_for_native(train, numeric, [], backend="lightgbm"), y, categorical_feature="auto")
    return model


def _predict(model: Any, frame: pd.DataFrame, numeric: Sequence[str]) -> pd.Series:
    values = model.predict_proba(_frame_for_native(frame, numeric, [], backend="lightgbm"))[:, 1]
    return pd.Series(values, index=frame.index, dtype=float)


def _rank_score(score_mode: str, p_success: pd.Series, p_tail: pd.Series, p_hit10: pd.Series) -> pd.Series:
    if score_mode == "ev":
        return p_success * TARGET_NET_PCT - p_tail * abs(STOP_PCT)
    if score_mode == "success_tail":
        return p_success - p_tail * 1.8
    if score_mode == "ev_hit10":
        return p_success * TARGET_NET_PCT + p_hit10 * 1.5 - p_tail * abs(STOP_PCT)
    raise ValueError(f"unknown_score_mode:{score_mode}")


def _choose_threshold(calibration: pd.DataFrame, score: pd.Series) -> Tuple[float | None, Dict[str, Any]]:
    top = _top_per_day(calibration, score)
    if top.empty:
        return None, {"reason": "empty_calibration_top"}
    thresholds = sorted(set([float(top["_rank_score"].quantile(q)) for q in (0.0, 0.2, 0.4, 0.6, 0.75, 0.85, 0.9)] + [0.0]))
    best_threshold: float | None = None
    best_objective = -1e9
    best_metrics: Dict[str, Any] = {}
    for threshold in thresholds:
        selected = top[top["_rank_score"].ge(float(threshold))]
        metrics = _metric_summary(calibration, selected.index)
        if int(metrics.get("n") or 0) < 3:
            continue
        objective = (
            float(metrics.get("avg_ordered_exit_5d_pct") or -20.0) * 3.0
            + float(metrics.get("hit5_dd10_5d_pct") or 0.0) * 0.08
            - float(metrics.get("tail_breach_5d_pct") or 0.0) * 0.10
            + min(int(metrics.get("active_days") or 0), 12) * 0.02
        )
        if objective > best_objective:
            best_objective = objective
            best_threshold = float(threshold)
            best_metrics = metrics
    return best_threshold, {"objective": _round(best_objective), "metrics": best_metrics}


def _configs(pool_modes: Sequence[str], pool_k: Sequence[int], score_modes: Sequence[str]) -> List[Config]:
    return [Config(pool=pool, pool_k=int(k), score_mode=score) for pool in pool_modes for k in pool_k for score in score_modes]


def _baseline_metrics(path: Path, market: str) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    item = (payload.get("markets") or {}).get(market.upper()) if isinstance(payload.get("markets"), dict) else None
    best = item.get("best") if isinstance(item, dict) else None
    return best.get("metrics") if isinstance(best, dict) else None


def _market_report(
    *,
    market: str,
    start: str,
    end: str,
    cache_path: Path,
    baseline_report: Path,
    rank_metric: str,
    pool_modes: Sequence[str],
    pool_k: Sequence[int],
    score_modes: Sequence[str],
    min_train_days: int,
    test_days: int,
    max_folds: int,
    embargo_days: int,
    calibration_days: int,
) -> Dict[str, Any]:
    started = perf_counter()
    frame = _load_market_frame(cache_path, market)
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
    configs = _configs(pool_modes, pool_k, score_modes)
    selected_by_config: Dict[str, List[pd.Index]] = {cfg.key(): [] for cfg in configs}
    fold_rows: List[Dict[str, Any]] = []
    tested_days: List[str] = []

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
            fold_rows.append({"fold": window.fold, "skipped": True, "reason": str(exc)})
            continue

        p_success_cal = _predict(success_model, calibration, numeric)
        p_tail_cal = _predict(tail_model, calibration, numeric)
        p_hit10_cal = _predict(hit10_model, calibration, numeric)
        p_success_test = _predict(success_model, test, numeric)
        p_tail_test = _predict(tail_model, test, numeric)
        p_hit10_test = _predict(hit10_model, test, numeric)
        cal_pool_scores = _score_family(calibration)
        test_pool_scores = _score_family(test)
        tested_days.extend(window.test_days)
        fold_config_rows: List[Dict[str, Any]] = []

        for cfg in configs:
            cal_pool = _select_pool(calibration, cal_pool_scores, cfg.pool, cfg.pool_k)
            test_pool = _select_pool(test, test_pool_scores, cfg.pool, cfg.pool_k)
            if len(cal_pool) == 0 or len(test_pool) == 0:
                continue
            cal_score = _rank_score(cfg.score_mode, p_success_cal, p_tail_cal, p_hit10_cal).reindex(cal_pool)
            threshold, threshold_meta = _choose_threshold(calibration.loc[cal_pool], cal_score)
            if threshold is None:
                continue
            test_score = _rank_score(cfg.score_mode, p_success_test, p_tail_test, p_hit10_test).reindex(test_pool)
            test_top = _top_per_day(test.loc[test_pool], test_score)
            selected = test_top[test_top["_rank_score"].ge(float(threshold))]
            selected_by_config[cfg.key()].append(selected.index)
            fold_config_rows.append(
                {
                    "config": cfg.key(),
                    "threshold": _round(threshold),
                    "calibration": threshold_meta,
                    "test_metrics": _metric_summary(test, selected.index),
                }
            )

        fold_rows.append(
            {
                "fold": int(window.fold),
                "train_days": len(window.train_days),
                "calibration_days": len(cal_days),
                "test_days": len(window.test_days),
                "test_start": window.test_days[0] if window.test_days else None,
                "test_end": window.test_days[-1] if window.test_days else None,
                "configs_evaluated": len(fold_config_rows),
            }
        )

    ranked: List[Dict[str, Any]] = []
    unique_test_days = sorted(dict.fromkeys(tested_days))
    for cfg in configs:
        parts = selected_by_config[cfg.key()]
        if not parts:
            continue
        idx = parts[0]
        for part in parts[1:]:
            idx = idx.append(part)
        idx = idx.drop_duplicates()
        metrics = _metric_summary(frame, idx)
        metrics["coverage_test_days_pct"] = _pct((int(metrics.get("active_days") or 0) / len(unique_test_days)) if unique_test_days else 0.0)
        ranked.append({"config": cfg.__dict__, "metrics": metrics})
    ranked.sort(
        key=lambda row: (
            float((row.get("metrics") or {}).get(rank_metric) or -99.0),
            float((row.get("metrics") or {}).get("avg_ordered_exit_5d_pct") or -99.0),
            float((row.get("metrics") or {}).get("hit5_dd10_5d_pct") or 0.0),
            int((row.get("metrics") or {}).get("n") or 0),
        ),
        reverse=True,
    )

    baseline = _baseline_metrics(baseline_report, market)
    best = ranked[0] if ranked else None
    improvement: Dict[str, Any] = {}
    if best and baseline:
        best_metrics = best.get("metrics") or {}
        improvement = {
            "baseline_avg_ordered_exit_5d_pct": baseline.get("avg_ordered_exit_5d_pct"),
            "best_avg_ordered_exit_5d_pct": best_metrics.get("avg_ordered_exit_5d_pct"),
            "avg_ordered_exit_delta_pct": _round(
                float(best_metrics.get("avg_ordered_exit_5d_pct") or 0.0)
                - float(baseline.get("avg_ordered_exit_5d_pct") or 0.0)
            ),
            "best_avg_dynamic_exit_5d_pct": best_metrics.get("avg_dynamic_exit_5d_pct"),
            "dynamic_minus_fixed_exit_delta_pct": _round(
                float(best_metrics.get("avg_dynamic_exit_5d_pct") or 0.0)
                - float(best_metrics.get("avg_ordered_exit_5d_pct") or 0.0)
            ),
            "baseline_hit5_dd10_5d_pct": baseline.get("hit5_dd10_5d_pct"),
            "best_hit5_dd10_5d_pct": best_metrics.get("hit5_dd10_5d_pct"),
            "hit5_dd10_delta_pct": _round(
                float(best_metrics.get("hit5_dd10_5d_pct") or 0.0) - float(baseline.get("hit5_dd10_5d_pct") or 0.0)
            ),
        }

    return {
        "market": market,
        "cache_path": str(cache_path),
        "rows": int(len(frame)),
        "days": int(frame["base_trade_date"].nunique()),
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
        "folds": fold_rows,
        "baseline_best_metrics": baseline,
        "rank_metric": rank_metric,
        "improvement": improvement,
        "best": best,
        "ranked": ranked[:20],
        "elapsed_sec": _round(perf_counter() - started, 3),
    }


def _market_cache_path(market: str, start: str, end: str, override: str | None = None) -> Path:
    if override:
        return Path(override)
    return (
        PROJECT_ROOT
        / "runtime_state/reports/learning"
        / f"kis_historical_universe_prepared_{market.lower()}_{start.replace('-', '')}_{end.replace('-', '')}.pkl"
    )


def run(args: argparse.Namespace) -> Dict[str, Any]:
    reports = []
    input_paths = args.input_paths if isinstance(getattr(args, "input_paths", None), dict) else {}
    for market in args.markets:
        market_key = market.upper()
        reports.append(
            _market_report(
                market=market_key,
                start=args.start,
                end=args.end,
                cache_path=_market_cache_path(market_key, args.start, args.end, input_paths.get(market_key)),
                baseline_report=Path(args.baseline_report),
                rank_metric=args.rank_metric,
                pool_modes=args.pool_modes,
                pool_k=args.pool_k,
                score_modes=args.score_modes,
                min_train_days=args.min_train_days,
                test_days=args.test_days,
                max_folds=args.max_folds,
                embargo_days=args.embargo_days,
                calibration_days=args.calibration_days,
            )
        )
    improved = [
        report
        for report in reports
        if float((report.get("improvement") or {}).get("avg_ordered_exit_delta_pct") or 0.0) > 0.0
    ]
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "status": "improved_shadow_research" if improved else "no_improvement",
        "objective": "Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.",
        "validation": "walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.",
        "assumptions": {
            "buy_premium_pct": BUY_PREMIUM_PCT,
            "target_pct": TARGET_PCT,
            "stop_pct": STOP_PCT,
            "target_net_pct_after_costs": _round(TARGET_NET_PCT),
            "target10_net_pct_after_costs": _round(TARGET10_NET_PCT),
            "success_label": "buy_premium_target_hit_5d == true AND buy_premium_min_low_return_5d_pct >= -10",
            "tail_breach_label": "buy_premium_min_low_return_5d_pct < -10",
        },
        "baseline_report": str(args.baseline_report),
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
        "# KIS Three-Stage EV Ranker Research",
        "",
        f"- status: `{report.get('status')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- objective: `{report.get('objective')}`",
        f"- validation: `{report.get('validation')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- rank_metric: `{(report.get('markets') or [{}])[0].get('rank_metric') if report.get('markets') else None}`",
        "",
    ]
    for market_report in report.get("markets", []):
        best = market_report.get("best") or {}
        metrics = best.get("metrics") or {}
        config = best.get("config") or {}
        improvement = market_report.get("improvement") or {}
        lines.extend(
            [
                f"## {market_report.get('market')}",
                "",
                f"- rows/days: `{market_report.get('rows')}` / `{market_report.get('days')}`",
                f"- best_config: pool=`{config.get('pool')}` pool_k=`{config.get('pool_k')}` score=`{config.get('score_mode')}`",
                f"- avg_exit improvement: `{improvement.get('baseline_avg_ordered_exit_5d_pct')}` -> `{improvement.get('best_avg_ordered_exit_5d_pct')}` (delta `{improvement.get('avg_ordered_exit_delta_pct')}`)",
                f"- dynamic_exit: `{metrics.get('avg_dynamic_exit_5d_pct')}` (fixed 대비 delta `{improvement.get('dynamic_minus_fixed_exit_delta_pct')}`)",
                f"- hit5_dd10: `{improvement.get('baseline_hit5_dd10_5d_pct')}` -> `{improvement.get('best_hit5_dd10_5d_pct')}` (delta `{improvement.get('hit5_dd10_delta_pct')}`)",
                f"- best metrics: n=`{metrics.get('n')}`, active_days=`{metrics.get('active_days')}`, hit5_dd10=`{metrics.get('hit5_dd10_5d_pct')}`, hit10=`{metrics.get('hit10_5d_pct')}`, safe_hit10=`{metrics.get('safe_hit10_5d_pct')}`, tail=`{metrics.get('tail_breach_5d_pct')}`, bad_path=`{metrics.get('bad_path_pct')}`, avg_exit=`{metrics.get('avg_ordered_exit_5d_pct')}`, dynamic_exit=`{metrics.get('avg_dynamic_exit_5d_pct')}`, min_low=`{metrics.get('min_min_low_5d_pct')}`",
                "",
                "| rank | pool | pool_k | score | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |",
                "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for rank, row in enumerate((market_report.get("ranked") or [])[:10], start=1):
            row_config = row.get("config") or {}
            row_metrics = row.get("metrics") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(rank),
                        str(row_config.get("pool")),
                        _fmt(row_config.get("pool_k")),
                        str(row_config.get("score_mode")),
                        _fmt(row_metrics.get("n")),
                        _fmt(row_metrics.get("active_days")),
                        _fmt(row_metrics.get("coverage_test_days_pct")),
                        _fmt(row_metrics.get("hit5_dd10_5d_pct")),
                        _fmt(row_metrics.get("hit10_5d_pct")),
                        _fmt(row_metrics.get("safe_hit10_5d_pct")),
                        _fmt(row_metrics.get("tail_breach_5d_pct")),
                        _fmt(row_metrics.get("bad_path_pct")),
                        _fmt(row_metrics.get("avg_ordered_exit_5d_pct")),
                        _fmt(row_metrics.get("avg_dynamic_exit_5d_pct")),
                        _fmt(row_metrics.get("min_min_low_5d_pct")),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research a three-stage KIS touch5_dd10 expected-value ranker.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"])
    parser.add_argument(
        "--pool-modes",
        nargs="+",
        default=[
            "prefilter",
            "day_return",
            "coverage",
            "composite",
            "defensive",
            "union:day_return+prefilter+coverage",
            "union:day_return+composite+defensive",
        ],
    )
    parser.add_argument("--pool-k", nargs="+", type=int, default=[10, 20, 50, 100])
    parser.add_argument("--score-modes", nargs="+", default=["ev", "success_tail", "ev_hit10"])
    parser.add_argument("--min-train-days", type=int, default=45)
    parser.add_argument("--test-days", type=int, default=8)
    parser.add_argument("--max-folds", type=int, default=6)
    parser.add_argument("--embargo-days", type=int, default=5)
    parser.add_argument("--calibration-days", type=int, default=12)
    parser.add_argument("--baseline-report", default=str(DEFAULT_BASELINE_REPORT))
    parser.add_argument(
        "--rank-metric",
        choices=["avg_ordered_exit_5d_pct", "avg_dynamic_exit_5d_pct", "hit5_dd10_5d_pct"],
        default="avg_ordered_exit_5d_pct",
    )
    parser.add_argument("--output-json", default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_STEM}.json"))
    parser.add_argument("--output-md", default=str(PROJECT_ROOT / f"runtime_state/reports/learning/{DEFAULT_STEM}.md"))
    parser.add_argument("--input-path", action="append", default=[], help="MARKET=path override for prepared cache.")
    args = parser.parse_args(argv)
    args.input_paths = {}
    for raw in args.input_path:
        if "=" not in str(raw):
            raise ValueError("--input-path must be MARKET=path")
        market, path = str(raw).split("=", 1)
        args.input_paths[market.strip().upper()] = path.strip()
    return args


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
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "output_json": str(output_json),
                "output_md": args.output_md,
                "markets": [
                    {
                        "market": item.get("market"),
                        "best": (item.get("best") or {}).get("metrics"),
                        "improvement": item.get("improvement"),
                    }
                    for item in report.get("markets", [])
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
