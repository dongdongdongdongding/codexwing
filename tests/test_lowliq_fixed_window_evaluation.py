from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from research.lowliq_fixed_window_evaluation import evaluate, fingerprint, block_ci, placebo_excess, VARIANTS


def fixture():
    spec=json.loads((Path(__file__).resolve().parents[1]/'research/prereg_lowliq_touch10_cumulative_20261007.json').read_text())
    calendar=pd.bdate_range('2026-01-05',periods=60).strftime('%Y-%m-%d').tolist()
    fixed=calendar[:50]
    spec['fit_cutoff']='2025-12-31'
    spec['test_signal_start'],spec['test_signal_end']=fixed[0],fixed[-1]
    universe=[];outcomes=[]
    for i,day in enumerate(fixed):
        for code in range(8):
            key={'date':day,'code':f'{code:06d}','market':'KOSPI'}
            universe.append(key)
            outcomes.append({**key,'status':'resolved','policy_ret':5.0 if code<3 else 0.0,
                             'touch':int(code<3),'horizon_end':calendar[i+10]})
    source={name:{d:[f'{c:06d}' for c in (range(3) if name.startswith('real') else range(3,6))]
                  for d in fixed} for name in VARIANTS}
    # Three fires per complete five-day block; 30/50 => 3 per five sessions.
    picks={name:{d:source[name][d] if i%5 in (1,3,4) else [] for i,d in enumerate(fixed)} for name in VARIANTS}
    proof={'source_verdict':'ACCEPTED_FOR_RESEARCH','source_sha256':spec['source']['panel_sha256'],
           'calendar_verified':True,'contract_verified':True,'complete_universe_verified':True,
           'model_score_replay_verified':True,'source_observed_through':calendar[-1],
           'as_of':calendar[-1],'fixed_signal_dates':fixed}
    data=[spec,calendar,universe,picks,source,proof,outcomes]
    bind(data)
    return data


def bind(data):
    spec,calendar,universe,picks,source,proof,outcomes=data
    proof['input_binding_sha256']=fingerprint({'spec':spec,'calendar':calendar,'universe':universe,
                                              'selections':picks,'source_picks':source})
    proof['outcomes_sha256']=fingerprint(outcomes)


def run(data):
    return evaluate(*data[:6], lambda:data[6])


def poison():
    raise AssertionError('outcomes accessed before preflight')


@pytest.mark.parametrize('change', [
    {'source_verdict':'INPUT_REJECTED_FOR_QUALIFICATION'}, {'calendar_verified':False},
    {'contract_verified':'true'}, {'complete_universe_verified':False},
    {'model_score_replay_verified':False}, {'source_sha256':'wrong'},
    {'source_observed_through':'2026-01-06'}, {'fixed_signal_dates':[]},
])
def test_source_and_maturity_refuse_before_outcome_access(change):
    data=fixture();data[5].update(change)
    result=evaluate(*data[:6],poison)
    assert result['status']=='NOT_EVALUABLE_PREFLIGHT' and result['outcomes_loaded'] is False
    assert 'variants' not in result


def test_input_binding_checked_before_loading():
    data=fixture();data[2][0]['code']='999999'
    assert evaluate(*data[:6],poison)['reason']=='input_binding_mismatch'


def test_outcome_binding_changed():
    data=fixture();data[6][0]['policy_ret']=6
    assert run(data)['reason']=='outcome_binding_mismatch'


def test_primary_all_metrics_pass_but_never_publication():
    result=run(fixture())
    assert result['status']=='RETROSPECTIVE_SCREEN_PASS'
    assert result['publication_allowed'] is False and result['per_pick_probability_calibrated'] is False
    assert set(result['variants'])==set(VARIANTS)
    real=result['variants']['real_0']
    assert real['selected']==90 and real['resolved_filled']==90 and real['touch_all_selected']==1
    assert real['net_ev']==4 and real['same_day_excess']==5
    assert real['paired_noise_excess']==5
    assert real['net_block']['ci']==[4,4] and real['excess_block']['ci']==[5,5]
    assert real['ticker_placebo']['raw_p']==1/5001
    assert real['ticker_placebo']['family_adjusted_p']==4/5001
    assert result['firing_dates_per_five_sessions']==3 and result['max_rolling_five']==3
    assert len(result['circular_shifts'])==49
    assert all(r['status']=='DIAGNOSTIC_ONLY' for r in result['circular_shifts'])
    assert result['variants']['noise_0']['screen_pass'] is False


def test_unfilled_is_zero_with_no_fee_and_not_removed():
    data=fixture();day=data[1][1]
    row=next(r for r in data[6] if r['date']==day and r['code']=='000000')
    row.update(status='unfilled_entry',touch=0,policy_ret=0)
    bind(data);result=run(data)['variants']['real_0']
    assert result['selected']==90 and result['unfilled']==1 and result['resolved_filled']==89
    assert result['touch_all_selected']==89/90 and result['touch_filled_only']==1
    assert result['net_ev']==pytest.approx(4*89/90)
    assert result['cost_sensitivities']['0.3']['net_ev']==pytest.approx(4.7*89/90)


@pytest.mark.parametrize('status', ['pending_exit','data_error','action_unresolved','pending_maturity'])
def test_unresolved_control_never_disappears_from_primary(status):
    data=fixture();day=data[1][1]
    row=next(r for r in data[6] if r['date']==day and r['code']=='000007')
    row.update(status=status,policy_ret=None,touch=None)
    bind(data);result=run(data)
    assert result['status']=='NOT_EVALUABLE_OUTCOMES' and 'variants' not in result


def test_unresolved_abstention_only_rows_kept_in_shift_diagnostics():
    data=fixture();row=data[6][0];row.update(status='pending_exit',policy_ret=None,touch=None)
    bind(data);result=run(data)
    assert result['status']=='RETROSPECTIVE_SCREEN_PASS'
    assert len(result['circular_shifts'])==49
    assert any(r['status']=='UNAVAILABLE' for r in result['circular_shifts'])


def test_same_market_controls_not_pooled_with_unselected_market():
    data=fixture()
    # All primary selected records KOSPI; changing KOSDAQ returns must not
    # contaminate its controls. Noise selects partly KOSDAQ and still has controls.
    for rows in [data[2],data[6]]:
        for row in rows:
            if int(row['code'])>=5:row['market']='KOSDAQ'
    for row in data[6]:
        if row['market']=='KOSDAQ':row.update(policy_ret=-50,touch=0)
    bind(data);result=run(data)['variants']['real_0']
    assert result['same_day_excess']==5
    assert result['markets']['KOSDAQ']['selected']==0


def test_control_absence_refuses_instead_of_zero_baseline():
    data=fixture()
    for rows in [data[2],data[6]]:
        for row in rows:
            if int(row['code'])<3:row['market']='KOSDAQ'
    bind(data)
    assert run(data)['reason']=='same_date_market_control_missing'


def test_bad_horizon_or_missing_seed_is_rejected():
    data=fixture();data[6][0]['horizon_end']=data[1][-1];bind(data)
    with pytest.raises(ValueError,match='wrong_outcome_horizon'):run(data)
    data=fixture();data[3].pop('noise_2');bind(data)
    with pytest.raises(ValueError,match='missing_or_extra_seed'):run(data)


def test_block_bootstrap_retains_abstentions_and_weights_counts():
    sums=[10,0,30,0,20];counts=[1,0,3,0,2]
    result=block_ci(sums,counts,block=5,draws=5000,seed=20261007)
    assert result=={'ci':[10,10],'empty_draws':0}


def test_placebo_equal_universe_ties_cannot_claim_edge():
    result=placebo_excess([([1,1,1,1],2)],0,draws=5000,seed=20261007,family=4)
    assert result['raw_p']==1 and result['family_adjusted_p']==1 and result['null_mean']==0


def test_input_records_are_not_mutated():
    data=fixture();before=deepcopy(data)
    run(data)
    assert data==before


def test_good_secondary_seed_cannot_rescue_failed_primary():
    data=fixture()
    data[3]['real_0']=deepcopy(data[3]['noise_0'])
    data[4]['real_0']=deepcopy(data[4]['noise_0'])
    bind(data);result=run(data)
    assert result['status']=='REJECTED_SCREEN'
    assert result['variants']['real_1']['screen_pass'] is True
    assert 'touch_target_missed' in result['variants']['real_0']['reasons']


def test_frequency_uses_all_sessions_and_enforces_rolling_cap():
    data=fixture()
    for name in VARIANTS:
        data[3][name]={d:data[4][name][d] if i%5!=0 else [] for i,d in enumerate(data[1][:50])}
    bind(data);result=run(data)
    assert result['firing_dates_per_five_sessions']==4
    assert result['status']=='REJECTED_SCREEN'
    assert 'cadence_target_missed' in result['variants']['real_0']['reasons']
    assert 'rolling_cadence_exceeded' in result['variants']['real_0']['reasons']


def test_cheaper_cost_sensitivity_cannot_rescue_primary_failure():
    data=fixture();keys={(d,c) for d,codes in data[3]['real_0'].items() for c in codes}
    changed=0
    for row in data[6]:
        if (row['date'],row['code']) in keys and changed<27:
            row.update(policy_ret=-10,touch=0);changed+=1
    bind(data);result=run(data);real=result['variants']['real_0']
    assert real['touch_all_selected']==.7
    assert real['net_ev']==-.5
    assert real['cost_sensitivities']['0.3']['net_ev']==pytest.approx(.2)
    assert result['status']=='REJECTED_SCREEN' and 'net_block_not_positive' in real['reasons']


@pytest.mark.parametrize('field,value', [('as_of','not-a-date'),('source_observed_through','9999-99-99'),('as_of',None)])
def test_invalid_observation_dates_never_open_loader(field,value):
    data=fixture();data[5][field]=value
    result=evaluate(*data[:6],poison)
    assert result['ready'] is False and 'invalid_observation_dates' in result['reasons']


def test_training_cutoff_cannot_enter_test_window():
    data=fixture();data[0]['fit_cutoff']=data[1][0]
    result=evaluate(*data[:6],poison)
    assert 'fit_cutoff_not_before_test' in result['reasons']


@pytest.mark.parametrize('field,value', [('minimum_resolved',1),('touch_rate_all_selected_min',.5),
    ('paired_excess_min_pp',0),('unresolved_selected_or_control_max',1)])
def test_registered_target_cannot_be_relaxed(field,value):
    data=fixture();data[0]['evaluation'][field]=value;bind(data)
    with pytest.raises(ValueError,match='unsupported_preregistered_contract'):
        evaluate(*data[:6],poison)


def test_ticker_placebo_agrees_with_exact_small_universe_null():
    # Six equally likely subsets: one has excess +2, four 0, one -2.
    result=placebo_excess([([2,2,0,0],2)],2,draws=5000,seed=20261007,family=3)
    assert result['raw_p']==pytest.approx(1/6,abs=.03)
    assert result['family_adjusted_p']==pytest.approx(.5,abs=.09)
    assert result['null_mean']==pytest.approx(0,abs=.05)
    assert result['null_interval']==[-2,2]
