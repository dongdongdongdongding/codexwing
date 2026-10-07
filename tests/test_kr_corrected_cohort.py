import pytest
from research.revalidate_kr_corrected_cohort import coefficient_interval, run


def test_empty_rounding_interval_does_not_become_certified():
    result=coefficient_interval([
        {'source':'100','provider':'50','date':'2026-07-01','field':'close'},
        {'source':'100','provider':'51','date':'2026-07-02','field':'close'},
    ])
    assert not result['nonempty_half_open']
    assert result['closed_bounds_overlap']


def test_source_hash_is_checked_before_cohort_inputs(tmp_path):
    source=tmp_path/'unapproved.parquet';source.write_bytes(b'unapproved')
    with pytest.raises(ValueError,match='changed_corrected_source'):
        run(tmp_path,source,tmp_path/'output','0'*64)
    assert not list((tmp_path/'output').iterdir())
