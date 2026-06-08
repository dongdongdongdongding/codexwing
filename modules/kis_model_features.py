from __future__ import annotations

import json
import math
from typing import Any, Dict, Mapping

from modules.kis_theme_news_evidence import build_kis_theme_news_evidence


KIS_SIDECAR_MODEL_NUMERIC_FEATURES = (
    "kis_current_price",
    "kis_day_change_pct",
    "kis_value_traded",
    "kis_prev_volume_ratio",
    "kis_market_cap",
    "kis_per",
    "kis_pbr",
    "kis_high_250d_gap_pct",
    "kis_low_250d_gap_pct",
    "kis_whale_score",
    "kis_foreigner_1d",
    "kis_institution_1d",
    "kis_retail_1d",
    "kis_whale_flow_3d",
    "kis_whale_flow_10d",
    "kis_daily_bar_count",
    "kis_daily_return_5d_pct",
    "kis_daily_return_20d_pct",
    "kis_daily_return_60d_pct",
    "kis_daily_volume_ratio_20d",
    "kis_daily_ma5",
    "kis_daily_ma20",
    "kis_daily_ma60",
    "kis_daily_prior_20d_high",
    "kis_daily_range_20d_high",
    "kis_daily_range_20d_low",
    "kis_daily_close_location_pct",
    "kis_daily_high_52w",
    "kis_daily_pct_from_52w_high",
    "kis_minute_bar_count",
    "kis_rank_volume",
    "kis_rank_fluctuation",
    "kis_rank_volume_power",
    "kis_vi_triggered",
    "kis_news_title_count",
    "kis_news_source_scope_confidence",
    "kis_news_source_scope_ambiguous",
    "kis_news_promotion_blocked",
    "kis_stock_listed_shares",
    "kis_stock_capital_amount",
    "kis_stock_par_value",
    "kis_financial_revenue_growth_rate",
    "kis_financial_operating_profit_margin",
    "kis_financial_net_income_margin",
    "kis_financial_roe",
    "kis_financial_eps",
    "kis_financial_bps",
    "kis_financial_per",
    "kis_financial_pbr",
    "kis_financial_debt_ratio",
    "kis_financial_current_ratio",
    "kis_financial_reserve_ratio",
)

KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES = (
    "kis_sidecar_present",
    "kis_sidecar_model_ready",
    "kis_sidecar_production_ready",
    "kis_sidecar_coverage_quote_snapshot",
    "kis_sidecar_coverage_daily_ohlcv",
    "kis_sidecar_coverage_daily_ohlcv_50d",
    "kis_sidecar_coverage_minute_ohlcv",
    "kis_sidecar_coverage_investor_flow",
    "kis_sidecar_coverage_rank_membership",
    "kis_sidecar_coverage_vi_status",
    "kis_sidecar_coverage_news_titles",
    "kis_sidecar_coverage_stock_info",
    "kis_sidecar_coverage_financial_ratio",
    "kis_sidecar_coverage_financial_style",
    "kis_sidecar_warning_count",
)

KIS_SIDECAR_CATEGORICAL_FEATURES = (
    "kis_sidecar_contract_version",
    "kis_sidecar_feature_origin",
    "kis_stock_market_code",
    "kis_stock_market_name",
    "kis_stock_type",
    "kis_stock_listed_date",
    "kis_stock_status_code",
    "kis_stock_sector_name",
    "kis_stock_standard_industry_code",
    "kis_stock_kospi200_item",
    "kis_stock_trade_stop",
    "kis_stock_admin_item",
    "kis_news_source_scope",
    "kis_financial_statement_period",
)

KIS_PREFILTER_NUMERIC_FEATURES = (
    "kis_prefilter_present",
    "kis_prefilter_rejected",
    "kis_prefilter_selection_score",
    "kis_prefilter_rank_volume",
    "kis_prefilter_rank_fluctuation",
    "kis_prefilter_rank_volume_power",
    "kis_prefilter_source_count",
    "kis_prefilter_vi_triggered",
    "kis_prefilter_quote_ok",
    "kis_prefilter_flow_ok",
    "kis_prefilter_quote_current_price",
    "kis_prefilter_quote_day_change_pct",
    "kis_prefilter_quote_value_traded",
    "kis_prefilter_quote_volume",
    "kis_prefilter_quote_prev_volume_ratio",
    "kis_prefilter_quote_market_cap",
    "kis_prefilter_quote_per",
    "kis_prefilter_quote_pbr",
    "kis_prefilter_flow_valid",
    "kis_prefilter_flow_whale_score",
    "kis_prefilter_flow_foreigner_1d",
    "kis_prefilter_flow_institution_1d",
    "kis_prefilter_flow_retail_1d",
    "kis_prefilter_flow_foreigner_3d",
    "kis_prefilter_flow_institution_3d",
    "kis_prefilter_flow_retail_3d",
    "kis_prefilter_flow_foreigner_10d",
    "kis_prefilter_flow_institution_10d",
    "kis_prefilter_flow_retail_10d",
    "kis_prefilter_score_value_traded",
    "kis_prefilter_score_prev_volume_ratio",
    "kis_prefilter_score_day_change_pct",
    "kis_prefilter_score_market_cap",
    "kis_prefilter_score_status_warning_penalty",
    "kis_prefilter_score_whale_score",
    "kis_prefilter_score_vi_triggered",
    "kis_prefilter_score_volume_rank",
    "kis_prefilter_score_fluctuation_rank",
    "kis_prefilter_score_volume_power_rank",
    "kis_prefilter_warning_count",
)

KIS_PREFILTER_CATEGORICAL_FEATURES = (
    "kis_prefilter_feature_origin",
    "kis_prefilter_snapshot_feature_version",
    "kis_prefilter_source_signature",
    "kis_prefilter_reject_reason",
    "kis_prefilter_quote_source_status",
    "kis_prefilter_quote_status_warning",
    "kis_prefilter_flow_source",
    "kis_prefilter_flow_source_status",
    "kis_prefilter_flow_unit",
)

KIS_THEME_NEWS_NUMERIC_FEATURES = (
    "kis_theme_news_available",
    "kis_theme_news_kis_backed",
    "kis_theme_news_evidence_score",
    "kis_theme_news_news_checked",
    "kis_theme_news_news_count",
    "kis_theme_news_headline_count",
    "kis_theme_news_positive_tag_count",
    "kis_theme_news_risk_tag_count",
    "kis_theme_news_source_scope_confidence",
    "kis_theme_news_promotion_blocked",
    "kis_theme_news_vi_triggered",
    "kis_theme_news_prefilter_source_count",
)

KIS_THEME_NEWS_CATEGORICAL_FEATURES = (
    "kis_theme_news_level",
    "kis_theme_news_primary_theme",
    "kis_theme_news_kis_sector_name",
    "kis_theme_news_standard_industry_code",
    "kis_theme_news_source_scope",
    "kis_theme_news_top_positive_tag",
    "kis_theme_news_top_risk_tag",
)

KIS_NUMERIC_FEATURES = (
    *KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES,
    *KIS_SIDECAR_MODEL_NUMERIC_FEATURES,
    *KIS_PREFILTER_NUMERIC_FEATURES,
    *KIS_THEME_NEWS_NUMERIC_FEATURES,
)
KIS_CATEGORICAL_FEATURES = (
    *KIS_SIDECAR_CATEGORICAL_FEATURES,
    *KIS_PREFILTER_CATEGORICAL_FEATURES,
    *KIS_THEME_NEWS_CATEGORICAL_FEATURES,
)


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _nested_dict(source: Any, *keys: str) -> Dict[str, Any]:
    current: Any = source
    for key in keys:
        current = _json_dict(current)
        if not current:
            return {}
        current = current.get(key)
    return _json_dict(current)


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        parsed = _json_dict(value)
        if parsed:
            return parsed
    return {}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        if isinstance(value, str):
            text = value.replace(",", "").replace("%", "").strip()
            if not text:
                return None
            lower = text.lower()
            if lower in {"true", "yes", "y", "on"}:
                return 1.0
            if lower in {"false", "no", "n", "off"}:
                return 0.0
            value = text
        numeric = float(value)
    except Exception:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _flag(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "none", "null", "nan"}:
            return None
        if text in {"1", "true", "yes", "y", "on", "ok", "pass", "passed"}:
            return 1.0
        if text in {"0", "false", "no", "n", "off", "fail", "failed"}:
            return 0.0
    return 1.0 if bool(value) else 0.0


def _count_items(value: Any) -> float | None:
    if isinstance(value, (list, tuple, set)):
        return float(len(value))
    if isinstance(value, Mapping):
        return float(len(value))
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_kis_sidecar(row: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = _json_dict(row.get("feature_snapshot"))
    leader_metrics = _first_dict(
        row.get("leader_metrics"),
        row.get("_leader_metrics"),
        snapshot.get("leader_metrics"),
        snapshot.get("_leader_metrics"),
    )
    return _first_dict(
        row.get("kis_sidecar"),
        row.get("_kis_sidecar"),
        _nested_dict(leader_metrics, "kis_sidecar"),
        snapshot.get("kis_sidecar"),
        snapshot.get("_kis_sidecar"),
        _nested_dict(snapshot, "leader_metrics", "kis_sidecar"),
        _nested_dict(snapshot, "_leader_metrics", "kis_sidecar"),
    )


def extract_kis_prefilter(row: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = _json_dict(row.get("feature_snapshot"))
    return _first_dict(
        row.get("kis_operational_prefilter"),
        snapshot.get("kis_operational_prefilter"),
    )


def _extract_sidecar_model_features(row: Mapping[str, Any], sidecar: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = _json_dict(row.get("feature_snapshot"))
    return _first_dict(
        sidecar.get("model_candidate_features"),
        row.get("kis_model_candidate_features"),
        snapshot.get("kis_model_candidate_features"),
        _nested_dict(snapshot, "kis_sidecar", "model_candidate_features"),
        _nested_dict(snapshot, "leader_metrics", "kis_sidecar", "model_candidate_features"),
        _nested_dict(snapshot, "_leader_metrics", "kis_sidecar", "model_candidate_features"),
    )


def flatten_kis_model_features(row: Mapping[str, Any]) -> Dict[str, Any]:
    sidecar = extract_kis_sidecar(row)
    model_features = _extract_sidecar_model_features(row, sidecar)
    coverage = _json_dict(sidecar.get("coverage"))
    readiness = _json_dict(sidecar.get("replacement_readiness"))
    out: Dict[str, Any] = {}

    sidecar_present = bool(sidecar or model_features)
    out["kis_sidecar_present"] = 1.0 if sidecar_present else 0.0
    out["kis_sidecar_model_ready"] = _flag(readiness.get("model_sidecar_ready"))
    out["kis_sidecar_production_ready"] = _flag(readiness.get("production_replacement_ready"))
    out["kis_sidecar_warning_count"] = _count_items(sidecar.get("warnings")) or 0.0 if sidecar_present else 0.0
    out["kis_sidecar_contract_version"] = _text(sidecar.get("contract_version"))
    out["kis_sidecar_feature_origin"] = _text(sidecar.get("feature_origin")) or ("kis_openapi_sidecar" if sidecar_present else None)
    for key in (
        "quote_snapshot",
        "daily_ohlcv",
        "daily_ohlcv_50d",
        "minute_ohlcv",
        "investor_flow",
        "rank_membership",
        "vi_status",
        "news_titles",
        "stock_info",
        "financial_ratio",
        "financial_style",
    ):
        out[f"kis_sidecar_coverage_{key}"] = _flag(coverage.get(key))
    for key in KIS_SIDECAR_MODEL_NUMERIC_FEATURES:
        out[key] = _safe_float(model_features.get(key))
    for key in KIS_SIDECAR_CATEGORICAL_FEATURES:
        if key not in out:
            out[key] = _text(model_features.get(key))

    prefilter = extract_kis_prefilter(row)
    rank = _json_dict(prefilter.get("rank"))
    quote = _json_dict(prefilter.get("quote"))
    flow = _json_dict(prefilter.get("flow"))
    score = _json_dict(prefilter.get("score_components"))
    sources = prefilter.get("sources") if isinstance(prefilter.get("sources"), list) else []
    prefilter_present = bool(prefilter)
    out["kis_prefilter_present"] = 1.0 if prefilter_present else 0.0
    out["kis_prefilter_rejected"] = _flag(bool(prefilter.get("reject_reason"))) if prefilter_present else 0.0
    out["kis_prefilter_selection_score"] = _safe_float(prefilter.get("selection_score"))
    out["kis_prefilter_rank_volume"] = _safe_float(rank.get("volume_rank"))
    out["kis_prefilter_rank_fluctuation"] = _safe_float(rank.get("fluctuation_rank"))
    out["kis_prefilter_rank_volume_power"] = _safe_float(rank.get("volume_power_rank"))
    out["kis_prefilter_source_count"] = float(len(sources)) if prefilter_present else 0.0
    out["kis_prefilter_vi_triggered"] = _flag(prefilter.get("vi_triggered"))
    out["kis_prefilter_quote_ok"] = _flag(prefilter.get("quote_ok"))
    out["kis_prefilter_flow_ok"] = _flag(prefilter.get("flow_ok"))
    out["kis_prefilter_quote_current_price"] = _safe_float(quote.get("current_price"))
    out["kis_prefilter_quote_day_change_pct"] = _safe_float(quote.get("day_change_pct"))
    out["kis_prefilter_quote_value_traded"] = _safe_float(quote.get("value_traded"))
    out["kis_prefilter_quote_volume"] = _safe_float(quote.get("volume"))
    out["kis_prefilter_quote_prev_volume_ratio"] = _safe_float(quote.get("prev_volume_ratio"))
    out["kis_prefilter_quote_market_cap"] = _safe_float(quote.get("market_cap"))
    out["kis_prefilter_quote_per"] = _safe_float(quote.get("per"))
    out["kis_prefilter_quote_pbr"] = _safe_float(quote.get("pbr"))
    out["kis_prefilter_flow_valid"] = _flag(flow.get("valid"))
    out["kis_prefilter_flow_whale_score"] = _safe_float(flow.get("whale_score"))
    out["kis_prefilter_flow_foreigner_1d"] = _safe_float(flow.get("foreigner_1d"))
    out["kis_prefilter_flow_institution_1d"] = _safe_float(flow.get("institution_1d"))
    out["kis_prefilter_flow_retail_1d"] = _safe_float(flow.get("retail_1d"))
    out["kis_prefilter_flow_foreigner_3d"] = _safe_float(flow.get("foreigner_3d"))
    out["kis_prefilter_flow_institution_3d"] = _safe_float(flow.get("institution_3d"))
    out["kis_prefilter_flow_retail_3d"] = _safe_float(flow.get("retail_3d"))
    out["kis_prefilter_flow_foreigner_10d"] = _safe_float(flow.get("foreigner_10d"))
    out["kis_prefilter_flow_institution_10d"] = _safe_float(flow.get("institution_10d"))
    out["kis_prefilter_flow_retail_10d"] = _safe_float(flow.get("retail_10d"))
    out["kis_prefilter_score_value_traded"] = _safe_float(score.get("value_traded"))
    out["kis_prefilter_score_prev_volume_ratio"] = _safe_float(score.get("prev_volume_ratio"))
    out["kis_prefilter_score_day_change_pct"] = _safe_float(score.get("day_change_pct"))
    out["kis_prefilter_score_market_cap"] = _safe_float(score.get("market_cap"))
    out["kis_prefilter_score_status_warning_penalty"] = _safe_float(score.get("status_warning_penalty"))
    out["kis_prefilter_score_whale_score"] = _safe_float(score.get("whale_score"))
    out["kis_prefilter_score_vi_triggered"] = _safe_float(score.get("vi_triggered"))
    out["kis_prefilter_score_volume_rank"] = _safe_float(score.get("volume_rank"))
    out["kis_prefilter_score_fluctuation_rank"] = _safe_float(score.get("fluctuation_rank"))
    out["kis_prefilter_score_volume_power_rank"] = _safe_float(score.get("volume_power_rank"))
    out["kis_prefilter_warning_count"] = _count_items(prefilter.get("warnings")) or 0.0 if prefilter_present else 0.0
    out["kis_prefilter_feature_origin"] = _text(prefilter.get("feature_origin")) or ("kis_openapi_prefilter" if prefilter_present else None)
    out["kis_prefilter_snapshot_feature_version"] = _text(prefilter.get("snapshot_feature_version"))
    out["kis_prefilter_source_signature"] = "|".join(sorted(str(item) for item in sources if str(item).strip())) or None
    out["kis_prefilter_reject_reason"] = _text(prefilter.get("reject_reason"))
    out["kis_prefilter_quote_source_status"] = _text(quote.get("source_status"))
    out["kis_prefilter_quote_status_warning"] = _text(quote.get("status_warning"))
    out["kis_prefilter_flow_source"] = _text(flow.get("flow_source"))
    out["kis_prefilter_flow_source_status"] = _text(flow.get("source_status"))
    out["kis_prefilter_flow_unit"] = _text(flow.get("flow_unit"))

    theme_news = build_kis_theme_news_evidence(row)
    theme_payload = _json_dict(theme_news.get("theme"))
    news_payload = _json_dict(theme_news.get("news"))
    action_payload = _json_dict(theme_news.get("market_action"))
    positive_tags = news_payload.get("positive_tags") if isinstance(news_payload.get("positive_tags"), list) else []
    risk_tags = news_payload.get("risk_tags") if isinstance(news_payload.get("risk_tags"), list) else []
    headlines = news_payload.get("headlines") if isinstance(news_payload.get("headlines"), list) else []
    prefilter_sources = (
        action_payload.get("prefilter_sources")
        if isinstance(action_payload.get("prefilter_sources"), list)
        else []
    )
    out["kis_theme_news_available"] = _flag(theme_news.get("available"))
    out["kis_theme_news_kis_backed"] = _flag(theme_news.get("kis_backed"))
    out["kis_theme_news_evidence_score"] = _safe_float(theme_news.get("evidence_strength_score"))
    out["kis_theme_news_news_checked"] = _flag(news_payload.get("checked"))
    out["kis_theme_news_news_count"] = _safe_float(news_payload.get("news_count"))
    out["kis_theme_news_headline_count"] = float(len(headlines))
    out["kis_theme_news_positive_tag_count"] = float(len(positive_tags))
    out["kis_theme_news_risk_tag_count"] = float(len(risk_tags))
    out["kis_theme_news_source_scope_confidence"] = _safe_float(news_payload.get("source_scope_confidence"))
    out["kis_theme_news_promotion_blocked"] = _flag(news_payload.get("promotion_blocked") or theme_news.get("promotion_blocked"))
    out["kis_theme_news_vi_triggered"] = _flag(action_payload.get("vi_triggered"))
    out["kis_theme_news_prefilter_source_count"] = float(len(prefilter_sources))
    out["kis_theme_news_level"] = _text(theme_news.get("evidence_strength_level"))
    out["kis_theme_news_primary_theme"] = _text(theme_payload.get("primary_theme"))
    out["kis_theme_news_kis_sector_name"] = _text(theme_payload.get("kis_sector_name"))
    out["kis_theme_news_standard_industry_code"] = _text(theme_payload.get("kis_standard_industry_code"))
    out["kis_theme_news_source_scope"] = _text(news_payload.get("source_scope"))
    out["kis_theme_news_top_positive_tag"] = _text(positive_tags[0]) if positive_tags else None
    out["kis_theme_news_top_risk_tag"] = _text(risk_tags[0]) if risk_tags else None
    return out


__all__ = [
    "KIS_CATEGORICAL_FEATURES",
    "KIS_NUMERIC_FEATURES",
    "KIS_PREFILTER_CATEGORICAL_FEATURES",
    "KIS_PREFILTER_NUMERIC_FEATURES",
    "KIS_SIDECAR_CATEGORICAL_FEATURES",
    "KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES",
    "KIS_SIDECAR_MODEL_NUMERIC_FEATURES",
    "KIS_THEME_NEWS_CATEGORICAL_FEATURES",
    "KIS_THEME_NEWS_NUMERIC_FEATURES",
    "extract_kis_prefilter",
    "extract_kis_sidecar",
    "flatten_kis_model_features",
]
