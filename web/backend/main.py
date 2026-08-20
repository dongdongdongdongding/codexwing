"""신웹 백엔드 (FastAPI) — React 프론트에 JSON 제공. 기존 모듈 재사용·재계산 없음.

실행: python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8800 --reload
정직 원칙: 모든 응답에 데이터 신선도/배지 정보 포함. 비밀키는 백엔드만(.env.local).
"""
from __future__ import annotations
import os
from fastapi import FastAPI, Query, Header, HTTPException, Depends, Request
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


# --- 쓰기(운영 트리거) 경로 = 루프백 전용 ------------------------------------
# 2026-08-15 (trace-b-lane-f7.md §4): 정지된 B 레인에 30건을 쓴 요청 3건이 전부
# 원격 IP(218.232.78.85 / 211.215.170.190)에서 **무인증**으로 들어왔다.
# WEB_API_TOKEN이 .env.example에만 있고 run_web_backend.sh가 export하지 않아
# require_token이 전 요청을 통과시킨다. 조회는 그대로 두고 쓰기만 막는다.
#
# 터널 주의: cloudflared는 로컬(127.0.0.1)에서 백엔드로 붙는다. 소켓 peer IP만 보면
# 터널 경유 원격 요청이 루프백으로 보일 수 있고, uvicorn이 proxy header를 신뢰하도록
# 떠 있으면 반대로 client.host가 실제 원격 IP로 치환된다. 어느 설정에도 기대지 않으려고
# 두 조건을 **동시에** 요구한다: ①peer가 루프백 ②전달 헤더가 하나도 없을 것.
# 전달 헤더가 붙어 있다는 건 중간에 프록시가 있었다는 뜻이므로 그 자체로 거부 사유다.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"}
_PROXY_HEADERS = ("x-forwarded-for", "x-real-ip", "cf-connecting-ip", "forwarded", "cf-ray")


def _requester(request: Request) -> dict:
    """실행 저널에 남길 요청자 식별 (trace-b-lane-f7.md §4 — 추적 불가였던 지점)."""
    return {
        "origin_ip": (request.client.host if request.client else "") or "",
        "user_agent": request.headers.get("user-agent", ""),
        "forwarded_for": request.headers.get("x-forwarded-for", ""),
    }


def require_loopback(request: Request):
    if os.getenv("WEB_OPS_ALLOW_REMOTE", "0").strip() in ("1", "true", "True"):
        return  # 명시적 옵트인 — 기본은 차단
    host = (request.client.host if request.client else "") or ""
    proxied = [h for h in _PROXY_HEADERS if h in request.headers]
    if host in _LOOPBACK_HOSTS and not proxied:
        return
    raise HTTPException(
        status_code=403,
        detail=("이 엔드포인트는 loopback 전용입니다 (원격 스캔 트리거 차단). "
                f"origin={host or 'unknown'} proxy_headers={proxied or 'none'}. "
                "로컬에서 실행하거나, 의도한 경우에만 WEB_OPS_ALLOW_REMOTE=1로 해제하세요."),
    )


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


@app.get("/api/compass")
def compass():
    return S.market_compass()


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


@app.post("/api/ops/scan", dependencies=[Depends(require_loopback)])
def scan_start(request: Request, target: str = Query("all", description="kospi_swing|kosdaq_swing|nasdaq_swing|kospi_intraday|kosdaq_intraday|b|kospi_all|kosdaq_all|all")):
    return jobs.start(target or "all", requester=_requester(request))


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
