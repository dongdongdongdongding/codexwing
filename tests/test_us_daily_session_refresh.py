from datetime import datetime
from zoneinfo import ZoneInfo
import json

import pandas as pd
import pytest

from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import us_daily_session_refresh as sr


def raw(days, factor=1.):
    return pd.DataFrame({'date':pd.to_datetime(days),'symbol':'AAA','name':'AAA','market':'NASDAQ',
                         'open':10*factor,'high':11*factor,'low':9*factor,'close':10*factor,
                         'raw_close':10.,'adj_close':10*factor,'volume':1000.,'adj_factor':factor,
                         'dollar_volume':10000*factor,'source':'yfinance'})


@pytest.fixture
def setup(tmp_path,monkeypatch):
    paths=bf.BackfillPaths(tmp_path,'NASDAQ');paths.raw_dir.mkdir(parents=True)
    universe=pd.DataFrame({'symbol':['AAA'],'name':['AAA']})
    old=raw(['2026-09-30','2026-10-01','2026-10-02']);old.to_parquet(bf._raw_path(paths,'AAA'),index=False)
    monkeypatch.setattr(bf,'_download_batch',lambda *a,**kw:pd.DataFrame())
    return paths,universe,old


def collect(setup,tmp_path):
    paths,universe,_=setup
    return sr.refresh_raw(universe,paths,'2026-10-06',start='2018-01-01',batch_size=10,
                          timeout=1,sleep=0,budget=30,audit=tmp_path/'audit')


def test_target_session_ignores_partial_current_day_and_handles_weekend(tmp_path,monkeypatch):
    paths=bf.BackfillPaths(tmp_path,'NASDAQ')
    monkeypatch.setattr(bf,'_download_single',lambda *a:raw(['2026-10-02','2026-10-05']))
    assert sr.latest_completed_session(paths,datetime(2026,10,5,15,tzinfo=ZoneInfo('America/New_York')))=='2026-10-02'
    assert sr.latest_completed_session(paths,datetime(2026,10,5,16,30,tzinfo=ZoneInfo('America/New_York')))=='2026-10-05'


def test_single_fresh_symbol_cannot_mask_missing_coverage(tmp_path):
    path=tmp_path/'panel.parquet'
    pd.DataFrame({'date':pd.to_datetime(['2026-10-02','2026-10-02','2026-10-06']),
                  'symbol':['AAA','BBB','NEW']}).to_parquet(path,index=False)
    result=sr.coverage(path,'2026-10-06',['AAA','BBB','NEW'])
    assert not result['current'] and result['missing_symbols']==['AAA','BBB']


def test_incremental_refresh_is_audited_and_then_resumes_without_refetch(setup,tmp_path,monkeypatch):
    paths,universe,old=setup
    new=raw(['2026-09-30','2026-10-01','2026-10-02','2026-10-05','2026-10-06'])
    calls=[]
    monkeypatch.setattr(bf,'_download_single',lambda *a:calls.append(a) or new.copy())
    first=collect(setup,tmp_path)
    assert first['written']==['AAA'] and not first['failed']
    assert pd.read_parquet(tmp_path/'audit/before/AAA.parquet').equals(old)
    assert pd.read_parquet(bf._raw_path(paths,'AAA')).equals(new)
    second=collect(setup,tmp_path/'second')
    assert second['skipped_current']==['AAA'] and len(calls)==1


def test_adjustment_change_requires_complete_history_before_write(setup,tmp_path,monkeypatch):
    paths,_,old=setup
    partial=raw(['2026-10-01','2026-10-02','2026-10-05','2026-10-06'],.5)
    monkeypatch.setattr(bf,'_download_single',lambda *a:partial.copy())
    result=collect(setup,tmp_path)
    assert result['failed'][0]['reason']=='adjustment_refresh_incomplete_history'
    assert pd.read_parquet(bf._raw_path(paths,'AAA')).equals(old)
    assert not (tmp_path/'audit/before').exists()


def test_adjustment_change_uses_complete_refetched_basis(setup,tmp_path,monkeypatch):
    paths,_,old=setup
    partial=raw(['2026-10-01','2026-10-02','2026-10-05','2026-10-06'],.5)
    full=raw(['2026-09-30','2026-10-01','2026-10-02','2026-10-05','2026-10-06'],.5)
    monkeypatch.setattr(bf,'_download_single',lambda symbol,start,*a:full.copy() if start=='2018-01-01' else partial.copy())
    result=collect(setup,tmp_path)
    assert result['full_adjustment_refresh']==['AAA'] and not result['failed']
    assert pd.read_parquet(bf._raw_path(paths,'AAA')).equals(full)


def test_nonempty_but_stale_response_is_failure_without_mutation(setup,tmp_path,monkeypatch):
    paths,_,old=setup
    monkeypatch.setattr(bf,'_download_single',lambda *a:old.copy())
    result=collect(setup,tmp_path)
    assert result['failed'][0]['reason']=='provider_missing_requested_session'
    assert pd.read_parquet(bf._raw_path(paths,'AAA')).equals(old)


@pytest.mark.parametrize('single_has_target',[True,False])
def test_nonempty_stale_batch_retries_single_once(setup,tmp_path,monkeypatch,single_has_target):
    paths,_,old=setup
    calls=[]
    fresh=raw(['2026-09-30','2026-10-01','2026-10-02','2026-10-05','2026-10-06'])
    monkeypatch.setattr(bf,'_extract_yfinance_frame',lambda *a:old.copy())
    monkeypatch.setattr(bf,'_download_single',lambda *a:calls.append(a) or (fresh if single_has_target else old).copy())
    result=collect(setup,tmp_path)
    assert len(calls)==1
    assert result['single_retries'][0]['has_target'] is single_has_target
    assert result['single_retries'][0]['batch_latest']=='2026-10-02 00:00:00'
    assert result['written']==(['AAA'] if single_has_target else [])
    assert bool(result['failed']) is not single_has_target
    assert pd.read_parquet(bf._raw_path(paths,'AAA')).equals(fresh if single_has_target else old)


def test_verified_panel_receipt_is_invalidated_by_changed_file(setup,monkeypatch):
    paths,universe,_=setup
    universe.to_csv(paths.universe_path,index=False)
    raw(['2026-10-06']).to_parquet(bf._raw_path(paths,'AAA'),index=False)
    info=bf.write_feature_panel(universe,paths,start='2018-01-01',end='2026-10-07',output_prefix='daily_features',feature_batch_size=100)
    from pathlib import Path
    path=Path(info['output_feature_path'])
    identity={'path':str(path),'mtime_ns':path.stat().st_mtime_ns,'size':path.stat().st_size}
    sr.save_json(paths.market_root/'.refresh/current.json',{'status':'refreshed','required_through':'2026-10-06','panel_identity':identity,'universe_sha256':sr.digest(paths.universe_path)})
    monkeypatch.setattr(bf,'_run_refresh',lambda *a,**kw:{'status':'refreshed'})
    assert bf.daily_refresh(paths,required_through='2026-10-06')['status']=='already_current'
    path.touch()
    assert bf.daily_refresh(paths,required_through='2026-10-06')['status']=='refreshed'


def test_feature_panel_excludes_uncompleted_future_raw_rows(setup):
    paths,universe,_=setup
    frame=raw(pd.bdate_range('2026-01-01','2026-10-07'))
    frame.to_parquet(bf._raw_path(paths,'AAA'),index=False)
    info=bf.write_feature_panel(universe,paths,start='2026-01-01',end='2026-10-07',output_prefix='daily_features',feature_batch_size=1)
    panel=pd.read_parquet(info['output_feature_path'])
    assert panel.date.max()==pd.Timestamp('2026-10-06')
    assert pd.isna(panel.sort_values('date').iloc[-1]['fwd_high_ret_1d'])


def test_manual_cli_and_daily_refresh_share_writer_lock(setup,monkeypatch):
    import fcntl
    from types import SimpleNamespace
    paths,_,_=setup
    monkeypatch.setattr(bf,'parse_args',lambda:SimpleNamespace(daily_refresh=False,output_root=str(paths.root),market='NASDAQ'))
    with (paths.market_root/'.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert bf.main()==2
        assert bf.daily_refresh(paths,required_through='2026-10-06')['status']=='busy'
