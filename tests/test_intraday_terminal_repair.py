import copy
import fcntl
import json
from pathlib import Path

import pandas as pd
import pytest

from research import repair_intraday_terminal_cohort as m


def frame(index,rows):
    return pd.DataFrame(rows,index=pd.DatetimeIndex(index,name='Date'),columns=m.COLS).astype(float).assign(code='011230')


def test_only_reviewed_received_high_is_replaced():
    old=frame(['2026-09-23 09:00','2026-09-22 09:00'],[[2730,2725,2725,2725,385],[2700,2700,2700,2700,10]])
    fresh=old.iloc[:1].copy();fresh['High']=2730.;saved=old.copy()
    actual=m.corrected_frame('011230',old,{'100000':fresh})
    assert old.equals(saved) and actual.loc[pd.Timestamp('2026-09-22 09:00')].equals(old.iloc[1])
    assert actual.iloc[0]['High']==2730 and actual.drop(columns='High').equals(old.drop(columns='High'))
    fresh['Volume']=1
    with pytest.raises(ValueError,match='replacement'):m.corrected_frame('011230',old,{'100000':fresh})


def test_unreviewed_overlap_difference_and_new_rows_refused():
    old=frame(['2026-09-23 09:00'],[[100,102,99,101,10]])
    changed=old.copy();changed['Volume']=11
    with pytest.raises(AssertionError):m.corrected_frame('393890',old,{'100000':changed})
    new=old.copy();new.index=pd.DatetimeIndex(['2026-09-23 09:01'],name='Date')
    with pytest.raises(ValueError,match='unexpected_new'):m.corrected_frame('393890',old,{'100000':new})


def test_exactly_100_new_timestamps_preserve_existing_rows():
    old=frame(['2026-09-28 09:00'],[[100,102,99,101,10]]).assign(code='220260')
    fresh=frame(pd.date_range('2026-09-28 09:00',periods=101,freq='min'),[[100,102,99,101,10]]*101).assign(code='220260')
    actual=m.corrected_frame('220260',old,{'153000':fresh})
    assert actual.equals(fresh) and actual.loc[old.index].equals(old)
    with pytest.raises(ValueError,match='unexpected_new'):m.corrected_frame('220260',old,{'153000':fresh.iloc[:-1]})


def plan(tmp_path):
    entries=[]
    for n in range(2):
        live=tmp_path/f'live{n}';live.write_bytes(b'before')
        entries.append(m.artifact(tmp_path,'011230',str(n),live,b'after',price=n==0))
    return {'implementation_sha256':m.digest(Path(m.__file__)),'dependencies':{},'inputs':{},
            'entries':entries,'guards':[],'summaries':[]}


def test_apply_replay_retains_identity_and_no_rewrite(tmp_path):
    p=plan(tmp_path);assert m.apply(p)['files_changed_this_run']==2
    before={x['path']:(Path(x['path']).read_bytes(),m.identity(Path(x['path']))) for x in p['entries']}
    assert m.apply(p)['status']=='REUSED'
    assert before=={x['path']:(Path(x['path']).read_bytes(),m.identity(Path(x['path']))) for x in p['entries']}


@pytest.mark.parametrize('field',['path','before_path','after_path'])
def test_entire_preflight_prevents_first_write_on_second_conflict(tmp_path,field):
    p=plan(tmp_path);Path(p['entries'][1][field]).write_bytes(b'changed')
    with pytest.raises(ValueError):m.apply(p)
    assert Path(p['entries'][0]['path']).read_bytes()==b'before'


def test_interrupted_apply_resumes_first_file_without_rewriting(tmp_path,monkeypatch):
    p=plan(tmp_path);original=m.atomic_write;calls=[]
    def fail_second(path,writer):
        calls.append(path)
        if len(calls)==2:raise OSError('interruption')
        original(path,writer)
    monkeypatch.setattr(m,'atomic_write',fail_second)
    with pytest.raises(OSError):m.apply(p)
    first=Path(p['entries'][0]['path']);before=m.identity(first)
    monkeypatch.setattr(m,'atomic_write',original)
    assert m.apply(p)['files_changed_this_run']==1 and m.identity(first)==before


def test_concurrent_change_during_temp_creation_refused(tmp_path,monkeypatch):
    p=plan(tmp_path);original=m.atomic_write
    def interfere(path,writer):
        path.write_bytes(b'external');original(path,writer)
    monkeypatch.setattr(m,'atomic_write',interfere)
    with pytest.raises(ValueError):m.apply(p)
    assert Path(p['entries'][0]['path']).read_bytes()==b'external'


def test_changed_price_identity_and_guard_refused(tmp_path):
    p=plan(tmp_path);path=Path(p['entries'][0]['path']);saved=path.read_bytes();path.write_bytes(saved)
    with pytest.raises(ValueError,match='changed_live'):m.apply(p)
    p=plan(tmp_path);guard=tmp_path/'guard';guard.write_bytes(b'a');p['guards']=[{'path':str(guard),'sha256':m.digest(guard)}]
    guard.write_bytes(b'b')
    with pytest.raises(ValueError,match='changed_guard'):m.apply(p)


def test_lock_refuses_before_any_planning(tmp_path,monkeypatch,capsys):
    cache=tmp_path/'cache';(cache/'.backfill').mkdir(parents=True)
    monkeypatch.setattr('sys.argv',['repair','--root',str(tmp_path),'--cache',str(cache),'--apply'])
    with (cache/'.backfill/writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert m.main()==2
    assert json.loads(capsys.readouterr().out)['status']=='BUSY' and not (tmp_path/'runtime_state').exists()


def test_live_mutations_must_be_bound_to_lock_cache(tmp_path):
    p={'entries':[{'code':'011230','role':'cache','path':str(tmp_path/'011230.parquet')}]}
    m.validate_binding(p,tmp_path)
    with pytest.raises(ValueError,match='outside_locked'):m.validate_binding(p,tmp_path/'other')
    p['entries']*=2
    with pytest.raises(ValueError,match='duplicate'):m.validate_binding(p,tmp_path)
