import pandas as pd
import pytest

from research.audit_large_gap_references import EVENTS, verify_event


def example(spec):
    code,day,ref,prior,close,_,company,cls,*_=spec
    auction=spec[-1]=='auction'
    raw=pd.DataFrame([
        {'code':code,'date':pd.Timestamp(day)-pd.Timedelta(days=1),'close':prior,
         'open':prior,'volume':100,'stocks':70507919,'adj_factor':1.},
        {'code':code,'date':pd.Timestamp(day),'close':close,'open':ref,'volume':200,
         'stocks':53328897,'adj_factor':prior/close if auction else 1.}])
    quote={'stck_clpr':str(close),'acml_vol':'200','prdy_vrss':str(close-ref),
           'prdy_vrss_sign':'2' if close>ref else '5','flng_cls_code':'01',
           'prtt_rate':'-1.00','stck_oprc':str(ref)}
    text=f'{company} {cls} {day}'
    text+=(' 평가가격(원) 83,800 167,600 41,900 회사분할 단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨'
           if auction else f' 기준가격(원) {ref:,} 권리락(유상증자)')
    return raw,quote,text


@pytest.mark.parametrize('spec',EVENTS)
def test_official_reference_and_quote_agree(spec):
    raw,quote,text=example(spec);event=verify_event(spec,raw,quote,text)
    assert event['reference_price']==spec[2]


@pytest.mark.parametrize('spec',EVENTS)
def test_signed_quote_disagreement_rejected(spec):
    raw,quote,text=example(spec);quote['prdy_vrss']=str(int(quote['prdy_vrss'])+1)
    with pytest.raises(ValueError,match='quote_disagreement'):verify_event(spec,raw,quote,text)


def test_evaluated_price_is_not_actual_auction():
    spec=EVENTS[0];raw,quote,text=example(spec);raw.loc[1,'open']=83800;quote['stck_oprc']='83800'
    with pytest.raises(ValueError,match='unproved_actual_auction'):verify_event(spec,raw,quote,text)


def test_preferred_requires_own_class_notice():
    spec=EVENTS[-1];raw,quote,text=example(spec)
    with pytest.raises(ValueError,match='wrong_official_identity'):
        verify_event(spec,raw,quote,text.replace('1우선주','보통주식'))


def test_changed_source_factor_rejected():
    spec=EVENTS[1];raw,quote,text=example(spec);raw.loc[1,'adj_factor']=1.1
    with pytest.raises(ValueError,match='changed_missing_factor'):verify_event(spec,raw,quote,text)


def test_wrong_auction_share_counts_rejected():
    spec=EVENTS[0];raw,quote,text=example(spec);raw.loc[1,'stocks']=70507919
    with pytest.raises(ValueError,match='changed_split_share_counts'):verify_event(spec,raw,quote,text)


def test_zero_volume_auction_cannot_prove_execution():
    spec=EVENTS[0];raw,quote,text=example(spec);raw.loc[1,'volume']=0;quote['acml_vol']='0'
    with pytest.raises(ValueError,match='quote_disagreement'):verify_event(spec,raw,quote,text)
