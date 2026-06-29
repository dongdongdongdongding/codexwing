"""신웹 백엔드 (FastAPI) — React 프론트에 JSON 제공. 기존 모듈 재사용·재계산 없음.

실행: python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8800 --reload
정직 원칙: 모든 응답에 데이터 신선도/배지 정보 포함. 비밀키는 백엔드만(.env.local).
"""
from __future__ import annotations
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from web.backend import services as S
from web.backend import jobs

app = FastAPI(title="SWING 신웹 API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발: React dev서버(5173). 운영선 도메인 제한.
    allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "freshness": S.freshness()}


@app.get("/api/overview")
def overview(top: int = 6):
    return S.overview(top=top)


@app.get("/api/picks")
def picks(lane: str = Query("", description="kospi_swing|kosdaq_swing|kospi_intraday|kosdaq_intraday|b_market_neutral|'' 전체")):
    rows = S.picks(lane or None)
    return {"lane": lane or "all", "count": len(rows), "picks": rows}


@app.get("/api/prices")
def prices(codes: str = Query("", description="콤마구분 코드")):
    cs = [c for c in codes.split(",") if c.strip()]
    return S.prices(cs) if cs else {}


@app.get("/api/health/freshness")
def freshness():
    return S.freshness()


@app.get("/api/chart")
def chart(code: str, tf: str = Query("day", description="day|minute"), days: int = 120):
    return S.chart(code, tf=tf, days=days)


@app.get("/api/picks/{code}")
def pick_detail(code: str):
    return S.pick_detail(code)


@app.get("/api/analyze/{code}")
def analyze(code: str):
    return S.analyze(code)


@app.get("/api/performance")
def performance():
    return S.performance()


@app.get("/api/market")
def market():
    return S.market()


@app.get("/api/theme")
def theme():
    return S.theme()


@app.get("/api/ops/status")
def ops_status():
    return S.ops_status()


@app.get("/api/ops/scan")
def scan_status():
    return jobs.status()


@app.post("/api/ops/scan")
def scan_start(market: str = Query("", description="KOSPI|KOSDAQ|'' 전체")):
    return jobs.start(market or "")


@app.get("/api/archive")
def archive(date_from: str = "", date_to: str = "", market: str = "", ticker: str = "", limit: int = 200, offset: int = 0):
    return S.archive(date_from or None, date_to or None, market or None, ticker or None, limit, offset)


@app.get("/api/lanes")
def lanes():
    """레인 메타(프론트 필터용)."""
    out = [{"key": k, **{kk: v[kk] for kk in ("label", "kind", "badge")}} for k, v in S.LANES.items()]
    out.append({"key": "b_market_neutral", "label": "B 시장중립", "kind": "B", "badge": "🟣"})
    return {"lanes": out}


@app.get("/")
def root():
    return JSONResponse({"service": "SWING 신웹 API", "docs": "/docs",
                         "endpoints": ["/api/overview", "/api/picks", "/api/prices", "/api/lanes", "/api/health/freshness"]})
