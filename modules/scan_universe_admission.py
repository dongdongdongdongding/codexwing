from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd

from modules.close_failure_prior_profile import (
    apply_close_failure_prior_profile_to_features,
    load_close_failure_prior_profile,
)
from modules.kis_shadow_exit_policy import build_kis_shadow_exit_policy
from modules.kis_theme_news_evidence import (
    build_kis_theme_news_evidence,
    format_kis_theme_news_summary,
)
from modules.kis_model_features import flatten_kis_model_features
from modules.kis_model_gate import evaluate_kis_model_gate


MODEL_DIR = Path("models/scan_universe_challengers")
KIS_MODEL_COMPARISON_PATH = Path("runtime_state/reports/learning/kis_model_market_comparison.json")
MODEL_PATHS = {
    "KOSPI": MODEL_DIR / "kospi__touch10_guard_5d__wide_theme__xgboost__top1_p0p45.pkl",
    "KOSDAQ": MODEL_DIR / "kosdaq__touch5_guard_5d__flow_no_gate__lightgbm__top1.pkl",
}
KIS_SHADOW_MODEL_PATHS = {
    "KOSPI": MODEL_DIR / "kospi__touch5_dd10_5d__kis_shadow_best_effort_current.pkl",
    "KOSDAQ": MODEL_DIR / "kosdaq__touch5_dd10_5d__kis_shadow_best_effort_current.pkl",
}

ADMISSION_SECTION = "Scan Universe Admission"
NEAR_MISS_SECTION = "Admission Near Miss"
KIS_SHADOW_SECTION = "KIS Shadow Candidate"
RUNTIME_VERSION = "scan_universe_admission_runtime_v2_entry_touch"
KIS_SHADOW_RUNTIME_VERSION = "kis_shadow_admission_runtime_v1"
INTERPRETATION_VERSION = "scan_universe_admission_interpretation_v2_entry_touch"
UNIVERSE_INPUT_VERSION = "scan_universe_admission_universe_input_v1"
KIS_PREFILTER_FEATURE_VERSION = "kis_operational_prefilter_snapshot_v1"
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
LOW_LIQUIDITY_REJECT_REASON = "LIQUIDITY_FILTER_FAIL"

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


def _nested_mapping(row: Dict[str, Any], *path: str) -> Dict[str, Any]:
    current: Any = row
    for key in path:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


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


def _has_kis_runtime_evidence(row: Dict[str, Any], features: Dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    numeric_evidence = (
        features.get("kis_sidecar_present"),
        features.get("kis_prefilter_present"),
        features.get("kis_sidecar_model_ready"),
        features.get("kis_prefilter_quote_ok"),
        features.get("kis_prefilter_flow_ok"),
    )
    if any((_safe_float(value) or 0.0) > 0.0 for value in numeric_evidence):
        return True
    origin_values = [
        row.get("feature_origin"),
        _nested_present(row, "feature_snapshot.feature_origin"),
        _nested_present(row, "feature_snapshot.kis_sidecar.feature_origin"),
        _nested_present(row, "feature_snapshot.kis_operational_prefilter.feature_origin"),
        _nested_present(row, "kis_sidecar.feature_origin"),
        _nested_present(row, "_kis_sidecar.feature_origin"),
    ]
    if any(str(value or "").startswith("kis_openapi") for value in origin_values):
        return True
    if _nested_mapping(row, "feature_snapshot", "kis_sidecar"):
        return True
    if _nested_mapping(row, "feature_snapshot", "kis_operational_prefilter"):
        return True
    if _nested_mapping(row, "leader_metrics", "kis_sidecar"):
        return True
    if _nested_mapping(row, "_leader_metrics", "kis_sidecar"):
        return True
    return False


@lru_cache(maxsize=4)
def _load_kis_shadow_report(market: str) -> Dict[str, Any]:
    market_key = str(market or "").upper().strip()
    if market_key not in {"KOSPI", "KOSDAQ"}:
        return {}
    try:
        import json

        payload = json.loads(KIS_MODEL_COMPARISON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    markets = payload.get("markets") if isinstance(payload.get("markets"), dict) else {}
    block = markets.get(market_key) if isinstance(markets.get(market_key), dict) else {}
    current = block.get("current_kis_model") if isinstance(block.get("current_kis_model"), dict) else {}
    identity = current.get("identity") if isinstance(current.get("identity"), dict) else {}
    metrics = current.get("metrics") if isinstance(current.get("metrics"), dict) else {}
    kis_model_gate = current.get("kis_model_gate") if isinstance(current.get("kis_model_gate"), dict) else {}
    if not kis_model_gate:
        kis_model_gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market_key)
    if not identity and not metrics:
        return {}
    return {
        "report_path": str(KIS_MODEL_COMPARISON_PATH),
        "report_generated_at": payload.get("generated_at"),
        "source_generated_at": block.get("source_generated_at"),
        "source_path": block.get("source_path"),
        "identity": identity,
        "metrics": metrics,
        "kis_model_gate": kis_model_gate,
    }


def _fmt_pct_short(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric:.2f}%"


def _kis_shadow_gate_payload(market: str) -> Dict[str, Any]:
    report = _load_kis_shadow_report(market)
    identity = report.get("identity") if isinstance(report.get("identity"), dict) else {}
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    kis_model_gate = report.get("kis_model_gate") if isinstance(report.get("kis_model_gate"), dict) else {}
    if not kis_model_gate:
        kis_model_gate = evaluate_kis_model_gate(identity=identity, metrics=metrics, market=market)
    blockers = []
    if isinstance(kis_model_gate.get("production_blocking_reasons"), list):
        blockers = [str(item) for item in kis_model_gate.get("production_blocking_reasons") if str(item).strip()]
    if not blockers:
        promotion = identity.get("promotion_candidate") if isinstance(identity.get("promotion_candidate"), dict) else {}
        if isinstance(promotion.get("blocking_reasons"), list):
            blockers = [str(item) for item in promotion.get("blocking_reasons") if str(item).strip()]
    profile = " / ".join(
        str(value)
        for value in (
            identity.get("label"),
            identity.get("feature_set"),
            identity.get("model"),
            identity.get("selection_rule"),
        )
        if value
    )
    if metrics and metrics.get("hit5_dd10_5d_pct") is not None:
        metrics_line = (
            f"n={metrics.get('n', '-')} · active_days={metrics.get('active_days', '-')} · "
            f"5D +5%/-10% 성공 {_fmt_pct_short(metrics.get('hit5_dd10_5d_pct'))} · "
            f"+10% 터치 {_fmt_pct_short(metrics.get('hit10_5d_pct'))} · "
            f"손절 {_fmt_pct_short(metrics.get('stop5_pct'))} · "
            f"평균종가 {_fmt_pct_short(metrics.get('avg_5d_pct'))} · "
            f"stop반영평균 {_fmt_pct_short(metrics.get('avg_ordered_exit_5d_pct'))}"
        )
    else:
        metrics_line = (
            f"n={metrics.get('n', '-')} · active_days={metrics.get('active_days', '-')} · "
            f"1D 목표/방어/평균 {_fmt_pct_short(metrics.get('win_1d_pct'))}/{_fmt_pct_short(metrics.get('close_win_1d_pct'))}/{_fmt_pct_short(metrics.get('avg_1d_pct'))} · "
            f"3D {_fmt_pct_short(metrics.get('win_3d_pct'))}/{_fmt_pct_short(metrics.get('close_win_3d_pct'))}/{_fmt_pct_short(metrics.get('avg_3d_pct'))} · "
            f"5D {_fmt_pct_short(metrics.get('win_5d_pct'))}/{_fmt_pct_short(metrics.get('close_win_5d_pct'))}/{_fmt_pct_short(metrics.get('avg_5d_pct'))}"
            if metrics
            else "KIS 비교 리포트 미확보"
        )
    return {
        "label": "KIS 쉐도우",
        "profile": profile or "kis_runtime_evidence",
        "conditions": "실제 KIS sidecar/prefilter evidence가 있는 현재 스캔 row만 shadow 채점",
        "metrics": metrics_line,
        "note": "운영 승격 전 관찰 레인입니다. 기존 운영 Top/Admission 후보를 대체하지 않습니다.",
        "report_path": report.get("report_path"),
        "report_generated_at": report.get("report_generated_at"),
        "source_path": report.get("source_path"),
        "blocking_reasons": blockers,
        "kis_model_gate": kis_model_gate,
        "status": kis_model_gate.get("status"),
        "production_ready": bool(kis_model_gate.get("production_ready")),
        "shadow_display_allowed": bool(kis_model_gate.get("shadow_display_allowed")),
        "risk_review_required": bool(kis_model_gate.get("risk_review_required")),
        "risk_review_reasons": list(kis_model_gate.get("risk_review_reasons") or []),
    }


def kis_shadow_gate_status(market: str) -> Dict[str, Any]:
    """Return the current KIS shadow display gate without creating candidates."""

    market_key = str(market or "").upper().strip()
    if market_key not in {"KOSPI", "KOSDAQ"}:
        return {}
    return _kis_shadow_gate_payload(market_key)


def _kis_shadow_topn(market: str, fallback: int = 3) -> int:
    report = _load_kis_shadow_report(market)
    identity = report.get("identity") if isinstance(report.get("identity"), dict) else {}
    topn = _safe_int(identity.get("topn"))
    return max(1, int(topn or fallback or 3))


def _kis_prefilter_feature_index(summary: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    payload = summary.get("kis_operational_prefilter") if isinstance(summary, dict) and isinstance(summary.get("kis_operational_prefilter"), dict) else {}
    candidates: List[Dict[str, Any]] = []
    for key in ("selected", "rejected_sample"):
        rows = payload.get(key) if isinstance(payload.get(key), list) else []
        candidates.extend(row for row in rows if isinstance(row, dict))
    markets = payload.get("markets") if isinstance(payload.get("markets"), dict) else {}
    for market_payload in markets.values():
        if not isinstance(market_payload, dict):
            continue
        for key in ("selected", "rejected_sample"):
            rows = market_payload.get(key) if isinstance(market_payload.get(key), list) else []
            candidates.extend(row for row in rows if isinstance(row, dict))

    indexed: Dict[str, Dict[str, Any]] = {}
    for row in candidates:
        if row.get("is_dummy_data") is True:
            continue
        ticker = _ticker(row)
        if not ticker:
            continue
        feature = dict(row)
        feature.setdefault("snapshot_feature_version", KIS_PREFILTER_FEATURE_VERSION)
        feature.setdefault("feature_origin", "kis_openapi_prefilter")
        feature.setdefault("is_dummy_data", False)
        indexed[ticker] = feature
    return indexed


def merge_kis_prefilter_evidence_into_rows(
    rows: List[Dict[str, Any]],
    summary: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    """Attach real KIS operational-prefilter evidence from scan summary rows.

    This only merges KIS OpenAPI payloads already persisted in
    ``scan_pipeline_summary.kis_operational_prefilter``. It does not synthesize
    candidates or fabricate missing KIS fields.
    """

    index = _kis_prefilter_feature_index(summary)
    if not index:
        return rows
    merged: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        ticker = _ticker(row)
        feature = index.get(ticker)
        if not feature:
            merged.append(row)
            continue
        copy = dict(row)
        snapshot = copy.get("feature_snapshot") if isinstance(copy.get("feature_snapshot"), dict) else {}
        snapshot = dict(snapshot)
        snapshot["kis_operational_prefilter"] = dict(feature)
        copy["feature_snapshot"] = snapshot
        copy["kis_operational_prefilter"] = dict(feature)
        origin = str(copy.get("feature_origin") or "").strip()
        if "kis_openapi_prefilter" not in origin:
            copy["feature_origin"] = f"{origin}+kis_openapi_prefilter" if origin else "kis_openapi_prefilter"
        merged.append(copy)
    return merged


def build_kis_shadow_admission_records(
    rows: List[Dict[str, Any]],
    *,
    market: str,
    limit: int | None = None,
    include_blocked_watch: bool = False,
) -> List[Dict[str, Any]]:
    """Return display-only KIS shadow candidates for the current run.

    No synthetic rows are created. A row is eligible only when the current scan
    payload contains real KIS sidecar or KIS operational-prefilter evidence.
    """

    market_key = str(market or "").upper().strip()
    if market_key not in {"KOSPI", "KOSDAQ"}:
        return []
    limit_n = max(1, int(limit if limit is not None else _kis_shadow_topn(market_key)))
    bundle = load_kis_shadow_model(market_key)
    scored = _score_scan_universe_admission_rows_with_bundle(rows, market=market_key, bundle=bundle)
    if not scored:
        return []
    gate = _kis_shadow_gate_payload(market_key)
    if not gate.get("shadow_display_allowed"):
        return []
    report = _load_kis_shadow_report(market_key)
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    identity = report.get("identity") if isinstance(report.get("identity"), dict) else {}
    kis_model_gate = report.get("kis_model_gate") if isinstance(report.get("kis_model_gate"), dict) else gate.get("kis_model_gate") or {}
    primary_threshold = _safe_float(bundle.get("prob_threshold"))
    primary_score_threshold = _safe_float(bundle.get("score_threshold"))
    selected: List[Dict[str, Any]] = []
    blocked_watch: List[Dict[str, Any]] = []
    for model_rank, row in enumerate(scored, start=1):
        features = row.get("_admission_features") if isinstance(row.get("_admission_features"), dict) else {}
        if not _has_kis_runtime_evidence(row, features):
            continue
        tail_gate_passed, _tail_threshold, _tail_probability = _tail_risk_gate(bundle, row)
        probability = float(row.get("_admission_probability") or 0.0)
        score = _safe_float(row.get("_admission_score"))
        primary_score_passed = primary_score_threshold is None or (score is not None and score >= primary_score_threshold)
        primary_probability_passed = primary_threshold is None or probability >= primary_threshold
        blocked_reasons: List[str] = []
        if not tail_gate_passed:
            blocked_reasons.append("dd10_safety_probability_below_threshold")
        if not primary_score_passed:
            blocked_reasons.append("score_threshold_not_met")
        if not primary_probability_passed:
            blocked_reasons.append("probability_threshold_not_met")
        strict_candidate = not blocked_reasons
        if not strict_candidate and not include_blocked_watch:
            continue
        record = _attach_display_payload(
            row,
            bundle=bundle,
            features=features,
            probability=probability,
            model_rank=model_rank,
            passed=False,
        )
        theme_news_evidence = build_kis_theme_news_evidence(
            record,
            market=market_key,
        )
        theme_news_summary = format_kis_theme_news_summary(theme_news_evidence)
        target_rows = selected if strict_candidate else blocked_watch
        shadow_rank = len(target_rows) + 1
        dynamic_exit_policy = build_kis_shadow_exit_policy(
            features=features,
            metrics=metrics,
            identity=identity,
            market=market_key,
        )
        trade_plan = record.get("trade_plan") if isinstance(record.get("trade_plan"), dict) else {}
        execution_stop = record.get("execution_stop") if isinstance(record.get("execution_stop"), dict) else {}
        tail_probability = _safe_float(row.get("_tail_risk_probability"))
        tail_threshold = _safe_float(bundle.get("max_stop_probability"))
        if tail_threshold is None:
            tail_threshold = _safe_float(bundle.get("tail_risk_prob_threshold"))
        record.update(
            {
                "decision": "KIS_SHADOW",
                "decision_bucket": "kis_shadow",
                "final_action": (
                    "KIS 쉐도우 위험검토 - 운영 승격 차단"
                    if kis_model_gate.get("risk_review_required")
                    else "KIS 쉐도우 관찰 - 운영 승격 전 후보"
                ),
                "entry_condition_text": (
                    f"KIS evidence 기반 shadow 후보 #{shadow_rank}: "
                    f"runtime admission score {probability * 100.0:.1f}% · "
                    f"동적 TP {dynamic_exit_policy.get('target_tp_pct')}% / SL {dynamic_exit_policy.get('stop_sl_pct')}%"
                ),
                "stop_condition_text": (
                    f"동적 손절 {dynamic_exit_policy.get('stop_sl_pct')}% · "
                    f"최대보유 {dynamic_exit_policy.get('hold_days')}일 · "
                    f"bad-path {metrics.get('bad_path_pct', '-')}%"
                    if metrics
                    else "KIS 쉐도우 검증 메타 미확보"
                ),
                "_analysis_section": KIS_SHADOW_SECTION,
                "_analysis_section_order": -250,
                "_analysis_section_rank": shadow_rank,
                "_source_order": "kis_shadow_admission_candidate",
                "_shadow_gate": gate,
                "trade_plan": {
                    **trade_plan,
                    "entry_policy": dynamic_exit_policy.get("entry_policy"),
                    "entry_premium_assumption_pct": dynamic_exit_policy.get("entry_premium_assumption_pct"),
                    "target_tp_pct": dynamic_exit_policy.get("target_tp_pct"),
                    "stop_sl_pct": dynamic_exit_policy.get("stop_sl_pct"),
                    "hold_days": dynamic_exit_policy.get("hold_days"),
                    "dynamic_exit_policy": dynamic_exit_policy,
                },
                "execution_stop": {
                    **execution_stop,
                    "display_stop_sl_pct": dynamic_exit_policy.get("stop_sl_pct"),
                    "display_stop_source": "kis_shadow_dynamic_exit_policy",
                    "dynamic_exit_policy": dynamic_exit_policy,
                },
                "kis_theme_news_evidence": theme_news_evidence,
                "kis_shadow_candidate": {
                    "version": KIS_SHADOW_RUNTIME_VERSION,
                    "runtime_model_path": bundle.get("_model_path"),
                    "shadow_model_loaded": bool(bundle.get("_shadow_model_loaded")),
                    "market": market_key,
                    "shadow_only": True,
                    "runtime_model_probability_pct": round(probability * 100.0, 4),
                    "runtime_model_score": _safe_float(row.get("_admission_score")),
                    "runtime_model_score_threshold": _safe_float(bundle.get("score_threshold")),
                    "tail_risk_probability_pct": round(tail_probability * 100.0, 4) if tail_probability is not None else None,
                    "tail_risk_prob_threshold_pct": round(tail_threshold * 100.0, 4) if tail_threshold is not None else None,
                    "tail_risk_label": bundle.get("tail_risk_label"),
                    "tail_risk_probability_semantics": (
                        "5거래일 내 저점이 진입가 대비 -10% 아래로 밀리지 않을 확률"
                    ),
                    "runtime_model_rank": model_rank,
                    "selection_rank": shadow_rank,
                    "source": "real_kis_sidecar_or_prefilter_evidence",
                    "candidate_status": "eligible_shadow",
                    "blocking_reasons": [],
                    "tail_risk_gate_passed": tail_gate_passed,
                    "primary_score_gate_passed": primary_score_passed,
                    "primary_probability_gate_passed": primary_probability_passed,
                    "identity": identity,
                    "metrics": metrics,
                    "kis_model_gate": kis_model_gate,
                    "gate_status": kis_model_gate.get("status"),
                    "production_ready": bool(kis_model_gate.get("production_ready")),
                    "risk_review_required": bool(kis_model_gate.get("risk_review_required")),
                    "dynamic_exit_policy": dynamic_exit_policy,
                    "theme_news_evidence": {
                        "available": theme_news_evidence.get("available"),
                        "kis_backed": theme_news_evidence.get("kis_backed"),
                        "strength_score": theme_news_evidence.get("evidence_strength_score"),
                        "strength_level": theme_news_evidence.get("evidence_strength_level"),
                        "summary": theme_news_summary,
                    },
                    "promotion_blocking_reasons": gate.get("blocking_reasons") or [],
                    "risk_review_reasons": gate.get("risk_review_reasons") or [],
                },
                "realized_expectancy_admission": {
                    **(record.get("realized_expectancy_admission") if isinstance(record.get("realized_expectancy_admission"), dict) else {}),
                    "available": bool(metrics),
                    "policy_version": KIS_SHADOW_RUNTIME_VERSION,
                    "source": "kis_shadow_validation_report",
                    "kis_model_gate_status": kis_model_gate.get("status"),
                    "risk_review_required": bool(kis_model_gate.get("risk_review_required")),
                    "5d_prob": metrics.get("win_5d_pct"),
                    "target_touch_win_pct": metrics.get("win_5d_pct"),
                    "close_defense_5d_pct": metrics.get("close_win_5d_pct"),
                    "win_metric_semantics": metrics.get("win_metric_semantics"),
                    "ranking_score_5d": round(probability * 100.0, 4),
                    "tail_risk_probability_pct": round(tail_probability * 100.0, 4) if tail_probability is not None else None,
                    "tail_risk_prob_threshold_pct": round(tail_threshold * 100.0, 4) if tail_threshold is not None else None,
                    "base_expected_value_5d_pct": metrics.get("avg_5d_pct"),
                    "expected_value_5d_pct": metrics.get("avg_5d_pct"),
                    "stress_expected_value_5d_pct": metrics.get("min_5d_pct"),
                    "expected_max_high_5d_pct": metrics.get("avg_max_high_5d_pct"),
                    "stop5_pct": metrics.get("stop5_pct"),
                    "dynamic_exit_policy_version": dynamic_exit_policy.get("version"),
                    "target_tp_pct": dynamic_exit_policy.get("target_tp_pct"),
                    "stop_sl_pct": dynamic_exit_policy.get("stop_sl_pct"),
                    "hold_days": dynamic_exit_policy.get("hold_days"),
                    "dynamic_risk_level": dynamic_exit_policy.get("risk_level"),
                    "dynamic_expected_net_avg_5d_pct": dynamic_exit_policy.get("expected_net_avg_5d_pct"),
                },
                "prediction": {
                    **(record.get("prediction") if isinstance(record.get("prediction"), dict) else {}),
                    "kis_shadow_runtime_probability_pct": round(probability * 100.0, 4),
                    "kis_shadow_tail_risk_probability_pct": (
                        round(tail_probability * 100.0, 4) if tail_probability is not None else None
                    ),
                    "realized_expectancy_5d_prob": metrics.get("win_5d_pct"),
                    "ranking_score_5d": round(probability * 100.0, 4),
                    "admission_policy_version": KIS_SHADOW_RUNTIME_VERSION,
                    "kis_model_gate_status": kis_model_gate.get("status"),
                    "dynamic_exit_policy_version": dynamic_exit_policy.get("version"),
                },
            }
        )
        interpretation = record.get("scan_result_interpretation") if isinstance(record.get("scan_result_interpretation"), dict) else {}
        drivers = list(interpretation.get("drivers") or [])
        if theme_news_summary:
            drivers.append(f"KIS테마/뉴스 {theme_news_summary}")
        record["scan_result_interpretation"] = {
            **interpretation,
            "model_decision": "KIS 쉐도우 후보",
            "action": (
                "운영 승격 전 최상단 관찰 · "
                f"동적 TP {dynamic_exit_policy.get('target_tp_pct')}% / SL {dynamic_exit_policy.get('stop_sl_pct')}%"
            ),
            "drivers": drivers[:8],
            "warnings": list(interpretation.get("warnings") or [])
            + list(theme_news_evidence.get("warnings") or [])[:3]
            + ["KIS_SHADOW_NOT_PRODUCTION_PROMOTED"]
            + (["KIS_SHADOW_RISK_REVIEW_REQUIRED"] if kis_model_gate.get("risk_review_required") else []),
            "plain_text": (
                f"KIS 쉐도우 후보: runtime admission score {probability * 100.0:.1f}%. "
                f"{gate.get('metrics') or ''} gate={kis_model_gate.get('status') or '-'} "
                f"dynamic_exit={dynamic_exit_policy.get('target_tp_pct')}%/{dynamic_exit_policy.get('stop_sl_pct')}%."
            ).strip(),
        }
        if not strict_candidate:
            record.update(
                {
                    "decision": "KIS_SHADOW_BLOCKED",
                    "decision_bucket": "kis_shadow_blocked_watch",
                    "final_action": "KIS 쉐도우 관찰 후보 - 모델/손절 게이트 차단, 매수 금지",
                    "entry_condition_text": (
                        f"KIS evidence 기반 blocked watch #{shadow_rank}: "
                        f"runtime admission score {probability * 100.0:.1f}% · "
                        f"차단 사유 {', '.join(blocked_reasons)}"
                    ),
                    "_analysis_section_order": -240,
                }
            )
            risk_flags = record.get("risk_flags") if isinstance(record.get("risk_flags"), list) else []
            record["risk_flags"] = list(dict.fromkeys([*risk_flags, "KIS_SHADOW_BLOCKED_WATCH", *blocked_reasons]))
            if isinstance(record.get("kis_shadow_candidate"), dict):
                record["kis_shadow_candidate"].update(
                    {
                        "candidate_status": "blocked_watch",
                        "blocking_reasons": blocked_reasons,
                        "tail_risk_gate_passed": tail_gate_passed,
                        "primary_score_gate_passed": primary_score_passed,
                        "primary_probability_gate_passed": primary_probability_passed,
                    }
                )
            interpretation = record.get("scan_result_interpretation") if isinstance(record.get("scan_result_interpretation"), dict) else {}
            record["scan_result_interpretation"] = {
                **interpretation,
                "model_decision": "KIS 쉐도우 blocked watch",
                "action": "최상단 관찰 전용 · 매수 금지 · 차단 사유 확인",
                "warnings": list(interpretation.get("warnings") or []) + ["KIS_SHADOW_BLOCKED_WATCH", *blocked_reasons],
            }
            blocked_watch.append(record)
            continue
        selected.append(record)
        if len(selected) >= limit_n:
            break
    if selected:
        return selected
    return blocked_watch[:limit_n] if include_blocked_watch else []


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
    features.update(flatten_kis_model_features(row))
    features = apply_close_failure_prior_profile_to_features(
        features,
        row=row,
        profile=load_close_failure_prior_profile(),
    )
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


@lru_cache(maxsize=4)
def load_kis_shadow_model(market: str) -> Dict[str, Any]:
    market_key = str(market or "").upper().strip()
    path = KIS_SHADOW_MODEL_PATHS.get(market_key)
    if path and path.exists():
        bundle = joblib.load(path)
        bundle["_model_path"] = str(path)
        bundle["_shadow_model_loaded"] = True
        return bundle
    bundle = load_admission_model(market_key)
    bundle["_shadow_model_loaded"] = False
    return bundle


def _bundle_features(bundle: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    columns = bundle.get("feature_columns") if isinstance(bundle.get("feature_columns"), dict) else {}
    numeric = [str(col) for col in columns.get("numeric", [])]
    categorical = [str(col) for col in columns.get("categorical", [])]
    return numeric, categorical


def _bundle_feature_frame(bundle: Dict[str, Any], feature_rows: List[Dict[str, Any]]) -> pd.DataFrame:
    numeric, categorical = _bundle_features(bundle)
    columns = numeric + categorical
    frame = pd.DataFrame(feature_rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in categorical:
        values = frame[column].fillna("UNKNOWN").astype(str).replace("", "UNKNOWN")
        frame[column] = values.astype("category") if bundle.get("native_lightgbm_categorical") else values
    return frame[columns]


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _predict_model_outputs(bundle: Dict[str, Any], feature_rows: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    frame = _bundle_feature_frame(bundle, feature_rows)
    pipeline = bundle.get("pipeline")
    if pipeline is None:
        raise ValueError("admission_model_pipeline_missing")
    if hasattr(pipeline, "predict_proba") and bundle.get("score_output_type") != "raw_score":
        probabilities = pipeline.predict_proba(frame)[:, 1]
        return [{"score": float(value), "probability": float(value)} for value in probabilities]
    raw_scores = pipeline.predict(frame)
    outputs: List[Dict[str, float]] = []
    for value in raw_scores:
        score = float(value)
        outputs.append({"score": score, "probability": float(_sigmoid(score))})
    return outputs


def _predict_probabilities(bundle: Dict[str, Any], feature_rows: List[Dict[str, Any]]) -> List[float]:
    return [item["probability"] for item in _predict_model_outputs(bundle, feature_rows)]


def _predict_tail_risk_probabilities(bundle: Dict[str, Any], feature_rows: List[Dict[str, Any]]) -> List[float | None]:
    pipeline = bundle.get("tail_risk_pipeline")
    if pipeline is None:
        return [None for _ in feature_rows]
    frame = _bundle_feature_frame(bundle, feature_rows)
    probabilities = pipeline.predict_proba(frame)[:, 1]
    return [float(value) for value in probabilities]


def _tail_risk_gate(bundle: Dict[str, Any], row: Dict[str, Any]) -> Tuple[bool, float | None, float | None]:
    max_stop_probability = _safe_float(bundle.get("max_stop_probability"))
    if max_stop_probability is not None:
        probability = _safe_float(row.get("_tail_risk_probability"))
        if probability is None:
            return False, max_stop_probability, None
        return probability <= max_stop_probability, max_stop_probability, probability
    threshold = _safe_float(bundle.get("tail_risk_prob_threshold"))
    if threshold is None:
        return True, None, None
    probability = _safe_float(row.get("_tail_risk_probability"))
    if probability is None:
        return False, threshold, None
    return probability >= threshold, threshold, probability


def _metrics(bundle: Dict[str, Any]) -> Dict[str, Any]:
    validation = bundle.get("validation") if isinstance(bundle.get("validation"), dict) else {}
    metrics = validation.get("metrics") if isinstance(validation.get("metrics"), dict) else {}
    return metrics


def _target_pct_from_label(label: Any) -> float:
    text = str(label or "").lower()
    if "touch5_dd10" in text or "hit5_dd10" in text:
        return 5.0
    if "touch5" in text or "hit5" in text:
        return 5.0
    return 10.0 if "10" in text else 5.0


def _objective_text(bundle: Dict[str, Any]) -> str:
    target = _target_pct_from_label(bundle.get("label"))
    label = str(bundle.get("label") or "")
    guard = "guard" in label
    suffix = " 및 -5% 선행손절 회피" if guard else ""
    return f"스캔 이후 5거래일 내 +{target:.0f}% 고가 터치{suffix}"


def _primary_validation_rate(metrics: Dict[str, Any]) -> float | None:
    return _round_pct(
        _first_present(
            metrics,
            "label_win_pct",
            "hit10_guard_5d_pct",
            "hit5_guard_5d_pct",
            "hit10_5d_pct",
            "hit5_5d_pct",
            "win_5d_pct",
        )
    )


def _touch_expected_value(metrics: Dict[str, Any]) -> float | None:
    return _round_pct(_first_present(metrics, "avg_max_high_5d_pct", "avg_5d_pct"))


def _touch_stress_value(metrics: Dict[str, Any]) -> float | None:
    return _round_pct(_first_present(metrics, "min_max_high_5d_pct", "min_5d_pct"))


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
    existing_evidence = row.get("kis_theme_news_evidence") if isinstance(row.get("kis_theme_news_evidence"), dict) else {}
    theme_block = row.get("theme") if isinstance(row.get("theme"), dict) else {}
    if not existing_evidence and isinstance(theme_block.get("kis_theme_news_evidence"), dict):
        existing_evidence = theme_block.get("kis_theme_news_evidence") or {}
    try:
        evidence = existing_evidence or build_kis_theme_news_evidence(row)
    except Exception:
        evidence = existing_evidence
    if isinstance(evidence, dict) and evidence.get("promotion_blocked"):
        reason = str(evidence.get("promotion_block_reason") or "").strip()
        if reason:
            return reason

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
    threshold_pct: float | None,
    passed: bool,
    model_rank: int,
    metrics: Dict[str, Any],
    promotion_block_reason: str = "",
) -> Dict[str, Any]:
    coverage = _safe_float(features.get("feature_coverage_score"))
    coverage_pct = round(float(coverage or 0.0) * 100.0, 1) if coverage is not None else None
    gap = round(float(probability_pct) - float(threshold_pct), 4) if threshold_pct is not None else None
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

    target_pct = _safe_float(metrics.get("target_return_pct")) or 5.0
    decision = "운영 통과" if passed else (
        "모델 기준 통과·운영 차단"
        if promotion_block_reason and (gap is None or gap >= 0)
        else "기준 미달"
    )
    action = f"5거래일 내 +{target_pct:.0f}% 목표터치 후보" if passed else "승격 전 관찰 후보"
    if promotion_block_reason:
        action = f"모델 확률은 높지만 {promotion_block_reason} 때문에 운영 매수 차단"
    elif not passed and gap is not None and gap < 0:
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
        "threshold_pct": round(float(threshold_pct), 4) if threshold_pct is not None else None,
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
            "win_metric_semantics": metrics.get("win_metric_semantics"),
            "close_win_metric_semantics": metrics.get("close_win_metric_semantics"),
            "label_win_pct": metrics.get("label_win_pct"),
            "hit5_5d_pct": metrics.get("hit5_5d_pct"),
            "hit10_5d_pct": metrics.get("hit10_5d_pct"),
            "hit5_guard_5d_pct": metrics.get("hit5_guard_5d_pct"),
            "hit10_guard_5d_pct": metrics.get("hit10_guard_5d_pct"),
            "avg_max_high_5d_pct": metrics.get("avg_max_high_5d_pct"),
            "min_max_high_5d_pct": metrics.get("min_max_high_5d_pct"),
            "max_max_high_5d_pct": metrics.get("max_max_high_5d_pct"),
            "win_1d_pct": metrics.get("win_1d_pct"),
            "avg_1d_pct": metrics.get("avg_1d_pct"),
            "min_1d_pct": metrics.get("min_1d_pct"),
            "max_1d_pct": metrics.get("max_1d_pct"),
            "win_3d_pct": metrics.get("win_3d_pct"),
            "close_win_1d_pct": metrics.get("close_win_1d_pct"),
            "close_win_3d_pct": metrics.get("close_win_3d_pct"),
            "close_win_5d_pct": metrics.get("close_win_5d_pct"),
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
            (
                f"{decision}: 5D 목표터치 확률 {probability_pct:.1f}% / 기준 {threshold_pct:.1f}% "
                f"({gap:+.1f}%p). "
                if threshold_pct is not None and gap is not None
                else f"{decision}: 5D 목표터치 확률 {probability_pct:.1f}% / Top{model_rank} 선발. "
            )
            + f"{action}. "
            + " · ".join(drivers)
        ),
    }


def admission_model_summary(market: str) -> Dict[str, Any]:
    bundle = load_admission_model(market)
    metrics = _metrics(bundle)
    raw_threshold = bundle.get("prob_threshold")
    has_probability_floor = raw_threshold is not None
    threshold = float(raw_threshold) if has_probability_floor else 0.0
    tail_threshold = _safe_float(bundle.get("max_stop_probability"))
    if tail_threshold is None:
        tail_threshold = _safe_float(bundle.get("tail_risk_prob_threshold"))
    target_pct = _target_pct_from_label(bundle.get("label"))
    return {
        "version": RUNTIME_VERSION,
        "market": bundle.get("market"),
        "model_name": bundle.get("model_name"),
        "label": bundle.get("label"),
        "label_description": bundle.get("label_description"),
        "objective": _objective_text(bundle),
        "target_return_pct": target_pct,
        "feature_set": bundle.get("feature_set"),
        "selection_rule": bundle.get("selection_rule"),
        "prob_threshold": threshold if has_probability_floor else None,
        "prob_threshold_pct": round(threshold * 100.0, 2) if has_probability_floor else None,
        "tail_risk_prob_threshold": tail_threshold,
        "tail_risk_prob_threshold_pct": round(tail_threshold * 100.0, 2) if tail_threshold is not None else None,
        "has_tail_risk_gate": tail_threshold is not None,
        "tail_risk_label": bundle.get("tail_risk_label"),
        "topn": int(bundle.get("topn") or 1),
        "model_path": bundle.get("_model_path"),
        "has_probability_floor": has_probability_floor,
        "threshold_label": f"{round(threshold * 100.0, 2):g}%" if has_probability_floor else f"Top{int(bundle.get('topn') or 1)} 선발",
        "validation": {
            "n": metrics.get("n"),
            "active_runs": metrics.get("active_runs"),
            "active_days": metrics.get("active_days"),
            "win_metric_semantics": metrics.get("win_metric_semantics"),
            "close_win_metric_semantics": metrics.get("close_win_metric_semantics"),
            "label_win_pct": metrics.get("label_win_pct"),
            "hit5_5d_pct": metrics.get("hit5_5d_pct"),
            "hit10_5d_pct": metrics.get("hit10_5d_pct"),
            "hit5_guard_5d_pct": metrics.get("hit5_guard_5d_pct"),
            "hit10_guard_5d_pct": metrics.get("hit10_guard_5d_pct"),
            "avg_max_high_5d_pct": metrics.get("avg_max_high_5d_pct"),
            "min_max_high_5d_pct": metrics.get("min_max_high_5d_pct"),
            "max_max_high_5d_pct": metrics.get("max_max_high_5d_pct"),
            "avg_min_low_5d_pct": metrics.get("avg_min_low_5d_pct"),
            "min_min_low_5d_pct": metrics.get("min_min_low_5d_pct"),
            "win_1d_pct": metrics.get("win_1d_pct"),
            "avg_1d_pct": metrics.get("avg_1d_pct"),
            "min_1d_pct": metrics.get("min_1d_pct"),
            "max_1d_pct": metrics.get("max_1d_pct"),
            "win_3d_pct": metrics.get("win_3d_pct"),
            "close_win_1d_pct": metrics.get("close_win_1d_pct"),
            "close_win_3d_pct": metrics.get("close_win_3d_pct"),
            "close_win_5d_pct": metrics.get("close_win_5d_pct"),
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
    raw_threshold = bundle.get("prob_threshold")
    has_probability_floor = raw_threshold is not None
    threshold = float(raw_threshold) if has_probability_floor else 0.0
    promotion_block = _promotion_block_reason(row)
    probability_pct = round(probability * 100.0, 4)
    threshold_pct = round(threshold * 100.0, 4) if has_probability_floor else None
    primary_probability_met = threshold_pct is None or probability >= threshold
    primary_probability_relation = ">=" if primary_probability_met else "<"
    tail_probability = _safe_float(row.get("_tail_risk_probability"))
    max_stop_threshold = _safe_float(bundle.get("max_stop_probability"))
    tail_threshold = max_stop_threshold if max_stop_threshold is not None else _safe_float(bundle.get("tail_risk_prob_threshold"))
    tail_probability_pct = round(tail_probability * 100.0, 4) if tail_probability is not None else None
    tail_threshold_pct = round(tail_threshold * 100.0, 4) if tail_threshold is not None else None
    if tail_threshold is None:
        tail_gate_passed = None
    elif max_stop_threshold is not None:
        tail_gate_passed = bool(tail_probability is not None and tail_probability <= tail_threshold)
    else:
        tail_gate_passed = bool(tail_probability is not None and tail_probability >= tail_threshold)
    tail_gate_text = ""
    if tail_threshold_pct is not None:
        if tail_probability_pct is None:
            label = "-10% stop확률" if max_stop_threshold is not None else "-10% 방어확률"
            tail_gate_text = f" · {label} 미확보"
        else:
            relation = "<=" if max_stop_threshold is not None and tail_gate_passed else ">" if max_stop_threshold is not None else ">=" if tail_gate_passed else "<"
            label = "-10% stop확률" if max_stop_threshold is not None else "-10% 방어확률"
            tail_gate_text = f" · {label} {tail_probability_pct:.1f}% {relation} 기준 {tail_threshold_pct:.1f}%"
    threshold_label = f"{threshold_pct:.1f}%" if threshold_pct is not None else f"Top{int(bundle.get('topn') or 1)} 선발"
    target_pct = _target_pct_from_label(bundle.get("label"))
    section = ADMISSION_SECTION if passed else NEAR_MISS_SECTION
    stop_risk = _safe_float(metrics.get("stop_before_target_5d_pct"))
    stop5 = _safe_float(metrics.get("stop5_pct"))
    bad_path = _safe_float(metrics.get("bad_path_pct"))
    loss_risk_score = max(value for value in (stop_risk, bad_path, 0.0) if value is not None)
    if stop5 is not None:
        loss_risk_score = max(loss_risk_score, stop5)
    stock_name = _stock_name(row, _ticker(row))
    metrics_for_interpretation = {**metrics, "target_return_pct": target_pct}
    target_rate = _round_pct(
        _first_present(
            metrics,
            "label_win_pct",
            "hit10_guard_5d_pct" if target_pct >= 10 else "hit5_guard_5d_pct",
            "hit10_5d_pct" if target_pct >= 10 else "hit5_5d_pct",
        )
    )
    expected_mfe = _touch_expected_value(metrics)
    stress_mfe = _touch_stress_value(metrics)
    ticker = _ticker(row)
    enriched = dict(row)
    enriched.update(
        {
            "stock_name": stock_name,
            "ticker": ticker,
            "market": bundle.get("market"),
            "decision": "ADMISSION_PASS" if passed else "ADMISSION_NEAR_MISS",
            "decision_bucket": "admission_pass" if passed else "admission_near_miss",
            "phase25_oos_win_rate_pct": target_rate,
            "loss_risk_score": _round_pct(_first_present(row, "loss_risk_score", "Loss Risk") or loss_risk_score),
            "final_action": (
                f"Admission 모델 통과 - 5D +{target_pct:.0f}% 목표터치 후보"
                if passed
                else "Admission 모델 기준 미달 - 신규 매수 대기"
            ),
            "entry_condition_text": (
                (
                    f"5D +{target_pct:.0f}% 목표터치 확률 {probability_pct:.1f}% "
                    f"{primary_probability_relation} 운영기준 {threshold_pct:.1f}%{tail_gate_text}"
                )
                if threshold_pct is not None
                else f"5D +{target_pct:.0f}% 목표터치 확률순 {threshold_label}{tail_gate_text}"
            ),
            "stop_condition_text": (
                f"검증 최저 5D고가 {_round_pct(metrics.get('min_max_high_5d_pct'))}% · "
                f"최저 5D종가 {_round_pct(metrics.get('min_5d_pct'))}% · "
                f"stop5 {_round_pct(metrics.get('stop5_pct'))}% 기준"
            ),
            "risk_flags": [
                "SCAN_UNIVERSE_ADMISSION_MODEL",
                f"model={bundle.get('model_name')}",
                f"objective=5d_touch_{target_pct:.0f}",
                f"threshold={threshold_pct:.1f}%" if threshold_pct is not None else f"selection={threshold_label}",
            ]
            + (
                [
                    f"tail_safe_threshold={tail_threshold_pct:.1f}%",
                    f"tail_safe_probability={tail_probability_pct:.1f}%" if tail_probability_pct is not None else "tail_safe_probability_missing",
                ]
                if tail_threshold_pct is not None
                else []
            )
            + ([] if tail_gate_passed is not False else ["TAIL_RISK_THRESHOLD_NOT_MET"])
            + ([] if primary_probability_met else ["ADMISSION_THRESHOLD_NOT_MET"]),
            "_analysis_section": section,
            "_analysis_section_order": 0 if passed else 10,
            "_analysis_section_rank": model_rank,
            "_source_order": "scan_universe_admission_model",
            "scan_universe_admission": {
                "version": RUNTIME_VERSION,
                "market": bundle.get("market"),
                "model_name": bundle.get("model_name"),
                "label": bundle.get("label"),
                "label_description": bundle.get("label_description"),
                "objective": _objective_text(bundle),
                "target_return_pct": target_pct,
                "feature_set": bundle.get("feature_set"),
                "selection_rule": bundle.get("selection_rule"),
                "topn": int(bundle.get("topn") or 1),
                "probability": probability,
                "score": _safe_float(row.get("_admission_score")),
                "score_threshold": _safe_float(bundle.get("score_threshold")),
                "probability_pct": probability_pct,
                "prob_threshold": raw_threshold,
                "prob_threshold_pct": threshold_pct,
                "tail_risk_probability": tail_probability,
                "tail_risk_probability_pct": tail_probability_pct,
                "tail_risk_prob_threshold": tail_threshold,
                "tail_risk_prob_threshold_pct": tail_threshold_pct,
                "tail_risk_gate_passed": tail_gate_passed,
                "threshold_label": threshold_label,
                "has_probability_floor": has_probability_floor,
                "passed": passed,
                "model_rank": model_rank,
                "model_path": bundle.get("_model_path"),
                "feature_coverage_score": features.get("feature_coverage_score"),
                "feature_missing_keys": features.get("feature_missing_keys") or [],
                "feature_values": {
                    "turnover": features.get("turnover"),
                    "volume_ratio": features.get("volume_ratio"),
                    "day_return_pct": features.get("day_return_pct"),
                    "whale_score": features.get("whale_score"),
                },
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
                metrics=metrics_for_interpretation,
                promotion_block_reason=promotion_block,
            ),
            "realized_expectancy_admission": {
                "available": True,
                "policy_version": RUNTIME_VERSION,
                "source": "scan_universe_admission_model",
                "5d_prob": probability_pct,
                "ranking_score_5d": probability_pct,
                "target_return_pct": target_pct,
                "target_touch_win_pct": target_rate,
                "close_defense_5d_pct": _round_pct(metrics.get("close_win_5d_pct")),
                "win_metric_semantics": metrics.get("win_metric_semantics"),
                "hit5_5d_pct": _round_pct(metrics.get("hit5_5d_pct")),
                "hit10_5d_pct": _round_pct(metrics.get("hit10_5d_pct")),
                "hit5_guard_5d_pct": _round_pct(metrics.get("hit5_guard_5d_pct")),
                "hit10_guard_5d_pct": _round_pct(metrics.get("hit10_guard_5d_pct")),
                "base_expected_value_5d_pct": expected_mfe,
                "expected_value_5d_pct": expected_mfe,
                "stress_expected_value_5d_pct": stress_mfe,
                "expected_max_high_5d_pct": expected_mfe,
                "worst_max_high_5d_pct": stress_mfe,
                "stop_first_risk_pct": _round_pct(metrics.get("stop_before_target_5d_pct")),
                "stop5_pct": _round_pct(metrics.get("stop5_pct")),
            },
            "prediction": {
                **(row.get("prediction") if isinstance(row.get("prediction"), dict) else {}),
                "realized_expectancy_5d_prob": probability_pct,
                "ranking_score_5d": probability_pct,
                "admission_policy_version": RUNTIME_VERSION,
                "scan_universe_admission_probability_pct": probability_pct,
                "scan_universe_tail_risk_probability_pct": tail_probability_pct,
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
    return _score_scan_universe_admission_rows_with_bundle(rows, market=market_key, bundle=bundle)


def _score_scan_universe_admission_rows_with_bundle(
    rows: List[Dict[str, Any]],
    *,
    market: str,
    bundle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    market_key = str(market or "").upper().strip()
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
    feature_rows = [features for _, features in prepared]
    model_outputs = _predict_model_outputs(bundle, feature_rows)
    tail_risk_probabilities = _predict_tail_risk_probabilities(bundle, feature_rows)
    scored: List[Dict[str, Any]] = []
    for (row, features), output, tail_risk_probability in zip(prepared, model_outputs, tail_risk_probabilities):
        copy = dict(row)
        copy["_admission_probability"] = output["probability"]
        copy["_admission_score"] = output["score"]
        copy["_tail_risk_probability"] = tail_risk_probability
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
    raw_threshold = bundle.get("prob_threshold")
    threshold = float(raw_threshold) if raw_threshold is not None else 0.0
    topn = max(1, int(bundle.get("topn") or 1))
    scored = score_scan_universe_admission_rows(rows, market=market_key)
    pass_records: List[Dict[str, Any]] = []
    near_records: List[Dict[str, Any]] = []
    blocked_records: List[Dict[str, Any]] = []
    liquidity_blocked_records: List[Dict[str, Any]] = []
    all_records: List[Dict[str, Any]] = []
    selected_tickers: set[str] = set()
    pass_candidates: List[Tuple[int, Dict[str, Any], float]] = []

    for rank, row in enumerate(scored, start=1):
        probability = float(row.get("_admission_probability") or 0.0)
        ticker = _ticker(row)
        tail_gate_passed, _tail_threshold, _tail_probability = _tail_risk_gate(bundle, row)
        if not ticker or probability < threshold or not tail_gate_passed or _promotion_block_reason(row):
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
            block_reason = _promotion_block_reason(row)
            if block_reason:
                if block_reason == LOW_LIQUIDITY_REJECT_REASON:
                    if len(liquidity_blocked_records) < blocked_limit:
                        liquidity_blocked_records.append(record)
                elif len(blocked_records) < blocked_limit:
                    blocked_records.append(record)
                continue
            if len(near_records) < near_limit:
                near_records.append(record)
            if (
                len(near_records) >= near_limit
                and len(blocked_records) >= blocked_limit
                and len(liquidity_blocked_records) >= blocked_limit
            ):
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
        "liquidity_blocked": liquidity_blocked_records,
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
    has_probability_floor = summary.get("has_probability_floor")
    threshold_pct = None if has_probability_floor is False else _safe_float(summary.get("prob_threshold_pct"))
    if threshold_pct is None and has_probability_floor is not False:
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
        if has_probability_floor is False:
            message = f"운영 통과 후보 {passed_count}개가 있습니다. 확률 바닥 없이 Top{topn} 선택규칙으로 선발했습니다."
        else:
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
    "KIS_SHADOW_SECTION",
    "NEAR_MISS_SECTION",
    "RUNTIME_VERSION",
    "UNIVERSE_INPUT_VERSION",
    "admission_model_summary",
    "admission_run_status",
    "build_kis_shadow_admission_records",
    "kis_shadow_gate_status",
    "load_kis_shadow_model",
    "merge_kis_prefilter_evidence_into_rows",
    "build_scan_universe_admission_input_rows",
    "build_scan_universe_admission_records",
    "score_scan_universe_admission_rows",
]
