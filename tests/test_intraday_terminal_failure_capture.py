import copy
import json
from types import SimpleNamespace

import pytest

from research import capture_intraday_terminal_failures as m


def payload(high='102'):
    return {'rt_cd':'0','output2':[{'stck_bsop_date':'20260923','stck_cntg_hour':'090000',
            'stck_oprc':'100','stck_hgpr':high,'stck_lwpr':'99','stck_prpr':'101','cntg_vol':'10'}]}


def test_immutable_capture_replay_retains_invalid_payload(tmp_path):
    plan={'requests':[{'code':'011230','day':'20260923','hour':'100000'}]};calls=[]
    def get(*a,**k):calls.append(k);return payload('50')
    first=m.capture(plan,tmp_path,SimpleNamespace(daily_minute_bars=get),pause=lambda _:None)
    assert first['status_counts']=={'INVALID_OHLCV':1} and len(calls)==1
    paths=list(tmp_path.rglob('*.json'));before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
    assert m.capture(plan,tmp_path,None)['network_calls_this_run']==0
    assert before=={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
    receipt=json.loads(next((tmp_path/'responses').glob('*')).read_text())
    assert receipt['payload']==payload('50')


def test_request_error_preserved_without_sensitive_message_or_retry(tmp_path):
    plan={'requests':[{'code':'011230','day':'20260923','hour':'100000'}]}
    def fail(*a,**k):raise RuntimeError('secret-example')
    result=m.capture(plan,tmp_path,SimpleNamespace(daily_minute_bars=fail),pause=lambda _:None)
    assert result['status_counts']=={'REQUEST_ERROR':1}
    assert 'secret-example' not in next((tmp_path/'responses').glob('*')).read_text()
    assert m.capture(plan,tmp_path,None)['network_calls_this_run']==0


@pytest.mark.parametrize('field',['request','payload','inspection'])
def test_changed_receipt_refused(tmp_path,field):
    plan={'requests':[{'code':'011230','day':'20260923','hour':'100000'}]}
    m.capture(plan,tmp_path,SimpleNamespace(daily_minute_bars=lambda *a,**k:payload()),pause=lambda _:None)
    p=next((tmp_path/'responses').glob('*'));item=json.loads(p.read_text());item[field]={};p.write_text(json.dumps(item))
    with pytest.raises(ValueError):m.capture(plan,tmp_path,None)


def test_scope_is_seven_failures_plus_twelve_storage_windows_deduplicated():
    tuples=[('220260','20260928','153000'),('011230','20260923','100000'),
            ('012280','20260923','153000'),('012280','20260923','133000'),
            ('013000','20260923','133000'),('393890','20260923','100000'),('460850','20260923','113000')]
    report={'run_id':'20261007T205547317819','request_errors':[dict(zip(['code','day','hour'],r)) for r in tuples],
            'storage_errors':[{'code':c} for c in ['011230','013000','014130']]}
    original=copy.deepcopy(report);requests=m.request_scope(report)
    assert len(requests)==17 and report==original
    report['run_id']='different'
    with pytest.raises(ValueError):m.request_scope(report)


def test_provider_error_empty_and_valid_distinct():
    request={'code':'011230','day':'20260923','hour':'100000'}
    assert m.inspect(request,{'rt_cd':'1'})=={'status':'PROVIDER_ERROR'}
    assert m.inspect(request,{'rt_cd':'0','output2':[]})=={'status':'EMPTY_SLICE','rows':0}
    assert m.inspect(request,payload())=={'status':'VALID_SLICE','rows':1}
