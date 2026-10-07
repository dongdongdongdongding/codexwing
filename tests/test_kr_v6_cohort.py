import pytest
from research.revalidate_kr_v6_cohort import coefficient_interval


def cell(source,provider):
    return {'date':'2026-07-01','field':'close','source':source,'provider':provider}


def test_consistent_integer_observations_bound_one_coefficient():
    result=coefficient_interval([cell('100','50'),cell('200','100')])
    assert result['lower_inclusive']=='0.5'
    assert result['upper_exclusive']=='0.505'
    assert result['nonempty_half_open']


def test_excluded_boundary_is_not_certified_as_nonempty():
    result=coefficient_interval([cell('100','50'),cell('100','51')])
    assert not result['nonempty_half_open']
    assert result['closed_bounds_overlap']


def test_tiny_float_gap_is_reported_without_tolerance_waiver():
    result=coefficient_interval([cell('100','50'),cell('99.99999999999999','51')])
    assert not result['closed_bounds_overlap']
    assert result['relative_gap']!='0'


@pytest.mark.parametrize('source',['0','-1','NaN','Infinity'])
def test_invalid_source_fails_closed(source):
    with pytest.raises(ValueError):coefficient_interval([cell(source,'1')])
