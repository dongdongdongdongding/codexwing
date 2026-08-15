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

# 레인별: 원장, 실현수익 필드, 동결된 백테스트 기대(연구 로그 근거), 성숙 표본 수
# cost: 왕복 비용(%p) — 원장은 gross를 저장하므로 게이트가 차감해 net으로 판정 (2026-08-03 PKG-B ②).
#   기대치는 전부 net 기준으로 동결돼 있었음(§28 threshold_frontier=net−0.3, §11-A=net−0.33,
#   §7-A=net, §12-D=net−0.25) — 종전 게이트는 gross forward vs net 기대로 forward에 0.25~0.33
#   관대했음. B는 시장중립 α(백테스트와 동일 기저)라 cost=0.
LANES: Dict[str, Dict[str, Any]] = {
    "kospi_intraday_t5": {
        "ledger": EXP / "kospi_intraday_swing_ledger.jsonl", "field": "exit_t5_h5", "cost": 0.3,
        "expect_ev": 5.65, "expect_win": 92.0, "n_min": 20,
        "basis": "§28 q0.5 승격 (2026-07-13) — 8 OOS월 rank-1 선별 q0.5 티어+터치익절"},
    "kosdaq_intraday_t10": {
        "ledger": EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "field": "exit_t10_h5", "cost": 0.33,
        "expect_ev": 3.14, "expect_win": 75.8, "n_min": 20,
        "basis": "§11-A 15:00 실파이프라인 재검증"},
    "swing_candidate": {
        "ledger": EXP / "kr_swing_candidate_ledger.jsonl", "field": "policy_ret", "cost": 0.3,
        "expect_ev": 0.65, "expect_win": 62.0, "n_min": 30,
        "basis": "§7-A 8년 분기 walk-forward (플라시보 사망)"},
    # swing_ensemble: 2026-07-19 아카이브 — DEGRADE 확정(n=112, EV −0.72)·교체 완료, 일일 실행 중지.
    "b_primary_top3": {
        "ledger": PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", "field": "alpha", "cost": 0.0,
        "filter": {"status": "settled", "tier": "PRIMARY"}, "date_field": "scan_date",
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
                "win_verdict": str(v.get("win_verdict") or "")}
    return {"verdict": str(v or ""), "since": "", "win_verdict": ""}


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


def _suspension(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """정지 마커 판독 (F7).

    규칙: **정지된 레인은 정지 시각 이후에 생성된 표본으로 판정하지 않는다.**
    b 레인은 2026-08-03 정지 선언 후에도 웹 스캔 경로(web/backend/jobs.py::_run_step)에
    가드가 없어 08-04·08-05·08-10 에 30건이 더 생성됐다(orca/reports/trace-b-lane-f7.md).
    생성 경로는 정지를 무시하고 표시 경로는 정지를 지켜서 아무도 모르는 채 정지 레인의
    판정 표본이 불어났다.

    **왜 원장 플래그가 아니라 게이트 쪽 배제인가**
      - 일반해다. "정지 이후 표본 무시"는 레인 단위 규칙이고, 앞으로 정지되는 어떤 레인에도
        마커 배선만으로 적용된다. 행마다 플래그를 박는 방식은 사고가 날 때마다 소급 편집이
        필요하다.
      - 되돌리기 쉽다. 원장(b_shadow.jsonl)은 수정하지 않으므로 판단이 바뀌면 이 배선만
        떼면 되고, 원본 표본은 그대로 남아 재분석이 가능하다.
      - 원장 스키마·내용 변경은 승인 대상이기도 하다.

    **파싱 실패 시 배제하지 않는다** — 표본을 줄이면 n<n_min 에서 DEGRADE 가 OBSERVING 이
    되고, services.py 는 DEGRADE 만 발행 제외하므로 정지 레인이 조용히 발행으로 돌아온다.
    안전장치가 열리는 방향으로 실패하면 안 된다. 대신 note 에 크게 남긴다.
    """
    mk = cfg.get("suspend_marker")
    if not mk or not Path(mk).exists():
        return {"since": None, "broken": False}
    try:
        d = json.loads(Path(mk).read_text(encoding="utf-8"))
        if not d.get("suspended"):
            return {"since": None, "broken": False}
        since = str(d.get("since") or "")[:10]
        if len(since) != 10:
            return {"since": None, "broken": True}
        return {"since": since, "broken": False}
    except Exception:
        return {"since": None, "broken": True}


def _win_verdict(fwd_win_hi: float, expect_win: float) -> str:
    """승률 축 (F5).

    **왜 CI 상단 기준인가** — 승률은 비율이라 표본이 작으면 크게 흔들린다. 점추정으로
    판정하면 잡음에 반응한다. EV 쪽 DEGRADE 가 이미 'CI 상단 < 기대*배율' 형태이므로
    같은 모양을 써서 파일 내부 규칙을 하나로 유지했다.

    **왜 강등에는 안 쓰는가 (비대칭)** — expect_win 의 근거가 레인마다 불균질하다.
    감사 F4 기준 b 레인 두 개의 55.0 은 §11-B 에 근거 수치가 없고, nasdaq 79.3 은 EV 만
    헤어컷된 채 남은 원수치다. 게다가 fwd_win 은 '순수익 > 0.3%' 비율인데 expect_win 의
    출처(예: §28 의 92%)는 터치익절 도달률로 보여 **정의가 일치한다는 보장이 없다**.
    근거가 불확실한 수치로 DEGRADE 를 띄우면 멀쩡한 레인이 발행에서 빠진다(되돌리기 어려운
    방향). 반대로 승격 차단은 틀려도 '아직 안 올림'에 그친다. 그래서 SHORT 는
    ④ 승격 차단 + 진단 티켓까지만 하고, 사이징·발행 판정(verdict)은 건드리지 않는다.
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
    cost = float(cfg.get("cost", 0.0))  # PKG-B ②: 원장 gross → net 통일 (기대치는 전부 net 동결)
    dfield = cfg.get("date_field", "date")
    pairs = [(_row_date(r, dfield), float(r[cfg["field"]]) - cost)
             for r in rows if isinstance(r.get(cfg["field"]), (int, float))]

    # --- F7: 정지 이후 생성된 표본 배제 ---------------------------------------
    susp = _suspension(cfg)
    dropped = 0
    if susp["since"]:
        keep_pairs = [(d, v) for d, v in pairs if not (d and d > susp["since"])]
        dropped = len(pairs) - len(keep_pairs)
        pairs = keep_pairs
    if susp["broken"]:
        susp_note = " · ⚠️정지 마커 판독 실패 — 표본 배제를 적용하지 못했다(수동 확인 필요)"
    elif dropped:
        susp_note = f" · 정지({susp['since']}) 이후 {dropped}건 제외 — 정지 레인은 정지 이후 표본으로 판정하지 않음"
    else:
        susp_note = ""

    vals = [v for _, v in pairs]
    res: Dict[str, Any] = {"lane": name, "basis": cfg["basis"], "n": len(vals), "cost": cost,
                           "expect_ev": cfg["expect_ev"], "expect_win": cfg["expect_win"],
                           "n_min": cfg["n_min"], "win_verdict": "NA",
                           "suspended_since": susp["since"], "excluded_post_suspension": dropped,
                           "suspend_marker_broken": susp["broken"]}

    def _finish(verdict: str, note: str) -> Dict[str, Any]:
        # verdict_since: 계열이 유지되는 동안만 이어받는다 (③이 실제로 소비하는 값).
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
        dated = [(d, v) for d, v in pairs if d]
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
            desc = (f"Why: 재귀 연구 게이트 자동 발행 — {r['lane']} forward n={r['n']} EV {r.get('fwd_ev')} "
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
                    f"틀렸는지(승률 정의 불일치 가능 — 게이트 fwd_win 은 '순수익>0.3%' 비율) 판별. "
                    f"근거: {r['basis']}")
            if _bd_create(title, desc):
                tickets.append(title)
        state[r["lane"]] = {"verdict": r["verdict"], "since": r["verdict_since"],
                            "win_verdict": r["win_verdict"]}
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
