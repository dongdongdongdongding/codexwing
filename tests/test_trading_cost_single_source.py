"""왕복 비용이 다시 세 값으로 갈라지는 것을 막는다.

2026-08-25 이전에 이 값은 0.30 / 0.33 / 0.6 세 개로 저장소 안에 흩어져 있었다.
두 배 차이가 나는 값들이 같은 원장을 채점했고, 폐기선 판정은 가장 낙관적인
0.30 을 썼다. 어느 것도 실측이 아니었다(운영자 실측: 0.215).
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
# 비용 상수를 쓰는 것으로 알려진 경로. 새로 생기면 여기에 추가하지 말고
# modules.trading_costs 에서 import 하게 만들어라 — 그게 이 테스트의 요점이다.
SCANNED = ("modules", "web", "multi_agent")


def test_single_definition_exists():
    from modules.trading_costs import KR_ROUNDTRIP_COST_PCT, US_ROUNDTRIP_COST_PCT

    assert KR_ROUNDTRIP_COST_PCT == 0.215
    # US 는 KR 실측치를 쓰면 안 된다 — 세금 구조가 다르다.
    assert US_ROUNDTRIP_COST_PCT != KR_ROUNDTRIP_COST_PCT


def test_no_other_module_defines_its_own_cost():
    """`...COST...= <숫자>` 형태의 정의는 단일 출처 파일에만 있어야 한다.

    첫 판에서는 정규식이 `_PCT` 접미사를 요구해 `COST = 0.3` 세 개를 놓쳤다.
    이름이 아니라 **역할**로 잡아야 한다.
    """
    pat = re.compile(r"^\s*[A-Z_]*COST[A-Z_]*\s*=\s*[0-9]", re.M)
    offenders = []
    for top in SCANNED:
        for path in (REPO / top).rglob("*.py"):
            if "/tests/" in str(path) or path.name.startswith("test_"):
                continue
            if path.name == "trading_costs.py":
                continue
            if pat.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(REPO)))
    assert not offenders, (
        "비용 상수를 자기 파일에 다시 정의했다: "
        + ", ".join(offenders)
        + " — modules.trading_costs 에서 import 해라."
    )


@pytest.mark.parametrize(
    "module_path,attr",
    [
        ("web.backend.services", "COST_PCT"),
        ("modules.kosdaq_intraday_vwap_guard", "ROUNDTRIP_COST_PCT"),
    ],
)
def test_call_sites_resolve_to_the_single_source(module_path, attr):
    import importlib

    from modules.trading_costs import ROUNDTRIP_COST_PCT

    mod = importlib.import_module(module_path)
    assert getattr(mod, attr) == ROUNDTRIP_COST_PCT
