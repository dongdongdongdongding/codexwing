#!/usr/bin/env python3
"""PKG-C ④ (§40): KIS 장중 잠정수급 스냅샷 적재 — 백필 불가 자산, 오늘부터 시계가 돈다.

배경: 외인/기관 잠정 수급은 거래소가 09:30(외인만)/10:00/11:30/13:20/14:30에 공표하고
KIS 엔드포인트 3종이 어댑터에 등록돼 있었으나 소비 코드가 0이었다(§40 감사). 이 데이터는
백필이 불가능하므로 '수집 개시 결정'을 미룰수록 미래 검증 가능 시점이 밀린다. 이 수집기는
관측 전용 적재만 한다 — 피처/게이트 주장 금지(§5-A 수급증분 킬 전례, 재도전 시 사전등록 필수).

수집 (호출 예산 ~41콜/회, 실전 초당 20건 한도 내):
  - foreign_institution_total: 시장 전체 외인/기관 매매종목가집계 (1콜)
  - investor_trend_estimate: 유동 상위 N종목(기본 40) 종목별 외인/기관 추정가집계
적재: ~/research_cache/investor_estimate/YYYYMM.jsonl — {ts_kst, round, kind, symbol?, payload}
  round = 직전 공표 회차(0930/1000/1130/1320/1430) — 확정치(장후) 대조 조인 키.
게이트: KIS_ENABLE_LIVE_CALLS=1 필요, 주말/장외 시간 자동 스킵. 비활성: AG_INVESTOR_EST=0.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 2026-08-05 수리: launchd 환경에는 KIS 키가 없음 — .env.local 명시 로드 (short_update 패턴).
# 첫 이틀(08-04~05) 수집분은 전 콜 'Missing KIS_APP_KEY' — 시계 시작일은 실질 08-06.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env.local")
except Exception:
    pass

OUT_DIR = Path(os.path.expanduser("~/research_cache/investor_estimate"))
ROUNDS = ["0930", "1000", "1130", "1320", "1430"]


def current_round(now_kst: datetime) -> str | None:
    hm = now_kst.strftime("%H%M")
    past = [r for r in ROUNDS if r <= hm]
    return past[-1] if past else None


def main() -> None:
    if os.environ.get("AG_INVESTOR_EST", "1").strip() not in ("1", "true", "True"):
        print(json.dumps({"skip": "AG_INVESTOR_EST=0"}))
        return
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if now.weekday() >= 5:
        print(json.dumps({"skip": "weekend"}))
        return
    rnd = current_round(now)
    if rnd is None or now.strftime("%H%M") > "1540":
        print(json.dumps({"skip": f"out of session ({now.strftime('%H:%M')})"}))
        return

    from modules.kis_openapi import KISOpenAPIClient  # noqa: E402

    client = KISOpenAPIClient()
    n_syms = int(os.environ.get("AG_INVESTOR_EST_N", "40"))
    records = []

    # 1) 시장 전체 외인/기관 매매종목가집계
    try:
        payload = client.foreign_institution_total(market="ALL")
        records.append({"kind": "foreign_institution_total", "symbol": None, "payload": payload})
    except Exception as exc:
        records.append({"kind": "foreign_institution_total", "symbol": None, "error": repr(exc)[:200]})

    # 2) 유동 상위 N 종목별 추정가집계 (px_long 유동성 중위 상위)
    try:
        import pandas as pd
        px = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"),
                             columns=["code", "date", "liq"])
        px["date"] = pd.to_datetime(px["date"])
        recent = px[px["date"] >= px["date"].max() - pd.Timedelta(days=60)]
        top = recent.groupby("code")["liq"].median().sort_values(ascending=False).head(n_syms).index
        for code in top:
            try:
                payload = client.investor_trend_estimate(str(code))
                records.append({"kind": "investor_trend_estimate", "symbol": str(code), "payload": payload})
            except Exception as exc:
                records.append({"kind": "investor_trend_estimate", "symbol": str(code),
                                "error": repr(exc)[:120]})
    except Exception as exc:
        records.append({"kind": "universe", "error": repr(exc)[:200]})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fp = OUT_DIR / f"{now.strftime('%Y%m')}.jsonl"
    ts = now.isoformat()
    with fp.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps({"ts_kst": ts, "date": now.strftime("%Y-%m-%d"), "round": rnd, **r},
                                ensure_ascii=False) + "\n")
    ok = sum(1 for r in records if "payload" in r)
    print(json.dumps({"date": now.strftime("%Y-%m-%d"), "round": rnd, "written": len(records),
                      "ok": ok, "file": str(fp)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
