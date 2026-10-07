from copy import deepcopy

import pytest

from research.repair_kosdaq_entry_timezone import plan, cas_sql


def sample():
    l={'run_id':'KQ-ITD-3D-T5-20260916','ticker':'049080.KQ','ordered_entry_at':'2026-09-16T14:59:00',
       'p':1.,'generated_at':'2026-09-17T01:17:26.083527+00:00','hold_days':5,'target_tp_pct':10.}
    s={**l,'id':42,'feature_origin':'kosdaq_intraday_1500_vwap_guard','market':'KOSDAQ',
       'ordered_entry_at':'2026-09-16T14:59:00+00:00','recommended_at':l['generated_at'],'ml_prob':100.}
    return l,s


def test_known_local_minute_has_exact_utc_repair_and_all_other_values_stay_out_of_patch():
    l,s=sample();original=deepcopy((l,s));u=plan([l],[s])
    assert u[0]['after']=={'ordered_entry_at':'2026-09-16T05:59:00+00:00'}
    assert (l,s)==original
    sql=cas_sql(u)
    assert 'to_jsonb(t)=to_jsonb(p.b)' in sql
    assert 'SET ordered_entry_at=(p.a).ordered_entry_at' in sql
    assert 'performance_updated_at = ' not in sql


@pytest.mark.parametrize('field,value',[('recommended_at','later'),('hold_days',3),('ml_prob',70),('ordered_entry_at','2026-09-16T05:59:00+00:00'),('market','KOSPI')])
def test_unverified_or_already_fixed_source_cannot_be_corrected_again(field,value):
    l,s=sample();s[field]=value
    with pytest.raises(ValueError):plan([l],[s])


def test_wrong_day_and_missing_ledger_require_explicit_audited_identity():
    l,s=sample();l['ordered_entry_at']='2026-09-15T14:59:00'
    with pytest.raises(ValueError,match='entry_day'):plan([l],[s])
    with pytest.raises(ValueError,match='archive_only'):plan([],[s])
    s.update(run_id='KQ-ITD-3D-T5-20260630',ticker='036930.KQ',ordered_entry_at='2026-06-30T15:00:00+00:00',feature_snapshot={'entry_time_kst':'15:00'})
    assert plan([],[s])[0]['basis']=='explicit_archive_schedule_only'
    s['feature_snapshot']={}
    with pytest.raises(ValueError,match='schedule'):plan([],[s])


def test_cas_cannot_change_arbitrary_fields_or_repeat_ids():
    l,s=sample();u=plan([l],[s])
    with pytest.raises(ValueError,match='duplicate'):cas_sql(u+u)
    u[0]['after']['p']=.9
    with pytest.raises(ValueError,match='only_entry'):cas_sql(u)
