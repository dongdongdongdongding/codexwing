from __future__ import annotations

import math
import re
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
INTERPRETATION_VERSION = "scan_universe_admission_interpretation_v1"
UNIVERSE_INPUT_VERSION = "scan_universe_admission_universe_input_v1"
CRITICAL_LEGACY_REJECT_REASONS = {
    "FETCH_DATA_FAIL",
    "INTRADAY_FETCH_FAIL",
    "RATE_LIMIT_EXHAUSTED",
    "LIQUIDITY_FILTER_FAIL",
    "ML_INFERENCE_FAILED",
    "ML_PROB_MISSING",
    "KR_SIGNAL_COLUMN_MISSING",
    "MISSING_ANTIGRAV_SCORE",
    "EXHAUSTION_CONTEXT_UNAVAILABLE",
}

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


_NUMERIC_PATTERN = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?")


def _numeric_from_text(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return _safe_float(value)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = _NUMERIC_PATTERN.search(text)
    if not match:
        return None
    return _safe_float(match.group(0))


def _nested_dict(row: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def _nested_present(row: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = row
        ok = True
        for part in path.split("."):
            if not isinstance(current, dict):
                ok = False
                break
            current = current.get(part)
        if ok and _present(current):
            return current
    return None


def _feature_number_any(row: Dict[str, Any], *keys_or_paths: str) -> float | None:
    value = _first_present(row, *keys_or_paths)
    if value is None:
        value = _nested_present(row, *keys_or_paths)
    numeric = _safe_float(value)
    if numeric is not None:
        return numeric
    return _numeric_from_text(value)


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
    feature_snapshot = _nested_dict(row, "feature_snapshot")
    leader_metrics = _nested_dict(row, "leader_metrics") or _nested_dict(feature_snapshot, "leader_metrics")
    tech_score = _feature_number_any(row, "tech_score", "Tech", "기술점수", "feature_snapshot.tech_score")
    alpha_score = _feature_number_any(row, "alpha_score", "Antigrav", "Alpha", "alpha", "feature_snapshot.alpha_score", "feature_snapshot.antigrav")
    if tech_score is None:
        # KR scanner writes tech_score equal to Antigrav in DB payload, while
        # table/artifact rows often only keep Antigrav.
        tech_score = alpha_score
    whale_score = _feature_number_any(row, "whale_score", "Whale", "수급", "feature_snapshot.whale", "leader_metrics.whale_score")
    if whale_score is None:
        whale_score = _feature_number_any(leader_metrics, "kr_flow_leader_score")
    volume_ratio = _feature_number_any(
        row,
        "volume_ratio",
        "vol_ratio",
        "Volume Ratio",
        "거래량",
        "feature_snapshot.volume",
        "leader_metrics.kr_volume_ratio",
        "leader_metrics.volume_ratio",
        "price.volume_ratio_20d",
    )
    features = {
        "alpha_score": alpha_score,
        "tech_score": tech_score,
        "ml_prob": _feature_number_any(row, "ml_prob", "prob_5", "phase25_prob", "probability", "AI확률", "feature_snapshot.prob_5", "prediction.phase25_prob"),
        "prob_clean": _feature_number_any(row, "prob_clean", "phase25_prob_clean", "clean_prob", "_prob_clean", "정밀확률", "feature_snapshot.prob_clean"),
        "whale_score": whale_score,
        "decision_score": _feature_number_any(row, "decision_score", "Decision Score", "score", "buy_score", "feature_snapshot.decision_score"),
        "day_return_pct": _feature_number_any(row, "day_return_pct", "day_change_pct", "day_ret", "Change %", "전일비", "price.day_change_pct"),
        "volume_ratio": _feature_number(row, "volume_ratio", "vol_ratio", "Volume Ratio"),
        "turnover": _feature_number_any(row, "turnover", "trading_value", "amount", "거래대금", "leader_metrics.kr_turnover"),
        "foreigner_1d": _feature_number_any(row, "foreigner_1d", "foreign_1d", "foreign_flow_1d", "flow.foreigner_1d", "leader_metrics.kr_foreign_flow"),
        "institution_1d": _feature_number_any(row, "institution_1d", "inst_1d", "institution_flow_1d", "flow.institution_1d", "leader_metrics.kr_institution_flow"),
        "retail_1d": _feature_number_any(row, "retail_1d", "individual_1d", "flow.retail_1d", "leader_metrics.kr_retail_flow"),
        "foreigner_3d": _feature_number_any(row, "foreigner_3d", "foreign_3d", "flow.foreigner_3d"),
        "institution_3d": _feature_number_any(row, "institution_3d", "inst_3d", "flow.institution_3d"),
        "retail_3d": _feature_number_any(row, "retail_3d", "individual_3d", "flow.retail_3d"),
        "foreigner_10d": _feature_number_any(row, "foreigner_10d", "foreign_10d", "flow.foreigner_10d"),
        "institution_10d": _feature_number_any(row, "institution_10d", "inst_10d", "flow.institution_10d"),
        "retail_10d": _feature_number_any(row, "retail_10d", "individual_10d", "flow.retail_10d"),
        "entry_reference_price": _feature_number_any(row, "entry_reference_price", "scan_entry_reference_price", "Entry", "매수가(-2%)", "curr_price", "price", "feature_snapshot.entry_reference_price", "trade_plan.entry_reference_price"),
        "priority_rank": _safe_int(_nested_present(row, "priority_rank", "_raw_scan_rank", "rank", "Rank", "selection_alignment.raw_scan_rank")),
        "total_scans": _safe_int(_nested_present(row, "total_scans", "_total_scans")),
        "filtered_count": _safe_int(_nested_present(row, "filtered_count", "_filtered_count")),
        "market": market,
        "row_role": str(_nested_present(row, "row_role", "feature_snapshot.row_role") or "emitted"),
        "passed_current_model": _safe_bool(_nested_present(row, "passed_current_model", "feature_snapshot.passed_current_model")) if _present(_nested_present(row, "passed_current_model", "feature_snapshot.passed_current_model")) else True,
        "decision": _nested_present(row, "decision", "Decision", "strategy"),
        "decision_bucket": _nested_present(row, "decision_bucket", "selection_lane"),
        "reject_stage": _nested_present(row, "reject_stage"),
        "reject_reason": _nested_present(row, "reject_reason"),
        "primary_theme": _nested_present(row, "primary_theme", "theme.primary_theme", "theme_context.primary_theme", "feature_snapshot.theme_context.primary_theme", "theme", "Theme", "테마"),
        "theme_source": _nested_present(row, "theme_source", "theme_context.theme_source", "feature_snapshot.theme_context.theme_source"),
        "theme_inference_status": _nested_present(row, "theme_inference_status", "theme_context.theme_inference_status", "feature_snapshot.theme_context.theme_inference_status"),
        "kr_universe_role": _nested_present(row, "kr_universe_role", "feature_snapshot.kr_universe_role"),
        "scanner_timeframe_profile": _nested_present(row, "scanner_timeframe_profile", "feature_snapshot.scanner_timeframe_profile"),
        "has_actual_flow": _safe_bool(_nested_present(row, "has_actual_flow", "flow.valid")),
        "flow_consensus_buying": _safe_bool(_nested_present(row, "flow_consensus_buying", "leader_metrics.kr_flow_consensus_buying")),
        "retail_dominant": _safe_bool(_nested_present(row, "retail_dominant", "leader_metrics.kr_retail_dominant")),
        "dominant": _nested_present(row, "dominant", "flow.dominant"),
        "whale_trend": _nested_present(row, "whale_trend", "flow.whale_trend"),
    }
    features["volume_ratio"] = volume_ratio
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
    missing = [key for key in FEATURE_KEYS if not _present(features.get(key))]
    present = len(FEATURE_KEYS) - len(missing)
    features["feature_coverage_score"] = round(present / len(FEATURE_KEYS), 6)
    features["feature_missing_keys"] = missing
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


def _reason_codes(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace(",", "|").split("|") if part.strip()]
    if isinstance(value, dict):
        return [str(key) for key, enabled in value.items() if enabled]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def _promotion_block_reason(row: Dict[str, Any]) -> str:
    source_role = str(row.get("_admission_source_role") or row.get("row_role") or "").strip()
    if source_role not in {"legacy_rejected", "rejected"}:
        return ""
    codes = _reason_codes(row.get("reject_reason_codes") or row.get("reject_reason"))
    normalized = {str(code).upper().strip() for code in codes}
    for reason in CRITICAL_LEGACY_REJECT_REASONS:
        if reason in normalized:
            return reason
    return ""


def build_scan_universe_admission_input_rows(
    emitted_rows: List[Dict[str, Any]],
    *,
    diagnostics: Dict[str, Any] | None = None,
    market: str = "",
) -> Dict[str, Any]:
    """Build the runtime admission universe from emitted and rejected rows.

    The legacy scanner only emits rows after its hard filters. For the new
    admission model, those emitted rows are not enough: feature-rich rejected
    diagnostics are also valid scoring input because they represent symbols the
    scanner actually inspected before a legacy gate stopped them. Rows with
    sparse diagnostics stay in the universe with low feature coverage and
    visible warnings; they are not hidden behind Top5/Exception lanes.
    """

    market_key = str(market or "").upper().strip()
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    emitted: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for idx, source in enumerate(emitted_rows or [], start=1):
        if not isinstance(source, dict):
            continue
        ticker = _ticker(source)
        if not ticker:
            continue
        copy = dict(source)
        copy.setdefault("_raw_scan_rank", idx)
        copy.setdefault("_admission_source_role", "emitted")
        copy.setdefault("row_role", "emitted")
        copy.setdefault("feature_origin", copy.get("feature_origin") or "raw_scan_results")
        copy.setdefault("passed_current_model", True)
        emitted.append(copy)
        seen.add(ticker)

    rejected: List[Dict[str, Any]] = []
    details_by_symbol = diagnostics.get("reject_details_by_symbol") if isinstance(diagnostics.get("reject_details_by_symbol"), dict) else {}
    reasons_by_symbol = diagnostics.get("reject_reasons_by_symbol") if isinstance(diagnostics.get("reject_reasons_by_symbol"), dict) else {}
    for raw_ticker, raw_history in details_by_symbol.items():
        ticker = str(raw_ticker or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        if isinstance(raw_history, list):
            history = [item for item in raw_history if isinstance(item, dict)]
        elif isinstance(raw_history, dict):
            history = [raw_history]
        else:
            history = []
        if not history:
            continue
        terminal = dict(history[-1])
        terminal.setdefault("ticker", ticker)
        terminal.setdefault("티커", ticker)
        terminal.setdefault("market", market_key)
        terminal.setdefault("stock_name", terminal.get("stock_name") or terminal.get("종목명") or ticker)
        terminal["row_role"] = "rejected"
        terminal["passed_current_model"] = False
        terminal["decision_bucket"] = terminal.get("decision_bucket") or "legacy_rejected"
        terminal["reject_reason"] = terminal.get("reject_reason") or reasons_by_symbol.get(raw_ticker) or reasons_by_symbol.get(ticker)
        terminal["reject_reason_codes"] = _reason_codes(terminal.get("reject_reason"))
        terminal["reject_detail_history"] = history
        terminal["_admission_source_role"] = "legacy_rejected"
        terminal["_raw_scan_rank"] = len(emitted) + len(rejected) + 1
        terminal["feature_origin"] = terminal.get("feature_origin") or "reject_diagnostics"
        rejected.append(terminal)
        seen.add(ticker)

    rows = emitted + rejected
    return {
        "version": UNIVERSE_INPUT_VERSION,
        "market": market_key,
        "rows": rows,
        "emitted_count": len(emitted),
        "rejected_feature_rows": len(rejected),
        "total_input_rows": len(rows),
        "legacy_top5_auxiliary": True,
        "diagnostics_available": bool(diagnostics),
    }


def _signed(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{float(value):+.1f}{suffix}"


def _level_for_volume(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "거래량 데이터 부족"
    if numeric >= 2.5:
        return f"거래량 강함({numeric:.2f}x)"
    if numeric >= 1.2:
        return f"거래량 양호({numeric:.2f}x)"
    if numeric >= 0.8:
        return f"거래량 보통({numeric:.2f}x)"
    return f"거래량 약함({numeric:.2f}x)"


def _flow_label(features: Dict[str, Any]) -> str:
    whale_1d = _safe_float(features.get("whale_flow_1d"))
    whale_3d = _safe_float(features.get("whale_flow_3d"))
    foreigner = _safe_float(features.get("foreigner_1d"))
    institution = _safe_float(features.get("institution_1d"))
    retail = _safe_float(features.get("retail_1d"))
    if whale_1d is None and whale_3d is None and foreigner is None and institution is None and retail is None:
        return "수급 데이터 부족"
    direction = "혼조"
    if whale_1d is not None and whale_3d is not None:
        if whale_1d > 0 and whale_3d > 0:
            direction = "외인+기관 누적 매수"
        elif whale_1d < 0 and whale_3d < 0:
            direction = "외인+기관 누적 매도"
    elif whale_1d is not None:
        direction = "외인+기관 당일 매수" if whale_1d > 0 else "외인+기관 당일 매도" if whale_1d < 0 else "외인+기관 중립"
    parts = []
    if foreigner is not None:
        parts.append(f"외인 {_signed(foreigner)}")
    if institution is not None:
        parts.append(f"기관 {_signed(institution)}")
    if retail is not None:
        parts.append(f"개인 {_signed(retail)}")
    return direction + (" · " + " / ".join(parts) if parts else "")


def _theme_label(features: Dict[str, Any]) -> str:
    theme = str(features.get("primary_theme") or "").strip()
    source = str(features.get("theme_source") or "").strip()
    if not theme:
        return "테마 미확정"
    return f"테마 {theme}" + (f"({source})" if source else "")


def _build_result_interpretation(
    *,
    features: Dict[str, Any],
    probability_pct: float,
    threshold_pct: float,
    passed: bool,
    model_rank: int,
    metrics: Dict[str, Any],
    promotion_block_reason: str = "",
) -> Dict[str, Any]:
    coverage = _safe_float(features.get("feature_coverage_score"))
    coverage_pct = round(float(coverage or 0.0) * 100.0, 1) if coverage is not None else None
    gap = round(float(probability_pct) - float(threshold_pct), 4)
    day_return = _safe_float(features.get("day_return_pct"))
    missing = list(features.get("feature_missing_keys") or [])
    warnings: List[str] = []
    if coverage_pct is None or coverage_pct < 80.0:
        warnings.append(f"피처 커버리지 낮음 {coverage_pct if coverage_pct is not None else '-'}%")
    if missing:
        warnings.append("누락피처 " + ",".join(str(key) for key in missing[:5]))
    if day_return is not None and day_return < -3.0:
        warnings.append(f"당일 급락 {_signed(day_return, '%')}")
    if str(features.get("whale_trend") or "").lower() == "distribution":
        warnings.append("외인+기관 분산/매도 흐름")
    if promotion_block_reason:
        warnings.append(f"운영 차단 {promotion_block_reason}")

    decision = "운영 통과" if passed else ("모델 기준 통과·운영 차단" if promotion_block_reason and gap >= 0 else "기준 미달")
    action = "조건부 매수 후보로 표시" if passed else "승격 전 관찰 후보"
    if promotion_block_reason:
        action = f"모델 확률은 높지만 {promotion_block_reason} 때문에 운영 매수 차단"
    elif not passed and gap < 0:
        action = f"운영 기준까지 {abs(gap):.1f}%p 부족"

    drivers = [
        _level_for_volume(features.get("volume_ratio")),
        _flow_label(features),
        _theme_label(features),
    ]
    if day_return is not None:
        drivers.append(f"전일비 {_signed(day_return, '%')}")
    return {
        "version": INTERPRETATION_VERSION,
        "model_decision": decision,
        "action": action,
        "model_rank": model_rank,
        "probability_pct": round(float(probability_pct), 4),
        "threshold_pct": round(float(threshold_pct), 4),
        "threshold_gap_pct_points": gap,
        "promotion_blocked": bool(promotion_block_reason),
        "promotion_block_reason": promotion_block_reason,
        "feature_coverage_pct": coverage_pct,
        "feature_missing_keys": missing,
        "drivers": drivers,
        "warnings": warnings,
        "validation_summary": {
            "sample_n": metrics.get("n"),
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
            "bad_path_pct": metrics.get("bad_path_pct"),
        },
        "plain_text": (
            f"{decision}: 후보확률 {probability_pct:.1f}% / 기준 {threshold_pct:.1f}% "
            f"({gap:+.1f}%p). {action}. " + " · ".join(drivers)
        ),
    }


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
    promotion_block = _promotion_block_reason(row)
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
                "feature_missing_keys": features.get("feature_missing_keys") or [],
                "validation": admission_model_summary(str(bundle.get("market") or "")).get("validation", {}),
                "input_source_role": row.get("_admission_source_role") or row.get("row_role"),
                "legacy_reject_reason": row.get("reject_reason"),
                "promotion_blocked": bool(promotion_block),
                "promotion_block_reason": promotion_block,
            },
            "scan_result_interpretation": _build_result_interpretation(
                features=features,
                probability_pct=probability_pct,
                threshold_pct=threshold_pct,
                passed=passed,
                model_rank=model_rank,
                metrics=metrics,
                promotion_block_reason=promotion_block,
            ),
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
    input_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    market_key = str(market or "").upper().strip()
    bundle = load_admission_model(market_key)
    threshold = float(bundle.get("prob_threshold") or 0.0)
    topn = max(1, int(bundle.get("topn") or 1))
    scored = score_scan_universe_admission_rows(rows, market=market_key)
    pass_records: List[Dict[str, Any]] = []
    near_records: List[Dict[str, Any]] = []
    blocked_records: List[Dict[str, Any]] = []
    all_records: List[Dict[str, Any]] = []
    selected_tickers: set[str] = set()
    pass_candidates: List[Tuple[int, Dict[str, Any], float]] = []

    for rank, row in enumerate(scored, start=1):
        probability = float(row.get("_admission_probability") or 0.0)
        ticker = _ticker(row)
        if not ticker or probability < threshold or _promotion_block_reason(row):
            continue
        pass_candidates.append((rank, row, probability))
        selected_tickers.add(ticker)
        if len(pass_candidates) >= topn:
            break

    for rank, row in enumerate(scored, start=1):
        probability = float(row.get("_admission_probability") or 0.0)
        ticker = _ticker(row)
        all_records.append(
            _attach_display_payload(
                row,
                bundle=bundle,
                features=row.get("_admission_features") if isinstance(row.get("_admission_features"), dict) else {},
                probability=probability,
                model_rank=rank,
                passed=bool(ticker and ticker in selected_tickers),
            )
        )

    for rank, row, probability in pass_candidates:
        ticker = _ticker(row)
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
        blocked_limit = near_limit
        for rank, row in enumerate(scored, start=1):
            ticker = _ticker(row)
            if not ticker or ticker in selected_tickers:
                continue
            probability = float(row.get("_admission_probability") or 0.0)
            record = _attach_display_payload(
                row,
                bundle=bundle,
                features=row.get("_admission_features") if isinstance(row.get("_admission_features"), dict) else {},
                probability=probability,
                model_rank=rank,
                passed=False,
            )
            if _promotion_block_reason(row):
                if len(blocked_records) < blocked_limit:
                    blocked_records.append(record)
                continue
            if len(near_records) < near_limit:
                near_records.append(record)
            if len(near_records) >= near_limit and len(blocked_records) >= blocked_limit:
                break

    return {
        "market": market_key,
        "summary": admission_model_summary(market_key),
        "input_summary": input_summary if isinstance(input_summary, dict) else {
            "version": UNIVERSE_INPUT_VERSION,
            "market": market_key,
            "rows": "direct_rows",
            "emitted_count": len(rows or []),
            "rejected_feature_rows": 0,
            "total_input_rows": len(rows or []),
            "legacy_top5_auxiliary": True,
        },
        "passed": pass_records,
        "near_miss": near_records,
        "blocked": blocked_records,
        "combined": pass_records + near_records,
        "all_records": all_records,
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
    "UNIVERSE_INPUT_VERSION",
    "admission_model_summary",
    "admission_run_status",
    "build_scan_universe_admission_input_rows",
    "build_scan_universe_admission_records",
    "score_scan_universe_admission_rows",
]
