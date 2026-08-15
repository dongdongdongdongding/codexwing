"""B 레인 정지가 호출자 관례가 아니라 **엔진의 계약**인지 (trace-b-lane-f7.md).

정지 가드가 3곳 중 2곳에만 있었다:
  run_daily_ops.sh:287            → AG_B_ENGINE_SCAN 환경변수로 가드 (있음)
  web/backend/services.py:453     → 표시 경로, 마커 존재 시 [] 반환 (있음)
  web/backend/jobs.py:76 spec=='b' → **없음**
  b_engine/model_scan.py          → 마커를 읽는 코드가 **아예 없음**

그래서 `POST /api/ops/scan?target=all` 3건이 정지 이후 원장에 30건을 썼다.
`TARGETS["all"]`의 **첫 스텝이 b**라 B를 의도하지 않아도 발행된다.

가장 고약한 부분: **생성 경로는 정지를 무시해 쓰고, 표시 경로는 정지를 지켜 안 띄운다.**
버튼을 누른 사람은 자기가 방금 정지된 레인에 10건을 기록했다는 걸 화면에서 알 수 없다.
두 가드가 "부분적으로만" 맞은 것이 무가드보다 더 조용한 실패를 만들었다.

→ 판정을 엔진 안으로 내린다. **네 번째 호출자가 생겨도 안전해야 한다.**
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def b_engine_sandbox(tmp_path, monkeypatch):
    """b_engine 데이터 디렉터리를 tmp로 돌려 실제 원장을 건드리지 않는다."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    data = tmp_path / "b_data"
    data.mkdir()
    monkeypatch.setattr(E, "DATA", str(data))
    monkeypatch.setattr(model_scan, "PICKS", str(data / "b_picks_latest.json"))
    monkeypatch.setattr(model_scan, "SHADOW", str(data / "b_shadow.jsonl"))
    monkeypatch.setattr(model_scan, "SUSPEND_MARKER", str(data / "b_lane_suspended.json"))
    return data


def _suspend(data, **extra):
    payload = {"suspended": True, "since": "2026-08-03", "reason": "PKG-A §40", **extra}
    (data / "b_lane_suspended.json").write_text(json.dumps(payload), encoding="utf-8")


def _pick_payload():
    return {"scan_date": "2026-08-20", "top_n": 10,
            "picks": [{"code": f"{i:06d}", "pred_alpha_5d": 1.0, "close": 1000, "smart5": 0.5}
                      for i in range(10)]}


# --------------------------------------------------------------------------
# 1) 엔진 자체가 정지를 강제하는가
# --------------------------------------------------------------------------

def test_scan_writes_nothing_while_suspended(b_engine_sandbox, monkeypatch):
    """정지 중이면 엔진이 픽 파일도 원장도 만들지 않는다."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    _suspend(b_engine_sandbox)
    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())

    out = model_scan.scan()

    assert out is None
    assert not (b_engine_sandbox / "b_shadow.jsonl").exists()
    assert not (b_engine_sandbox / "b_picks_latest.json").exists()


def test_scan_writes_normally_when_not_suspended(b_engine_sandbox, monkeypatch):
    """양성 대조 — 정지가 아니면 평소대로 쓴다(과잉차단 방지)."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())
    monkeypatch.setattr(E, "META_PATH", str(b_engine_sandbox / "meta.json"))
    (b_engine_sandbox / "meta.json").write_text("{}", encoding="utf-8")

    out = model_scan.scan()

    assert out is not None
    assert (b_engine_sandbox / "b_shadow.jsonl").exists()
    assert len((b_engine_sandbox / "b_shadow.jsonl").read_text().strip().splitlines()) == 10


def test_unparseable_marker_is_treated_as_suspended(b_engine_sandbox, monkeypatch):
    """마커가 깨져 있으면 '정지 아님'이 아니라 **정지**로 읽는다 (fail-closed)."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    (b_engine_sandbox / "b_lane_suspended.json").write_text("{truncated", encoding="utf-8")
    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())

    assert model_scan.scan() is None
    assert not (b_engine_sandbox / "b_shadow.jsonl").exists()


def test_marker_can_explicitly_declare_not_suspended(b_engine_sandbox, monkeypatch):
    """suspended:false는 정지 해제로 읽는다 (마커를 남겨둔 채 재개하는 경우)."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    (b_engine_sandbox / "b_lane_suspended.json").write_text(
        json.dumps({"suspended": False}), encoding="utf-8")
    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())
    monkeypatch.setattr(E, "META_PATH", str(b_engine_sandbox / "meta.json"))
    (b_engine_sandbox / "meta.json").write_text("{}", encoding="utf-8")

    assert model_scan.scan() is not None


def test_settle_is_not_blocked_by_suspension(b_engine_sandbox):
    """정지 마커의 계약: '신규 픽 발행 중지. settle은 잔여 open 픽 정산까지 유지.'"""
    from b_engine import model_scan

    _suspend(b_engine_sandbox)

    assert model_scan.suspension() is not None
    assert not hasattr(model_scan.settle, "__wrapped_suspended__")


# --------------------------------------------------------------------------
# 2) 어느 호출자로도 안 써지는가 — 이번 사고의 그 호출자
# --------------------------------------------------------------------------

def test_web_scan_job_cannot_write_a_suspended_lane(b_engine_sandbox, monkeypatch):
    """jobs._run_step('b') — 30건을 쓴 바로 그 경로."""
    from b_engine import model_engine as E
    from web.backend import jobs

    _suspend(b_engine_sandbox)
    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())

    rec = jobs._run_step("B 시장중립", "b")

    assert not (b_engine_sandbox / "b_shadow.jsonl").exists()
    assert rec["ok"] is False
    assert rec.get("suspended") is True
    # 실행자가 화면에서 사유를 볼 수 있어야 한다 — 이번 사고의 핵심이 '몰랐다'는 것이다.
    assert "정지" in rec["note"]
    assert "2026-08-03" in rec["note"]


def test_a_fourth_unknown_caller_is_also_safe(b_engine_sandbox, monkeypatch):
    """관례를 모르는 새 호출자가 생겨도 안전해야 한다 — 그게 계약으로 내린 이유다."""
    from b_engine import model_engine as E
    from b_engine import model_scan

    _suspend(b_engine_sandbox)
    monkeypatch.setattr(E, "pick", lambda as_of=None: _pick_payload())

    def brand_new_caller_that_never_heard_of_the_marker():
        return model_scan.scan()

    assert brand_new_caller_that_never_heard_of_the_marker() is None
    assert not (b_engine_sandbox / "b_shadow.jsonl").exists()
