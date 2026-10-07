import pytest

from research.capture_historical_reference_inventory import windows_for


def event(code,date,name='Example'):
    return {'code':code,'date':date,'provider_names':[name]}


def test_merges_only_overlapping_windows_of_same_code():
    w=windows_for([event('000001','2024-01-01'),event('000001','2024-02-01'),
        event('000001','2024-12-01'),event('000002','2024-01-01')])
    assert len(w)==3
    assert w[0]['event_dates']==['2024-01-01','2024-02-01']
    assert w[0]['begin']=='2023-11-17' and w[0]['end']=='2024-03-17'


def test_missing_name_preserves_ticker_and_event():
    w=windows_for([event('000001','2024-01-01','')])
    assert w[0]['name']=='' and w[0]['code']=='000001'


def test_duplicate_event_aborts():
    with pytest.raises(ValueError,match='duplicate_event'):
        windows_for([event('000001','2024-01-01')]*2)


def test_ambiguous_names_abort_instead_of_guessing():
    with pytest.raises(ValueError,match='ambiguous_security_name'):
        windows_for([event('000001','2024-01-01','A'),event('000001','2024-02-01','B')])
