"""Single source of truth for market_scan_results column ↔ source-key mapping.

When the scanner adds a new field, register it here ONCE.
Silent drops (the bug behind model_trace_status NULL) are now structurally impossible:
build_scan_result_payload iterates this map.

No fabricated defaults — fields not provided by the scanner stay NULL in DB.
Only deterministic value coercion (string→int/float) is applied here.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def _to_int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if result != result:  # NaN
            return None
        return result
    except (TypeError, ValueError):
        return None


def _to_pct_or_none(value: Any) -> Optional[float]:
    """Clamp to 0-100, return None if not numeric."""
    f = _to_float_or_none(value)
    if f is None:
        return None
    return max(0.0, min(100.0, f))


def _passthrough(value: Any) -> Any:
    return value


def _to_str_list_or_none(value: Any) -> Optional[list]:
    """Normalize rationale/theme_risk into a JSONB-friendly list of strings.

    Planner emits these as List[str]. Tolerate single strings (older artifacts)
    and drop empty/whitespace entries. Return None when the input is empty so
    Supabase stores NULL rather than [].
    """
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else None
    if isinstance(value, (list, tuple)):
        cleaned = [str(item).strip() for item in value if item is not None and str(item).strip()]
        return cleaned or None
    return None


# (db_column, source_key_in_data, coercer)
# source_key=None means the column is computed/derived (caller must pass via overrides).
SCAN_RESULT_COLUMNS: tuple = (
    # Identity
    ("ticker",                          "ticker",                          _passthrough),
    ("stock_name",                      "name",                            _passthrough),  # rename: scanner passes 'name'
    ("market",                          None,                              _passthrough),  # derived: _resolve_submarket
    ("market_type",                     "market_type",                     _passthrough),
    ("scan_mode",                       "scan_mode",                       _passthrough),

    # Scoring (numeric — preserve NULL if missing; do NOT coerce to 0)
    ("alpha_score",                     "alpha_score",                     _to_int_or_none),
    ("tech_score",                      "tech_score",                      _to_int_or_none),
    ("ml_prob",                         "ml_prob",                         _to_pct_or_none),
    ("prob_clean",                      "prob_clean",                      _to_float_or_none),
    ("whale_score",                     "whale_score",                     _to_int_or_none),
    ("foreigner",                       "foreigner",                       _to_float_or_none),
    ("foreign_flow",                    "foreign_flow",                    _to_float_or_none),
    ("institution",                     "institution",                     _to_float_or_none),
    ("institution_flow",                "institution_flow",                _to_float_or_none),
    ("retail",                          "retail",                          _to_float_or_none),
    ("retail_flow",                     "retail_flow",                     _to_float_or_none),
    ("flow_consensus_buying",           "flow_consensus_buying",           _passthrough),
    ("retail_dominant",                 "retail_dominant",                 _passthrough),
    ("dominant",                        "dominant",                        _passthrough),
    ("whale_trend",                     "whale_trend",                     _passthrough),
    ("decision_score",                  "decision_score",                  _to_float_or_none),
    ("conviction_score",                "conviction_score",                _to_float_or_none),

    # Labels (string — keep NULL if missing; no 'Unknown' fabrication)
    ("fund_status",                     "fund_status",                     _passthrough),
    ("trend",                           "initial_trend",                   _passthrough),  # rename
    ("verdict",                         "verdict",                         _passthrough),
    ("tier",                            "tier",                            _passthrough),
    ("volume",                          "volume",                          _passthrough),
    ("volume_ratio",                    "volume_ratio",                    _to_float_or_none),
    ("day_return_pct",                  "day_return_pct",                  _to_float_or_none),
    ("volume_confirmed",                "volume_confirmed",                _passthrough),
    ("context",                         "context",                         _passthrough),
    ("surge",                           "surge",                           _passthrough),
    ("win_rate",                        "win_rate",                        _passthrough),
    ("position",                        "position",                        _passthrough),
    ("strategy",                        "note",                            _passthrough),  # rename: scanner passes 'note'

    # Strategy / orchestration
    ("strategy_family",                 "strategy_family",                 _passthrough),
    ("run_id",                          "run_id",                          _passthrough),
    ("priority_rank",                   "priority_rank",                   _to_int_or_none),
    ("decision",                        "decision",                        _passthrough),
    ("decision_bucket",                 "decision_bucket",                 _passthrough),
    ("outcome_status",                  "outcome_status",                  _passthrough),
    ("quality_flags",                   "quality_flags",                   _passthrough),
    ("recommended_at",                  "recommended_at",                  _passthrough),
    ("outcome_recorded_at",             "outcome_recorded_at",             _passthrough),
    ("horizon",                         "horizon",                         _passthrough),
    ("base_trade_date",                 "base_trade_date",                 _passthrough),
    ("entry_reference_price",           "entry_reference_price",           _to_float_or_none),
    ("source_ref",                      "source_ref",                      _passthrough),

    # Scanner lane / role trace
    ("market_gate",                     "market_gate",                     _passthrough),
    ("scanner_timeframe_profile",       "scanner_timeframe_profile",       _passthrough),
    ("kr_universe_role",                "kr_universe_role",                _passthrough),
    ("selection_lane",                  "selection_lane",                  _passthrough),

    # Planner gate rationale (swing-main-h4x): JSONB lists from planner_handoff.json.
    # Required by priority_watchlist_gap diagnostics so DB-only reports can name
    # the gate cause without re-reading local RUN-* artifacts.
    ("rationale",                       "rationale",                       _to_str_list_or_none),
    ("theme_risk",                      "theme_risk",                      _to_str_list_or_none),
    ("explosive_leader_flag",           "explosive_leader_flag",           _passthrough),
    ("core_trend_flag",                 "core_trend_flag",                 _passthrough),
    ("continuation_eligible",           "continuation_eligible",           _passthrough),
    ("continuation_enabled",            "continuation_enabled",            _passthrough),
    ("continuation_prob_3d",            "continuation_prob_3d",            _to_float_or_none),
    ("continuation_evidence",           "continuation_evidence",           _to_int_or_none),
    ("continuation_gate_reasons",       "continuation_gate_reasons",       _passthrough),

    # Returns (post-scan outcome sync)
    ("latest_return_pct",               "latest_return_pct",               _to_float_or_none),
    ("return_30m_pct",                  "return_30m_pct",                  _to_float_or_none),
    ("return_1h_pct",                   "return_1h_pct",                   _to_float_or_none),
    ("return_close_pct",                "return_close_pct",                _to_float_or_none),
    ("return_1d_pct",                   "return_1d_pct",                   _to_float_or_none),
    ("return_2d_pct",                   "return_2d_pct",                   _to_float_or_none),
    ("return_3d_pct",                   "return_3d_pct",                   _to_float_or_none),
    ("return_5d_pct",                   "return_5d_pct",                   _to_float_or_none),
    ("return_7d_pct",                   "return_7d_pct",                   _to_float_or_none),
    ("return_14d_pct",                  "return_14d_pct",                  _to_float_or_none),
    ("return_30d_pct",                  "return_30d_pct",                  _to_float_or_none),
    ("max_high_return_5d_pct",          "max_high_return_5d_pct",          _to_float_or_none),
    ("hit_5pct_within_5d",              "hit_5pct_within_5d",              _passthrough),
    ("hit_5pct_within_5d_at",           "hit_5pct_within_5d_at",           _passthrough),
    ("swing_target_label_version",      "swing_target_label_version",      _passthrough),

    # Phase25 / model trace
    ("phase25_variant",                 "phase25_variant",                 _passthrough),
    ("phase25_prob",                    "phase25_prob",                    _to_float_or_none),
    ("phase25_signal_direction",        "phase25_signal_direction",        _passthrough),
    ("phase25_raw_auc",                 "phase25_raw_auc",                 _to_float_or_none),
    ("phase25_oos_auc",                 "phase25_oos_auc",                 _to_float_or_none),
    ("phase25_oos_win_rate_pct",        "phase25_oos_win_rate_pct",        _to_float_or_none),
    ("phase25_oos_avg_return_pct",      "phase25_oos_avg_return_pct",      _to_float_or_none),
    ("phase25_shadow_variant",          "phase25_shadow_variant",          _passthrough),
    ("phase25_shadow_prob",             "phase25_shadow_prob",             _to_float_or_none),
    ("phase25_recommended_threshold",   "phase25_recommended_threshold",   _to_float_or_none),
    ("phase25_degraded",                "phase25_degraded",                _passthrough),
    ("performance_updated_at",          "performance_updated_at",          _passthrough),
    ("inference_failed",                "inference_failed",                _passthrough),
    ("model_trace_status",              "model_trace_status",              _passthrough),
    ("model_error",                     "model_error",                     _passthrough),

    # Expected return / exit policy
    ("expected_edge_score",             "expected_edge_score",             _to_float_or_none),
    ("expected_return_1d_pct",          "expected_return_1d_pct",          _to_float_or_none),
    ("expected_return_3d_pct",          "expected_return_3d_pct",          _to_float_or_none),
    ("model_prob_available_count",      "model_prob_available_count",      _to_float_or_none),
    ("model_prob_mean",                 "model_prob_mean",                 _to_float_or_none),
    ("low_model_prob_score",            "low_model_prob_score",            _to_float_or_none),
    ("low_prob_high_score",             "low_prob_high_score",             _to_float_or_none),
    ("expected_edge_inversion_score",   "expected_edge_inversion_score",   _to_float_or_none),
    ("loss_risk_score",                 "loss_risk_score",                 _to_float_or_none),
    ("relative_rank_score",             "relative_rank_score",             _to_float_or_none),
    ("relative_rank_pct",               "relative_rank_pct",               _to_float_or_none),
    ("regime_adjusted_grade",           "regime_adjusted_grade",           _passthrough),
    ("relative_rank_model",             "relative_rank_model",             _passthrough),
    ("target_tp_pct",                   "target_tp_pct",                   _to_float_or_none),
    ("stop_sl_pct",                     "stop_sl_pct",                     _to_float_or_none),
    ("hold_days",                       "hold_days",                       _to_int_or_none),

    # Regime
    ("regime_volatility_20d",           "regime_volatility_20d",           _to_float_or_none),
    ("regime_breadth_pct",              "regime_breadth_pct",              _to_float_or_none),
    ("kospi_chg",                       "kospi_chg",                       _to_float_or_none),
    ("kosdaq_chg",                      "kosdaq_chg",                      _to_float_or_none),
    ("regime_avg_chg",                  "regime_avg_chg",                  _to_float_or_none),

    # Theme
    ("theme_context",                   "theme_context",                   _passthrough),
    ("leader_metrics",                  "leader_metrics",                  _passthrough),
    ("routing_path",                    "routing_path",                    _passthrough),
    ("theme_score_adjustment",          "theme_score_adjustment",          _to_float_or_none),
    ("primary_theme",                   "primary_theme",                   _passthrough),
    ("theme_source",                    "theme_source",                    _passthrough),
    ("theme_inference_status",          "theme_inference_status",          _passthrough),
    ("secondary_themes",                "secondary_themes",                _passthrough),
    ("theme_routing_path",              "theme_routing_path",              _passthrough),

    # Feature provenance (computed by _feature_quality_payload helper, passed via overrides)
    ("feature_origin",                  None,                              _passthrough),
    ("feature_quality",                 None,                              _passthrough),
    ("feature_completeness",            None,                              _passthrough),
    ("feature_missing_fields",          None,                              _passthrough),
    ("validation_excluded",             None,                              _passthrough),
    ("validation_excluded_reason",      None,                              _passthrough),
    ("is_dummy_data",                   None,                              _passthrough),

    # DB write timestamp (NOT data-derived; caller passes via overrides)
    ("created_at",                      None,                              _passthrough),
)


def build_scan_result_payload(
    data: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None,
    *,
    fallback_keys: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a payload dict by mapping data → DB columns via SCAN_RESULT_COLUMNS.

    Rules:
    - Columns with `source_key=None` are skipped unless provided in `overrides`.
    - Columns with a `source_key` pull from data[source_key] and coerce.
    - `overrides` always wins (used for derived fields like market, created_at, feature_quality).
    - `fallback_keys` lets callers say "if data[primary_key] is None, try data[fallback_key]"
      (used for `theme_routing_path` ← `routing_path`).
    - Missing values stay `None` — NEVER fabricate. Downstream `_filter_payload_to_existing_columns`
      drops keys that don't exist in the live DB schema.
    """
    overrides = overrides or {}
    fallback_keys = fallback_keys or {}
    payload: Dict[str, Any] = {}
    for column, source_key, coerce in SCAN_RESULT_COLUMNS:
        if column in overrides:
            payload[column] = overrides[column]
            continue
        if source_key is None:
            continue
        value = data.get(source_key)
        if value is None and source_key in fallback_keys:
            value = data.get(fallback_keys[source_key])
        payload[column] = coerce(value)
    return payload


# Default fallback chain for known scanner aliases (cumulative — column then source).
DEFAULT_FALLBACK_KEYS: Dict[str, str] = {
    "theme_routing_path": "routing_path",
}


REQUIRED_FEATURE_FIELDS_FOR_TRAINING: tuple = (
    "alpha_score",
    "tech_score",
    "ml_prob",
    "whale_score",
    "decision_score",
    "volume_ratio",
    "entry_reference_price",
)
