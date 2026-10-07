import json
from types import SimpleNamespace

import pytest
from research.capture_lowliq_history import collect


def plan():
    return {'plan_sha256': 'abc', 'requests': [
        {'id': f'A_{basis}', 'code':'A', 'basis':basis, 'start_date':'20260630',
         'end_date':'20260701', 'expected_dates':['2026-06-30','2026-07-01']}
        for basis in ['nominal','adjusted']]}


def payload():
    return {'rt_cd':'0', 'output2':[dict(stck_bsop_date=day, stck_oprc='100',
        stck_hgpr='102', stck_lwpr='99', stck_clpr='101', acml_vol='50')
        for day in ['20260630','20260701']]}


def test_bounded_resume_and_no_network_replay(tmp_path):
    calls=[]
    def fetch(symbol, **request):
        calls.append(request); return payload()
    client=SimpleNamespace(daily_bars=fetch)
    first=collect(plan(),tmp_path,client,budget=30,max_calls=1,interval=0)
    assert first['status']=='BUDGET_EXHAUSTED' and len(calls)==1
    second=collect(plan(),tmp_path,client,budget=30,max_calls=1,interval=0)
    assert second['status']=='ATTEMPTS_COMPLETE' and second['reused']==1 and len(calls)==2
    before={p.name:p.read_bytes() for p in (tmp_path/'responses').glob('*.json')}
    final=collect(plan(),tmp_path,client,budget=30,max_calls=0)
    assert final['network_calls']==0 and final['status_counts']=={'CAPTURED':2}
    assert before=={p.name:p.read_bytes() for p in (tmp_path/'responses').glob('*.json')}
    assert {r['adjusted'] for r in calls}=={False,True}


def test_errors_are_explicit_preserved_attempts(tmp_path):
    def fetch(symbol, **request): raise TimeoutError('do not expose provider secrets')
    client=SimpleNamespace(daily_bars=fetch)
    first=collect(plan(),tmp_path,client,budget=30,max_calls=2,interval=0)
    assert first['status_counts']=={'REQUEST_ERROR':2}
    assert collect(plan(),tmp_path,client,budget=30,max_calls=0)['reused']==2
    assert 'secrets' not in (tmp_path/'responses/A_nominal.json').read_text()
    assert first['source_certified'] is False


@pytest.mark.parametrize('field', ['payload','request','plan_sha256','inspection'])
def test_corruption_blocks_reuse(tmp_path,field):
    client=SimpleNamespace(daily_bars=lambda symbol, **kwargs:payload())
    collect(plan(),tmp_path,client,budget=30,max_calls=2,interval=0)
    path=tmp_path/'responses/A_nominal.json'; item=json.loads(path.read_text())
    if field=='payload': item[field]['output2'][0]['stck_clpr']='1'
    elif field=='request': item[field]['start_date']='20260101'
    elif field=='plan_sha256': item[field]='other'
    else: item[field]={'status':'CAPTURED'}
    path.write_text(json.dumps(item))
    with pytest.raises(ValueError): collect(plan(),tmp_path,client,budget=30,max_calls=0)


def test_missing_dates_do_not_count_as_complete_source(tmp_path):
    p=payload();p['output2']=p['output2'][1:]
    client=SimpleNamespace(daily_bars=lambda symbol, **kwargs:p)
    result=collect(plan(),tmp_path,client,budget=30,max_calls=2,interval=0)
    assert result['status_counts']=={'PARTIAL':2}
    item=json.loads((tmp_path/'responses/A_nominal.json').read_text())
    assert item['inspection']['missing_existing_dates']==['2026-06-30']
    assert result['source_certified'] is False
