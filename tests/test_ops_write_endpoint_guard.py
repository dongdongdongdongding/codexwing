"""쓰기 엔드포인트 루프백 전용 + 실행 저널 요청자 기록 (trace-b-lane-f7.md §4).

정지된 레인에 30건을 쓴 요청 3건은 전부 **원격 IP에서 무인증으로** 들어왔다
(218.232.78.85 / 211.215.170.190, cloudflared 터널 경유).
`WEB_API_TOKEN`은 `.env.example`에만 있고 `scripts/run_web_backend.sh`가 export하지 않아
`require_token`이 전 요청을 통과시킨다 — 인증 주체 기록이 애초에 없었다.
저널(`scan_runs.jsonl`)에도 IP·UA가 없어 goblin이 나흘치 드리부터 재구성해야 했다.

터널 주의: cloudflared는 로컬(127.0.0.1)에서 백엔드로 붙는다. 그래서
**소켓 peer IP만 보면 터널 경유 원격 요청도 루프백으로 보일 수 있다.**
uvicorn이 proxy header를 신뢰하도록 떠 있으면 client.host가 실제 원격 IP로 치환되지만,
그 설정에 의존하면 안 된다. 그래서 두 조건을 **동시에** 요구한다:
  ① peer가 루프백이고
  ② 전달 헤더(X-Forwarded-For / X-Real-IP / CF-Connecting-IP / Forwarded / CF-Ray)가 없을 것
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_factory(monkeypatch):
    from web.backend import jobs, main

    started = []
    monkeypatch.setattr(jobs, "start", lambda target="all", requester=None: (
        started.append({"target": target, "requester": requester}) or {"ok": True}))

    def make(host="127.0.0.1", headers=None):
        c = TestClient(main.app, client=(host, 51234))
        c.headers.update(headers or {})
        return c

    return make, started


LOCAL = "127.0.0.1"
REMOTE = "218.232.78.85"


def test_remote_request_cannot_start_a_scan(client_factory):
    """이번 사고의 요청을 그대로 재현 — 거부돼야 한다."""
    make, started = client_factory

    r = make(host=REMOTE).post("/api/ops/scan?target=all")

    assert r.status_code == 403
    assert started == [], "거부됐는데 잡이 시작되면 안 된다"


def test_tunnelled_request_is_rejected_even_when_the_peer_looks_local(client_factory):
    """cloudflared는 127.0.0.1에서 붙는다 — peer IP만 믿으면 터널이 통째로 우회한다."""
    make, started = client_factory

    for header in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP", "CF-Ray", "Forwarded"):
        r = make(host=LOCAL, headers={header: "218.232.78.85"}).post("/api/ops/scan?target=all")
        assert r.status_code == 403, f"{header} 가 붙은 요청이 통과했다"
    assert started == []


def test_genuine_loopback_request_is_allowed(client_factory):
    """양성 대조 — 로컬 운영자는 계속 스캔할 수 있어야 한다."""
    make, started = client_factory

    r = make(host=LOCAL).post("/api/ops/scan?target=all")

    assert r.status_code == 200
    assert len(started) == 1


def test_read_endpoints_stay_open_to_remote(client_factory):
    """조회는 그대로 둔다 — 공개 대시보드가 죽으면 안 된다."""
    make, _ = client_factory

    r = make(host=REMOTE).get("/api/health")

    assert r.status_code == 200


def test_remote_writes_can_be_restored_by_explicit_opt_in(client_factory, monkeypatch):
    """이 리포의 롤백 관례(AG_DEGRADE_STREAM_EXCLUSION=0 형태)와 같은 탈출구. 기본은 차단."""
    make, started = client_factory
    monkeypatch.setenv("WEB_OPS_ALLOW_REMOTE", "1")

    r = make(host=REMOTE).post("/api/ops/scan?target=all")

    assert r.status_code == 200
    assert len(started) == 1


def test_block_response_explains_itself(client_factory):
    """차단 응답이 '왜'를 말해야 운영자가 헤매지 않는다."""
    make, _ = client_factory

    body = make(host=REMOTE).post("/api/ops/scan?target=all").json()

    assert "loopback" in json.dumps(body).lower()


# --------------------------------------------------------------------------
# 실행 저널 요청자 기록
# --------------------------------------------------------------------------

def test_scan_endpoint_passes_requester_identity_to_the_job(client_factory):
    make, started = client_factory

    make(host=LOCAL, headers={"User-Agent": "Mozilla/5.0 (iPhone; operator)"}).post("/api/ops/scan?target=b")

    req = started[0]["requester"]
    assert req["origin_ip"] == LOCAL
    assert "iPhone; operator" in req["user_agent"]


def test_journal_row_records_who_asked(tmp_path, monkeypatch):
    """scan_runs.jsonl에 origin IP·UA가 남아야 한다 — 이번 추적이 어려웠던 이유."""
    from web.backend import jobs

    monkeypatch.setattr(jobs, "REPO", str(tmp_path))
    requester = {"origin_ip": "218.232.78.85", "user_agent": "curl/8.4", "forwarded_for": "1.2.3.4"}

    jobs._write_journal("all", [{"label": "B 시장중립", "ok": False, "note": "정지됨"}], requester=requester)

    line = (tmp_path / "runtime_state" / "local_short_term" / "scan_runs.jsonl").read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["requester"]["origin_ip"] == "218.232.78.85"
    assert row["requester"]["user_agent"] == "curl/8.4"
    assert row["requester"]["forwarded_for"] == "1.2.3.4"
    assert row["scan_id"].startswith("MANUAL-")


def test_journal_without_requester_still_writes(tmp_path, monkeypatch):
    """저널 기록이 요청자 정보 부재로 깨지면 안 된다 (CLI/내부 호출)."""
    from web.backend import jobs

    monkeypatch.setattr(jobs, "REPO", str(tmp_path))

    jobs._write_journal("b", [{"label": "B", "ok": True, "note": "10픽"}])

    row = json.loads((tmp_path / "runtime_state" / "local_short_term" / "scan_runs.jsonl").read_text(encoding="utf-8").strip())
    assert row["requester"] is None
