#!/usr/bin/env python3
"""Validate KIS touch5/dd10 candidates by period slices and feature ablations.

This report is intentionally stricter than a leaderboard sweep.  It replays the
current best per-market KIS rule on actual sidecar rows only, then checks whether
the result survives monthly/rolling period splits and feature-family changes.
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


REPORT_VERSION = "kis_touch5_slice_ablation_v1"
REPORT_DIR = ROOT / "runtime_state/reports/learning"
DEFAULT_PREPARED_CACHE = (
    REPORT_DIR / "scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl"
)
DEFAULT_LEADERBOARD = REPORT_DIR / "kis_touch5_candidate_leaderboard_20260613.json"
DEFAULT_OUTPUT = REPORT_DIR / "kis_touch5_slice_ablation_20260613.json"
REQUIRED_MONTHS = ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")
REQUIRED_MARKETS = ("KOSPI", "KOSDAQ")
BASE_FEATURE_SET = "kis_sidecar_failure_risk_augmented"
LABEL_NAME = "touch5_dd10_5d"

DEFAULT_RULES: Dict[str, Dict[str, Any]] = {
    "KOSPI": {
        "model": "lightgbm",
        "topn": 2,
        "prob_threshold": 0.8,
        "tail_risk_prob_threshold": 0.85,
        "score_mode": "prob_plus_tail",
    },
    "KOSDAQ": {
        "model": "lightgbm",
        "topn": 3,
        "prob_threshold": None,
        "tail_risk_prob_threshold": 0.9,
        "score_mode": "ev",
    },
}


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


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _month(value: Any) -> str | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return str(ts.to_period("M"))


def _normalize_dates(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    out["_slice_month"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.to_period("M").astype(str)
    if "run_id" not in out.columns:
        out["run_id"] = out["trade_date"]
    out["run_id"] = out["run_id"].fillna(out["trade_date"]).astype(str)
    out["market"] = out.get("market", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    return out


def _feature_family(column: str) -> str:
    name = str(column or "").lower()
    if name.startswith("close_failure_prior_"):
        return "close_failure_prior"
    if name.startswith(("kis_news_", "kis_theme_news_", "theme_", "news_")) or name in {
        "primary_theme",
        "theme_source",
        "theme_inference_status",
    }:
        return "theme_news"
    if name.startswith("kis_financial_"):
        return "kis_financial"
    if name.startswith("kis_stock_") or name in {
        "kis_sector_code",
        "kis_sector_name",
        "kis_industry_code",
        "kis_industry_name",
    }:
        return "kis_static_master"
    if name.startswith(("kis_foreigner", "kis_institution", "kis_individual", "kis_whale")):
        return "kis_flow"
    if name.startswith("kis_"):
        return "kis_price_rank_quote"
    if name.startswith(("foreigner_", "institution_", "retail_", "whale_flow_")):
        return "scanner_technical"
    if any(part in name for part in ("rsi", "macd", "ma_", "volume", "momentum", "breakout", "trend", "tech", "alpha", "whale")):
        return "scanner_technical"
    return "scanner_context"


def _split_feature_configs(numeric: Sequence[str], categorical: Sequence[str]) -> Dict[str, Dict[str, List[str]]]:
    numeric = list(dict.fromkeys(numeric))
    categorical = list(dict.fromkeys(categorical))
    all_columns = numeric + categorical
    by_family: Dict[str, List[str]] = {}
    for column in all_columns:
        by_family.setdefault(_feature_family(column), []).append(column)

    def cols_for(*families: str) -> List[str]:
        selected: List[str] = []
        for family in families:
            selected.extend(by_family.get(family, []))
        return list(dict.fromkeys(selected))

    def config(name: str, columns: Sequence[str]) -> Dict[str, List[str]]:
        chosen = set(columns)
        return {
            "numeric": [col for col in numeric if col in chosen],
            "categorical": [col for col in categorical if col in chosen],
        }

    no_prior = [col for col in all_columns if _feature_family(col) != "close_failure_prior"]
    no_theme_news = [col for col in all_columns if _feature_family(col) != "theme_news"]
    no_kis_flow = [col for col in all_columns if _feature_family(col) != "kis_flow"]
    configs = {
        "all_features": config("all_features", all_columns),
        "all_minus_close_failure_prior": config("all_minus_close_failure_prior", no_prior),
        "all_minus_theme_news": config("all_minus_theme_news", no_theme_news),
        "all_minus_kis_flow": config("all_minus_kis_flow", no_kis_flow),
        "close_failure_prior_only": config("close_failure_prior_only", cols_for("close_failure_prior")),
        "kis_price_rank_quote_only": config("kis_price_rank_quote_only", cols_for("kis_price_rank_quote")),
        "kis_flow_only": config("kis_flow_only", cols_for("kis_flow")),
        "kis_static_financial_only": config("kis_static_financial_only", cols_for("kis_static_master", "kis_financial")),
        "theme_news_only": config("theme_news_only", cols_for("theme_news")),
        "scanner_technical_only": config("scanner_technical_only", cols_for("scanner_technical")),
    }
    return configs


def _family_profile(numeric: Sequence[str], categorical: Sequence[str]) -> Dict[str, Any]:
    profile: Dict[str, Dict[str, int]] = {}
    for column in numeric:
        family = _feature_family(column)
        profile.setdefault(family, {"numeric": 0, "categorical": 0})["numeric"] += 1
    for column in categorical:
        family = _feature_family(column)
        profile.setdefault(family, {"numeric": 0, "categorical": 0})["categorical"] += 1
    return {
        family: {
            "numeric": int(values["numeric"]),
            "categorical": int(values["categorical"]),
            "total": int(values["numeric"] + values["categorical"]),
        }
        for family, values in sorted(profile.items())
    }


def _parse_csv(raw: str) -> List[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def _slice_specs(months: Sequence[str]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for month in months:
        specs.append({"name": month, "type": "monthly", "months": [month]})
    for first, second in zip(months, months[1:]):
        specs.append({"name": f"{first}..{second}", "type": "rolling_2m", "months": [first, second]})
    specs.append({"name": "actual_available_full", "type": "available_full", "months": list(months)})
    return specs


def _rules_from_leaderboard(path: Path) -> Dict[str, Dict[str, Any]]:
    rules = {market: dict(rule) for market, rule in DEFAULT_RULES.items()}
    payload = _load_json(path)
    markets = payload.get("markets") if isinstance(payload.get("markets"), Mapping) else {}
    for market in REQUIRED_MARKETS:
        best = (markets.get(market) or {}).get("best_candidate") if isinstance(markets.get(market), Mapping) else {}
        identity = best.get("identity") if isinstance(best, Mapping) and isinstance(best.get("identity"), Mapping) else {}
        if not identity:
            continue
        rules[market] = {
            "model": identity.get("model") or rules[market]["model"],
            "topn": int(identity.get("topn") or rules[market]["topn"]),
            "prob_threshold": identity.get("prob_threshold"),
            "tail_risk_prob_threshold": identity.get("tail_risk_prob_threshold"),
            "score_mode": identity.get("score_mode") or rules[market]["score_mode"],
        }
    return rules


def _candidate_selection(
    scoped: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    rule: Mapping[str, Any],
) -> pd.Index:
    score = _score_predictions(predictions, str(rule.get("score_mode") or "prob"))
    candidate_idx = predictions.index
    prob_threshold = rule.get("prob_threshold")
    tail_threshold = rule.get("tail_risk_prob_threshold")
    if prob_threshold is not None:
        candidate_idx = candidate_idx.intersection(predictions.index[predictions["prob"].ge(float(prob_threshold))])
    if tail_threshold is not None:
        candidate_idx = candidate_idx.intersection(predictions.index[predictions["tail_prob"].ge(float(tail_threshold))])
    return top_indices_by_run(scoped.loc[candidate_idx], score.loc[candidate_idx], int(rule.get("topn") or 1))


def _evaluate_slice_config(
    data: pd.DataFrame,
    *,
    market: str,
    slice_spec: Mapping[str, Any],
    feature_config: str,
    numeric: Sequence[str],
    categorical: Sequence[str],
    rule: Mapping[str, Any],
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
    min_slice_rows: int,
    min_slice_days: int,
    progress: bool,
) -> Dict[str, Any]:
    label_spec = next(spec for spec in LABEL_SPECS if spec.name == LABEL_NAME)
    label, valid = label_series(data, label_spec)
    tail_label, tail_valid = tail_safe_series(data)
    month_mask = data["_slice_month"].isin(list(slice_spec.get("months") or []))
    scoped = data.loc[
        valid
        & tail_valid
        & data["market"].eq(market)
        & month_mask
        & kis_presence_mask(data, BASE_FEATURE_SET)
    ].copy()
    y = label.loc[scoped.index].astype(int)
    y_tail = tail_label.loc[scoped.index].astype(int)
    numeric, categorical = usable_features(scoped, numeric, categorical)
    scope = {
        "market": market,
        "slice": slice_spec.get("name"),
        "slice_type": slice_spec.get("type"),
        "months": list(slice_spec.get("months") or []),
        "feature_config": feature_config,
        "rows": int(len(scoped)),
        "unique_days": int(scoped["trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
        "unique_runs": int(scoped["run_id"].nunique()) if "run_id" in scoped.columns else 0,
        "positive_rate_pct": _round(float(y.mean() * 100.0)) if len(y) else None,
        "tail_safe_rate_pct": _round(float(y_tail.mean() * 100.0)) if len(y_tail) else None,
        "usable_numeric": int(len(numeric)),
        "usable_categorical": int(len(categorical)),
        "required_rows": int(max(min_slice_rows, min_train_rows + min_test_rows)),
        "required_days": int(max(min_slice_days, min_train_days + test_days)),
    }
    skip_reasons = []
    if not numeric and not categorical:
        skip_reasons.append("no_usable_features")
    if scope["rows"] < scope["required_rows"]:
        skip_reasons.append("rows_lt_required")
    if scope["unique_days"] < scope["required_days"]:
        skip_reasons.append("days_lt_required")
    if len(y) == 0 or y.nunique() < 2:
        skip_reasons.append("label_single_class")
    if len(y_tail) == 0 or y_tail.nunique() < 2:
        skip_reasons.append("tail_label_single_class")
    if skip_reasons:
        return {"status": "skipped_scope_not_trainable", "scope": scope, "skip_reasons": skip_reasons}

    fold_payload = _fit_predict_folds(
        scoped,
        y=y,
        y_tail=y_tail,
        numeric=numeric,
        categorical=categorical,
        model_name=str(rule.get("model") or "lightgbm"),
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
        return {"status": "skipped_no_predictions", "scope": scope, "fold_meta": fold_payload}
    selected = _candidate_selection(scoped, predictions, rule=rule)
    if selected.empty:
        return {"status": "skipped_no_selected_rows", "scope": scope, "fold_meta": fold_payload}
    result_metrics = metrics(scoped, selected, label)
    identity = {
        "market": market,
        "label": LABEL_NAME,
        "feature_set": BASE_FEATURE_SET,
        "feature_config": feature_config,
        "model": rule.get("model"),
        "score_mode": rule.get("score_mode"),
        "selection_rule": _selection_rule(
            int(rule.get("topn") or 1),
            rule.get("prob_threshold"),
            rule.get("tail_risk_prob_threshold"),
            str(rule.get("score_mode") or "prob"),
        ),
        "slice": slice_spec.get("name"),
        "slice_type": slice_spec.get("type"),
    }
    gate = evaluate_kis_model_gate(identity=identity, metrics=result_metrics, market=market)
    selected_frame = scoped.loc[selected].copy()
    sample_cols = [col for col in ("trade_date", "run_id", "ticker", "market") if col in selected_frame.columns]
    return {
        "status": "ok",
        "scope": scope,
        "identity": identity,
        "metrics": result_metrics,
        "kis_model_gate": gate,
        "quality_score": _round(quality_score(result_metrics, topn=int(rule.get("topn") or 1), label_name=LABEL_NAME)),
        "fold_meta": fold_payload,
        "selected_sample": selected_frame[sample_cols].head(12).to_dict(orient="records") if sample_cols else [],
        "feature_columns": {"numeric": list(numeric), "categorical": list(categorical)},
        "feature_family_profile": _family_profile(numeric, categorical),
    }


def _result_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics_row = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    gate = row.get("kis_model_gate") if isinstance(row.get("kis_model_gate"), Mapping) else {}
    status_rank = {"production_ready": 0, "shadow_ready": 1, "shadow_risk_review": 2, "blocked": 3}
    return (
        status_rank.get(str(gate.get("status")), 9),
        -float(row.get("quality_score") or -1e9),
        -float(metrics_row.get("hit5_dd10_5d_pct") or 0.0),
        -float(metrics_row.get("avg_5d_pct") or -999.0),
        -float(metrics_row.get("min_min_low_5d_pct") or -999.0),
        -int(metrics_row.get("n") or 0),
    )


def _compact_result(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"feature_columns", "selected_sample"}}


def _outcome_pass(row: Mapping[str, Any]) -> bool:
    metrics_row = row.get("metrics") if isinstance(row.get("metrics"), Mapping) else {}
    hit = float(metrics_row.get("hit5_dd10_5d_pct") or 0.0)
    low = float(metrics_row.get("min_min_low_5d_pct") or -999.0)
    return hit >= 73.0 and low >= -10.0


def _market_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    by_status: Dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    all_feature_periods = [
        row
        for row in ok_rows
        if (row.get("scope") or {}).get("feature_config") == "all_features"
        and (row.get("scope") or {}).get("slice_type") in {"monthly", "rolling_2m", "available_full"}
    ]
    ablations = [
        row
        for row in ok_rows
        if (row.get("scope") or {}).get("slice_type") == "available_full"
        and (row.get("scope") or {}).get("feature_config") != "all_features"
    ]
    all_feature_pass = [row for row in all_feature_periods if _outcome_pass(row)]
    ablation_pass = [row for row in ablations if _outcome_pass(row)]
    full_all = next(
        (
            row
            for row in ok_rows
            if (row.get("scope") or {}).get("slice_type") == "available_full"
            and (row.get("scope") or {}).get("feature_config") == "all_features"
        ),
        {},
    )
    full_no_prior = next(
        (
            row
            for row in ok_rows
            if (row.get("scope") or {}).get("slice_type") == "available_full"
            and (row.get("scope") or {}).get("feature_config") == "all_minus_close_failure_prior"
        ),
        {},
    )
    dominant_prior = bool(full_all and _outcome_pass(full_all) and (not full_no_prior or not _outcome_pass(full_no_prior)))
    production_ready = [row for row in ok_rows if ((row.get("kis_model_gate") or {}).get("production_ready"))]
    shadow_ready = [row for row in ok_rows if ((row.get("kis_model_gate") or {}).get("shadow_display_allowed"))]
    return {
        "total_results": int(len(rows)),
        "ok_results": int(len(ok_rows)),
        "status_counts": dict(sorted(by_status.items())),
        "production_ready_count": int(len(production_ready)),
        "shadow_display_allowed_count": int(len(shadow_ready)),
        "all_feature_period_result_count": int(len(all_feature_periods)),
        "all_feature_period_outcome_pass_count": int(len(all_feature_pass)),
        "available_full_ablation_result_count": int(len(ablations)),
        "available_full_ablation_outcome_pass_count": int(len(ablation_pass)),
        "dominant_close_failure_prior_dependency": dominant_prior,
        "best_results": [_compact_result(row) for row in sorted(ok_rows, key=_result_sort_key)[:8]],
        "all_feature_periods": [_compact_result(row) for row in sorted(all_feature_periods, key=_result_sort_key)],
        "available_full_ablations": [_compact_result(row) for row in sorted(ablations, key=_result_sort_key)],
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
    feature_config_names = _parse_csv(args.feature_configs)
    if not feature_config_names:
        feature_config_names = [
            "all_features",
            "all_minus_close_failure_prior",
            "all_minus_theme_news",
            "all_minus_kis_flow",
            "close_failure_prior_only",
            "kis_price_rank_quote_only",
            "kis_flow_only",
            "kis_static_financial_only",
            "theme_news_only",
            "scanner_technical_only",
        ]
    rules = _rules_from_leaderboard(Path(args.candidate_leaderboard))
    base_numeric, base_categorical = feature_sets(data)[BASE_FEATURE_SET]
    configs = _split_feature_configs(base_numeric, base_categorical)
    unknown_configs = [name for name in feature_config_names if name not in configs]
    if unknown_configs:
        raise KeyError(f"unknown feature configs: {unknown_configs}")
    slice_specs = _slice_specs(months)
    data_months = sorted({month for month in data["_slice_month"].dropna().astype(str).unique().tolist() if month})
    market_rows: Dict[str, List[Dict[str, Any]]] = {market: [] for market in REQUIRED_MARKETS}
    for market in REQUIRED_MARKETS:
        for spec in slice_specs:
            spec_type = str(spec.get("type") or "")
            if args.focused_matrix and spec_type != "available_full":
                config_names = ["all_features"]
            else:
                config_names = feature_config_names
            for config_name in config_names:
                config = configs[config_name]
                row = _evaluate_slice_config(
                    data,
                    market=market,
                    slice_spec=spec,
                    feature_config=config_name,
                    numeric=config["numeric"],
                    categorical=config["categorical"],
                    rule=rules[market],
                    min_train_rows=int(args.min_train_rows),
                    min_test_rows=int(args.min_test_rows),
                    min_train_days=int(args.min_train_days),
                    test_days=int(args.test_days),
                    max_folds=int(args.max_folds),
                    min_slice_rows=int(args.min_slice_rows),
                    min_slice_days=int(args.min_slice_days),
                    progress=bool(args.progress),
                )
                market_rows[market].append(row)
    summaries = {market: _market_summary(rows) for market, rows in market_rows.items()}
    missing_actual_months = [month for month in months if month not in data_months]
    sparse_months: List[str] = []
    for month in months:
        if month in missing_actual_months:
            continue
        month_frame = data[data["_slice_month"].eq(month)]
        if len(month_frame) < int(args.month_usable_rows) or any(
            len(month_frame[month_frame["market"].eq(market)]) == 0 for market in REQUIRED_MARKETS
        ):
            sparse_months.append(month)
    production_ready = all(summaries[market]["production_ready_count"] > 0 for market in REQUIRED_MARKETS)
    all_periods_pass = all(
        summaries[market]["all_feature_period_result_count"] > 0
        and summaries[market]["all_feature_period_result_count"] == summaries[market]["all_feature_period_outcome_pass_count"]
        for market in REQUIRED_MARKETS
    )
    ablations_pass = all(
        summaries[market]["available_full_ablation_result_count"] > 0
        and summaries[market]["available_full_ablation_outcome_pass_count"] >= 2
        for market in REQUIRED_MARKETS
    )
    decision_status = "production_replacement_candidate" if production_ready and not missing_actual_months and not sparse_months else "slice_ablation_blocks_production_replacement"
    return {
        "version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "dummy_data_used": False,
        "prepared_cache": _rel(cache_path),
        "candidate_leaderboard": _rel(Path(args.candidate_leaderboard)),
        "data_profile": {
            "rows": int(len(data)),
            "date_min": str(pd.to_datetime(data["trade_date"], errors="coerce").dropna().min().date()) if len(data) else None,
            "date_max": str(pd.to_datetime(data["trade_date"], errors="coerce").dropna().max().date()) if len(data) else None,
            "months_present": data_months,
            "required_months": months,
            "missing_actual_months": missing_actual_months,
            "sparse_actual_months": sparse_months,
        },
        "evaluation_contract": {
            "label": LABEL_NAME,
            "feature_set": BASE_FEATURE_SET,
            "buy_premium_pct": 2.0,
            "win_definition": "5거래일 내 +5% 터치 and 5거래일 저점 -10% 이상 방어",
            "period_axis": "monthly + rolling two-month + actual_available_full",
            "feature_axis": feature_config_names,
            "focused_matrix": bool(args.focused_matrix),
            "model_rules": rules,
        },
        "decision": {
            "status": decision_status,
            "production_replacement_ready": bool(decision_status == "production_replacement_candidate"),
            "production_ready_by_gate": bool(production_ready),
            "all_trainable_periods_outcome_pass": bool(all_periods_pass),
            "available_full_ablation_has_multiple_passing_families": bool(ablations_pass),
            "missing_or_sparse_actual_months": sorted(set(missing_actual_months + sparse_months)),
            "recommended_action": (
                "keep KIS model in shadow and continue actual sidecar backfill/forward tracking"
                if decision_status != "production_replacement_candidate"
                else "human review for controlled production replacement"
            ),
        },
        "markets": summaries,
        "raw_results": market_rows,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    profile = report.get("data_profile") if isinstance(report.get("data_profile"), Mapping) else {}
    contract = report.get("evaluation_contract") if isinstance(report.get("evaluation_contract"), Mapping) else {}
    lines = [
        "# KIS Touch5 Slice Ablation",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- decision: `{decision.get('status')}`",
        f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
        f"- recommended_action: `{decision.get('recommended_action')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}` rows=`{profile.get('rows')}` date=`{profile.get('date_min')}`..`{profile.get('date_max')}`",
        f"- missing_or_sparse_actual_months: `{decision.get('missing_or_sparse_actual_months')}`",
        f"- feature_axis: `{contract.get('feature_axis')}`",
        "",
        "## Market Summary",
        "| market | ok | production_ready | shadow | period_pass/periods | ablation_pass/ablations | dominant_prior |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    markets = report.get("markets") if isinstance(report.get("markets"), Mapping) else {}
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        lines.append(
            f"| {market} | {row.get('ok_results')} | {row.get('production_ready_count')} | "
            f"{row.get('shadow_display_allowed_count')} | "
            f"{row.get('all_feature_period_outcome_pass_count')}/{row.get('all_feature_period_result_count')} | "
            f"{row.get('available_full_ablation_outcome_pass_count')}/{row.get('available_full_ablation_result_count')} | "
            f"{row.get('dominant_close_failure_prior_dependency')} |"
        )
    lines.extend(["", "## Best Results"])
    for market in REQUIRED_MARKETS:
        row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        lines.append(f"### {market}")
        for idx, result in enumerate(row.get("best_results") or [], start=1):
            if not isinstance(result, Mapping):
                continue
            metrics_row = result.get("metrics") if isinstance(result.get("metrics"), Mapping) else {}
            scope = result.get("scope") if isinstance(result.get("scope"), Mapping) else {}
            gate = result.get("kis_model_gate") if isinstance(result.get("kis_model_gate"), Mapping) else {}
            ident = result.get("identity") if isinstance(result.get("identity"), Mapping) else {}
            lines.append(
                f"{idx}. slice=`{scope.get('slice')}` config=`{scope.get('feature_config')}` "
                f"rule=`{ident.get('selection_rule')}` status=`{gate.get('status')}` "
                f"n=`{metrics_row.get('n')}` days=`{metrics_row.get('active_days')}` "
                f"hit5=`{metrics_row.get('hit5_dd10_5d_pct')}` avg5=`{metrics_row.get('avg_5d_pct')}` "
                f"min_low=`{metrics_row.get('min_min_low_5d_pct')}` blockers=`{gate.get('production_blocking_reasons')}`"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-cache", default=str(DEFAULT_PREPARED_CACHE))
    parser.add_argument("--candidate-leaderboard", default=str(DEFAULT_LEADERBOARD))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--months", default=",".join(REQUIRED_MONTHS))
    parser.add_argument("--feature-configs", default="")
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=1)
    parser.add_argument("--min-train-days", type=int, default=7)
    parser.add_argument("--test-days", type=int, default=1)
    parser.add_argument("--max-folds", type=int, default=8)
    parser.add_argument("--min-slice-rows", type=int, default=1200)
    parser.add_argument("--min-slice-days", type=int, default=8)
    parser.add_argument("--month-usable-rows", type=int, default=1000)
    parser.add_argument("--full-matrix", action="store_true", help="Evaluate every feature config on every period slice.")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    args.focused_matrix = not bool(args.full_matrix)
    return args


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
