from copy import deepcopy

import pytest

from research.audit_kosdaq_vwap_provenance import reconcile, freeze, stamp


def rows():
    identity={'run_id':'KQ-ITD-3D-T5-20260630','ticker':'036930.KQ'}
    ledger={**identity,'ordered_entry_at':'2026-06-30T15:00:00',
            'generated_at':'2026-06-30T12:36:04+00:00','p':1.,'target_tp_pct':5.,'hold_days':3}
    scan={**identity,'ordered_entry_at':'2026-06-30T15:00:00+00:00',
          'recommended_at':ledger['generated_at'],'ml_prob':100.,'target_tp_pct':5.,'hold_days':3,
          'feature_snapshot':{'entry_time_kst':'15:00'}}
    deep={**identity,'generated_at':ledger['generated_at'],'buy_score':1.,'trade_plan':{}}
    return ledger,scan,deep


def test_naive_local_entry_and_utc_db_entry_do_not_make_late_pick_timely():
    l,s,d=rows(); original=deepcopy((l,s,d));r=reconcile([l],[s],[d])[0]
    assert r['stored_minus_reference_seconds']==9*3600
    assert r['before_stored_entry'] is True
    assert r['before_reference_entry'] is False
    assert all(r['ledger_scan_checks'].values())
    assert r['recovered_original_pick'] is False
    assert (l,s,d)==original


def test_missing_ledger_can_only_establish_declared_schedule():
    _,s,d=rows();r=reconcile([],[s],[d])[0]
    assert not r['in_ledger'] and r['in_scan'] and r['in_deep']
    assert r['entry_evidence']=='archive_declared_1500_KST_only'
    assert not r['before_reference_entry'] and not r['recovered_original_pick']


def test_unknown_or_missing_timing_is_not_promoted_to_valid():
    _,s,_=rows();s['feature_snapshot']=None;s['recommended_at']='2026-06-30T12:00:00'
    r=reconcile([],[s],[])[0]
    assert r['before_reference_entry'] is None and r['before_stored_entry'] is None
    assert r['entry_evidence']=='unavailable'
    assert stamp('not-a-date') is None


def test_known_aware_entry_keeps_its_instant_and_differing_scores_are_visible():
    l,s,d=rows();l['ordered_entry_at']='2026-06-30T06:00:00+00:00';l['p']=.7
    l['hold_days']=5;d['buy_score']=.6
    r=reconcile([l],[s],[d])[0]
    assert r['stored_minus_reference_seconds']==9*3600
    assert not r['ledger_scan_checks']['score_equal']
    assert not r['ledger_scan_checks']['horizon_equal']
    assert not r['deep_score_equals_scan']


def test_duplicate_or_unrelated_identity_is_rejected():
    l,s,d=rows()
    with pytest.raises(ValueError,match='duplicate'):
        reconcile([l,l],[s],[d])
    s['run_id']='ANOTHER-LANE'
    with pytest.raises(ValueError,match='unexpected_identity'):
        reconcile([l],[s],[d])


def test_capture_never_overwrites_different_original_bytes(tmp_path):
    p=tmp_path/'snapshot';freeze(p,b'original');freeze(p,b'original')
    with pytest.raises(ValueError,match='capture_changed'):
        freeze(p,b'changed')
    assert p.read_bytes()==b'original'
