import numpy as np
import pandas as pd
import pytest

from research.freeze_lowliq_history_scope import history_scope, requests_for_scope


def frame(code, dates, close=None):
    return pd.DataFrame({'code': code, 'date': pd.to_datetime(dates),
                         'adj_close': np.ones(len(dates)) if close is None else close})


def test_all_codes_including_ineligible_and_nontrading_are_covered():
    days = pd.bdate_range('2020-01-01', periods=250)
    a = frame('A', days)
    # B disappears before signal start but contributes to preceding index context.
    b = frame('B', [days[0], days[175], days[179]])
    raw = pd.concat([a, b], ignore_index=True)
    scope, _ = history_scope(raw, days[180])
    assert set(scope.loc[scope.code.eq('B'), 'date']) == set(b.date)
    assert set(scope.loc[scope.code.eq('A'), 'date']) == set(days[50:])


def test_long_up_run_extends_before_nominal_lookback():
    days = pd.bdate_range('2020-01-01', periods=250)
    scope, rules = history_scope(frame('A', days, np.arange(1,251)), days[200])
    assert len(scope) == 250
    assert rules['up_run_boundary_extensions'] == 1


def test_fit_snapshot_can_extend_boundary_even_if_current_prices_do_not():
    days = pd.bdate_range('2020-01-01', periods=250)
    raw = frame('A', days)
    scope, rules = history_scope(raw, days[200], pd.Series(np.arange(1,251)))
    assert len(scope) == 250
    assert rules['up_run_boundary_extensions'] == 1


def test_old_predecessor_of_market_context_is_not_lost():
    days = pd.bdate_range('2020-01-01', periods=250)
    raw = pd.concat([frame('A', days), frame('B', [days[0], days[160]])], ignore_index=True)
    scope, _ = history_scope(raw, days[180])
    old = scope.loc[scope.code.eq('B') & scope.date.eq(days[0])].iloc[0]
    assert old.scope_flags & 4


def test_requests_cover_each_key_once_per_basis_and_never_exceed_90_calendar_days():
    days = pd.bdate_range('2020-01-01', periods=250)
    raw = pd.concat([frame('A', days), frame('B', [days[0], days[-1]])], ignore_index=True)
    requests = requests_for_scope(raw)
    observed = []
    for request in requests:
        assert (pd.Timestamp(request['end_date']) - pd.Timestamp(request['start_date'])).days < 90
        assert len(request['expected_dates']) <= 90
        observed.extend((request['code'], day, request['basis']) for day in request['expected_dates'])
    expected = {(row.code, str(row.date.date()), basis) for row in raw.itertuples()
                for basis in ['nominal','adjusted']}
    assert len(observed) == len(set(observed)) == len(expected)
    assert set(observed) == expected
    assert len({r['id'] for r in requests}) == len(requests)


def test_duplicate_keys_and_short_calendar_fail_closed():
    days = pd.bdate_range('2020-01-01', periods=50)
    raw = frame('A', days)
    with pytest.raises(ValueError, match='invalid_source_keys'):
        history_scope(pd.concat([raw, raw.iloc[-1:]], ignore_index=True), days[30])
    with pytest.raises(ValueError, match='insufficient_context_calendar'):
        history_scope(raw, days[5])
    with pytest.raises(ValueError, match='invalid_request_width'):
        requests_for_scope(raw, 101)
