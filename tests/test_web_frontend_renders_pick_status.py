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
OVERVIEW = ROOT / "web/frontend/src/pages/Overview.tsx"
UI = ROOT / "web/frontend/src/components/ui.tsx"
API = ROOT / "web/frontend/src/api.ts"


@pytest.fixture(scope="module")
def picks_src():
    return PICKS.read_text(encoding="utf-8") + UI.read_text(encoding="utf-8")


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


def test_status_chips_live_in_one_shared_component():
    """픽 페이지·개요가 같은 컴포넌트를 써야 한다.

    페이지마다 사본을 두면 한쪽만 고쳐진다. 실제로 그랬다 — 픽 페이지엔 판정을
    그렸는데 **첫 화면인 개요엔 아무것도 없어서** 사용자는 "적중확률 84.4%"만
    보고 있었다. 그 레인은 forward EV +0.09% 로 폐기선 아래다.
    """
    ui = UI.read_text(encoding="utf-8")
    pk = PICKS.read_text(encoding="utf-8")
    ov = OVERVIEW.read_text(encoding="utf-8")
    assert ui.count("export function StatusChips") == 1, "정의는 공용 ui.tsx 한 곳"
    assert "function StatusChips" not in pk and "function StatusChips" not in ov, "페이지 사본 금지"
    assert pk.count("<StatusChips p={p} />") == 2, "카드 뷰·테이블 뷰 모두"
    assert "<StatusChips p={p} />" in ov, "개요에도 판정이 보여야 한다"
    assert "StatusChips" in ov.split("from \"../components/ui\"")[0], "공용에서 가져와야 한다"


def test_overview_does_not_show_the_array_index_as_a_rank():
    """개요는 첫 화면이다 — 여기서 #1 이 실제 1순위가 아니면 가장 크게 오해한다."""
    ov = OVERVIEW.read_text(encoding="utf-8")
    assert "#{i + 1}" not in ov, "배열 인덱스를 순위처럼 보여주면 안 된다"
    assert "rank_in_day" in ov


def test_overview_pairs_the_model_score_with_the_realised_ev():
    """확률만 크게 보이면 폐기선 아래 레인도 좋아 보인다."""
    ov = OVERVIEW.read_text(encoding="utf-8")
    assert "적중확률" in ov and "실측 EV" in ov, "모델 점수와 실현 성적을 나란히 둔다"


def test_kill_and_expiry_are_visible_not_only_in_a_tooltip(picks_src):
    """폐기선·만료는 칩으로 보여야 한다 — 상세를 열어야만 보이면 놓친다."""
    assert '폐기선 EV' in picks_src
    assert '⏱ 만료' in picks_src
    assert '발화부족' in picks_src


def test_compass_does_not_vanish_silently_on_failure():
    """카드가 조용히 사라지면 사용자는 '없는 것'과 '못 불러온 것'을 구분 못 한다.

    2026-08-20 에 실제로 겪었다 — `if (!c) return null` + `.catch(() => {})` 라
    콜드 스타트 2초 동안 나침반이 통째로 없어졌고, 화면이 깨진 줄 알았다.
    이 리포에서 가장 비쌌던 실패가 조용한 실패다.
    """
    ov = OVERVIEW.read_text(encoding="utf-8")
    assert "if (!c) return null;" not in ov, "실패/지연을 화면에 남겨야 한다"
    assert "불러오지 못했다" in ov and "불러오는 중" in ov
    assert ".catch(() => {})" not in ov.split("function Compass")[1], "에러를 삼키면 안 된다"
