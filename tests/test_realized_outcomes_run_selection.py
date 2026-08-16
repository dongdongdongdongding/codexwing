"""정산기가 고르는 "최근 N개" RUN 이 실제로 최근인가.

배경: `update_realized_outcomes.py:61` 이 `sorted(runs, key=lambda p: p.name)` 이었다.
RUN 디렉터리 이름은 `RUN-<랜덤16진수>` 라 **시간 정보가 없다.** 따라서 `runs[-limit:]` 는
"최근 200개"가 아니라 이름이 `RUN-FF…` 쪽인 **고정된 임의 200개**를 뽑는다.

라이브 실측(2026-08-16, RUN 1601개):
    이름순 최근200 ∩ 시간순 최근200 = **25/200**
    이름순 200 mtime 범위 = 2026-06-15 ~ 08-15  (두 달에 흩어짐)
    시간순 200 mtime 범위 = 2026-08-08 ~ 08-15  (최근 7일)
    이름순 200 의 이름 접두 = DF, E0…FF 만

같은 200개가 매번 다시 처리되고 나머지는 영원히 손이 닿지 않아 미정산이 쌓였다.
이름 분포가 우연히 균등해도 시간과 무관하므로, 이 테스트는 **이름과 시간이 어긋나게**
꾸민 표본으로 정렬키가 시간인지 확인한다.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
mod = importlib.import_module("multi_agent.tools.update_realized_outcomes")


def make_runs(root: Path, specs) -> dict:
    """specs: [(name_suffix, mtime)] — 이름과 mtime 을 따로 준다."""
    made = {}
    for suffix, mtime in specs:
        p = root / f"RUN-{suffix}"
        p.mkdir()
        os.utime(p, (mtime, mtime))
        made[suffix] = p
    return made


def test_selection_is_by_time_not_name(tmp_path):
    """이름 오름차순과 시간 오름차순이 **정반대**인 표본.

    이름순으로 뽑으면 가장 오래된 것들이 나오고, 시간순으로 뽑아야 최근이 나온다.
    """
    specs = [(f"{i:02X}", 1000 + (100 - i)) for i in range(1, 21)]   # 이름↑ = 시간↓
    made = make_runs(tmp_path, specs)

    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=5)

    newest = sorted(made.values(), key=lambda p: p.stat().st_mtime)[-5:]
    assert set(picked) == set(newest), (
        "이름순으로 뽑고 있다 — 이름에는 시간 정보가 없다\n"
        f"  뽑힘: {sorted(p.name for p in picked)}\n"
        f"  기대: {sorted(p.name for p in newest)}")


def test_name_prefix_skew_does_not_bias_selection(tmp_path):
    """라이브 실패 형태 재현: 최근 RUN 의 이름이 전부 낮은 접두(00…)여도 뽑혀야 한다.

    실측에서는 반대로 이름 높은 쪽(DF…FF)만 뽑히고 있었다. 어느 쪽이든 **이름 분포가
    선택에 영향을 주면 안 된다.**
    """
    old = [(f"F{i:X}", 1000 + i) for i in range(10)]        # 이름 높음 · 오래됨
    new = [(f"0{i:X}", 5000 + i) for i in range(10)]        # 이름 낮음 · 최근
    made = make_runs(tmp_path, old + new)

    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=10)

    assert {p.name for p in picked} == {f"RUN-0{i:X}" for i in range(10)}, (
        f"이름 접두에 끌려갔다: {sorted(p.name for p in picked)}")
    assert made["F0"] not in picked


def test_selection_is_stable_when_names_are_random(tmp_path):
    """실제 이름은 랜덤 16진수다 — 시간 정렬이면 이름과 무관하게 항상 최근 k개다."""
    import random
    rng = random.Random(20260816)
    specs = [("%016X" % rng.getrandbits(64), 1000 + i) for i in range(60)]
    made = make_runs(tmp_path, specs)
    expected = {p.name for p in sorted(made.values(), key=lambda x: x.stat().st_mtime)[-15:]}

    picked = {p.name for p in mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=15)}

    assert picked == expected


def test_zero_limit_takes_everything(tmp_path):
    make_runs(tmp_path, [(f"{i:02X}", 1000 + i) for i in range(7)])
    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=0)
    assert len(picked) == 7


def test_limit_larger_than_population_is_safe(tmp_path):
    make_runs(tmp_path, [(f"{i:02X}", 1000 + i) for i in range(3)])
    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=200)
    assert len(picked) == 3


def test_explicit_run_ids_bypass_the_limit(tmp_path):
    """--run-id 경로는 이번 변경의 대상이 아니다 — 회귀하지 않는지 확인."""
    made = make_runs(tmp_path, [(f"{i:02X}", 1000 + i) for i in range(5)])
    picked = mod._iter_target_runs(shared_dir=tmp_path,
                                   run_ids=["RUN-00", "RUN-04", "RUN-NOPE"], limit_runs=1)
    assert set(picked) == {made["00"], made["04"]}, "존재하는 것만, 한도 무시"


def test_non_run_entries_are_ignored(tmp_path):
    make_runs(tmp_path, [("AA", 1000)])
    (tmp_path / "notarun").mkdir()
    (tmp_path / "RUN-file.json").write_text("{}", encoding="utf-8")
    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=0)
    assert [p.name for p in picked] == ["RUN-AA"]


def test_selection_is_ordered_oldest_first(tmp_path):
    """뒤에서 자르는 구조라 정렬 방향이 뒤집히면 가장 오래된 것을 뽑는다."""
    made = make_runs(tmp_path, [(f"{i:02X}", 1000 + i) for i in range(10)])
    picked = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=0)
    mtimes = [p.stat().st_mtime for p in picked]
    assert mtimes == sorted(mtimes), "정렬이 오름차순이 아니다 — [-limit:] 가 최근을 못 집는다"
    assert picked[-1] == made["09"]


# ---------------------------------------------------------------------------
# 형제 도구 — 같은 이름-정렬 버그 (만료의 상류)
# ---------------------------------------------------------------------------
# update_realized_outcomes 만 고쳐서는 재발을 못 막는다. 수익률 지표 산출기가 같은 방식으로
# RUN 을 고르기 때문에 대부분의 RUN 에서 return_{h}d_pct 가 계산되지 않고, 정산기는 해결
# 근거를 못 찾아 HORIZON_ELAPSED_NO_RESOLUTION 으로 만료시킨다. 7,171건 만료의 상류가 여기다.

metrics = importlib.import_module("multi_agent.tools.update_outcome_return_metrics")


def test_metrics_producer_also_selects_by_time(tmp_path):
    specs = [(f"{i:02X}", 1000 + (100 - i)) for i in range(1, 21)]   # 이름↑ = 시간↓
    made = make_runs(tmp_path, specs)

    picked = metrics._iter_runs(shared_dir=tmp_path, run_ids=[], limit_runs=5)

    newest = sorted(made.values(), key=lambda p: p.stat().st_mtime)[-5:]
    assert set(picked) == set(newest), (
        "지표 산출기가 이름순으로 고른다 — 정산기만 고치면 만료가 계속 쌓인다\n"
        f"  뽑힘: {sorted(p.name for p in picked)}")


def test_both_producers_agree_on_the_same_runs(tmp_path):
    """두 도구가 같은 RUN 집합을 봐야 지표→정산 사슬이 끊기지 않는다."""
    import random
    rng = random.Random(20260816)
    make_runs(tmp_path, [("%016X" % rng.getrandbits(64), 1000 + i) for i in range(50)])
    a = mod._iter_target_runs(shared_dir=tmp_path, run_ids=[], limit_runs=20)
    b = metrics._iter_runs(shared_dir=tmp_path, run_ids=[], limit_runs=20)
    assert {p.name for p in a} == {p.name for p in b}
