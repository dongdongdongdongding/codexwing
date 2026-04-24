"""Schema SSOT tests — guard against silent field drops + synthetic defaults."""
from modules.db_schema import (
    SCAN_RESULT_COLUMNS,
    DEFAULT_FALLBACK_KEYS,
    build_scan_result_payload,
    _to_int_or_none,
    _to_float_or_none,
    _to_pct_or_none,
)


def test_empty_data_yields_nulls_not_synthetic_defaults():
    """Missing fields must stay None — never coerced to 0/'Unknown'/'' etc."""
    payload = build_scan_result_payload({}, overrides={})
    assert payload["alpha_score"] is None
    assert payload["tech_score"] is None
    assert payload["whale_score"] is None
    assert payload["ml_prob"] is None
    assert payload["fund_status"] is None
    assert payload["tier"] is None
    assert payload["volume"] is None
    assert payload["model_trace_status"] is None
    assert payload["model_error"] is None
    assert payload["entry_reference_price"] is None


def test_overrides_win():
    payload = build_scan_result_payload(
        {"alpha_score": 50},
        overrides={"market": "KOSPI", "alpha_score": 99},
    )
    assert payload["market"] == "KOSPI"
    assert payload["alpha_score"] == 99


def test_renamed_source_keys():
    """Scanner uses 'name'/'note'/'initial_trend'; DB uses 'stock_name'/'strategy'/'trend'."""
    payload = build_scan_result_payload(
        {"name": "Samsung", "note": "Momentum", "initial_trend": "UP"},
        overrides={},
    )
    assert payload["stock_name"] == "Samsung"
    assert payload["strategy"] == "Momentum"
    assert payload["trend"] == "UP"


def test_no_silent_drop_for_inferred_fields():
    """Regression: model_trace_status / model_error were silently dropped before SSOT."""
    payload = build_scan_result_payload(
        {"model_trace_status": "phase25_chosen", "model_error": "timeout"},
        overrides={},
    )
    assert payload["model_trace_status"] == "phase25_chosen"
    assert payload["model_error"] == "timeout"


def test_pct_clamp():
    payload = build_scan_result_payload({"ml_prob": 150}, overrides={})
    assert payload["ml_prob"] == 100.0
    payload = build_scan_result_payload({"ml_prob": -10}, overrides={})
    assert payload["ml_prob"] == 0.0
    payload = build_scan_result_payload({"ml_prob": "abc"}, overrides={})
    assert payload["ml_prob"] is None


def test_fallback_keys_only_used_when_primary_missing():
    payload = build_scan_result_payload(
        {"theme_routing_path": "primary", "routing_path": "fallback"},
        overrides={},
        fallback_keys=DEFAULT_FALLBACK_KEYS,
    )
    assert payload["theme_routing_path"] == "primary"

    payload = build_scan_result_payload(
        {"routing_path": "fallback"},
        overrides={},
        fallback_keys=DEFAULT_FALLBACK_KEYS,
    )
    assert payload["theme_routing_path"] == "fallback"


def test_all_columns_unique():
    cols = [c[0] for c in SCAN_RESULT_COLUMNS]
    assert len(cols) == len(set(cols)), f"duplicate columns: {[c for c in cols if cols.count(c) > 1]}"


def test_int_coercion_handles_floats_and_strings():
    assert _to_int_or_none("42") == 42
    assert _to_int_or_none(42.7) == 42
    assert _to_int_or_none("") is None
    assert _to_int_or_none(None) is None
    assert _to_int_or_none("nope") is None


def test_float_coercion_rejects_nan():
    assert _to_float_or_none("3.14") == 3.14
    assert _to_float_or_none(float("nan")) is None
    assert _to_float_or_none("") is None
    assert _to_float_or_none(None) is None
