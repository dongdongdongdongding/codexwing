"""재귀게이트 DEGRADE 스트림 제외 — 픽 계약 레벨 단일 지점.

§20 정책: DEGRADE 판정을 받은 레인의 픽은 **사이징 권고를 제거하고 관측 전용으로 강등**한다.
픽 자체는 계속 표시하고(nyg6 계약: 후보 가시성 유지) 원장 채점도 계속한다 —
막는 것은 **라우팅뿐**이다.

이 모듈이 생긴 이유 (audit-gate.md F1·F2):

- **F1** 제외 로직이 `web/backend/services.py:281-288` 한 곳에만 있었다. Discord 카드
  (`renderers.py:889 build_model_signals_embed`, `:647 build_top_deep_embeds`)와 top_deep은
  게이트를 **아예 읽지 않았다**. 그래서 DEGRADE 5레인 픽이 ⛔·관측전용 표시 없이
  진입가·목표가를 단 실행가능 매수카드로 Discord에 나갔다. §40이 "DEGRADE→발행 자동제외
  연동"을 집행완료로 기록했으나 실제 집행 범위는 웹 한 곳이었다.
  두 소비자가 서로 다른 어휘를 쓰는 것이 근본 원인이라(웹=lane_key, Discord=decision_bucket),
  `GATE_LANE_MAP`이 **양쪽 표기를 함께** 들고 한 판정으로 수렴시킨다.

- **F2** 게이트 리더가 fail-**open**이었다. `except Exception: pass` 후 `{}`를 돌려주면
  제외 블록이 통째로 건너뛰어져 DEGRADE 레인이 조용히 2% 사이징으로 복귀했다.
  신선도 검사도 없어 며칠 묵은 판정이 무한정 쓰였다. 안전장치가 **열리는 방향으로** 실패했다.
  → 여기서는 fail-**closed**다. 게이트를 못 읽거나 낡았으면 사이징을 뺀다.

**2026-08-16 운영자 정책 (2026-08-15 결정을 대체):**
`UNGATED`는 "게이트가 판단하지 않는다"이지 **"발행해도 된다"가 아니다.**
게이트 미판단 레인은 발행 불가로 다룬다.

직전 정책은 "fail-closed 범위는 게이트가 덮는 레인뿐"이라 `UNGATED_PUBLISHED_LANES`를
선언만 하고 통과시켰는데, 그 결과 2026-07-19에 아카이브된 `swing_ensemble`의 저장행이
계속 매수카드로 나갔다 — **판단하지 않는다는 사실이 발행 허가로 읽히고 있었다.**
지금은 선언된 발행 레인이 게이트에 없으면 제외하고, 사유(`UNGATED_LANE_KINDS`)로
왜 막혔고 어떻게 풀리는지를 남긴다.

정책 대상은 **선언된 발행 레인**이지 임의 `decision_bucket`이 아니다 —
admission 등 비-발행 버킷까지 막으면 top_deep 일반 후보 카드가 통째로 죽는다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_PATH = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.json"

# 일일 산출물 신선도 기준. report_daily_model_foundation_gate.py:548과 같은 값을 쓴다.
MAX_GATE_AGE_HOURS = 48.0

# 발행 레인 표기 → 재귀게이트 레인명(report_research_recursion_gate.py LANES).
# 웹(`_pick_row`의 lane_key)과 Discord(`decision_bucket`)가 같은 판정을 읽게 하는 것이 핵심이다.
GATE_LANE_MAP: Dict[str, str] = {
    # web lane_key
    "kospi_swing": "swing_candidate",
    "kosdaq_swing": "swing_candidate",
    "kosdaq_intraday": "kosdaq_intraday_t10",
    # web lane_key 이자 Discord decision_bucket (같은 문자열)
    "kospi_intraday": "kospi_intraday_t5",
    # Discord decision_bucket
    "swing_candidate": "swing_candidate",
    "kosdaq_intraday_3d_t5_vwap_guard": "kosdaq_intraday_t10",
    # 2026-08-20 정정: nasdaq_swing 은 UNGATED 가 아니다.
    # 아래 UNGATED 주석은 이 레인이 nasdaq_session_edge 의 웹 어휘라고 적었지만,
    # `services.nasdaq_picks()` 는 **2026-07-07 `10f6dfc` 에서 이미**
    # nasdaq_session_tape_ledger.jsonl 로 바뀌었다 — 게이트가 판정하는 바로 그 원장이다.
    # 08-16 분류가 한 달 묵은 사실 위에 세워졌고, 그래서 게이트가 CONFIRM 을 낸 레인이
    # 화면에선 "게이트가 판단하지 않는 레인"으로 막혔다.
    # 그 주석이 스스로 경고한 '두 어휘' 실패가 선언 계층에서 재발한 것이다.
    "nasdaq_swing": "nasdaq_session_tape",
}

# 발행되지만 게이트가 덮지 않는 레인 — 의도적 미매핑이며, 남의 판정을 물려주지 않는다.
#   nasdaq_session_edge : 라이브 모델 레인. 원장 nasdaq_session_edge_operational_ledger.jsonl.
#                         게이트의 nasdaq_session_tape는 nasdaq_session_tape_ledger.jsonl을 보는
#                         **별개 스트림**이라 판정을 입히면 틀린 배선이 된다.
#   b_market_neutral    : b_primary_top3 / b_all_top10 중 무엇에 대응하는지 행 단위로 모호.
#                         현재 AG_B_ENGINE_SCAN=0으로 스캔 자체가 꺼져 있다.
#   swing_ensemble      : 2026-07-19 아카이브. 게이트 LANES에서 제거됨(과거 픽 해석 호환용만 남음).
#   nasdaq_swing        : 위 nasdaq_session_edge의 **웹 어휘**(services.py:517 `_pick_row` 인자).
#                         2026-08-16 추가 — 두 집합 어디에도 없어 조용히 통과하고 있었다.
#                         "공백을 코드에 명시한다"는 계약이 Discord 어휘에만 적용됐던 것이라,
#                         이 커밋이 잡겠다던 근본원인(두 어휘)이 선언 계층에서 재발한 셈이다.
# 은퇴 레인 — **게이트보다 우선한다.** 게이트가 CONFIRM 을 줘도 여기 있으면 발행하지 않는다.
# 은퇴는 게이트 판정이 아니라 운영자 결정이고, 게이트는 "기대 정합"을 볼 뿐 "거래 가치"를 못 본다
# (services.py:44 운영자 EV 기준이 게이트와 다른 축인 이유와 같다).
RETIRED_LANES: Dict[str, str] = {
    # 2026-08-22 운영자 결정: 죽인다. 근거는 「EV 가 낮다」가 아니라 **「엣지가 체결 불가능한 진입 위에 있었다」**.
    #   · 이 레인은 **신호일 종가 진입**인데 랭커 top-1 의 **19.2% 가 신호일 상한가 종가**다
    #     (유니버스는 0.21% — **91배 농축**). 상한가에는 매도호가가 없어 체결 자체가 안 된다.
    #   · 체결 가능한 픽만 남기면 백테스트 net 이 **+1.620 → −0.009** 로 사라진다(6시드, 음수시드 3/6).
    #     즉 **측정된 엣지의 100% 가 아무도 낼 수 없는 진입 위에 있었다.**
    #   · 전진 실측도 같은 방향이다: n=53 · net EV **−1.87** · 승률 47.2%.
    #   · 운영자 폐기선(services.py:44 `OPERATOR_EV_KILL_PCT=1.0`)에 **백테·전진 양쪽에서** 걸린다.
    #   · 같은 병의 원장 증거: `475150.KS 2026-07-23` 은 +30.00% 종가에 잡혀 **실제 ret3d −39.58%** 인데
    #     원장에는 터치 성공으로 기록돼 있다(`services.py:335 _entry_attainability` docstring).
    # 과거 픽 해석을 위해 LANES 에는 남긴다 — 레인을 지우면 ledger="" 가 되어 /api/picks 가 죽는다.
    "kospi_intraday": "killed",

    # 2026-09-02 운영자 결정: 은퇴. 근거는 「엣지가 없다」가 아니라 **「이 데이터로는 검증이 끝나지 않는다」**.
    #   · 후계 레인 `nasdaq_session_tape`(A1: 편입자격 0.10 · TP5/H20)가 **감사를 통과했다** —
    #     [F4] 가 [U]류 결함(시드-0·이산널 중복추출·풀링)을 찾으러 들어가 하나도 못 찾았고,
    #     새 패널 6시드 전면 재측정에서 net +1.431 · CI 6/6 · 형태일치 널 본페로니 통과.
    #   · 반면 이 레인은 **42거래일간 0픽**이다. 수집은 정상인데(42,520행·120종목·오류 0)
    #     자기 승격 게이트가 `missing_n · missing_days · missing_ret5` 로 막혀 있다.
    #   · 막힌 이유가 구조적이다: `sample_limit_warning = recent_60d_yfinance_5m_intraday_only;
    #     multi_year_overnight_provider_not_loaded`. **다년 장중 공급원 없이는 표본이 안 찬다** — 유료 영역.
    #   · 전진 원장은 2026-06-26 한 행에서 멈춰 있고 파일 mtime 만 매일 새로 찍혔다
    #     (「append 0 에도 전량 재기록」 함정 — 센티넬이 내용 신선도로 잡아냈다).
    # 과거 픽 해석을 위해 LANES 에는 남긴다 — 레인을 지우면 ledger="" 가 되어 /api/picks 가 죽는다.
    "nasdaq_session_edge": "retired",

    # 2026-09-03 운영자 결정: **재학습이 유효해질 때까지 정지**(은퇴가 아니다 — 복귀 경로가 있다).
    #   · 서빙 중이던 `phase25_kr_intraday_xgboost.pkl` 은 **2026-05-08 학습**이고 auc **0.478 —
    #     무작위 미만**이다. 생산자(`evaluate_kr_intraday_models.py`)를 호출하는 곳이
    #     저장소에 없어 넉 달간 아무도 갱신하지 않았다.
    #   · 이를 잡아야 할 OOS 거버넌스는 그 번들에 `oos_*`/`signal_direction` 이 **아예 없어서**
    #     한 번도 발동하지 못했다(`modules/phase25_governance.py` 상단 참조).
    #   · 2026-09-03 재측정(70/15/15 정직 분할): 후보 6종 전부 oos_auc <= 0.503,
    #     그중 4종이 무작위 미만. **리프트가 없다** — rep 구간 기준선 win 37.6% / 평균 −0.88% 에
    #     대해 최고 모델이 37.9% / −0.86% 로 **+0.3pp**, 즉 기준선을 그대로 복제한다.
    #     (같은 자로 잰 SWING 은 +7.6pp 라 이 축만의 문제다.)
    #   · [H1] 독립 실측도 같은 방향: INTRADAY 통합 라인 shadow **−13.2pp (p=3.3e-03)**.
    # 복귀 조건: 재학습 번들이 OOS 게이트를 통과하고(중립화 사유 0건) 리프트가 양수일 것.
    # 두 어휘를 **둘 다** 적는다 — 웹은 lane_key, Discord 는 decision_bucket 을 쓰고
    # 한쪽만 적으면 다른 쪽으로 그대로 나간다(F1 이 정확히 그 실패였다).
    "kosdaq_intraday": "model_stale",
    "kosdaq_intraday_3d_t5_vwap_guard": "model_stale",
}

# 은퇴 사유는 레인마다 다르고 복귀 경로도 다르다. 한 문장으로 뭉치면 남의 사유가 붙는다 —
# 실제로 은퇴 레인이 하나였을 땐 `UNGATED_LANE_NOTES["retired"]` 에 `kospi_intraday` 의
# 사유가 박혀 있었고, 2026-09-02 에 두 번째 레인이 들어오자 그게 그대로 붙었다.
RETIRED_NOTES: Dict[str, str] = {
    # 두 어휘가 같은 사유를 봐야 한다 — 아래에서 alias 로 묶는다.
    "kosdaq_intraday": ("⛔ 발행 제외(관측) — 모델 정지 (2026-09-03). 서빙 모델이 2026-05-08 학습이고 "
                        "auc 0.478(무작위 미만)인데 생산자를 호출하는 곳이 없어 넉 달간 갱신되지 않았다. "
                        "재측정 결과 후보 6종 전부 리프트 없음(기준선 win 37.6%/−0.88% 대비 최고 +0.3pp). "
                        "**복귀 경로 있음**: 재학습 번들이 OOS 게이트를 통과하고 리프트가 양수이면 해제"),
    # 2026-09-03: 이 항목은 그동안 **도달 불가능한 죽은 코드**였다 — kind 가 "killed" 라
    # `_size_note` 가 `UNGATED_LANE_NOTES["killed"]` 만 봤다. 레인별 조회를 모든 kind 로
    # 넓히면서 살아났고, 그때 「죽은 레인」이 「은퇴」로 바뀌는 회귀가 났다(테스트가 잡았다).
    # 이 레인은 은퇴가 아니라 **죽은** 레인이다 — 복귀 경로가 없다는 뜻이고 어휘가 다르다.
    "kospi_intraday": ("⛔ 발행 제외(관측) — 죽은 레인 (2026-08-22 운영자 결정). 엣지가 **체결 불가능한 진입** 위에 있었다: "
                       "랭커 top-1 의 19.2% 가 신호일 상한가 종가(유니버스 0.21% — 91배 농축)이고, "
                       "체결 가능한 픽만 남기면 net 이 +1.620 → −0.009 로 사라진다. 복귀 경로 없음"),
    "nasdaq_session_edge": ("⛔ 발행 제외(관측) — 은퇴 (2026-09-02). 후계 `nasdaq_session_tape`(A1)가 "
                            "감사를 통과했고, 이 레인은 42거래일간 0픽이다. 승격 게이트가 표본 부족으로 "
                            "막혀 있으며 원인이 `multi_year_overnight_provider_not_loaded` — "
                            "**다년 장중 공급원(유료) 없이는 안 풀린다.** 되살리려면 그 데이터부터다"),
}


# 정지 레인의 두 어휘가 같은 사유 문구를 보게 한다(한쪽만 적으면 다른 쪽이 기본 문구로 샌다).
RETIRED_NOTES["kosdaq_intraday_3d_t5_vwap_guard"] = RETIRED_NOTES["kosdaq_intraday"]

# 은퇴/정지 레인은 전부 사유 문구를 가져야 한다 — 없으면 남의 사유가 붙는다.
_missing_note = [k for k in RETIRED_LANES if k not in RETIRED_NOTES]
if _missing_note:
    raise RuntimeError(f"은퇴/정지 레인에 사유 문구가 없다: {sorted(_missing_note)}")

UNGATED_PUBLISHED_LANES = frozenset({
    # nasdaq_swing 은 2026-08-20 에 GATE_LANE_MAP 으로 옮겼다 — 실제로 게이트 원장을 읽는다.
    "nasdaq_session_edge", "b_market_neutral", "swing_ensemble",
})

# UNGATED 레인의 사유 분류. 전부 발행 불가지만 **왜 막혔고 어떻게 풀리는지**가 다르다.
# 2026-08-16 운영자 정책: **UNGATED는 "게이트가 판단하지 않는다"이지 "발행해도 된다"가 아니다.**
#
# 일괄 차단 근거 (실측):
#   swing_ensemble      판정 완료 DEGRADE(n=112, EV −0.72) 후 2026-07-19 아카이브
#   nasdaq_session_edge 자기 원장 1행(2026-06-26, 7주 경과) — forward 근거 없음
#   nasdaq_swing        위 레인의 웹 어휘
#   b_market_neutral    게이트가 b 두 레인 모두 DEGRADE + 2026-08-03 정지 마커
# **네 레인 중 현재 forward 근거를 가진 레인이 하나도 없다.** 따라서 '자기 원장 근거로 가른다'는
# 분기는 오늘 결과를 바꾸지 못하고, **게이트 밖에 두 번째 판정 권위**를 만들 뿐이다 —
# F1·R5에서 닫아 온 '판정 사본이 둘' 실패 계열 그 자체다.
# nasdaq_session_edge를 다시 발행하려면 그 레인을 **게이트 LANES에 배선**하는 게 정답이지
# 여기에 예외를 두는 것이 아니다(tape 판정을 물려주는 오배선과는 별개 문제다).
UNGATED_LANE_KINDS: Dict[str, str] = {
    "swing_ensemble": "retired",
    "nasdaq_session_edge": "unadjudicated",
    # nasdaq_swing 제거(2026-08-20): UNGATED 가 아니라 GATE_LANE_MAP 소속이다.
    # services.nasdaq_picks() 가 읽는 원장이 게이트의 nasdaq_session_tape 그것이다.
    "b_market_neutral": "suspended",
}

UNGATED_LANE_NOTES: Dict[str, str] = {
    "retired": ("⛔ 발행 제외(관측) — 은퇴한 레인 (2026-07-19 아카이브, "
                "판정 완료 DEGRADE n=112 EV −0.72). 복귀 경로 없음 — 교체 완료된 레인이다"),
    "unadjudicated": ("⛔ 발행 제외(관측) — 재귀게이트가 판단하지 않는 레인 "
                      "(자기 스트림이라 타 레인 판정을 물려줄 수 없음). "
                      "발행하려면 게이트 LANES에 이 레인의 원장을 배선해야 한다"),
    "suspended": ("⛔ 발행 제외(관측) — 정지된 레인 "
                  "(b_lane_suspended.json, 2026-08-03 · AG_B_ENGINE_SCAN=0)"),
    "killed": ("⛔ 발행 제외(관측) — 죽은 레인 (2026-08-22 운영자 결정). "
               "측정된 엣지가 체결 불가능한 진입 위에 있었다 — 랭커 top-1 의 19.2% 가 신호일 "
               "상한가 종가(유니버스 0.21%, 91배 농축)라 살 수 없고, 체결 가능한 픽만 남기면 "
               "백테스트 net 이 +1.620 → −0.009 로 사라진다. 전진도 n=53 EV −1.87. "
               "복귀하려면 체결가능성 가드를 생산자에 배선한 뒤 다시 재야 한다"),
}

_missing_kind = UNGATED_PUBLISHED_LANES - frozenset(UNGATED_LANE_KINDS)
if _missing_kind:
    raise RuntimeError(f"UNGATED 레인에 사유 분류가 없다: {sorted(_missing_kind)}")

# 발행 레인은 **두 집합 중 정확히 하나**에 속해야 한다.
DECLARED_PUBLISHED_LANES = frozenset(GATE_LANE_MAP) | UNGATED_PUBLISHED_LANES

_both = frozenset(GATE_LANE_MAP) & UNGATED_PUBLISHED_LANES
if _both:
    raise RuntimeError(f"레인이 GATE_LANE_MAP과 UNGATED에 동시에 선언됨: {sorted(_both)}")

# 게이트가 '정상'이라고 인정하는 판정. 이 목록에 없으면 전부 닫는다(화이트리스트).
# report_research_recursion_gate.py가 내는 값은 OBSERVING / DEGRADE / EXCEED / CONFIRM 넷뿐이다(전수 확인).
# `!= "DEGRADE"` 블랙리스트는 값만 오염돼도 fail-open이었다 — "DEGRADED"·"degrade"·0·None이 전부 통과했고,
# 리포에 이미 **다른 의미의 "DEGRADED"**(파이프라인 헬스)가 있어 어휘충돌은 가설이 아니다.
HEALTHY_VERDICTS = frozenset({"CONFIRM", "OBSERVING", "EXCEED"})

_CACHE: Dict[str, Any] = {"key": None, "ts": 0.0, "state": None}
_CACHE_TTL_SEC = 600.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_hours(stamp: Any, now: datetime) -> Optional[float]:
    text = str(stamp or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (now - parsed).total_seconds() / 3600.0


def load_gate_state(gate_path: Optional[Path] = None, *, now: Optional[datetime] = None, use_cache: bool = True) -> Dict[str, Any]:
    """게이트 판정을 읽는다. **실패는 열리지 않고 닫힌다.**

    반환: `{"usable": bool, "error": str|None, "age_hours": float|None, "lanes": {...}}`
    `usable=False`면 게이트가 덮는 레인은 전부 제외 대상이 된다.
    """
    path = Path(gate_path) if gate_path is not None else DEFAULT_GATE_PATH
    moment = now or _now()

    cache_key = str(path)
    if use_cache and _CACHE["key"] == cache_key and _CACHE["state"] is not None:
        if (moment.timestamp() - float(_CACHE["ts"])) < _CACHE_TTL_SEC:
            return _CACHE["state"]

    state: Dict[str, Any] = {"usable": False, "error": None, "age_hours": None, "lanes": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        state["error"] = "gate_report_missing"
    except Exception as e:
        state["error"] = f"gate_report_unreadable: {type(e).__name__}"
    else:
        if not isinstance(payload, dict):
            state["error"] = "gate_report_malformed"
        else:
            age = _age_hours(payload.get("generated_at"), moment)
            state["age_hours"] = round(age, 3) if age is not None else None
            lanes = {}
            for entry in payload.get("results") or []:
                if isinstance(entry, dict) and entry.get("lane"):
                    lanes[str(entry["lane"])] = {
                        "verdict": entry.get("verdict"),
                        "fwd_ev": entry.get("fwd_ev"),
                        "n": entry.get("n"),
                    }
            if not lanes:
                state["error"] = "gate_report_empty"
            elif age is None:
                state["error"] = "gate_report_undated"
            elif age > MAX_GATE_AGE_HOURS or age < 0:
                # 음수 age = 미래시각 리포트. 검사하지 않으면 영원히 '신선'해서
                # 시계 오류·조작된 타임스탬프가 신선도 게이트를 통째로 무력화한다.
                state["error"] = "gate_report_stale"
                state["lanes"] = lanes
            else:
                state["usable"] = True
                state["lanes"] = lanes

    if use_cache:
        _CACHE.update(key=cache_key, ts=moment.timestamp(), state=state)
    return state


def invalidate_cache() -> None:
    _CACHE.update(key=None, ts=0.0, state=None)


def exclusion_enabled() -> bool:
    """롤백 스위치. 기본 ON — 기존 계약(AG_DEGRADE_STREAM_EXCLUSION=0으로 롤백)을 그대로 유지한다."""
    return os.environ.get("AG_DEGRADE_STREAM_EXCLUSION", "1") == "1"


def stream_status(lane_key: Any, *, gate_state: Optional[Dict[str, Any]] = None,
                  gate_path: Optional[Path] = None, strict: bool = False) -> Dict[str, Any]:
    """레인 하나의 발행 자격. 세 소비자가 전부 이걸 통해서 묻는다.

    `strict=True`는 **발행 관문**(웹 `_pick_row`)용이다. 거기 오는 lane_key는 반드시
    발행 레인이므로, 두 집합 어디에도 없으면 선언을 잊은 것이고 조용히 통과시키면 안 된다.
    비-strict 경로(해석 빌더)는 admission 등 임의 decision_bucket을 지나므로 막지 않는다.
    """
    key = str(lane_key or "")
    # 은퇴가 게이트를 이긴다. 게이트를 먼저 보면 CONFIRM 판정이 은퇴를 덮어쓴다.
    if key in RETIRED_LANES:
        kind = RETIRED_LANES[key]
        # `lane` 을 실어 보낸다 — 사유 문구가 레인마다 다르고, 안 실으면 `_size_note` 가
        # 어느 레인인지 몰라 남의 은퇴 사유를 붙인다(2026-09-02 에 실제로 그랬다).
        return {"gated": False, "excluded": True, "reason": "lane_" + kind,
                "gate_lane": None, "verdict": None, "ungated_kind": kind, "lane": key}
    gate_lane = GATE_LANE_MAP.get(key)
    if gate_lane is None:
        if key in UNGATED_PUBLISHED_LANES:
            # 2026-08-16 정책: 게이트 미판단 = 발행 불가. 사유는 레인별로 다르다.
            kind = UNGATED_LANE_KINDS[key]
            return {"gated": False, "excluded": True, "reason": "lane_" + kind,
                    "gate_lane": None, "verdict": None, "ungated_kind": kind}
        if strict:
            return {"gated": True, "excluded": True, "reason": "lane_undeclared",
                    "gate_lane": None, "verdict": None, "error": "lane_undeclared:" + (key or "-")}
        # 선언된 발행 레인이 아닌 임의 decision_bucket(admission 등)은 정책 대상이 아니다.
        return {"gated": False, "excluded": False, "reason": None, "gate_lane": None, "verdict": None}

    state = gate_state if gate_state is not None else load_gate_state(gate_path)
    if not state.get("usable"):
        stale = state.get("error") == "gate_report_stale"
        return {
            "gated": True,
            "excluded": True,
            "reason": "gate_stale" if stale else "gate_unavailable",
            "gate_lane": gate_lane,
            "verdict": None,
            "age_hours": state.get("age_hours"),
            "error": state.get("error"),
        }

    verdict_row = state["lanes"].get(gate_lane) or {}
    verdict = verdict_row.get("verdict")
    if verdict is None and gate_lane not in state["lanes"]:
        # 게이트는 읽혔는데 이 레인 판정이 없다 = 덮인다고 믿었던 레인이 사라졌다. 닫는다.
        return {"gated": True, "excluded": True, "reason": "gate_unavailable",
                "gate_lane": gate_lane, "verdict": None, "error": "lane_missing_from_gate"}
    healthy = verdict in HEALTHY_VERDICTS
    if healthy:
        reason = None
    elif verdict == "DEGRADE":
        reason = "degrade"
    else:
        reason = "unrecognized_verdict"
    return {
        "gated": True,
        "excluded": not healthy,
        "reason": reason,
        "gate_lane": gate_lane,
        "verdict": verdict,
        "n": verdict_row.get("n"),
        "fwd_ev": verdict_row.get("fwd_ev"),
    }


def _size_note(status: Dict[str, Any]) -> str:
    reason = status.get("reason")
    if reason == "degrade":
        return (f"⛔ 발행 제외(관측) — 재귀게이트 DEGRADE (forward n={status.get('n')} "
                f"EV {status.get('fwd_ev')}, §20 스트림 제외 정책)")
    kind = status.get("ungated_kind")
    if kind:
        # 2026-09-03: 레인별 문구를 **모든 kind 에서** 먼저 찾는다. 이전에는 'retired' 일 때만
        # 찾아서, 새 kind 를 추가하면 다시 남의 사유가 붙는 구조였다(2026-09-02 재발 지점과 같다).
        lane_note = RETIRED_NOTES.get(str(status.get("lane") or ""))
        if lane_note:
            return lane_note
        return UNGATED_LANE_NOTES.get(kind, UNGATED_LANE_NOTES["retired"])
    if reason == "lane_undeclared":
        return ("⛔ 발행 제외(관측) — 이 레인이 스트림 계약에 선언되지 않음 "
                "(modules/stream_exclusion.py의 GATE_LANE_MAP 또는 UNGATED_PUBLISHED_LANES에 추가 필요)")
    if reason == "unrecognized_verdict":
        return (f"⛔ 발행 제외(관측) — 재귀게이트 판정을 해석할 수 없음 "
                f"(verdict={status.get('verdict')!r}, 화이트리스트 밖, fail-closed)")
    if reason == "gate_stale":
        age = status.get("age_hours")
        return (f"⛔ 발행 제외(관측) — 재귀게이트 판정이 낡음 "
                f"({age}h > {MAX_GATE_AGE_HOURS}h, fail-closed)")
    return "⛔ 발행 제외(관측) — 재귀게이트 판정을 읽을 수 없음 (fail-closed)"


def apply_stream_exclusion(
    row: Dict[str, Any],
    lane_key: Any,
    *,
    gate_state: Optional[Dict[str, Any]] = None,
    gate_path: Optional[Path] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """픽 행에 스트림 제외를 적용한다(제자리 수정 후 같은 행 반환).

    제외 시: 사이징 권고 제거 · `stream_excluded=True` · ⛔ 라벨 ·
    실행가능 표식(`buy_ready` / `operational_action_level`) 회수.
    픽 내용(코드·확률·진입가)과 원장 채점은 건드리지 않는다.
    """
    if not isinstance(row, dict):
        return row
    if not exclusion_enabled():
        return row

    status = stream_status(lane_key, gate_state=gate_state, gate_path=gate_path, strict=strict)
    if not status.get("excluded"):
        return row

    row.pop("size_pct_total", None)
    row["stream_excluded"] = True
    row["stream_exclusion_reason"] = status.get("reason")
    row["size_note"] = _size_note(status)
    marker = "⛔관측전용(DEGRADE)" if status.get("reason") == "degrade" else "⛔관측전용(게이트 불가)"
    existing = row.get("rationale")
    row["rationale"] = f"{existing} · {marker}" if existing else marker

    # 실행가능 매수 표식 회수 — F1에서 실제 피해가 난 지점(Discord 매수카드).
    if "buy_ready" in row:
        row["buy_ready"] = False
    if "operational_action_level" in row:
        row["operational_action_level"] = "OBSERVE_ONLY"
    return row
