#!/usr/bin/env python3
"""Fast threshold sweep for KIS sidecar admission models.

The full challenger trainer retrains for every probability/tail threshold.
This tool trains once per market/fold/model/feature set, stores the fold
probabilities in memory, and sweeps selection thresholds against the same
out-of-sample predictions.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_model_gate import evaluate_kis_model_gate
from multi_agent.tools.train_scan_universe_admission_challenger import (
    LABEL_SPECS,
    feature_sets,
    kis_presence_mask,
    label_series,
    metrics,
    model_candidate,
    preprocessor,
    quality_score,
    split_windows,
    tail_safe_series,
    top_indices_by_run,
    usable_features,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return round(float(value), 6)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _parse_float_list(raw: str, *, include_none: bool = False) -> List[float | None]:
    out: List[float | None] = [None] if include_none else []
    for item in str(raw or "").split(","):
        text = item.strip()
        if not text:
            continue
        if text.lower() in {"none", "null", "na", "-"}:
            if None not in out:
                out.append(None)
            continue
        out.append(float(text))
    return out or ([None] if include_none else [])


def _parse_int_list(raw: str) -> List[int]:
    return [int(item.strip()) for item in str(raw or "").split(",") if item.strip()]


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _selection_rule(topn: int, prob_threshold: float | None, tail_threshold: float | None) -> str:
    parts = [f"top{int(topn)}"]
    if prob_threshold is not None:
        parts.append(f"p{prob_threshold:.3g}".replace(".", "p"))
    if tail_threshold is not None:
        parts.append(f"tail{tail_threshold:.3g}".replace(".", "p"))
    return "_".join(parts)


def _feature_frame(frame: pd.DataFrame, columns: Sequence[str], categorical: Sequence[str]) -> pd.DataFrame:
    out = frame.loc[:, list(columns)].copy()
    for col in categorical:
        if col in out.columns:
            out[col] = out[col].fillna("UNKNOWN").astype(str)
    return out


def _fit_predict_folds(
    scoped: pd.DataFrame,
    *,
    y: pd.Series,
    y_tail: pd.Series,
    numeric: Sequence[str],
    categorical: Sequence[str],
    model_name: str,
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
    need_tail: bool,
    progress: bool,
) -> Dict[str, Any]:
    windows = split_windows(scoped, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds)
    features = list(numeric) + list(categorical)
    prediction_frames: List[pd.DataFrame] = []
    fold_metrics: List[Dict[str, Any]] = []
    aucs: List[float] = []
    briers: List[float] = []
    tail_aucs: List[float] = []
    tail_briers: List[float] = []
    for fold_idx, (train_days, test_day_set) in enumerate(windows, start=1):
        train_idx = scoped.index[scoped["trade_date"].isin(train_days)]
        test_idx = scoped.index[scoped["trade_date"].isin(test_day_set)]
        if len(train_idx) < min_train_rows or len(test_idx) < min_test_rows:
            continue
        if y.loc[train_idx].nunique() < 2 or y.loc[test_idx].nunique() < 2:
            continue
        if need_tail and y_tail.loc[train_idx].nunique() < 2:
            continue
        estimator = model_candidate(model_name)
        if estimator is None:
            raise RuntimeError(f"model unavailable: {model_name}")
        scale = model_name == "logistic"
        pipe = Pipeline([("pre", preprocessor(numeric, categorical, scale_numeric=scale)), ("model", estimator)])
        x_train = _feature_frame(scoped.loc[train_idx], features, categorical)
        x_test = _feature_frame(scoped.loc[test_idx], features, categorical)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipe.fit(x_train, y.loc[train_idx])
            prob = pd.Series(pipe.predict_proba(x_test)[:, 1], index=test_idx)
        tail_prob = pd.Series(np.nan, index=test_idx, dtype=float)
        if need_tail:
            tail_estimator = model_candidate(model_name)
            tail_pipe = Pipeline([("pre", preprocessor(numeric, categorical, scale_numeric=scale)), ("model", tail_estimator)])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tail_pipe.fit(x_train, y_tail.loc[train_idx])
                tail_prob = pd.Series(tail_pipe.predict_proba(x_test)[:, 1], index=test_idx)
        try:
            aucs.append(float(roc_auc_score(y.loc[test_idx], prob)))
            briers.append(float(brier_score_loss(y.loc[test_idx], prob)))
        except Exception:
            pass
        if need_tail:
            try:
                tail_aucs.append(float(roc_auc_score(y_tail.loc[test_idx], tail_prob)))
                tail_briers.append(float(brier_score_loss(y_tail.loc[test_idx], tail_prob)))
            except Exception:
                pass
        prediction_frames.append(
            pd.DataFrame(
                {
                    "prob": prob,
                    "tail_prob": tail_prob,
                    "fold": fold_idx,
                    "test_days": ",".join(sorted(test_day_set)),
                },
                index=test_idx,
            )
        )
        fold_metrics.append({"fold": fold_idx, "test_days": sorted(test_day_set), "test_rows": int(len(test_idx))})
        if progress:
            print(f"[INFO] fitted fold {fold_idx}/{len(windows)} rows train={len(train_idx)} test={len(test_idx)}", flush=True)
    predictions = pd.concat(prediction_frames).sort_index() if prediction_frames else pd.DataFrame()
    return {
        "predictions": predictions,
        "folds": fold_metrics,
        "auc_mean": _round(np.mean(aucs)) if aucs else None,
        "brier_mean": _round(np.mean(briers)) if briers else None,
        "tail_risk_auc_mean": _round(np.mean(tail_aucs)) if tail_aucs else None,
        "tail_risk_brier_mean": _round(np.mean(tail_briers)) if tail_briers else None,
    }


def _sweep_market(
    data: pd.DataFrame,
    *,
    market: str,
    label_name: str,
    feature_set: str,
    model_name: str,
    topns: Sequence[int],
    prob_thresholds: Sequence[float | None],
    tail_thresholds: Sequence[float | None],
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
    min_kis_rows: int,
    min_kis_days: int,
    progress: bool,
) -> Dict[str, Any]:
    label_spec = next(spec for spec in LABEL_SPECS if spec.name == label_name)
    feature_map = feature_sets(data)
    if feature_set not in feature_map:
        raise KeyError(f"unknown feature set: {feature_set}")
    numeric, categorical = feature_map[feature_set]
    label, valid = label_series(data, label_spec)
    tail_label, tail_valid = tail_safe_series(data)
    valid &= tail_valid
    scoped = data.loc[valid & data["market"].eq(market)].copy()
    scoped = scoped.loc[kis_presence_mask(scoped, feature_set)].copy()
    y = label.loc[scoped.index].astype(int)
    y_tail = tail_label.loc[scoped.index].astype(int)
    numeric, categorical = usable_features(scoped, numeric, categorical)
    required_rows = max(int(min_kis_rows or 0), int(min_train_rows) + int(min_test_rows))
    scope = {
        "market": market,
        "rows": int(len(scoped)),
        "positive_rate_pct": _round(float(y.mean() * 100.0)) if len(y) else None,
        "tail_safe_rate_pct": _round(float(y_tail.mean() * 100.0)) if len(y_tail) else None,
        "unique_days": int(scoped["trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
        "unique_runs": int(scoped["run_id"].nunique()) if "run_id" in scoped.columns else 0,
        "usable_numeric": len(numeric),
        "usable_categorical": len(categorical),
        "required_rows": required_rows,
        "required_days": int(min_kis_days),
    }
    if scope["rows"] < required_rows or scope["unique_days"] < int(min_kis_days) or y.nunique() < 2 or y_tail.nunique() < 2:
        return {"scope": scope, "results": [], "status": "skipped_scope_not_trainable"}
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
        need_tail=any(item is not None for item in tail_thresholds),
        progress=progress,
    )
    predictions = fold_payload.pop("predictions")
    if predictions.empty:
        return {"scope": scope, "results": [], "status": "skipped_no_predictions", "fold_meta": fold_payload}
    results: List[Dict[str, Any]] = []
    for topn in topns:
        for prob_threshold in prob_thresholds:
            for tail_threshold in tail_thresholds:
                candidate_idx = predictions.index
                if prob_threshold is not None:
                    candidate_idx = candidate_idx.intersection(predictions.index[predictions["prob"].ge(float(prob_threshold))])
                if tail_threshold is not None:
                    candidate_idx = candidate_idx.intersection(predictions.index[predictions["tail_prob"].ge(float(tail_threshold))])
                selected = top_indices_by_run(scoped.loc[candidate_idx], predictions.loc[candidate_idx, "prob"], int(topn))
                if selected.empty:
                    continue
                result_metrics = metrics(scoped, selected, label)
                identity = {
                    "market": market,
                    "label": label_name,
                    "feature_set": feature_set,
                    "model": model_name,
                    "selection_rule": _selection_rule(topn, prob_threshold, tail_threshold),
                }
                gate = evaluate_kis_model_gate(identity=identity, metrics=result_metrics, market=market)
                results.append(
                    {
                        **identity,
                        "topn": int(topn),
                        "prob_threshold": prob_threshold,
                        "tail_risk_prob_threshold": tail_threshold,
                        "status": "ok",
                        "metrics": result_metrics,
                        "kis_model_gate": gate,
                        "quality_score": _round(quality_score(result_metrics, topn=int(topn), label_name=label_name), 6),
                        "feature_columns": {"numeric": list(numeric), "categorical": list(categorical)},
                        "fold_meta": fold_payload,
                    }
                )
    status_rank = {"production_ready": 0, "shadow_ready": 1, "shadow_risk_review": 2, "blocked": 3}
    results.sort(
        key=lambda row: (
            status_rank.get(str((row.get("kis_model_gate") or {}).get("status")), 9),
            -float(row.get("quality_score") or -1e9),
            -float(((row.get("metrics") or {}).get("hit5_dd10_5d_pct")) or 0.0),
            -int(((row.get("metrics") or {}).get("n")) or 0),
        )
    )
    return {"scope": scope, "results": results, "status": "ok", "fold_meta": fold_payload}


def _write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    md = output.with_suffix(".md")
    lines = [
        "# KIS Sidecar Threshold Sweep",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}`",
        f"- data_rows: `{report.get('data_rows')}`",
        f"- feature_set: `{report.get('feature_set')}`",
        f"- model: `{report.get('model')}`",
        "",
        "## Top Results",
        "",
    ]
    for idx, row in enumerate(report.get("top_results") or [], start=1):
        metrics_row = row.get("metrics") or {}
        gate = row.get("kis_model_gate") or {}
        lines.append(
            f"{idx}. `{row.get('market')}` `{row.get('selection_rule')}` "
            f"status=`{gate.get('status')}` n=`{metrics_row.get('n')}` "
            f"days=`{metrics_row.get('active_days')}` runs=`{metrics_row.get('active_runs')}` "
            f"hit5_dd10=`{metrics_row.get('hit5_dd10_5d_pct')}` "
            f"avg5=`{metrics_row.get('avg_5d_pct')}` min_low=`{metrics_row.get('min_min_low_5d_pct')}` "
            f"blockers=`{gate.get('production_blocking_reasons')}`"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", required=True)
    parser.add_argument("--markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--label", default="touch5_dd10_5d")
    parser.add_argument("--feature-set", default="kis_sidecar_failure_risk_augmented")
    parser.add_argument("--model", default="lightgbm")
    parser.add_argument("--topns", default="1,2,3,4,5")
    parser.add_argument("--prob-thresholds", default="none,0.35,0.40,0.45,0.50,0.55,0.60,0.65")
    parser.add_argument("--tail-thresholds", default="none,0.50,0.60,0.70,0.80,0.85,0.90,0.95")
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=200)
    parser.add_argument("--min-train-days", type=int, default=3)
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--max-folds", type=int, default=5)
    parser.add_argument("--min-kis-rows", type=int, default=1200)
    parser.add_argument("--min-kis-days", type=int, default=10)
    parser.add_argument("--top-results", type=int, default=30)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--output", default="runtime_state/reports/learning/kis_sidecar_threshold_sweep.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_path = Path(args.prepared_cache)
    data = pd.read_pickle(cache_path)
    markets = [item.strip().upper() for item in str(args.markets).split(",") if item.strip()]
    topns = _parse_int_list(args.topns)
    prob_thresholds = _parse_float_list(args.prob_thresholds, include_none=False)
    tail_thresholds = _parse_float_list(args.tail_thresholds, include_none=False)
    market_reports = []
    all_results: List[Dict[str, Any]] = []
    for market in markets:
        if not args.quiet:
            print(f"[INFO] sweeping {market}", flush=True)
        market_report = _sweep_market(
            data,
            market=market,
            label_name=args.label,
            feature_set=args.feature_set,
            model_name=args.model,
            topns=topns,
            prob_thresholds=prob_thresholds,
            tail_thresholds=tail_thresholds,
            min_train_rows=int(args.min_train_rows),
            min_test_rows=int(args.min_test_rows),
            min_train_days=int(args.min_train_days),
            test_days=int(args.test_days),
            max_folds=int(args.max_folds),
            min_kis_rows=int(args.min_kis_rows),
            min_kis_days=int(args.min_kis_days),
            progress=not bool(args.quiet),
        )
        market_reports.append(market_report)
        all_results.extend(market_report.get("results") or [])
    status_rank = {"production_ready": 0, "shadow_ready": 1, "shadow_risk_review": 2, "blocked": 3}
    all_results.sort(
        key=lambda row: (
            status_rank.get(str((row.get("kis_model_gate") or {}).get("status")), 9),
            -float(row.get("quality_score") or -1e9),
            -float(((row.get("metrics") or {}).get("hit5_dd10_5d_pct")) or 0.0),
            -int(((row.get("metrics") or {}).get("n")) or 0),
        )
    )
    report = {
        "version": "kis_sidecar_threshold_sweep_v1",
        "generated_at": _utc_now(),
        "prepared_cache": str(cache_path),
        "data_rows": int(len(data)),
        "label": args.label,
        "feature_set": args.feature_set,
        "model": args.model,
        "markets": markets,
        "threshold_grid": {
            "topns": topns,
            "prob_thresholds": prob_thresholds,
            "tail_thresholds": tail_thresholds,
        },
        "market_reports": market_reports,
        "top_results": all_results[: int(args.top_results)],
        "summary": {
            "evaluated_results": len(all_results),
            "production_ready": sum(1 for row in all_results if (row.get("kis_model_gate") or {}).get("production_ready")),
            "shadow_display_allowed": sum(1 for row in all_results if (row.get("kis_model_gate") or {}).get("shadow_display_allowed")),
        },
    }
    _write_report(report, Path(args.output))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2, default=_json_default))
    print(f"[INFO] wrote report {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
