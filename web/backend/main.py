"""신웹 백엔드 (FastAPI) — React 프론트에 JSON 제공. 기존 모듈 재사용·재계산 없음.

실행: python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8800 --reload
정직 원칙: 모든 응답에 데이터 신선도/배지 정보 포함. 비밀키는 백엔드만(.env.local).
"""
from __future__ import annotations
import os
from fastapi import FastAPI, Query, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from web.backend import services as S
from web.backend import jobs
from web.backend import scans as SC

# --- 배포 보안 (터널로 공개 노출시 필수) -------------------------------------
# CORS: WEB_ALLOWED_ORIGINS(콤마구분, 예: https://xxx.vercel.app)로 제한. 미설정시 * (로컬).
_origins = [o.strip() for o in os.getenv("WEB_ALLOWED_ORIGINS", "").split(",") if o.strip()] or ["*"]
# 토큰: WEB_API_TOKEN 설정시 모든 요청에 Authorization: Bearer <token> 요구. 미설정시 무인증(로컬).
_API_TOKEN = os.getenv("WEB_API_TOKEN", "").strip()


def require_token(authorization: str = Header(default="")):
    if not _API_TOKEN:
        return  # 로컬 개발 = 무인증
    if authorization != f"Bearer {_API_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


app = FastAPI(title="SWING 신웹 API", version="0.1", dependencies=[Depends(require_token)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
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


@app.get("/api/buy-timing")
def buy_timing(days: int = Query(5, ge=1, le=5)):
    return S.buy_timing(days)


@app.get("/api/performance")
def performance():
    return S.performance()


@app.get("/api/contract-performance")
def contract_performance():
    """계약 실현 성과 — 승격 계약(터치익절)의 자동 채점 (exit shadow + 선별 뷰 + 스윙 후보)."""
    return S.contract_performance()


@app.get("/api/market")
def market():
    return S.market()


@app.get("/api/theme")
def theme():
    return S.theme()


@app.get("/api/scans")
def scans(limit: int = 40, source: str = "", market: str = ""):
    return SC.list_scans(limit=limit, source=source or None, market=market or None)


@app.get("/api/scans/{scan_id}")
def scan_detail(scan_id: str):
    return SC.scan_detail(scan_id)


@app.get("/api/scans/{scan_id}/analyze/{ticker}")
def scan_analyze(scan_id: str, ticker: str):
    return SC.scan_analyze(scan_id, ticker)


@app.get("/api/ops/status")
def ops_status():
    return S.ops_status()


@app.get("/api/ops/scan")
def scan_status():
    return jobs.status()


@app.get("/api/ops/scan-targets")
def scan_targets():
    return {"targets": jobs.targets()}


@app.post("/api/ops/scan")
def scan_start(target: str = Query("all", description="kospi_swing|kosdaq_swing|nasdaq_swing|kospi_intraday|kosdaq_intraday|b|kospi_all|kosdaq_all|all")):
    return jobs.start(target or "all")


@app.get("/api/archive")
def archive(date_from: str = "", date_to: str = "", market: str = "", ticker: str = "", limit: int = 200, offset: int = 0):
    return S.archive(date_from or None, date_to or None, market or None, ticker or None, limit, offset)


@app.get("/api/lanes")
def lanes():
    """레인 메타(프론트 필터용)."""
    out = [{"key": k, **{kk: v[kk] for kk in ("label", "kind", "badge")}} for k, v in S.LANES.items()]
    out.append({"key": "nasdaq_swing", "label": "나스닥 스윙", "kind": "SWING", "badge": "🟢"})
    out.append({"key": "b_market_neutral", "label": "B 시장중립", "kind": "B", "badge": "🟣"})
    return {"lanes": out}


@app.get("/")
def root():
    return JSONResponse({"service": "SWING 신웹 API", "docs": "/docs",
                         "endpoints": ["/api/overview", "/api/picks", "/api/prices", "/api/lanes", "/api/health/freshness"]})
