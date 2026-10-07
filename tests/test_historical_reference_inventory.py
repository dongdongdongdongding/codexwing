import pandas as pd
import pytest

from research.inventory_historical_reference_gaps import inventory_code


def pair(close=60,change=10,factor=1.,volume=10):
    raw=pd.DataFrame([
        dict(code='000001',date=pd.Timestamp('2024-01-02'),open=100,close=100,volume=10,amount=1000,adj_factor=1.,stocks=100),
        dict(code='000001',date=pd.Timestamp('2024-01-03'),open=close,close=close,volume=volume,amount=volume*close,adj_factor=factor,stocks=100)])
    quotes={'2024-01-02':dict(stck_clpr='100',acml_vol='10',acml_tr_pbmn='1000',prdy_vrss='0',prdy_vrss_sign='3'),
            '2024-01-03':dict(stck_clpr=str(close),acml_vol=str(volume),acml_tr_pbmn=str(volume*close),prdy_vrss=str(change),prdy_vrss_sign='2' if change>0 else '3')}
    return raw,quotes


def test_missing_reference_change_is_primary_candidate():
    r=inventory_code(*pair());assert len(r['events'])==1
    assert r['events'][0]['classification']=='PRIMARY_REVIEW_REQUIRED'
    assert r['events'][0]['reference_price']==50
    assert r['counts']['unpaired_scope_boundary']==1


def test_exact_corrected_factor_is_not_candidate():
    r=inventory_code(*pair(factor=2));assert r['events']==[]
    assert r['counts']['exact_factor_agreement']==1


def test_normal_price_return_is_not_action():
    assert inventory_code(*pair(close=110,change=10))['events']==[]


def test_arithmetic_residual_is_retained():
    r=inventory_code(*pair(factor=2.0000000000000004))
    assert r['events'][0]['classification']=='ARITHMETIC_RESIDUAL'


def test_nontraded_factor_boundary_is_unresolved_separately():
    raw,q=pair(factor=2,volume=0);q['2024-01-03']['prdy_vrss_sign']='0'
    r=inventory_code(raw,q);assert not r['events'];assert len(r['nontraded_boundaries'])==1


def test_traded_unsupported_sign_is_not_dropped_as_clean():
    raw,q=pair();q['2024-01-03']['prdy_vrss_sign']='0';r=inventory_code(raw,q)
    assert len(r['unsupported_quotes'])==1;assert r['counts']['unsupported_quote']==1


def test_uncaptured_previous_date_not_assumed_verified():
    raw,q=pair();del q['2024-01-02'];r=inventory_code(raw,q)
    assert not r['events'];assert r['counts']['unpaired_scope_boundary']==1


def test_nominal_disagreement_aborts():
    raw,q=pair();q['2024-01-03']['acml_vol']='11'
    with pytest.raises(ValueError,match='nominal_source_disagreement'):inventory_code(raw,q)


def test_provider_date_absent_in_source_aborts():
    raw,q=pair();q['2024-01-04']=q['2024-01-03']
    with pytest.raises(ValueError,match='provider_date_absent'):inventory_code(raw,q)


def test_duplicate_source_date_aborts():
    raw,q=pair();raw.loc[1,'date']=raw.loc[0,'date']
    with pytest.raises(ValueError,match='invalid_source_identity'):inventory_code(raw,q)
