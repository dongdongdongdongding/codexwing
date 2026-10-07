import pandas as pd
import pytest

from research.audit_kr_kis_rollover import capture_paths, compare_prices


def test_comparison_keeps_revisions_and_rejects_missing_old_dates():
    old = pd.DataFrame({"date": pd.to_datetime(["2026-10-01", "2026-10-02"]),
        "adj_open": [100., 101.], "adj_high": [103., 104.], "adj_low": [99., 100.],
        "adj_close": [102., 103.], "volume": [10., 20.]})
    revised = old.copy(); revised.loc[1, "adj_close"] = 102.
    later = revised.iloc[[-1]].copy(); later["date"] = pd.Timestamp("2026-10-06")
    out = compare_prices({"X": old}, {"X": pd.concat([revised, later])})
    assert out == [{"code": "X", "date": "2026-10-02", "fields": {"adj_close": [103., 102.]}}]
    assert compare_prices({"X": old}, {"X": pd.concat([old, later])}) == []
    with pytest.raises(ValueError, match="missing_original"):
        compare_prices({"X": old}, {"X": revised.iloc[:1]})


def test_attempt_discovery_retains_original_failure_and_never_uses_other_code(tmp_path):
    for name in ["123456.json", "123456_attempt_002.json", "654321_attempt_003.json"]:
        (tmp_path / name).write_text('{}')
    assert [p.name for p in capture_paths(tmp_path, "123456")] == ["123456.json", "123456_attempt_002.json"]
    assert capture_paths(tmp_path, "111111") == []
