"""터널 래퍼 회귀 (swing-main-ap4o).

검증보고 orca/reports/verify-tunnel.md 가 잡아낸 실패들을 샌드박스에서 **실제로 재현**한다.
전부 `/bin/bash`(3.2)로, 진짜 git 리포(bare origin + clone)와 스텁 cloudflared 로 돌린다.

핵심은 E다: 이 래퍼는 dailyops·kr-daily-auto-scan·learning 이 함께 쓰는 공용 운영 리포에서
무인으로 돈다. 예전 `git pull --rebase --autostash` 는 상시 갱신되는 runtime_state/*.jsonl 과
충돌해 UU 를 방치하고 충돌 마커를 JSONL 에 물리적으로 기록했다. 여기서는 **그 충돌 상황을
인공적으로 만들어 놓고** 래퍼를 돌려 리포가 오염되지 않는지 확인한다.

`test_legacy_publish_path_would_have_corrupted_the_repo` 는 검출기 자체의 회귀다 —
옛 발행 시퀀스를 같은 샌드박스에 돌려서 정말로 충돌 마커가 생기는지 확인한다. 이게 실패하면
시나리오가 무뎌진 것이므로 다른 테스트의 통과가 의미를 잃는다.
"""
from __future__ import annotations

import glob
import os
import re
import signal
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "run_cloudflared_tunnel.sh"
SYSTEM_BASH = "/bin/bash"
TUNNEL_JSON = "web/frontend/public/tunnel.json"
STUB_URL = "https://anglerfish-sandbox-tunnel.trycloudflare.com"
OLD_URL = "https://old-dead-address.trycloudflare.com"

# 스텁 cloudflared: URL 을 즉시 뱉고, 래퍼의 즉사감지(2초)보다 오래 살아 있다가 끝난다.
STUB_CLOUDFLARED = """#!/bin/bash
echo "$$" > "{pidfile}"
echo "INF |  {url}  |"
sleep {lifetime}
"""

# 옛 발행 시퀀스 (수정 전 run_cloudflared_tunnel.sh:31-37 그대로).
LEGACY_PUBLISH = """#!/bin/bash
set -uo pipefail
REPO="$1"; URL="$2"
printf '{{"api": "%s", "updated": "%s"}}\\n' "$URL" "$(date -u +%FT%TZ)" > "$REPO/{tunnel_json}"
cd "$REPO"
git pull --rebase --autostash -q origin "$(git rev-parse --abbrev-ref HEAD)" || true
git add {tunnel_json}
git commit -q -m "chore(tunnel): rotate api tunnel url [auto]" || true
git push -q || echo "[tunnel] push 실패 — 수동 확인 필요"
echo "[tunnel] tunnel.json 갱신·푸시 완료 → Vercel 재배포 대기"
"""


def _git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, check=check)


class Sandbox:
    """bare origin + 작업 클론 + 스텁 cloudflared. 실 운영 리포는 절대 건드리지 않는다."""

    def __init__(self, root: Path):
        self.root = root
        self.origin = root / "origin.git"
        self.work = root / "work"
        self.bin = root / "bin"
        self.pidfile = root / "cfpid"

        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)],
                       check=True, capture_output=True)
        for k, v in (("user.email", "tunnel@test"), ("user.name", "tunnel-test"),
                     ("commit.gpgsign", "false")):
            _git(self.work, "config", k, v)

        (self.work / "web/frontend/public").mkdir(parents=True)
        (self.work / "runtime_state").mkdir(parents=True)
        (self.work / TUNNEL_JSON).write_text('{"api": "%s"}\n' % OLD_URL)
        (self.work / "runtime_state/state.jsonl").write_text('{"seq": 1}\n')
        _git(self.work, "add", "-A")
        _git(self.work, "commit", "-q", "-m", "base")
        _git(self.work, "push", "-q", "origin", "HEAD:refs/heads/main")
        _git(self.work, "branch", "-q", "-M", "main")
        _git(self.work, "branch", "--set-upstream-to=origin/main", "main", check=False)

        self.bin.mkdir()
        self.stub = self.bin / "cloudflared"

    def install_stub(self, url: str = STUB_URL, lifetime: int = 4) -> None:
        self.stub.write_text(STUB_CLOUDFLARED.format(
            pidfile=self.pidfile, url=url, lifetime=lifetime))
        self.stub.chmod(0o755)

    def make_upstream_move(self, content: str = "UPSTREAM-CHANGE\n") -> None:
        """다른 잡이 origin 에 runtime_state 를 갱신해 둔 상태를 만든다."""
        other = self.root / "other"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(other)],
                       check=True, capture_output=True)
        _git(other, "config", "user.email", "other@test")
        _git(other, "config", "user.name", "other")
        (other / "runtime_state/state.jsonl").write_text(content)
        _git(other, "commit", "-aqm", "upstream job wrote state")
        _git(other, "push", "-q", "origin", "main")

    def make_local_dirty(self, content: str = "LOCAL-DIRTY-CONFLICTING\n") -> None:
        """실 운영 리포의 상태: launchd 잡들이 상시 갱신하는 dirty 파일."""
        (self.work / "runtime_state/state.jsonl").write_text(content)

    def run_wrapper(self, repo_override=None, env_extra=None, timeout=60):
        env = dict(os.environ)
        env["TUNNEL_REPO"] = str(self.work if repo_override is None else repo_override)
        env["CLOUDFLARED_BIN"] = str(self.stub)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env.update(env_extra or {})
        return subprocess.run([SYSTEM_BASH, str(SCRIPT)], capture_output=True,
                              text=True, timeout=timeout, env=env, cwd=str(self.root))

    # --- 관측 ---------------------------------------------------------------
    def origin_api(self) -> str:
        r = _git(self.origin, "show", "main:" + TUNNEL_JSON, check=False)
        return r.stdout if r.returncode == 0 else ""

    def status(self) -> str:
        return _git(self.work, "status", "--porcelain").stdout

    def unmerged(self) -> str:
        return _git(self.work, "ls-files", "-u").stdout

    def stashes(self) -> str:
        return _git(self.work, "stash", "list").stdout

    def head(self) -> str:
        return _git(self.work, "rev-parse", "HEAD").stdout.strip()

    def state_text(self) -> str:
        return (self.work / "runtime_state/state.jsonl").read_text()


@pytest.fixture
def sb(tmp_path):
    box = Sandbox(tmp_path)
    box.install_stub()
    yield box
    pf = box.pidfile
    if pf.exists():                      # 스텁 잔재 정리 (테스트 격리)
        try:
            os.kill(int(pf.read_text().strip()), signal.SIGKILL)
        except (ProcessLookupError, ValueError):
            pass


# ---------------------------------------------------------------------------
# E — 공용 운영 리포 오염 (P0)
# ---------------------------------------------------------------------------

def test_legacy_publish_path_would_have_corrupted_the_repo(sb):
    """검출기 회귀: 옛 발행 시퀀스는 이 시나리오에서 반드시 리포를 오염시켜야 한다.

    이게 통과해야 아래 test_dirty_repo_with_upstream_conflict_stays_clean 의 통과가
    '시나리오가 무뎌서'가 아니라 '수정이 실제로 막아서'임이 보장된다.
    """
    sb.make_upstream_move()
    sb.make_local_dirty()
    legacy = sb.root / "legacy_publish.sh"
    legacy.write_text(LEGACY_PUBLISH.format(tunnel_json=TUNNEL_JSON))
    legacy.chmod(0o755)

    r = subprocess.run([SYSTEM_BASH, str(legacy), str(sb.work), STUB_URL],
                       capture_output=True, text=True, timeout=60)

    assert r.returncode == 0, "옛 경로는 실패해도 exit 0 이었다 — 전제가 바뀌었다"
    assert "갱신·푸시 완료" in r.stdout, "옛 경로는 실패해도 성공 줄을 찍었다"
    assert "<<<<<<<" in sb.state_text(), (
        "옛 경로가 runtime_state 에 충돌 마커를 남기지 않았다 — 시나리오가 무뎌졌다"
    )
    assert sb.unmerged(), "옛 경로가 UU 를 남기지 않았다 — 시나리오가 무뎌졌다"


def test_dirty_repo_with_upstream_conflict_stays_clean(sb):
    """E: 같은 충돌 상황에서 래퍼는 리포를 오염시키지 않고 발행에 성공해야 한다."""
    sb.make_upstream_move()
    sb.make_local_dirty()
    head_before = sb.head()

    r = sb.run_wrapper()

    assert r.returncode == 0, f"래퍼 실패\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    # 1. 공개 사이트가 새 주소를 받는다
    assert STUB_URL in sb.origin_api(), f"origin 미갱신: {sb.origin_api()!r}"
    # 2. 공용 리포에 충돌 마커·UU·stash 가 남지 않는다
    assert "<<<<<<<" not in sb.state_text()
    assert sb.state_text() == "LOCAL-DIRTY-CONFLICTING\n", "dirty 파일이 변조됐다"
    assert sb.unmerged() == "", f"미해결 충돌 발생:\n{sb.unmerged()}"
    assert sb.stashes() == "", f"stash 잔재:\n{sb.stashes()}"
    # 3. 워킹트리·HEAD 를 건드리지 않는다
    assert sb.head() == head_before, "HEAD 가 움직였다 — 워킹트리 비침투 계약 위반"
    assert sb.status() == " M runtime_state/state.jsonl\n", (
        f"워킹트리 상태가 예상 밖:\n{sb.status()}"
    )


def test_publish_survives_repo_with_preexisting_unmerged_files(sb):
    """이미 오염된 리포(UU 잔존)에서도 발행은 되고, 경고가 크게 찍혀야 한다."""
    sb.make_upstream_move()
    sb.make_local_dirty()
    _git(sb.work, "pull", "--rebase", "--autostash", "-q", "origin", "main", check=False)
    assert sb.unmerged(), "전제 실패: UU 상태를 못 만들었다"

    r = sb.run_wrapper()

    assert r.returncode == 0, f"기존 UU 때문에 발행이 막혔다\n{r.stderr}"
    assert STUB_URL in sb.origin_api()
    assert "미해결 충돌" in r.stderr, "기존 오염을 조용히 지나쳤다"


# ---------------------------------------------------------------------------
# B — push 실패의 거짓 성공
# ---------------------------------------------------------------------------

def test_push_failure_is_fatal_and_never_prints_success(sb):
    _git(sb.work, "remote", "set-url", "origin", str(sb.root / "does-not-exist.git"))

    r = sb.run_wrapper()

    assert r.returncode != 0, "push 실패인데 exit 0 (launchd 가 정상으로 인식)"
    assert "발행 완료" not in r.stdout, f"거짓 성공 줄 출력:\n{r.stdout}"
    assert "갱신·푸시 완료" not in r.stdout
    assert "발행 실패" in r.stderr, f"실패가 크게 보고되지 않았다:\n{r.stderr}"


def test_unchanged_url_does_not_create_a_commit(sb):
    """주소 불변이면 발행을 생략한다 — 매 재시작 빈 커밋 금지."""
    sb.install_stub(url=OLD_URL)
    before = _git(sb.origin, "rev-parse", "main").stdout.strip()

    r = sb.run_wrapper()

    assert r.returncode == 0, r.stderr
    assert "주소 불변" in r.stdout
    assert _git(sb.origin, "rev-parse", "main").stdout.strip() == before


# ---------------------------------------------------------------------------
# G — REPO 하드코딩 / cd 미가드
# ---------------------------------------------------------------------------

def test_missing_repo_is_fatal_before_starting_the_tunnel(sb):
    r = sb.run_wrapper(repo_override=sb.root / "nope")

    assert r.returncode != 0, "리포가 없는데 exit 0"
    assert "발행 완료" not in r.stdout and "갱신·푸시 완료" not in r.stdout
    assert "실패" in r.stderr
    assert not sb.pidfile.exists(), "리포 검증 전에 cloudflared 를 띄웠다"


def test_wrong_repo_is_rejected(sb):
    """git 리포이긴 하나 발행 리포가 아니면 커밋을 시도하지 않는다."""
    other = sb.root / "unrelated"
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True)

    r = sb.run_wrapper(repo_override=other)

    assert r.returncode != 0
    assert "발행 리포가 아니다" in r.stderr
    assert not sb.pidfile.exists()


def test_repo_is_derived_from_script_location_when_unset(sb):
    """TUNNEL_REPO 미설정이면 스크립트 위치의 git 최상위를 쓴다(하드코딩 제거)."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "/Users/dongdong/Projects" not in text, "리포 경로가 다시 하드코딩됐다"
    probe = subprocess.run(
        [SYSTEM_BASH, "-c",
         'cd -- "$(dirname -- "$1")" && git rev-parse --show-toplevel',
         "_", str(SCRIPT)],
        capture_output=True, text=True)
    assert probe.returncode == 0
    assert Path(probe.stdout.strip()).resolve() == REPO.resolve()


# ---------------------------------------------------------------------------
# C — /tmp 로그 누적 (이번 수리가 만든 신규 회귀)
# ---------------------------------------------------------------------------

def _tmp_logs() -> set:
    return set(glob.glob("/tmp/cloudflared.*")) | set(glob.glob("/tmp/tunnelidx.*"))


def test_tmp_log_is_removed_on_success(sb):
    before = _tmp_logs()
    r = sb.run_wrapper()
    assert r.returncode == 0, r.stderr
    assert _tmp_logs() - before == set(), "성공 경로가 /tmp 잔재를 남겼다"


def test_tmp_log_is_removed_on_failure(sb):
    before = _tmp_logs()
    _git(sb.work, "remote", "set-url", "origin", str(sb.root / "does-not-exist.git"))
    r = sb.run_wrapper()
    assert r.returncode != 0
    assert _tmp_logs() - before == set(), "실패 경로가 /tmp 잔재를 남겼다"


# ---------------------------------------------------------------------------
# D — SIGTERM 시 cloudflared 고아
# ---------------------------------------------------------------------------

def test_sigterm_does_not_orphan_cloudflared(sb):
    sb.install_stub(lifetime=60)
    env = dict(os.environ)
    env.update({"TUNNEL_REPO": str(sb.work), "CLOUDFLARED_BIN": str(sb.stub)})
    proc = subprocess.Popen([SYSTEM_BASH, str(SCRIPT)], env=env, cwd=str(sb.root),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not sb.pidfile.exists():
            time.sleep(0.1)
        assert sb.pidfile.exists(), "스텁 cloudflared 가 뜨지 않았다"
        child = int(sb.pidfile.read_text().strip())
        os.kill(child, 0)                       # 살아 있음 확인

        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=20)

        for _ in range(100):                    # 자식 종료 대기
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            pytest.fail(f"SIGTERM 후 cloudflared({child}) 가 고아로 남았다")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# 구조 잠금 — 워킹트리 비침투 계약
# ---------------------------------------------------------------------------

WORKTREE_MUTATING = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+)?(?:pull|stash|checkout|reset|merge|rebase|add|restore)\b")


def test_script_never_mutates_the_shared_worktree():
    """E 재발 잠금: 공용 리포의 워킹트리·인덱스를 바꾸는 porcelain 을 쓰지 않는다.

    (`git commit-tree` 는 임시 인덱스 전용이라 예외 — `git commit` 과 다르다.)
    """
    body = "\n".join(l for l in SCRIPT.read_text(encoding="utf-8").splitlines()
                     if not l.lstrip().startswith("#"))
    hits = WORKTREE_MUTATING.findall(body)
    assert not hits, f"워킹트리 변경 명령 사용: {hits}"
    assert "--autostash" not in body, "autostash 재도입 — E 가 그대로 돌아온다"
    assert not re.search(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b(?!-tree)", body), \
        "git commit (worktree 커밋) 재도입"


def test_no_predictable_tmp_fallback():
    """F: mktemp 실패 시 예측 가능한 고정 경로로 폴백하지 않는다(심링크 추종)."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "/tmp/cloudflared.$$" not in body
