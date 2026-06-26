"""B 엔진 실시간 대시보드 서버 (신규 페이지, A와 별개). stdlib http.server — 의존성 0.

라우트:
  GET /                  → b_dashboard.html
  GET /api/picks         → 오늘의 B top10 픽 (b_picks_latest.json)
  GET /api/prices?codes=  → 실시간 시세 (KIS, 장중 라이브 / 장외 종가). 갱신용.
  GET /api/shadow        → forward-shadow 라이브 성과 요약
  POST/GET /api/rescan   → 픽 재생성(수동)

실행: python -m b_engine.server  (기본 0.0.0.0:8848)  env B_PORT 로 변경.
실시간 시세엔 KIS_ENABLE_LIVE_CALLS=1 + .env.local 필요(없으면 종가 폴백).
"""
from __future__ import annotations
import os, json, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from b_engine import model_engine as E
from b_engine import model_scan as S

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "b_dashboard.html")
PORT = int(os.environ.get("B_PORT", "8848"))
_CLIENT = None
_CLIENT_TRIED = False
_KIS_COOLDOWN = 0.0          # 실패시 재시도 억제(초)
_PRICE_BUDGET = float(os.environ.get("B_PRICE_TIMEOUT", "6"))  # 시세요청 총 예산(초)


def _kis():
    """KIS 클라이언트(1회 init). 실패시 None + 쿨다운으로 재시도 억제(대시보드 행 방지)."""
    global _CLIENT, _CLIENT_TRIED, _KIS_COOLDOWN
    if _CLIENT is not None:
        return _CLIENT
    if _CLIENT_TRIED and time.time() < _KIS_COOLDOWN:
        return None
    _CLIENT_TRIED = True
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(HERE), ".env.local"))
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"   # 대시보드는 라이브 시세가 목적 → 강제 on(.env 값 덮어씀)
        from modules.kis_openapi import KISOpenAPIClient
        c = KISOpenAPIClient(timeout=5.0); c.get_access_token()
        _CLIENT = c
    except Exception as e:
        print(f"[B server] KIS 라이브 불가 → 종가 폴백 ({e})", flush=True)
        _CLIENT = None
        _KIS_COOLDOWN = time.time() + 120   # 2분 쿨다운
    return _CLIENT


def _fetch(codes, out):
    c = _kis()
    if c is None:
        return
    for code in codes:
        try:
            q = c.quote_snapshot(code)   # 이미 파싱된 dict: last_price / day_change_pct
            out[code] = {"price": q.get("last_price"), "change_pct": q.get("day_change_pct"),
                         "status": q.get("source_status")}
        except Exception:
            pass


def live_prices(codes):
    """{code:{price,change_pct}}. 워커스레드+예산초과시 부분/빈 반환 → 대시보드 절대 안 멈춤."""
    out = {}
    t = threading.Thread(target=_fetch, args=(codes, out), daemon=True)
    t.start(); t.join(_PRICE_BUDGET)     # 예산 내 안 끝나면 그대로 둠(빈값=프론트 종가폴백)
    return out


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path); path = u.path
        try:
            if path in ("/", "/index.html"):
                with open(HTML, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif path == "/api/picks":
                p = E.DATA + "/b_picks_latest.json"
                self._send(200, open(p, encoding="utf-8").read() if os.path.exists(p) else "{}")
            elif path == "/api/shadow":
                self._send(200, json.dumps(S.shadow_summary(), ensure_ascii=False))
            elif path == "/api/prices":
                q = parse_qs(u.query); codes = q.get("codes", [""])[0].split(",")
                codes = [c for c in codes if c]
                self._send(200, json.dumps(live_prices(codes), ensure_ascii=False))
            elif path == "/api/rescan":
                out = S.scan()
                self._send(200, json.dumps({"ok": bool(out), "scan_date": out["scan_date"] if out else None}, ensure_ascii=False))
            else:
                self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


def main():
    # KIS 클라이언트를 시작시 백그라운드로 워밍(토큰 캐시) → 첫 시세요청부터 빠름.
    threading.Thread(target=lambda: (_kis() and print("[B server] KIS 라이브 준비됨", flush=True)),
                     daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"[B 엔진 대시보드] http://localhost:{PORT}  (Ctrl+C 종료)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
