import pandas as pd
import pytest
from research.audit_kr_touch10_price_source import parse_bars,evaluate


def test_parser_rejects_errors_duplicates_and_invalid_bars():
    row={'stck_bsop_date':'20260824','stck_oprc':'100','stck_hgpr':'105','stck_lwpr':'99','stck_clpr':'102','acml_vol':'1'}
    payload={'rt_cd':'0','output2':[row]}
    assert len(parse_bars(payload,'20260824','20260824'))==1
    for bad in [{'rt_cd':'1','output2':[row]}, {'rt_cd':'0','output2':[row,row]},
                {'rt_cd':'0','output2':[{**row,'stck_hgpr':'80'}]}]:
        with pytest.raises(ValueError):parse_bars(bad,'20260824','20260824')


def test_same_frozen_pick_must_report_source_sensitive_touch_without_promotion():
    dates=pd.bdate_range('2026-08-24',periods=11)
    pick={'date':'2026-08-24','ticker':'000001.KS','market':'KOSPI','baseline_horizon':10}
    spec={'cohort':[pick],'contract':{'cost_pct':.215}}
    prior={'records':[{**pick,'variant':v,'status':'resolved','touch':1,'policy_ret':5.} for v in ['baseline','candidate_h10']]}
    bars=pd.DataFrame({'date':dates,'adj_open':100.,'adj_high':104.,'adj_low':99.,'adj_close':102.,'volume':1.})
    result=evaluate(spec,prior,{'000001':bars},dates)
    assert result['status']=='PRICE_SOURCE_SENSITIVE'
    assert result['metrics']['combined/candidate_h10']['touch_rate']==0
    assert result['publication_allowed'] is False
    missing=evaluate(spec,prior,{},dates)
    assert missing['metrics']['combined/candidate_h10']['status_counts']=={'data_error':1}
