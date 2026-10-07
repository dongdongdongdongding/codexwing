from decimal import Decimal

import pytest

from research.audit_kr_exrights_basis import parse_notice, project_price


def test_preferred_notice_preserves_security_identity():
    text='권리락 기준가격 안내 1. 회사명 계양전기 2. 주식의 종류와 가격 주권종류 기준가격(원) 1우선주 6,710 3. 사유 권리락(유상증자) 4. 적용일 2026-07-27'
    row=parse_notice('012200','권리락 기준가격 안내(계양전기우)',text)
    assert row['code']=='012205' and row['query_code']=='012200'
    assert row['reference_price']=='6710' and row['identity_basis']=='issuer_name_and_stock_class'
    with pytest.raises(ValueError):parse_notice('012200','계양전기우',text.replace('1우선주','보통주식'))


def test_direct_code_notice_and_missing_structure():
    row=parse_notice('340570','권리락(무상증자)','티앤엘 보통주식 A340570 33,200 2026-08-06 무상증자')
    assert row['kind']=='bonus' and row['reference_price']=='33200'
    with pytest.raises(ValueError):parse_notice('340570','권리락', 'empty response')


def test_rounding_hypotheses_are_distinct_and_do_not_round_to_nearest():
    assert project_price('2505',['-16.37'])==2094
    assert project_price('3',['-10','-10'])==2
    assert project_price('3',['-10','-10'],round_each=True)==1
    assert project_price('2505',[])==Decimal('2505')
