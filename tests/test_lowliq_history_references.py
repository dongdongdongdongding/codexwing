import copy
from fractions import Fraction
import pandas as pd
import pytest
from research.audit_lowliq_history_references import signed_reference,verify_nontrade
from research.normalize_lowliq_history_references import overlay_rules


def example():
    return ({'close':12230,'volume':170,'stocks':470810},
            {'close':12200,'volume':0,'amount':0,'stocks':470810},
            {'stck_clpr':'12200','prdy_vrss':'-30','prdy_vrss_sign':'5','acml_vol':'0','prtt_rate':'0.00'},
            {'stck_clpr':'12200'})


def test_nontrading_price_change_is_preserved_not_smoothed():
    args=example();assert verify_nontrade(*args,'admin')==12230
    assert signed_reference(args[2])==12230


@pytest.mark.parametrize('which,field,value',[(1,'volume',1),(1,'stocks',470811),(0,'volume',0),
    (2,'prtt_rate','1'),(2,'prdy_vrss','-20'),(2,'prdy_vrss_sign','0'),(3,'stck_clpr','6100')])
def test_ambiguous_nontrading_corporate_basis_fails(which,field,value):
    args=list(copy.deepcopy(example()));args[which][field]=value
    with pytest.raises(ValueError):verify_nontrade(*args,'admin')


def test_wrong_algorithm_rule_is_not_removed():
    with pytest.raises(ValueError):verify_nontrade(*example(),'same_day')


def test_multiple_overlays_compose_once_and_preserve_later_relative_factors():
    raw=pd.DataFrame({'code':['A']*5,'date':pd.date_range('2024-01-01',periods=5),
                      'close':[100,50,60,30,40],'adj_factor':[1.,2.,2.,4.,8.],'stocks':[10]*5})
    events=[{'id':'one','code':'A','date':'2024-01-02','prior_close':100,'first_close':50,
             'before_factor':1.,'old_event_factor':2.,'reference_price':100,
             'multiplier_numerator':1,'multiplier_denominator':2},
            {'id':'two','code':'A','date':'2024-01-04','prior_close':60,'first_close':30,
             'before_factor':2.,'old_event_factor':4.,'reference_price':60,
             'multiplier_numerator':1,'multiplier_denominator':2}]
    result=overlay_rules(raw,events)
    assert [(r['rows'],r['new_factor']) for r in result]==[(2,1.),(1,1.),(1,2.)]
    assert sum(r['rows'] for r in result)==4
    events[0]['multiplier_numerator']=2
    with pytest.raises(ValueError,match='changed_event_multiplier'):overlay_rules(raw,events)
