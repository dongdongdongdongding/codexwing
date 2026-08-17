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

# 레인 → (원장 상대경로, 날짜 필드, 시장). 게이트 LANES 와 같은 원장을 본다.
LANE_LEDGERS = {
    "kospi_intraday_t5": ("runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl", "date", "KR"),
    "kosdaq_intraday_t10": ("runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "date", "KR"),
    "swing_candidate": ("runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl", "date", "KR"),
    "b_primary_top3": ("b_engine/data/b_shadow.jsonl", "scan_date", "KR"),
    "b_all_top10": ("b_engine/data/b_shadow.jsonl", "scan_date", "KR"),
    "nasdaq_session_tape": ("runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl", "date", "US"),
}
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
    """거래일을 **데이터에서** 유래시킨다. 당일은 미완결이라 제외한다."""
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

def check_firing_qualification(root: Path, cfg: Dict[str, Any], today: str,
                               suspensions: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """OD-34 발화 자격 + OD-39(마커 없는 정지는 면제 아님)."""
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

        if suspended:
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
            "action": "block_sizing" if verdict == "FAIL" else None,
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


def check_prereg_kill_criteria(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """OD-19. 기계 판독 가능한 킬 기준만 대조할 수 있다."""
    reg = cfg.get("prereg_kill_criteria") or []
    if not reg:
        return [{"check": "prereg_kill_criteria", "verdict": "NONE_REGISTERED", "severity": "warn",
                 "detail": "기계 판독 가능한 사전등록 킬 기준이 0건이다 — OD-19 가 요구하는 "
                           "매일 대조가 아직 성립하지 않는다(등록되면 여기서 판정한다)"}]
    return [{"check": "prereg_kill_criteria", "verdict": "REGISTERED", "severity": "info",
             "count": len(reg), "detail": f"{len(reg)}건 등록됨"}]


# ---------------------------------------------------------------------------

def run(root: Path, cfg: Dict[str, Any], today: str, state: Dict[str, Any]) -> Dict[str, Any]:
    suspensions = _gate_suspensions(root)
    findings = check_firing_qualification(root, cfg, today, suspensions)
    findings += check_qualification_transition(findings, state)
    findings += check_suspension_deadlines(root, cfg, today)
    findings += check_artifact_freshness(root, cfg, today)
    findings += check_prereg_kill_criteria(cfg)
    worst = max((SEV_ORDER.get(f.get("severity", "info"), 0) for f in findings), default=0)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "today": today,
        "trading_days": {m: len(trading_days(root, m, today)) for m in ("KR", "US")},
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
