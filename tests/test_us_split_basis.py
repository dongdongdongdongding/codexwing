from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from modules import us_split_basis as basis
from modules.us_symbol_lineage import daily_bar_issues
from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools.us_daily_session_refresh import _validate_merged_bars


def sample(nominal=False):
    ref = basis.reference()
    rows = deepcopy(ref['verified_adjusted_rows'])
    if nominal:
        rows.update(ref['known_nominal_rows'])
    return pd.DataFrame([{'date': pd.Timestamp(day), 'symbol': 'VWAV', 'source': 'yfinance',
                          **dict(zip(ref['fields'], values))} for day, values in rows.items()])


def test_only_two_proven_rows_change_and_repeat_is_exactly_unchanged():
    raw = sample(nominal=True)
    original = raw.copy(deep=True)
    expected = sample()
    actual = basis.normalize_known_split_rows(raw)
    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(raw, original)
    pd.testing.assert_frame_equal(basis.normalize_known_split_rows(actual), actual)
    changed = ~(raw.eq(actual) | (raw.isna() & actual.isna())).all(axis=1)
    assert raw.loc[changed, 'date'].dt.strftime('%Y-%m-%d').tolist() == ['2026-09-15', '2026-09-16']
    assert daily_bar_issues(actual).eq('').all()
    assert daily_bar_issues(raw).ne('').sum() == 2
    np.testing.assert_allclose(raw.dollar_volume, actual.dollar_volume, rtol=1e-15)


@pytest.mark.parametrize('field', basis.reference()['fields'])
def test_unknown_numeric_revision_is_not_repaired_or_released(field):
    raw = sample(nominal=True).query("date == '2026-09-15'").copy()
    raw[field] += .001
    pd.testing.assert_frame_equal(basis.normalize_known_split_rows(raw), raw)
    assert daily_bar_issues(raw).ne('').all()
    corrected = sample().query("date == '2026-09-15'").copy()
    corrected[field] += .001
    assert daily_bar_issues(corrected).ne('').all()


def test_identity_dates_missing_fields_and_duplicate_index_are_scoped():
    raw = sample(nominal=True).query("date >= '2026-09-14'").copy()
    raw.index = [0] * len(raw)
    expected = sample().query("date >= '2026-09-14'").copy()
    expected.index = raw.index
    pd.testing.assert_frame_equal(basis.normalize_known_split_rows(raw), expected)
    for key, value in [('symbol', 'NFE'), ('source', 'another_provider'), ('date', pd.Timestamp('2025-01-01'))]:
        other = raw.copy(); other[key] = value
        pd.testing.assert_frame_equal(basis.normalize_known_split_rows(other), other)
        assert not basis.verified_split_rows(other).any()
    assert not basis.verified_split_rows(expected.drop(columns=['volume'])).any()


def test_real_extraction_refresh_and_known_fixed_provider_are_idempotent():
    for nominal in [True, False]:
        raw = sample(nominal=nominal)
        payload = raw.set_index('date')[['open', 'high', 'low', 'raw_close', 'adj_close', 'volume']]
        payload = payload.rename(columns={'raw_close': 'Close', 'adj_close': 'Adj Close'})
        actual = bf._extract_yfinance_frame(payload, 'VWAV')
        expected = sample().reindex(columns=actual.columns)
        pd.testing.assert_frame_equal(actual, expected)
        assert _validate_merged_bars(expected, actual, actual.date.max()) == []
    # Unknown source revisions are no longer accepted as unchanged old quarantine.
    changed = actual.copy(); changed.loc[changed.date.eq('2026-09-15'), 'volume'] += 1
    with pytest.raises(ValueError, match='unverified_mixed_split_basis'):
        _validate_merged_bars(actual, changed, changed.date.max())


def test_certificate_integrity_is_checked(monkeypatch, tmp_path):
    path = tmp_path / 'reference.json'; path.write_text('{}')
    monkeypatch.setattr(basis, 'REFERENCE', path)
    basis.reference.cache_clear()
    try:
        with pytest.raises(ValueError, match='integrity'):
            basis.reference()
    finally:
        basis.reference.cache_clear()
