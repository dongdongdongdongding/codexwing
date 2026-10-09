import copy

import pandas as pd
import pytest

from research.inventory_expanded_historical_references import reconcile_old_events
from research.inventory_historical_reference_gaps import inventory_code


def case():
    raw = pd.DataFrame([
        dict(code='000001', date=pd.Timestamp('2024-01-02'), open=100, close=100,
             volume=10, amount=1000, adj_factor=1., stocks=100),
        dict(code='000001', date=pd.Timestamp('2024-01-03'), open=60, close=60,
             volume=10, amount=600, adj_factor=1., stocks=100)])
    quotes = {'2024-01-02': dict(stck_clpr='100', acml_vol='10', acml_tr_pbmn='1000',
                                prdy_vrss='0', prdy_vrss_sign='3'),
              '2024-01-03': dict(stck_clpr='60', acml_vol='10', acml_tr_pbmn='600',
                                prdy_vrss='10', prdy_vrss_sign='2')}
    old = inventory_code(raw, quotes)['events']
    return old, {'000001': raw}, {'000001': quotes}


@pytest.mark.parametrize('factor,status', [
    (1., 'PRIMARY_REVIEW_REQUIRED'), (2., 'EXACT_FACTOR_AGREEMENT'),
    (2.0000000000000004, 'ARITHMETIC_RESIDUAL')])
def test_each_old_event_is_rechecked_even_without_a_queue_entry(factor, status):
    old, groups, quotes = case()
    groups['000001'].loc[1, 'adj_factor'] = factor
    before = copy.deepcopy(old)
    result = reconcile_old_events(old, groups, quotes)
    assert result[0]['current_classification'] == status
    assert old == before


def test_removed_provider_date_cannot_be_declared_resolved():
    old, groups, quotes = case()
    del quotes['000001']['2024-01-02']
    with pytest.raises(ValueError, match='unverified_old_event_scope'):
        reconcile_old_events(old, groups, quotes)


def test_changed_raw_value_cannot_be_declared_resolved():
    old, groups, quotes = case()
    groups['000001'].loc[1, 'open'] = 50
    with pytest.raises(ValueError, match='changed_old_event_nominal'):
        reconcile_old_events(old, groups, quotes)


def test_unsupported_quote_cannot_be_declared_resolved():
    old, groups, quotes = case()
    quotes['000001']['2024-01-03']['prdy_vrss_sign'] = '0'
    with pytest.raises(ValueError, match='old_event_no_longer_comparable'):
        reconcile_old_events(old, groups, quotes)


def test_duplicate_old_event_aborts():
    old, groups, quotes = case()
    with pytest.raises(ValueError, match='duplicate_old_event'):
        reconcile_old_events(old * 2, groups, quotes)


def test_missing_source_date_aborts():
    old, groups, quotes = case()
    groups['000001'] = groups['000001'].iloc[:1]
    with pytest.raises(ValueError, match='unverified_old_event_scope'):
        reconcile_old_events(old, groups, quotes)
