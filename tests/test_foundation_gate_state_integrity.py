"""학습 상태파일 손상이 게이트에 잡히는가 (d1538e9 후속).

d1538e9가 `state_load_error`로 손상을 **리포트에** 표면화했지만
`report_daily_model_foundation_gate.py`가 그 필드를 읽지 않아 **게이트로는 안 잡혔다**.
배터리 없는 화재감지기 상태였다.

핵심은 단순 경보 추가가 아니다. 손상되면 전 기준선이 0으로 리셋되고
`new_resolved_since_last_cycle`이 "새 작업"이 아니라 **창 전체**(실측 4156)가 되어
`NEW_OUTCOMES` 체크가 `4156 >= 1`로 **초록**이 된다.
즉 상태파일이 날아간 사고가 "건강한 대량 신규 수확"으로 보인다.
그래서 손상 시에는 그 숫자에 기댄 판정이 **초록을 못 내게** 막아야 한다.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from multi_agent.tools.report_daily_model_foundation_gate import build_report

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _learning_reports(tmp_path, *, nightly_extra=None, weekly_extra=None):
    _write_json(
        tmp_path / "learning" / "learning_cycle_nightly.json",
        {"generated_at": "2026-08-15T02:00:00+00:00", "action": "dataset_refresh",
         "new_resolved_since_last_cycle": 4156, "total_resolved": 4156,
         "state_load_error": None, **(nightly_extra or {})},
    )
    _write_json(
        tmp_path / "learning" / "learning_cycle_weekly.json",
        {"generated_at": "2026-08-14T00:00:00+00:00", "action": "dataset_refresh",
         "new_resolved_since_last_cycle": 4156, "total_resolved": 4156,
         "state_load_error": None, **(weekly_extra or {})},
    )


def _checks(tmp_path):
    report = build_report(report_dir=tmp_path, now=NOW)
    return {c["code"]: c for c in report["checks"]}


CORRUPT = "training_state.json: JSONDecodeError: Unterminated string starting at: line 1 column 63000"


def test_healthy_state_passes_integrity_check(tmp_path):
    """양성 대조 — 정상일 때 새 체크가 잡음을 내면 안 된다."""
    _learning_reports(tmp_path)

    checks = _checks(tmp_path)

    assert checks["NIGHTLY_LEARNING_STATE_INTEGRITY"]["passed"] is True
    assert checks["WEEKLY_LEARNING_STATE_INTEGRITY"]["passed"] is True


def test_corrupt_state_file_fails_the_gate(tmp_path):
    """손상이 게이트에 잡혀야 한다 — 이게 없던 배선이다."""
    _learning_reports(tmp_path, nightly_extra={"state_load_error": CORRUPT})

    check = _checks(tmp_path)["NIGHTLY_LEARNING_STATE_INTEGRITY"]

    assert check["passed"] is False
    assert "JSONDecodeError" in check["detail"]
    assert check["severity"] == "hard_daily"


def test_corruption_stops_new_outcomes_from_reporting_a_false_green(tmp_path):
    """가장 중요한 단정.

    손상 시 new_resolved=4156은 '새 작업'이 아니라 리셋된 기준선 위의 창 전체다.
    이 숫자로 NEW_OUTCOMES가 통과하면 사고가 풍년으로 보인다 — 그걸 막는다.
    """
    _learning_reports(tmp_path, nightly_extra={"state_load_error": CORRUPT})

    checks = _checks(tmp_path)

    assert checks["NIGHTLY_LEARNING_NEW_OUTCOMES"]["passed"] is False
    assert "신뢰할 수 없" in checks["NIGHTLY_LEARNING_NEW_OUTCOMES"]["detail"]


def test_weekly_corruption_uses_the_weekly_severity_policy(tmp_path):
    """심각도는 모드별 기존 정책을 따른다 (nightly hard / weekly soft) — 새 정책 발명 금지."""
    _learning_reports(tmp_path, weekly_extra={"state_load_error": CORRUPT})

    check = _checks(tmp_path)["WEEKLY_LEARNING_STATE_INTEGRITY"]

    assert check["passed"] is False
    assert check["severity"] == "soft_daily"


def test_integrity_check_points_at_the_preserved_corrupt_copy(tmp_path):
    """복구 경로를 알려줘야 한다 — d1538e9가 <name>.corrupt로 보존해 둔다."""
    _learning_reports(tmp_path, nightly_extra={"state_load_error": CORRUPT})

    check = _checks(tmp_path)["NIGHTLY_LEARNING_STATE_INTEGRITY"]

    assert ".corrupt" in check["next_action"]


def test_missing_field_is_treated_as_healthy_for_older_reports(tmp_path):
    """d1538e9 이전 리포트에는 이 필드가 없다 — 과거 산출물을 손상으로 오인하면 안 된다."""
    _learning_reports(tmp_path)
    payload = json.loads((tmp_path / "learning" / "learning_cycle_nightly.json").read_text())
    payload.pop("state_load_error")
    _write_json(tmp_path / "learning" / "learning_cycle_nightly.json", payload)

    checks = _checks(tmp_path)

    assert checks["NIGHTLY_LEARNING_STATE_INTEGRITY"]["passed"] is True
    assert checks["NIGHTLY_LEARNING_NEW_OUTCOMES"]["passed"] is True


def test_corruption_does_not_mask_the_action_check(tmp_path):
    """ACTION 체크는 손상과 독립이어야 한다 — 서로 다른 사실이다."""
    _learning_reports(tmp_path, nightly_extra={"state_load_error": CORRUPT, "action": "dataset_refresh"})

    assert _checks(tmp_path)["NIGHTLY_LEARNING_ACTION"]["passed"] is True
