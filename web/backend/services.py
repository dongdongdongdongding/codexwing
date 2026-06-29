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

from modules.ticker_names import resolve_name  # noqa: E402

# 레인 메타: ledger 파일 · 표시명 · 신호유형 · 시장(원장에 있으면 우선)
LANES = {
    "kospi_swing":   {"ledger": "swing_ensemble_ledger.jsonl",                 "label": "코스피 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kosdaq_swing":  {"ledger": "swing_ensemble_ledger.jsonl",                 "label": "코스닥 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kospi_intraday":{"ledger": "kospi_intraday_swing_ledger.jsonl",           "label": "코스피 장중",  "kind": "INTRADAY", "badge": "🔵"},
    "kosdaq_intraday":{"ledger":"kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl","label":"코스닥 장중","kind":"INTRADAY","badge":"🔵"},
}
TARGET_PCT = 5.0


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


def _pick_row(code, market, lane_key, *, entry=None, prob=None, name=None, scan_date=None, source="A", extra=None):
    code6 = str(code).split(".")[0].zfill(6)
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
        "prob": round(float(prob) * 100, 1) if (prob is not None and prob <= 1.5) else (round(float(prob), 1) if prob is not None else None),
        "entry": float(entry) if entry else None,
        "target": round(float(entry) * (1 + TARGET_PCT / 100), 2) if entry else None,
        "target_pct": TARGET_PCT,
    }
    if extra:
        row.update(extra)
    return row


def a_picks(lane=None):
    """A 레인 픽 — 각 레인 최신 스캔일만. lane=None이면 전체."""
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
        recs = [r for r in led if (str(r.get("market", "")).upper() == want_market or not r.get("market"))]
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
            rows.append(_pick_row(code, want_market or mk, key, entry=r.get("entry_reference_price"),
                                  prob=r.get("p"), scan_date=last, source="A"))
    return rows


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
                              entry=p.get("close"), prob=None, name=p.get("name"),
                              scan_date=d.get("scan_date"), source="B",
                              extra={"lane_label": "B 시장중립", "kind": "B", "badge": "🟣",
                                     "pred_alpha_5d": p.get("pred_alpha_5d"), "smart5": p.get("smart5"),
                                     "rsi14": p.get("rsi14"), "hold_days": p.get("hold_days")}))
    return rows


def picks(lane=None):
    if lane == "b_market_neutral":
        return b_picks()
    if lane:
        return a_picks(lane)
    return a_picks() + b_picks()


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


def overview(top=6):
    allp = picks()
    # 통합 상위: prob 있는 A 우선 + B 일부. 단순 정렬(추후 통합 점수).
    a = [p for p in allp if p["signal_class"] == "A" and p.get("prob") is not None]
    b = [p for p in allp if p["signal_class"] == "B"]
    a.sort(key=lambda x: x.get("prob") or 0, reverse=True)
    merged = (a[: max(3, top - 2)] + b[:2])[:top]
    fr = freshness()
    return {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "top_picks": merged, "freshness": fr,
            "counts": {"A": len([p for p in allp if p["signal_class"] == "A"]),
                       "B": len(b)}}
