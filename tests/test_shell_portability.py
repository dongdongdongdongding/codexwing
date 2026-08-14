"""셸 스크립트 이식성 회귀 (swing-main-7x7h).

배경: macOS 기본 `/bin/bash`는 3.2.57이다. 3.2는 `set -u` 아래에서 **빈 배열 확장**을
`unbound variable`로 죽인다(4.4+에서 고쳐진 동작). `run_daily_ops.sh`가 바로 이 패턴을
써서 2026-06-08~08-14 데일리옵스가 153회 실행 153회 실패했고, 마지막 2스텝
(emit_daily_backtest / report_daily_model_foundation_gate)은 한 번도 성공한 적이 없다.
로그에만 남는 실패라 2개월간 아무도 몰랐다.

launchd는 `/bin/bash`를 명시적으로 호출하므로(`run_primary_market_session_ops.py`)
shebang이 `#!/usr/bin/env bash`여도 3.2로 실행된다. 따라서 셸 스크립트는 전부 3.2에서
돌아가야 한다 — 이 테스트가 그 계약을 고정한다.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SYSTEM_BASH = "/bin/bash"

# bash 4+ 전용 구문 — 3.2에서 실행하면 죽거나 조용히 다르게 동작한다
BASH4_ONLY = [
    (re.compile(r"\bdeclare\s+-A\b"), "declare -A (연관배열)"),
    (re.compile(r"\bmapfile\b"), "mapfile"),
    (re.compile(r"\breadarray\b"), "readarray"),
    (re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\^\^"), "${v^^} (대문자 확장)"),
    (re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*,,"), "${v,,} (소문자 확장)"),
    (re.compile(r"\bwait\s+-n\b"), "wait -n"),
]


def shell_scripts() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.sh"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout.split()
    return [REPO / p for p in out]


SCRIPTS = shell_scripts()


def test_repo_has_shell_scripts():
    assert SCRIPTS, "git ls-files '*.sh' 가 비었다 — 탐색이 깨진 것"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_parses_under_system_bash(script: Path):
    """운영이 실제로 쓰는 셸(3.2)에서 구문이 통과해야 한다."""
    r = subprocess.run([SYSTEM_BASH, "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, f"{script.name}: bash -n 실패\n{r.stderr}"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_no_bash4_only_constructs(script: Path):
    text = script.read_text(encoding="utf-8")
    hits = [label for pattern, label in BASH4_ONLY if pattern.search(text)]
    assert not hits, f"{script.name}: bash 4 전용 구문 {hits} — /bin/bash 3.2에서 실행된다"


def _unguarded_empty_array_expansions(text: str) -> list[str]:
    """빈 배열로 선언된 변수를 가드 없이 확장하는 지점을 찾는다.

    안전한 형태: `${A[*]:-}` (기본값) / `${A[@]+"${A[@]}"}` (존재 가드) / `${#A[@]}` (길이).
    위험한 형태: `"${A[@]}"` / `${A[*]}` — 3.2 + set -u 에서 unbound variable.

    비어 있지 않은 재대입(`A=("x")`)이 함께 있으면 폴백이 있는 것으로 보고 면제한다
    (`run_daily_ops.sh`의 MARKETS: 빈 경우 `MARKETS=("KOSDAQ")`). 한계 — 그 재대입이
    조건부이고 모든 경로를 덮지 않으면 놓친다. 지배적 형태(`A=()`만 존재)는 잡는다.
    """
    decls = re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=\((\s*)\)\s*$", text, re.M)
    empty_decls = {name for name, _ in decls}
    for name in list(empty_decls):
        if re.search(r"^\s*" + name + r"=\(\s*[^)\s]", text, re.M):
            empty_decls.discard(name)   # 비어 있지 않은 재대입 = 폴백 있음
    if not empty_decls:
        return []
    stripped = text
    for name in empty_decls:
        # 가드된 형태를 먼저 제거해야 안쪽 확장이 오탐되지 않는다
        stripped = re.sub(r"\$\{" + name + r"\[@\]\+\"\$\{" + name + r"\[@\]\}\"\}", "", stripped)
        stripped = re.sub(r"\$\{" + name + r"\[[@*]\]:-[^}]*\}", "", stripped)
        stripped = re.sub(r"\$\{#" + name + r"\[[@*]\]\}", "", stripped)
    bad = []
    for name in empty_decls:
        for m in re.finditer(r"\$\{" + name + r"\[[@*]\]\}", stripped):
            line = stripped[:m.start()].count("\n") + 1
            bad.append(f"{name} @ 원문라인≈{line}")
    return bad


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_empty_arrays_are_guarded(script: Path):
    """swing-main-7x7h 재발 방지 — 이 검사가 그 버그를 정확히 잡는다."""
    bad = _unguarded_empty_array_expansions(script.read_text(encoding="utf-8"))
    assert not bad, (
        f"{script.name}: 빈 배열 무가드 확장 {bad} — bash 3.2 + set -u 에서 unbound variable.\n"
        f"수정: `${{A[*]}}` → `${{A[*]:-}}`, `\"${{A[@]}}\"` → `${{A[@]+\"${{A[@]}}\"}}`"
    )


def test_detector_catches_the_original_bug():
    """검출기 자체의 회귀 — 원래 버그 형태를 넣으면 반드시 잡혀야 한다."""
    buggy = 'set -euo pipefail\nDRIFT_ARGS=()\necho "x ${DRIFT_ARGS[*]}"\nfoo "${DRIFT_ARGS[@]}"\n'
    assert len(_unguarded_empty_array_expansions(buggy)) == 2
    fixed = ('set -euo pipefail\nDRIFT_ARGS=()\necho "x ${DRIFT_ARGS[*]:-}"\n'
             'foo ${DRIFT_ARGS[@]+"${DRIFT_ARGS[@]}"}\n')
    assert _unguarded_empty_array_expansions(fixed) == []


def test_system_bash_actually_has_the_flaw():
    """플랫폼 가정을 고정 — 이 전제가 깨지면(bash 4+로 이관) 위 검사의 근거가 바뀐다."""
    unguarded = subprocess.run(
        [SYSTEM_BASH, "-c", 'set -euo pipefail; A=(); echo "${A[*]}"'],
        capture_output=True, text=True)
    guarded = subprocess.run(
        [SYSTEM_BASH, "-c", 'set -euo pipefail; A=(); echo "${A[*]:-}"; set -- ${A[@]+"${A[@]}"}; echo "args=$#"'],
        capture_output=True, text=True)
    assert unguarded.returncode != 0 and "unbound variable" in unguarded.stderr
    assert guarded.returncode == 0 and "args=0" in guarded.stdout
