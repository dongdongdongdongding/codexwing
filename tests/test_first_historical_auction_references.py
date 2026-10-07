import pandas as pd
import pytest

from research.audit_first_historical_auction_references import (
    parse_auction,verify_identity,verify_listing,verify_auction)

METHOD=(':: 99409_매매거래재개 기준가격결정방법 안내 1. 회사명 만호제강 '
    '2. 주권종류와 가격 주권종류 평가가격(원) 최고호가(원) 최저호가(원) 보통주식 '
    '47,150 94,300 23,600 3. 기준가격 결정방법 최저호가가격 및 최고호가가격의 범위내에서 '
    '단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨 '
    '4. 매매방법 결정된 기준가격을 기준으로 상하 30% 5. 사유 매매거래재개 '
    '6. 적용일 2024-09-23 7. 근거규정 시행세칙')


def sample():
    raw=pd.DataFrame([
        dict(code='001080',date=pd.Timestamp('2024-09-20'),open=0.,close=47150.,volume=0.,stocks=4150000,adj_factor=1.),
        dict(code='001080',date=pd.Timestamp('2024-09-23'),open=45000.,close=36300.,volume=36168.,stocks=4150000,adj_factor=1.)])
    quote=dict(stck_oprc='45000',stck_clpr='36300',acml_vol='36168',prdy_vrss='-8700',prdy_vrss_sign='5')
    candidate=dict(code='001080',date='2024-09-23',prior_date='2024-09-20',prior_close=47150.,close=36300.,reference_price=45000)
    return '001080',raw,quote,parse_auction(METHOD),candidate


def test_actual_auction_not_evaluated_or_event_close():
    event=verify_auction(*sample())
    assert event['reference_price']==45000 and event['evaluated_price']==47150
    assert (event['multiplier_numerator'],event['multiplier_denominator'])==(943,900)


@pytest.mark.parametrize('old,new',[
    ('보통주식','1우선주'),('47,150 94,300 23,600','47,150 94,300 100,000'),
    ('단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨','평가가격을 기준가격으로 사용'),
    ('6. 적용일','6. 예정일')])
def test_unproved_method_or_class_rejected(old,new):
    with pytest.raises(ValueError):parse_auction(METHOD.replace(old,new))


def test_fixed_reference_is_excluded():
    assert parse_auction(METHOD.replace('99409_','99321_')) is None


@pytest.mark.parametrize('field,value',[('open',47150.),('close',45000.),('volume',0.),('stocks',4000000),('code','001081')])
def test_changed_boundary_rejected(field,value):
    code,raw,quote,notice,candidate=sample();raw.loc[1,field]=value
    with pytest.raises(ValueError):verify_auction(code,raw,quote,notice,candidate)


@pytest.mark.parametrize('field,value',[('stck_oprc','47150'),('prdy_vrss','-1'),('acml_vol','36169')])
def test_nominal_disagreement_rejected(field,value):
    code,raw,quote,notice,candidate=sample();quote[field]=value
    with pytest.raises(ValueError):verify_auction(code,raw,quote,notice,candidate)


def test_outside_official_auction_bounds_rejected():
    code,raw,quote,notice,candidate=sample();notice['lower']=46000
    with pytest.raises(ValueError):verify_auction(code,raw,quote,notice,candidate)


def test_existing_cumulative_factor_is_preserved():
    code,raw,quote,notice,candidate=sample();raw['adj_factor']=2.5
    event=verify_auction(code,raw,quote,notice,candidate)
    assert event['before_factor']==event['old_event_factor']==2.5
    assert (event['multiplier_numerator'],event['multiplier_denominator'])==(943,900)


def test_historical_name_requires_exact_official_viewer_binding():
    n=dict(company='백광산업')
    html='<h1 class="ttl">PKC (001340)</h1>'
    result=verify_identity('001340',n,'PKC',html,'PKC')
    assert result['official_company_at_notice']=='백광산업'
    with pytest.raises(ValueError):verify_identity('001340',n,'PKC',html.replace('001340','001341'),'PKC')
    with pytest.raises(ValueError):verify_identity('001340',dict(company='다른회사'),'PKC',html,'PKC')


def test_missing_provider_name_requires_scoped_exception():
    r=verify_identity('001140',dict(company='국보'),'국보','<h1 class="ttl">국보 (001140)</h1>',None)
    assert r['provider_name_unavailable']
    with pytest.raises(ValueError):verify_identity('001080',dict(company='만호제강'),'만호제강','<h1 class="ttl">만호제강 (001080)</h1>',None)


def test_par_value_reduction_does_not_imply_fewer_shares():
    text=('한솔테크닉스보통주 보통주 32,109,878주 (변경사항 없음) '
          '액면가액 : 5,000원 → 1,000원 2025년09월26일 KR7004710000 (단축코드:A004710)')
    verify_listing('004710','2025-09-26',text,32109878,32109878)
    with pytest.raises(ValueError):verify_listing('004710','2025-09-26',text,32109878,6421976)
    with pytest.raises(ValueError):verify_listing('004710','2025-09-26',text.replace('A004710','A004711'),32109878,32109878)


def test_concurrent_cb_increase_is_separate_from_par_value_reduction():
    text=('케이지모빌리티보통주 5,952,380주 국내CB전환 202,356,634주 (변경사항 없음) '
          '액면가액 : 5,000원 → 1,000원 2025년05월09일 KR7003620002 (단축코드 : A003620)')
    verify_listing('003620','2025-05-09',text,196404254,202356634)
    with pytest.raises(ValueError):verify_listing('003620','2025-05-09',text,202356634,202356634)
