import pandas as pd
import pytest

from research.audit_aerospace_split_reference import verify_boundary


def evidence():
    raw=pd.DataFrame([
        dict(code='012450',date=pd.Timestamp('2024-09-26'),close=290000,open=0,volume=0,stocks=50630000,adj_factor=1.),
        dict(code='012450',date=pd.Timestamp('2024-09-27'),close=317000,open=300000,volume=1553930,stocks=45581161,adj_factor=1.)])
    quote=dict(stck_clpr='317000',stck_oprc='300000',acml_vol='1553930',prdy_vrss='17000',prdy_vrss_sign='2')
    texts={'method':'한화에어로스페이스 보통주식 2024-09-27 평가가격(원) 290,000 580,000 145,000 회사분할 단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨',
        'listing':'A012450 KR7012450003 50,630,000 45,581,161 2024년09월27일 회사분할(존속)'}
    return raw,quote,texts


def test_actual_auction_overlays_missing_factor():
    r=verify_boundary(*evidence())
    assert (r['reference_price'],r['multiplier_numerator'],r['multiplier_denominator'])==(300000,29,30)


@pytest.mark.parametrize('field,value',[('open',290000),('close',300000),('volume',0),('stocks',50630000),('adj_factor',.9)])
def test_changed_source_boundary_rejected(field,value):
    raw,quote,texts=evidence();raw.loc[1,field]=value
    with pytest.raises(ValueError):verify_boundary(raw,quote,texts)


def test_evaluated_reference_in_quote_is_rejected():
    raw,quote,texts=evidence();quote.update(stck_oprc='290000',prdy_vrss='27000')
    with pytest.raises(ValueError,match='unproved_actual_auction'):verify_boundary(raw,quote,texts)


def test_wrong_official_class_rejected():
    raw,quote,texts=evidence();texts['method']=texts['method'].replace('보통주식','1우선주')
    with pytest.raises(ValueError,match='wrong_auction_method'):verify_boundary(raw,quote,texts)


def test_wrong_listing_identity_rejected():
    raw,quote,texts=evidence();texts['listing']=texts['listing'].replace('A012450','A000880')
    with pytest.raises(ValueError,match='wrong_final_listing'):verify_boundary(raw,quote,texts)
