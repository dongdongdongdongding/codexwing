#!/usr/bin/env python3
"""sentinel 기준을 실제로 대조하는 판정기 (OD-37).

`multi_agent/config/sentinel_expectations.yaml` 에는 기준·재계산법·에스컬레이션 대상까지
전부 적혀 있었는데 **그걸 돌리는 것이 존재하지 않았다.** 이 리포가 반복해 온 실패가 정확히 그
형태다 — §40 킬 기준이 산문으로만 적혀 두 달 뒤 우연히 발견됐고, `suspend_marker_broken` 은
결과 JSON 에 실리고도 아무도 읽지 않았다.

## 판정 항목

  OD-34  발화 자격 — 직전 10거래일 중 8일(0.8) 이상 픽이 도착했는가
  OD-35  정지 기한 — suspended_since 경과가 20거래일을 넘었는가
  OD-39  마커 없이 멈춘 레인은 **미달**로 판정한다 (면제를 주면 고장이 정지로 위장된다)
  WARN   자격 전이 — PASS→FAIL 이 보이지 않으면 사이징이 조용히 0 이 된다
  신선도 — mtime 이 아니라 **내용**(행수·max date) 기준
  OD-19  사전등록 킬 기준 대조

## 거래일은 데이터에서 유래시킨다

월~금을 분모로 쓰면 휴장일이 결석으로 잡힌다. goblin 초판이 정확히 그렇게 틀렸고
("정상 75~83%" → 고치면 1.000), 그래서 달력을 **원장의 발화일 union** 에서 만든다.
  KR = union(kospi_intraday_t5, swing_candidate) 발화일
  US = nasdaq_session_tape 자기 발화일 (2번째 US 레인이 없어 독립 검증 불가 — 한계)
당일은 제외한다(미완결). **기한을 날짜로 박지 않는다** — 대체휴일이 끼면 하루씩 밀리므로
"정지일 이후 N번째 거래일"로 매일 재계산한다.

  python3 multi_agent/tools/report_sentinel_expectations.py
  python3 multi_agent/tools/report_sentinel_expectations.py --json-only --no-write
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / "multi_agent" / "config" / "sentinel_expectations.yaml"
OUT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "sentinel_latest.json"
OUT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "sentinel_escalations.md"
STATE = PROJECT_ROOT / "runtime_state" / "long_term" / "ops" / "sentinel_state.json"

SEV_ORDER = {"info": 0, "warn": 1, "alert": 2, "critical": 3}

# OD-50: 노후 문턱은 **산출 파일이 싣고 소비자는 읽는다.** 배선 하루 만에 두 값(36/48)이
# 생겼고, 어느 쪽이 맞느냐가 아니라 두 개라는 것 자체가 OD-44 가 막으려던 형태다.
# 소비자가 자기 기본값을 갖지 않도록 이 필드는 **모든 산출에 반드시 실린다**(테스트로 고정).
MAX_AGE_HOURS = 36

# 레인 정의는 **게이트 LANES 에서 가져온다.** 여기 따로 적으면 두 벌이 갈린다 —
# HEALTHY_VERDICTS 어휘 드리프트와 kosdaq 승률 이중화가 정확히 그 형태였다.
# (아래 상수는 게이트를 못 읽는 환경의 폴백 겸 문서다.)
_FALLBACK_LANE_LEDGERS = {
    "kospi_intraday_t5": ("runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl", "date", "KR"),
    "kosdaq_intraday_t10": ("runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "date", "KR"),
    "swing_candidate": ("runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl", "date", "KR"),
    "b_primary_top3": ("b_engine/data/b_shadow.jsonl", "scan_date", "KR"),
    "b_all_top10": ("b_engine/data/b_shadow.jsonl", "scan_date", "KR"),
    "nasdaq_session_tape": ("runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl", "date", "US"),
}
try:
    from multi_agent.tools.report_research_recursion_gate import (  # noqa: E402
        LANES as _GATE_LANES, trading_days as _gate_trading_days,
    )
    LANE_LEDGERS = {n: (str(c["ledger"]).split("swing-main/")[-1],
                        c.get("date_field", "date"), c.get("market", "KR"))
                    for n, c in _GATE_LANES.items()}
except Exception:                                   # pragma: no cover
    _GATE_LANES, _gate_trading_days = None, None
    LANE_LEDGERS = _FALLBACK_LANE_LEDGERS

KR_CALENDAR_LANES = ["kospi_intraday_t5", "swing_candidate"]
US_CALENDAR_LANES = ["nasdaq_session_tape"]


def _iso(value: Any) -> str:
    s = str(value or "").strip()[:10]
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s if len(s) == 10 and s[4] == "-" else ""


def firing_days(root: Path, lane: str) -> Set[str]:
    """레인이 픽을 낸 날짜 집합. 채점 여부와 무관하다 — '발화했는가'만 묻는다."""
    rel, dfield, _ = LANE_LEDGERS[lane]
    path = root / rel
    if not path.exists():
        return set()
    out: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            iso = _iso(json.loads(line).get(dfield))
        except Exception:
            continue
        if iso:
            out.add(iso)
    return out


def trading_days(root: Path, market: str, today: str) -> List[str]:
    """거래일을 **데이터에서** 유래시킨다. 당일은 미완결이라 제외한다.

    구현은 게이트 한 곳에만 둔다 — 여기 사본을 두면 두 벌이 갈리고, 그게 이 리포가 반복해 온
    드리프트다. 게이트를 못 읽거나 다른 리포 루트를 볼 때만 지역 계산으로 떨어진다.
    """
    if _gate_trading_days is not None and root == PROJECT_ROOT:
        return _gate_trading_days(market, today)
    lanes = KR_CALENDAR_LANES if market == "KR" else US_CALENDAR_LANES
    union: Set[str] = set()
    for lane in lanes:
        union |= firing_days(root, lane)
    return sorted(d for d in union if d < today)


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def _load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gate_suspensions(root: Path) -> Dict[str, Optional[str]]:
    """게이트 산출의 suspended_since. 면제는 여기서만 나온다(OD-39)."""
    path = root / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.json"
    try:
        results = json.loads(path.read_text(encoding="utf-8")).get("results") or []
    except Exception:
        return {}
    return {r.get("lane"): r.get("suspended_since") for r in results if r.get("lane")}


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------

def expired_suspension_lanes(root: Path, cfg: Dict[str, Any], today: str) -> Dict[str, Dict[str, Any]]:
    """OD-35 기한을 넘긴 정지 레인. OD-49 로 **면제를 내기 전에** 쓰인다."""
    out: Dict[str, Dict[str, Any]] = {}
    for d in check_suspension_deadlines(root, cfg, today):
        if d.get("verdict") != "OVERDUE":
            continue
        for lane in (d.get("lanes") or []):
            out[lane] = d
    return out


def check_firing_qualification(root: Path, cfg: Dict[str, Any], today: str,
                               suspensions: Dict[str, Optional[str]],
                               expired: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """OD-34 발화 자격 + OD-39(마커 없는 정지는 면제 아님) + OD-49(면제에 기한이 있다).

    OD-49: 기한 검사가 **여기** 있어야 한다. 발행 경로에 되살리면 "정지가 만료됐는가"를
    두 곳이 판단하게 되어 OD-44 가 막으려는 형태가 된다. 그리고 이 검사가 없으면
    정지 레인이 **무기한 면제**로 남는다 — 실제로 그 상태였다.
    """
    expired = expired or {}
    q = cfg.get("lane_firing_qualification") or {}
    crit = q.get("criterion") or {}
    window = int(crit.get("window_trading_days", 10))
    floor = float(crit.get("floor", 0.8))
    cal = {m: trading_days(root, m, today) for m in ("KR", "US")}

    findings: List[Dict[str, Any]] = []
    for lane, (_, _, market) in LANE_LEDGERS.items():
        days = firing_days(root, lane)
        recent = cal[market][-window:]
        suspended = suspensions.get(lane)
        if not recent:
            findings.append({"check": "firing_qualification", "lane": lane, "verdict": "NO_CALENDAR",
                             "severity": "warn", "detail": f"{market} 거래일을 데이터에서 만들지 못했다"})
            continue
        fired = sum(1 for d in recent if d in days)
        rate = fired / len(recent)
        first = min(days) if days else None
        elapsed = len([d for d in cal[market] if first and d >= first])

        if suspended and lane in expired:
            # 면제가 만료됐다. EXEMPT 로 내보내면 lane_sizing.allowed 가 참이 되어
            # 무기한 정지가 발행 자격처럼 읽힌다.
            verdict, sev = "SUSPENSION_EXPIRED", "alert"
        elif suspended:
            verdict, sev = "EXEMPT", "info"
        elif first is None:
            # OD-39: 마커도 없고 픽도 없다 — 면제를 주면 고장이 정지로 위장된다.
            verdict, sev = "FAIL", "alert"
        elif elapsed < window:
            verdict, sev = "GRACE", "info"     # 신규 레인 보호
        elif rate >= floor:
            verdict, sev = "PASS", "info"
        else:
            verdict, sev = "FAIL", "alert"
        findings.append({
            "check": "firing_qualification", "lane": lane, "verdict": verdict, "severity": sev,
            "fired": fired, "window": len(recent), "rate": round(rate, 3), "floor": floor,
            "market": market, "suspended_since": suspended,
            "suspension_deadline": (expired.get(lane) or {}).get("detail"),
            "action": "block_sizing" if verdict in ("FAIL", "SUSPENSION_EXPIRED") else None,
            "detail": f"{fired}/{len(recent)} = {rate:.2f} (하한 {floor})",
        })
    return findings


def check_qualification_transition(findings: List[Dict[str, Any]],
                                   state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """PASS→FAIL 전이를 보이게 한다. 차단은 자동이지만 **이유가 보여야** 한다."""
    prev = (state.get("firing_verdicts") or {})
    out = []
    for f in findings:
        if f["check"] != "firing_qualification":
            continue
        before = prev.get(f["lane"])
        if before == "PASS" and f["verdict"] == "FAIL":
            out.append({"check": "qualification_transition", "lane": f["lane"], "severity": "warn",
                        "verdict": "TRANSITION", "detail": f"PASS → FAIL ({f['detail']}) — 사이징이 0 이 된다"})
    return out


def check_suspension_deadlines(root: Path, cfg: Dict[str, Any], today: str) -> List[Dict[str, Any]]:
    """OD-35. **날짜를 박지 않는다** — 정지일 이후 N번째 거래일로 매일 재계산한다."""
    q = cfg.get("lane_firing_qualification") or {}
    out = []
    for dl in (q.get("active_deadlines") or []):
        since = _iso(dl.get("suspended_since"))
        limit = int(dl.get("deadline_trading_days", 20))
        market = dl.get("market", "KR")
        cal = trading_days(root, market, today)
        elapsed = len([d for d in cal if d > since])
        over = elapsed > limit
        out.append({
            "check": "suspension_deadline", "id": dl.get("id"), "lanes": dl.get("lanes"),
            "verdict": "OVERDUE" if over else "TRACKING",
            "severity": "alert" if over else "info",
            "suspended_since": since, "elapsed_trading_days": elapsed,
            "deadline_trading_days": limit, "remaining_trading_days": max(0, limit - elapsed),
            "detail": (f"경과 {elapsed}/{limit} 거래일"
                       + ("" if over else f" — 남은 {limit - elapsed}거래일 (달력은 매일 재계산, 날짜 미고정)")),
            "escalate_to": dl.get("escalate_to") or "orca-worker-fleet-infra",
        })
    return out


def check_artifact_freshness(root: Path, cfg: Dict[str, Any], today: str) -> List[Dict[str, Any]]:
    """내용 기준 신선도. mtime 은 매일 재기록되는 원장에서 아무 정보도 주지 않는다."""
    cal = trading_days(root, "KR", today)
    out: List[Dict[str, Any]] = []
    unchecked = 0
    for art in (cfg.get("artifacts") or []):
        raw = str(art.get("path", ""))
        sev = art.get("severity", "medium")
        sev = {"critical": "critical", "high": "alert", "medium": "warn"}.get(sev, "warn")
        if not art.get("producer_scheduled", True):
            continue                                   # 은퇴한 생산자의 정체는 정상이다
        if "{" in raw:
            # 월별 파일 등 템플릿 경로. 해석기 없이 MISSING 으로 올리면 **오탐**이고,
            # 오탐이 쌓이면 경보 전체가 무시된다 — 조용히 넘기지도 않고 미검사로 드러낸다.
            unchecked += 1
            continue
        path = Path(raw).expanduser() if raw.startswith("~") else root / raw
        if not path.exists():
            out.append({"check": "artifact_freshness", "path": str(art.get("path")),
                        "verdict": "MISSING", "severity": sev, "detail": "파일 없음"})
            continue
        max_age = art.get("content_max_age_days")
        rows, max_date = _content_stats(path)
        if max_date:
            newer = [d for d in cal if d > max_date]
            age_td = len(newer)
            limit = int(max_age) if max_age is not None else 5
            stale = age_td > limit
            out.append({"check": "artifact_freshness", "path": str(art.get("path")),
                        "verdict": "STALE_CONTENT" if stale else "OK",
                        "severity": sev if stale else "info", "rows": rows, "max_date": max_date,
                        "age_trading_days": age_td, "limit_trading_days": limit,
                        "mtime_is_meaningless": bool(art.get("mtime_is_meaningless")),
                        "detail": f"내용 최신일 {max_date} · {age_td}거래일 경과(한도 {limit})"})
        else:
            unchecked += 1
    if unchecked:
        out.append({"check": "artifact_freshness", "verdict": "NOT_MACHINE_CHECKABLE",
                    "severity": "warn", "count": unchecked,
                    "detail": f"내용에서 날짜를 못 읽어 판정 불가한 아티팩트 {unchecked}건 — "
                              f"조용히 통과시키지 않고 드러낸다"})
    prose = sum(len(a.get("content_checks") or []) for a in (cfg.get("artifacts") or []))
    if prose:
        out.append({"check": "artifact_freshness", "verdict": "PROSE_RULES_UNRUN", "severity": "warn",
                    "count": prose,
                    "detail": f"산문으로만 적힌 content_checks {prose}건은 기계가 못 돌린다 "
                              f"— OD-19 가 지적한 형태다"})
    return out


def _content_stats(path: Path):
    rows, latest = 0, ""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return 0, ""
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            if not line.strip():
                continue
            rows += 1
            try:
                obj = json.loads(line)
            except Exception:
                continue
            for key in ("date", "scan_date", "trade_date", "base_trade_date"):
                iso = _iso(obj.get(key))
                if iso and iso > latest:
                    latest = iso
    else:
        try:
            obj = json.loads(text)
        except Exception:
            return 0, ""
        rows = 1
        for key in ("generated_at", "score_date", "date", "as_of"):
            iso = _iso(obj.get(key))
            if iso and iso > latest:
                latest = iso
    return rows, latest


def _kc_rows(root: Path, rel: str) -> List[Dict[str, Any]]:
    path = root / str(rel)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _kc_no_rows_after(root: Path, chk: Dict[str, Any]) -> Dict[str, Any]:
    """킬 선언일 이후 신규 행이 생기면 위반. '이미 발동한 킬이 유지되는가'를 묻는다."""
    rows = _kc_rows(root, chk["ledger"])
    after = str(chk["after"])
    dates = [_iso(r.get(chk.get("date_field", "date"))) for r in rows]
    newer = [d for d in dates if d and d > after]          # 행 단위 — 축소 보고 금지
    newer_dates = sorted(set(newer))                        # 거래일 단위
    return {"fired": bool(newer),
            "observed": {"max_date": max(dates) if dates else None,
                         "rows_after": len(newer),
                         "dates_after": len(newer_dates),
                         "first_date_after": newer_dates[0] if newer_dates else None},
            "detail": (f"킬 선언일 {after} 이후 행 {len(newer)}건"
                       f" ({len(newer_dates)}거래일"
                       + (f", {newer_dates[0]}~{newer_dates[-1]}" if newer_dates else "") + ")"
                       if newer else f"킬 선언일 {after} 이후 행 0건")}


def _kc_field_min(root: Path, chk: Dict[str, Any]) -> Dict[str, Any]:
    rows = _kc_rows(root, chk["ledger"])
    field, floor = chk["field"], float(chk["min"])
    vals = [float(r[field]) for r in rows if isinstance(r.get(field), (int, float))]
    bad = [v for v in vals if v < floor]
    return {"fired": bool(bad), "observed": {"rows": len(vals), "min": min(vals) if vals else None,
                                             "violations": len(bad)},
            "detail": f"{len(vals)}행 중 {field}<{floor} 위반 {len(bad)}건"}


def _kc_symbol_absent(root: Path, chk: Dict[str, Any]) -> Dict[str, Any]:
    """어떤 이름이 발행 경로 설정에 등장하면 위반. 파일이 없으면 **판정 불가**로 낸다."""
    path = root / str(chk["file"])
    if not path.exists():
        return {"fired": None, "observed": {"file": str(chk["file"])},
                "detail": f"검사 대상 파일 없음 — 판정 불가"}
    body = path.read_text(encoding="utf-8")
    sym = str(chk["symbol"])
    return {"fired": sym in body, "observed": {"file": str(chk["file"]), "symbol": sym},
            "detail": f"{chk['file']} 안에 '{sym}' {'있음(위반)' if sym in body else '없음'}"}


def _kc_rank_monotonicity(root: Path, chk: Dict[str, Any]) -> Dict[str, Any]:
    """심도 단조성 — 순위~수익 상관(음수여야) + 같은날 top/bottom 차분(양수여야).

    풀링 금지: 시장별로 따로 본다. 표본 하한 미달이면 **판정 불가**를 낸다(0건을 통과로 읽지 않는다).
    """
    import numpy as np
    rows = _kc_rows(root, chk["ledger"])
    rank_f, ret_f = chk.get("rank_field", "rank"), chk.get("return_field", "fwd5_cc")
    cost = float(chk.get("cost", 0.0))
    need_rows = int((chk.get("min_sample") or {}).get("scored_rows_per_market", 100))
    need_days = int((chk.get("min_sample") or {}).get("days", 4))
    per: Dict[str, Any] = {}
    fired = False
    undecided = []
    for mkt in sorted({str(r.get("market")) for r in rows if r.get("market")}):
        sel = [r for r in rows if str(r.get("market")) == mkt
               and isinstance(r.get(ret_f), (int, float)) and isinstance(r.get(rank_f), (int, float))]
        days = {_iso(r.get("date")) for r in sel}
        if len(sel) < need_rows or len(days) < need_days:
            per[mkt] = {"rows": len(sel), "days": len(days), "verdict": "UNDECIDED"}
            undecided.append(mkt)
            continue
        rk = np.array([float(r[rank_f]) for r in sel])
        rv = np.array([float(r[ret_f]) - cost for r in sel])
        corr = float(np.corrcoef(rk, rv)[0, 1]) if rk.std() > 0 and rv.std() > 0 else 0.0
        tops, bots = [], []
        for d in sorted(days):
            day = sorted((r for r in sel if _iso(r.get("date")) == d), key=lambda r: r[rank_f])
            if len(day) < 20:
                continue
            tops.append(np.mean([float(r[ret_f]) - cost for r in day[:10]]))
            bots.append(np.mean([float(r[ret_f]) - cost for r in day[-10:]]))
        depth = float(np.mean(tops) - np.mean(bots)) if tops and bots else None
        hit = (corr >= 0) or (depth is not None and depth <= 0)
        fired = fired or hit
        per[mkt] = {"rows": len(sel), "corr": round(corr, 3),
                    "top10_minus_bottom10": None if depth is None else round(depth, 2),
                    "verdict": "FIRED" if hit else "OK"}
    if undecided and not fired:
        return {"fired": None, "observed": per,
                "detail": f"표본 하한 미달 {undecided} — 판정 불가(0건을 통과로 읽지 않는다)"}
    return {"fired": fired, "observed": per,
            "detail": " · ".join(f"{m}: corr={v.get('corr')} depth={v.get('top10_minus_bottom10')}"
                                 for m, v in per.items())}


KC_EVALUATORS = {
    "no_rows_after_date": _kc_no_rows_after,
    "field_min": _kc_field_min,
    "symbol_absent_in_file": _kc_symbol_absent,
    "rank_return_monotonicity": _kc_rank_monotonicity,
}


ADJUDICATIONS = PROJECT_ROOT / "runtime_state" / "long_term" / "ops" / "adjudications.jsonl"


def _adjudicated_ids(root: Path) -> Dict[str, Dict[str, Any]]:
    """판정 기록 원장. **이 자리가 없던 것이 §40 이 두 달 놓친 진짜 원인이다** —
    킬 기준이 산문이었던 게 문제가 아니라 판정했는지 확인할 곳이 없었다.

    한 줄 = 한 판정: {"gate_id": ..., "adjudicated_at": ..., "outcome": ..., "where": ...}
    """
    path = root / ADJUDICATIONS.relative_to(PROJECT_ROOT)
    out: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        gid = row.get("gate_id")
        if gid:
            out[str(gid)] = row
    return out


def _count_top1_scored(root: Path, chk: Dict[str, Any]) -> Dict[str, Any]:
    """같은날 랭킹 1위이면서 채점까지 끝난 행을 센다.

    **왜 순진한 min_rows 로는 안 되는가**: 이 원장의 raw 행은 225 인데 필요 n 은 46 이다.
    행 수만 세면 46 을 이미 넘어 관문이 **거짓으로 열린다**. 판정에 쓰이는 표본은
    "날짜×시장마다 p 최댓값 1건, policy_ret 채점 완료" 이므로 그 정의대로 세야 한다.

    이것은 여전히 **계수**다 — 연구 술어(CI 하한이 0 을 넘는가)는 평가하지 않는다.
    """
    path = root / str(chk.get("file", ""))
    if not path.exists():
        return {"met": False, "verified": True, "detail": f"{chk.get('file')} 없음"}
    market = chk.get("market")
    score = str(chk.get("score_field", "p"))
    outcome = str(chk.get("outcome_field", "policy_ret"))
    dfield = str(chk.get("date_field", "date"))
    best: Dict[Any, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if market and row.get("market") != market:
            continue
        if not isinstance(row.get(score), (int, float)):
            continue
        key = (row.get(dfield), row.get("market"))
        cur = best.get(key)
        if cur is None or float(row[score]) > float(cur[score]):
            best[key] = row
    scored = [r for r in best.values() if isinstance(r.get(outcome), (int, float))]
    need = int(chk.get("min", 0))
    return {"met": len(scored) >= need, "verified": True,
            "detail": f"{market or '전체'} top-1 채점행 {len(scored)}건 "
                      f"(필요 {need}, 발화일 {len(best)})"}


def _precondition_state(root: Path, pre: Any) -> Dict[str, Any]:
    """선행조건. **연구 술어가 아니라 파일·행수만 본다.**

    `check` 가 있으면 기계로 재확인하고, 없으면 선언된 met 을 쓰되 미검증임을 표시한다 —
    선언을 조용히 사실로 승격시키지 않는다.
    """
    if not isinstance(pre, dict):
        return {"met": True, "verified": False, "detail": "선행조건 미선언 — 즉시 판정 대상"}
    chk = pre.get("check")
    if isinstance(chk, dict) and chk.get("type") == "top1_scored":
        return _count_top1_scored(root, chk)
    if isinstance(chk, dict) and chk.get("type") == "min_rows":
        path = root / str(chk.get("file", ""))
        if not path.exists():
            return {"met": False, "verified": True, "detail": f"{chk.get('file')} 없음"}
        rows = sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip())
        need = int(chk.get("min", 0))
        return {"met": rows >= need, "verified": True,
                "detail": f"{chk.get('file')} {rows}행 (필요 {need})"}
    return {"met": bool(pre.get("met")), "verified": False,
            "detail": f"선언값 met={bool(pre.get('met'))} (미검증) — {pre.get('desc','')}"}


def check_prereg_track_gates(cfg: Dict[str, Any], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """트랙 종료 관문 (OD-48/56).

    **관문은 연구 술어를 평가하지 않는다.** 매일 보는 것은 두 가지뿐이다:

        선행조건 충족  AND  판정 기록 부재   ⇒  발동 (판정이 밀렸다)

    연간 기여 <1%p 같은 걸 매일 계산하는 척하면 매일 같은 답을 내는 가짜 감시가 된다.
    실제 판정은 사람·하니스가 하고, 그 결과가 판정 원장에 남아야 관문이 닫힌다.
    """
    gates = cfg.get("prereg_track_gates") or []
    if not gates:
        return []
    root = root or PROJECT_ROOT
    done = _adjudicated_ids(root)
    out: List[Dict[str, Any]] = []
    for g in gates:
        gid = str(g.get("id", "?"))
        base = {"check": "prereg_track_gate", "id": gid, "kind": g.get("kind", "one_shot"),
                "criterion_at_termination": g.get("criterion_at_termination")}
        status = str(g.get("status", "overdue"))
        if status == "see_standing_registry":
            out.append({**base, "verdict": "IN_STANDING_REGISTRY", "severity": "info",
                        "detail": f"상시 항목 {g.get('ref')} 에 등록됨 — 중복 판정하지 않는다"})
            continue
        if status == "adjudicated" and gid not in done:
            out.append({**base, "verdict": "CLOSED", "severity": "info",
                        "detail": f"판정 완료: {g.get('adjudicated_at')} — {g.get('outcome','')}"})
            continue
        if gid in done:
            rec = done[gid]
            out.append({**base, "verdict": "CLOSED", "severity": "info",
                        "detail": f"판정 원장 기록: {rec.get('adjudicated_at')} — {rec.get('outcome','')}"})
            continue
        pre = _precondition_state(root, g.get("precondition"))
        if not pre["met"]:
            out.append({**base, "verdict": "BLOCKED", "severity": "info",
                        "precondition_verified": pre["verified"],
                        "detail": f"선행조건 미충족 — {pre['detail']}"})
            continue
        out.append({**base, "verdict": "OVERDUE", "severity": str(g.get("severity", "warn")),
                    "precondition_verified": pre["verified"],
                    "adjudication_record": g.get("adjudication_record"),
                    "detail": f"판정할 때가 됐는데 기록이 없다 — {pre['detail']} · "
                              f"기록처: {g.get('adjudication_record','미지정')}",
                    "on_fire": g.get("on_fire")})
    return out


def check_prereg_reopen_conditions(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """재개봉 조건 (OD-51). 킬 기준의 거울상이고 똑같이 아무도 다시 읽지 않는다.

    등록이 없으면 누군가 **"표본 쌓였으니 다시 켜자"** 로 되살린다. 재개봉은 "표본이 쌓이면"이
    아니라 **"측정 자체가 유효해지면"** 이다.
    """
    out: List[Dict[str, Any]] = []
    for item in (cfg.get("prereg_reopen_conditions") or []):
        conds = item.get("conditions") or []
        checkable = [c for c in conds if c.get("machine_readable") is not False]
        unmet = [c["id"] for c in checkable if not c.get("met")]
        manual = [c["id"] for c in conds if c.get("machine_readable") is False]
        ready = not unmet
        out.append({
            "check": "prereg_reopen", "id": item.get("id"), "applies_to": item.get("applies_to"),
            "verdict": "READY_FOR_REVIEW" if ready else "NOT_REOPENABLE",
            "severity": "warn" if ready else "info",
            "unmet": unmet, "manual_only": manual,
            "detail": (f"미충족 {unmet} · 술어화 불가 {manual}" if unmet
                       else f"전 조건 충족 — 재연구 검토 대상(발행 재개 아님) · 술어화 불가 {manual}"),
        })
    return out


def check_prereg_kill_criteria(cfg: Dict[str, Any], root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """OD-19 대조 + OD-47(등록과 평가기는 같은 변경에 들어간다).

    **등록만 하고 세기만 하면 판정이 초록인데 검사는 없는 상태가 된다** — 이 리포의 상습
    실패 형태다(부분 가드가 무가드보다 조용했고, 중지 선언이 no-op 이었다). 그래서 평가할 수
    없는 항목은 통과가 아니라 `NOT_EVALUATED` 로 낸다.

    OD-48: 일회형(트랙 종료 관문)은 상시 술어와 섞지 않는다 — 매일 같은 답을 내는 가짜 감시가 된다.
    """
    reg = cfg.get("prereg_kill_criteria") or []
    if not reg:
        return [{"check": "prereg_kill_criteria", "verdict": "NONE_REGISTERED", "severity": "warn",
                 "detail": "기계 판독 가능한 사전등록 킬 기준이 0건이다 — OD-19 가 요구하는 "
                           "매일 대조가 성립하지 않는다"}]
    root = root or PROJECT_ROOT
    out: List[Dict[str, Any]] = []
    for item in reg:
        cid = item.get("id", "?")
        base = {"check": "prereg_kill_criteria", "id": cid,
                "narrowing": bool(item.get("narrowing")), "kind": item.get("kind", "standing")}
        status = str(item.get("status", "active"))
        if status == "blocked":
            out.append({**base, "verdict": "BLOCKED", "severity": "info",
                        "detail": f"{item.get('blocked_by')} — 해제 시 평가한다: {item.get('unblock_when','')}"})
            continue
        chk = item.get("check")
        if not isinstance(chk, dict) or chk.get("type") not in KC_EVALUATORS:
            out.append({**base, "verdict": "NOT_EVALUATED", "severity": "warn",
                        "detail": f"평가기가 없는 술어(type={None if not isinstance(chk, dict) else chk.get('type')}) "
                                  f"— 등록만으로는 대조가 아니다"})
            continue
        try:
            res = KC_EVALUATORS[chk["type"]](root, chk)
        except Exception as exc:                                   # pragma: no cover
            out.append({**base, "verdict": "EVAL_ERROR", "severity": "warn",
                        "detail": f"{type(exc).__name__}: {exc}"})
            continue
        if res["fired"] is None:
            verdict, sev = "UNDECIDED", "warn"
        elif res["fired"]:
            verdict, sev = "FIRED", str(item.get("severity", "alert"))
        else:
            verdict, sev = "OK", "info"
        out.append({**base, "verdict": verdict, "severity": sev,
                    "observed": res.get("observed"), "detail": res["detail"],
                    "on_fire": item.get("on_fire") if verdict == "FIRED" else None})
    unreadable = cfg.get("prereg_kill_criteria_not_machine_readable") or []
    if unreadable:
        out.append({"check": "prereg_kill_criteria", "id": "not_machine_readable",
                    "verdict": "NOT_MACHINE_READABLE", "severity": "warn", "count": len(unreadable),
                    "detail": f"술어화 불가로 남긴 {len(unreadable)}건 — 목록으로만 존재한다"})
    return out


# ---------------------------------------------------------------------------

def run(root: Path, cfg: Dict[str, Any], today: str, state: Dict[str, Any]) -> Dict[str, Any]:
    suspensions = _gate_suspensions(root)
    expired = expired_suspension_lanes(root, cfg, today)      # OD-49: 면제보다 먼저
    findings = check_firing_qualification(root, cfg, today, suspensions, expired)
    findings += check_qualification_transition(findings, state)
    findings += check_suspension_deadlines(root, cfg, today)
    findings += check_artifact_freshness(root, cfg, today)
    findings += check_prereg_kill_criteria(cfg, root)
    findings += check_prereg_track_gates(cfg, root)
    findings += check_prereg_reopen_conditions(cfg)
    worst = max((SEV_ORDER.get(f.get("severity", "info"), 0) for f in findings), default=0)
    cal = {m: trading_days(root, m, today) for m in ("KR", "US")}

    # OD-44: 이 산출이 발행 경로의 입력이 된다(OD-34 적용). **fail-closed 계약** —
    # 파일이 없거나 낡으면 "통과"로 읽히면 안 된다. 소비자가 그걸 판단할 수 있도록
    # 신선도 근거를 함께 싣고, 사이징 허용 여부를 파생시키지 말고 명시한다.
    #   · 지도에 없는 레인은 **불허**로 읽어야 한다(빠진 레인이 통과가 되면 안 된다)
    #   · allowed=true 는 "OD-34 발화 자격을 통과했다"만 뜻한다. OD-1 자격·게이트 판정 등
    #     다른 조건은 여기서 판정하지 않는다.
    lane_sizing = {}
    for f in findings:
        if f.get("check") != "firing_qualification" or not f.get("lane"):
            continue
        lane_sizing[f["lane"]] = {
            "allowed": f["verdict"] in ("PASS", "GRACE", "EXEMPT"),
            "verdict": f["verdict"], "reason": f.get("detail", ""),
        }
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "today": today,
        "freshness": {
            "last_trading_day": {m: (v[-1] if v else None) for m, v in cal.items()},
            "max_age_hours": MAX_AGE_HOURS,
            "contract": ("fail-closed: 이 파일이 없거나 generated_at 이 max_age_hours 를 넘으면 "
                         "통과로 읽지 말 것. lane_sizing 에 없는 레인도 불허로 읽을 것."),
        },
        "lane_sizing": lane_sizing,
        "trading_days": {m: len(v) for m, v in cal.items()},
        "worst_severity": [k for k, v in SEV_ORDER.items() if v == worst][0],
        "escalations": [f for f in findings if SEV_ORDER.get(f.get("severity", "info"), 0) >= 2],
        "findings": findings,
    }


def _escalation_markdown(report: Dict[str, Any]) -> str:
    lines = [f"# sentinel 에스컬레이션 — {report['today']}", "",
             f"생성 {report['generated_at']} · 최고 심각도 **{report['worst_severity']}**",
             f"거래일(데이터 유래) KR {report['trading_days']['KR']} · US {report['trading_days']['US']}", ""]
    esc = report["escalations"]
    if not esc:
        lines += ["에스컬레이션 없음."]
    else:
        lines += ["| 검사 | 대상 | 판정 | 상세 |", "|---|---|---|---|"]
        for f in esc:
            who = f.get("lane") or f.get("id") or f.get("path") or "-"
            lines.append(f"| {f['check']} | {who} | **{f['verdict']}** | {f.get('detail','')} |")
    lines += ["", "## 전체 판정", "", "| 검사 | 대상 | 판정 | 심각도 | 상세 |", "|---|---|---|---|---|"]
    for f in report["findings"]:
        who = f.get("lane") or f.get("id") or f.get("path") or "-"
        lines.append(f"| {f['check']} | {who} | {f['verdict']} | {f.get('severity')} | {f.get('detail','')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--repo-root", default=str(PROJECT_ROOT))
    ap.add_argument("--today", default="")
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    root = Path(args.repo_root)
    today = args.today or _today()
    state = _load_state()
    report = run(root, cfg, today, state)

    if not args.no_write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        # 에스컬레이션은 파일로 남긴다 — 메시지는 승인 대기로 만료돼 사라진 적이 여러 번이다.
        OUT_MD.write_text(_escalation_markdown(report), encoding="utf-8")
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({
            "updated_at": report["generated_at"],
            "firing_verdicts": {f["lane"]: f["verdict"] for f in report["findings"]
                                if f["check"] == "firing_qualification" and f.get("lane")},
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({"worst_severity": report["worst_severity"],
                      "escalations": len(report["escalations"]),
                      "findings": len(report["findings"])}, ensure_ascii=False))
    if not args.json_only:
        for f in report["findings"]:
            mark = "⚠️" if SEV_ORDER.get(f.get("severity", "info"), 0) >= 2 else "  "
            who = f.get("lane") or f.get("id") or f.get("path") or "-"
            print(f"{mark} [{f['check']}] {who}: {f['verdict']} — {f.get('detail','')}")
    return 1 if report["escalations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
