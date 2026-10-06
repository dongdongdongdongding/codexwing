import pandas as pd

from modules.db_manager import DBManager
from multi_agent.tools.normalize_verified_archive_daily import original_matches
from multi_agent.tools.repair_issued_outcomes import recompute


def test_original_identity_requires_unique_ticker_reference_and_timestamp():
    row = {"ticker": "037710.KS", "entry_reference_price": 48804,
           "recommended_at": "2026-07-12T00:37:42.20095+00:00"}
    original = {**row, "recommended_at": "2026-07-12T00:37:42.200950Z"}
    assert original_matches(row, [original])
    assert not original_matches(row, [original, original])
    assert not original_matches(row, [{**original, "entry_reference_price": 43850}])
    assert not original_matches(row, [{**original, "recommended_at": "2026-07-13T00:00:00Z"}])
    assert not original_matches(row, [])


def test_generic_sync_cannot_overwrite_normalized_bundle_or_clear_exclusion():
    db = DBManager.__new__(DBManager)
    row = {"ticker": "037710.KS", "entry_reference_price": 48804,
           "base_trade_date": "2026-07-13", "return_1d_pct": 0.912201,
           "return_30d_pct": None, "validation_excluded": True,
           "validation_excluded_reason": "FEATURE_MISSING:position,tier",
           "feature_snapshot": {"scanner_feature": 1, "daily_outcome_basis": {
               "source": "KIS:J:adjusted", "adjusted_base_close": 43850}}}
    incoming = {"entry_reference_price": 43850, "return_1d_pct": 99,
                "return_30d_pct": 99, "base_trade_date": "2026-07-14",
                "feature_snapshot": {"new_feature": 2, "daily_outcome_basis": {"source": "raw"}},
                "validation_excluded": False, "validation_excluded_reason": None}
    merged = db._merge_non_empty_payload(row, incoming)
    for key in row:
        if key != "feature_snapshot":
            assert merged[key] == row[key]
    assert merged["feature_snapshot"] == {**row["feature_snapshot"], "new_feature": 2}
    assert db._merge_non_empty_payload(row, {"feature_snapshot": None})["feature_snapshot"] == row["feature_snapshot"]


def test_explicit_provider_basis_preserves_original_reference_and_all_exclusions():
    days = pd.bdate_range("2026-07-13", periods=3)
    prices = pd.DataFrame({"date": days, "adj_close": [100, 110, 105],
                           "adj_high": [101, 111, 106], "volume": [100, 100, 100]})
    row = {"base_trade_date": "2026-07-13", "entry_reference_price": 120,
           "validation_excluded": False, "feature_snapshot": {"scanner": "preserved"}}
    patch, basis = recompute(row, row, prices, days, price_source="KIS:J:adjusted")
    assert basis["source"] == "KIS:J:adjusted"
    assert patch["return_1d_pct"] == 10
    assert "entry_reference_price" not in patch
    assert "validation_excluded" not in patch
    assert patch["feature_snapshot"]["scanner"] == "preserved"
