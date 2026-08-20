"""스위트 전역 픽스처.

재귀게이트 산출물(`runtime_state/reports/validation/research_recursion_gate_latest.json`)은
`.gitignore:61`로 제외된 **런타임 파일**이다. 운영자 체크아웃에는 있고 새 클론·워크트리에는 없다.

`modules.stream_exclusion`이 fail-closed라, 이 파일의 유무가 발행 판정을 뒤집는다:
  - 파일 없음(클론)      → 게이트가 덮는 레인 전부 제외
  - 파일 있음(운영자 기기) → DEGRADE 레인만 제외, OBSERVING 레인은 통과

즉 아무것도 하지 않으면 `build_candidate_interpretation`을 지나는 모든 테스트가
**환경의존**이 된다 — verify-phase0 F-5와 정확히 같은 계열이고, 그때는 운영자 기기에서만
빨간불이라 클론 기준 CI로는 영원히 안 보였다.

그래서 게이트를 "정상·전 레인 OBSERVING"으로 못박는다. 제외 동작 자체를 검증하는
테스트는 `gate_path`를 명시로 넘기거나 `DEFAULT_GATE_PATH`를 직접 갈아끼우므로 영향받지 않는다.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from modules import stream_exclusion as _stream_exclusion

# report_research_recursion_gate.py LANES 전체
_GATE_LANES = (
    "kospi_intraday_t5",
    "kosdaq_intraday_t10",
    "swing_candidate",
    "b_primary_top3",
    "b_all_top10",
    "nasdaq_session_tape",
)


def write_gate_report(path, verdicts=None, *, generated_at=None):
    """테스트용 게이트 산출물 작성 헬퍼. verdicts 미지정 시 전 레인 OBSERVING."""
    table = dict.fromkeys(_GATE_LANES, "OBSERVING")
    table.update(verdicts or {})
    payload = {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "results": [
            {"lane": lane, "verdict": verdict, "n": 50, "fwd_ev": 1.0}
            for lane, verdict in table.items()
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def pin_recursion_gate(tmp_path_factory, monkeypatch):
    """전역 기본값: 신선하고 정상인 게이트, 제외 없음."""
    path = write_gate_report(tmp_path_factory.mktemp("gate") / "research_recursion_gate_latest.json")
    monkeypatch.setattr(_stream_exclusion, "DEFAULT_GATE_PATH", path)
    _stream_exclusion.invalidate_cache()
    yield path
    _stream_exclusion.invalidate_cache()
