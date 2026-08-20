"""프런트엔드가 백엔드의 판정 필드를 실제로 그리는가.

**필드를 추가해도 UI 가 안 읽으면 사용자에겐 없는 것과 같다.**
2026-08-20 실측: 백엔드에 rank_note·operator_verdict·lane_frequency·expired·forward_ev 를
넣었는데 프런트 참조가 **전부 0회**였다. 화면엔 아무 변화가 없었다.

이 테스트는 소스를 문자열로 검사한다. 렌더 결과를 검증하진 못하지만
**참조가 사라지는 회귀는 잡는다** — 그것이 실제로 일어난 실패다.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PICKS = ROOT / "web/frontend/src/pages/Picks.tsx"
API = ROOT / "web/frontend/src/api.ts"


@pytest.fixture(scope="module")
def picks_src():
    return PICKS.read_text(encoding="utf-8")


@pytest.mark.parametrize("field", [
    "is_top1", "rank_in_day", "rank_note",
    "operator_verdict", "forward_ev",
    "expired", "stale_days", "lane_frequency",
])
def test_frontend_reads_the_backend_verdict_fields(picks_src, field):
    assert field in picks_src, f"{field} 를 화면이 읽지 않는다 — 사용자에겐 없는 것과 같다"


@pytest.mark.parametrize("field", [
    "rank_in_day", "is_top1", "operator_verdict", "forward_ev",
    "expired", "stale_days", "lane_frequency",
])
def test_pick_type_declares_the_fields(field):
    assert field in API.read_text(encoding="utf-8"), f"Pick 타입에 {field} 가 없다"


def test_table_index_is_not_shown_as_a_rank(picks_src):
    """급소 — `#` 열이 배열 인덱스({i + 1})였다.

    정렬 근거가 없는 숫자인데 사용자는 순위로 읽는다. 실제 당일 순위를 써야 한다.
    """
    assert "{i + 1}</Td>" not in picks_src, "배열 인덱스를 순위처럼 보여주면 안 된다"
    assert "p.rank_in_day != null ?" in picks_src, "실제 순위를 써야 한다"


def test_status_chips_are_one_component_not_two_copies(picks_src):
    """카드 뷰와 테이블 뷰가 같은 함수를 써야 한다.

    두 벌로 두면 한쪽만 고쳐지고 화면이 뷰에 따라 달라진다 —
    백엔드 랭킹에서 실제로 그랬다(DB 경로엔 순위가 없고 원장 경로엔 있었다).
    """
    assert picks_src.count("function StatusChips") == 1, "칩 컴포넌트는 하나여야 한다"
    assert picks_src.count("<StatusChips p={p} />") == 2, "두 뷰 모두 같은 것을 써야 한다"


def test_kill_and_expiry_are_visible_not_only_in_a_tooltip(picks_src):
    """폐기선·만료는 칩으로 보여야 한다 — 상세를 열어야만 보이면 놓친다."""
    assert '⛔ 폐기선' in picks_src
    assert '⏱ 만료' in picks_src
    assert '발화부족' in picks_src
