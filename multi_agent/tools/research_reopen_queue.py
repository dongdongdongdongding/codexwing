#!/usr/bin/env python3
"""연구 재개봉 큐 — "표본 부족 보류" 실험이 데이터 성숙 시 자동으로 다시 열린다.

각 항목: 사전등록 가설 + 재개봉 조건(데이터 행수/일수). 조건 충족 시 bd 티켓 1회 발행
(state 파일 dedup). daily ops 등록 — 사람이 기억하지 않아도 연구 큐가 스스로 깨어난다.

  python3 multi_agent/tools/research_reopen_queue.py [--no-tickets]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.path.expanduser("~/research_cache"))
STATE = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "reopen_queue_state.json"
OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_reopen_queue_latest.json"


def _short_days() -> int:
    fp = CACHE / "short.parquet"
    if not fp.exists():
        return 0
    import pandas as pd
    return int(pd.read_parquet(fp, columns=["date"])["date"].nunique())


def _ext_days() -> int:
    d = CACHE / "intraday_ext"
    if not d.exists():
        return 0
    import pandas as pd
    fs = sorted(d.glob("*.parquet"))[:5]
    days = set()
    for f in fs:
        try:
            days |= set(pd.to_datetime(pd.read_parquet(f).index).strftime("%Y%m%d"))
        except Exception:
            pass
    return len(days)


def _ledger_resolved(rel: str, field: str) -> int:
    fp = PROJECT_ROOT / rel
    if not fp.exists():
        return 0
    n = 0
    for ln in fp.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                if isinstance(json.loads(ln).get(field), (int, float)):
                    n += 1
            except Exception:
                pass
    return n


def _lanes_resolved_total() -> int:
    return (_ledger_resolved("runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl", "exit_t5_h5")
            + _ledger_resolved("runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5")
            + _ledger_resolved("runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl", "policy_ret"))


# 사전등록: 가설·조건·근거. 조건 함수는 지연 평가.
QUEUE: Dict[str, Dict[str, Any]] = {
    "short_squeeze_hypothesis": {
        "need": 120, "have": _short_days,
        "title": "[재개봉] 공매도 비중 신호: 스퀴즈 연료·비중 전환 (short.parquet 120일 도달)",
        "desc": "사전등록(2026-07-07): ①공매도 비중 급증 × 항복픽 → 스퀴즈 증폭? ②비중 피크아웃 전환 시그널? "
                "검증규율: 시장초과 + 일내셔플 플라시보(서브셋 편향 감지, §18) + 랭커 증분(노이즈 플라시보, §19 측정하한) + 시드3.",
    },
    "ext_session_transfer": {
        "need": 120, "have": _ext_days,
        "title": "[재개봉] 확장세션 가격발견 → 익일 전이 (intraday_ext 120거래일 도달)",
        "desc": "사전등록(2026-07-07): 애프터장(16:00-20:00) 가격/거래 이벤트가 익일 시가·일중에 전이되는가 "
                "(KR판 세션테이프). 현실체결(다음 세션 시가) 필수 — B트랙 갭 아티팩트 교훈. 정규장 대비 증분 판정.",
    },
    "live_meta_calibration": {
        "need": 100, "have": _lanes_resolved_total,
        "title": "[재개봉] 라이브 픽 메타 캘리브레이션 (전 레인 정산 100건 도달)",
        "desc": "사전등록(2026-07-07): 픽 시점 메타피처(티어·레짐·rank gap·시드 분산)로 forward 결과를 예측하는 "
                "2층 캘리브레이터 — 라이브-백테스트 갭 자체를 학습. §19 측정하한 준수(시드3+노이즈 플라시보).",
    },
    "nasdaq_tape_verdict_deep": {
        "need": 30, "have": lambda: _ledger_resolved("runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl", "policy_ret"),
        "title": "[재개봉] 나스닥 테이프 forward 판정 + 어닝스 메타 (정산 30건 도달)",
        "desc": "사전등록: 게이트 판정과 별도로 어닝스 근접 조건부 성과 분해(£12-D 후속). CONFIRM 시 실자본 승격 검토 재료.",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tickets", action="store_true")
    args = ap.parse_args()
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        state = {}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "items": []}
    for key, cfg in QUEUE.items():
        try:
            have = int(cfg["have"]())
        except Exception:
            have = -1
        ready = have >= cfg["need"]
        report["items"].append({"key": key, "have": have, "need": cfg["need"],
                                "ready": ready, "ticketed": bool(state.get(key))})
        if ready and not state.get(key) and not args.no_tickets:
            try:
                r = subprocess.run(["bd", "create", f"--title={cfg['title']}",
                                    f"--description={cfg['desc']} (재개봉 큐 자동 발행: {have}/{cfg['need']})",
                                    "--type=task", "--priority=1"],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    state[key] = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({i["key"]: f"{i['have']}/{i['need']}" + (" READY" if i["ready"] else "")
                      for i in report["items"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
