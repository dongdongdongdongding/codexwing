from datetime import date, datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from multi_agent.tools import refresh_nasdaq_listing as listing
from multi_agent.tools import report_nasdaq_session_tape as tape

NOW = datetime(2026,10,6,21,40,tzinfo=timezone.utc)


def directory(rows=None, stamp='1006202617:01'):
    rows = rows or ['NEW|New company - Common Stock|Q|N|N|100|N|N',
                    'NA|Nano Labs Ltd - Ordinary Shares|S|N|N|100|N|N']
    return ('|'.join(listing.HEADER)+'\n'+'\n'.join(rows)+'\nFile Creation Time: '+stamp+'|||||||\n').encode()


@pytest.fixture
def source(tmp_path,monkeypatch):
    output=tmp_path/'T1.parquet'
    old=pd.DataFrame({'snapshot_ts':[date(2026,6,11)],'symbol':['OLD'],
        'security_name':['Old company - Common Stock'],'market_category':['Q'],
        'test_issue':[False],'financial_status':['N'],'round_lot':[100],
        'etf':[False],'source_url':['legacy_archive']})
    old.to_parquet(output,index=False)
    monkeypatch.setattr(listing,'now_utc',lambda:NOW)
    monkeypatch.setattr(listing.requests,'get',lambda *a,**kw:SimpleNamespace(
        status_code=200,content=directory(),headers={'Last-Modified':'Tue, 06 Oct 2026 21:01:07 GMT'}))
    return output,old


def test_append_preserves_history_and_uses_observation_time(source):
    output,old=source;before=listing.file_sha(output)
    result=listing.refresh(output)
    assert result['status']=='appended' and result['appended_rows']==2
    assert result['snapshot_ts']=='2026-10-06T21:40:00'
    assert result['source_generated_at_utc']=='2026-10-06T21:01:00+00:00'
    assert listing.file_sha(Path(result['audit'])/'before.parquet')==before
    restored=pd.read_parquet(output);old['snapshot_ts']=pd.to_datetime(old.snapshot_ts)
    pd.testing.assert_frame_equal(restored.iloc[:1][old.columns],old)
    assert restored.symbol.tolist()==['OLD','NEW','NA']
    again=listing.refresh(output)
    assert again['status']=='unchanged' and again['appended_rows']==0
    assert listing.file_sha(output)==result['after_sha256']


def test_consumer_cannot_use_capture_before_it_was_observed(source,monkeypatch):
    output,_=source
    assert listing.refresh(output)['status']=='appended'
    monkeypatch.setattr(tape,'T1_PATH',str(output))
    p=pd.DataFrame({'symbol':['OLD','NEW']*4,'date':pd.to_datetime([
        '2026-10-06','2026-10-06','2026-10-06 21:39:59','2026-10-06 21:39:59',
        '2026-10-06 21:40:00','2026-10-06 21:40:00','2026-10-07','2026-10-07'],format='mixed')})
    assert tape._listed_pit(p).tolist()==[True,False,True,False,False,True,False,True]


@pytest.mark.parametrize('body,reason',[
    (b'<html>server error</html>','invalid_listing_header'),
    (directory().split(b'File Creation Time:')[0],'missing_listing_footer'),
    (directory(['A|A|Q|N|N|100|N|N']*2),'invalid_listing_keys'),
    (directory(['A|A|Q|UNKNOWN|N|100|N|N']),'invalid_listing_keys'),
    (directory(['A|A|Q|N|N|0|N|N']),'invalid_round_lot'),
    (directory(['A|A|Q|N|N|100|N']),'invalid_listing_row_width'),
    (directory(stamp='1007202617:01'),'future_listing_generation'),
    (directory(stamp='0920202617:01'),'stale_listing_source'),
])
def test_invalid_response_cannot_replace_history(source,monkeypatch,body,reason):
    output,_=source;before=listing.file_sha(output)
    monkeypatch.setattr(listing.requests,'get',lambda *a,**kw:SimpleNamespace(status_code=200,content=body,headers={}))
    result=listing.refresh(output)
    assert result['status']=='failed' and reason in result['error']
    assert listing.file_sha(output)==before
    assert json.loads((Path(result['audit'])/'result.json').read_text())['status']=='failed'


def test_new_file_bootstrap_and_http_failure(source,monkeypatch):
    output,_=source;output.unlink()
    assert listing.refresh(output)['status']=='appended'
    before=listing.file_sha(output)
    monkeypatch.setattr(listing.requests,'get',lambda *a,**kw:SimpleNamespace(status_code=503,content=b'unavailable',headers={}))
    assert listing.refresh(output)['error']=='listing_HTTP_503'
    assert listing.file_sha(output)==before


def test_external_change_requires_reconciliation(source):
    output,_=source
    assert listing.refresh(output)['status']=='appended'
    frame=pd.read_parquet(output);frame.loc[0,'security_name']='Changed outside writer'
    frame.to_parquet(output,index=False);before=listing.file_sha(output)
    assert listing.refresh(output)['error']=='listing_changed_outside_verified_writer'
    assert listing.file_sha(output)==before


def test_writer_lock_prevents_parallel_collection(source,monkeypatch):
    import fcntl
    output,_=source
    state=output.parent/('.'+output.stem+'_refresh');state.mkdir()
    with (state/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        monkeypatch.setattr(listing.requests,'get',lambda *a,**kw:pytest.fail('fetched while locked'))
        assert listing.refresh(output)['status']=='busy'
