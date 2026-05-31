from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd


MODEL_DIR = Path("models/scan_universe_challengers")
MODEL_PATHS = {
    "KOSPI": MODEL_DIR / "kospi__clean_5d__wide_no_theme__xgboost__top1_p0p60.pkl",
    "KOSDAQ": MODEL_DIR / "kosdaq__pos_5d__wide_no_theme__hist_gb__top1_p0p55.pkl",
}

ADMISSION_SECTION = "Scan Universe Admission"
NEAR_MISS_SECTION = "Admission Near Miss"
RUNTIME_VERSION = "scan_universe_admission_runtime_v1"

FEATURE_KEYS = (
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "entry_reference_price",
)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and text.lower() not in {"none", "nan", "null", "-"}
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    return True


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if _present(value):
            return value
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if not _present(value):
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except Exception:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "pass", "passed"}:
        return True
    if text in {"0", "false", "no", "n", "fail", "failed"}:
        return False
    return None


def _ticker(row: Dict[str, Any]) -> str:
    return str(_first_present(row, "ticker", "Ticker", "symbol", "Symbol", "티커") or "").upper().strip()


def _stock_name(row: Dict[str, Any], ticker: str) -> str:
    return str(_first_present(row, "stock_name", "Stock Name", "종목명", "Name", "name") or ticker).strip()


def _market_from(row: Dict[str, Any], fallback: str = "") -> str:
    value = str(_first_present(row, "market", "Market", "market_subtype") or fallback or "").upper().strip()
    ticker = _ticker(row)
    if value in {"KOSPI", "KOSDAQ"}:
        return value
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return value


def _feature_number(row: Dict[str, Any], *keys: str) -> float | None:
    return _safe_float(_first_present(row, *keys))


def _extract_feature_columns(row: Dict[str, Any], *, market: str) -> Dict[str, Any]:
    features = {
        "alpha_score": _feature_number(row, "alpha_score", "Antigrav", "Alpha", "alpha"),
        "tech_score": _feature_number(row, "tech_score", "technical_score", "Tech"),
        "ml_prob": _feature_number(row, "ml_prob", "prob_5", "phase25_prob", "probability", "AI확률"),
        "prob_clean": _feature_number(row, "prob_clean", "phase25_prob_clean", "clean_prob", "_prob_clean", "정밀확률"),
        "whale_score": _feature_number(row, "whale_score", "whale", "Whale"),
        "decision_score": _feature_number(row, "decision_score", "Decision Score", "score", "buy_score"),
        "day_return_pct": _feature_number(row, "day_return_pct", "day_change_pct", "day_ret", "Change %", "전일비"),
        "volume_ratio": _feature_number(row, "volume_ratio", "vol_ratio", "Volume Ratio"),
        "turnover": _feature_number(row, "turnover", "trading_value", "amount", "거래대금"),
        "foreigner_1d": _feature_number(row, "foreigner_1d", "foreign_1d", "foreign_flow_1d"),
        "institution_1d": _feature_number(row, "institution_1d", "inst_1d", "institution_flow_1d"),
        "retail_1d": _feature_number(row, "retail_1d", "individual_1d"),
        "foreigner_3d": _feature_number(row, "foreigner_3d", "foreign_3d"),
        "institution_3d": _feature_number(row, "institution_3d", "inst_3d"),
        "retail_3d": _feature_number(row, "retail_3d", "individual_3d"),
        "foreigner_10d": _feature_number(row, "foreigner_10d", "foreign_10d"),
        "institution_10d": _feature_number(row, "institution_10d", "inst_10d"),
        "retail_10d": _feature_number(row, "retail_10d", "individual_10d"),
        "entry_reference_price": _feature_number(row, "entry_reference_price", "scan_entry_reference_price", "Entry", "매수가(-2%)", "curr_price", "price"),
        "priority_rank": _safe_int(_first_present(row, "priority_rank", "_raw_scan_rank", "rank", "Rank")),
        "total_scans": _safe_int(_first_present(row, "total_scans", "_total_scans")),
        "filtered_count": _safe_int(_first_present(row, "filtered_count", "_filtered_count")),
        "market": market,
        "row_role": str(_first_present(row, "row_role") or "emitted"),
        "passed_current_model": _safe_bool(_first_present(row, "passed_current_model")) if _present(row.get("passed_current_model")) else True,
        "decision": _first_present(row, "decision", "Decision", "strategy"),
        "decision_bucket": _first_present(row, "decision_bucket", "selection_lane"),
        "reject_stage": _first_present(row, "reject_stage"),
        "reject_reason": _first_present(row, "reject_reason"),
        "primary_theme": _first_present(row, "primary_theme", "theme", "Theme", "테마"),
        "theme_source": _first_present(row, "theme_source"),
        "theme_inference_status": _first_present(row, "theme_inference_status"),
        "kr_universe_role": _first_present(row, "kr_universe_role"),
        "scanner_timeframe_profile": _first_present(row, "scanner_timeframe_profile"),
        "has_actual_flow": _safe_bool(_first_present(row, "has_actual_flow")),
        "flow_consensus_buying": _safe_bool(_first_present(row, "flow_consensus_buying")),
        "retail_dominant": _safe_bool(_first_present(row, "retail_dominant")),
        "dominant": _first_present(row, "dominant"),
        "whale_trend": _first_present(row, "whale_trend"),
    }
    whale_1d = None
    if features["foreigner_1d"] is not None or features["institution_1d"] is not None:
        whale_1d = float(features["foreigner_1d"] or 0.0) + float(features["institution_1d"] or 0.0)
    whale_3d = None
    if features["foreigner_3d"] is not None or features["institution_3d"] is not None:
        whale_3d = float(features["foreigner_3d"] or 0.0) + float(features["institution_3d"] or 0.0)
    whale_10d = None
    if features["foreigner_10d"] is not None or features["institution_10d"] is not None:
        whale_10d = float(features["foreigner_10d"] or 0.0) + float(features["institution_10d"] or 0.0)
    features["whale_flow_1d"] = whale_1d
    features["whale_flow_3d"] = whale_3d
    features["whale_flow_10d"] = whale_10d
    if features["has_actual_flow"] is None:
        features["has_actual_flow"] = any(features.get(key) is not None for key in ("foreigner_1d", "institution_1d", "retail_1d", "foreigner_3d", "institution_3d", "retail_3d"))
    if features["flow_consensus_buying"] is None and whale_1d is not None and whale_3d is not None:
        features["flow_consensus_buying"] = whale_1d > 0 and whale_3d > 0
    if features["retail_dominant"] is None and whale_1d is not None and features["retail_1d"] is not None:
        features["retail_dominant"] = float(features["retail_1d"] or 0.0) > 0 and whale_1d < 0
    if features["dominant"] is None:
        flows = {
            "foreigner": features["foreigner_1d"],
            "institution": features["institution_1d"],
            "retail": features["retail_1d"],
        }
        flows = {key: value for key, value in flows.items() if value is not None}
        if flows:
            features["dominant"] = max(flows, key=lambda key: abs(float(flows[key] or 0.0)))
    if features["whale_trend"] is None and whale_1d is not None and whale_3d is not None:
        if whale_1d > 0 and whale_3d > 0:
            features["whale_trend"] = "accumulation"
        elif whale_1d < 0 and whale_3d < 0:
            features["whale_trend"] = "distribution"
        else:
            features["whale_trend"] = "mixed"
    present = sum(1 for key in FEATURE_KEYS if _present(features.get(key)))
    features["feature_coverage_score"] = round(present / len(FEATURE_KEYS), 6)
    return features


@lru_cache(maxsize=4)
def load_admission_model(market: str) -> Dict[str, Any]:
    market_key = str(market or "").upper().strip()
    path = MODEL_PATHS.get(market_key)
    if not path:
        raise ValueError(f"unsupported_admission_market:{market}")
    if not path.exists():
        raise FileNotFoundError(f"admission_model_missing:{path}")
    bundle = joblib.load(path)
    bundle["_model_path"] = str(path)
    return bundle


def _bundle_features(bundle: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    columns = bundle.get("feature_columns") if isinstance(bundle.get("feature_columns"), dict) else {}
    numeric = [str(col) for col in columns.get("numeric", [])]
    categorical = [str(col) for col in columns.get("categorical", [])]
    return numeric, categorical


def _predict_probabilities(bundle: Dict[str, Any], feature_rows: List[Dict[str, Any]]) -> List[float]:
    numeric, categorical = _bundle_features(bundle)
    columns = numeric + categorical
    frame = pd.DataFrame(feature_rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    pipeline = bundle.get("pipeline")
    if pipeline is None:
        raise ValueError("admission_model_pipeline_missing")
    probabilities = pipeline.predict_proba(frame[columns])[:, 1]
    return [float(value) for value in probabilities]


def _metrics(bundle: Dict[str, Any]) -> Dict[str, Any]:
    validation = bundle.get("validation") if isinstance(bundle.get("validation"), dict) else {}
    metrics = validation.get("metrics") if isinstance(validation.get("metrics"), dict) else {}
    return metrics


def _round_pct(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return round(numeric, 4)


def admission_model_summary(market: str) -> Dict[str, Any]:
    bundle = load_admission_model(market)
    metrics = _metrics(bundle)
    threshold = float(bundle.get("prob_threshold") or 0.0)
    return {
        "version": RUNTIME_VERSION,
        "market": bundle.get("market"),
        "model_name": bundle.get("model_name"),
        "label": bundle.get("label"),
        "feature_set": bundle.get("feature_set"),
        "selection_rule": bundle.get("selection_rule"),
        "prob_threshold": threshold,
        "prob_threshold_pct": round(threshold * 100.0, 2),
        "topn": int(bundle.get("topn") or 1),
        "model_path": bundle.get("_model_path"),
        "validation": {
            "n": metrics.get("n"),
            "active_runs": metrics.get("active_runs"),
            "active_days": metrics.get("active_days"),
            "win_1d_pct": metrics.get("win_1d_pct"),
            "avg_1d_pct": metrics.get("avg_1d_pct"),
            "min_1d_pct": metrics.get("min_1d_pct"),
            "max_1d_pct": metrics.get("max_1d_pct"),
            "win_3d_pct": metrics.get("win_3d_pct"),
            "avg_3d_pct": metrics.get("avg_3d_pct"),
            "min_3d_pct": metrics.get("min_3d_pct"),
            "max_3d_pct": metrics.get("max_3d_pct"),
            "win_5d_pct": metrics.get("win_5d_pct"),
            "avg_5d_pct": metrics.get("avg_5d_pct"),
            "min_5d_pct": metrics.get("min_5d_pct"),
            "max_5d_pct": metrics.get("max_5d_pct"),
            "target_before_stop_5d_pct": metrics.get("target_before_stop_5d_pct"),
            "stop_before_target_5d_pct": metrics.get("stop_before_target_5d_pct"),
            "bad_path_pct": metrics.get("bad_path_pct"),
            "stop5_pct": metrics.get("stop5_pct"),
        },
    }


def _attach_display_payload(
    row: Dict[str, Any],
    *,
    bundle: Dict[str, Any],
    features: Dict[str, Any],
    probability: float,
    model_rank: int,
    passed: bool,
) -> Dict[str, Any]:
    metrics = _metrics(bundle)
    threshold = float(bundle.get("prob_threshold") or 0.0)
    probability_pct = round(probability * 100.0, 4)
    threshold_pct = round(threshold * 100.0, 4)
    section = ADMISSION_SECTION if passed else NEAR_MISS_SECTION
    stop_risk = _safe_float(metrics.get("stop_before_target_5d_pct"))
    bad_path = _safe_float(metrics.get("bad_path_pct"))
    loss_risk_score = max(value for value in (stop_risk, bad_path, 0.0) if value is not None)
    stock_name = _stock_name(row, _ticker(row))
    enriched = dict(row)
    enriched.update(
        {
            "stock_name": stock_name,
            "market": bundle.get("market"),
            "decision": "ADMISSION_PASS" if passed else "ADMISSION_NEAR_MISS",
            "decision_bucket": "admission_pass" if passed else "admission_near_miss",
            "phase25_oos_win_rate_pct": _round_pct(metrics.get("win_5d_pct")),
            "loss_risk_score": _round_pct(_first_present(row, "loss_risk_score", "Loss Risk") or loss_risk_score),
            "final_action": "Admission 모델 통과 - 조건부 매수 후보" if passed else "Admission 모델 기준 미달 - 신규 매수 대기",
            "entry_condition_text": (
                f"모델확률 {probability_pct:.1f}% >= 운영기준 {threshold_pct:.1f}%"
                if passed
                else f"모델확률 {probability_pct:.1f}% < 운영기준 {threshold_pct:.1f}%"
            ),
            "stop_condition_text": (
                f"검증 최저5D {_round_pct(metrics.get('min_5d_pct'))}% · "
                f"stop-first {_round_pct(metrics.get('stop_before_target_5d_pct'))}% 기준"
            ),
            "risk_flags": [
                "SCAN_UNIVERSE_ADMISSION_MODEL",
                f"model={bundle.get('model_name')}",
                f"threshold={threshold_pct:.1f}%",
            ]
            + ([] if passed else ["ADMISSION_THRESHOLD_NOT_MET"]),
            "_analysis_section": section,
            "_analysis_section_order": 0 if passed else 10,
            "_analysis_section_rank": model_rank,
            "_source_order": "scan_universe_admission_model",
            "scan_universe_admission": {
                "version": RUNTIME_VERSION,
                "market": bundle.get("market"),
                "model_name": bundle.get("model_name"),
                "label": bundle.get("label"),
                "feature_set": bundle.get("feature_set"),
                "selection_rule": bundle.get("selection_rule"),
                "topn": int(bundle.get("topn") or 1),
                "probability": probability,
                "probability_pct": probability_pct,
                "prob_threshold": threshold,
                "prob_threshold_pct": threshold_pct,
                "passed": passed,
                "model_rank": model_rank,
                "model_path": bundle.get("_model_path"),
                "feature_coverage_score": features.get("feature_coverage_score"),
                "validation": admission_model_summary(str(bundle.get("market") or "")).get("validation", {}),
            },
            "realized_expectancy_admission": {
                "available": True,
                "policy_version": RUNTIME_VERSION,
                "source": "scan_universe_admission_model",
                "5d_prob": probability_pct,
                "ranking_score_5d": probability_pct,
                "base_expected_value_5d_pct": _round_pct(metrics.get("avg_5d_pct")),
                "expected_value_5d_pct": _round_pct(metrics.get("avg_5d_pct")),
                "stress_expected_value_5d_pct": _round_pct(metrics.get("min_5d_pct")),
                "stop_first_risk_pct": _round_pct(metrics.get("stop_before_target_5d_pct")),
            },
            "prediction": {
                **(row.get("prediction") if isinstance(row.get("prediction"), dict) else {}),
                "realized_expectancy_5d_prob": probability_pct,
                "ranking_score_5d": probability_pct,
                "admission_policy_version": RUNTIME_VERSION,
                "scan_universe_admission_probability_pct": probability_pct,
            },
        }
    )
    return enriched


def score_scan_universe_admission_rows(
    rows: List[Dict[str, Any]],
    *,
    market: str,
) -> List[Dict[str, Any]]:
    market_key = str(market or "").upper().strip()
    bundle = load_admission_model(market_key)
    prepared: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for idx, row in enumerate(rows or [], start=1):
        if not isinstance(row, dict):
            continue
        ticker = _ticker(row)
        if not ticker:
            continue
        row_market = _market_from(row, fallback=market_key)
        if row_market != market_key:
            continue
        copy = dict(row)
        copy.setdefault("_raw_scan_rank", idx)
        prepared.append((copy, _extract_feature_columns(copy, market=market_key)))
    if not prepared:
        return []
    probabilities = _predict_probabilities(bundle, [features for _, features in prepared])
    scored: List[Dict[str, Any]] = []
    for (row, features), probability in zip(prepared, probabilities):
        copy = dict(row)
        copy["_admission_probability"] = probability
        copy["_admission_features"] = features
        scored.append(copy)
    return sorted(
        scored,
        key=lambda item: (
            -float(item.get("_admission_probability") or 0.0),
            _safe_int(item.get("_raw_scan_rank")) or 9999,
        ),
    )


def build_scan_universe_admission_records(
    rows: List[Dict[str, Any]],
    *,
    market: str,
    limit: int = 5,
    include_near_miss: bool = True,
) -> Dict[str, Any]:
    market_key = str(market or "").upper().strip()
    bundle = load_admission_model(market_key)
    threshold = float(bundle.get("prob_threshold") or 0.0)
    topn = max(1, int(bundle.get("topn") or 1))
    scored = score_scan_universe_admission_rows(rows, market=market_key)
    pass_records: List[Dict[str, Any]] = []
    near_records: List[Dict[str, Any]] = []
    selected_tickers: set[str] = set()

    for rank, row in enumerate(scored[:topn], start=1):
        probability = float(row.get("_admission_probability") or 0.0)
        if probability < threshold:
            continue
        ticker = _ticker(row)
        selected_tickers.add(ticker)
        pass_records.append(
            _attach_display_payload(
                row,
                bundle=bundle,
                features=row.get("_admission_features") if isinstance(row.get("_admission_features"), dict) else {},
                probability=probability,
                model_rank=rank,
                passed=True,
            )
        )

    if include_near_miss:
        near_limit = max(0, int(limit or 0))
        for rank, row in enumerate(scored, start=1):
            ticker = _ticker(row)
            if not ticker or ticker in selected_tickers:
                continue
            probability = float(row.get("_admission_probability") or 0.0)
            near_records.append(
                _attach_display_payload(
                    row,
                    bundle=bundle,
                    features=row.get("_admission_features") if isinstance(row.get("_admission_features"), dict) else {},
                    probability=probability,
                    model_rank=rank,
                    passed=False,
                )
            )
            if len(near_records) >= near_limit:
                break

    return {
        "market": market_key,
        "summary": admission_model_summary(market_key),
        "passed": pass_records,
        "near_miss": near_records,
        "combined": pass_records + near_records,
        "scored_count": len(scored),
        "threshold": threshold,
        "topn": topn,
    }


def admission_run_status(admission: Dict[str, Any]) -> Dict[str, Any]:
    """Return operator-facing admission status for one scan run.

    This separates the model's historical validation metrics from the current
    run's candidate-level probability, which is the value that controls
    admission/pass.
    """
    if not isinstance(admission, dict):
        return {
            "passed_count": 0,
            "near_miss_count": 0,
            "topn": 1,
            "threshold_pct": None,
            "best_probability_pct": None,
            "best_gap_pct_points": None,
            "best_ticker": "",
            "best_name": "",
            "status": "no_candidates",
            "message": "Admission 모델로 채점할 후보가 없습니다.",
        }
    summary = admission.get("summary") if isinstance(admission.get("summary"), dict) else {}
    passed = admission.get("passed") if isinstance(admission.get("passed"), list) else []
    near_miss = admission.get("near_miss") if isinstance(admission.get("near_miss"), list) else []
    combined = passed + near_miss
    threshold_pct = _safe_float(summary.get("prob_threshold_pct"))
    if threshold_pct is None:
        threshold_pct = _safe_float(admission.get("threshold"))
        if threshold_pct is not None and threshold_pct <= 1.0:
            threshold_pct *= 100.0
    topn = max(1, _safe_int(summary.get("topn")) or _safe_int(admission.get("topn")) or 1)
    best = combined[0] if combined else {}
    best_model = best.get("scan_universe_admission") if isinstance(best.get("scan_universe_admission"), dict) else {}
    best_probability_pct = _safe_float(best_model.get("probability_pct"))
    best_gap = None
    if best_probability_pct is not None and threshold_pct is not None:
        best_gap = round(best_probability_pct - threshold_pct, 4)
    passed_count = len(passed)
    if not combined:
        status = "no_candidates"
        message = "Admission 모델로 채점할 후보가 없습니다."
    elif passed_count:
        status = "passed"
        message = f"운영 통과 후보 {passed_count}개가 있습니다."
    else:
        status = "near_miss_only"
        if best_probability_pct is None or threshold_pct is None or best_gap is None:
            message = "운영 통과 후보는 없고 기준 미달 후보만 있습니다."
        else:
            message = (
                f"운영 통과 후보 0개: 최고 후보확률 {best_probability_pct:.1f}%가 "
                f"기준 {threshold_pct:.1f}%보다 {abs(best_gap):.1f}%p 낮습니다."
            )
    return {
        "passed_count": passed_count,
        "near_miss_count": len(near_miss),
        "topn": topn,
        "threshold_pct": round(threshold_pct, 4) if threshold_pct is not None else None,
        "best_probability_pct": round(best_probability_pct, 4) if best_probability_pct is not None else None,
        "best_gap_pct_points": best_gap,
        "best_ticker": _ticker(best) if isinstance(best, dict) else "",
        "best_name": _stock_name(best, _ticker(best)) if isinstance(best, dict) and best else "",
        "status": status,
        "message": message,
    }


__all__ = [
    "ADMISSION_SECTION",
    "NEAR_MISS_SECTION",
    "RUNTIME_VERSION",
    "admission_model_summary",
    "admission_run_status",
    "build_scan_universe_admission_records",
    "score_scan_universe_admission_rows",
]
