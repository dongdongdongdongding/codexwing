#!/usr/bin/env python3
"""Search KIS touch5/dd10 selection rules for period-stable candidates.

This is a rule-stability layer on top of the existing fold-separated KIS model.
It trains once per market on actual sidecar rows, sweeps stage-3 selection rules,
then replays each selected rule across available monthly and rolling two-month
periods.  It does not create or use dummy data.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate
from multi_agent.tools.sweep_kis_sidecar_thresholds import (
    _fit_predict_folds,
    _score_predictions,
    _selection_rule,
)
from multi_agent.tools.train_scan_universe_admission_challenger import (
    LABEL_SPECS,
    feature_sets,
    kis_presence_mask,
    label_series,
    metrics,
    quality_score,
    tail_safe_series,
    top_indices_by_run,
    usable_features,
)


REPORT_VERSION = "kis_touch5_stability_search_v1"
REPORT_DIR = ROOT / "runtime_state/reports/learning"
DEFAULT_PREPARED_CACHE = (
    REPORT_DIR / "scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_OUTPUT = REPORT_DIR / "kis_touch5_stability_search_20260613.json"
REQUIRED_MONTHS = ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")
REQUIRED_MARKETS = ("KOSPI", "KOSDAQ")
LABEL_NAME = "touch5_dd10_5d"
FEATURE_SET = "kis_sidecar_failure_risk_augmented"


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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _parse_csv(raw: str) -> List[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def _parse_float_list(raw: str, *, include_none: bool = False) -> List[float | None]:
    values: List[float | None] = [None] if include_none else []
    for item in _parse_csv(raw):
        if item.lower() in {"none", "null", "na", "-"}:
            if None not in values:
                values.append(None)
            continue
        values.append(float(item))
    return values


def _parse_int_list(raw: str) -> List[int]:
    return [int(item) for item in _parse_csv(raw)]


def _normalize_dates(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    out["_stability_month"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.to_period("M").astype(str)
    if "run_id" not in out.columns:
        out["run_id"] = out["trade_date"]
    out["run_id"] = out["run_id"].fillna(out["trade_date"]).astype(str)
    out["market"] = out.get("market", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    return out


def _slice_specs(months: Sequence[str]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for month in months:
        specs.append({"name": month, "type": "monthly", "months": [month]})
    for first, second in zip(months, months[1:]):
        specs.append({"name": f"{first}..{second}", "type": "rolling_2m", "months": [first, second]})
    return specs


def _outcome_pass(row: Mapping[str, Any], *, min_hit5: float, min_low: float) -> bool:
    metrics_row = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    hit = float(metrics_row.get("hit5_dd10_5d_pct") or 0.0)
    low = float(metrics_row.get("min_min_low_5d_pct") or -999.0)
    return hit >= float(min_hit5) and low >= float(min_low)


def _rule_selected_indices(
    scoped: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    topn: int,
    score_mode: str,
    prob_threshold: float | None,
    tail_threshold: float | None,
) -> pd.Index:
    candidate_idx = predictions.index
    if prob_threshold is not None:
        candidate_idx = candidate_idx.intersection(predictions.index[predictions["prob"].ge(float(prob_threshold))])
    if tail_threshold is not None:
        candidate_idx = candidate_idx.intersection(predictions.index[predictions["tail_prob"].ge(float(tail_threshold))])
    if candidate_idx.empty:
        return pd.Index([])
    score = _score_predictions(predictions, score_mode)
    return top_indices_by_run(scoped.loc[candidate_idx], score.loc[candidate_idx], int(topn))


def _slice_metrics(
    scoped: pd.DataFrame,
    selected: pd.Index,
    label: pd.Series,
    spec: Mapping[str, Any],
    *,
    min_selected: int,
    min_active_days: int,
    min_hit5: float,
    min_low: float,
) -> Dict[str, Any]:
    month_mask = scoped["_stability_month"].isin(list(spec.get("months") or []))
    scoped_idx = scoped.index[month_mask]
    selected_idx = selected.intersection(scoped_idx)
    if selected_idx.empty:
        return {
            "slice": spec.get("name"),
            "slice_type": spec.get("type"),
            "months": list(spec.get("months") or []),
            "status": "no_selected_rows",
            "pass": False,
            "metrics": {"n": 0, "active_days": 0, "active_runs": 0},
        }
    result_metrics = metrics(scoped, selected_idx, label)
    reasons = []
    if int(result_metrics.get("n") or 0) < int(min_selected):
        reasons.append(f"n_lt_{int(min_selected)}")
    if int(result_metrics.get("active_days") or 0) < int(min_active_days):
        reasons.append(f"active_days_lt_{int(min_active_days)}")
    if float(result_metrics.get("hit5_dd10_5d_pct") or 0.0) < float(min_hit5):
        reasons.append(f"hit5_dd10_lt_{min_hit5:g}")
    if float(result_metrics.get("min_min_low_5d_pct") or -999.0) < float(min_low):
        reasons.append(f"min_low_lt_{min_low:g}")
    return {
        "slice": spec.get("name"),
        "slice_type": spec.get("type"),
        "months": list(spec.get("months") or []),
        "status": "ok" if not reasons else "failed",
        "pass": not reasons,
        "reasons": reasons,
        "metrics": result_metrics,
    }


def _compact_candidate(row: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "market",
        "selection_rule",
        "score_mode",
        "topn",
        "prob_threshold",
        "tail_risk_prob_threshold",
        "stability_status",
        "stability_score",
        "period_pass_count",
        "period_result_count",
        "monthly_pass_count",
        "monthly_result_count",
        "rolling_2m_pass_count",
        "rolling_2m_result_count",
        "gate_status",
        "production_ready",
        "shadow_display_allowed",
        "production_blocking_reasons",
        "metrics",
        "worst_period",
        "best_period",
        "selected_month_coverage",
        "coverage_blockers",
    )
    return {key: row.get(key) for key in keys if key in row}


def _candidate_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics_row = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    return (
        0 if row.get("stability_status") == "period_stable_candidate" else 1,
        -int(((row.get("selected_month_coverage") or {}).get("selected_month_count")) or 0),
        -int(row.get("period_pass_count") or 0),
        -float(row.get("stability_score") or -1e9),
        -float(metrics_row.get("hit5_dd10_5d_pct") or 0.0),
        -float(metrics_row.get("avg_5d_pct") or -999.0),
        -float(metrics_row.get("min_min_low_5d_pct") or -999.0),
        -int(metrics_row.get("active_days") or 0),
        -int(metrics_row.get("n") or 0),
    )


def _selected_month_coverage(scoped: pd.DataFrame, selected: pd.Index) -> Dict[str, Any]:
    if selected.empty:
        return {
            "selected_months": [],
            "selected_month_count": 0,
            "month_rows": {},
            "max_month_share_pct": None,
        }
    sub = scoped.loc[selected].copy()
    grouped = sub.groupby("_stability_month", dropna=False)
    month_rows = {
        str(month): {
            "n": int(len(group)),
            "active_days": int(group["trade_date"].nunique()) if "trade_date" in group.columns else 0,
            "active_runs": int(group["run_id"].nunique()) if "run_id" in group.columns else 0,
        }
        for month, group in grouped
    }
    total = max(1, int(len(sub)))
    max_month_n = max((row["n"] for row in month_rows.values()), default=0)
    return {
        "selected_months": sorted(month_rows.keys()),
        "selected_month_count": int(len(month_rows)),
        "month_rows": dict(sorted(month_rows.items())),
        "max_month_share_pct": _round(max_month_n / total * 100.0),
    }


def _scope_market(data: pd.DataFrame, *, market: str) -> Dict[str, Any]:
    label_spec = next(spec for spec in LABEL_SPECS if spec.name == LABEL_NAME)
    label, valid = label_series(data, label_spec)
    tail_label, tail_valid = tail_safe_series(data)
    scoped = data.loc[
        valid & tail_valid & data["market"].eq(market) & kis_presence_mask(data, FEATURE_SET)
    ].copy()
    y = label.loc[scoped.index].astype(int)
    y_tail = tail_label.loc[scoped.index].astype(int)
    numeric, categorical = feature_sets(data)[FEATURE_SET]
    numeric, categorical = usable_features(scoped, numeric, categorical)
    return {
        "scoped": scoped,
        "label": label,
        "y": y,
        "y_tail": y_tail,
        "numeric": numeric,
        "categorical": categorical,
    }


def _evaluate_market(
    data: pd.DataFrame,
    *,
    market: str,
    months: Sequence[str],
    model_name: str,
    topns: Sequence[int],
    score_modes: Sequence[str],
    prob_thresholds: Sequence[float | None],
    tail_thresholds: Sequence[float | None],
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
    min_scope_rows: int,
    min_scope_days: int,
    min_period_selected: int,
    min_period_active_days: int,
    min_selected_months: int,
    min_hit5: float,
    min_low: float,
    top_limit: int,
    progress: bool,
) -> Dict[str, Any]:
    scoped_payload = _scope_market(data, market=market)
    scoped: pd.DataFrame = scoped_payload["scoped"]
    y: pd.Series = scoped_payload["y"]
    y_tail: pd.Series = scoped_payload["y_tail"]
    label: pd.Series = scoped_payload["label"]
    numeric = scoped_payload["numeric"]
    categorical = scoped_payload["categorical"]
    scope = {
        "market": market,
        "rows": int(len(scoped)),
        "unique_days": int(scoped["trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
        "unique_runs": int(scoped["run_id"].nunique()) if "run_id" in scoped.columns else 0,
        "months_present": sorted(scoped["_stability_month"].dropna().astype(str).unique().tolist()),
        "positive_rate_pct": _round(float(y.mean() * 100.0)) if len(y) else None,
        "tail_safe_rate_pct": _round(float(y_tail.mean() * 100.0)) if len(y_tail) else None,
        "usable_numeric": int(len(numeric)),
        "usable_categorical": int(len(categorical)),
        "required_rows": int(max(min_scope_rows, min_train_rows + min_test_rows)),
        "required_days": int(max(min_scope_days, min_train_days + test_days)),
    }
    if (
        scope["rows"] < scope["required_rows"]
        or scope["unique_days"] < scope["required_days"]
        or len(y) == 0
        or y.nunique() < 2
        or len(y_tail) == 0
        or y_tail.nunique() < 2
    ):
        return {"market": market, "status": "skipped_scope_not_trainable", "scope": scope, "candidates": []}
    fold_payload = _fit_predict_folds(
        scoped,
        y=y,
        y_tail=y_tail,
        numeric=numeric,
        categorical=categorical,
        model_name=model_name,
        min_train_rows=min_train_rows,
        min_test_rows=min_test_rows,
        min_train_days=min_train_days,
        test_days=test_days,
        max_folds=max_folds,
        need_tail=True,
        progress=progress,
    )
    predictions = fold_payload.pop("predictions")
    if predictions.empty:
        return {"market": market, "status": "skipped_no_predictions", "scope": scope, "fold_meta": fold_payload, "candidates": []}
    period_specs = [
        spec
        for spec in _slice_specs(months)
        if int(scoped["_stability_month"].isin(spec["months"]).sum()) >= int(min_scope_rows)
    ]
    candidates: List[Dict[str, Any]] = []
    for topn in topns:
        for score_mode in score_modes:
            for prob_threshold in prob_thresholds:
                for tail_threshold in tail_thresholds:
                    selected = _rule_selected_indices(
                        scoped,
                        predictions,
                        topn=int(topn),
                        score_mode=str(score_mode),
                        prob_threshold=prob_threshold,
                        tail_threshold=tail_threshold,
                    )
                    if selected.empty:
                        continue
                    result_metrics = metrics(scoped, selected, label)
                    coverage = _selected_month_coverage(scoped, selected)
                    coverage_blockers = []
                    if int(coverage.get("selected_month_count") or 0) < int(min_selected_months):
                        coverage_blockers.append(f"selected_months_lt_{int(min_selected_months)}")
                    identity = {
                        "market": market,
                        "label": LABEL_NAME,
                        "feature_set": FEATURE_SET,
                        "model": model_name,
                        "score_mode": score_mode,
                        "selection_rule": _selection_rule(int(topn), prob_threshold, tail_threshold, str(score_mode)),
                    }
                    gate = evaluate_kis_model_gate(identity=identity, metrics=result_metrics, market=market)
                    period_results = [
                        _slice_metrics(
                            scoped,
                            selected,
                            label,
                            spec,
                            min_selected=min_period_selected,
                            min_active_days=min_period_active_days,
                            min_hit5=min_hit5,
                            min_low=min_low,
                        )
                        for spec in period_specs
                    ]
                    monthly = [row for row in period_results if row.get("slice_type") == "monthly"]
                    rolling = [row for row in period_results if row.get("slice_type") == "rolling_2m"]
                    passed = [row for row in period_results if row.get("pass")]
                    failed = [row for row in period_results if not row.get("pass")]
                    worst = sorted(
                        period_results,
                        key=lambda row: (
                            float((row.get("metrics") or {}).get("hit5_dd10_5d_pct") or -1.0),
                            float((row.get("metrics") or {}).get("min_min_low_5d_pct") or -999.0),
                            int((row.get("metrics") or {}).get("n") or 0),
                        ),
                    )[0] if period_results else {}
                    best = sorted(
                        period_results,
                        key=lambda row: (
                            -float((row.get("metrics") or {}).get("hit5_dd10_5d_pct") or -1.0),
                            -float((row.get("metrics") or {}).get("avg_5d_pct") or -999.0),
                            -int((row.get("metrics") or {}).get("n") or 0),
                        ),
                    )[0] if period_results else {}
                    pass_ratio = (len(passed) / len(period_results)) if period_results else 0.0
                    hit = float(result_metrics.get("hit5_dd10_5d_pct") or 0.0)
                    avg5 = float(result_metrics.get("avg_5d_pct") or -999.0)
                    low = float(result_metrics.get("min_min_low_5d_pct") or -999.0)
                    stability_score = (
                        (pass_ratio * 500.0)
                        + (hit * 2.0)
                        + max(-100.0, avg5)
                        + max(-100.0, low)
                        + min(100.0, float(result_metrics.get("active_days") or 0) * 2.0)
                        + min(100.0, float(result_metrics.get("n") or 0))
                    )
                    if len(period_results) and len(passed) == len(period_results):
                        stability_status = (
                            "period_stable_candidate"
                            if not coverage_blockers
                            else "period_pass_single_month_candidate"
                        )
                    elif passed:
                        stability_status = "partial_period_candidate"
                    else:
                        stability_status = "unstable_candidate"
                    candidates.append(
                        {
                            **identity,
                            "topn": int(topn),
                            "prob_threshold": prob_threshold,
                            "tail_risk_prob_threshold": tail_threshold,
                            "metrics": result_metrics,
                            "gate_status": gate.get("status"),
                            "production_ready": bool(gate.get("production_ready")),
                            "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
                            "production_blocking_reasons": gate.get("production_blocking_reasons") or [],
                            "kis_model_gate": gate,
                            "quality_score": _round(quality_score(result_metrics, topn=int(topn), label_name=LABEL_NAME)),
                            "period_pass_count": int(len(passed)),
                            "period_fail_count": int(len(failed)),
                            "period_result_count": int(len(period_results)),
                            "monthly_pass_count": int(sum(1 for row in monthly if row.get("pass"))),
                            "monthly_result_count": int(len(monthly)),
                            "rolling_2m_pass_count": int(sum(1 for row in rolling if row.get("pass"))),
                            "rolling_2m_result_count": int(len(rolling)),
                            "selected_month_coverage": coverage,
                            "coverage_blockers": coverage_blockers,
                            "stability_status": stability_status,
                            "stability_score": _round(stability_score),
                            "worst_period": worst,
                            "best_period": best,
                            "period_results": period_results,
                        }
                    )
    candidates.sort(key=_candidate_sort_key)
    production_ready = [row for row in candidates if row.get("production_ready")]
    period_stable = [row for row in candidates if row.get("stability_status") == "period_stable_candidate"]
    shadow_period_stable = [row for row in period_stable if row.get("shadow_display_allowed")]
    return {
        "market": market,
        "status": "ok",
        "scope": scope,
        "fold_meta": fold_payload,
        "period_specs": period_specs,
        "evaluated_candidates": int(len(candidates)),
        "production_ready_count": int(len(production_ready)),
        "period_stable_count": int(len(period_stable)),
        "shadow_period_stable_count": int(len(shadow_period_stable)),
        "top_candidates": [_compact_candidate(row) for row in candidates[:top_limit]],
        "period_stable_top": [_compact_candidate(row) for row in period_stable[:top_limit]],
        "shadow_period_stable_top": [_compact_candidate(row) for row in shadow_period_stable[:top_limit]],
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    cache_path = Path(args.prepared_cache)
    if not cache_path.exists():
        raise FileNotFoundError(cache_path)
    data = pd.read_pickle(cache_path)
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"prepared cache is not a DataFrame: {cache_path}")
    data = _normalize_dates(data)
    months = _parse_csv(args.months) or list(REQUIRED_MONTHS)
    markets = _parse_csv(args.markets) or list(REQUIRED_MARKETS)
    topns = _parse_int_list(args.topns)
    score_modes = _parse_csv(args.score_modes)
    prob_thresholds = _parse_float_list(args.prob_thresholds, include_none=True)
    tail_thresholds = _parse_float_list(args.tail_thresholds, include_none=True)
    market_reports = {
        market: _evaluate_market(
            data,
            market=market,
            months=months,
            model_name=args.model,
            topns=topns,
            score_modes=score_modes,
            prob_thresholds=prob_thresholds,
            tail_thresholds=tail_thresholds,
            min_train_rows=int(args.min_train_rows),
            min_test_rows=int(args.min_test_rows),
            min_train_days=int(args.min_train_days),
            test_days=int(args.test_days),
            max_folds=int(args.max_folds),
            min_scope_rows=int(args.min_scope_rows),
            min_scope_days=int(args.min_scope_days),
            min_period_selected=int(args.min_period_selected),
            min_period_active_days=int(args.min_period_active_days),
            min_selected_months=int(args.min_selected_months),
            min_hit5=float(args.min_hit5),
            min_low=float(args.min_low),
            top_limit=int(args.top_limit),
            progress=bool(args.progress),
        )
        for market in markets
    }
    missing_months = [
        month for month in months if month not in set(data["_stability_month"].dropna().astype(str).unique().tolist())
    ]
    sparse_months = []
    for month in months:
        if month in missing_months:
            continue
        month_frame = data[data["_stability_month"].eq(month)]
        if len(month_frame) < int(args.min_scope_rows) or any(
            len(month_frame[month_frame["market"].eq(market)]) == 0 for market in REQUIRED_MARKETS
        ):
            sparse_months.append(month)
    production_ready = all(
        int((market_reports.get(market) or {}).get("production_ready_count") or 0) > 0 for market in markets
    )
    both_market_period_stable = all(
        int((market_reports.get(market) or {}).get("period_stable_count") or 0) > 0 for market in markets
    )
    status = (
        "production_candidate_found"
        if production_ready and both_market_period_stable and not missing_months and not sparse_months
        else "period_stable_shadow_candidates_found"
        if both_market_period_stable
        else "no_period_stable_both_market_candidate"
    )
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "prepared_cache": _rel(cache_path),
        "data_profile": {
            "rows": int(len(data)),
            "date_min": str(pd.to_datetime(data["trade_date"], errors="coerce").dropna().min().date()) if len(data) else None,
            "date_max": str(pd.to_datetime(data["trade_date"], errors="coerce").dropna().max().date()) if len(data) else None,
            "months_present": sorted(data["_stability_month"].dropna().astype(str).unique().tolist()),
            "required_months": months,
            "missing_actual_months": missing_months,
            "sparse_actual_months": sparse_months,
        },
        "evaluation_contract": {
            "label": LABEL_NAME,
            "feature_set": FEATURE_SET,
            "model": args.model,
            "buy_premium_pct": 2.0,
            "win_definition": "5거래일 내 +5% 터치 and 5거래일 저점 -10% 이상 방어",
            "validation_mode": "fold_predictions_rule_sweep_with_period_replay",
            "topns": topns,
            "score_modes": score_modes,
            "prob_thresholds": prob_thresholds,
            "tail_thresholds": tail_thresholds,
            "min_period_selected": int(args.min_period_selected),
            "min_period_active_days": int(args.min_period_active_days),
            "min_selected_months": int(args.min_selected_months),
            "min_hit5": float(args.min_hit5),
            "min_low": float(args.min_low),
        },
        "decision": {
            "status": status,
            "production_replacement_ready": bool(status == "production_candidate_found"),
            "period_stable_both_market_candidate": bool(both_market_period_stable),
            "missing_or_sparse_actual_months": sorted(set(missing_months + sparse_months)),
            "recommended_action": (
                "keep KIS candidates in shadow; continue backfill and forward validation"
                if status != "production_candidate_found"
                else "human review for controlled production replacement"
            ),
        },
        "markets": market_reports,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    profile = report.get("data_profile") if isinstance(report.get("data_profile"), Mapping) else {}
    lines = [
        "# KIS Touch5 Stability Search",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- decision: `{decision.get('status')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}` rows=`{profile.get('rows')}` date=`{profile.get('date_min')}`..`{profile.get('date_max')}`",
        f"- missing_or_sparse_actual_months: `{decision.get('missing_or_sparse_actual_months')}`",
        "",
        "## Market Summary",
        "| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    markets = report.get("markets") if isinstance(report.get("markets"), Mapping) else {}
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        top = (row.get("top_candidates") or [{}])[0] if isinstance(row.get("top_candidates"), list) and row.get("top_candidates") else {}
        metrics_row = top.get("metrics") if isinstance(top.get("metrics"), Mapping) else {}
        lines.append(
            f"| {market} | {row.get('evaluated_candidates')} | {row.get('production_ready_count')} | "
            f"{row.get('period_stable_count')} | {row.get('shadow_period_stable_count')} | "
            f"{top.get('selection_rule')} | {metrics_row.get('hit5_dd10_5d_pct')} | "
            f"{metrics_row.get('avg_5d_pct')} | {metrics_row.get('min_min_low_5d_pct')} |"
        )
    lines.extend(["", "## Period Stable Top"])
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        lines.append(f"### {market}")
        stable = row.get("period_stable_top") if isinstance(row.get("period_stable_top"), list) else []
        if not stable:
            lines.append("- none")
            continue
        for idx, candidate in enumerate(stable[:5], start=1):
            metrics_row = candidate.get("metrics") if isinstance(candidate.get("metrics"), Mapping) else {}
            worst = candidate.get("worst_period") if isinstance(candidate.get("worst_period"), Mapping) else {}
            worst_metrics = worst.get("metrics") if isinstance(worst.get("metrics"), Mapping) else {}
            coverage = candidate.get("selected_month_coverage") if isinstance(candidate.get("selected_month_coverage"), Mapping) else {}
            lines.append(
                f"{idx}. `{candidate.get('selection_rule')}` status=`{candidate.get('stability_status')}` "
                f"gate=`{candidate.get('gate_status')}` pass=`{candidate.get('period_pass_count')}/{candidate.get('period_result_count')}` "
                f"n=`{metrics_row.get('n')}` days=`{metrics_row.get('active_days')}` "
                f"hit5=`{metrics_row.get('hit5_dd10_5d_pct')}` avg5=`{metrics_row.get('avg_5d_pct')}` "
                f"min_low=`{metrics_row.get('min_min_low_5d_pct')}` worst=`{worst.get('slice')}` "
                f"worst_hit5=`{worst_metrics.get('hit5_dd10_5d_pct')}` "
                f"selected_months=`{coverage.get('selected_months')}`"
            )
    lines.extend(["", "## Best Overall"])
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        lines.append(f"### {market}")
        for idx, candidate in enumerate((row.get("top_candidates") or [])[:5], start=1):
            if not isinstance(candidate, Mapping):
                continue
            metrics_row = candidate.get("metrics") if isinstance(candidate.get("metrics"), Mapping) else {}
            worst = candidate.get("worst_period") if isinstance(candidate.get("worst_period"), Mapping) else {}
            worst_metrics = worst.get("metrics") if isinstance(worst.get("metrics"), Mapping) else {}
            coverage = candidate.get("selected_month_coverage") if isinstance(candidate.get("selected_month_coverage"), Mapping) else {}
            lines.append(
                f"{idx}. `{candidate.get('selection_rule')}` status=`{candidate.get('stability_status')}` "
                f"pass=`{candidate.get('period_pass_count')}/{candidate.get('period_result_count')}` "
                f"n=`{metrics_row.get('n')}` days=`{metrics_row.get('active_days')}` "
                f"hit5=`{metrics_row.get('hit5_dd10_5d_pct')}` avg5=`{metrics_row.get('avg_5d_pct')}` "
                f"min_low=`{metrics_row.get('min_min_low_5d_pct')}` worst=`{worst.get('slice')}` "
                f"worst_hit5=`{worst_metrics.get('hit5_dd10_5d_pct')}` "
                f"selected_months=`{coverage.get('selected_months')}` "
                f"coverage_blockers=`{candidate.get('coverage_blockers')}` "
                f"blockers=`{candidate.get('production_blocking_reasons')}`"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--markets", default=",".join(REQUIRED_MARKETS))
    parser.add_argument("--months", default=",".join(REQUIRED_MONTHS))
    parser.add_argument("--model", default="lightgbm")
    parser.add_argument("--topns", default="1,2,3,5")
    parser.add_argument("--score-modes", default="prob,prob_plus_tail,prob_tail_margin,tail,tail_plus_prob,ev,ev_strict")
    parser.add_argument("--prob-thresholds", default="none,0.2,0.3,0.5,0.65,0.75,0.8,0.9")
    parser.add_argument("--tail-thresholds", default="none,0.6,0.75,0.85,0.9,0.95")
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=1)
    parser.add_argument("--min-train-days", type=int, default=7)
    parser.add_argument("--test-days", type=int, default=1)
    parser.add_argument("--max-folds", type=int, default=8)
    parser.add_argument("--min-scope-rows", type=int, default=1200)
    parser.add_argument("--min-scope-days", type=int, default=8)
    parser.add_argument("--min-period-selected", type=int, default=2)
    parser.add_argument("--min-period-active-days", type=int, default=1)
    parser.add_argument("--min-selected-months", type=int, default=2)
    parser.add_argument("--min-hit5", type=float, default=73.0)
    parser.add_argument("--min-low", type=float, default=-10.0)
    parser.add_argument("--top-limit", type=int, default=12)
    parser.add_argument("--progress", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    output = Path(args.output)
    write_report(report, output)
    print(
        json.dumps(
            {
                "status": (report.get("decision") or {}).get("status"),
                "production_replacement_ready": (report.get("decision") or {}).get("production_replacement_ready"),
                "output": _rel(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
