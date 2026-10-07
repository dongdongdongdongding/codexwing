from copy import deepcopy
from fractions import Fraction

import pytest

from research.nominal_share_settlement import settle_nominal, schedule_sha256

DAYS = ['2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09']
SHA = 'a'*64


def bars():
    return [dict(date=d, code='000001', open=100, high=104, low=99, close=101, volume=1000) for d in DAYS]


def action(kind='share_conversion', **kw):
    return dict({'id': 'event1', 'code': '000001', 'kind': kind, 'effective_date': DAYS[2],
                 'available_date': DAYS[2], 'availability_status': 'verified', 'ratio': [2, 1], 'evidence_sha256': SHA}, **kw)


def run(b=None, actions=None, *, coverage_change=None, **kw):
    b = bars() if b is None else b
    actions = [] if actions is None else actions
    coverage = {'code': '000001', 'price_basis': 'nominal', 'start': DAYS[1], 'end': DAYS[-1],
                'evidence_sha256': SHA, 'prices_sha256': schedule_sha256(b),
                'actions_sha256': schedule_sha256(actions)}
    coverage.update(coverage_change or {})
    return settle_nominal(b, DAYS, DAYS[0], code='000001', actions=actions,
                          coverage=coverage, horizon=4, **kw)


def test_no_action_full_horizon_and_cost():
    result = run()
    assert result['status'] == 'resolved' and result['touch'] == 0
    assert result['policy_ret'] == 1 and result['net_ret'] == 0
    assert result['label_available_date'] == DAYS[-1]
    assert not result['source_certified'] and not result['execution_verified']


def test_entry_day_touch_and_later_gap_fill():
    b = bars(); b[1]['high'] = 110
    assert run(b)['exit_cash'] == 105
    b = bars(); b[2].update(open=110, high=111, low=109, close=110)
    result = run(b)
    assert result['exit_date'] == DAYS[2] and result['policy_ret'] == 10
    assert result['net_ret'] == 9


@pytest.mark.parametrize('ratio,price,quantity', [([2,1], 50, 1), ([1,2], 200, 2), ([5,1],20,10)])
def test_split_and_consolidation_conserve_cash_not_quote_ratio(ratio, price, quantity):
    b = bars()
    for bar in b[2:]: bar.update(open=price, high=price, low=price, close=price)
    result = run(b, [action(ratio=ratio)], initial_shares=quantity)
    assert result['status'] == 'resolved' and result['touch'] == 0
    assert result['exit_cash'] == 100*quantity and result['policy_ret'] == 0
    assert result['net_ret'] == -1


def test_delayed_bonus_cannot_be_liquidated_on_exdate():
    b = bars()
    for bar in b[2:]: bar.update(open=53, high=54, low=52, close=53)
    event = action('bonus', ratio=[1,1], available_date=DAYS[-1])
    result = run(b, [event])
    assert result['touch'] == 1 and result['exit_date'] == DAYS[-1]
    assert result['exit_cash'] == 106  # gap over target only when ALL shares tradeable
    assert [r['kind'] for r in result['trace']] == ['entry','bonus','shares_available','exit']


def test_unlisted_bonus_is_unresolved_even_if_adjusted_high_would_touch():
    b = bars()
    for bar in b[2:]: bar.update(open=60, high=70, low=55, close=60)
    result = run(b, [action('bonus', ratio=[1,1], available_date='2026-02-01')])
    assert result['status'] == 'action_unresolved'
    assert result['reason'] == 'unavailable_shares_at_horizon'
    assert result['touch'] is None and result['policy_ret'] is None


def test_bonus_after_horizon_does_not_reprice_earlier_position():
    result = run(actions=[action('bonus', effective_date='2026-02-01', available_date='2026-02-01')])
    assert result['policy_ret'] == 1


def test_effective_on_entry_earns_no_preexisting_share_entitlement():
    result = run(actions=[action(effective_date=DAYS[1], available_date=DAYS[1])])
    assert result['exit_cash'] == 101


@pytest.mark.parametrize('kind', ['rights', 'cash_dividend', 'merger', 'unknown'])
def test_unsupported_entitlement_cannot_use_adjustment_factor(kind):
    result = run(actions=[action(kind, quote_factor=.5)])
    assert result['status'] == 'action_unresolved'
    assert result['reason'] == 'unsupported_entitlement'
    assert result['touch'] is None


def test_exit_before_unsupported_event_has_no_remaining_entitlement():
    b=bars();b[1]['high']=105
    result=run(b,[action('rights')])
    assert result['status']=='resolved' and result['exit_date']==DAYS[1]


def test_share_fraction_never_invents_cash_in_lieu():
    result = run(actions=[action(ratio=[1,2])])
    assert result['reason'] == 'fractional_entitlement'
    assert result['policy_ret'] is None


def test_whole_horizon_required_even_after_early_touch():
    b=bars();b[1]['high']=110
    assert run(b[:-1])['reason']=='missing_horizon_bar'
    result=settle_nominal(b,DAYS[:-1],DAYS[0],code='000001',actions=[],coverage={},horizon=4)
    assert result['status']=='pending_maturity' and result['touch'] is None


@pytest.mark.parametrize('field,value', [('high',90),('volume',-1),('open',True),('close',None)])
def test_invalid_later_bar_does_not_allow_early_success(field,value):
    b=bars();b[1]['high']=110;b[-1][field]=value
    assert run(b)['status']=='data_error'


def test_suspension_is_not_delayed_entry_or_terminal_fill():
    b=bars();b[1].update(open=0,high=0,low=0,close=100,volume=0)
    result=run(b)
    assert result['status']=='unfilled_entry' and result['touch']==0 and result['net_ret']==0
    b=bars();b[-1]['volume']=0
    assert run(b)['status']=='pending_exit'


@pytest.mark.parametrize('change', [
    {'price_basis':'adjusted'}, {'code':'000002'}, {'actions_sha256':'b'*64},
    {'prices_sha256':'b'*64}, {'end':DAYS[-2]}, {'start':DAYS[2]}, {'evidence_sha256':None},
])
def test_coverage_and_exact_inputs_must_bind(change):
    result=run(coverage_change=change)
    assert result['status']=='source_unverified' and result['touch'] is None


def test_simultaneous_and_overlapping_events_not_ordered_by_json():
    events=[action(),action('bonus',id='event2')]
    assert run(actions=events)['reason']=='simultaneous_action_order_unverified'
    events=[action(available_date=DAYS[-1]),action('bonus',id='event2',effective_date=DAYS[3],available_date=DAYS[3])]
    assert run(actions=events)['reason']=='overlapping_pending_entitlements'


def test_unchanged_inputs_and_exact_rational_entitlement():
    b=bars();events=[action('bonus',ratio=[1,5],available_date=DAYS[-1])]
    for bar in b[2:]:bar.update(open=85,high=86,low=84,close=85)
    before=deepcopy((b,events))
    result=run(b,events,initial_shares=5)
    assert result['exit_cash']==510 and result['policy_ret']==2
    assert (b,events)==before
    # Independent cash-flow identity; no price adjustment coefficient involved.
    assert Fraction(str(result['exit_cash'])) == (5+5*Fraction(1,5))*85


def test_later_unknown_order_does_not_change_already_closed_position():
    b=bars();b[1]['high']=106
    result=run(b,[action(),action('bonus',id='second')])
    assert result['status']=='resolved' and result['exit_date']==DAYS[1]


@pytest.mark.parametrize('payload', [[None], ['bad'], {'date':DAYS[0]}])
def test_malformed_bars_are_recorded_not_thrown(payload):
    result=settle_nominal(payload,DAYS,DAYS[0],code='000001',actions=[],coverage={},horizon=4)
    assert result['status']=='data_error'


def test_effective_date_not_in_calendar_cannot_be_silently_skipped():
    result=run(actions=[action(effective_date='2026-01-10',available_date='2026-01-10')])
    assert result['status']=='resolved'  # outside this horizon, no exposure
    calendar=[DAYS[0],DAYS[1],DAYS[3],DAYS[4]]
    a=[action(effective_date=DAYS[2])];b=bars()
    coverage={'code':'000001','price_basis':'nominal','start':DAYS[1],'end':DAYS[-1],
        'evidence_sha256':SHA,'prices_sha256':schedule_sha256(b),'actions_sha256':schedule_sha256(a)}
    result=settle_nominal(b,calendar,DAYS[0],code='000001',actions=a,coverage=coverage,horizon=3)
    assert result['reason']=='effective_date_outside_calendar'


def test_independent_generated_cashflow_cases():
    """240 deterministic synthetic paths checked by independent share-value arrays."""
    import random
    rng=random.Random(20261007)
    for _ in range(240):
        ratio=rng.choice([Fraction(1,2),Fraction(2),Fraction(3),Fraction(1)])
        b=bars(); quantities=[2,2,2*ratio,2*ratio,2*ratio]
        for i in range(1,5):
            # Nominal price intervals chosen independently of the engine.
            center=Fraction(rng.randint(92,109))*2/quantities[i]
            b[i].update(open=float(center),high=float(center+2),low=float(center-2),close=float(center+1))
        event=action(ratio=[ratio.numerator,ratio.denominator])
        result=run(b,[event],initial_shares=2)
        investment=Fraction(str(b[1]['open']))*2
        wealth_high=[Fraction(str(b[i]['high']))*quantities[i] for i in range(1,5)]
        hits=[i for i,w in enumerate(wealth_high,1) if w>=investment*Fraction(105,100)]
        if hits:
            index=hits[0]
            cash=investment*Fraction(105,100)
            if index>1:cash=max(cash,Fraction(str(b[index]['open']))*quantities[index])
            assert result['touch']==1
        else:
            index=4;cash=Fraction(str(b[4]['close']))*quantities[4]
            assert result['touch']==0
        assert result['exit_date']==DAYS[index]
        assert result['exit_cash']==float(cash)
        assert result['policy_ret']==float((cash/investment-1)*100)


def test_planned_listing_date_cannot_release_bonus_shares():
    result=run(actions=[action('bonus', availability_status='planned')])
    assert result['reason']=='availability_unverified'
    assert result['touch'] is None
