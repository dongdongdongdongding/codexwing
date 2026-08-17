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


def guard_block(step: str = STEP, flag: str = FLAG) -> str:
    """스텝을 감싸는 `if ... fi` 블록을 run_daily_ops.sh 에서 원문 그대로 추출한다.

    가드는 들여쓰기될 수 있으므로(중첩) strip 후 판정한다.
    """
    lines = OPS.read_text(encoding="utf-8").splitlines()
    step_idx = next((i for i, l in enumerate(lines) if f'[STEP] {step}' in l), None)
    assert step_idx is not None, f"{step} 스텝을 찾지 못했다 — 추출이 깨진 것"
    start = next((i for i in range(step_idx, -1, -1)
                  if lines[i].strip().startswith("if [[") and flag in lines[i]), None)
    assert start is not None, f"{flag} 가드 if 문을 찾지 못했다 — 추출이 깨진 것"
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


# ---------------------------------------------------------------------------
# NASDAQ 일봉 패널 갱신 스텝 배선 (audit-ledger-rewrite-pattern.md §2.2)
# ---------------------------------------------------------------------------
# 원장이 승격 이래 0행이었던 직접 원인은 원천 패널이 2026-06-29 동결이고 재생성 스텝이
# 아예 없었던 것이다. 생산자 계약은 impl-nasdaq-daily-panel-seaslug.md.

PANEL_FLAG = "AG_US_DAILY_PANEL_REFRESH_ENABLE"
PANEL_STEP = "backfill_us_daily_features"
PANEL_CONSUMER = "report_nasdaq_daily_edge_shadow"

# 생산자를 대신하는 스텁. 블록이 python3 를 호출하므로 셸 함수로 가로챈다.
PANEL_HARNESS = """#!/bin/bash
set -uo pipefail
run_optional() { echo "[RAN] $1"; }
python3() { echo '%s'; return %d; }
%s
"""
PANEL_JSON_OK = '{"status": "already_current", "panel_max_date": "2026-08-14", "age_days": 2}'
PANEL_JSON_FAIL = '{"status": "error", "reason": "network"}'


def run_panel_block(tmp_path: Path, *, stdout=PANEL_JSON_OK, rc=0, **flags) -> str:
    script = tmp_path / "panel.sh"
    script.write_text(PANEL_HARNESS % (stdout, rc, guard_block(PANEL_STEP, PANEL_FLAG)),
                      encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AG_US_DAILY")}
    env.update({k: str(v) for k, v in flags.items()})
    r = subprocess.run([SYSTEM_BASH, str(script)], capture_output=True, text=True,
                       timeout=60, env=env, cwd=str(REPO))
    return r.stdout + r.stderr


# --- (a) 가드 선언 = 실제 실행 -------------------------------------------------

def test_panel_step_runs_by_default(tmp_path):
    out = run_panel_block(tmp_path)
    assert f"[STEP] {PANEL_STEP}" in out, out


def test_panel_flag_zero_actually_skips(tmp_path):
    out = run_panel_block(tmp_path, **{PANEL_FLAG: "0"})
    assert f"[SKIP] {PANEL_STEP}" in out, out
    assert f"[STEP] {PANEL_STEP}" not in out, out
    assert PANEL_FLAG in out, "SKIP 줄이 어떤 플래그 때문인지 밝히지 않는다"


def test_panel_guard_is_single_name():
    head = guard_block(PANEL_STEP, PANEL_FLAG).splitlines()[0]
    assert PANEL_FLAG in head and ":-${" not in head, head


# --- (b) 소비자가 새 패널을 집는가 ---------------------------------------------

def test_consumer_picks_the_newest_non_latest_panel(tmp_path, monkeypatch):
    """배선의 성패는 소비자가 갱신분을 실제로 여는지에 달렸다.

    소비자는 `_latest_` 가 든 이름을 **명시적으로 제외**한다. 생산자가 그 이름으로 쓰면
    "스텝은 already_current 인데 소비자는 동결 패널을 본다" — seaslug 초기 구현의 결함이
    정확히 이것이었고 내가 배선 전 경고한 함정이다. 실제 소비자 함수로 고정한다.
    """
    consumer = pytest.importorskip("multi_agent.tools.report_nasdaq_daily_edge_shadow")
    monkeypatch.setattr(consumer, "DEFAULT_PANEL_ROOT", tmp_path)
    old = tmp_path / "daily_features_20180101_20260630_20260629_113805.parquet"
    new = tmp_path / "daily_features_20180101_20260814_20260816_010101.parquet"
    trap = tmp_path / "daily_features_latest_20260816_010101.parquet"
    for f in (old, new, trap):
        f.write_bytes(b"x")
    os.utime(old, (1, 1))
    os.utime(new, (100, 100))
    os.utime(trap, (999, 999))          # 가장 최신이지만 소비자는 봐선 안 된다

    picked = consumer.resolve_panel_path("latest")

    assert picked == new, f"소비자가 갱신 패널을 집지 않았다: {picked}"
    assert "_latest_" not in picked.name


def test_producer_output_name_must_not_contain_latest():
    """생산자 산출물 이름 규칙 — 계약의 핵심 조건이라 배선 쪽에서도 고정한다."""
    consumer = pytest.importorskip("multi_agent.tools.report_nasdaq_daily_edge_shadow")
    src = Path(consumer.__file__).read_text(encoding="utf-8")
    assert '"_latest_" not in' in src, "소비자의 _latest_ 제외 규칙이 사라졌다 — 계약 전제가 바뀐다"


# --- (c) stdout status 가 로그에 남는가 ----------------------------------------

def test_panel_status_json_is_logged_on_success(tmp_path):
    """run_optional 은 실패를 [WARN] 한 줄로 삼킨다. 이번 사고들의 뿌리가 그 삼킴이라
    생산자가 stdout 에 내는 status 를 라벨 붙여 남긴다(생산자 요청 사항)."""
    out = run_panel_block(tmp_path)
    assert "already_current" in out, f"stdout status 가 로그에 없다:\n{out}"
    assert "[DATA]" in out, "status 줄에 라벨이 없어 grep 이 어렵다"


def test_panel_failure_is_visible_and_does_not_kill_dailyops(tmp_path):
    out = run_panel_block(tmp_path, stdout=PANEL_JSON_FAIL, rc=1)
    assert "[WARN]" in out, f"실패가 로그에 드러나지 않는다:\n{out}"
    assert "rc=1" in out, "종료코드가 로그에 없다"
    assert PANEL_JSON_FAIL.split(",")[0][2:] in out or "error" in out, "실패 status 가 유실됐다"


def test_panel_failure_does_not_abort_the_block(tmp_path):
    """run_daily_ops.sh 는 set -e 다 — 실패를 잘못 다루면 dailyops 전체가 죽는다."""
    out = run_panel_block(tmp_path, stdout=PANEL_JSON_FAIL, rc=1)
    assert "[WARN]" in out and "[STEP]" in out


# --- 순서 — 갱신이 소비자보다 앞이어야 그날 갱신분이 반영된다 ---------------------

def test_panel_refresh_runs_before_its_consumer():
    lines = OPS.read_text(encoding="utf-8").splitlines()
    refresh = next(i for i, l in enumerate(lines) if f"[STEP] {PANEL_STEP}" in l)
    consumer = next(i for i, l in enumerate(lines) if f"[STEP] {PANEL_CONSUMER}" in l)
    assert refresh < consumer, (
        f"갱신({refresh})이 소비자({consumer})보다 뒤에 있다 — 그날 갱신분이 반영되지 않는다")


def test_panel_step_is_inside_the_nasdaq_swing_lane_guard():
    """레인이 꺼져 있으면 패널도 갱신하지 않는다 — 선례(update_us_hourly)와 같은 구조."""
    lines = OPS.read_text(encoding="utf-8").splitlines()
    refresh = next(i for i, l in enumerate(lines) if f"[STEP] {PANEL_STEP}" in l)
    lane = next(i for i, l in enumerate(lines)
                if l.startswith("if [[") and "AG_NASDAQ_SWING_MODEL_ENABLE" in l)
    assert lane < refresh, "패널 갱신이 레인 가드 밖에 있다"


# ---------------------------------------------------------------------------
# 미채점 행 경보 배선 (F6)
# ---------------------------------------------------------------------------

STALE_FLAG = "AG_UNRESOLVED_STALENESS_ALERT"
STALE_STEP = "report_unresolved_outcome_staleness"


def run_stale_block(tmp_path: Path, *, stdout='{"total_stale": 0}', rc=0, **flags) -> str:
    script = tmp_path / "stale.sh"
    script.write_text(PANEL_HARNESS % (stdout, rc, guard_block(STALE_STEP, STALE_FLAG)),
                      encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AG_UNRESOLVED")}
    env.update({k: str(v) for k, v in flags.items()})
    r = subprocess.run([SYSTEM_BASH, str(script)], capture_output=True, text=True,
                       timeout=60, env=env, cwd=str(REPO))
    return r.stdout + r.stderr


def test_staleness_alert_runs_by_default(tmp_path):
    assert f"[STEP] {STALE_STEP}" in run_stale_block(tmp_path)


def test_staleness_alert_can_be_switched_off(tmp_path):
    out = run_stale_block(tmp_path, **{STALE_FLAG: "0"})
    assert f"[SKIP] {STALE_STEP}" in out and f"[STEP] {STALE_STEP}" not in out
    assert STALE_FLAG in out


def test_staleness_breach_is_loud_and_labelled(tmp_path):
    """임계 초과가 조용히 지나가면 이 스텝을 만든 이유가 사라진다."""
    out = run_stale_block(tmp_path, stdout='{"total_stale": 3}', rc=1)
    assert "[WARN]" in out and "rc=1" in out
    assert "total_stale" in out, "status 가 로그에 안 남았다"
    assert "[DATA]" in out


def test_staleness_breach_does_not_abort_dailyops(tmp_path):
    out = run_stale_block(tmp_path, stdout='{"total_stale": 3}', rc=1)
    assert "[STEP]" in out and "[WARN]" in out


def test_staleness_guard_is_single_name():
    head = guard_block(STALE_STEP, STALE_FLAG).splitlines()[0]
    assert STALE_FLAG in head and ":-${" not in head, head


# ---------------------------------------------------------------------------
# sentinel 판정기 배선 (OD-38) — 새 launchd 잡 없이 dailyops 스텝으로
# ---------------------------------------------------------------------------

SENTINEL_FLAG = "AG_SENTINEL_CHECK"
SENTINEL_STEP = "report_sentinel_expectations"


def run_sentinel_block(tmp_path: Path, *, stdout='{"escalations": 0}', rc=0, **flags) -> str:
    script = tmp_path / "sentinel.sh"
    script.write_text(PANEL_HARNESS % (stdout, rc, guard_block(SENTINEL_STEP, SENTINEL_FLAG)),
                      encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AG_SENTINEL")}
    env.update({k: str(v) for k, v in flags.items()})
    r = subprocess.run([SYSTEM_BASH, str(script)], capture_output=True, text=True,
                       timeout=60, env=env, cwd=str(REPO))
    return r.stdout + r.stderr


def test_sentinel_declared_state_matches_execution(tmp_path):
    """선언 = 실제 실행. c9cf7db 가 100회 동안 어긋났던 그 계약이다."""
    assert f"[STEP] {SENTINEL_STEP}" in run_sentinel_block(tmp_path)
    off = run_sentinel_block(tmp_path, **{SENTINEL_FLAG: "0"})
    assert f"[SKIP] {SENTINEL_STEP}" in off and f"[STEP] {SENTINEL_STEP}" not in off
    assert SENTINEL_FLAG in off


def test_sentinel_guard_is_single_name():
    head = guard_block(SENTINEL_STEP, SENTINEL_FLAG).splitlines()[0]
    assert SENTINEL_FLAG in head and ":-${" not in head, head


def test_sentinel_escalation_is_loud(tmp_path):
    out = run_sentinel_block(tmp_path, stdout='{"escalations": 3}', rc=1)
    assert "[WARN]" in out and "rc=1" in out and "[DATA]" in out
    assert "escalations" in out, "status 가 로그에 안 남았다"
    assert "sentinel_escalations.md" in out, "어디를 봐야 하는지가 없다"


def test_sentinel_failure_does_not_abort_dailyops(tmp_path):
    out = run_sentinel_block(tmp_path, stdout='{"escalations": 3}', rc=1)
    assert "[STEP]" in out and "[WARN]" in out


def test_no_new_launchd_job_was_added():
    """OD-38: 새 launchd 잡을 만들지 않는다 — dailyops 스텝으로 붙인다."""
    plists = list((REPO / "scripts" / "launchd").glob("*.plist"))
    assert not any("sentinel" in p.name.lower() for p in plists), \
        f"sentinel 용 launchd 잡이 생겼다: {[p.name for p in plists]}"


def test_sentinel_runs_before_the_two_hour_backfill():
    """OD-41: 맨 뒤에 두면 매 실행 4.5시간 뒤에야 판정이 나온다.

    판정기는 원장·마커·산출물만 읽어 그날 백필 결과에 의존하지 않는다.
    """
    lines = OPS.read_text(encoding="utf-8").splitlines()
    sentinel = next(i for i, l in enumerate(lines) if f"[STEP] {SENTINEL_STEP}" in l)
    backfill = next(i for i, l in enumerate(lines) if "[STEP] intraday_backfill" in l)
    assert sentinel < backfill, (
        f"판정기({sentinel})가 2시간 백필({backfill}) 뒤에 있다 — 기한·발화율 판정이 그만큼 늦는다")


def test_od43_intraday_producers_run_before_the_backfill():
    """OD-43: 웹 /api/picks 가 이 두 레인의 dailyops 산출을 유일한 소스로 읽는다.

    백필 뒤에 두면 장중 픽이 14:12 에 갱신된다 — 마감 한 시간 전이다.
    실측상 둘 다 그날 백필 산출을 읽지 않으므로 앞으로 옮겼다.
    """
    lines = OPS.read_text(encoding="utf-8").splitlines()
    pos = {}
    for i, l in enumerate(lines):
        for step in ("intraday_backfill", "report_kosdaq_intraday_vwap_guard",
                     "report_kr_swing_candidate", "report_kospi_intraday_swing",
                     "build_intraday_3d_panel"):
            if f"[STEP] {step}" in l and step not in pos:
                pos[step] = i
    assert pos["report_kosdaq_intraday_vwap_guard"] < pos["intraday_backfill"]
    assert pos["report_kr_swing_candidate"] < pos["intraday_backfill"]
    # 41 은 패널을 읽으므로 옮기지 않는다 — 패널 빌더 뒤에 있어야 한다
    assert pos["report_kospi_intraday_swing"] > pos["build_intraday_3d_panel"], \
        "코스피는 intraday_3d_panel 을 읽는다 — 패널 빌더보다 앞서면 안 된다"


def test_moved_producers_still_run_after_px_long_refresh():
    """옮긴 두 생산자는 px_long 만 읽는다 — 그 갱신보다는 뒤여야 한다."""
    lines = OPS.read_text(encoding="utf-8").splitlines()
    px = next(i for i, l in enumerate(lines) if "[STEP] px_long_refresh" in l)
    for step in ("report_kosdaq_intraday_vwap_guard", "report_kr_swing_candidate"):
        s = next(i for i, l in enumerate(lines) if f"[STEP] {step}" in l)
        assert s > px, f"{step} 이 px_long_refresh 보다 앞에 있다 — 낡은 가격을 읽는다"
