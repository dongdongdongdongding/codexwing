import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from research import compare_indexed_lowliq_history as m
from research.capture_lowliq_history import collect
from research.index_lowliq_history_capture import build_index
from research.recover_lowliq_history_request import capture_retry
from research.run_lowliq_touch10_reconstruction import save_json


def payload():
    return {'rt_cd':'0','output2':[dict(stck_bsop_date='20260602',stck_oprc='100',stck_hgpr='102',
        stck_lwpr='99',stck_clpr='101',acml_vol='50',acml_tr_pbmn='5000')]}


def fixture(tmp_path,*,calls=4,fail=False,supplement=False):
    requests=[{'id':c+'_'+b,'code':c,'basis':b,'start_date':'20260602','end_date':'20260602',
               'expected_dates':['2026-06-02']} for c in ['A','B'] for b in ['nominal','adjusted']]
    scope=tmp_path/'scope.json';save_json(scope,{'requests':requests});sha=m.digest(scope)
    capture=tmp_path/'capture';save_json(capture/'manifest.json',{'scope_plan_sha256':sha})
    def get(code,**kwargs):
        if fail and code=='A' and not kwargs['adjusted']:raise TimeoutError()
        return payload()
    collect({'requests':requests,'plan_sha256':sha},capture,SimpleNamespace(daily_bars=get),budget=30,max_calls=calls,interval=0)
    supplements=[]
    if supplement:
        original=capture/'responses/A_nominal.json';item=json.loads(original.read_text());out=tmp_path/'supplement'
        rows=[dict(date='2026-06-02',open='100',high='102',low='99',close='101',volume='50',amount='5000')]
        plan={'request':item['request'],'scope_plan_sha256':sha,'parent_failure_sha256':m.digest(original),
              'expected_dates':['2026-06-02'],'reference_rows':rows,'paired_rows':rows}
        capture_retry(plan,out,SimpleNamespace(daily_bars=lambda *a,**k:payload()))
        supplements=[{'request_id':'A_nominal','directory':str(out),'plan_sha256':m.digest(out/'plan.json')}]
    index=tmp_path/'index.json';save_json(index,build_index(scope,capture,supplements=supplements))
    return scope,index,capture


def load(paths):
    return m.load_snapshot(*paths,m.digest(paths[1]))


def source():
    return pd.DataFrame([{'code':c,'date':pd.Timestamp('2026-06-02'),'open':100.,'high':102.,'low':99.,
        'close':101.,'volume':50.,'amount':5000.,'adj_open':100.,'adj_high':102.,'adj_low':99.,'adj_close':101.} for c in ['A','B']])


def test_partial_code_is_explicit_and_cannot_join_complete_cohort(tmp_path):
    paths=fixture(tmp_path,calls=3);available,coverage=load(paths)
    assert set(available)=={'A'} and coverage['unvisited_requests']==1
    assert coverage['partial_codes']==[{'code':'B','unvisited_requests':['B_adjusted']}]
    tables,summary=m.compare_frame(source(),available)
    assert summary['compared_codes']==1 and summary['nominal_diff_cells']==0
    assert summary['source_certified'] is False and summary['strategy_outcomes_computed'] is False


def test_fully_attempted_error_stays_unavailable_without_supplement(tmp_path):
    available,coverage=load(fixture(tmp_path,fail=True))
    assert set(available)=={'B'} and coverage['fully_attempted_codes']==2
    assert coverage['unavailable_codes']==[{'code':'A','requests':[{'id':'A_nominal','status':'REQUEST_ERROR'}]}]


def test_reviewed_supplement_used_with_original_error_provenance(tmp_path):
    paths=fixture(tmp_path,fail=True,supplement=True);available,coverage=load(paths)
    assert set(available)=={'A','B'} and coverage['supplements']==['A_nominal']
    assert json.loads((paths[2]/'responses/A_nominal.json').read_text())['inspection']['status']=='REQUEST_ERROR'
    p=tmp_path/'supplement/validation.json';p.write_text('{}')
    with pytest.raises(ValueError,match='supplement_validation'):load(paths)


@pytest.mark.parametrize('target',['original','effective','scope','index'])
def test_changed_frozen_artifacts_rejected(tmp_path,target):
    paths=fixture(tmp_path,fail=True,supplement=True);expected=m.digest(paths[1])
    p={'original':paths[2]/'responses/A_nominal.json','effective':tmp_path/'supplement/response.json',
       'scope':paths[0],'index':paths[1]}[target]
    p.write_text(p.read_text()+' ')
    with pytest.raises(ValueError):m.load_snapshot(*paths,expected)


@pytest.mark.parametrize('mutation',['count','duplicate','path'])
def test_inconsistent_index_semantics_rejected_even_with_its_new_digest(tmp_path,mutation):
    paths=fixture(tmp_path);item=json.loads(paths[1].read_text())
    if mutation=='count':item['snapshot_receipts']+=1
    elif mutation=='duplicate':item['entries'].append(item['entries'][0])
    else:item['entries'][0]['effective_path']=str(tmp_path/'unrelated')
    paths[1].write_text(json.dumps(item))
    with pytest.raises(ValueError):load(paths)


def test_nominal_mismatch_and_nontraded_close_are_not_hidden(tmp_path):
    available,_=load(fixture(tmp_path));raw=source();raw.loc[0,'volume']=51
    raw.loc[0,'adj_open']=90
    tables,summary=m.compare_frame(raw,available)
    assert tables['nominal_differences'][0]['field']=='volume'
    assert summary['nominal_nonconventional_diff_cells']==1
    assert summary['comparable_codes_over_one_krw']==['A']
    assert Decimal(tables['adjusted_differences'][0]['absolute_difference'])==10
    # The zero OHL convention is diagnostic only; zero-volume close survives.
    second=copy.deepcopy(available['A']);r=copy.deepcopy(second['nominal']['2026-06-02'])
    r.update(stck_bsop_date='20260603',stck_oprc='0',stck_hgpr='0',stck_lwpr='0',stck_clpr='90',acml_vol='0',acml_tr_pbmn='0')
    for b in second:second[b]['2026-06-03']=copy.deepcopy(r)
    base=source().iloc[:1];extra=base.copy();extra['date']=pd.Timestamp('2026-06-03');extra['volume']=0;extra['amount']=0;extra['close']=90
    for col in ['open','high','low']:extra[col]=90
    for col in ['adj_open','adj_high','adj_low']:extra[col]=101
    tables,summary=m.compare_frame(pd.concat([base,extra]),{'A':second})
    assert summary['nominal_nonconventional_diff_cells']==0
    diffs=[r for r in tables['adjusted_differences'] if not r['nontraded_zero_ohl_convention']]
    assert len(diffs)==1 and diffs[0]['field']=='close' and Decimal(diffs[0]['absolute_difference'])==11


@pytest.mark.parametrize('left,right,lc,rc,expected',[(0,100,100,100,True),(100,0,100,100,True),
                         (0,99,100,100,False),(99,0,100,100,False),(0,0,100,100,False)])
def test_zero_ohl_requires_opposite_close_and_no_trades(left,right,lc,rc,expected):
    source={'volume':0,'amount':0};provider={'acml_vol':'0','acml_tr_pbmn':'0'}
    assert m.zero_ohl_representation(left,right,lc,rc,source,provider)==expected
    assert m.zero_ohl_representation(left,right,lc,rc,{**source,'volume':1},provider) is False
    assert m.zero_ohl_representation(left,right,lc,rc,source,{**provider,'acml_tr_pbmn':'1'}) is False


def test_missing_source_date_is_error_not_smaller_denominator(tmp_path):
    available,_=load(fixture(tmp_path));raw=source();raw.loc[0,'date']=pd.Timestamp('2026-06-01')
    with pytest.raises(ValueError,match='coverage_mismatch'):m.compare_frame(raw,available)


def test_full_run_replay_preserves_all_saved_outputs(tmp_path):
    paths=fixture(tmp_path,fail=True,supplement=True);panel=tmp_path/'panel.parquet';source().to_parquet(panel)
    out=tmp_path/'result';kwargs={'index_sha':m.digest(paths[1]),'source_sha':m.digest(panel)}
    result=m.run(*paths,panel,out,**kwargs);assert result['compared_rows']==2
    saved={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in out.iterdir()}
    assert m.run(*paths,panel,out,**kwargs)==result
    assert saved=={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in out.iterdir()}
    with pytest.raises(ValueError,match='changed_source'):m.run(*paths,panel,out,index_sha=kwargs['index_sha'],source_sha='bad')
