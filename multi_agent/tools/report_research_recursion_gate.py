#!/usr/bin/env python3
"""Recursive research gate (모델 연구 재귀 루프의 심판자).

Every lane already auto-scores its forward outcomes into a ledger. This tool closes the
loop: per lane it compares matured forward results against the lane's frozen backtest
expectation and issues a verdict —
  OBSERVING        n < n_min (표본 미성숙)
  CONFIRM          forward CI가 백테스트 기대의 절반 이상을 지지 (계속 + 표본 확대)
  DEGRADE          forward CI 상단 < 기대EV의 50% 또는 forward 평균 <= 0
                   (사이징 축소 권고 + 재연구 beads 티켓 자동 발행)
  EXCEED_PENDING   forward 평균 > 기대EV*1.5 이나 승격 조건 미충족 — 관측만, 티켓 없음
  EXCEED_ELIGIBLE  승격 조건 전부 충족 — 승격/확대 검토 티켓

승격(EXCEED_ELIGIBLE) 조건 — 2026-08-15 F3 수리로 **코드 강제**. 이전에는 note 문자열이라
사람이 그대로 우회할 수 있었다(§36 whipsaw: EXCEED 5영업일 뒤 DEGRADE 재발 방지 실패):
  ① 성숙시차 재확인 — 최근 MATURITY_LAG_BDAYS 영업일을 제외한 지연 표본만으로도 기대*1.5 초과
  ② n >= EXCEED_MIN_N
  ③ EXCEED 계열을 EXCEED_HOLD_BDAYS 영업일 이상 유지 (verdict_since 를 실제로 소비)
  ④ 승률이 기대 대비 미달(win_verdict=SHORT)이 아닐 것

승률 축(win_verdict, 2026-08-15 F5) — expect_win 이 어떤 분기에도 없던 것을 편입:
  OK / SHORT / NA. **비대칭 설계**: 승격은 막지만(④) 강등은 시키지 않는다. 근거는
  docstring 아래 _win_verdict() 참조.

Ticket dedup via state file — one ticket per lane per verdict-change. Runs in daily ops.

  python3 multi_agent/tools/report_research_recursion_gate.py [--no-tickets]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
USR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
OUT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.json"
OUT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.md"
STATE = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "recursion_gate_state.json"

# --- 승격 래칫 상수 (F3: 선언 → 코드 강제) ---------------------------------
EXCEED_MIN_N = 100          # ② 표본 하한
EXCEED_HOLD_BDAYS = 10      # ③ EXCEED 유지 영업일
MATURITY_LAG_BDAYS = 5      # ① 성숙시차 — 이 기간의 최신 표본을 빼고 재확인
# ④ 승률 미달 판정 배율: 부트스트랩 CI **상단**이 기대*WIN_TOL 아래면 SHORT.
# 1.0 = "95% CI 전체가 동결 기대 아래" — 임의 상수 없이 통계적 유의성만으로 판정한다.
# 라이브 6레인 실측 캘리브레이션(2026-08-15): 0.85 는 한 레인도 못 잡고, 1.0 은
# kospi_intraday_t5(69.8% vs 92.0, CI[55.8,81.5]) 하나만 잡는다 — 감사 F5 가 지목한 바로
# 그 레인이다. 나머지 5레인은 CI 가 기대에 걸쳐 있어 잡음으로 판정하지 않는다.
WIN_TOL = 1.0

# 발행 스트림 선언용 센티널. **모든 레인이 publish_scope 를 명시해야 한다** — 미선언이
# 조용히 "원장 전체"로 떨어지면 kospi_intraday 에서 난 사고(발행되지 않는 픽으로 발행
# 레인을 강등)가 다른 레인에서 그대로 반복된다. 전체가 발행분인 레인도 값을 적어 선언한다.
WHOLE_LEDGER = "WHOLE_LEDGER"

# 레인별: 원장, 실현수익 필드, 동결된 백테스트 기대(연구 로그 근거), 성숙 표본 수
# cost: 왕복 비용(%p) — 원장은 gross를 저장하므로 게이트가 차감해 net으로 판정 (2026-08-03 PKG-B ②).
#   기대치는 전부 net 기준으로 동결돼 있었음(§28 threshold_frontier=net−0.3, §11-A=net−0.33,
#   §7-A=net, §12-D=net−0.25) — 종전 게이트는 gross forward vs net 기대로 forward에 0.25~0.33
#   관대했음. B는 시장중립 α(백테스트와 동일 기저)라 cost=0.
LANES: Dict[str, Dict[str, Any]] = {
    "kospi_intraday_t5": {
        "ledger": EXP / "kospi_intraday_swing_ledger.jsonl", "field": "exit_t5_h5", "cost": 0.3,
        # 2026-08-16 판정범위 수정(운영자 승인, audit-lane-champions.md): §7-E:178 은 이 레인이
        #   PRIMARY 만 라우팅하고 "CANDIDATE 는 원장 기록만"이라고 명시한다. 그런데 게이트는
        #   원장 전체 43건으로 DEGRADE 를 냈고, 그 표본에 **게이트 자신이 베토한 3건**
        #   (VETO_REBOUND_PHASE, net −4.83), 티어제 이전 15건(−3.03), 라우팅 안 되는
        #   CANDIDATE 15건이 섞여 있었다. 발행되지 않는 픽으로 발행 레인을 강등한 것이다.
        #   (베토분이 원장에 남는 것 자체는 정상이다 — forward 연속성. 판정에 쓰는 게 문제다.)
        "publish_scope": {"tier": "PRIMARY"},
        "expect_ev": 5.65, "expect_win": 92.0, "n_min": 20,
        "basis": "§28 q0.5 승격 (2026-07-13) — 8 OOS월 rank-1 선별 q0.5 티어+터치익절"},
    "kosdaq_intraday_t10": {
        "ledger": EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "field": "exit_t10_h5", "cost": 0.33,
        # 원장 8행 전부 decision=KOSDAQ_INTRADAY_3D_T5_BUY 인 발행분이다(티어 구분 없음).
        "publish_scope": WHOLE_LEDGER,
        # 2026-08-16 정본 통일(운영자 승인, audit-lane-basis.md "소비자 간 동결값 불일치"):
        #   expect_win 75.8 → 72.0. 게이트는 §11-A:263(2026-07-03, n=66)의 75.8 을, 웹
        #   폴백(services.py:166)은 §27:584(2026-07-13, n=101)의 72 를 써서 **같은 레인에
        #   두 개의 "백테스트 승률"이 동시에 노출**되고 있었다. 더 늦고 표본이 큰 §27 을
        #   정본으로 삼는다 — 게이트를 웹에 맞춘다(웹은 이미 §27, 즉 소비자 한쪽만 갱신돼
        #   있던 상태였다). expect_ev 3.14 는 §11-A 그대로다(§27 은 EV 를 주지 않는다).
        #   ⚠️ 그래서 이 레인은 EV 근거와 승률 근거의 § 가 서로 다르다. 값을 바꿀 때
        #   한쪽만 보고 고치면 다시 갈라진다.
        "expect_ev": 3.14, "expect_win": 72.0, "n_min": 20,
        "basis": "EV=§11-A:263 15:00 실파이프라인 재검증(n=66) · 승률=§27:584 티어 승률 맵(n=101, 2026-07-13 정본)"},
    "swing_candidate": {
        "ledger": EXP / "kr_swing_candidate_ledger.jsonl", "field": "policy_ret", "cost": 0.3,
        # ⚠️ 종전 동작(원장 전체)을 그대로 선언한다 — **바꾸지 않기 위해서가 아니라 확인이
        #   안 돼서다.** tier 스탬프가 213행 중 17행(CANDIDATE)에만 있어 나머지 196행이
        #   발행분인지 판별할 근거가 원장에 없다. 근거가 생기면 좁혀야 한다(§ 확인 필요).
        "publish_scope": WHOLE_LEDGER,
        "expect_ev": 0.65, "expect_win": 62.0, "n_min": 30,
        "basis": "§7-A 8년 분기 walk-forward (플라시보 사망)"},
    # swing_ensemble: 2026-07-19 아카이브 — DEGRADE 확정(n=112, EV −0.72)·교체 완료, 일일 실행 중지.
    "b_primary_top3": {
        "ledger": PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", "field": "alpha", "cost": 0.0,
        "filter": {"status": "settled"}, "date_field": "scan_date",
        # 발행 스트림 = PRIMARY 티어. 종전에는 filter 에 섞여 있었는데, filter(성숙 조건)와
        # publish_scope(발행 범위)는 다른 개념이라 분리했다. 판정 대상은 종전과 동일하다.
        "publish_scope": {"tier": "PRIMARY"},
        "suspend_marker": PROJECT_ROOT / "b_engine" / "data" / "b_lane_suspended.json",
        # 2026-08-15 F4 정정: expect_win 55.0 은 §11-B 표에 승률 열 자체가 없어 근거가
        #   없었다. 원장이 이미 win=int(alpha>0) 을 저장하므로 실측으로 교체(정지 이후
        #   제외 후 n=52). expect_ev 2.18 은 §11-B:271 BASE top3 와 일치 — 유지.
        "expect_ev": 2.18, "expect_win": 38.5, "n_min": 30,
        "basis": "§11-B:271 24폴드 BASE top3 +2.18 (α/트레이드) · 승률=원장 실측 2026-08-15"},
    "b_all_top10": {
        # 2026-07-10: 전체 스트림 감시 추가 — PRIMARY 정산 대기 중 top10 전체가 α −5.1로 붕괴한
        # 사각지대 발견(운영자 질의). tier 스탬프 이전 정산분 포함 전체를 게이트가 공식 판정.
        "ledger": PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", "field": "alpha", "cost": 0.0,
        "filter": {"status": "settled"}, "date_field": "scan_date",
        # 이 레인은 **설계상 전체 스트림 감시용**이다(2026-07-10, PRIMARY 정산 대기 중
        # top10 전체가 α −5.1 로 붕괴한 사각지대를 잡으려고 추가). 발행분만 보면 존재 이유가
        # 사라진다 — 여기서 WHOLE_LEDGER 는 미선언 폴백이 아니라 명시적 설계 선택이다.
        "publish_scope": WHOLE_LEDGER,
        "suspend_marker": PROJECT_ROOT / "b_engine" / "data" / "b_lane_suspended.json",
        # 2026-08-15 F4 정정(운영자 승인, audit-lane-basis.md): expect_ev 1.20 → 1.63.
        #   커밋 9e47d73 이 "expect +1.20 per §11-B"라 명시했으나 §11-B:271 의 top10
        #   점추정은 +1.63 이고 1.20 은 CI 하단(1.19)에 가까운 값이었다. 임계가 곱셈이라
        #   기대를 낮게 잡는 것은 보수적이지 않다 — 강등(0.5x)과 승격(1.5x) 문턱이 동시에
        #   내려가 부실 레인을 살려두면서 승격은 앞당긴다. 규칙: **점추정을 동결한다**
        #   (kosdaq §11-A 도 CI 하단 0.21 을 두고 점추정 3.14 를 쓰고 있어 이쪽이 일관).
        # expect_win: 근거 없던 55.0 → 원장 실측(net>0, 정지 이후 제외 후 n=380) 40.3.
        "expect_ev": 1.63, "expect_win": 40.3, "n_min": 30,
        "basis": "§11-B:271 24폴드 BASE top10 점추정 +1.63 (α/트레이드) · 승률=원장 실측 2026-08-15"},
    "nasdaq_session_tape": {
        "ledger": USR / "nasdaq_session_tape_ledger.jsonl", "field": "policy_ret", "cost": 0.25,
        # 원장 54행 전부 tier=SHADOW — shadow 레인이라 기록분이 곧 발행(shadow)분이다.
        "publish_scope": WHOLE_LEDGER,
        "expect_ev": 0.75, "expect_win": 79.3, "n_min": 30,
        "basis": "§12-D 29개월 (정직 추정 +0.5~1.0 — 기대는 중간값 0.75)"},
}


def _rows(fp: Path) -> List[Dict[str, Any]]:
    if not fp.exists():
        return []
    out = []
    for l in fp.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def _load_state() -> Dict[str, str]:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _bd_create(title: str, desc: str) -> bool:
    try:
        r = subprocess.run([os.environ.get("BD_BIN", "/Users/dongdong/.local/bin/bd"), "create", f"--title={title}", f"--description={desc}",
                            "--type=task", "--priority=1"], capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _family(verdict: str) -> str:
    """EXCEED_PENDING ↔ EXCEED_ELIGIBLE 은 같은 계열.

    계열로 묶지 않으면 PENDING→ELIGIBLE 승격 순간 verdict_since 가 리셋돼 다음 날 다시
    PENDING 으로 떨어지는 플립플롭이 난다(③을 영원히 못 채운다).
    """
    return "EXCEED" if verdict.startswith("EXCEED") else verdict


def _prev_entry(state: Dict[str, Any], lane: str) -> Dict[str, str]:
    """구형 state 는 값이 문자열이었다 ("swing_ensemble": "DEGRADE")."""
    v = state.get(lane)
    if isinstance(v, dict):
        return {"verdict": str(v.get("verdict") or ""), "since": str(v.get("since") or ""),
                "win_verdict": str(v.get("win_verdict") or ""),
                # 마커가 삭제돼도 정지 창을 잃지 않으려면 게이트가 스스로 기억해야 한다
                "suspension": v.get("suspension") or None}
    return {"verdict": str(v or ""), "since": "", "win_verdict": "", "suspension": None}


def _row_date(row: Dict[str, Any], key: str) -> str:
    """ISO(2026-08-14) / compact(20260814) / 타임스탬프 앞부분을 ISO 로 정규화."""
    raw = row.get(key)
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    s = s[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return ""


def _bd(d: str) -> Any:
    return np.datetime64(d, "D")


def _norm_ts(value: Any) -> str:
    """타임스탬프/날짜를 비교 가능한 ISO 문자열로. **시각을 버리지 않는다.**

    d42d1a2 는 `str(since)[:10]` 로 시각을 잘라냈다. 정지가 09:00 이어도 같은 날 09:30 픽이
    표본에 남는다 — 이 게이트가 제거하려는 바로 그 희석이다(verify-gate-d42d1a2.md §2).

    한계(명시): 타임존 표기는 떼고 **벽시계로 비교**한다. 마커와 원장이 같은 호스트에서
    생성되므로 실무상 성립하지만, 서로 다른 타임존이 섞이면 어긋난다.
    """
    s = str(value or "").strip()
    if not s:
        return ""
    s = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", s)
    if len(s) > 10 and s[10] == " ":
        s = s[:10] + "T" + s[11:]
    if len(s) >= 8 and s[:8].isdigit() and "-" not in s[:10]:
        s = f"{s[:4]}-{s[4:6]}-{s[6:8]}" + s[8:]
    return s


def _is_post_suspension(row_ts: str, row_date: str, since: str) -> bool:
    """행이 정지 시각 **이후** 생성됐는가 (경계는 배타적).

    since 에 시각이 있고 행에도 시각이 있으면 시각까지 비교한다. 둘 중 하나라도 날짜뿐이면
    날짜 경계로 떨어진다 — 정지 당일 픽을 통째로 지우지 않기 위해서다. 2026-08-03 정지
    (커밋 22:28)의 그날 13건은 13:48·20:03 생성으로 전부 정지 이전이었고, 날짜 경계라야 산다.
    """
    if not since:
        return False
    if len(since) > 10 and row_ts and len(row_ts) > 10:
        return row_ts > since
    rd = (row_ts or row_date)[:10]
    return bool(rd) and rd > since[:10]


def _stamp_record(rec: Any, today: str) -> Any:
    """정지 창 기록의 최초 관측일을 채운다(이미 있으면 보존)."""
    if not rec or not rec.get("since"):
        return rec or None
    return {"since": rec["since"], "first_seen": rec.get("first_seen") or today}


def _suspension(cfg: Dict[str, Any], prev: Dict[str, Any]) -> Dict[str, Any]:
    """정지 마커 판독 (F7). **엔진 b_engine/model_scan.suspension() 과 같은 의미론.**

    규칙: 정지된 레인은 정지 시각 이후에 생성된 표본으로 판정하지 않는다. b 레인은
    2026-08-03 정지 선언 후에도 웹 스캔 경로에 가드가 없어 30건이 더 생성됐다
    (orca/reports/trace-b-lane-f7.md).

    **왜 원장 플래그가 아니라 게이트 쪽 배제인가** — 일반해이고(앞으로 정지되는 어떤 레인도
    마커 배선만으로 적용), 원장을 수정하지 않아 되돌리기 쉬우며, 원장 내용 변경은 승인 대상이다.

    **fail-closed (2026-08-16 교정)** — 마커를 못 읽으면 정지로 본다. 해제는 파일 삭제 또는
    명시적 `"suspended": false` 이지 파싱 실패가 아니다. d42d1a2 는 `if not d.get("suspended")`
    라 키 누락·리스트·falsy 를 해제로 읽어 **엔진과 어긋나 있었다** — 엔진은 멈추는데 게이트는
    정지 이후 표본으로 계속 판정하는 형태로, F7 을 만든 "호출자마다의 관례"의 재발이다.

    d42d1a2 가 fail-open 을 택한 근거("표본을 줄이면 n<n_min 에서 DEGRADE 가 OBSERVING 이
    되고 stream_exclusion 은 verdict 만 읽으므로 발행이 재개된다")는 옳았다. 해법은 fail-open 이
    아니라 **정지 자체가 발행을 막게** 하는 것이다 — 그러면 표본 크기가 판정을 좌우하지 않아
    fail-closed 와 안전성을 동시에 얻는다. evaluate() 의 publication_block 참조.

    **마커 삭제 감지** — 삭제는 마커 자신의 resume_condition 이 규정한 정상 재개 절차이면서
    동시에 사고 경로이고, 둘이 같은 몸짓이라 구분 신호가 없었다. 게이트가 관측한 정지 창을
    state 에 기억해, 마커가 사라져도 **그 창에 생성된 표본은 계속 배제**한다. 재개는 앞으로를
    여는 것이지 정지 중 계약 위반 표본을 소급 정당화하지 않는다. 발행 자체는 다시 허용한다 —
    막으면 문서화된 재개 절차가 동작하지 않는다.
    """
    mk = cfg.get("suspend_marker")
    rec = (prev or {}).get("suspension") or None
    rec_since = (rec or {}).get("since") or ""

    def _resumed(reason: str) -> Dict[str, Any]:
        return {"suspended": False, "broken": False, "resumed": bool(rec),
                "since": rec_since, "record": rec, "reason": reason if rec else ""}

    if not mk or not Path(mk).exists():
        return _resumed("정지 마커가 사라졌다 — 재개 절차이거나 실수다(수동 확인 필요)")
    try:
        d = json.loads(Path(mk).read_text(encoding="utf-8"))
    except Exception:
        return {"suspended": True, "broken": True, "resumed": False, "since": rec_since,
                "record": rec, "reason": "정지 마커를 읽을 수 없다 — 안전하게 정지로 취급(fail-closed)"}
    if isinstance(d, dict):
        if d.get("suspended") is False:          # 엔진과 동일한 정체 비교
            return _resumed("정지가 명시적으로 해제됐다(suspended=false)")
        since = _norm_ts(d.get("since")) or rec_since
        return {"suspended": True, "broken": False, "resumed": False, "since": since,
                "record": {"since": since, "first_seen": (rec or {}).get("first_seen") or ""},
                "reason": f"레인 정지 중(since={since or '미상'})"}
    return {"suspended": True, "broken": True, "resumed": False, "since": rec_since,
            "record": rec, "reason": "정지 마커 형식 오류 — 안전하게 정지로 취급(fail-closed)"}


def _win_verdict(fwd_win_hi: float, expect_win: float) -> str:
    """승률 축 (F5).

    **왜 CI 상단 기준인가** — 승률은 비율이라 표본이 작으면 크게 흔들린다. 점추정으로
    판정하면 잡음에 반응한다. EV 쪽 DEGRADE 가 이미 'CI 상단 < 기대*배율' 형태이므로
    같은 모양을 써서 파일 내부 규칙을 하나로 유지했다.

    **왜 강등에는 안 쓰는가 (비대칭)** — expect_win 의 근거가 레인마다 불균질하다.
    감사 F4 기준 b 레인 두 개의 55.0 은 §11-B 에 근거 수치가 없고, nasdaq 79.3 은 EV 만
    헤어컷된 채 남은 원수치다. 게다가 fwd_win 은 '순수익 > 0' 비율인데 expect_win 의
    출처(예: §28 의 92%)는 터치익절 도달률로 보여 **정의가 일치한다는 보장이 없다**.
    근거가 불확실한 수치로 DEGRADE 를 띄우면 멀쩡한 레인이 발행에서 빠진다(되돌리기 어려운
    방향). 반대로 승격 차단은 틀려도 '아직 안 올림'에 그친다. 그래서 SHORT 는
    ④ 승격 차단 + 진단 티켓까지만 하고, 사이징·발행 판정(verdict)은 건드리지 않는다.

    ⚠️ **알려진 무력화 — 두 b 레인에서 이 축은 자기참조다** (verify-gate-d42d1a2.md §5).
    2026-08-15 F4 정정이 근거 없던 expect_win 55.0 을 **그 시점의 실측값**으로 채웠다
    (top3 38.5 / top10 40.3). 기대치가 측정치와 같으면 CI 상단은 반드시 기대 이상이므로
    **이 두 레인은 정의상 SHORT 가 될 수 없다.** 즉 승률 축은 b 레인에 대해 지금 아무것도
    감시하지 못한다. 근거 없는 상수를 실측으로 바꾼 것 자체는 개선이지만, 동결 기대치를
    측정치로 채우는 것은 §7-A 류 walk-forward 관행과 어긋난다. 독립 근거(백테스트 승률)로
    재동결하기 전까지는 이 두 레인의 win_verdict=OK 를 "승률이 기대에 부합한다"로 읽으면 안
    된다 — 표본이 자기 기준이라 항상 OK 다. 나머지 4레인은 정상 작동한다.
    """
    return "SHORT" if fwd_win_hi < expect_win * WIN_TOL else "OK"


def evaluate(name: str, cfg: Dict[str, Any], state: Dict[str, Any] | None = None,
             today: str | None = None) -> Dict[str, Any]:
    state = state or {}
    today = today or _today()
    prev = _prev_entry(state, name)

    rows = _rows(cfg["ledger"])
    flt = cfg.get("filter") or {}
    rows = [r for r in rows if all(r.get(k) == v for k, v in flt.items())]

    # --- 판정 범위 = 발행 스트림 -------------------------------------------
    # 미선언은 오류다. 기본값을 주면 그 기본값이 조용히 정책이 된다(플래그 P0 의 교훈).
    if "publish_scope" not in cfg:
        raise KeyError(f"{name}: publish_scope 미선언 — 발행 스트림 기준을 명시해야 한다 "
                       f"(행 필터 dict 또는 WHOLE_LEDGER)")
    scope = cfg["publish_scope"]
    ledger_n = len(rows)
    if scope != WHOLE_LEDGER:
        rows = [r for r in rows if all(r.get(k) == v for k, v in scope.items())]
    cost = float(cfg.get("cost", 0.0))  # PKG-B ②: 원장 gross → net 통일 (기대치는 전부 net 동결)
    dfield = cfg.get("date_field", "date")
    tfield = cfg.get("time_field", "logged_at")
    triples = [(_row_date(r, dfield), _norm_ts(r.get(tfield)), float(r[cfg["field"]]) - cost)
               for r in rows if isinstance(r.get(cfg["field"]), (int, float))]

    # --- F7: 정지 이후 생성된 표본 배제 ---------------------------------------
    susp = _suspension(cfg, prev)
    kept = [t for t in triples if not _is_post_suspension(t[1], t[0], susp["since"])]
    dropped = len(triples) - len(kept)
    triples = kept

    notes = []
    if susp["broken"]:
        notes.append(f"⚠️{susp['reason']}")
    if susp["resumed"]:
        notes.append(f"⚠️{susp['reason']} — 기록된 정지 창({susp['since']}) 표본은 계속 배제한다")
    if dropped:
        notes.append(f"정지({susp['since']}) 이후 {dropped}건 제외 — 정지 레인은 정지 이후 표본으로 판정하지 않음")
    susp_note = ("" if not notes else " · " + " · ".join(notes))

    vals = [v for _, _, v in triples]
    block = bool(susp["suspended"])
    res: Dict[str, Any] = {"lane": name, "basis": cfg["basis"], "n": len(vals), "cost": cost,
                           "expect_ev": cfg["expect_ev"], "expect_win": cfg["expect_win"],
                           "n_min": cfg["n_min"], "win_verdict": "NA",
                           "publish_scope": "WHOLE_LEDGER" if scope == WHOLE_LEDGER else dict(scope),
                           "ledger_rows_before_scope": ledger_n,
                           "suspended_since": susp["since"] or None,
                           "excluded_post_suspension": dropped,
                           "suspend_marker_broken": susp["broken"],
                           "marker_resumed": susp["resumed"],
                           "suspension_record": _stamp_record(susp["record"], today),
                           "publication_block": block,
                           "publication_block_reason": susp["reason"] if block else ""}

    def _finish(verdict: str, note: str) -> Dict[str, Any]:
        # 정지 레인은 성적과 무관하게 발행되지 않아야 한다. 소비자(services.py·
        # stream_exclusion)가 읽는 신호는 verdict 하나뿐이고 DEGRADE 만 사이징을 뺀다 —
        # 새 문자열을 만들면 소비자가 모르는 값이라 오히려 발행이 열린다. 그래서 판정을
        # DEGRADE 로 내리되 **원 판정을 note 에 남겨** 성적 판단과 구분되게 한다.
        # (더 나은 형태는 픽 계약 레벨의 publication_block 필드를 소비자가 읽는 것이다 —
        #  audit-gate.md F1·F2 권고. services.py 는 내 소유가 아니라 여기서는 못 한다.)
        if block and verdict != "DEGRADE":
            note = f"발행 차단({susp['reason']}) · 원 판정 {verdict}: {note}"
            verdict = "DEGRADE"
        keep = prev["since"] and _family(prev["verdict"]) == _family(verdict)
        res.update(verdict=verdict, note=note + susp_note,
                   verdict_since=prev["since"] if keep else today)
        return res

    if len(vals) < 5:
        return _finish("OBSERVING", f"n={len(vals)} (표본 축적 중)")
    arr = np.array(vals)
    bs = [np.random.default_rng(s).choice(arr, len(arr), True).mean() for s in range(400)]
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    wins = (arr > 0).astype(float)
    wbs = [np.random.default_rng(1000 + s).choice(wins, len(wins), True).mean() * 100 for s in range(400)]
    win_lo, win_hi = float(np.percentile(wbs, 2.5)), float(np.percentile(wbs, 97.5))
    res.update(fwd_ev=round(float(arr.mean()), 2), fwd_win=round(float(wins.mean()) * 100, 1),
               fwd_ci=[round(lo, 2), round(hi, 2)], worst=round(float(arr.min()), 2),
               fwd_win_ci=[round(win_lo, 1), round(win_hi, 1)])
    if len(vals) < cfg["n_min"]:
        return _finish("OBSERVING", f"n={len(vals)}<{cfg['n_min']} — 참고치만")

    # --- 승률 축 (F5). 표본이 성숙한 뒤에만 판정한다. -------------------------
    res["win_verdict"] = _win_verdict(win_hi, cfg["expect_win"])
    res["win_shortfall_pp"] = round(cfg["expect_win"] - float(wins.mean()) * 100, 1)

    if hi < cfg["expect_ev"] * 0.5 or arr.mean() <= 0:
        why = "forward 평균 <= 0" if arr.mean() <= 0 else "forward CI 상단 < 기대EV 50%"
        return _finish("DEGRADE", f"{why} — 스트림 제외(§20 자동) + 재연구")
    if arr.mean() > cfg["expect_ev"] * 1.5:
        # PKG-B ⑤ 래칫 메타규칙(§40) — 2026-08-15 F3: 선언에서 코드 강제로.
        # EXCEED 가 곧 승격이 아니다. 네 조건을 전부 코드가 판정한다.
        gate_n = len(vals) >= EXCEED_MIN_N
        # ③ 유지 영업일 — 계열 판정이므로 verdict 문자열을 먼저 정하기 전에 계산 가능.
        since = prev["since"] if (prev["since"] and _family(prev["verdict"]) == "EXCEED") else today
        hold = int(np.busday_count(_bd(since), _bd(today))) if since <= today else 0
        gate_hold = hold >= EXCEED_HOLD_BDAYS
        # ① 성숙시차 재확인 — 원장 최신일 기준 최근 N영업일을 빼고도 기대*1.5 를 넘는가.
        #   기준을 today 가 아니라 원장 최신일로 잡아야 파이프가 멈춰도 보수적으로 남는다.
        dated = [(d, v) for d, _, v in triples if d]
        lag_ev = None
        gate_lag = False
        if dated:
            cutoff = np.busday_offset(_bd(max(d for d, _ in dated)), -MATURITY_LAG_BDAYS, roll="backward")
            lagged = [v for d, v in dated if _bd(d) <= cutoff]
            if len(lagged) >= cfg["n_min"]:
                lag_ev = round(float(np.mean(lagged)), 2)
                gate_lag = float(np.mean(lagged)) > cfg["expect_ev"] * 1.5
        gate_win = res["win_verdict"] != "SHORT"
        res["exceed_gate"] = {
            "n": gate_n, "n_have": len(vals), "n_need": EXCEED_MIN_N,
            "hold": gate_hold, "hold_bdays": hold, "hold_need": EXCEED_HOLD_BDAYS,
            "lag": gate_lag, "lag_ev": lag_ev, "lag_bdays": MATURITY_LAG_BDAYS,
            "win": gate_win, "fwd_win": res.get("fwd_win"), "expect_win": cfg["expect_win"],
        }
        if gate_n and gate_hold and gate_lag and gate_win:
            return _finish("EXCEED_ELIGIBLE",
                           f"기대 초과 + 승격 4조건 충족 (n={len(vals)}, {hold}영업일 유지, "
                           f"지연표본 EV {lag_ev}, 승률 {res.get('fwd_win')}) — 승격 검토")
        unmet = [lbl for ok, lbl in (
            (gate_lag, f"①성숙시차 지연표본 재확인(EV {lag_ev})"),
            (gate_n, f"②n≥{EXCEED_MIN_N}(현 {len(vals)})"),
            (gate_hold, f"③EXCEED {EXCEED_HOLD_BDAYS}영업일 유지(현 {hold})"),
            (gate_win, f"④승률 {res.get('fwd_win')} vs 기대 {cfg['expect_win']}"),
        ) if not ok]
        return _finish("EXCEED_PENDING", "기대 초과 — 승격 불가, 미충족: " + " / ".join(unmet))
    return _finish("CONFIRM", "백테스트 기대와 정합")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tickets", action="store_true")
    args = ap.parse_args()
    state = _load_state()
    today = _today()
    # verdict_since 는 evaluate() 안에서 소비·산출된다(③). main 은 저장만 한다.
    results = [evaluate(name, cfg, state, today) for name, cfg in LANES.items()]
    tickets = []

    for r in results:
        prev = _prev_entry(state, r["lane"])
        changed = prev["verdict"] != r["verdict"]
        # 승격 티켓은 EXCEED_ELIGIBLE 에서만. EXCEED_PENDING 은 관측일 뿐 승격 신호가 아니다(F3).
        if changed and r["verdict"] in ("DEGRADE", "EXCEED_ELIGIBLE") and not args.no_tickets:
            title = f"[재귀게이트:{r['verdict']}] {r['lane']} forward {r.get('fwd_ev')} vs 기대 {r['expect_ev']}"
            why = (f"발행 차단 — {r['publication_block_reason']}. " if r.get("publication_block")
                   else "")
            desc = (f"Why: 재귀 연구 게이트 자동 발행 — {why}{r['lane']} forward n={r['n']} EV {r.get('fwd_ev')} "
                    f"CI {r.get('fwd_ci')} vs 백테스트 기대 {r['expect_ev']} ({r['basis']}). "
                    f"What: {'열화 원인 진단(레짐/드리프트/계약) 후 재연구 or 레인 축소' if r['verdict']=='DEGRADE' else '승격/사이징 확대 검토 + 과최적화 점검'}. "
                    f"판정 근거: {r['note']}")
            if _bd_create(title, desc):
                tickets.append(title)
        # 승률 미달 티켓(F5). DEGRADE 레인은 이미 재연구 티켓이 나가므로 겹쳐 내지 않는다 —
        # F5 가 지목한 사각지대는 'EV 로만 통과하는' 레인이다.
        if (r["win_verdict"] == "SHORT" and r["verdict"] != "DEGRADE"
                and prev.get("win_verdict") != "SHORT" and not args.no_tickets):
            title = (f"[재귀게이트:승률미달] {r['lane']} 승률 {r.get('fwd_win')}% vs 기대 "
                     f"{r['expect_win']}% ({r['win_shortfall_pp']}pp)")
            desc = (f"Why: EV 판정은 {r['verdict']} 인데 승률이 기대 대비 {r['win_shortfall_pp']}pp 미달 "
                    f"(forward {r.get('fwd_win')}% CI {r.get('fwd_win_ci')}, n={r['n']}). "
                    f"EV 만으로 통과하는 레인의 사각지대 — 프로젝트 목표의 정확도 축이 무감시가 된다. "
                    f"What: ①레인이 실제 열화했는지 ②아니면 동결 기대 {r['expect_win']}%의 근거·정의가 "
                    f"틀렸는지(승률 정의 불일치 가능 — 게이트 fwd_win 은 '순수익>0' 비율) 판별. "
                    f"근거: {r['basis']}")
            if _bd_create(title, desc):
                tickets.append(title)
        entry = {"verdict": r["verdict"], "since": r["verdict_since"],
                 "win_verdict": r["win_verdict"]}
        # 정지 창은 마커가 사라져도 보존한다 — 재개가 정지 중 표본을 소급 정당화하지 않도록.
        rec = r.get("suspension_record") or prev.get("suspension")
        if rec:
            entry["suspension"] = rec
        state[r["lane"]] = entry
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "results": results, "tickets_created": tickets}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Research recursion gate — {report['generated_at'][:10]}", "",
             "| Lane | verdict | fwd n | fwd EV | CI | 기대EV | 승률(기대) | 승률판정 | note |",
             "|---|---|---:|---:|---|---:|---|---|---|"]
    for r in results:
        lines.append(f"| {r['lane']} | **{r['verdict']}** | {r['n']} | {r.get('fwd_ev','–')} | "
                     f"{r.get('fwd_ci','–')} | {r['expect_ev']} | "
                     f"{r.get('fwd_win','–')}% ({r['expect_win']}%) | {r['win_verdict']} | {r['note']} |")
    if tickets:
        lines += ["", "## Auto tickets", *[f"- {t}" for t in tickets]]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({r["lane"]: r["verdict"] for r in results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
