from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from research.recover_lowliq_history_request import capture_retry, resolve_response, digest, compare_rows
from research.run_lowliq_touch10_reconstruction import save_json


def fixture(tmp_path):
    identity={'code':'004310','market_div':'J','period':'D','start_date':'20260602','end_date':'20260602','adjusted':False}
    parent=tmp_path/'original.json'
    save_json(parent,{'request':identity,'plan_sha256':'scope','inspection':{'status':'REQUEST_ERROR'},'error_type':'KISOpenAPIError'})
    rows=[{'date':'2026-06-02','open':'100','high':'103','low':'99','close':'101','volume':'50','amount':'5000'}]
    plan={'request':identity,'scope_plan_sha256':'scope','parent_failure_sha256':digest(parent),
          'expected_dates':['2026-06-02'],'reference_rows':rows,'paired_rows':deepcopy(rows)}
    payload={'rt_cd':'0','output2':[{'stck_bsop_date':'20260602','stck_oprc':'100','stck_hgpr':'103',
             'stck_lwpr':'99','stck_clpr':'101','acml_vol':'50','acml_tr_pbmn':'5000'}]}
    return parent,plan,payload


def test_one_shot_capture_replay_and_opt_in_resolver(tmp_path):
    parent,plan,payload=fixture(tmp_path);out=tmp_path/'supplement';calls=[]
    client=SimpleNamespace(daily_bars=lambda code,**kw:(calls.append((code,kw)) or payload))
    first=capture_retry(plan,out,client)
    assert first['accepted'] is True and first['network_calls']==1
    before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*.json')}
    replay=capture_retry(plan,out,None)
    assert replay['network_calls']==0
    resolved=resolve_response(parent,out,expected_plan_sha256=digest(out/'plan.json'))
    assert resolved['provenance']['original_status']=='REQUEST_ERROR'
    assert resolved['receipt']['payload']==payload and resolved['source_certified'] is False
    assert before=={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*.json')}
    assert len(calls)==1 and json.loads(parent.read_text())['inspection']['status']=='REQUEST_ERROR'


def test_failed_retry_is_preserved_and_not_retried(tmp_path):
    parent,plan,_=fixture(tmp_path);out=tmp_path/'supplement';calls=[]
    def failure(*a,**k):calls.append(1);raise RuntimeError('sensitive provider message')
    first=capture_retry(plan,out,SimpleNamespace(daily_bars=failure))
    assert not first['accepted'] and first['network_calls']==1
    again=capture_retry(plan,out,SimpleNamespace(daily_bars=failure))
    assert not again['accepted'] and again['network_calls']==0 and len(calls)==1
    assert 'sensitive' not in (out/'response.json').read_text()
    with pytest.raises(ValueError,match='supplement_not_accepted'):
        resolve_response(parent,out,expected_plan_sha256=digest(out/'plan.json'))


@pytest.mark.parametrize('field,value', [('stck_clpr','102'),('acml_tr_pbmn','4999'),('acml_vol','49')])
def test_changed_values_do_not_get_accepted(tmp_path,field,value):
    parent,plan,payload=fixture(tmp_path);payload['output2'][0][field]=value
    out=tmp_path/'supplement'
    result=capture_retry(plan,out,SimpleNamespace(daily_bars=lambda *a,**k:payload))
    assert result['accepted'] is False
    with pytest.raises(ValueError,match='supplement_not_accepted'):
        resolve_response(parent,out,expected_plan_sha256=digest(out/'plan.json'))


def test_missing_expected_day_and_extra_day_are_not_accepted(tmp_path):
    _,plan,payload=fixture(tmp_path);payload['output2']=[]
    assert not capture_retry(plan,tmp_path/'missing',SimpleNamespace(daily_bars=lambda *a,**k:payload))['accepted']
    assert compare_rows([{'date':'2026-06-03'}],plan['reference_rows'])['matched'] is False


@pytest.mark.parametrize('target', ['parent','plan','payload','inspection','validation'])
def test_modified_lineage_is_rejected(tmp_path,target):
    parent,plan,payload=fixture(tmp_path);out=tmp_path/'supplement'
    capture_retry(plan,out,SimpleNamespace(daily_bars=lambda *a,**k:payload))
    trusted=digest(out/'plan.json')
    path={'parent':parent,'plan':out/'plan.json','payload':out/'response.json',
          'inspection':out/'response.json','validation':out/'validation.json'}[target]
    data=json.loads(path.read_text())
    if target=='parent':data['request']['code']='000001'
    elif target=='plan':data['request']['adjusted']=True
    elif target=='payload':data['payload']['output2'][0]['stck_clpr']='102'
    elif target=='inspection':data['inspection']['rows']=999
    else:data['accepted']=False
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):resolve_response(parent,out,expected_plan_sha256=trusted)


def test_comparison_uses_exact_decimal_not_float_tolerance():
    row={'date':'2026-06-02',**{k:'9007199254740992' for k in ['open','high','low','close','volume','amount']}}
    other=deepcopy(row);other['amount']='9007199254740993'
    result=compare_rows([row],[other])
    assert not result['matched'] and len(result['differences'])==1
