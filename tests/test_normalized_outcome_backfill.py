from multi_agent.tools.backfill_scanner_full_returns import _build_update_payload


def test_unadjusted_fallback_cannot_refill_normalized_immature_labels():
    row = {"return_5d_pct":None,"feature_snapshot":{"daily_outcome_basis":{
        "kind":"adjusted_signal_close_to_close","asof":"2026-10-02"}}}
    assert _build_update_payload(row,{"return_5d_pct":99}) == {}
    other = {"feature_snapshot":{"daily_outcome_basis":{
        "kind":"adjusted_signal_close_to_close","asof":"2026-10-01"}},"return_5d_pct":99}
    assert _build_update_payload(row,other) == {}


def test_legacy_backfill_still_fills_missing_cells_only():
    patch = _build_update_payload({"return_1d_pct":3},{"return_1d_pct":9,"return_3d_pct":4})
    assert "return_1d_pct" not in patch
    assert patch["return_3d_pct"] == 4


def test_new_issued_rows_use_dedicated_refresh_even_before_first_normalization():
    assert _build_update_payload({"run_id":"SWING-CAND-20261007"}, {"return_1d_pct":2.}) == {}
