"""선언한 중지가 실제로 SKIP 을 만드는가 (trace-ops-flag-mismatch.md).

배경: 2026-07-05 `b6d2477` 이 nasdaq_session_edge 레인을 "기본 OFF" 로 껐다고 선언했다.
실제로는 `run_daily_ops.sh` 의 가드가 3단 폴백이었다 —

    ${AG_NASDAQ_SESSION_EDGE_ENABLE:-${AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-0}}

1순위 신규명은 리포 전체에서 설정하는 곳이 0건, 2순위 레거시명은 호출자
(`run_primary_market_session_ops.py:298`)가 `os.getenv(..., "1")` 로 **항상 주입**한다.
따라서 07-05 에 고친 3순위 리터럴은 **도달 불가능**했고 편집은 스케줄 경로에서 no-op 이었다.
레인은 2026-06-30 승격 이래 100회 실행 SKIP 0회로 계속 돌았다.

이 테스트가 고정하는 계약은 하나다: **끄면 실제로 꺼지고, 그 사실이 로그에 보인다.**
`test_legacy_nested_fallback_was_a_no_op` 은 검출기 자체의 회귀다 — 옛 형태를 그대로
재현해서 정말 무효였는지 확인한다. 이게 실패하면 시나리오가 무뎌진 것이므로 나머지
테스트의 통과가 의미를 잃는다.

`run_daily_ops.sh` 전체는 네트워크·DB·KIS 를 건드리므로 테스트에서 통째로 돌릴 수 없다
(`DAILY_OPS_DRY_RUN` 은 updater 인자만 바꿀 뿐 실행을 건너뛰지 않는다). 그래서 해당 스텝의
`if..fi` 블록을 **원문 그대로 잘라내서** 돌린다 — 재구현 사본이 아니라 실제 코드 텍스트다.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
OPS = REPO / "multi_agent" / "tools" / "run_daily_ops.sh"
SYSTEM_BASH = "/bin/bash"

FLAG = "AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE"
DEAD_NAME = "AG_NASDAQ_SESSION_EDGE_ENABLE"      # 배선된 적 없는 신규명
STEP = "report_nasdaq_session_edge_shadow"

# 블록을 돌리기 위한 최소 스텁. run_optional 만 막으면 python3 는 인자로만 남아 실행되지 않는다.
HARNESS = """#!/bin/bash
set -uo pipefail
run_optional() { echo "[RAN] $1"; }
%s
"""


def guard_block(step: str = STEP) -> str:
    """스텝을 감싸는 `if ... fi` 블록을 run_daily_ops.sh 에서 원문 그대로 추출한다."""
    lines = OPS.read_text(encoding="utf-8").splitlines()
    step_idx = next((i for i, l in enumerate(lines) if f'[STEP] {step}' in l), None)
    assert step_idx is not None, f"{step} 스텝을 찾지 못했다 — 추출이 깨진 것"
    start = next((i for i in range(step_idx, -1, -1)
                  if lines[i].startswith("if [[") and "SESSION_EDGE" in lines[i]), None)
    assert start is not None, "가드 if 문을 찾지 못했다 — 추출이 깨진 것"
    depth = 0
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s.startswith("if "):
            depth += 1
        elif s == "fi":
            depth -= 1
            if depth == 0:
                return "\n".join(lines[start:i + 1])
    pytest.fail("가드 블록의 fi 를 찾지 못했다")


def run_block(block: str, tmp_path: Path, **flags) -> str:
    """블록을 격리된 env 로 실행하고 stdout+stderr 를 돌려준다."""
    script = tmp_path / "block.sh"
    script.write_text(HARNESS % block, encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("AG_NASDAQ_SESSION_EDGE")}
    env.update({k: str(v) for k, v in flags.items()})
    r = subprocess.run([SYSTEM_BASH, str(script)], capture_output=True, text=True,
                       timeout=60, env=env, cwd=str(REPO))
    return r.stdout + r.stderr


# ---------------------------------------------------------------------------
# 검출기 회귀 — 옛 형태가 정말 무효였는가
# ---------------------------------------------------------------------------

def test_legacy_nested_fallback_was_a_no_op(tmp_path):
    """옛 3단 폴백 + 호출자의 강제 주입 조합에서는 안쪽 리터럴을 0 으로 바꿔도 계속 돈다.

    b6d2477 이 바꾼 것이 바로 그 안쪽 리터럴 한 글자였다.
    """
    legacy = (f'if [[ "${{{DEAD_NAME}:-${{{FLAG}:-0}}}}" == "1" ]]; then\n'
              f'  echo "[STEP] {STEP}"\n'
              f'else\n'
              f'  echo "[SKIP] {STEP}"\n'
              f'fi')
    # 호출자가 레거시명을 "1" 로 주입하던 실제 상황
    out = run_block(legacy, tmp_path, **{FLAG: "1"})
    assert f"[STEP] {STEP}" in out, "옛 형태 재현 실패 — 시나리오가 무뎌졌다"
    assert "[SKIP]" not in out, "안쪽 리터럴 0 이 효력을 가졌다 — 전제가 바뀌었다"


# ---------------------------------------------------------------------------
# 현재 가드 — 끄면 실제로 꺼지는가
# ---------------------------------------------------------------------------

def test_flag_zero_actually_skips(tmp_path):
    """이 파일의 존재 이유. 끈다고 선언하면 실제로 SKIP 이 찍혀야 한다."""
    out = run_block(guard_block(), tmp_path, **{FLAG: "0"})
    assert f"[SKIP] {STEP}" in out, f"0 으로 껐는데 SKIP 이 없다:\n{out}"
    assert f"[STEP] {STEP}" not in out, f"0 으로 껐는데 스텝이 실행됐다:\n{out}"
    assert "[RAN]" not in out, f"0 으로 껐는데 run_optional 이 호출됐다:\n{out}"


def test_flag_one_runs_the_step(tmp_path):
    out = run_block(guard_block(), tmp_path, **{FLAG: "1"})
    assert f"[STEP] {STEP}" in out
    assert f"[RAN] {STEP}" in out
    assert "[SKIP]" not in out


def test_default_keeps_the_lane_running(tmp_path):
    """운영자 결정: 이 레인은 수리해 존속. 미설정 기본값은 ON 이어야 한다.

    (스케줄 경로의 실효 기본값이 계속 ON 이었으므로 이것이 동작 보존이다.)
    """
    out = run_block(guard_block(), tmp_path)
    assert f"[STEP] {STEP}" in out, f"기본값이 레인을 껐다 — 운영자 결정과 어긋난다:\n{out}"


def test_skip_line_names_how_to_resume(tmp_path):
    """조용한 SKIP 금지 — 왜 꺼졌고 어떻게 켜는지가 로그에 있어야 한다."""
    out = run_block(guard_block(), tmp_path, **{FLAG: "0"})
    assert FLAG in out, f"SKIP 줄이 어떤 플래그 때문인지 밝히지 않는다:\n{out}"


# ---------------------------------------------------------------------------
# 구조 잠금 — 같은 형태의 재발 방지
# ---------------------------------------------------------------------------

def test_guard_uses_a_single_name():
    block = guard_block()
    head = block.splitlines()[0]
    assert FLAG in head, f"가드가 정본 이름을 쓰지 않는다: {head}"
    assert ":-${" not in head, (
        f"중첩 2이름 폴백이 다시 들어왔다 — 안쪽 기본값이 도달 불가해진다: {head}")


def test_dead_flag_name_is_gone_from_the_repo():
    """배선된 적 없는 이름을 남겨두면 '고쳤는데 안 되는' 자리가 다시 생긴다."""
    hits = subprocess.run(["git", "grep", "-n", DEAD_NAME], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    real = []
    for line in hits.splitlines():
        path, _, text = line.partition(":")[0], None, line.split(":", 2)[-1]
        if path.startswith("tests/") or path.endswith(".md"):
            continue                      # 테스트 자신과 문서의 언급은 대상 아님
        if text.strip().startswith("#"):
            continue                      # 주석의 역사 기록은 남겨 두는 편이 낫다
        real.append(line)
    assert not real, ("배선되지 않은 이름이 코드에서 아직 참조된다:\n" + "\n".join(real))


def test_no_onoff_guard_uses_a_nested_two_name_fallback():
    """run_daily_ops.sh 전체 규칙. 값 인자(`--panel "${A:-${B:-x}}"`)는 대상이 아니다 —
    켜고 끄는 판정만 단일 이름이어야 기본값 편집이 그대로 효력을 갖는다."""
    bad = []
    for i, line in enumerate(OPS.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not (s.startswith("if [[") and '== "1"' in s):
            continue
        if re.search(r'\$\{AG_[A-Z0-9_]+:-\$\{', s):
            bad.append(f"{i}: {s}")
    assert not bad, "on/off 가드에 중첩 2이름 폴백이 있다:\n" + "\n".join(bad)


def test_every_declared_stop_has_a_visible_skip():
    """중지를 선언한 가드는 else 로 SKIP 을 남겨야 한다 — 100회 실행 SKIP 0회를
    아무도 눈치채지 못한 것이 이 사고의 절반이다."""
    block = guard_block()
    assert "else" in block and "[SKIP]" in block, (
        f"가드에 SKIP 분기가 없다 — 꺼져도 로그에 흔적이 없다:\n{block[:400]}")
