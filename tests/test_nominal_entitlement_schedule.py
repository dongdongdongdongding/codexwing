import pytest
from research.audit_nominal_entitlement_schedule import parse_schedule

@pytest.mark.parametrize('date', ['2026.10.13', '2026년 10월 13일'])
def test_planned_is_never_actual(date):
    text='5. 1주당 신주배정 주식수 보통주식 (주) 0.2 8. 신주의 상장 예정일 '+date
    out=parse_schedule(text)
    assert out['ratio']==[1,5] and out['planned_listing_date']=='2026-10-13'
    assert out['availability_status']=='planned' and out['actual_tradeable_date'] is None


def test_conflicting_schedule_is_not_latest_by_accident():
    text='1주당 신주배정 주식수 보통주식 (주) 1 8. 신주의 상장 예정일 2026.08.20 '
    with pytest.raises(ValueError,match='ambiguous_bonus_schedule'):
        parse_schedule(text+text.replace('2026.08.20','2026.08.25'))
