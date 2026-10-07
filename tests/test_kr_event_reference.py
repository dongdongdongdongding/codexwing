import pytest
from research.audit_kr_event_reference import quote_reference


def row(**updates):
    value={'stck_oprc':'2290','stck_clpr':'2335','prdy_vrss':'45','prdy_vrss_sign':'2','acml_vol':'100'}
    return {**value,**updates}


def test_reference_uses_signed_change_and_open_not_event_close():
    assert quote_reference(row(),2290,2335)==2290


def test_negative_change_is_already_signed():
    assert quote_reference(row(stck_oprc='1175',stck_clpr='979',prdy_vrss='-196',prdy_vrss_sign='5'),1175,979)==1175


@pytest.mark.parametrize('updates',[
    {'prdy_vrss_sign':'5'}, {'prdy_vrss':'0'}, {'prdy_vrss_sign':'0'},
    {'acml_vol':'0'}, {'stck_oprc':'2030'}, {'prdy_vrss':'-45'},
])
def test_unproved_reference_fails_closed(updates):
    with pytest.raises(ValueError):quote_reference(row(**updates),2290,2335)


@pytest.mark.parametrize('opening,closing',[(2030,2335),(2290,2290)])
def test_independent_source_disagreement_fails(opening,closing):
    with pytest.raises(ValueError):quote_reference(row(),opening,closing)
