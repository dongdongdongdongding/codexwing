import copy

import pytest

from research.normalize_kr_ex_reference import CONVENTION, reference_factor, validate_rules


def contract():
    return {'start':'2026-07-15','baseline_factor':1.,'events':[
        {'date':'2026-07-15','prior_close':8750,'reference_price':8470},
        {'date':'2026-09-17','prior_close':8100,'reference_price':6750}]}


def test_compound_official_references_apply_on_date_and_preserve_prior_basis():
    c=contract()
    assert reference_factor(c,'2026-07-14')==1.
    assert reference_factor(c,'2026-07-15')==125/121
    assert reference_factor(c,'2026-09-17')==150/121
    assert reference_factor({'baseline_factor':.2,'events':[]},'2026-09-17')==.2


def test_rule_cannot_cross_another_ex_date_or_substitute_entitlement():
    c=contract();rule={'code':'220100','start':'2026-07-15','end':'2026-09-16','new_factor':125/121}
    spec={'price_convention':CONVENTION,'contracts':{'220100':c},'rules':[rule]}
    validate_rules(spec)
    changed=copy.deepcopy(spec);changed['rules'][0]['end']='2026-09-17'
    with pytest.raises(ValueError,match='factor_disagreement'):validate_rules(changed)
    changed=copy.deepcopy(spec);changed['rules'][0]['new_factor']=1.2
    with pytest.raises(ValueError,match='factor_disagreement'):validate_rules(changed)


@pytest.mark.parametrize('kind',['duplicate','reverse','zero_price','negative_baseline'])
def test_invalid_reference_schedule_fails(kind):
    c=contract()
    if kind=='duplicate':c['events'].append(c['events'][-1])
    if kind=='reverse':c['events'].reverse()
    if kind=='zero_price':c['events'][0]['reference_price']=0
    if kind=='negative_baseline':c['baseline_factor']=-1
    with pytest.raises(ValueError):reference_factor(c,'2026-10-02')
