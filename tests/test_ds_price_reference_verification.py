import copy
from fractions import Fraction

import pandas as pd
import pytest

from research import audit_ds_price_references as m
from research.normalize_lowliq_history_references import overlay_rules
from research.normalize_verified_kr_events import corrected_chunk


def inputs():
    factor=128800/55800
    rows=[('2024-11-22',128800,1.),('2024-11-25',55800,factor),
          ('2025-12-26',18600,factor),('2025-12-29',18270,factor)]
    raw=pd.DataFrame([{'code':'017860','date':pd.Timestamp(day),'close':close,'volume':100,
                       'adj_factor':f,'stocks':5861404} for day,close,f in rows])
    quotes={'2024-11-25':{'stck_clpr':'55800','prdy_vrss':'12850','prdy_vrss_sign':'1'},
            '2025-12-29':{'stck_clpr':'18270','prdy_vrss':'-150','prdy_vrss_sign':'5'}}
    texts={'bonus_reference':'DS단석 보통주식 42,950 권리락(무상증자) 2024-11-25',
           'dividend_reference':'DS단석 보통주식 18,420 주식배당 2025-12-29'}
    return raw,quotes,texts


def test_two_fixed_references_preserve_return_from_reference_to_first_close():
    raw,quotes,texts=inputs();saved=raw.copy();events=m.verify_reference_events(raw,quotes,texts)
    assert raw.equals(saved) and len(events)==2
    for field in ['open','high','low']:raw[field]=raw.close
    for field in ['open','high','low','close']:raw['adj_'+field]=raw[field]*raw.adj_factor
    rules=overlay_rules(raw,events);corrected,counts=corrected_chunk(raw,rules)
    assert counts=={'017860':3}
    assert corrected.loc[1,'adj_close']/corrected.loc[0,'adj_close']==pytest.approx(55800/42950)
    assert corrected.loc[3,'adj_close']/corrected.loc[2,'adj_close']==pytest.approx(18270/18420)
    assert corrected.loc[1,'adj_factor']!=3  # official tick-rounded reference, not share count
    pd.testing.assert_frame_equal(corrected[['code','date','close','volume','stocks']],raw[['code','date','close','volume','stocks']])


@pytest.mark.parametrize('mutation',['company','class','price','date','reason','prior','close','quote','sign','suspended','factor','duplicate'])
def test_unproved_reference_or_changed_boundary_refused(mutation):
    raw,quotes,texts=inputs()
    if mutation=='company':texts['bonus_reference']=texts['bonus_reference'].replace('DS단석','other')
    elif mutation=='class':texts['bonus_reference']=texts['bonus_reference'].replace('보통주식','우선주식')
    elif mutation=='price':texts['bonus_reference']=texts['bonus_reference'].replace('42,950','42,933')
    elif mutation=='date':texts['bonus_reference']=texts['bonus_reference'].replace('2024-11-25','2024-11-26')
    elif mutation=='reason':texts['dividend_reference']=texts['dividend_reference'].replace('주식배당','현금배당')
    elif mutation=='prior':raw.loc[0,'close']=128700
    elif mutation=='close':raw.loc[1,'close']=55000
    elif mutation=='quote':quotes['2024-11-25']['prdy_vrss']='12800'
    elif mutation=='sign':quotes['2024-11-25']['prdy_vrss_sign']='5'
    elif mutation=='suspended':raw.loc[1,'volume']=0
    elif mutation=='factor':raw.loc[3,'adj_factor']*=1.01
    else:raw=pd.concat([raw,raw.iloc[:1]])
    with pytest.raises(ValueError):m.verify_reference_events(raw,quotes,texts)
