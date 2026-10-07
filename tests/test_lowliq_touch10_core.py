import numpy as np
import pandas as pd
import pytest

from modules.kr_contract_settlement import settle
from research.lowliq_touch10_core import FEATS, stock_features, feature_frame, training_labels, rank_and_cap


def bars(n=180):
    rng = np.random.default_rng(42)
    close = 100 * np.exp(np.cumsum(rng.normal(0, .015, n)))
    return pd.DataFrame({'date':pd.bdate_range('2025-01-01',periods=n),'code':'000001','market':'KOSPI',
                         'adj_open':close,'adj_high':close*1.02,'adj_low':close*.98,'adj_close':close,
                         'volume':100000.,'amount':1e9,'marcap':1e11})


def quiet(n=15):
    frame = bars(n)
    frame[['adj_open','adj_close']] = 100.
    frame.adj_high = 101.
    frame.adj_low = 99.
    return frame


def test_complete_quiet_windows_are_zero_not_dropped_and_maturity_is_explicit():
    b = quiet()
    labels = training_labels(b, b.date)
    assert labels.iloc[:5].target.eq(0).all()
    assert labels.iloc[:5].status.eq('resolved').all()
    assert labels.iloc[0].label_available_date == b.date.iloc[10]
    assert labels.iloc[5:].target.isna().all()
    assert labels.iloc[5:].status.eq('pending_maturity').all()


def test_early_touch_does_not_bypass_training_label_availability():
    b = quiet()
    b.loc[1, 'adj_high'] = 110
    labels = training_labels(b, b.date)
    assert labels.iloc[0].target == 1
    assert labels.iloc[0].label_available_date == b.date.iloc[10]
    limited = training_labels(b.iloc[:5], b.date.iloc[:5])
    assert limited.iloc[0].status == 'pending_maturity'


def test_missing_session_unfilled_and_halted_exit_are_not_fake_losers():
    b = quiet()
    missing = training_labels(b.drop(index=5), b.date)
    assert missing.iloc[0].status == 'data_error' and np.isnan(missing.iloc[0].target)
    b.loc[1, 'volume'] = 0
    assert training_labels(b, b.date).iloc[0].status == 'unfilled_entry'
    b = quiet()
    b.loc[10, 'volume'] = 0
    assert training_labels(b, b.date).iloc[0].status == 'pending_exit'
    b.loc[3, 'adj_high'] = 110
    assert training_labels(b, b.date).iloc[0].target == 1


def test_invalid_traded_bar_cannot_create_touch():
    b = quiet()
    b.loc[4, ['adj_high','adj_low']] = [110, 120]
    row = training_labels(b, b.date).iloc[0]
    assert row.status == 'data_error' and np.isnan(row.target)


def test_label_vectorization_matches_independent_contract_settlement():
    b = bars(150)
    labels = training_labels(b, b.date)
    for i, day in enumerate(b.date):
        result = settle(b, list(b.date), day, 10)
        if result['status'] == 'resolved':
            assert labels.iloc[i].status == 'resolved'
            assert labels.iloc[i].target == result['touch']
        else:
            assert np.isnan(labels.iloc[i].target)


@pytest.mark.parametrize('monotone', [False, True])
def test_last_only_features_equal_full_history_including_long_up_run(monotone):
    b = bars(400)
    if monotone:
        b[['adj_open','adj_close']] = np.arange(1, 401)[:,None].repeat(2,axis=1)
        b.adj_high = b.adj_close * 1.02
        b.adj_low = b.adj_close * .98
    full = stock_features(b).iloc[-1:]
    latest = stock_features(b, last_only=True)
    pd.testing.assert_frame_equal(full, latest, check_exact=False, rtol=1e-10, atol=1e-10)
    if monotone:
        assert latest.consec_up.iloc[0] == 399


def test_prediction_features_ignore_labels_and_reject_future_rows():
    b = bars()
    prices = b[['code','date','adj_open','adj_high','adj_low','adj_close']]
    a = feature_frame(b, prices, only_date=b.date.iloc[-1])
    changed = b.assign(target=1., exited=True, delist_date=pd.Timestamp('2099-01-01'))
    pd.testing.assert_frame_equal(feature_frame(changed,prices,only_date=b.date.iloc[-1]),a)
    assert len(a) == 1 and set(FEATS).issubset(a)
    with pytest.raises(ValueError, match='future_input'):
        feature_frame(b,prices,only_date=b.date.iloc[-2])


def test_missing_future_labels_never_remove_eligible_test_candidate():
    b = quiet(180)
    prices = b[['code','date','adj_open','adj_high','adj_low','adj_close']]
    assert training_labels(b, b.date).iloc[-1].status == 'pending_maturity'
    result = feature_frame(b,prices,only_date=b.date.iloc[-1])
    assert result.code.tolist() == ['000001']


def test_cadence_is_causal_and_ties_use_code():
    calendar = list(pd.bdate_range('2026-07-01', periods=10))
    prior = {}
    firings = []
    for day in calendar:
        frame = pd.DataFrame({'date':[day]*4,'code':['4','2','3','1'],'score':[.7]*4})
        original, actual = rank_and_cap(frame, calendar, prior)
        assert original.code.tolist() == ['1','2','3']
        prior[str(day.date())] = bool(len(actual))
        firings.append(bool(len(actual)))
    assert firings == [True,True,True,False,False,True,True,True,False,False]
    with pytest.raises(ValueError, match='missing_prior'):
        rank_and_cap(frame,calendar,{})
