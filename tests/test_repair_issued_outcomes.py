import pandas as pd
import pytest

from multi_agent.tools.repair_issued_outcomes import QUARANTINE, recompute


def sample():
    days = pd.bdate_range("2026-08-24", periods=7)
    prices = pd.DataFrame({"date": days, "adj_close": [200, 202, 204, 206, 208, 210, 212],
                           "adj_high": [201, 204, 206, 212, 210, 211, 213]})
    row = {"base_trade_date": "2026-08-24", "ticker": "X.KS", "market": "KOSPI",
           "entry_reference_price": 98, "scan_entry_reference_price": 98,
           "validation_excluded": True, "validation_excluded_reason": QUARANTINE}
    original = {"validation_excluded": True, "validation_excluded_reason": "FEATURE_MISSING:x"}
    return row, original, prices, days


def test_adjusted_close_labels_preserve_issued_price_and_original_exclusion():
    row, original, prices, days = sample()
    patch, basis = recompute(row, original, prices, days)
    assert patch["return_1d_pct"] == 1.0
    assert patch["return_5d_pct"] == 5.0
    assert patch["hit_5pct_within_5d"] is True
    assert "entry_reference_price" not in patch
    assert "scan_entry_reference_price" not in patch
    assert patch["validation_excluded"] is True
    assert patch["validation_excluded_reason"] == "FEATURE_MISSING:x"
    assert basis["contract_pnl"] is False
    assert basis["adjusted_base_close"] == 200
    assert recompute({**row, **patch}, original, prices, days)[0] == {}


@pytest.mark.parametrize("missing", [0, 2, 6])
def test_missing_first_middle_or_last_market_session_is_not_compressed(missing):
    row, original, prices, days = sample()
    with pytest.raises(ValueError, match="incomplete"):
        recompute(row, original, prices.drop(missing), days)


def test_other_exclusions_are_never_restored_or_removed():
    row, original, prices, days = sample()
    row["validation_excluded_reason"] = "NEW_EXCLUSION"
    patch, _ = recompute(row, original, prices, days)
    assert "validation_excluded_reason" not in patch


def test_immature_window_remains_unknown_and_invalid_price_fails():
    row, original, prices, days = sample()
    patch, _ = recompute(row, original, prices.iloc[:3], days[:3])
    assert patch.get("return_5d_pct") is None
    assert patch.get("hit_5pct_within_5d") is None
    prices["adj_high"] = prices["adj_high"].astype(float)
    prices.loc[1, "adj_high"] = float("inf")
    with pytest.raises(ValueError, match="invalid"):
        recompute(row, original, prices, days)
