import copy
import pandas as pd
import pytest

from research.compare_lowliq_krx_source import compare_code, index_payload


def sample():
    dates=pd.date_range('2026-07-01',periods=2)
    raw=pd.DataFrame([dict(date=d,open=100,high=104,low=98,close=102,volume=100,
                          amount=10100,adj_open=50,adj_high=52,adj_low=49,adj_close=51) for d in dates])
    nominal={str(d.date()):dict(stck_oprc='100',stck_hgpr='104',stck_lwpr='98',
                stck_clpr='102',acml_vol='100',acml_tr_pbmn='10100') for d in dates}
    adjusted={str(d.date()):dict(stck_oprc='25',stck_hgpr='26',stck_lwpr='24.5',
                stck_clpr='25.5',acml_vol='400',acml_tr_pbmn='10100') for d in dates}
    return raw,nominal,adjusted


def test_constant_currency_scaling_is_not_path_error_and_volume_is_separate():
    raw,nom,adj=sample();n,a,b,c=compare_code('000001',raw,nom,adj)
    assert n==a==[] and c['constant_scale']=='0.5' and c['anchor_date']=='2026-07-02'
    assert c['nominal_cells']==12 and c['adjusted_cells']==8
    assert len(b)==2 and all(r['volume_diff'] and not r['amount_diff'] for r in b)
    assert all(r['inverse_price_volume_error_shares']=='0' for r in b)


def test_one_bad_historical_high_and_nominal_amount_are_preserved():
    raw,nom,adj=sample();raw.loc[0,'adj_high']=60;raw.loc[0,'amount']=10099
    n,a,b,c=compare_code('000001',raw,nom,adj)
    assert len(n)==1 and n[0]['field']=='amount' and n[0]['panel']=='10099'
    assert len(a)==1 and a[0]['field']=='high' and a[0]['absolute_difference']=='4.0'
    assert a[0]['exceeds_one_krw'] and c['adjusted_diff_cells_over_one_krw']==1


def test_nonfinite_source_not_dropped_and_no_anchor_is_explicit():
    raw,nom,adj=sample();raw.loc[0,'open']=float('nan');raw['volume']=0
    n,a,b,c=compare_code('000001',raw,nom,adj)
    assert any(r['field']=='open' and r['panel']=='NaN' for r in n)
    assert c['anchor_date'] is None and a==[] and c.get('adjusted_cells',0)==0


def test_date_gaps_and_duplicate_provider_rows_rejected():
    raw,nom,adj=sample();adj.pop('2026-07-01')
    with pytest.raises(ValueError,match='coverage'):compare_code('000001',raw,nom,adj)
    row={**nom['2026-07-01'],'stck_bsop_date':'20260701'}
    with pytest.raises(ValueError,match='duplicate'):
        index_payload({'rt_cd':'0','output2':[row,copy.copy(row)]})


def test_nontrading_ohl_conventions_remain_differences_and_do_not_set_anchor():
    raw,nom,adj=sample()
    day='2026-07-02'
    raw.loc[1,['open','high','low','adj_open','adj_high','adj_low','volume','amount']]=0
    for rows in [nom,adj]:
        rows[day].update(acml_vol='0',acml_tr_pbmn='0')
        for field in ['stck_oprc','stck_hgpr','stck_lwpr']:
            rows[day][field]=rows[day]['stck_clpr']
    original=raw.copy(deep=True)
    n,a,b,c=compare_code('000001',raw,nom,adj)
    assert c['anchor_date']=='2026-07-01'
    assert {r['field'] for r in n}=={'open','high','low'}
    assert len(n)==len(a)==3
    pd.testing.assert_frame_equal(raw,original)
