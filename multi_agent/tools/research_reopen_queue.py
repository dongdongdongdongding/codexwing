#!/usr/bin/env python3
"""연구 재개봉 큐 — "표본 부족 보류" 실험이 데이터 성숙 시 자동으로 다시 열린다.

각 항목: 사전등록 가설 + 재개봉 조건(데이터 행수/일수). 조건 충족 시 bd 티켓 1회 발행
(state 파일 dedup). daily ops 등록 — 사람이 기억하지 않아도 연구 큐가 스스로 깨어난다.

  python3 multi_agent/tools/research_reopen_queue.py [--no-tickets]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
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


META_LEDGERS = (
    ("kospi_intraday_swing_ledger.jsonl", "exit_t5_h5"),
    ("kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5"),
    ("kr_swing_candidate_ledger.jsonl", "policy_ret"),
)


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _ledger_evidence(rel: str, field: str) -> dict:
    fp = PROJECT_ROOT / rel
    result = {"path": rel, "field": field, "resolved": 0,
              "regimes": {}, "contracts": {}, "malformed_rows": 0}
    if not fp.exists():
        return {**result, "missing": True}
    raw = fp.read_bytes()
    result["sha256"] = hashlib.sha256(raw).hexdigest()
    regimes, contracts = Counter(), Counter()
    for ln in raw.decode("utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
                if not isinstance(row, dict):
                    raise ValueError("ledger row must be an object")
                if _finite_number(row.get(field)):
                    result["resolved"] += 1
                    regimes[str(row.get("mkt_state") or "UNKNOWN")] += 1
                    contracts[json.dumps({k: row.get(k) for k in
                        ("contract", "contract_h", "contract_tp", "contract_top_k",
                         "hold_days", "target_tp_pct", "stop_sl_pct")},
                        sort_keys=True, ensure_ascii=False)] += 1
            except (ValueError, TypeError):
                result["malformed_rows"] += 1
    result.update(regimes=dict(regimes), contracts=dict(contracts))
    return result


def _ledger_resolved(rel: str, field: str) -> int:
    return _ledger_evidence(rel, field)["resolved"]


def _meta_evidence() -> dict:
    ledgers = [_ledger_evidence("runtime_state/reports/experimental/" + name, field)
               for name, field in META_LEDGERS]
    regimes = Counter()
    for ledger in ledgers:
        regimes.update(ledger["regimes"])
    # §40 A4 specifies accumulation outside RISK_OFF, but no numeric minimum.
    # Recognized NORMAL/RISK_ON observations establish presence only, not fit quality.
    return {"resolved": sum(x["resolved"] for x in ledgers),
            "known_non_risk_off": sum(regimes[k] for k in ("NORMAL", "RISK_ON")),
            "regimes": dict(regimes), "ledgers": ledgers,
            "scope": "acquisition_readiness_only_mixed_lanes_and_contracts",
            "fit_requires": ["contract_and_epoch_audit", "pick_time_features",
                             "settlement_validity", "independent_validation"],
            "h10_tp5_probability_verified": False, "promotion_allowed": False}


def _lanes_resolved_total() -> int:
    return _meta_evidence()["resolved"]


def _nasdaq_current_resolved() -> int:
    from modules.nasdaq_epoch_evidence import current_rows, statistics
    fp = PROJECT_ROOT / "runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl"
    rows = [json.loads(line) for line in fp.read_text().splitlines() if line.strip()] if fp.exists() else []
    return statistics(current_rows(rows))["n"]


# 사전등록: 가설·조건·근거. 조건 함수는 지연 평가.
QUEUE: Dict[str, Dict[str, Any]] = {
    # short_squeeze_hypothesis: 제거(2026-08-05, §40 킬대조 후속) — 등록 당일 §23이 8.7y 백필로
    # 두 가설(급증×항복 H-A, 피크아웃 H-B) 모두 킬 완료(informed shorts 보조정리). 큐 좀비였음.
    # 공매도 축 잔여는 분봉/이벤트 입도 재탐사감으로만 보류(§23 명시).
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
    "live_meta_calibration_full": {
        "need": 200, "have": _lanes_resolved_total,
        "title": "[재개봉] 라이브 메타 캘리브레이션 2차 (200건 및 비RISK_OFF 관측)",
        "desc": "OD-55/§38의 독립된 200건 단계 및 §40 A4의 비RISK_OFF 축적 조건. "
                "원장 합계는 수집 재개 조건일 뿐 동일 계약/H10 학습 표본이 아니다. "
                "원장별 계약·epoch·정산·픽 시점 피처 감사를 먼저 수행하고 유효 표본으로 "
                "기존 사전등록 비교(시드3+노이즈 대조)를 재평가한다. 비RISK_OFF 수치 하한은 "
                "기존 등록에 없으므로 관측 존재만 확인하며 충분성은 별도 판정. "
                "승격·발행·70% 확률 인정 권한을 부여하지 않는다.",
    },
    "nasdaq_tape_verdict_deep": {
        "need": 30, "have": _nasdaq_current_resolved,
        "title": "[재개봉] 나스닥 테이프 forward 판정 + 어닝스 메타 (현행 구성 정산 30건 도달)",
        "desc": "사전등록: 게이트 판정과 별도로 어닝스 근접 조건부 성과 분해(£12-D 후속). CONFIRM 시 실자본 승격 검토 재료.",
    },
}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8",
                                     delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def run_queue(*, no_tickets: bool = False) -> dict:
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        state = {}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "items": []}
    meta = None
    for key, cfg in QUEUE.items():
        evidence = None
        try:
            if key in ("live_meta_calibration", "live_meta_calibration_full"):
                if meta is None:
                    meta = _meta_evidence()
                evidence = meta
                have = meta["resolved"]
            else:
                have = int(cfg["have"]())
        except Exception:
            have = -1
        ready = have >= cfg["need"]
        if key == "live_meta_calibration_full":
            ready = ready and bool(evidence and evidence["known_non_risk_off"] > 0)
        item = {"key": key, "have": have, "need": cfg["need"],
                "ready": ready, "ticketed": bool(state.get(key))}
        if evidence is not None:
            item["evidence"] = evidence
        report["items"].append(item)
        if ready and not state.get(key) and not no_tickets:
            try:
                r = subprocess.run([os.environ.get("BD_BIN", "/Users/dongdong/.local/bin/bd"), "create", f"--title={cfg['title']}",
                                    f"--description={cfg['desc']} (재개봉 큐 자동 발행: {have}/{cfg['need']})",
                                    "--type=task", "--priority=1"],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    state[key] = datetime.now(timezone.utc).isoformat()
                    item["ticketed"] = True
            except Exception:
                pass
    _write_json(STATE, state)
    _write_json(OUT, report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tickets", action="store_true")
    args = ap.parse_args()
    # Serialize scheduled/manual invocations so the per-stage dedup state is shared.
    import fcntl
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        report = run_queue(no_tickets=args.no_tickets)
    print(json.dumps({i["key"]: f"{i['have']}/{i['need']}" + (" READY" if i["ready"] else "")
                      for i in report["items"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
