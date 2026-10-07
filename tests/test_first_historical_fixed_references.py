import pandas as pd
import pytest

from research.audit_first_historical_fixed_references import (
    parse_fixed, security_for, provider_name_for, verify_quote_event)
from research.normalize_lowliq_history_references import overlay_rules


NOTICE=':: 99321_기준가격안내 1. 회사명 JW중외제약 2. 주권종류와 가격 주권종류 기준가격(원) 1우선주 32,750 3. 사유 무상증자 4. 적용일 2023-12-27 5. 근거규정 시행세칙'


def test_fixed_notice_and_explicit_preferred_identity():
    n=parse_fixed(NOTICE)
    assert n['reference']==32750 and n['date']=='2023-12-27'
    assert security_for('001060',n)==('001065','JW중외제약우')
    assert security_for('001510',n) is None


def test_common_share_stays_with_queried_issuer():
    n=parse_fixed(NOTICE.replace('1우선주','보통주식'))
    assert security_for('001060',n)==('001060','JW중외제약')


def test_auction_is_not_misread_as_fixed_reference():
    assert parse_fixed(NOTICE.replace('99321_','99332_')) is None


@pytest.mark.parametrize('old,new',[('32,750','0'),('1우선주','4우선주'),('4. 적용일','4. 미확정일')])
def test_invalid_fixed_notice_rejected(old,new):
    with pytest.raises(ValueError):parse_fixed(NOTICE.replace(old,new))


def test_name_alias_needs_official_class_and_code():
    text='디아이동일(주) 상장종목 : DI동일보통주 KR7001530005 (단축코드:A001530)'
    assert provider_name_for('001530','디아이동일',text)=='DI동일'
    with pytest.raises(ValueError):provider_name_for('001530','디아이동일',text.replace('A001530','A001531'))
    assert provider_name_for('999999','디아이동일',text)=='디아이동일'


def boundary():
    raw=pd.DataFrame([
        dict(code='001065',date=pd.Timestamp('2023-12-26'),close=40000,volume=100,stocks=100,adj_factor=1.),
        dict(code='001065',date=pd.Timestamp('2023-12-27'),close=34000,volume=123,stocks=110,adj_factor=1.1)])
    candidate=dict(code='001065',date='2023-12-27',prior_date='2023-12-26',prior_close=40000,
                   close=34000,before_factor=1.,after_factor=1.1,reference_price=32750)
    quote=dict(stck_clpr='34000',acml_vol='123',prdy_vrss='1250',prdy_vrss_sign='2')
    return candidate,raw,quote,parse_fixed(NOTICE)


def test_official_reference_overrides_wrong_existing_factor():
    event=verify_quote_event(*boundary())
    assert event['multiplier_numerator']==1600 and event['multiplier_denominator']==1441


@pytest.mark.parametrize('field,value',[('close',34001),('adj_factor',1.2),('volume',0),('code','001060')])
def test_changed_source_boundary_rejected(field,value):
    candidate,raw,quote,notice=boundary();raw.loc[1,field]=value
    with pytest.raises(ValueError):verify_quote_event(candidate,raw,quote,notice)


@pytest.mark.parametrize('field,value',[('prdy_vrss','1249'),('prdy_vrss_sign','5'),('acml_vol','124')])
def test_disagreeing_nominal_quote_rejected(field,value):
    candidate,raw,quote,notice=boundary();quote[field]=value
    with pytest.raises(ValueError):verify_quote_event(candidate,raw,quote,notice)


def test_multiple_events_compound_without_losing_prior_correction():
    candidate,raw,quote,notice=boundary();first=verify_quote_event(candidate,raw,quote,notice)
    later=raw.iloc[-1].copy();later['date']=pd.Timestamp('2024-01-02');later['close']=18000;later['adj_factor']=2.2
    raw=pd.concat([raw,pd.DataFrame([later])],ignore_index=True)
    candidate.update(date='2024-01-02',prior_date='2023-12-27',prior_close=34000,close=18000,
                     before_factor=1.1,after_factor=2.2,reference_price=17000)
    second=verify_quote_event(candidate,raw,dict(stck_clpr='18000',acml_vol='123',prdy_vrss='1000',prdy_vrss_sign='2'),
                              dict(notice,date='2024-01-02',reference=17000))
    rules=overlay_rules(raw,[first,second])
    assert rules[-1]['verified_events']==[first['id'],second['id']]
    assert rules[-1]['new_factor']==pytest.approx(40000/32750*2)
