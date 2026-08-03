"""§39 섹터동반 항복 (2026-08-04, 운영자 승인 배포 — swing-main-pwen).

근거 (RESEARCH_LOG §39, 사전등록 1분할 + 8y 일반화 통과):
  진앙지(섹터 60d수익 하위 1/4) 항복  : 크래시 +1.73 CI[+1.36,+2.15] 터치69% / 8y +1.44 CI[+1.27,+1.62]
  비진앙(상위 1/2) 항복              : 크래시 −0.17 / 8y +1.12
  → §24의 프랙탈 확장: 종목이 시장과 함께 무너져야 하듯, 섹터와 함께 무너져야 반등이 진짜다.
     버틴 섹터의 단독 폭락 = 섹터 수준 고유하락 = 정보성(악재) — 2026-07 랭커 출혈의 원인 셀.

제공: 픽 태그/발행 차등용 sec_q 조회 + 나침반 섹터 로테이션 패널. soft 계층 — 계약/원장 불변,
라벨과 사이징 권고 차등만. 롤백: AG_SECTOR_CAPITULATION=0.
섹터 정의: px_long `industry`(KRX 업종, ~160개), 최소 5종목 업종만 분위 계산.
sec_q = 업종 60d 동일가중 수익의 업종 간 분위 (0=최악=진앙지). §39 임계: 진앙 q<=0.25, 비진앙 q>0.5.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

_CACHE: Dict[str, Any] = {"mtime": None, "by_code": {}, "sectors": []}
_PX = os.path.expanduser("~/research_cache/px_long.parquet")
MIN_SECTOR_N = 5
EPICENTER_Q = 0.25   # §39 사전등록 분할
RESILIENT_Q = 0.50


def _refresh() -> None:
    mtime = os.path.getmtime(_PX) if os.path.exists(_PX) else None
    if mtime is None or _CACHE["mtime"] == mtime:
        return
    import pandas as pd
    px = pd.read_parquet(_PX, columns=["code", "date", "market", "industry", "close"])
    px["date"] = pd.to_datetime(px["date"])
    latest = px["date"].max()
    win = px[px["date"] >= latest - pd.Timedelta(days=130)].sort_values("date")
    g = win.groupby("code")
    first, last = g["close"].first(), g["close"].last()
    meta = g[["industry", "market"]].last()
    # 종목 60d(≈130달력일) 수익 → 업종 동일가중 평균
    r = ((last / first - 1) * 100).rename("ret60")
    df = meta.join(r).dropna(subset=["ret60"])
    df = df[df["industry"].notna() & (df["industry"] != "NA")]
    sec = df.groupby("industry").agg(ret60=("ret60", "mean"), n=("ret60", "size"))
    sec = sec[sec["n"] >= MIN_SECTOR_N]
    sec["sec_q"] = sec["ret60"].rank(pct=True)   # 0=최악(진앙지)
    # 20d도 로테이션 패널용
    win20 = px[px["date"] >= latest - pd.Timedelta(days=45)].sort_values("date")
    g20 = win20.groupby("code")["close"]
    r20 = ((g20.last() / g20.first() - 1) * 100).rename("ret20")
    sec20 = df.join(r20).groupby("industry")["ret20"].mean()
    sec = sec.join(sec20)
    by_code = {}
    for code, row in df.iterrows():
        ind = row["industry"]
        if ind in sec.index:
            s = sec.loc[ind]
            by_code[str(code)] = {"industry": ind, "sec_q": round(float(s["sec_q"]), 3),
                                  "sec_ret60": round(float(s["ret60"]), 1)}
    sectors = [{"industry": ind, "ret60": round(float(s["ret60"]), 1),
                "ret20": round(float(s["ret20"]), 1) if s["ret20"] == s["ret20"] else None,
                "sec_q": round(float(s["sec_q"]), 3), "n": int(s["n"])}
               for ind, s in sec.iterrows()]
    _CACHE.update(mtime=mtime, by_code=by_code, sectors=sectors, asof=str(latest.date()))


def sec_q_of(code: str) -> Optional[Dict[str, Any]]:
    """종목 → {industry, sec_q(0=진앙), sec_ret60} 또는 None(미분류/데이터 없음). fail-safe."""
    try:
        _refresh()
        return _CACHE["by_code"].get(str(code).split(".")[0].zfill(6))
    except Exception:
        return None


def classify_capitulation(code: str) -> Optional[str]:
    """항복픽의 섹터 문맥: 'epicenter'(q<=0.25) / 'resilient'(q>0.5) / 'mid' / None."""
    s = sec_q_of(code)
    if not s:
        return None
    q = s["sec_q"]
    return "epicenter" if q <= EPICENTER_Q else ("resilient" if q > RESILIENT_Q else "mid")


def rotation_panel(top_n: int = 6) -> Optional[Dict[str, Any]]:
    """나침반용 섹터 로테이션: 20d 상위(신 리더십) / 60d 하위(진앙지) 업종. fail-safe."""
    try:
        _refresh()
        secs = [s for s in _CACHE["sectors"] if s.get("ret20") is not None]
        if not secs:
            return None
        lead = sorted(secs, key=lambda s: -s["ret20"])[:top_n]
        epi = sorted(secs, key=lambda s: s["sec_q"])[:top_n]
        return {"asof": _CACHE.get("asof"),
                "leadership_20d": lead, "epicenter_60d": epi,
                "note": "§39: 진앙지(60d 하위 1/4) 항복만 반등코어 — 버틴 섹터의 단독 폭락은 정보성(회피)"}
    except Exception:
        return None
