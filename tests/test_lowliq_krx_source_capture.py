import json
from types import SimpleNamespace

import pytest

from research.capture_lowliq_krx_source import collect, inspect_payload
from research.run_lowliq_touch10_reconstruction import save_json


def response(dates=('20260630','20260701')):
    return {'rt_cd': '0', 'output2': [dict(stck_bsop_date=d, stck_oprc='100',
        stck_hgpr='102', stck_lwpr='99', stck_clpr='101', acml_vol='50') for d in dates]}


def spec():
    return {'expected_dates': {'000001': ['2026-06-30','2026-07-01'],
                                '000002': ['2026-06-30','2026-07-01']},
            'request': {'start_date': '20260630','end_date': '20261002','market_div': 'J','period':'D'},
            'bases': ['adjusted','nominal']}


def test_fixed_all_code_bases_capture_and_no_network_replay(tmp_path):
    s=spec();save_json(tmp_path/'plan.json',s);calls=[]
    def fetch(code,**kwargs):calls.append((code,kwargs));return response()
    client=SimpleNamespace(daily_bars=fetch)
    first=collect(s,tmp_path,client,30)
    assert first['network_calls']==4 and first['status_counts']=={'CAPTURED':4}
    assert {kw['adjusted'] for _,kw in calls}=={True,False}
    assert all(kw['market_div']=='J' for _,kw in calls)
    assert all(kw['start_date'].isdigit() and len(kw['start_date'])==8 and kw['period']=='D'
               for _,kw in calls)
    assert collect(s,tmp_path,client,30)['network_calls']==0 and len(calls)==4
    p=tmp_path/'responses/000001_adjusted.json';x=json.loads(p.read_text())
    x['payload']['output2'][0]['stck_clpr']='99';p.write_text(json.dumps(x))
    with pytest.raises(ValueError,match='changed_provider_payload'):collect(s,tmp_path,client,30)


def test_error_and_empty_are_preserved_not_deleted_or_retried(tmp_path):
    s=spec();save_json(tmp_path/'plan.json',s)
    def fetch(code,**kwargs):
        if code=='000001':raise TimeoutError('synthetic')
        return {'rt_cd':'0','output2':[]}
    client=SimpleNamespace(daily_bars=fetch)
    first=collect(s,tmp_path,client,30)
    assert first['completed_attempts']==4
    assert first['status_counts']=={'REQUEST_ERROR':2,'EMPTY_PROVIDER':2}
    assert collect(s,tmp_path,client,30)['network_calls']==0
    assert len(list((tmp_path/'responses').glob('*.json')))==4


def test_budget_stops_before_request_then_resumes_all(tmp_path):
    s=spec();save_json(tmp_path/'plan.json',s)
    client=SimpleNamespace(daily_bars=lambda *a,**kw:response())
    first=collect(s,tmp_path,client,1e-12)
    assert first['status']=='BUDGET_EXHAUSTED' and first['network_calls']==0
    assert collect(s,tmp_path,client,30)['completed_attempts']==4


def test_missing_dates_outside_dates_and_non_mapping_not_certified():
    s=spec();r=s['request'];dates=s['expected_dates']['000001']
    assert inspect_payload(response(('20260701',)),r,dates)=={
        'status':'PARTIAL','rows':1,'missing_existing_dates':['2026-06-30'],
        'additional_provider_dates':[],'first_date':'2026-07-01','last_date':'2026-07-01'}
    assert inspect_payload(response(('20261007',)),r,dates)['status']=='INVALID_RESPONSE'
    assert inspect_payload(None,r,dates)['status']=='INVALID_RESPONSE'
    assert inspect_payload({'rt_cd':'1'},r,dates)['status']=='PROVIDER_ERROR'
