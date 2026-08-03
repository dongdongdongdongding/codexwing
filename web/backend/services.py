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
    # 2026-07-06 P3 교체: 스윙 = 8y first-touch 랭커(구 후보). 앙상블은 shadow 강등(게이트 감시 지속).
    "kospi_swing":   {"ledger": "kr_swing_candidate_ledger.jsonl",             "label": "코스피 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kosdaq_swing":  {"ledger": "kr_swing_candidate_ledger.jsonl",             "label": "코스닥 스윙",  "kind": "SWING",    "badge": "🟢"},
    "kospi_intraday":{"ledger": "kospi_intraday_swing_ledger.jsonl",           "label": "코스피 장중",  "kind": "INTRADAY", "badge": "🔵"},
    "kosdaq_intraday":{"ledger":"kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl","label":"코스닥 장중","kind":"INTRADAY","badge":"🔵"},

}
TARGET_PCT = 5.0
# 승격 계약(§7-E)의 원장 필드 → 웹 노출 (티어/레짐상태/계약)
_LEDGER_EXTRA_KEYS = ("tier", "tier_threshold", "mkt_state", "mkt_dd20", "hold_days",
                      "target_tp_pct", "ev_pred", "exit_contract", "ret_5d", "ret_5d_d",
                      "atr_pct", "exit_band", "exit_mix_plan")


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


@lru_cache(maxsize=1)
def _us_names():
    """US symbol -> company name (나스닥 8y 패널의 name 컬럼, 1회 캐시)."""
    try:
        import pandas as pd
        fp = os.path.join(RESEARCH, "us_daily/NASDAQ/daily_features_latest_20260629_113805.parquet")
        d = pd.read_parquet(fp, columns=["symbol", "name"]).dropna()
        return dict(zip(d["symbol"].astype(str), d["name"].astype(str)))
    except Exception:
        return {}


def resolve_any_name(code: str, stock_name: str | None = None) -> str:
    """모든 화면 공용 이름 해석: KR=resolve_name 우선(저장된 stock_name이 티커인 경우 방지),
    US=패널 회사명 맵. 실패시 코드 그대로."""
    raw = str(code).split(".")[0]
    if raw.isdigit():
        nm = resolve_name(raw.zfill(6), default="")
        if nm:
            return nm
    else:
        nm = _us_names().get(raw.upper())
        if nm:
            return nm
    sn = str(stock_name or "").strip()
    if sn and sn.split(".")[0] != raw:  # stock_name이 티커 재탕이면 무시
        return sn
    return raw


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




_MEASURED_WIN_CACHE = {"ts": 0.0, "data": {}}


_GATE_VERDICT_CACHE = {"ts": 0.0, "data": {}}
# 웹 레인키 → 재귀게이트 레인명 (report_research_recursion_gate.py LANES)
_GATE_LANE_MAP = {"kospi_swing": "swing_candidate", "kosdaq_swing": "swing_candidate",
                  "kospi_intraday": "kospi_intraday_t5", "kosdaq_intraday": "kosdaq_intraday_t10"}


def _gate_verdicts():
    """재귀게이트 최신 판정 (research_recursion_gate_latest.json, 10분 캐시, fail-safe).
    2026-08-03 PKG-A(§40): §20 'DEGRADE 레인은 스트림 제외' 정책의 발행 연동 —
    DEGRADE 레인 픽은 사이징 권고를 제거하고 관측 전용으로 강등(원장·표시는 유지,
    forward 측정 연속성 보존). 롤백: AG_DEGRADE_STREAM_EXCLUSION=0."""
    import time as _t
    if _t.time() - _GATE_VERDICT_CACHE["ts"] < 600 and _GATE_VERDICT_CACHE["data"]:
        return _GATE_VERDICT_CACHE["data"]
    out = {}
    try:
        fp = os.path.join(REPO, "runtime_state/reports/validation/research_recursion_gate_latest.json")
        rep = json.load(open(fp, encoding="utf-8"))
        for r in rep.get("results", []):
            out[r.get("lane")] = {"verdict": r.get("verdict"), "fwd_ev": r.get("fwd_ev"), "n": r.get("n")}
    except Exception:
        pass
    _GATE_VERDICT_CACHE.update(ts=_t.time(), data=out)
    return out


def _measured_win():
    """레인별 실측 승률 (정산 원장) — §38: 개별 p는 라이브 비캘리브레이션 → 표시용 통계는
    실측으로. n<20 레인은 동결 백테스트 승률로 폴백(출처 표기)."""
    import time as _t
    if _t.time() - _MEASURED_WIN_CACHE["ts"] < 600 and _MEASURED_WIN_CACHE["data"]:
        return _MEASURED_WIN_CACHE["data"]
    out = {}
    spec = [("kospi_swing", "kr_swing_candidate_ledger.jsonl", "policy_ret"),
            ("kosdaq_swing", "kr_swing_candidate_ledger.jsonl", "policy_ret"),
            ("kospi_intraday", "kospi_intraday_swing_ledger.jsonl", "exit_t5_h5"),
            ("kosdaq_intraday", "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5")]
    fallback = {"kospi_intraday": (92, "백테스트 q0.5"), "kosdaq_intraday": (72, "백테스트"),
                "kospi_swing": (62, "백테스트 8y"), "kosdaq_swing": (62, "백테스트 8y")}
    for lane, fn, field in spec:
        try:
            vals = [r[field] for r in _read_ledger(fn) if isinstance(r.get(field), (int, float))]
            if len(vals) >= 20:
                out[lane] = (round(sum(1 for v in vals if v > 0.3) / len(vals) * 100), f"실측 {len(vals)}건")
                continue
        except Exception:
            pass
        out[lane] = fallback.get(lane, (None, ""))
    _MEASURED_WIN_CACHE.update(ts=_t.time(), data=out)
    return out


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
    # 근거 한 줄 — 가진 필드로 조합 (모델이 "왜"를 말하게)
    bits = []
    mw = _measured_win().get(lane_key)
    if mw and mw[0] is not None:
        row["measured_win"] = mw[0]
        row["measured_win_src"] = mw[1]
        bits.append(f"승률 {mw[0]}% ({mw[1]})")
    elif row.get("prob") is not None:
        bits.append(f"모델확률 {row['prob']}% (미캘리브레이션)")
    cv = (extra or {}).get("close_vwap")
    if isinstance(cv, (int, float)):
        bits.append(f"VWAP {'상방' if cv >= 0 else '하방'} {cv:+.1f}%")
    liq_eok = row.get("liq억") or (extra or {}).get("liq_eok")
    if liq_eok:
        bits.append(f"유동성 {liq_eok}억")
    if row.get("mkt_state") == "RISK_OFF":
        bits.append("⚠약세장")
        # §24 항복 해부: 시장 동반붕괴 중 항복픽 = 반등코어 (8y 픽레벨 +1.51 CI>0, 7/8년 —
        # 시장 상승 중 단독붕괴는 반대로 음수). 정보 태그만, 계약/발행 불변.
        r5 = row.get("ret_5d") if row.get("ret_5d") is not None else (extra or {}).get("ret_5d_d")
        if isinstance(r5, (int, float)) and r5 <= -13:
            bits.append("반등코어(동반항복)")
    if row.get("tier") == "PRIMARY":
        bits.append("고확신 선별")
    if (extra or {}).get("rationale_extra"):
        bits.append(str(extra["rationale_extra"]))
    if bits:
        row["rationale"] = " · ".join(bits)
    # 권장 비중 (§20 구성수학, swing-main-wdu2): 검증 레인 = 총자본 2%/픽 (8:2, 분수Kelly 0.10).
    # 관측(shadow)·후보성 레인은 사이징 권고 제외 — forward 미확인 스트림에 실자본 배분 금지.
    # 2026-07-23 운영자 승인: 스윙 EXCEED(게이트 n=61, 기대 2.2배) → 3% 승격.
    # 2026-08-03 PKG-A(운영자 승인): 3%→2% 원복 — §36 EXCEED는 크래시 미성숙 표본의 래칫이었고
    # (§39: 07-23 승격 직후 크래시분 성숙하며 DEGRADE 전환), §39 사이징 원복 권고 집행.
    # 재승격 조건: §40 래칫 메타규칙(성숙시차 지연 표본 + n>=100 + 10영업일 엠바고) 충족 시.
    _swing_lanes = {"kospi_swing", "kosdaq_swing", "swing_candidate"}
    _itd_lanes = {"kospi_intraday", "kosdaq_intraday", "kosdaq_intraday_3d_t5_vwap_guard"}
    if row.get("tier") not in ("VETO_DD_OVERHEAT", "VETO_REBOUND_PHASE"):
        if lane_key in _swing_lanes:
            row["size_pct_total"] = 2.0
            row["size_note"] = "총자본 2%/픽 (§39 원복 2026-08-03 · 8:2 정책 · §20 f=0.10)"
        elif lane_key in _itd_lanes:
            row["size_pct_total"] = 2.0
            row["size_note"] = "총자본 2%/픽 (8:2 정책 · §20)"
    # PKG-A(§40): DEGRADE 레인 스트림 제외 — 사이징 권고 제거 + 관측 라벨 (§20 정책 집행).
    # 픽 자체는 계속 표시(nyg6 계약: 후보 가시성 유지 + 라우팅만 명시적 차단), 원장 채점도 지속.
    if os.environ.get("AG_DEGRADE_STREAM_EXCLUSION", "1") == "1":
        gv = _gate_verdicts().get(_GATE_LANE_MAP.get(lane_key) or "")
        if gv and gv.get("verdict") == "DEGRADE":
            row.pop("size_pct_total", None)
            row["stream_excluded"] = True
            row["size_note"] = (f"⛔ 발행 제외(관측) — 재귀게이트 DEGRADE (forward n={gv.get('n')} "
                                f"EV {gv.get('fwd_ev')}, §20 스트림 제외 정책)")
            row["rationale"] = ((row.get("rationale") + " · ") if row.get("rationale") else "") + "⛔관측전용(DEGRADE)"
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
    ("swing_candidate", "KOSPI"): "kospi_swing",
    ("swing_candidate", "KOSDAQ"): "kosdaq_swing",
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
    # 2026-08-03 PKG-A(§40): B 레인 발행 중지 — 마커 존재 시 stale 픽을 계속 노출하지 않음.
    # (스캔이 멈추면 b_picks_latest.json 날짜가 동결되므로 명시적 서스펜션 게이트 필요)
    if os.path.exists(os.path.join(REPO, "b_engine/data/b_lane_suspended.json")):
        return []
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
                                     "tier": p.get("tier"),
                                     # §26 C1: RISK_OFF에서 B 발행보류 (α 1/6 + 라이브 -5.1) — 보류 사유 표시
                                     "regime_hold": d.get("regime_hold") or None,
                                     "rationale_extra": ("⛔ 약세장 보류 — RISK_OFF에서 B α는 정상장의 1/6 (§26), 관측만"
                                                         if d.get("regime_hold") else None)}))
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
    """나스닥 픽 = 세션테이프 shadow 원장 (§12-D: 유일한 플라시보-분리 신호, rank-1/일).
    2026-07-07 교체: 이전엔 구식 범용 스캔(RUN-*)의 음수엣지 종목이 확률 50% 스텁으로 표시되던 문제."""
    fp = os.path.join(REPO, "runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl")
    if not os.path.exists(fp):
        return []
    rows = []
    for ln in open(fp, encoding="utf-8"):
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    if not rows:
        return []
    last = max(str(r.get("date", "")) for r in rows)
    out = []
    for r in rows:
        if str(r.get("date")) != last:
            continue
        out.append(_pick_row(r.get("symbol"), "NASDAQ", "nasdaq_swing",
                             entry=r.get("entry"), prob=r.get("p"),
                             name=resolve_any_name(r.get("symbol")), scan_date=last, source="A",
                             extra={"lane_label": "나스닥 세션테이프", "kind": "SWING", "badge": "🟢",
                                    "hold_days": 5, "target_tp_pct": 5.0,
                                    "tier": "SHADOW" if r.get("tier") == "SHADOW" else r.get("tier"),
                                    "rationale_extra": "관측 shadow — forward n>=30 전 실자본 금지"}))
    return out


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


_QUOTE_CACHE: dict = {}   # code -> (ts, row) — 25s TTL (매수타이밍 30s 폴링과 정합)


def prices(codes, budget=None):
    """KIS 시세 일괄 조회 — 2026-07-14 수리: 8s 순차 예산이 36코드 중 24개를 자르던 병목
    (사용자 보고 '시세 조회 실패'). 캐시(25s) + 4-워커 병렬 + 코드수 비례 예산."""
    now = time.time()
    codes6 = [str(c).split(".")[0].zfill(6) for c in codes]
    out = {c: r for c, (ts, r) in _QUOTE_CACHE.items() if c in codes6 and now - ts < 25}
    todo = [c for c in codes6 if c not in out]
    if not todo:
        return out
    if budget is None:
        budget = min(25.0, 3.0 + 0.35 * len(todo))
    cli = _kis()
    if cli is None:
        return out
    import queue
    q_in = queue.Queue()
    for c in todo:
        q_in.put(c)

    def work():
        while True:
            try:
                code = q_in.get_nowait()
            except Exception:
                return
            try:
                q = cli.quote_snapshot(code)
                row = {"price": q.get("last_price"), "change_pct": q.get("day_change_pct"),
                       "status": q.get("source_status")}
                out[code] = row
                _QUOTE_CACHE[code] = (time.time(), row)
            except Exception:
                pass
    threads = [threading.Thread(target=work, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()
    deadline = time.time() + budget
    for t in threads:
        t.join(max(0.1, deadline - time.time()))
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
    # 모델 학습 신선도 — 프론트가 값을 그대로 렌더링하므로 반드시 문자열(객체 넣으면 React 크래시).
    try:
        bm = json.load(open(os.path.join(REPO, "b_engine/data/b_model_meta.json")))
        out["b_model"] = f"학습 {str(bm.get('trained_at',''))[:16]} · 데이터 ~{bm.get('trained_through')} (라벨상 −6세션 정상)"
    except Exception:
        out["b_model"] = None
    try:
        kb = json.load(open(os.path.join(REPO, "runtime_state/reports/learning/kosdaq_1500_bundle_retrain_latest.json")))
        out["kosdaq_bundle"] = f"재학습 {str(kb.get('retrained_at',''))[:16]} · {kb.get('train_span')}"
    except Exception:
        out["kosdaq_bundle"] = None
    return out


def chart(code, tf="day", days=120):
    """차트 데이터. tf=minute(분봉 OHLC, intraday캐시) / day(일봉: ohlc_daily 있으면 OHLC, 없으면 close 라인)."""
    import pandas as pd
    raw = str(code).split(".")[0]
    if not raw.isdigit():  # 미국 심볼 → 시간봉 캐시 (351종목, 일일 갱신)
        fp = os.path.join(RESEARCH, "us_daily", "hourly", f"{raw.upper()}.parquet")
        if not os.path.exists(fp):
            return {"type": "candle", "tf": tf, "bars": []}
        h = pd.read_parquet(fp)
        h.index = pd.to_datetime(h.index)
        h = h.sort_index()
        if tf == "minute":  # 시간봉 최근 ~10거래일
            h = h.tail(7 * 10)
            bars = [{"time": int(t.timestamp()), "open": float(r.Open), "high": float(r.High),
                     "low": float(r.Low), "close": float(r.Close)} for t, r in h.iterrows()]
            return {"type": "candle", "tf": "minute", "bars": bars}
        d = h.resample("1D").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
        d = d.tail(days)
        bars = [{"time": str(t.date()), "open": float(r.Open), "high": float(r.High),
                 "low": float(r.Low), "close": float(r.Close)} for t, r in d.iterrows()]
        return {"type": "candle", "tf": "day", "bars": bars}
    code6 = raw.zfill(6)
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
    try:
        detail["events"] = _events_ahead(code6, detail["market"])
    except Exception:
        detail["events"] = []
    return detail


def _events_ahead(code6: str, market: str):
    """픽 보유기간(~5거래일) 내 리스크 이벤트 — 만기일(계산) + US 어닝스 예정(캐시).
    KR 실적 '예정일'은 소스 미확보(사후 공시만) — 확보 시 추가."""
    import pandas as pd
    out = []
    today = pd.Timestamp.now().normalize()
    for mo in (today, today + pd.offsets.MonthBegin(1)):
        first = pd.Timestamp(mo.year, mo.month, 1)
        expiry = first + pd.Timedelta(days=(3 - first.weekday()) % 7 + 7)
        d = (expiry - today).days
        if 0 <= d <= 7:
            quad = expiry.month in (3, 6, 9, 12)
            out.append({"type": "동시만기(네 마녀)" if quad else "옵션만기",
                        "date": str(expiry.date()), "d_left": int(d),
                        "note": "만기 주간 변동성 확대 가능"})
            break
    if market not in ("KOSPI", "KOSDAQ"):
        try:
            e = pd.read_parquet(os.path.join(RESEARCH, "us_daily/earnings_dates.parquet"))
            e = e[e["symbol"] == code6]
            ts = pd.to_datetime(e["ann_ts"], errors="coerce", utc=True).dt.tz_localize(None)
            fut = ts[(ts >= today) & (ts <= today + pd.Timedelta(days=10))]
            if len(fut):
                d = (fut.min().normalize() - today).days
                out.append({"type": "실적발표", "date": str(fut.min().date()), "d_left": int(d),
                            "note": "어닝스 갭 리스크 — 보유 중 발표"})
        except Exception:
            pass
    return out


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
    ("swing_ensemble", "KOSPI"): "코스피 스윙(구)",
    ("swing_ensemble", "KOSDAQ"): "코스닥 스윙(구)",
    ("swing_candidate", "KOSPI"): "코스피 스윙",
    ("swing_candidate", "KOSDAQ"): "코스닥 스윙",
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
    # 스윙 (P3 교체 후 본선 — 익일 시가 진입, +5% 터치/5일)
    rows = _read_ledger("kr_swing_candidate_ledger.jsonl")
    vals = [float(r["policy_ret"]) for r in rows if isinstance(r.get("policy_ret"), (int, float))]
    out["lanes"]["swing"] = {"label": "스윙 (+5% 터치/5일, 익일시가)", **_agg(vals)}
    # §29 스윙 출구혼합 shadow (동일 픽, 대체 출구 병행채점 — 계약 불변)
    try:
        rows = _read_ledger("kr_swing_candidate_ledger.jsonl")
        vals = [float(r["exit_mix"]) - 0.3 for r in rows if isinstance(r.get("exit_mix"), (int, float))]
        out["lanes"]["swing_exit_mix"] = {"label": "스윙 출구혼합 shadow (§29 검증중)", **_agg(vals)}
    except Exception:
        pass
    # 나스닥 세션테이프 (관측 shadow, +5% 터치/5일 정책 채점)
    try:
        fp = os.path.join(REPO, "runtime_state/reports/us_research/nasdaq_session_tape_ledger.jsonl")
        rows = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()] if os.path.exists(fp) else []
        vals = [float(r["policy_ret"]) for r in rows if isinstance(r.get("policy_ret"), (int, float))]
        out["lanes"]["nasdaq_tape"] = {"label": "나스닥 세션테이프 (+5% 터치/5일, 관측)", **_agg(vals)}
    except Exception:
        pass
    # B 시장중립 (알파 = 시장대비 %p — 절대수익 아님 주의)
    try:
        rows = [json.loads(l) for l in open(os.path.join(REPO, "b_engine/data/b_shadow.jsonl"), encoding="utf-8") if l.strip()]
        st = [r for r in rows if r.get("status") == "settled" and isinstance(r.get("alpha"), (int, float))]
        vals = [float(r["alpha"]) for r in st]
        out["lanes"]["b_alpha"] = {"label": "B 시장중립 (α=시장대비%p, 절대수익 아님)", **_agg(vals)}
        pr = [float(r["alpha"]) for r in st if r.get("tier") == "PRIMARY"]
        if pr:
            out["lanes"]["b_primary_alpha"] = {"label": "B PRIMARY top3 (α)", **_agg(pr)}
    except Exception:
        pass
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

    LED = {"코스피 스윙": ("kr_swing_candidate_ledger.jsonl", "KOSPI"),
           "코스닥 스윙": ("kr_swing_candidate_ledger.jsonl", "KOSDAQ"),
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


# ── 매수 타이밍 (§26 후속, 운영자 요청): "지금 가격에 사도 되나" — 계약 오버레이 판단 ──
def buy_timing(days=5):
    """최근 N거래일 픽 전체 + 계약 대비 현재 위치 → 매수 신호등.
    상태: DONE(터치완료=추격금지) EXPIRED(만기) GREEN(기준가~+1%) YELLOW(+1~2.5%) RED(>+2.5%).
    근거: 진입가 초과분은 검증된 엣지를 1:1로 소진 (first-touch 계약 구조)."""
    import pandas as pd
    oh = pd.read_parquet(os.path.join(RESEARCH, "ohlc_daily.parquet"))
    oh["date"] = pd.to_datetime(oh["date"])
    sessions = sorted(oh["date"].unique())
    cutoff = sessions[-days] if len(sessions) >= days else sessions[0]
    picks = []
    for key, meta in LANES.items():
        for r in _read_ledger(meta["ledger"]):
            d = r.get("date")
            if not d or pd.Timestamp(d) < cutoff:
                continue
            mkt = r.get("market") or _market_of(r.get("ticker"))
            if key.startswith("kospi") and mkt != "KOSPI":
                continue
            if key.startswith("kosdaq") and mkt != "KOSDAQ":
                continue
            if r.get("tier") in ("CANDIDATE", "VETO_DD_OVERHEAT", "VETO_REBOUND_PHASE"):
                continue  # 발행 안 된 픽은 매수 화면에서 제외
            code = str(r.get("ticker", "")).split(".")[0].zfill(6)
            tp = float(r.get("target_tp_pct") or (10.0 if "kosdaq_intraday" in key else 5.0))
            swing = meta.get("kind") == "SWING"
            h = oh[(oh["code"] == code) & (oh["date"] > pd.Timestamp(d))].sort_values("date").head(6)
            if swing:
                # 익일시가 진입 — 아직 미개장(진입 전)이면 기준가=전일종가 참조
                ref = float(h["open"].iloc[0]) if len(h) else float(r.get("close") or 0)
                win = h.head(5)
            else:
                ref = float(r.get("entry_reference_price") or r.get("close_1500") or r.get("close") or 0)
                win = h.head(5)
            if not ref:
                continue
            target = ref * (1 + tp / 100)
            touched = bool((win["high"].astype(float) >= target).any()) if len(win) else False
            elapsed = len(win)
            left = max(0, 5 - elapsed)
            # 트레일 (ant.wiki RRG 스타일): 발행(여력=tp, 잔여5) → 매 세션 종가 좌표 경로
            trail = [{"d": str(pd.Timestamp(d).date()), "headroom": round(tp, 2), "left": 5}]
            for i in range(len(win)):
                c_i = float(win["close"].iloc[i])
                trail.append({"d": str(win["date"].iloc[i].date()),
                              "headroom": round((target / c_i - 1) * 100, 2), "left": max(0, 5 - (i + 1))})
            picks.append({"code": code, "ticker": r.get("ticker"), "name": resolve_any_name(code),
                          "lane": key, "lane_label": meta["label"], "kind": meta["kind"], "badge": meta["badge"],
                          "scan_date": d, "ref": round(ref, 1), "target": round(target, 1), "tp_pct": tp,
                          "age": elapsed, "sessions_left": left, "touched": touched,
                          "tier": r.get("tier"), "mkt_state": r.get("mkt_state"),
                          "prob": r.get("p"), "trail": trail,
                          "entry_note": "익일 시가 진입" if swing else "15:00 종가 기준"})
    # 현재가 일괄 (KIS)
    quotes = prices(list({p["code"] for p in picks}))
    for p in picks:
        q = quotes.get(p["code"]) or {}
        cur = q.get("price")
        p["current"] = cur
        p["change_pct"] = q.get("change_pct")
        if cur and p["ref"]:
            pos = (float(cur) / p["ref"] - 1) * 100
            p["pos_vs_ref"] = round(pos, 2)
            p["headroom"] = round((p["target"] / float(cur) - 1) * 100, 2)
            if p["touched"] or float(cur) >= p["target"]:
                # ohlc는 전일까지만 — 당일 장중 목표 초과도 현재가로 터치완료 처리
                p["touched"] = True
                p["state"], p["state_label"] = "DONE", "터치완료 — 추격 금지"
            elif p["sessions_left"] <= 0:
                p["state"], p["state_label"] = "EXPIRED", "만기 — 계약 종료"
            elif pos <= 1.0:
                p["state"], p["state_label"] = "GREEN", "기준가권 — 계약 그대로 유효"
            elif pos <= 2.5:
                p["state"], p["state_label"] = "YELLOW", f"기준가 +{pos:.1f}% — 여력 절반 소진"
            else:
                p["state"], p["state_label"] = "RED", f"기준가 +{pos:.1f}% — 추격 비추천"
        else:
            # KIS 실패 폴백: 최신 종가로 잠정 판정 (전일 기준임을 명시)
            try:
                g = oh[oh["code"] == p["code"]]
                cur = float(g["close"].iloc[-1]) if len(g) else None
            except Exception:
                cur = None
            if cur and p["ref"]:
                pos = (cur / p["ref"] - 1) * 100
                p["current"] = cur
                p["pos_vs_ref"] = round(pos, 2)
                p["headroom"] = round((p["target"] / cur - 1) * 100, 2)
                if p["touched"] or cur >= p["target"]:
                    p["state"], p["state_label"] = "DONE", "터치완료 — 추격 금지"
                elif p["sessions_left"] <= 0:
                    p["state"], p["state_label"] = "EXPIRED", "만기 — 계약 종료"
                elif pos <= 1.0:
                    p["state"], p["state_label"] = "GREEN", "기준가권 (전일종가 기준)"
                elif pos <= 2.5:
                    p["state"], p["state_label"] = "YELLOW", f"기준가 +{pos:.1f}% (전일종가 기준)"
                else:
                    p["state"], p["state_label"] = "RED", f"기준가 +{pos:.1f}% (전일종가 기준)"
            else:
                p["state"], p["state_label"] = "UNKNOWN", "시세 조회 실패"
    picks.sort(key=lambda x: (x["scan_date"], x["lane"]), reverse=True)
    # 오늘의 최선 (§27, swing-main-xfnc): 기권일 강제발행은 실측 EV<0으로 기각 —
    # 대신 레인 교차로 "지금 살 수 있는(GREEN) 픽 중 실측 티어 승률 최고" 1개를 지목.
    # 스윙(매일 top3)·나스닥(매일 rank-1)이 기권하지 않으므로 항상 후보가 존재.
    TIER_WIN = {("kospi_intraday", "PRIMARY"): 86, ("kosdaq_intraday", None): 72,
                ("kospi_swing", None): 62, ("kosdaq_swing", None): 62}
    def _w(p):
        return TIER_WIN.get((p["lane"], p.get("tier"))) or TIER_WIN.get((p["lane"], None)) or 50
    live = [p for p in picks if p["state"] == "GREEN"]
    pool2 = live or [p for p in picks if p["state"] == "YELLOW"]
    if pool2:
        best = max(pool2, key=lambda p: (_w(p), -(p.get("pos_vs_ref") or 0)))
        best["today_best"] = True
        best["today_best_note"] = f"레인 교차 최선 — {best['lane_label']} 실측 승률 ~{_w(best)}%"
    return {"days": days, "asof": datetime.now().strftime("%Y-%m-%d %H:%M"), "picks": picks}


# ── 국면 나침반 (2026-07-17, 운영자 요청): 실시간 지수 → 검증된 레짐 지도 투영 ──
_COMPASS_CACHE = {"ts": 0.0, "data": None}

# 8y 실증 forward 5d (harness: 국면 백테스트 2026-07-17) — 판단 근거를 숫자로 명시
# 2026-07-18 레퍼리 재심사(§33): 지수 forward 표는 블록부트스트랩+시프트플라시보에서
# 코스피 과열만 유의 — 나머지 판단 근거는 픽 단위 검증(§24/§26/§32 레인 증거)으로 교체.
_PHASE_MAP = {
    "KOSPI":  {"동반붕괴": ("LONG", "레인: 항복픽 +4.9/승100% (§24 픽단위)"), "반등국면": ("WAIT", "레인 EV −4.6 · 베토 활성 (§26)"),
               "NORMAL": ("LEAN_LONG", "레인 +4.07/81% (§17)"), "과열": ("LONG", "지수 +1.24%/5d 유일 유의 (§33) · 레인 과열픽 +5.5")},
    "KOSDAQ": {"동반붕괴": ("LONG", "레인: 항복반등 코어 (§24) · 발행은 캘리브레이터 판단"), "반등국면": ("WAIT", "KR 반등국면 독성 (§26, 레인 증거)"),
               "NORMAL": ("NEUTRAL", "지수·레인 모두 중립대"), "과열": ("NEUTRAL", "증거 중립")},
    "NASDAQ": {"동반붕괴": ("LONG", "레인 +1.38 (§32 픽단위, CI 0포함)"), "반등국면": ("LEAN_LONG", "KR과 달리 독성 증거 없음 (§31·32)"),
               "NORMAL": ("LEAN_LONG", "레인 +1.00 CI>0 (§32 픽단위)"), "과열": ("NEUTRAL", "레인 −1.72 관측플래그 (§32)")},
}
_JUDGE_LABEL = {"LONG": "🟢 롱 우호", "LEAN_LONG": "🟡 약한 롱", "NEUTRAL": "🟡 중립", "WAIT": "🔴 관망(현금)"}


def _phase_of(lvl):
    import pandas as pd
    dd20 = float((lvl.iloc[-1] / lvl.iloc[-20:].max() - 1) * 100)
    r5 = float((lvl.iloc[-1] / lvl.iloc[-6] - 1) * 100)
    r20 = float((lvl.iloc[-1] / lvl.iloc[-21] - 1) * 100)
    if r5 <= -3:
        ph = "동반붕괴"
    elif dd20 < -8 and r5 > -3:
        ph = "반등국면"
    elif dd20 > -2 and r20 > 8:
        ph = "과열"
    else:
        ph = "NORMAL"
    return ph, round(dd20, 1), round(r5, 1)


def market_compass():
    """코스피/코스닥/나스닥(+선물 야간신호) 실시간 국면 → 8y 검증 지도 기반 롱/숏 판단.
    '숏' 대신 관망(현금) — 검증된 숏 엣지는 없음(정직). 60s 캐시."""
    import time as _t
    if _t.time() - _COMPASS_CACHE["ts"] < 60 and _COMPASS_CACHE["data"]:
        return _COMPASS_CACHE["data"]
    import pandas as pd
    out = {"asof": datetime.now().strftime("%H:%M:%S"), "markets": [], "night": None}
    try:
        import FinanceDataReader as fdr
        hist = {}
        for sym, mkt in (("KS11", "KOSPI"), ("KQ11", "KOSDAQ"), ("IXIC", "NASDAQ")):
            hist[mkt] = fdr.DataReader(sym, (pd.Timestamp.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d"))["Close"]
        live = {}
        try:
            import yfinance as yf
            for ysym, mkt in (("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ"), ("^IXIC", "NASDAQ")):
                try:
                    fi = yf.Ticker(ysym).fast_info
                    lp = fi.get("last_price") or fi.get("lastPrice")
                    if lp:
                        live[mkt] = float(lp)
                except Exception:
                    pass
            try:
                nq = yf.Ticker("NQ=F").fast_info
                nql, nqp = nq.get("last_price"), nq.get("previous_close")
                if nql and nqp:
                    chg = (float(nql) / float(nqp) - 1) * 100
                    out["night"] = {"symbol": "나스닥 선물(NQ, 24h)", "change_pct": round(chg, 2),
                                    "note": "KR 야간 프록시 — 익일 시가 갭이 대부분 흡수(§30), 방향 참고용"}
            except Exception:
                pass
        except Exception:
            pass
        for mkt in ("KOSPI", "KOSDAQ", "NASDAQ"):
            lvl = hist[mkt].copy()
            if mkt in live and live[mkt] > 0:
                lvl = pd.concat([lvl, pd.Series([live[mkt]], index=[pd.Timestamp.now()])])
            ph, dd20, r5 = _phase_of(lvl)
            judge, basis = _PHASE_MAP[mkt][ph]
            out["markets"].append({"market": mkt, "phase": ph, "judge": judge, "judge_label": _JUDGE_LABEL[judge],
                                   "basis": f"8y: {basis}", "dd20": dd20, "ret5": r5,
                                   "live": mkt in live,
                                   "lane_note": ("항복픽 골든존 — 픽 뜨면 사는 국면" if ph == "동반붕괴" else
                                                 "레인 베토 활성 구간" if (ph == "반등국면" and mkt != "NASDAQ") else "")})
    except Exception as exc:
        out["error"] = repr(exc)[:120]
    _COMPASS_CACHE.update(ts=_t.time(), data=out)
    return out
