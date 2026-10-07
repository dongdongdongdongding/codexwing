import pytest
from research.audit_bonus_listing_evidence import parse_listing

KOSPI = ('◎ 회사 보통주 추가상장 ① 주식의 종류와 수 : 기명식 보통주 2,397,456주 '
         '⑤ 증자방법 : 무상증자 ⑥ 상장일 : 2026년08월20일 '
         '⑦ 코드 ▶ 표준코드 : KR7002070001 (단축코드:A002070)')
KOSDAQ = ('추가상장 1.회사명 회사 2.추가주식의 종류와 수 주권종류 단축코드 추가주식수(주) '
          '보통주 A475460 11,293,050 5.상장일 2026-10-13 6.기타 의무보유에 관한 사항 '
          '의무보유주식수 : 2,313,250주 【발행내역】 보통주 무상증자 - 11,293,050')


def test_kospi_notice_uses_share_identity_and_listing_date():
    result = parse_listing(KOSPI, '002070')
    assert result['listing_date'] == '2026-08-20'
    assert result['additional_common_shares'] == 2397456
    assert result['account_unrestricted_credit_verified'] is False


def test_kosdaq_notice_preserves_restriction_without_claiming_account_credit():
    result = parse_listing(KOSDAQ, '475460')
    assert result['listing_date'] == '2026-10-13'
    assert result['additional_common_shares'] == 11293050
    assert result['restriction_types_in_notice'] == ['의무보유']
    assert result['account_unrestricted_credit_verified'] is False


@pytest.mark.parametrize('text,code', [(KOSPI, '002075'), (KOSDAQ, '475465'),
    (KOSDAQ.replace('무상증자','유상증자'), '475460'),
    (KOSDAQ+' 5.상장일 2026-10-14 ', '475460'),
    (KOSDAQ.replace('A475460','A4754600'), '475460'),
    (KOSDAQ+' 보통주 A475460 10 ', '475460')])
def test_wrong_class_action_or_ambiguous_notice_rejected(text, code):
    with pytest.raises(ValueError):
        parse_listing(text, code)
