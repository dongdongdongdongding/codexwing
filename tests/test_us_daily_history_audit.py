import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from curl_cffi import requests

from multi_agent.tools import audit_us_daily_history as audit
from multi_agent.tools import backfill_us_daily_features as bf


def chart(symbol='AAA', days=('2026-07-29','2026-09-30','2026-10-06')):
    timestamps=[int(pd.Timestamp(day+' 13:30:00',tz='UTC').timestamp()) for day in days]
    n=len(days)
    return {'chart':{'error':None,'result':[{'meta':{'symbol':symbol,'exchangeTimezoneName':'America/New_York'},
        'timestamp':timestamps,'indicators':{'quote':[{'open':[10.]*n,'high':[11.]*n,'low':[9.]*n,
        'close':[10.]*n,'volume':[1000]*n}],'adjclose':[{'adjclose':[10.]*n}]}}]}}


def parsed(symbol='AAA'):
    return audit.parse_chart(chart(symbol),symbol,'2018-01-01','2026-10-06')


def test_old_isolated_split_basis_change_is_outside_recent_overlap():
    old=parsed();new=old.copy()
    for col in ['open','high','low','close','raw_close','adj_close']:
        new.loc[0,col]*=9
    new.loc[0,'volume']/=9
    summary,delta=audit.compare_frames(old,new,'2018-01-01','2026-10-06')
    assert summary['outside_overlap_changed_dates']==['2026-07-29']
    assert summary['changed_rows']==1 and len(delta)==1
    assert summary['changed_fields']['adj_factor']==0
    assert summary['changed_fields']['volume']==1


def test_missing_date_is_not_a_price_match_or_delisting():
    old=parsed();new=old.iloc[1:]
    summary,_=audit.compare_frames(old,new,'2018-01-01','2026-10-06')
    assert summary['missing_dates']==['2026-07-29']
    assert summary['changed_rows']==0 and summary['common_rows']==2


def test_missing_baseline_can_be_compared_without_claiming_historical_match():
    old=pd.DataFrame(columns=['date']+audit.FIELDS)
    summary,_=audit.compare_frames(old,parsed(),'2018-01-01','2026-10-06')
    assert summary['baseline_rows']==0 and summary['common_rows']==0
    assert len(summary['added_dates'])==3


@pytest.mark.parametrize('mutation,reason',[
    (lambda r:r['meta'].update(symbol='WRONG'),'provider_symbol_mismatch'),
    (lambda r:r['meta'].update(exchangeTimezoneName='Asia/Seoul'),'unexpected_exchange_timezone'),
    (lambda r:r['timestamp'].__setitem__(1,r['timestamp'][0]),'invalid_or_duplicate_provider_dates'),
])
def test_ambiguous_provider_identity_and_dates_are_rejected(mutation,reason):
    payload=chart();mutation(payload['chart']['result'][0])
    with pytest.raises(ValueError,match=reason):
        audit.parse_chart(payload,'AAA','2018-01-01','2026-10-06')


def test_partial_null_observation_is_quarantined_not_dropped():
    payload=chart();payload['chart']['result'][0]['indicators']['quote'][0]['low'][0]=None
    observed=audit.parse_chart(payload,'AAA','2018-01-01','2026-10-06')
    summary,_=audit.compare_frames(parsed(),observed,'2018-01-01','2026-10-06')
    assert summary['observed_rows']==3 and summary['invalid_observed_rows']==1
    assert summary['missing_dates']==[]


@pytest.fixture
def frozen(tmp_path,monkeypatch):
    paths=bf.BackfillPaths(tmp_path/'cache','NASDAQ');paths.raw_dir.mkdir(parents=True)
    symbols=['AAA','NA']
    pd.DataFrame({'symbol':symbols,'name':symbols}).to_csv(paths.universe_path,index=False)
    for symbol in symbols:parsed(symbol).to_parquet(bf._raw_path(paths,symbol),index=False)
    listing=tmp_path/'listing.parquet'
    pd.DataFrame({'snapshot_ts':pd.to_datetime(['2026-10-06']*2),'symbol':symbols,
        'security_name':['Common Stock']*2,'test_issue':['N']*2,'etf':['N']*2}).to_parquet(listing)
    ledger=tmp_path/'ledger.jsonl';ledger.write_text('preserved')
    panel=tmp_path/'panel.parquet';panel.write_bytes(b'unchanged')
    monkeypatch.setattr(audit.tape,'T1_PATH',str(listing));monkeypatch.setattr(audit.tape,'LEDGER',ledger)
    monkeypatch.setattr(audit.tape,'_latest_panel',lambda:str(panel))
    root=tmp_path/'audit';root.mkdir()
    return root,paths


def test_complete_resume_keeps_na_symbol_and_never_refetches(frozen,monkeypatch):
    root,paths=frozen;calls=[]
    class Response:
        status_code=200
        def __init__(self,symbol):self.content=json.dumps(chart(symbol)).encode()
        def json(self):return json.loads(self.content)
    monkeypatch.setattr(requests,'get',lambda url,**kw:calls.append(url) or Response(url.rsplit('/',1)[1]))
    first=audit.run(root,paths,'2018-01-01','2026-10-06',workers=2)
    assert first['status']=='REQUESTS_COMPLETE' and first['compared']==2
    assert not first['baseline_sources_changed'] and not first['metadata_changed']
    assert len(calls)==2 and any(url.endswith('/NA') for url in calls)
    monkeypatch.setattr(requests,'get',lambda *a,**kw:pytest.fail('resume must not refetch'))
    second=audit.run(root,paths,'2018-01-01','2026-10-06',workers=2)
    assert second['new_requests']==0 and second['terminal']==2
    response=next((root/'responses').glob('*.gz'));response.write_bytes(gzip.compress(b'tampered'))
    with pytest.raises(ValueError,match='saved_response_hash_mismatch'):
        audit.run(root,paths,'2018-01-01','2026-10-06')


def test_provider_rate_limit_stops_unvisited_cohort_without_overwriting_raw(frozen,monkeypatch):
    root,paths=frozen
    class Limited:
        status_code=429;content=b'rate limited'
    monkeypatch.setattr(requests,'get',lambda *a,**kw:Limited())
    summary=audit.run(root,paths,'2018-01-01','2026-10-06',workers=1)
    assert summary['status']=='PROVIDER_RATE_LIMIT' and summary['terminal']==1 and summary['unvisited']==1
    assert summary['errors']==1 and not summary['baseline_sources_changed']


def test_resume_cannot_change_target(frozen):
    root,paths=frozen
    audit.freeze_plan(root,paths,'2018-01-01','2026-10-06')
    with pytest.raises(ValueError,match='audit_configuration_changed'):
        audit.freeze_plan(root,paths,'2018-01-01','2026-10-07')
