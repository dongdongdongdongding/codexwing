from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.audit_kr_adjustment_asof import adjustment_block, rebuild, index_features, asof_adjustment

BUILDER = Path(__file__).resolve().parents[1] / 'research/data/build_px_delisted_20261007.py.txt'


def source(n=80):
    return pd.DataFrame({'code': '000001', 'date': pd.date_range('2026-01-01', periods=n),
                         'open': 100., 'high': 101., 'low': 99., 'close': 100.,
                         'volume': 1000., 'stocks': 100.})


def test_future_row_count_reclassifies_old_large_price_drop():
    raw = source(40)
    raw.loc[5:, ['open', 'high', 'low', 'close']] *= .5
    original = raw.copy(deep=True)
    full = rebuild(raw, adjustment_block(BUILDER))
    prefix = rebuild(raw.iloc[:10], adjustment_block(BUILDER))
    assert full.loc[5, 'event_factor'] == 2 and full.loc[5, 'limit_rule']
    assert prefix.loc[5, 'event_factor'] == 1 and not prefix.loc[5, 'limit_rule']
    assert full.loc[5, 'adj_close'] == 100 and prefix.loc[5, 'adj_close'] == 50
    pd.testing.assert_frame_equal(raw, original)


def test_later_stock_count_change_is_backdated_into_earlier_prices():
    raw = source()
    raw.loc[50:, ['open', 'high', 'low', 'close']] /= 1.2
    raw.loc[70:, 'stocks'] *= 1.2
    full = rebuild(raw, adjustment_block(BUILDER))
    prefix = rebuild(raw.iloc[:60], adjustment_block(BUILDER))
    assert full.loc[50, 'lag_rule'] and not full.loc[50, 'limit_rule']
    assert full.loc[50, 'event_factor'] == 1.2
    assert prefix.loc[50, 'event_factor'] == 1
    assert np.isclose(full.loc[50, 'adj_close'], 100)
    assert np.isclose(prefix.loc[50, 'adj_close'], 100 / 1.2)


def test_stable_source_and_same_day_split_have_stable_prefix():
    raw = source(40)
    raw.loc[5:, ['open', 'high', 'low', 'close']] *= .5
    raw.loc[5:, 'stocks'] *= 2
    full = rebuild(raw, adjustment_block(BUILDER))
    prefix = rebuild(raw.iloc[:10], adjustment_block(BUILDER))
    pd.testing.assert_frame_equal(full.iloc[:10].reset_index(drop=True), prefix)


def test_unreviewed_builder_and_duplicate_dates_rejected(tmp_path):
    path = tmp_path / 'builder.py'
    path.write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError, match='unreviewed'):
        adjustment_block(path)
    raw = source()
    with pytest.raises(ValueError, match='duplicate'):
        rebuild(pd.concat([raw, raw.iloc[-1:]]), adjustment_block(BUILDER))


def test_unsorted_input_rejected_instead_of_changing_event_order():
    with pytest.raises(ValueError, match='sorted'):
        rebuild(source().iloc[::-1], adjustment_block(BUILDER))


def test_one_symbols_revised_return_changes_shared_market_context():
    a = source(80)
    b = source(80)
    b['code'] = '000002'
    raw = pd.concat([a, b], ignore_index=True)
    raw['market'] = 'KOSPI'
    raw['marcap'] = 1e10
    prices = raw.close.copy()
    revised = prices.copy()
    revised.loc[60:79] *= .8
    before = index_features(raw, prices)['KOSPI']
    after = index_features(raw, revised)['KOSPI']
    # Code 000002 did not change, but its market-context feature would change.
    assert before.iloc[-1].idx_mom20 == 0
    assert after.iloc[-1].idx_mom20 < 0
    assert after.iloc[-1].idx_vol20 > 0


def test_date_limited_reconstruction_is_invariant_to_every_future_input():
    raw = source(80)
    cutoff = raw.date.iloc[59]
    changed = raw.copy()
    changed.loc[60:, ['open', 'high', 'low', 'close', 'stocks', 'volume']] *= 100
    block = adjustment_block(BUILDER)
    expected = rebuild(raw.iloc[:60], block)
    pd.testing.assert_frame_equal(asof_adjustment(raw, cutoff, block), expected)
    pd.testing.assert_frame_equal(asof_adjustment(changed, cutoff, block), expected)
    assert asof_adjustment(raw, cutoff, block).date.max() == cutoff
    with pytest.raises(ValueError, match='signal_date'):
        asof_adjustment(raw, cutoff + pd.Timedelta(hours=9), block)
    raw.loc[0, 'date'] = pd.NaT
    with pytest.raises(ValueError, match='source_date'):
        asof_adjustment(raw, cutoff, block)
