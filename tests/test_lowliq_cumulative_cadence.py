import numpy as np
import pandas as pd
import pytest

from research.freeze_lowliq_cumulative_cadence import cumulative_rank_and_cap, derive
from research.lowliq_touch10_core import rank_and_cap


def frame(date):
    return pd.DataFrame({'date': [date]*4, 'code': ['4','3','2','1'],
                         'market': ['KOSPI']*4, 'liq': [1e9]*4, 'score': [.1,.2,.3,.3]})


@pytest.mark.parametrize('gaps', [False, True])
def test_all_prefix_and_rolling_caps_preserve_ranked_tickers(gaps):
    calendar = pd.bdate_range('2026-07-01', periods=500)
    missing = np.random.default_rng(71).random(len(calendar)) < .3
    prior = {}
    for i, date in enumerate(calendar):
        f = frame(date)
        if gaps and missing[i]:f = f.iloc[:0]
        original, picks = cumulative_rank_and_cap(str(date.date()), f, calendar, prior)
        assert original.code.tolist() == ([] if f.empty else ['1','2','3'])
        assert picks.code.tolist() in [[], original.code.tolist()]
        prior[str(date.date())] = bool(len(picks))
        flags = list(prior.values())
        assert sum(flags) <= 3*(i+1)//5
        assert sum(flags[-5:]) <= 3
        if not gaps:assert sum(flags) == 3*(i+1)//5


def test_original_boundary_overshoot_is_retained_and_amendment_fixes_it():
    calendar = pd.bdate_range('2026-07-01', periods=62)
    old, new = {}, {}
    for date in calendar:
        day = str(date.date())
        old[day] = bool(len(rank_and_cap(frame(date), calendar, old)[1]))
        new[day] = bool(len(cumulative_rank_and_cap(day, frame(date), calendar, new)[1]))
    assert sum(old.values()) == 38 and sum(new.values()) == 37
    assert 5*sum(old.values())/62 > 3
    assert 2 <= 5*sum(new.values())/62 <= 3


def test_missing_abstention_and_future_prior_are_rejected():
    dates = pd.bdate_range('2026-07-01', periods=3)
    with pytest.raises(ValueError, match='incomplete_prior'):
        cumulative_rank_and_cap(str(dates[1].date()), frame(dates[1]), dates, {})
    with pytest.raises(ValueError, match='incomplete_prior'):
        cumulative_rank_and_cap(str(dates[0].date()), frame(dates[0]), dates,
                                {str(dates[1].date()): False})


def test_derivation_replays_parent_and_never_changes_scores_or_source_picks():
    dates = pd.bdate_range('2026-07-01', periods=12)
    prior, records, frames = {}, [], []
    for date in dates:
        day = str(date.date());f = frame(date);f['real_0'] = f.score;f = f.drop(columns='score')
        original, picks = rank_and_cap(f.assign(score=f.real_0), dates, prior)
        cols = ['code','market','liq','score']
        records.append({'date': day, 'input_max_date': day, 'universe_rows': len(f),
            'universe_sha256': 'synthetic', 'model_hashes': {'real_0': 'fixed'},
            'kind': 'retrospective_reconstruction', 'publication_allowed': False,
            'variants': {'real_0': {'source_picks': original[cols].to_dict('records'),
                                     'picks': picks[cols].to_dict('records')}}})
        prior[day] = bool(len(picks));frames.append(f)
    first = derive(dates, records, frames, {'real_0': 'fixed'})
    assert first == derive(dates, records, frames, {'real_0': 'fixed'})
    assert all(r['variants']['real_0']['source_picks'] == p['variants']['real_0']['source_picks']
               for r,p in zip(first[0], records))
    with pytest.raises(ValueError, match='incomplete_parent'):
        derive(dates, records[:-1], frames[:-1], {'real_0': 'fixed'})
    records[0]['variants']['real_0']['picks'] = []
    with pytest.raises(ValueError, match='changed_cadence'):
        derive(dates, records, frames, {'real_0': 'fixed'})
