import pytest

from research.normalize_kr_fixed_reference import CONVENTION, overlay_factor, validate_rules


def contract():
    return {'date':'2026-07-16','before_factor':1.,'old_event_factor':.19,'prior_close':310,'reference_price':1550}


def test_overlay_preserves_later_unreviewed_event_multiplier():
    c=contract()
    assert overlay_factor(.19,c)==.2
    assert overlay_factor(.114,c)==.12  # Subsequent 0.6 event retained, not flattened.


def test_overlay_cannot_rewrite_pre_event_or_use_other_price_basis():
    c=contract();rule={'code':'006490','start':'2026-07-16','end':'2026-09-09','old_factor':.19,'new_factor':.2}
    spec={'price_convention':CONVENTION,'contracts':{'006490':c},'rules':[rule]};validate_rules(spec)
    rule['start']='2026-07-15'
    with pytest.raises(ValueError,match='dates'):validate_rules(spec)
    rule['start']='2026-07-16';rule['new_factor']=.19
    with pytest.raises(ValueError,match='factor_disagreement'):validate_rules(spec)


@pytest.mark.parametrize('field',['before_factor','old_event_factor','prior_close','reference_price'])
def test_nonpositive_reference_input_rejected(field):
    c=contract();c[field]=0
    with pytest.raises(ValueError,match='invalid_fixed_reference_input'):overlay_factor(.19,c)
