#!/usr/bin/env python3
"""미채점 행이 임계를 넘겼는지 매일 대조한다 (F6, swing-main-r6sb).

배경: 원장에 채점되지 않은 행이 쌓여도 **경보가 없었다.** `kr_swing_candidate_ledger` 213행 중
46행이 미채점이고 그중 1건은 32일 경과(임계 10일)로 20회 넘는 런 동안 조용히 실패하고 있었다.

왜 아무도 못 봤나 — 세 겹이 전부 침묵한다:
  · resolver 가 전부 bare except 라 실패가 예외로 드러나지 않는다
  · 재시도 상한도 dead-letter 도 없어 실패한 행이 그냥 다음 런으로 넘어간다
  · `report_data_manifest.py` 는 원장의 **최신 date** 만 본다 — 새 행이 계속 들어오면
    개별 행의 미채점은 신선도 지표에 잡히지 않는다

**이 침묵이 7,171건 만료의 상류다.** 경보가 있었으면 두 달을 방치하지 않았다.

## 대상은 게이트 LANES 에서 가져온다

원장 경로·값 필드·날짜 필드를 여기서 따로 적으면 두 벌이 갈린다 — 이 리포가 반복해서 낸
사고가 정확히 그것이다(HEALTHY_VERDICTS 어휘 드리프트, 소비자 간 동결값 불일치).
게이트가 판정에 쓰는 그 정의를 그대로 쓴다.

## 임계 10일의 근거

원장에 실제로 존재하는 최대 지평이 T+5D 이고(만료 7,413건 전수: T+1D/2D/3D/5D), 정산기의
`--min-age-days` 기본이 3일이며, 주말·휴장 지연 2일을 더해 10일이다. 이보다 오래 미채점인
행은 "아직 안 익은 것"이 아니라 **파이프가 그 행을 놓친 것**이다.

  python3 multi_agent/tools/report_unresolved_outcome_staleness.py
  python3 multi_agent/tools/report_unresolved_outcome_staleness.py --stale-days 14 --json-only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.report_research_recursion_gate import (  # noqa: E402
    LANES, _row_date, _rows,
)

STALE_DAYS_DEFAULT = 10
OUT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "unresolved_staleness_latest.json"


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def scan_lane(name: str, cfg: Dict[str, Any], today: dt.date, stale_days: int) -> Dict[str, Any]:
    """한 레인의 미채점 행을 나이별로 센다.

    판정 범위(`publish_scope`)나 정지 배제는 **적용하지 않는다** — 그것들은 "무엇으로 판정할
    것인가"의 문제이고, 여기서 묻는 것은 "채점 파이프가 이 행을 처리했는가"다. 발행되지 않는
    픽도 채점은 돼야 한다.
    """
    field, dfield = cfg["field"], cfg.get("date_field", "date")
    rows = _rows(cfg["ledger"])
    unresolved: List[Dict[str, Any]] = []
    undated = 0
    for row in rows:
        if isinstance(row.get(field), (int, float)):
            continue
        iso = _row_date(row, dfield)
        if not iso:
            undated += 1
            continue
        try:
            age = (today - dt.date.fromisoformat(iso)).days
        except ValueError:
            undated += 1
            continue
        unresolved.append({"date": iso, "age_days": age, "ticker": row.get("ticker")})
    stale = [u for u in unresolved if u["age_days"] > stale_days]
    stale.sort(key=lambda u: -u["age_days"])
    return {
        "lane": name, "ledger": str(cfg["ledger"]), "field": field,
        "rows": len(rows), "unresolved": len(unresolved), "undated": undated,
        "stale": len(stale), "stale_days": stale_days,
        "max_age_days": max((u["age_days"] for u in unresolved), default=0),
        "worst": stale[:5],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS_DEFAULT)
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    today = _today()
    results = [scan_lane(n, c, today, args.stale_days) for n, c in LANES.items()]
    # 원장 경로가 같은 레인(b 두 개)은 같은 파일을 두 번 세므로 파일 단위로 접는다
    seen: Dict[str, Dict[str, Any]] = {}
    for r in results:
        seen.setdefault(r["ledger"], r)
    total_stale = sum(r["stale"] for r in seen.values())
    breached = sorted((r for r in seen.values() if r["stale"]), key=lambda r: -r["stale"])

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stale_days": args.stale_days,
        "total_stale": total_stale,
        "breached_ledgers": [r["lane"] for r in breached],
        "lanes": results,
    }
    if not args.no_write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: payload[k] for k in
                      ("stale_days", "total_stale", "breached_ledgers")}, ensure_ascii=False))
    if not args.json_only:
        for r in results:
            mark = "⚠️" if r["stale"] else "  "
            print(f"{mark} {r['lane']:22s} 행 {r['rows']:5d} · 미채점 {r['unresolved']:4d} · "
                  f"{args.stale_days}일초과 {r['stale']:3d} · 최대경과 {r['max_age_days']:3d}일")
            for w in r["worst"]:
                print(f"     └ {w['date']} ({w['age_days']}일) {w.get('ticker') or ''}")
    # 임계 초과가 있으면 실패로 끝낸다. 이 리포의 사고는 전부 "카운트는 남았는데 아무도
    # 읽지 않은 것"이라, 세어만 두고 0 으로 끝내면 같은 침묵을 하나 더 만드는 것이다.
    return 1 if total_stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
