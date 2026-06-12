#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Mapping, Sequence, Tuple

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_shadow_model_runtime import LightGBMStopAdjustedScorer
from multi_agent.tools.train_kis_historical_best_effort_suite import (
    BUY_PREMIUM_PCT,
    DEFAULT_END,
    DEFAULT_START,
    REPORT_VERSION as SOURCE_REPORT_VERSION,
    STOP_PCT,
    TARGET_PCT,
    LGBMClassifier,
    LGBMRanker,
    _feature_importance,
    _feature_sets,
    _filter_valid_labels,
    _frame_for_native,
    _json_default,
    _load_market_frame,
    _make_success_model,
    _round,
)


ARTIFACT_VERSION = "kis_shadow_model_artifact_v1"
DEFAULT_REPORT = PROJECT_ROOT / "runtime_state/reports/learning/kis_historical_best_effort_suite_stop_overlay_strict_20260101_20260610.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "models/scan_universe_challengers"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"source_report_missing:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dummy_data_used") is not False:
        raise ValueError("source_report_must_be_real_data_only")
    return payload


def _best_row(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    markets = report.get("markets") if isinstance(report.get("markets"), dict) else {}
    item = markets.get(market.upper())
    if not isinstance(item, dict) or not isinstance(item.get("best"), dict):
        raise ValueError(f"best_model_missing:{market}")
    return dict(item["best"])


def _feature_columns(frame: pd.DataFrame, feature_set: str) -> Tuple[list[str], list[str]]:
    feature_sets = _feature_sets(frame)
    if feature_set not in feature_sets:
        raise ValueError(f"feature_set_missing:{feature_set}")
    numeric, categorical = feature_sets[feature_set]
    if not numeric and not categorical:
        raise ValueError(f"feature_set_empty:{feature_set}")
    return list(numeric), list(categorical)


def _fit_classifier(
    *,
    frame: pd.DataFrame,
    numeric: Sequence[str],
    categorical: Sequence[str],
    target_column: str,
) -> Tuple[Any, Dict[str, Any]]:
    model = _make_success_model("lightgbm", numeric, categorical)
    if model is None or LGBMClassifier is None:
        raise RuntimeError("lightgbm_classifier_unavailable")
    y = frame[target_column].astype(int)
    if y.nunique() < 2:
        raise ValueError(f"single_class_target:{target_column}")
    started = perf_counter()
    x = _frame_for_native(frame, numeric, categorical, backend="lightgbm")
    model.fit(x, y, categorical_feature=list(categorical) if categorical else "auto")
    return model, {
        "target_column": target_column,
        "train_rows": int(len(frame)),
        "positive_rate_pct": _round(float(y.mean() * 100.0), 6),
        "elapsed_sec": _round(perf_counter() - started, 3),
        "feature_importance_top": _feature_importance(model, list(numeric) + list(categorical)),
    }


def _fit_ranker(
    *,
    frame: pd.DataFrame,
    numeric: Sequence[str],
    categorical: Sequence[str],
) -> Tuple[Any, Dict[str, Any]]:
    if LGBMRanker is None:
        raise RuntimeError("lightgbm_ranker_unavailable")
    ordered = frame.sort_values(["base_trade_date", "ticker"]).copy()
    relevance = (
        ordered["_label_success"].astype(int) * 3
        + ordered["_label_hit10"].astype(int)
        - ordered["_label_stop_hit"].astype(int)
    ).clip(lower=0)
    if relevance.nunique() < 2:
        raise ValueError("single_relevance_target")
    groups = ordered.groupby("base_trade_date", sort=False).size().astype(int).tolist()
    model = LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=180,
        max_depth=5,
        num_leaves=24,
        learning_rate=0.04,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_samples=20,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    started = perf_counter()
    x = _frame_for_native(ordered, numeric, categorical, backend="lightgbm")
    model.fit(x, relevance, group=groups, categorical_feature=list(categorical) if categorical else "auto")
    return model, {
        "target_column": "daily_lambdarank_relevance",
        "train_rows": int(len(ordered)),
        "positive_relevance_rate_pct": _round(float(relevance.gt(0).mean() * 100.0), 6),
        "elapsed_sec": _round(perf_counter() - started, 3),
        "feature_importance_top": _feature_importance(model, list(numeric) + list(categorical)),
    }


def _rule_text(identity: Mapping[str, Any]) -> str:
    parts = [f"top{int(identity.get('topn') or 1)}"]
    threshold = _safe_float(identity.get("score_threshold"))
    if threshold is not None:
        prefix = "p" if str(identity.get("score_mode")) == "success_probability" else "score"
        parts.append(f"{prefix}{threshold:g}".replace(".", "p"))
    stop_threshold = _safe_float(identity.get("max_stop_probability"))
    if stop_threshold is not None:
        parts.append(f"stop{stop_threshold:g}".replace(".", "p"))
    return "_".join(parts)


def _model_path(output_dir: Path, market: str) -> Path:
    return output_dir / f"{market.lower()}__touch5_dd10_5d__kis_shadow_best_effort_current.pkl"


def _train_market(
    *,
    market: str,
    report: Mapping[str, Any],
    source_report_path: Path,
    start_date: str,
    end_date: str,
    output_dir: Path,
    input_path: Path | None,
) -> Dict[str, Any]:
    market_key = market.upper()
    best = _best_row(report, market_key)
    identity = best.get("identity") if isinstance(best.get("identity"), dict) else {}
    metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    gate = best.get("gate") if isinstance(best.get("gate"), dict) else {}
    if not identity:
        raise ValueError(f"best_identity_missing:{market_key}")
    cache_path = input_path or (
        PROJECT_ROOT
        / "runtime_state/reports/learning"
        / f"kis_historical_universe_prepared_{market_key.lower()}_{start_date.replace('-', '')}_{end_date.replace('-', '')}.pkl"
    )
    frame = _load_market_frame(cache_path, market_key)
    valid = _filter_valid_labels(frame, start=start_date, end=end_date)
    numeric, categorical = _feature_columns(valid, str(identity.get("feature_set") or ""))
    model_name = str(identity.get("model") or "")
    if model_name == "lightgbm_ranker":
        pipeline, fit_meta = _fit_ranker(frame=valid, numeric=numeric, categorical=categorical)
        prob_threshold = None
        score_threshold = _safe_float(identity.get("score_threshold"))
        score_output_type = "raw_score"
    elif model_name == "lightgbm":
        pipeline, fit_meta = _fit_classifier(frame=valid, numeric=numeric, categorical=categorical, target_column="_label_success")
        if str(identity.get("score_mode")) == "success_probability":
            prob_threshold = _safe_float(identity.get("score_threshold"))
            score_threshold = None
            score_output_type = "probability"
        elif str(identity.get("score_mode")) == "success_minus_stop_risk":
            prob_threshold = None
            score_threshold = _safe_float(identity.get("score_threshold"))
            score_output_type = "raw_score"
        else:
            prob_threshold = None
            score_threshold = None
            score_output_type = "probability"
    else:
        raise ValueError(f"unsupported_best_model_for_runtime_artifact:{model_name}")
    tail_pipeline, tail_meta = _fit_classifier(frame=valid, numeric=numeric, categorical=categorical, target_column="_label_stop_hit")
    if model_name == "lightgbm" and str(identity.get("score_mode")) == "success_minus_stop_risk":
        pipeline = LightGBMStopAdjustedScorer(
            pipeline,
            tail_pipeline,
            stop_penalty_lambda=float(identity.get("stop_penalty_lambda") or 1.0),
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _model_path(output_dir, market_key)
    bundle = {
        "version": ARTIFACT_VERSION,
        "source_report_version": report.get("version") or SOURCE_REPORT_VERSION,
        "trained_at": _utc_now(),
        "source_report": str(source_report_path),
        "source_cache": str(cache_path),
        "dummy_data_used": False,
        "target_pct": TARGET_PCT,
        "stop_pct": STOP_PCT,
        "buy_premium_pct": BUY_PREMIUM_PCT,
        "label": "touch5_dd10_5d",
        "label_description": "+5% target touch within 5D after +2% buy premium, with no -10% hard stop breach",
        "market": market_key,
        "topn": int(identity.get("topn") or 1),
        "prob_threshold": prob_threshold,
        "score_threshold": score_threshold,
        "score_output_type": score_output_type,
        "stop_penalty_lambda": _safe_float(identity.get("stop_penalty_lambda")),
        "max_stop_probability": _safe_float(identity.get("max_stop_probability")),
        "tail_risk_label": "5D hard stop breach probability under the operational +2% entry assumption",
        "selection_rule": _rule_text(identity),
        "feature_set": identity.get("feature_set"),
        "feature_columns": {"numeric": numeric, "categorical": categorical},
        "native_lightgbm_categorical": bool(categorical),
        "model_name": model_name,
        "score_mode": identity.get("score_mode"),
        "pipeline": pipeline,
        "tail_risk_pipeline": tail_pipeline,
        "training": {
            "rows": int(len(valid)),
            "days": int(valid["base_trade_date"].nunique()),
            "date_min": str(valid["base_trade_date"].min()) if not valid.empty else None,
            "date_max": str(valid["base_trade_date"].max()) if not valid.empty else None,
            "success_fit": fit_meta,
            "hard_stop_fit": tail_meta,
        },
        "validation": {
            "identity": identity,
            "metrics": metrics,
            "kis_model_gate": gate,
            "source_best": best,
        },
        "deployment_scope": "kis_shadow_only",
        "shadow_only": True,
        "production_ready": bool(gate.get("production_ready")),
        "shadow_display_allowed": bool(gate.get("shadow_display_allowed")),
    }
    joblib.dump(bundle, path)
    return {
        "market": market_key,
        "saved": True,
        "model_path": str(path),
        "model_name": model_name,
        "score_mode": identity.get("score_mode"),
        "feature_set": identity.get("feature_set"),
        "feature_columns": {"numeric": len(numeric), "categorical": len(categorical)},
        "topn": int(identity.get("topn") or 1),
        "prob_threshold": prob_threshold,
        "score_threshold": score_threshold,
        "score_output_type": score_output_type,
        "max_stop_probability": _safe_float(identity.get("max_stop_probability")),
        "train_rows": int(len(valid)),
        "train_days": int(valid["base_trade_date"].nunique()),
        "validation_metrics": metrics,
        "gate": gate,
    }


def _write_markdown(report: Mapping[str, Any], path: Path) -> None:
    lines = [
        "# KIS shadow model artifacts",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source_report: `{report.get('source_report')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        "",
    ]
    for market, item in (report.get("markets") or {}).items():
        metrics = item.get("validation_metrics") if isinstance(item.get("validation_metrics"), dict) else {}
        gate = item.get("gate") if isinstance(item.get("gate"), dict) else {}
        lines.extend(
            [
                f"## {market}",
                "",
                f"- model_path: `{item.get('model_path')}`",
                f"- model: `{item.get('model_name')}` / `{item.get('score_mode')}` / `{item.get('feature_set')}`",
                f"- rule: topN `{item.get('topn')}`, prob `{item.get('prob_threshold')}`, score `{item.get('score_threshold')}`, max_stop `{item.get('max_stop_probability')}`",
                f"- train rows/days: `{item.get('train_rows')}` / `{item.get('train_days')}`",
                f"- validation hit5_dd10: `{metrics.get('hit5_dd10_5d_pct')}`",
                f"- validation hit10: `{metrics.get('hit10_5d_pct')}`",
                f"- validation stop5: `{metrics.get('stop5_pct')}`",
                f"- validation avg close 5D: `{metrics.get('avg_5d_pct')}`",
                f"- validation avg ordered exit 5D: `{metrics.get('avg_ordered_exit_5d_pct')}`",
                f"- gate: `{gate.get('status')}` production=`{gate.get('production_ready')}` shadow=`{gate.get('shadow_display_allowed')}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    started = perf_counter()
    source_report_path = Path(args.source_report)
    if not source_report_path.is_absolute():
        source_report_path = PROJECT_ROOT / source_report_path
    report = _load_report(source_report_path)
    input_paths: Dict[str, Path] = {}
    for raw in args.input_path:
        if "=" not in str(raw):
            raise ValueError("--input-path must be MARKET=path")
        market, path = str(raw).split("=", 1)
        input_paths[market.strip().upper()] = Path(path.strip())
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    markets: Dict[str, Any] = {}
    for market in args.markets:
        market_key = market.upper()
        markets[market_key] = _train_market(
            market=market_key,
            report=report,
            source_report_path=source_report_path,
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=output_dir,
            input_path=input_paths.get(market_key),
        )
    return {
        "version": ARTIFACT_VERSION,
        "generated_at": _utc_now(),
        "source_report": str(source_report_path),
        "dummy_data_used": False,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "markets_requested": list(args.markets),
        "elapsed_sec": _round(perf_counter() - started, 3),
        "markets": markets,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", default=str(DEFAULT_REPORT.relative_to(PROJECT_ROOT)))
    parser.add_argument("--start-date", default=DEFAULT_START)
    parser.add_argument("--end-date", default=DEFAULT_END)
    parser.add_argument("--markets", nargs="+", default=["KOSPI", "KOSDAQ"])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)))
    parser.add_argument("--input-path", action="append", default=[], help="MARKET=path override")
    parser.add_argument("--output-json", default="runtime_state/reports/learning/kis_shadow_model_artifacts.json")
    parser.add_argument("--output-md", default="runtime_state/reports/learning/kis_shadow_model_artifacts.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run(args)
    out_json = PROJECT_ROOT / args.output_json
    out_md = PROJECT_ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    _write_markdown(report, out_md)
    print(json.dumps({"output_json": str(out_json), "output_md": str(out_md), "markets": report.get("markets")}, ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
