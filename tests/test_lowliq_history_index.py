import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from research.capture_lowliq_history import collect
from research.index_lowliq_history_capture import build_index
from research.recover_lowliq_history_request import capture_retry,digest
from research.run_lowliq_touch10_reconstruction import save_json


def setup(tmp_path):
    scope={'requests':[{'id':'A_nominal','code':'A','basis':'nominal',
        'start_date':'20260602','end_date':'20260602','expected_dates':['2026-06-02']},
        {'id':'A_adjusted','code':'A','basis':'adjusted',
        'start_date':'20260602','end_date':'20260602','expected_dates':['2026-06-02']}]}
    path=tmp_path/'scope.json';save_json(path,scope);scope['plan_sha256']=digest(path)
    capture=tmp_path/'capture';save_json(capture/'manifest.json',{'scope_plan_sha256':digest(path)})
    def fail(*a,**k):raise TimeoutError()
    collect(scope,capture,SimpleNamespace(daily_bars=fail),budget=30,max_calls=1,interval=0)
    return path,capture


def test_partial_original_index_is_explicit(tmp_path):
    scope,capture=setup(tmp_path);result=build_index(scope,capture)
    assert result['target_requests']==2 and result['snapshot_receipts']==1
    assert result['unvisited_at_snapshot']==1
    assert result['effective_status_counts']=={'REQUEST_ERROR':1}
    assert result['source_certified'] is False


def test_index_uses_only_explicit_reviewed_supplement(tmp_path):
    scope,capture=setup(tmp_path);parent=capture/'responses/A_nominal.json'
    old=json.loads(parent.read_text());out=tmp_path/'supplement'
    rows=[dict(date='2026-06-02',open='100',high='102',low='99',close='101',volume='50',amount='5000')]
    plan={'request':old['request'],'scope_plan_sha256':digest(scope),'parent_failure_sha256':digest(parent),
          'expected_dates':['2026-06-02'],'reference_rows':rows,'paired_rows':rows}
    payload={'rt_cd':'0','output2':[dict(stck_bsop_date='20260602',stck_oprc='100',stck_hgpr='102',
        stck_lwpr='99',stck_clpr='101',acml_vol='50',acml_tr_pbmn='5000')]}
    capture_retry(plan,out,SimpleNamespace(daily_bars=lambda *a,**k:payload))
    assert build_index(scope,capture)['effective_status_counts']=={'REQUEST_ERROR':1}
    result=build_index(scope,capture,supplements=[{'request_id':'A_nominal','directory':str(out),
                                                'plan_sha256':digest(out/'plan.json')}])
    assert result['original_status_counts']=={'REQUEST_ERROR':1}
    assert result['effective_status_counts']=={'CAPTURED':1}
    assert result['unvisited_at_snapshot']==1
    assert result['entries'][0]['effective_path']==str(out/'response.json')
    assert result['entries'][0]['provenance']['original_status']=='REQUEST_ERROR'


def test_unknown_receipt_is_not_counted_as_coverage(tmp_path):
    scope,capture=setup(tmp_path)
    (capture/'responses/unknown.json').write_text('{}')
    with pytest.raises(ValueError,match='receipt_outside_frozen_scope'):build_index(scope,capture)


def test_stale_scope_binding_is_rejected(tmp_path):
    scope,capture=setup(tmp_path)
    changed=json.loads(scope.read_text());changed['new']='epoch';scope.write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='capture_scope_mismatch'):build_index(scope,capture)
