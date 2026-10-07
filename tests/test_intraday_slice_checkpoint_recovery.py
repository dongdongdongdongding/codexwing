import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from research import recover_intraday_slice_checkpoints as m


def payload(high='102',close='101'):
    return {'rt_cd':'0','output2':[{'stck_bsop_date':'20260929','stck_cntg_hour':'100000',
            'stck_oprc':'100','stck_hgpr':high,'stck_lwpr':'99','stck_prpr':close,'cntg_vol':'10'}]}


def frame():
    return m.normalize_kis_minute_bars('000001',payload(),trade_date='20260929')


def test_only_exact_existing_bars_may_recover_checkpoint():
    assert len(m.verified_frame('000001','20260929',payload(),frame()))==1
    with pytest.raises(AssertionError):m.verified_frame('000001','20260929',payload(close='100'),frame())
    with pytest.raises(ValueError,match='new_bar_requires'):m.verified_frame('000001','20260929',payload(),frame().iloc[:0])
    with pytest.raises(ValueError,match='invalid_minute'):m.verified_frame('000001','20260929',payload(high='50'),frame())
    with pytest.raises(ValueError,match='provider_error'):m.verified_frame('000001','20260929',{'rt_cd':'1'},frame())


def test_complete_requests_do_not_certify_complete_session():
    before={'identity':[1,2],'days':{'20260929':{'successful_hours':['113000','133000','153000'],
              'status':'PARTIAL_OR_EMPTY','retry_after':123,'session_complete':None},
              '20260928':{'untouched':'preserve'}}}
    saved=copy.deepcopy(before)
    after=m.recovered_state(before,{'20260929':[{'hour':'100000'}]},frame())
    assert before==saved and after['days']['20260928']==before['days']['20260928']
    cell=after['days']['20260929'];assert cell['status']=='REQUESTED_ALL_SLICES'
    assert cell['session_complete'] is None and 'retry_after' not in cell
    assert cell['verified_slice_recovery']['session_completeness']=='NOT_ESTABLISHED'


def test_unrecovered_hour_stays_partial():
    before={'days':{'20260929':{'successful_hours':['100000','133000'],'retry_after':123}}}
    after=m.recovered_state(before,{'20260929':[{'hour':'113000'}]},frame())
    assert after['days']['20260929']['status']=='PARTIAL_OR_EMPTY'
    assert after['days']['20260929']['retry_after']==123


def make_plan(tmp_path):
    cache=tmp_path/'cache.parquet';frame().to_parquet(cache)
    before=tmp_path/'before.json';before.write_text('{"before": true}')
    proposed=tmp_path/'after.json';proposed.write_text('{"after": true}')
    state=tmp_path/'state.json';state.write_bytes(before.read_bytes());stat=cache.stat()
    return {'implementation_sha256':m.digest(Path(m.__file__)),'dependencies':{},'inputs':{},
            'proposals':[{'state_path':str(state),'before_sha256':m.digest(before),'after_sha256':m.digest(proposed),
              'backup_path':str(before),'proposed_path':str(proposed),'cache_path':str(cache),
              'cache_sha256':m.digest(cache),'cache_identity':[stat.st_mtime_ns,stat.st_size]}],
            'accepted_requests':1,'rejected':[],'matched_cache_rows':1}


def test_apply_preserves_cache_and_reuses_without_rewriting(tmp_path):
    plan=make_plan(tmp_path);cache=Path(plan['proposals'][0]['cache_path']);original=cache.read_bytes()
    assert m.apply(plan,tmp_path)['changed_state_files_this_run']==1
    state=Path(plan['proposals'][0]['state_path']);mtime=state.stat().st_mtime_ns
    assert m.apply(plan,tmp_path)['status']=='REUSED'
    assert state.stat().st_mtime_ns==mtime and cache.read_bytes()==original


@pytest.mark.parametrize('which',['cache_path','state_path','backup_path','proposed_path'])
def test_changed_inputs_fail_before_mutation(tmp_path,which):
    plan=make_plan(tmp_path);row=plan['proposals'][0];Path(row[which]).write_bytes(b'changed')
    state=Path(row['state_path']);before=state.read_bytes()
    with pytest.raises(ValueError):m.apply(plan,tmp_path)
    assert state.read_bytes()==before


def test_cas_rechecks_after_temporary_write(tmp_path,monkeypatch):
    plan=make_plan(tmp_path);state=Path(plan['proposals'][0]['state_path']);original=m.atomic_write
    def interference(path,writer):
        state.write_bytes(b'external change');return original(path,writer)
    monkeypatch.setattr(m,'atomic_write',interference)
    with pytest.raises(ValueError,match='during_apply'):m.apply(plan,tmp_path)
    assert state.read_bytes()==b'external change'


def test_entire_plan_preflight_prevents_partial_apply_on_known_conflict(tmp_path):
    one=tmp_path/'one';two=tmp_path/'two';one.mkdir();two.mkdir()
    plan=make_plan(one);second=make_plan(two);plan['proposals']+=second['proposals']
    first_state=Path(plan['proposals'][0]['state_path']);before=first_state.read_bytes()
    Path(plan['proposals'][1]['state_path']).write_bytes(b'changed second state')
    with pytest.raises(ValueError,match='state_changed_since_plan'):m.apply(plan,tmp_path)
    assert first_state.read_bytes()==before


def test_interrupted_multi_file_apply_resumes_without_rewriting_completed_state(tmp_path,monkeypatch):
    one=tmp_path/'one';two=tmp_path/'two';one.mkdir();two.mkdir()
    plan=make_plan(one);plan['proposals']+=make_plan(two)['proposals'];original=m.atomic_write;calls=[]
    def fail_second(path,writer):
        calls.append(path)
        if len(calls)==2:raise OSError('injected interruption')
        return original(path,writer)
    monkeypatch.setattr(m,'atomic_write',fail_second)
    with pytest.raises(OSError):m.apply(plan,tmp_path)
    first=Path(plan['proposals'][0]['state_path']);mtime=first.stat().st_mtime_ns
    monkeypatch.setattr(m,'atomic_write',original)
    assert m.apply(plan,tmp_path)['changed_state_files_this_run']==1
    assert first.stat().st_mtime_ns==mtime


def test_active_operational_writer_blocks_before_planning(tmp_path,monkeypatch,capsys):
    import fcntl
    cache=tmp_path/'cache';(cache/'.backfill').mkdir(parents=True)
    monkeypatch.setattr('sys.argv',['recover','--root',str(tmp_path),'--cache',str(cache),'--apply'])
    with (cache/'.backfill/writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert m.main()==2
    assert json.loads(capsys.readouterr().out)['status']=='BUSY'
    assert not (tmp_path/'runtime_state').exists()
