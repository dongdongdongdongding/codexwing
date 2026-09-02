"""픽 페이지와 개요가 같은 픽을 두고 다른 말을 하지 않게 한다.

실측 결함(2026-09-02): `/api/picks` 는 AXTI 에 `blockers` 키를 **아예 안 붙였고**
`/api/overview` 는 같은 픽에서 2건(관측전용·폐기선 아래)을 찾았다. 조립 경로마다
붙이는 곳이 달라서 생긴 일이고, **픽 페이지 쪽이 더 관대했다** —
개요가 「차단」이라 말하는 픽을 픽 페이지는 살 수 있는 것처럼 보여줬다.
"""
import inspect

from web.backend import services as S


def test_every_picks_path_attaches_blockers():
    src = inspect.getsource(S.picks)
    assert src.count("_with_blockers") >= 3, "레인별·B·전체 세 경로 모두 붙어야 한다"


def test_overview_uses_the_shared_helper_not_its_own_loop():
    """두 곳에서 각자 짜면 다시 갈라진다 — 규칙은 `_with_blockers` 한 곳에만 둔다.

    다만 `overview` 가 「`picks` 가 이미 붙여줬겠지」로 가정하면 안 된다:
    `picks` 를 갈아끼우는 호출자에서 KeyError 로 화면이 죽는다(실제로 기존 테스트 5건이 그렇게 깨졌다).
    헬퍼가 멱등이라 다시 불러도 안전하다."""
    src = inspect.getsource(S.overview)
    assert "_with_blockers(picks())" in src
    assert "pick_blockers(p)" not in src


def test_the_helper_is_idempotent():
    rows = [{"ticker": "X"}]
    once = S._with_blockers(rows)
    twice = S._with_blockers(once)
    assert once[0]["blockers"] == twice[0]["blockers"]


def test_helper_uses_the_same_function_as_the_screen():
    src = inspect.getsource(S._with_blockers)
    assert "pick_blockers(r)" in src


def test_blockers_is_always_a_list_never_missing():
    rows = [{"ticker": "X"}, {"ticker": "Y", "blockers": None}]
    out = S._with_blockers(rows)
    assert all(isinstance(r.get("blockers"), list) for r in out)
