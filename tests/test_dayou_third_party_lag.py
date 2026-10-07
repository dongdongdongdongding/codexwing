import pandas as pd
import pytest

from research.audit_dayou_third_party_lag import verify_false_lag
from research.normalize_lowliq_history_references import overlay_rules


def example():
    before=322/1130;after=before*46739450/38730299
    raw=pd.DataFrame([
        dict(code='002880',date=pd.Timestamp('2023-12-21'),open=1469.,close=1618.,volume=31369042.,stocks=38730299,adj_factor=before),
        dict(code='002880',date=pd.Timestamp('2023-12-22'),open=1578.,close=1360.,volume=7009766.,stocks=38730299,adj_factor=after),
        dict(code='002880',date=pd.Timestamp('2024-01-18'),open=940.,close=939.,volume=1.,stocks=38730299,adj_factor=after),
        dict(code='002880',date=pd.Timestamp('2024-01-19'),open=940.,close=942.,volume=1.,stocks=46739450,adj_factor=after)])
    quote=dict(stck_oprc='1578',stck_clpr='1360',acml_vol='7009766',prdy_vrss='-258',prdy_vrss_sign='5',prtt_rate='0.00')
    observed=dict(code='002880',date='2023-12-22',rule='lag',trigger_date='2024-01-19',
        trigger_stocks_before=38730299,trigger_stocks_after=46739450,code_rows_between_event_and_trigger=17,
        event_factor=46739450/38730299)
    texts={
        'decision':'회 사 명 : (주)대유에이텍 보통주식 (주) 8,009,151 보통주식 (주) 38,730,299 '
            '5. 증자방식 제3자배정증자 (주)동강홀딩스 2,288,329 (주)푸른산수목원 1,716,247 '
            '(주)대유하늘 1,716,247 박은희 1,144,164 박은진 1,144,164',
        'payment':'기명식 보통주식 2. 발행방법 제3자배정 유상증자 실제발행주식수(주) 8,009,151 '
            '실제발행금액(원) 6,999,997,974 납입일 2023-12-26',
        'listing':'대유에이텍 보통주 추가상장 기명식 보통주 8,009,151주 유상증자(제3자배정) '
            'KR7002880003 (단축코드:A002880) (주)동강홀딩스 외 4인 2024년01월19일 ~ 2025년01월18일'}
    return raw,quote,observed,texts


def test_only_false_bonus_removed_real_consolidation_retained():
    raw,quote,observed,texts=example();event=verify_false_lag(raw,quote,observed,texts)
    rules=overlay_rules(raw,[event])
    assert rules[0]['start']=='2023-12-22'
    assert all(r['new_factor']==raw.adj_factor.iloc[0] for r in rules)
    assert rules[-1]['expected_stocks']==46739450


@pytest.mark.parametrize('which,old,new',[
    ('decision','제3자배정증자','주주배정증자'),('payment','실제발행주식수(주) 8,009,151','실제발행주식수(주) 8,009,150'),
    ('listing','A002880','A002881'),('listing','2024년01월19일','2024년01월20일')])
def test_wrong_economic_event_rejected(which,old,new):
    raw,quote,observed,texts=example();texts[which]=texts[which].replace(old,new)
    with pytest.raises(ValueError,match='unproved_third_party'):verify_false_lag(raw,quote,observed,texts)


@pytest.mark.parametrize('field,value',[('rule','same_day'),('trigger_date','2024-01-18'),
    ('trigger_stocks_after',46739451),('event_factor',1.3)])
def test_different_builder_cause_is_not_removed(field,value):
    raw,quote,observed,texts=example();observed[field]=value
    with pytest.raises(ValueError,match='wrong_algorithm'):verify_false_lag(raw,quote,observed,texts)


@pytest.mark.parametrize('row,field,value',[(1,'stocks',46739450),(1,'adj_factor',1.),
    (1,'volume',0.),(3,'stocks',46739451)])
def test_changed_source_boundary_rejected(row,field,value):
    raw,quote,observed,texts=example();raw.loc[row,field]=value
    with pytest.raises(ValueError):verify_false_lag(raw,quote,observed,texts)


def test_quote_indicating_a_real_reference_change_rejected():
    raw,quote,observed,texts=example();quote['prdy_vrss']='-257'
    with pytest.raises(ValueError,match='wrong_nominal_reference'):verify_false_lag(raw,quote,observed,texts)
