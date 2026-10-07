import copy
import json

import pandas as pd
import pytest

from research.audit_kr_adjustment_asof import digest
from research.normalize_verified_kr_issuance import build


@pytest.fixture
def fixture(tmp_path):
    source=tmp_path/'source.parquet';evidence=tmp_path/'evidence';evidence.mkdir();out=tmp_path/'output'
    frame=pd.DataFrame({'code':['071950']*3+['000001'], 'date':pd.to_datetime(['2026-08-01','2026-08-02','2026-08-03','2026-08-03']),
        'stocks':[100,120,120,999], 'open':[10.,10.,0.,20.], 'high':[12.,12.,0.,25.],
        'low':[9.,9.,0.,18.], 'close':[11.,11.,11.,22.], 'volume':[100,100,0,500], 'amount':[1000,1000,0,10000],
        'adj_factor':[1.2,1.2,1.2,1.]})
    for name in ['open','high','low','close']:frame['adj_'+name]=frame[name]*frame.adj_factor
    frame.to_parquet(source,index=False)
    for suffix in ['html','txt']:(evidence/('document.'+suffix)).write_text('official fixture')
    (evidence/'receipts.json').write_text(json.dumps({'document':{'sha256':digest(evidence/'document.html'),'text_sha256':digest(evidence/'document.txt')}}))
    (evidence/'economics_verification.json').write_text('{}')
    base={'code':'071950','old_factor':1.2,'new_factor':1.,'evidence':'document'}
    spec={'source_sha256':digest(source),'source_rows':4,'receipts_sha256':digest(evidence/'receipts.json'),
        'economics_sha256':digest(evidence/'economics_verification.json'), 'rules':[
            {**base,'start':'2026-08-01','end':'2026-08-01','rows':1,'expected_stocks':100},
            {**base,'start':'2026-08-02','end':'2026-08-03','rows':2,'expected_stocks':120}]}
    return source,evidence,out,spec,frame


def execute(fixture):
    source,evidence,out,spec,_=fixture
    return build(source,evidence,out,spec,implementation_sha='fixture')


def test_real_streaming_build_and_repeat_preserve_zero_volume_and_other_rows(fixture):
    source,evidence,out,spec,before=fixture
    result=execute(fixture);assert result['status']=='CREATED'
    assert result['corrected_rows_by_code']=={'071950':3}
    assert result['corrected_rows_by_rule']==[1,2]
    after=pd.read_parquet(out/'panel.parquet')
    assert after.loc[2,'adj_open']==0 and after.loc[2,'volume']==0
    assert after.loc[2,'adj_close']==11.
    pd.testing.assert_series_equal(before.loc[3],after.loc[3])
    fields=['manifest.json','panel.parquet','receipt.json']
    fingerprints={name:(digest(out/name),(out/name).stat().st_mtime_ns) for name in fields}
    assert execute(fixture)['status']=='REUSED'
    assert fingerprints=={name:(digest(out/name),(out/name).stat().st_mtime_ns) for name in fields}
    assert digest(source)==spec['source_sha256']


@pytest.mark.parametrize('kind',['source','document','receipt','output'])
def test_changed_source_or_evidence_or_output_fails(fixture,kind):
    source,evidence,out,spec,_=fixture
    execute(fixture)
    path={'source':source,'document':evidence/'document.html','receipt':evidence/'receipts.json','output':out/'panel.parquet'}[kind]
    with path.open('ab') as f:f.write(b'changed')
    with pytest.raises(ValueError):execute(fixture)


def test_each_rule_count_is_checked_even_when_total_count_matches(fixture):
    source,evidence,out,spec,_=fixture
    spec['rules'][0]['rows']=2;spec['rules'][1]['rows']=1
    with pytest.raises(ValueError,match='unexpected_source_scope'):execute(fixture)
    assert not (out/'panel.parquet').exists()


def test_no_immutable_output_overwrite(fixture):
    source,evidence,out,spec,_=fixture
    out.mkdir();destination=out/'panel.parquet';destination.write_bytes(b'preexisting')
    with pytest.raises(ValueError,match='immutable_output_changed'):execute(fixture)
    assert destination.read_bytes()==b'preexisting'
