"""신웹 백엔드 서비스층 — 기존 모듈/로컬 데이터 재사용(재계산 X = 속도). 정직(신선도·알파·배지) 포함.

소스:
  A 픽: runtime_state/reports/experimental/*_ledger.jsonl (레인별, 최신 스캔일)
  B 픽: b_engine/data/b_picks_latest.json
  종목명: modules.ticker_names · 시장: px_long(code→market) · 시세: KIS quote_snapshot
  신선도: ~/research_cache parquet 최신일
"""
from __future__ import annotations
import os, sys, json, threading, time
from functools import lru_cache
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
RESEARCH = os.path.expanduser("~/research_cache")
EXP = os.path.join(REPO, "runtime_state/reports/experimental")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(REPO, ".env.local"))  # GEMINI/KIS/Supabase 키 로드
except Exception:
    pass

from modules.ticker_names import resolve_name  # noqa: E402

# 레인 메타: ledger 파일 · 표시명 · 신호유형 · 시장(원장에 있으면 우선)
LANES = {
    "kospi_swing":   {"ledger": "swing_ensemble_ledger.jsonl",                 "label": "코스피 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kosdaq_swing":  {"ledger": "swing_ensemble_ledger.jsonl",                 "label": "코스닥 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kospi_intraday":{"ledger": "kospi_intraday_swing_ledger.jsonl",           "label": "코스피 장중",  "kind": "INTRADAY", "badge": "🔵"},
    "kosdaq_intraday":{"ledger":"kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl","label":"코스닥 장중","kind":"INTRADAY","badge":"🔵"},
    # 8년 검증 스윙 first-touch 랭커 (RESEARCH_LOG §7-A) — 정직한 modest 엣지, 후보픽 전용 (라우팅 없음)
    "swing_candidate":{"ledger": "kr_swing_candidate_ledger.jsonl",            "label": "스윙 후보",   "kind": "CANDIDATE","badge": "🧪"},
}
TARGET_PCT = 5.0
# 승격 계약(§7-E)의 원장 필드 → 웹 노출 (티어/레짐상태/계약)
_LEDGER_EXTRA_KEYS = ("tier", "tier_threshold", "mkt_state", "mkt_dd20", "hold_days",
                      "target_tp_pct", "ev_pred", "exit_contract")


@lru_cache(maxsize=1)
def _code_market():
    """code -> 'KOSPI'/'KOSDAQ' (px_long). 1회 캐시."""
    try:
        import pandas as pd
        df = pd.read_parquet(os.path.join(RESEARCH, "px_long.parquet"), columns=["code", "market"])
        df["code"] = df["code"].astype(str)
        return dict(zip(df["code"], df["market"].astype(str)))
    except Exception:
        return {}


def _market_of(code, fallback=""):
    m = _code_market().get(str(code).split(".")[0].zfill(6), "")
    if m:
        return "KOSPI" if "KOSPI" in m.upper() or m.upper() == "KS" else ("KOSDAQ" if "KOSDAQ" in m.upper() or m.upper() == "KQ" else m)
    t = str(code or "").upper()
    if t.endswith(".KS"):
        return "KOSPI"
    if t.endswith(".KQ"):
        return "KOSDAQ"
    return fallback


def _read_ledger(fn):
    fp = os.path.join(EXP, fn)
    if not os.path.exists(fp):
        return []
    out = []
    for ln in open(fp):
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def _next_trading_day(scan_date):
    """스캔일(마감 후 산출) → 매수 대상일 = 다음 영업일(주말 skip; 공휴일 미반영 근사)."""
    try:
        import pandas as pd
        d = pd.Timestamp(scan_date) + pd.Timedelta(days=1)
        while d.weekday() >= 5:  # 토/일
            d += pd.Timedelta(days=1)
        return str(d.date())
    except Exception:
        return None


def _pick_row(code, market, lane_key, *, entry=None, prob=None, alpha=None, name=None, scan_date=None, source="A", extra=None):
    raw = str(code).split(".")[0]
    code6 = raw.zfill(6) if raw.isdigit() else raw   # KR=6자리, US=원형 유지
    meta = LANES.get(lane_key, {})
    row = {
        "code": code6,
        "ticker": str(code),
        "name": name or resolve_name(code6, default=code6),
        "market": market or _market_of(code),
        "lane": lane_key,
        "lane_label": meta.get("label", lane_key),
        "kind": meta.get("kind", source),
        "badge": meta.get("badge", "🟣" if source == "B" else ""),
        "signal_class": source,
        "scan_date": scan_date,
        "buy_date": _next_trading_day(scan_date),   # 매수 대상일(다음 거래일)
        "prob": round(float(prob) * 100, 1) if (prob is not None and prob <= 1.5) else (round(float(prob), 1) if prob is not None else None),
        "alpha": round(float(alpha), 2) if alpha is not None else None,   # 예측 알파(B). A는 None.
        "entry": float(entry) if entry else None,
        "target": round(float(entry) * (1 + TARGET_PCT / 100), 2) if entry else None,
        "target_pct": TARGET_PCT,
    }
    if extra:
        row.update({k: v for k, v in extra.items() if v is not None})
        # 레인별 계약 TP(§7-E: KOSDAQ +10%)가 있으면 목표가 재계산
        tp = row.get("target_tp_pct")
        if tp and entry:
            row["target"] = round(float(entry) * (1 + float(tp) / 100), 2)
            row["target_pct"] = float(tp)
    return row


def _a_picks_ledger(lane=None):
    """A 레인 픽 (ledger 기반) — DB 불가시 폴백. 각 레인 최신 스캔일만."""
    keys = [lane] if lane and lane in LANES else list(LANES.keys())
    rows = []
    # swing_ensemble 원장은 코스피/코스닥 공용 → market으로 분리
    cache = {}
    for key in keys:
        meta = LANES[key]
        led = cache.setdefault(meta["ledger"], _read_ledger(meta["ledger"]))
        if not led:
            continue
        want_market = "KOSPI" if "kospi" in key else ("KOSDAQ" if "kosdaq" in key else "")
        recs = [r for r in led if (not want_market or str(r.get("market", "")).upper() == want_market or not r.get("market"))]
        if not recs:
            continue
        last = max(str(r.get("date", "")) for r in recs)
        seen = set()
        for r in recs:
            if str(r.get("date", "")) != last:
                continue
            code = str(r.get("ticker", ""))
            mk = (r.get("market") or _market_of(code)).upper()
            if want_market and mk != want_market:
                continue
            code6 = code.split(".")[0].zfill(6)
            if code6 in seen:
                continue
            seen.add(code6)
            rows.append(_pick_row(code, want_market or mk, key,
                                  entry=r.get("entry_reference_price") or r.get("close"),
                                  prob=r.get("p"), scan_date=last, source="A",
                                  extra={k: r.get(k) for k in _LEDGER_EXTRA_KEYS}))
    return rows


# 모델 레인 ↔ (scan_deep_reports decision_bucket, market)
_KR_LANE_OF = {
    ("swing_ensemble", "KOSPI"): "kospi_swing",
    ("swing_ensemble", "KOSDAQ"): "kosdaq_swing",
    ("kospi_intraday", "KOSPI"): "kospi_intraday",
    ("kosdaq_intraday_3d_t5_vwap_guard", "KOSDAQ"): "kosdaq_intraday",
}
_KR_CACHE = {"ts": 0.0, "rows": []}


def _kr_scan_picks():
    """KR 모델 레인 픽 — scan_deep_reports의 레인별 최신 run. 웹·일일·디스코드 스캔 모두 반영.
    120초 캐시 + 워커 타임아웃(웹 안 멈춤)."""
    if time.time() - _KR_CACHE["ts"] < 120 and _KR_CACHE["rows"]:
        return _KR_CACHE["rows"]
    out = {"rows": []}

    def work():
        db = _db()
        if db is None:
            return
        try:
            import json as _j
            buckets = list({b for (b, _m) in _KR_LANE_OF})
            q = (db.client.table("scan_deep_reports")
                 .select("ticker,stock_name,candidate_interpretation,prediction,run_id,generated_at,market,decision_bucket")
                 .in_("market", ["KOSPI", "KOSDAQ"]).in_("decision_bucket", buckets)
                 .order("generated_at", desc=True).limit(400).execute())
            rows = q.data or []
            latest_run = {}
            for r in rows:
                lane = _KR_LANE_OF.get((str(r.get("decision_bucket")), str(r.get("market")).upper()))
                if lane and lane not in latest_run:
                    latest_run[lane] = r.get("run_id")
            picks, seen = [], set()
            for r in rows:
                lane = _KR_LANE_OF.get((str(r.get("decision_bucket")), str(r.get("market")).upper()))
                if not lane or r.get("run_id") != latest_run.get(lane):
                    continue
                ci = r.get("candidate_interpretation") or {}
                if isinstance(ci, str):
                    ci = _j.loads(ci) if ci else {}
                pred = r.get("prediction") or {}
                if isinstance(pred, str):
                    pred = _j.loads(pred) if pred else {}
                mk = str(r.get("market")).upper()
                code = str(r.get("ticker", ""))
                base = code.split(".")[0]
                code6 = base.zfill(6) if base.isdigit() else base
                if (lane, code6) in seen:
                    continue
                seen.add((lane, code6))
                # KR은 stock_name이 티커인 경우가 많아 code로 resolve(한글명) — name=None이면 _pick_row가 처리
                picks.append(_pick_row(code, mk, lane, entry=ci.get("entry_reference_price"),
                                       prob=pred.get("phase25_prob"), name=None,
                                       scan_date=str(r.get("generated_at"))[:10], source="A"))
            out["rows"] = picks
        except Exception:
            pass
    t = threading.Thread(target=work, daemon=True); t.start(); t.join(7.0)
    if out["rows"]:
        _KR_CACHE.update(ts=time.time(), rows=out["rows"])
    return out["rows"]


def a_picks(lane=None):
    """A 레인 픽 — 레인별 최신: scan_deep_reports(웹·일일·디스코드 스캔) 우선, 없는 레인은 ledger 폴백.
    → 스캔하면 픽·개요에 즉시 반영(스캔 완료시 jobs가 캐시 무효화)."""
    by_lane = {}
    for r in _a_picks_ledger():
        by_lane.setdefault(r["lane"], []).append(r)
    scan = {}
    for r in _kr_scan_picks():
        scan.setdefault(r["lane"], []).append(r)
    by_lane.update(scan)  # 스캔이 있는 레인은 최신 스캔으로 교체
    rows = [r for rs in by_lane.values() for r in rs]
    if lane:
        rows = [r for r in rows if r.get("lane") == lane]
    return rows


def invalidate_pick_caches():
    """스캔 완료 후 호출 — 픽/개요/성과가 최신 스캔을 즉시 반영하도록 캐시 비움."""
    _KR_CACHE.update(ts=0.0, rows=[])
    _NASDAQ_CACHE.update(ts=0.0, rows=[])
    try:
        _PERF_CACHE.update(ts=0.0, data=None)
    except Exception:
        pass


def b_picks():
    fp = os.path.join(REPO, "b_engine/data/b_picks_latest.json")
    if not os.path.exists(fp):
        return []
    try:
        d = json.load(open(fp))
    except Exception:
        return []
    rows = []
    for p in d.get("picks", []):
        rows.append(_pick_row(p.get("code"), _market_of(p.get("code")), "b_market_neutral",
                              entry=p.get("close"), prob=p.get("prob_win"), alpha=p.get("pred_alpha_5d"),
                              name=p.get("name"), scan_date=d.get("scan_date"), source="B",
                              extra={"lane_label": "B 시장중립", "kind": "B", "badge": "🟣",
                                     "pred_alpha_5d": p.get("pred_alpha_5d"), "smart5": p.get("smart5"),
                                     "rsi14": p.get("rsi14"), "hold_days": p.get("hold_days"),
                                     "tier": p.get("tier")}))
    return rows


# ── NASDAQ 픽 (Supabase scan_deep_reports, 캐시·타임아웃 가드) ─────────
_DB = None
_DB_TRIED = False
_NASDAQ_CACHE = {"ts": 0.0, "rows": []}


def _db():
    global _DB, _DB_TRIED
    if _DB is not None or _DB_TRIED:
        return _DB
    _DB_TRIED = True
    try:
        from modules.db_manager import DBManager
        _DB = DBManager()
    except Exception:
        _DB = None
    return _DB


def nasdaq_picks():
    """NASDAQ 최신 스캔 픽 (scan_deep_reports). 5분 캐시 + 워커 타임아웃(웹 안 멈춤)."""
    import time
    if time.time() - _NASDAQ_CACHE["ts"] < 300 and _NASDAQ_CACHE["rows"]:
        return _NASDAQ_CACHE["rows"]
    out = {"rows": []}

    def work():
        db = _db()
        if db is None:
            return
        try:
            import json as _j
            q = (db.client.table("scan_deep_reports")
                 .select("ticker,stock_name,candidate_interpretation,prediction,run_id,generated_at,scan_mode")
                 .eq("market", "NASDAQ").order("generated_at", desc=True).limit(60).execute())
            rows = q.data or []
            if not rows:
                return
            latest_run = rows[0].get("run_id")
            picks = []
            for r in rows:
                if r.get("run_id") != latest_run:
                    continue
                ci = r.get("candidate_interpretation") or {}
                if isinstance(ci, str):
                    ci = _j.loads(ci) if ci else {}
                pred = r.get("prediction") or {}
                if isinstance(pred, str):
                    pred = _j.loads(pred) if pred else {}
                entry = ci.get("entry_reference_price")
                prob = pred.get("phase25_prob")
                picks.append(_pick_row(r.get("ticker"), "NASDAQ", "nasdaq_swing",
                                       entry=entry, prob=prob, name=r.get("stock_name"),
                                       scan_date=str(r.get("generated_at"))[:10], source="A",
                                       extra={"lane_label": "나스닥 스윙", "kind": "SWING", "badge": "🟢",
                                              "edge_score": pred.get("expected_edge_score"),
                                              "exp_ret_3d": pred.get("expected_return_3d_pct")}))
            out["rows"] = picks
        except Exception:
            pass
    t = threading.Thread(target=work, daemon=True); t.start(); t.join(7.0)
    if out["rows"]:
        _NASDAQ_CACHE["ts"] = time.time(); _NASDAQ_CACHE["rows"] = out["rows"]
    return out["rows"]


def picks(lane=None):
    if lane == "b_market_neutral":
        return b_picks()
    if lane == "nasdaq_swing":
        return nasdaq_picks()
    if lane:
        return a_picks(lane)
    # 전체: KR(A) + B + NASDAQ. 확률(p) 기준 통일 정렬 → 개요와 픽 순서 일치.
    allp = a_picks() + b_picks() + nasdaq_picks()
    return sorted(allp, key=lambda x: (x.get("prob") is None, -(x.get("prob") or 0)))


# ── 실시간 시세 (KIS, 타임아웃 가드 — 행 방지) ──────────────
_CLIENT = None
_TRIED = False
_COOL = 0.0


def _kis():
    global _CLIENT, _TRIED, _COOL
    if _CLIENT is not None:
        return _CLIENT
    if _TRIED and time.time() < _COOL:
        return None
    _TRIED = True
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO, ".env.local"))
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        from modules.kis_openapi import KISOpenAPIClient
        c = KISOpenAPIClient(timeout=5.0); c.get_access_token()
        _CLIENT = c
    except Exception:
        _CLIENT = None; _COOL = time.time() + 120
    return _CLIENT


def prices(codes, budget=8.0):
    out = {}

    def work():
        c = _kis()
        if c is None:
            return
        for code in codes:
            try:
                q = c.quote_snapshot(str(code).split(".")[0].zfill(6))
                out[str(code).split(".")[0].zfill(6)] = {
                    "price": q.get("last_price"), "change_pct": q.get("day_change_pct"),
                    "status": q.get("source_status")}
            except Exception:
                pass
    t = threading.Thread(target=work, daemon=True); t.start(); t.join(budget)
    return out


# ── 데이터 신선도 ──────────────────────────────────────────
def freshness():
    import pandas as pd
    out = {}
    for key, fn in [("daily", "px_long.parquet"), ("flow", "flow.parquet"),
                    ("dart", "dart_events.parquet"), ("pead", "pead_surprise.parquet")]:
        fp = os.path.join(RESEARCH, fn)
        try:
            d = pd.read_parquet(fp, columns=["date"] if key != "dart" else ["ann"])
            col = "date" if "date" in d.columns else "ann"
            out[key] = str(pd.to_datetime(d[col]).max())[:10]
        except Exception:
            out[key] = None
    # 분봉: 샘플 1종목 최신
    try:
        import glob
        f = sorted(glob.glob(os.path.join(RESEARCH, "intraday", "*.parquet")))[:1]
        if f:
            mi = pd.read_parquet(f[0]); out["minute"] = str(pd.to_datetime(mi.index).max())[:10]
    except Exception:
        out["minute"] = None
    return out


def chart(code, tf="day", days=120):
    """차트 데이터. tf=minute(분봉 OHLC, intraday캐시) / day(일봉: ohlc_daily 있으면 OHLC, 없으면 close 라인)."""
    import pandas as pd
    code6 = str(code).split(".")[0].zfill(6)
    if tf == "minute":
        fp = os.path.join(RESEARCH, "intraday", f"{code6}.parquet")
        if not os.path.exists(fp):
            return {"type": "candle", "tf": "minute", "bars": []}
        df = pd.read_parquet(fp); df.index = pd.to_datetime(df.index)
        df = df.sort_index().tail(390 * 3)  # 최근 ~3거래일 분봉
        bars = [{"time": int(t.timestamp()), "open": float(r.Open), "high": float(r.High),
                 "low": float(r.Low), "close": float(r.Close)} for t, r in df.iterrows()]
        return {"type": "candle", "tf": "minute", "bars": bars}
    # day: ohlc_daily(OHLC) 우선
    od = os.path.join(RESEARCH, "ohlc_daily.parquet")
    try:
        if os.path.exists(od):
            d = pd.read_parquet(od); d["code"] = d["code"].astype(str)
            s = d[d["code"] == code6].copy()
            if len(s):
                s["date"] = pd.to_datetime(s["date"]); s = s.sort_values("date").tail(days)
                bars = [{"time": r["date"].strftime("%Y-%m-%d"), "open": float(r["open"]), "high": float(r["high"]),
                         "low": float(r["low"]), "close": float(r["close"])} for _, r in s.iterrows()]
                return {"type": "candle", "tf": "day", "bars": bars}
    except Exception:
        pass
    # 폴백: px_long close 라인
    try:
        px = pd.read_parquet(os.path.join(RESEARCH, "px_long.parquet"), columns=["code", "date", "close"])
        px["code"] = px["code"].astype(str)
        s = px[px["code"] == code6].copy()
        s["date"] = pd.to_datetime(s["date"]); s = s.sort_values("date").tail(days)
        bars = [{"time": r["date"].strftime("%Y-%m-%d"), "value": float(r["close"])} for _, r in s.iterrows()]
        return {"type": "line", "tf": "day", "bars": bars}
    except Exception:
        return {"type": "line", "tf": "day", "bars": []}


def pick_detail(code):
    """픽 상세(드로어) — 픽 메타 + 수급/이벤트 근거. 차트는 별도 /api/chart."""
    import pandas as pd
    code6 = str(code).split(".")[0].zfill(6)
    # 현재 픽 목록에서 찾기
    base = next((p for p in picks() if p["code"] == code6), None)
    detail = {"code": code6, "name": resolve_name(code6, default=code6),
              "market": _market_of(code6), "in_picks": base is not None, "pick": base}
    # 수급(flow 최신)
    try:
        fl = pd.read_parquet(os.path.join(RESEARCH, "flow.parquet"))
        fl["code"] = fl["code"].astype(str); fl["date"] = pd.to_datetime(fl["date"])
        s = fl[fl["code"] == code6].sort_values("date").tail(5)
        if len(s):
            detail["flow"] = {"frgn_5d": int(s["frgn_ntby"].sum()), "orgn_5d": int(s["orgn_ntby"].sum()),
                              "asof": str(s["date"].max())[:10]}
    except Exception:
        pass
    # 공시(dart 최신)
    try:
        dr = pd.read_parquet(os.path.join(RESEARCH, "dart_events.parquet"))
        dr["code"] = dr["code"].astype(str)
        s = dr[dr["code"] == code6].tail(3)
        detail["dart"] = [{"ann": str(r["ann"]), "type": str(r.get("etype", ""))} for _, r in s.iterrows()]
    except Exception:
        pass
    return detail


def _regime_label(idx_mom, idx_vol):
    if idx_mom is None:
        return "정보없음"
    if idx_mom > 1.5:
        return "상승"
    if idx_mom < -1.5:
        return "하락"
    return "중립"


def _gemini_verdict(facts):
    """Gemini 종합판정(정직). 키/네트워크 실패시 규칙기반 폴백."""
    key = os.environ.get("GEMINI_API_KEY", "")
    f = facts
    feat = f.get("features", {})
    fl = f.get("flow", {})
    base = (
        f"종목 {f['name']}({f['code']}, {f['market']}). "
        f"모델: A {'픽('+f['model']['in_a']['lane_label']+', 확률'+str(f['model']['in_a'].get('prob'))+'%)' if f['model'].get('in_a') else '미픽'}, "
        f"B {'픽' if f['model'].get('in_b') else '미픽'}. "
        f"레짐 {f.get('regime')}. RSI {feat.get('rsi14')}, 20일수익 {feat.get('ret_20d')}%, "
        f"20일고가이격 {feat.get('dist_hi20')}%. 수급(5일) 외국인 {fl.get('frgn_5d')} 기관 {fl.get('orgn_5d')}. "
        f"공시 {len(f.get('events',{}).get('dart',[]))}건."
    )
    if not key:
        # 규칙 폴백
        pos, neg = [], []
        if f["model"].get("in_a") or f["model"].get("in_b"):
            pos.append("오늘 모델 픽")
        else:
            neg.append("오늘 모델 미픽")
        if (fl.get("frgn_5d") or 0) > 0:
            pos.append("외국인 순매수")
        if (feat.get("ret_20d") or 0) > 15:
            neg.append("단기 과열(20일 급등)")
        if f.get("regime") == "하락":
            neg.append("하락 레짐")
        v = f"강점: {', '.join(pos) or '특이 없음'}. 리스크: {', '.join(neg) or '특이 없음'}. (규칙기반 요약 — Gemini 키 없음)"
        return {"text": v, "source": "rule"}
    try:
        import urllib.request
        prompt = (
            "너는 신중한 한국 주식 퀀트 애널리스트다. 아래 사실만 근거로 이 종목의 현재 시점 매수 타당성을 "
            "한국어 2~3문장으로 정직하게 평가하라. 강점과 리스크를 균형있게, 과장 금지, 확정적 단정 금지, "
            "투자권유가 아님을 전제. 사실:\n" + base
        )
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read())
        text = d["candidates"][0]["content"]["parts"][0]["text"].strip()
        return {"text": text, "source": "gemini-2.5-flash"}
    except Exception as e:
        return {"text": f"종합 판정 생성 실패(폴백): {base}", "source": f"fallback({type(e).__name__})"}


def analyze(code):
    """③ 정밀분석 — 우리 데이터로 한 종목 종합(yfinance 폐기). A~E 사실 + G Gemini 판정."""
    import pandas as pd
    code6 = str(code).split(".")[0].zfill(6)
    name = resolve_name(code6, default=code6)
    market = _market_of(code6)
    # 모델 판정(오늘 픽 멤버십)
    all_picks = picks()
    in_a = next((p for p in all_picks if p["code"] == code6 and p["signal_class"] == "A"), None)
    in_b = next((p for p in all_picks if p["code"] == code6 and p["signal_class"] == "B"), None)
    # px_long 최신 피처
    FEAT = ["rsi14", "bb_pctb", "dist_hi20", "dist_lo20", "ret_5d", "ret_20d", "atr_pct", "ma20_dist", "idx_mom20", "idx_vol20", "close"]
    feat = {}
    try:
        px = pd.read_parquet(os.path.join(RESEARCH, "px_long.parquet"), columns=["code", "date"] + FEAT)
        px["code"] = px["code"].astype(str)
        import math
        def _fin(v):
            try:
                v = float(v)
                return round(v, 2) if math.isfinite(v) else None
            except Exception:
                return None
        s = px[px["code"] == code6].sort_values("date").tail(1)
        if len(s):
            r = s.iloc[0]
            feat = {k: _fin(r[k]) for k in FEAT}
            feat["asof"] = str(r["date"])[:10]
    except Exception:
        pass
    # 수급
    flow = {}
    try:
        fl = pd.read_parquet(os.path.join(RESEARCH, "flow.parquet"))
        fl["code"] = fl["code"].astype(str); fl["date"] = pd.to_datetime(fl["date"])
        s = fl[fl["code"] == code6].sort_values("date")
        if len(s):
            flow = {"frgn_5d": int(s["frgn_ntby"].tail(5).sum()), "orgn_5d": int(s["orgn_ntby"].tail(5).sum()),
                    "frgn_20d": int(s["frgn_ntby"].tail(20).sum()), "asof": str(s["date"].max())[:10]}
    except Exception:
        pass
    # 이벤트(공시/실적)
    events = {"dart": [], "pead": None}
    try:
        dr = pd.read_parquet(os.path.join(RESEARCH, "dart_events.parquet")); dr["code"] = dr["code"].astype(str)
        events["dart"] = [{"ann": str(x["ann"]), "type": str(x.get("etype", ""))} for _, x in dr[dr["code"] == code6].tail(3).iterrows()]
    except Exception:
        pass
    try:
        pe = pd.read_parquet(os.path.join(RESEARCH, "pead_surprise.parquet")); pe["code"] = pe["code"].astype(str)
        s = pe[pe["code"] == code6].tail(1)
        if len(s):
            import math
            se = float(s.iloc[0]["surp_eps"])
            events["pead"] = {"ann": str(s.iloc[0]["ann"])[:10],
                              "surp_eps": round(se, 1) if math.isfinite(se) else None}
    except Exception:
        pass
    regime = _regime_label(feat.get("idx_mom20"), feat.get("idx_vol20"))
    out = {"code": code6, "name": name, "market": market,
           "model": {"in_a": in_a, "in_b": in_b}, "features": feat, "flow": flow,
           "events": events, "regime": regime}
    out["verdict"] = _gemini_verdict(out)
    return out


_PERF_BUCKET_LANE = {
    ("swing_ensemble", "KOSPI"): "코스피 스윙",
    ("swing_ensemble", "KOSDAQ"): "코스닥 스윙",
    ("kospi_intraday", "KOSPI"): "코스피 장중",
    ("kosdaq_intraday_3d_t5_vwap_guard", "KOSDAQ"): "코스닥 장중",
}


def _scan_deep_perf_rows():
    """scan_deep_reports 모델버킷 픽(전체 history) → [(lane_label, scan_date_KST, code6)].
    성과 누적용 — 웹·디스코드·일일 모든 스캔 포함. DB 워커 타임아웃(웹 안 멈춤)."""
    out = {"rows": []}

    def work():
        db = _db()
        if db is None:
            return
        try:
            from datetime import datetime as _dt, timezone as _tz
            try:
                from zoneinfo import ZoneInfo
                _kst = ZoneInfo("Asia/Seoul")
            except Exception:
                _kst = None
            buckets = list({b for (b, _m) in _PERF_BUCKET_LANE})
            q = (db.client.table("scan_deep_reports")
                 .select("ticker,market,decision_bucket,generated_at")
                 .in_("decision_bucket", buckets).order("generated_at", desc=True).limit(3000).execute())
            res = []
            for r in (q.data or []):
                lane = _PERF_BUCKET_LANE.get((str(r.get("decision_bucket")), str(r.get("market")).upper()))
                if not lane:
                    continue
                base = str(r.get("ticker", "")).split(".")[0]
                if not base.isdigit():
                    continue
                ts = str(r.get("generated_at") or "")
                sdate = ts[:10]
                try:
                    d = _dt.fromisoformat(ts.replace("Z", "+00:00"))
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=_tz.utc)
                    sdate = (d.astimezone(_kst) if _kst else d).strftime("%Y-%m-%d")
                except Exception:
                    pass
                res.append((lane, sdate, base.zfill(6)))
            out["rows"] = res
        except Exception:
            pass
    t = threading.Thread(target=work, daemon=True); t.start(); t.join(7.0)
    return out["rows"]


def contract_performance():
    """④-b 계약 실현 성과 — 승격 계약(§7-E)의 자동 채점 결과.
    원천: 레인 원장의 exit shadow 필드(리졸버가 해상 9일차에 기록) + 선별 shadow 뷰 + 스윙 후보 원장.
    마크투마켓(performance)과 달리 '터치익절 계약대로 매매했을 때'의 실현 수익."""
    out = {"note": "터치익절 계약 실현 수익 (자동 채점, 비용 전). 마크투마켓 성과와 별개.", "lanes": {}}

    def _agg(vals):
        if not vals:
            return {"n": 0}
        return {"n": len(vals), "ev_avg": round(sum(vals) / len(vals), 2),
                "win_pct": round(sum(1 for v in vals if v > 0.3) / len(vals) * 100, 1),
                "worst": round(min(vals), 2)}

    for key, exit_key, label in (("kospi_intraday", "exit_t5_h5", "코스피 장중 (+5% 터치/5일)"),
                                 ("kosdaq_intraday", "exit_t10_h5", "코스닥 장중 (+10% 터치/5일)")):
        rows = _read_ledger(LANES[key]["ledger"])
        vals = [float(r[exit_key]) for r in rows if isinstance(r.get(exit_key), (int, float))]
        out["lanes"][key] = {"label": label, **_agg(vals)}
    # 스윙 후보 (익일 시가 진입, +5% 터치/5일, policy_ret에 비용 전 수익)
    rows = _read_ledger(LANES["swing_candidate"]["ledger"])
    vals = [float(r["policy_ret"]) for r in rows if isinstance(r.get("policy_ret"), (int, float))]
    out["lanes"]["swing_candidate"] = {"label": "스윙 후보 (+5% 터치/5일, 익일시가)", **_agg(vals)}
    # 선별 shadow (rank-1 고확신 트랙) 요약 패스스루
    try:
        sel = json.load(open(os.path.join(REPO, "runtime_state/reports/experimental/kr_selective_shadow_latest.json")))
        out["selective"] = {m: {"rank1": v.get("rank1_all"), "primary": v.get("rank1_primary")}
                            for m, v in (sel.get("lanes") or {}).items()}
    except Exception:
        out["selective"] = None
    return out


_PERF_CACHE = {"ts": 0.0, "data": None}


def performance():
    """④ 성과 — 레인별 실현 승률 + 시장대비 알파(베타 분리) + 절대수익. **누적**(갈아치우지 않음):
    ledger(일일ops) + scan_deep_reports(웹·디스코드·일일 모든 스캔) 전체 history를 합쳐 평가.
    ★ 진입 기준 = '다음 거래일 종가'(현실 진입). 스캔일 종가가 아니라 실제 매수가능 시점 → 정직.
    px_long 전체 읽기(무거움) → 10분 TTL 캐시. 스캔 완료시 invalidate_pick_caches가 비움.
    """
    if time.time() - _PERF_CACHE["ts"] < 600 and _PERF_CACHE["data"] is not None:
        return _PERF_CACHE["data"]
    import pandas as pd, numpy as np, math
    px = pd.read_parquet(os.path.join(RESEARCH, "px_long.parquet"), columns=["code", "date", "close", "liq"])
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"])
    cur_date = px["date"].max()
    cur = px[px["date"] == cur_date].set_index("code")["close"].to_dict()
    liq = px[px["date"] >= cur_date - pd.Timedelta(days=120)].groupby("code")["liq"].median()
    uni = set(liq[liq >= 100e8].index.astype(str))
    pv = px[px["code"].isin(uni)].pivot_table(index="date", columns="code", values="close")

    def mkt_ret(d):
        d = pd.Timestamp(d)
        if d not in pv.index:
            prev = pv.index[pv.index <= d]
            if not len(prev):
                return None
            d = prev.max()
        v = ((pv.loc[cur_date] / pv.loc[d] - 1) * 100).mean()
        return float(v) if math.isfinite(v) else None

    LED = {"코스피 스윙": ("swing_ensemble_ledger.jsonl", "KOSPI"),
           "코스닥 스윙": ("swing_ensemble_ledger.jsonl", "KOSDAQ"),
           "코스피 장중": ("kospi_intraday_swing_ledger.jsonl", "KOSPI"),
           "코스닥 장중": ("kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "KOSDAQ")}
    # 픽 먼저 수집 → 해당 종목들의 일별 종가 시리즈로 '다음 거래일' 진입 조회.
    raw = []
    seen = set()
    for label, (fn, want) in LED.items():
        for r in _read_ledger(fn):
            mk = (r.get("market") or "").upper()
            if want and mk and mk != want:
                continue
            code = str(r.get("ticker", "")).split(".")[0].zfill(6)
            key = (label, str(r.get("date")), code)
            if not r.get("entry_reference_price") or code not in cur or key in seen:
                continue
            seen.add(key)
            raw.append({"lane": label, "scan_date": str(r.get("date")), "code": code})
    # scan_deep_reports(웹·디스코드·일일 모든 스캔) 전체 history도 누적 — 중복은 (lane,date,code)로 제외
    for label, sdate, code in _scan_deep_perf_rows():
        key = (label, sdate, code)
        if code not in cur or key in seen:
            continue
        seen.add(key)
        raw.append({"lane": label, "scan_date": sdate, "code": code})
    codes = {x["code"] for x in raw}
    by_code = {}
    sub = px[px["code"].isin(codes)].sort_values("date")
    for code, g in sub.groupby("code"):
        by_code[code] = (g["date"].values, g["close"].values)

    def next_entry(code, scan_date):
        """스캔일 다음 거래일의 (날짜, 종가) = 현실 진입."""
        if code not in by_code:
            return None, None
        dates, closes = by_code[code]
        i = int(np.searchsorted(dates, np.datetime64(pd.Timestamp(scan_date)), side="right"))
        if i >= len(dates):
            return None, None  # 다음 거래일 데이터 아직 없음(너무 최근) → 미해결
        return pd.Timestamp(dates[i]), float(closes[i])

    rows = []
    pending = {}
    for x in raw:
        entry_day, entry = next_entry(x["code"], x["scan_date"])
        if entry is None or entry <= 0:
            pending[x["lane"]] = pending.get(x["lane"], 0) + 1
            continue  # 다음 거래일 미도래 → 평가 보류(집계엔 pending으로 표시)
        ret = (cur[x["code"]] / entry - 1) * 100
        m = mkt_ret(entry_day)
        rows.append({"lane": x["lane"], "date": x["scan_date"], "buy_date": str(entry_day.date()),
                     "code": x["code"], "name": resolve_name(x["code"], default=x["code"]), "ret": ret,
                     "alpha": (ret - m) if m is not None else None,
                     "days": (cur_date - entry_day).days})
    def agg(rs):
        rs = [r for r in rs if r["alpha"] is not None]
        if not rs:
            return {"n": 0}
        a = [r["alpha"] for r in rs]; ab = [r["ret"] for r in rs]
        return {"n": len(rs),
                "alpha_mean": round(float(np.mean(a)), 2), "alpha_win": round(float(np.mean([x > 0 for x in a])) * 100),
                "abs_mean": round(float(np.mean(ab)), 2), "abs_win": round(float(np.mean([x > 0 for x in ab])) * 100),
                "immature": int(sum(1 for r in rs if r["days"] < 3))}
    lanes_out = {label: agg([r for r in rows if r["lane"] == label]) for label in LED}
    for label in lanes_out:
        lanes_out[label]["pending"] = pending.get(label, 0)
    overall = agg(rows)
    overall["pending"] = int(sum(pending.values()))
    # B forward-shadow
    b = {"settled": 0}
    sp = os.path.join(REPO, "b_engine/data/b_shadow.jsonl")
    if os.path.exists(sp):
        st = [json.loads(l) for l in open(sp) if l.strip()]
        sett = [r for r in st if r.get("status") == "settled"]
        b = {"settled": len(sett), "open": len([r for r in st if r.get("status") == "open"])}
        if sett:
            b["alpha_mean"] = round(float(np.mean([r["alpha"] for r in sett])), 2)
            b["alpha_win"] = round(float(np.mean([r.get("win", 0) for r in sett])) * 100)
    out = {"as_of": str(cur_date.date()), "overall": overall, "lanes": lanes_out,
            "b_shadow": b, "rows": sorted(rows, key=lambda x: (x["alpha"] is None, -(x["alpha"] or -999)))}
    _PERF_CACHE.update(ts=time.time(), data=out)
    return out


@lru_cache(maxsize=1)
def _archive_df():
    import pandas as pd
    fp = os.path.join(REPO, "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv")
    if not os.path.exists(fp):
        return None
    # 큰 파일 → 필요한 컬럼만(있는 것만)
    head = pd.read_csv(fp, nrows=1)
    want = [c for c in ["recommended_at", "run_id", "ticker", "stock_name", "market", "market_type",
                        "scan_mode", "decision_bucket", "entry_reference_price", "alpha_score",
                        "return_3d_pct", "return_5d_pct"] if c in head.columns]
    df = pd.read_csv(fp, usecols=want or None)
    return df


def archive(date_from=None, date_to=None, market=None, ticker=None, limit=200, offset=0):
    """④ 스캔 아카이브 — 과거 스캔 이력 행단위 (학습데이터셋 CSV)."""
    import pandas as pd
    df = _archive_df()
    if df is None:
        return {"count": 0, "rows": [], "note": "아카이브 CSV 없음(daily ops export 대기)"}
    d = df.copy()
    dcol = "recommended_at" if "recommended_at" in d.columns else None
    if dcol:
        d["_d"] = pd.to_datetime(d[dcol], errors="coerce", utc=True).dt.tz_convert("Asia/Seoul").dt.tz_localize(None)
        if date_from:
            d = d[d["_d"] >= pd.Timestamp(date_from)]
        if date_to:
            d = d[d["_d"] <= pd.Timestamp(date_to) + pd.Timedelta(days=1)]
    if market and "market" in d.columns:
        d = d[d["market"].astype(str).str.upper() == market.upper()]
    if ticker and "ticker" in d.columns:
        d = d[d["ticker"].astype(str).str.contains(ticker, case=False, na=False)]
    total = len(d)
    if dcol:
        d = d.sort_values("_d", ascending=False)
    d = d.iloc[offset:offset + limit]
    def _s(x):
        return "" if (x is None or (isinstance(x, float) and pd.isna(x))) else str(x)
    out = []
    for _, r in d.iterrows():
        code = _s(r.get("ticker")).split(".")[0].zfill(6)
        ret = r.get("return_5d_pct") if pd.notna(r.get("return_5d_pct")) else r.get("return_3d_pct")
        nm = resolve_name(code, default="") or _s(r.get("stock_name")).strip() or code
        lane = _s(r.get("decision_bucket")).strip() or _s(r.get("scan_mode")).strip() or "–"
        # 과거 export가 모델레인 bucket을 unknown으로 눌러쓴 행 폴백: run_id로 레인 복원
        if lane in ("unknown", "", "–"):
            rid = _s(r.get("run_id"))
            if rid.startswith("SWING-ENS"):
                lane = "swing_ensemble"
            elif rid.startswith("KOSPI-ITD"):
                lane = "kospi_intraday"
            elif rid.startswith("KQ-ITD"):
                lane = "kosdaq_intraday"
            elif rid.startswith("NASDAQ-SESSION-EDGE"):
                lane = "nasdaq_session_edge"
        rv = _num(ret)
        out.append({"date": (r["_d"].strftime("%Y-%m-%d") if dcol and pd.notna(r.get("_d")) else None), "run_id": _s(r.get("run_id")),
                    "code": code, "name": nm, "market": _s(r.get("market")) or _s(r.get("market_type")),
                    "lane": lane, "entry": _num(r.get("entry_reference_price")), "prob": _num(r.get("alpha_score")),
                    "ret": rv, "result": ("승" if rv is not None and rv > 0 else ("패" if rv is not None else "미해결"))})
    return {"count": total, "offset": offset, "limit": limit, "rows": out}


def _num(x):
    import math
    try:
        v = float(x)
        return round(v, 2) if math.isfinite(v) else None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _index_snapshot(_day):
    import FinanceDataReader as fdr
    out = {}
    for name, sym in [("KOSPI", "KS11"), ("KOSDAQ", "KQ11")]:
        try:
            d = fdr.DataReader(sym, (datetime.now()).strftime("%Y-01-01"))["Close"]
            out[name] = {"level": round(float(d.iloc[-1]), 2), "change_pct": round(float(d.pct_change().iloc[-1] * 100), 2)}
        except Exception:
            out[name] = None
    return out


def market():
    """⑤ 시장·근거 — 지수/레짐 + 근거 피드(공시·수급)."""
    import pandas as pd
    today = datetime.now().strftime("%Y-%m-%d")
    idx = _index_snapshot(today)
    # 레짐(px_long idx_mom20 최신, 시장공통)
    regime = "정보없음"
    try:
        px = pd.read_parquet(os.path.join(RESEARCH, "px_long.parquet"), columns=["date", "idx_mom20"])
        px["date"] = pd.to_datetime(px["date"])
        v = px[px["date"] == px["date"].max()]["idx_mom20"].median()
        regime = _regime_label(float(v), None)
    except Exception:
        pass
    # 공시(DART 최신)
    dart = []
    try:
        dr = pd.read_parquet(os.path.join(RESEARCH, "dart_events.parquet")); dr["code"] = dr["code"].astype(str)
        dr["ann"] = dr["ann"].astype(str)
        for _, r in dr.sort_values("ann").tail(12).iloc[::-1].iterrows():
            dart.append({"ann": r["ann"], "code": r["code"], "name": resolve_name(r["code"], default=r["code"]), "type": str(r.get("etype", ""))})
    except Exception:
        pass
    # 수급 상위(외국인 순매수, flow 최신일)
    flow_top = []
    flow_asof = None
    try:
        fl = pd.read_parquet(os.path.join(RESEARCH, "flow.parquet")); fl["code"] = fl["code"].astype(str); fl["date"] = pd.to_datetime(fl["date"])
        last = fl["date"].max(); flow_asof = str(last.date())
        s = fl[fl["date"] == last].nlargest(10, "frgn_ntby")
        flow_top = [{"code": r["code"], "name": resolve_name(r["code"], default=r["code"]), "frgn": int(r["frgn_ntby"])} for _, r in s.iterrows()]
    except Exception:
        pass
    return {"index": idx, "regime": regime, "dart": dart, "flow_top": flow_top, "flow_asof": flow_asof}


@lru_cache(maxsize=1)
def _theme_records():
    return json.load(open(os.path.join(REPO, "runtime_state/long_term/theme_membership/KR.json")))["records"]


def theme():
    """⑥ 테마 네트워크 — primary_theme 그룹 + 오늘 픽 겹침(주도 테마). 가치사슬 요약."""
    try:
        recs = _theme_records()
    except Exception:
        return {"themes": [], "note": "테마 데이터 없음"}
    pick_codes = {p["code"] for p in picks()}
    groups = {}
    for r in recs:
        th = r.get("primary_theme")
        if not th:
            continue
        code = str(r.get("symbol", "")).split(".")[0].zfill(6)
        g = groups.setdefault(th, {"theme": th, "members": [], "pick_hits": []})
        g["members"].append({"code": code, "name": r.get("name") or resolve_name(code, default=code)})
        if code in pick_codes:
            g["pick_hits"].append(code)
    out = [{"theme": g["theme"], "size": len(g["members"]), "pick_hits": len(g["pick_hits"]),
            "members": g["members"][:30]} for g in groups.values()]
    out.sort(key=lambda x: (-x["pick_hits"], -x["size"]))
    return {"themes": out, "total_themes": len(out), "as_of": _theme_records and "최신"}


def ops_status():
    """⑦ 운영 — 스케줄러 세션 상태·데이터 신선도·모델 메타."""
    out = {"freshness": freshness(), "sessions": [], "models": {}}
    # 세션 상태(primary_market_session_state.json)
    sp = os.path.join(REPO, "runtime_state/long_term/ops/primary_market_session_state.json")
    try:
        st = json.load(open(sp))
        sessions = st.get("sessions", st) if isinstance(st, dict) else {}
        for sid, v in (sessions.items() if isinstance(sessions, dict) else []):
            if isinstance(v, dict):
                out["sessions"].append({"id": sid, "last_run": v.get("last_run_date") or v.get("last_ran_at") or v.get("last_run"),
                                        "status": v.get("status") or v.get("last_status")})
    except Exception:
        pass
    # B 모델 메타
    try:
        m = json.load(open(os.path.join(REPO, "b_engine/data/b_model_meta.json")))
        out["models"]["B"] = {"trained_through": m.get("trained_through"), "engine": m.get("engine")}
    except Exception:
        pass
    # 스케줄(코드 정의)
    out["schedule"] = [
        {"id": "kr_premarket_refresh", "time": "09:35 KST", "desc": "개장 데이터 갱신(수급 포함)+스캔"},
        {"id": "kr_regular_close", "time": "15:40 KST", "desc": "마감 스캔+일일 ops"},
        {"id": "kr_nxt_close", "time": "20:05 KST", "desc": "NXT 마감 갱신"},
    ]
    return out


def overview(top=6):
    allp = picks()   # 이미 확률 통일 정렬됨 → 픽 화면과 동일 순서
    merged = allp[:top]
    fr = freshness()
    return {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "top_picks": merged, "freshness": fr,
            "counts": {"A": len([p for p in allp if p["signal_class"] == "A"]),
                       "B": len([p for p in allp if p["signal_class"] == "B"])}}
