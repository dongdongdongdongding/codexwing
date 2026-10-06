import json
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import us_daily_panel_cache as cache
from multi_agent.tools import us_daily_session_refresh as sr


@pytest.fixture
def source(tmp_path):
    paths=bf.BackfillPaths(tmp_path,'NASDAQ');paths.raw_dir.mkdir(parents=True)
    universe=pd.DataFrame({'symbol':['NA'],'name':['Nano Labs']})
    frame=pd.DataFrame({'date':pd.to_datetime(['2026-10-02','2026-10-05','2026-10-06']),
        'symbol':'NA','name':'Nano Labs','open':100.,'high':101.,'low':99.,'close':100.,
        'volume':1000.,'dollar_volume':100000.})
    frame.to_parquet(bf._raw_path(paths,'NA'),index=False)
    return paths,universe,frame


def build(source,**overrides):
    paths,universe,_=source
    args=dict(start='2018-01-01',end='2026-10-07',output_prefix='daily_features',feature_batch_size=100)
    args.update(overrides)
    return bf.write_feature_panel(universe,paths,**args)


def test_unchanged_inputs_reuse_without_writes_even_below_storage_reserve(source,monkeypatch):
    import shutil
    first=build(source); path=Path(first['output_feature_path'])
    before={p:(p.stat().st_mtime_ns,p.stat().st_size) for p in source[0].market_root.rglob('*') if p.is_file()}
    monkeypatch.setattr(bf,'compute_feature_frame',lambda *_:pytest.fail('recomputed unchanged input'))
    monkeypatch.setattr(shutil,'disk_usage',lambda *_:SimpleNamespace(free=1))
    second=build(source)
    assert second['feature_panel_reused'] and second['output_feature_path']==str(path)
    assert before=={p:(p.stat().st_mtime_ns,p.stat().st_size) for p in source[0].market_root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('change',['raw','missing_raw','universe','start','end','prefix','code','library'])
def test_changed_dependencies_rebuild_without_overwriting_prior_panel(source,monkeypatch,change):
    first=build(source);old=Path(first['output_feature_path']);oldsha=cache.file_sha(old)
    paths,universe,frame=source;options={}
    if change=='raw':
        rawpath=bf._raw_path(paths,'NA');stamp=rawpath.stat()
        frame.loc[0,'close']=100.5;frame.to_parquet(rawpath,index=False)
        os.utime(rawpath,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    elif change=='missing_raw':
        universe.loc[1]=['NEW','New stock']
    elif change=='universe':universe.loc[0,'name']='Corrected name'
    elif change=='code':
        original=cache.file_sha
        monkeypatch.setattr(cache,'file_sha',lambda p:'new-code' if str(p)==bf.__file__ else original(p))
    elif change=='library':monkeypatch.setattr(cache.np,'__version__','different-version')
    else:options[change]={'start':'2026-10-03','end':'2026-10-06','prefix':'other_features'}[change]
    if 'prefix' in options:options['output_prefix']=options.pop('prefix')
    second=build(source,**options)
    assert not second['feature_panel_reused']
    assert second['output_feature_path']!=str(old)
    assert cache.file_sha(old)==oldsha


def test_missing_source_arriving_invalidates_cached_partial_panel(source):
    paths,universe,frame=source
    universe.loc[1]=['NEW','New stock']
    first=build(source);assert first['failed_feature_symbols']==['NEW']
    fresh=frame.copy();fresh['symbol']='NEW'
    fresh.to_parquet(bf._raw_path(paths,'NEW'),index=False)
    second=build(source)
    assert not second['feature_panel_reused'] and not second['failed_feature_symbols']


@pytest.mark.parametrize('field',['output_feature_path','output_latest_path','output_latest_csv_path'])
def test_corrupt_artifact_with_original_size_and_mtime_is_not_reused(source,field):
    first=build(source);path=Path(first[field]);stamp=path.stat()
    payload=bytearray(path.read_bytes());payload[len(payload)//2]^=1;path.write_bytes(payload)
    os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    second=build(source)
    assert not second['feature_panel_reused']


def test_changed_raw_during_build_is_rejected_before_publication(source,monkeypatch):
    paths,_,frame=source;compute=bf.compute_feature_frame
    def mutate(raw):
        frame.loc[0,'close']=100.5;frame.to_parquet(bf._raw_path(paths,'NA'),index=False)
        return compute(raw)
    monkeypatch.setattr(bf,'compute_feature_frame',mutate)
    with pytest.raises(ValueError,match='feature_inputs_changed_during_build'):build(source)
    assert not list(paths.market_root.glob('daily_features_*.parquet'))


def test_force_build_and_newer_consumer_panel_both_prevent_reuse(source):
    first=build(source);second=build(source,force_rebuild=True)
    assert not second['feature_panel_reused'] and first['output_feature_path']!=second['output_feature_path']
    Path(first['output_feature_path']).touch()
    third=build(source)
    assert not third['feature_panel_reused']


def test_partial_collection_stays_partial_when_features_are_reused(source,monkeypatch):
    paths,universe,_=source
    monkeypatch.setattr(bf,'_fetch_universe',lambda *a,**kw:universe.copy())
    monkeypatch.setattr(sr,'refresh_raw',lambda *a,**kw:{'written':[],'skipped_current':['NA'],'failed':[{'symbol':'NA','reason':'provider_failure'}],'unvisited':[]})
    first=sr.run(paths,required_through='2026-10-06',keep_panels=0)
    second=sr.run(paths,required_through='2026-10-06',keep_panels=0)
    assert first['status']==second['status']=='partial'
    assert second['feature_panel_reused'] and second['raw_failed']==1
    assert not (paths.market_root/'.refresh/current.json').exists()


def test_already_current_validates_raw_hash_and_preserves_real_NA_ticker(source,monkeypatch):
    paths,universe,frame=source
    monkeypatch.setattr(bf,'_fetch_universe',lambda *a,**kw:universe.copy())
    monkeypatch.setattr(sr,'refresh_raw',lambda *a,**kw:{'written':[],'skipped_current':['NA'],'failed':[],'unvisited':[]})
    assert sr.run(paths,required_through='2026-10-06',keep_panels=0)['status']=='refreshed'
    monkeypatch.setattr(bf,'_run_refresh',lambda *a,**kw:{'status':'rechecked'})
    assert bf.daily_refresh(paths,required_through='2026-10-06')['status']=='already_current'
    frame.loc[0,'close']=100.5;frame.to_parquet(bf._raw_path(paths,'NA'),index=False)
    assert bf.daily_refresh(paths,required_through='2026-10-06')['status']=='rechecked'


def test_limited_universe_cannot_certify_full_daily_refresh(source,monkeypatch):
    paths,universe,_=source
    monkeypatch.setattr(bf,'_fetch_universe',lambda *a,**kw:universe.copy())
    monkeypatch.setattr(sr,'refresh_raw',lambda *a,**kw:{'written':[],'skipped_current':['NA'],'failed':[],'unvisited':[]})
    result=sr.run(paths,required_through='2026-10-06',max_symbols=1,keep_panels=0)
    assert result['status']=='partial' and result['universe_limit']==1
    assert not (paths.market_root/'.refresh/current.json').exists()


def test_invalid_cache_record_rebuilds(source):
    first=build(source)
    index=next((source[0].market_root/'.refresh/feature_panels').glob('*.json'))
    record=json.loads(index.read_text());record['info']=None
    index.write_text(json.dumps(record))
    second=build(source)
    assert not second['feature_panel_reused'] and second['output_feature_path']!=first['output_feature_path']
