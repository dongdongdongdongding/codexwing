"""스캔 피드 (게시물 모델) — 스캔=기본단위(run_id), 자동+수동+디스코드 누적.
게시물 목록 → 티커카드 → 정밀분석 패널. 정밀분석은 로컬 JSON 캐시(누적), Gemini lazy-once.

결정(07 기획): 1b(Gemini 클릭시1회+캐시) 2a(로컬JSON) 3a(스캔피드) 4b(피처=스냅샷·차트=라이브).
소스: runtime_state/scan_sources.json (manual/discord 기록) + 기본 auto. run_id 접두사로 레인 추론.
"""
from __future__ import annotations
import os, json, time
from datetime import datetime, timezone
from web.backend import services as S

try:
    from zoneinfo import ZoneInfo
    _KST = ZoneInfo("Asia/Seoul")
except Exception:
    _KST = None


def _fmt_kst(ts):
    """저장 타임스탬프(scan_deep_reports=UTC) → KST 'YYYY-MM-DD HH:MM:SS' 표시.
    날짜만(예: '2026-06-30')이면 그대로. 파싱실패시 원본 19자."""
    s = str(ts or "")
    if not s:
        return ""
    if len(s) <= 10:
        return s
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)  # scan_deep_reports는 UTC 기록
        if _KST is not None:
            dt = dt.astimezone(_KST)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return s[:19].replace("T", " ")

REPO = S.REPO
CACHE_DIR = os.path.join(REPO, "runtime_state", "precision_cache")
SOURCES_PATH = os.path.join(REPO, "runtime_state", "scan_sources.json")
os.makedirs(CACHE_DIR, exist_ok=True)

_LIST_CACHE = {"ts": 0.0, "data": None}
JOURNAL = os.path.join(REPO, "runtime_state", "local_short_term", "scan_runs.jsonl")


def _journal_rows(limit=30):
    """수동 스캔 실행 저널 (jobs._write_journal) — 버튼 1회=1행, 스텝별 결과/사유 포함."""
    try:
        lines = open(JOURNAL, encoding="utf-8").read().splitlines()[-limit:]
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []


def record_source(run_id, source):
    """스캔 소스 기록(manual/discord/auto). 트리거가 호출."""
    if not run_id:
        return
    try:
        m = json.load(open(SOURCES_PATH)) if os.path.exists(SOURCES_PATH) else {}
    except Exception:
        m = {}
    m[str(run_id)] = source
    try:
        json.dump(m, open(SOURCES_PATH, "w"), ensure_ascii=False)
    except Exception:
        pass


def _sources():
    try:
        return json.load(open(SOURCES_PATH)) if os.path.exists(SOURCES_PATH) else {}
    except Exception:
        return {}


def _infer_source(run_id, override):
    if run_id in override:
        return override[run_id]
    return "auto"  # 스케줄/일일ops 기본


def _lane_label(bucket, mode, run_id):
    b = str(bucket or "")
    if "swing_candidate" in b or run_id.startswith("SWING-CAND"):
        return "스윙"
    if "swing_ensemble" in b or run_id.startswith("SWING-ENS"):
        return "스윙(구)"
    if "nasdaq_session_edge" in b or run_id.startswith("NASDAQ-SESSION-EDGE"):
        return "나스닥 세션"
    if "kospi_intraday" in b or run_id.startswith("KOSPI-ITD"):
        return "코스피 장중"
    if "kosdaq_intraday" in b or run_id.startswith("KQ-ITD"):
        return "코스닥 장중"
    return str(mode or bucket or "스캔")


def list_scans(limit=40, source=None, market=None):
    """게시물 목록 — scan_deep_reports run_id 그룹 + B 스캔. 5분 캐시."""
    if time.time() - _LIST_CACHE["ts"] < 300 and _LIST_CACHE["data"] is not None:
        posts = _LIST_CACHE["data"]
    else:
        posts = _build_list()
        _LIST_CACHE.update(ts=time.time(), data=posts)
    out = posts
    if source:
        out = [p for p in out if p["source"] == source]
    if market:
        out = [p for p in out if market.upper() in p["markets"]]
    return {"count": len(out), "scans": out[:limit]}


def _build_list():
    posts = {}
    override = _sources()
    db = S._db()
    if db is not None:
        try:
            q = (db.client.table("scan_deep_reports")
                 .select("run_id,market,decision_bucket,scan_mode,generated_at")
                 .order("generated_at", desc=True).limit(800).execute())
            for r in (q.data or []):
                rid = r.get("run_id")
                if not rid:
                    continue
                p = posts.setdefault(rid, {"scan_id": rid, "time": str(r.get("generated_at")),
                                           "markets": set(), "lanes": set(), "pick_count": 0})
                p["markets"].add(str(r.get("market") or ""))
                p["lanes"].add(_lane_label(r.get("decision_bucket"), r.get("scan_mode"), rid))
                p["pick_count"] += 1
                if str(r.get("generated_at")) > p["time"]:
                    p["time"] = str(r.get("generated_at"))
        except Exception:
            pass
    # 수동 스캔 저널 — 버튼 1회=게시물 1건 보장 (0픽/저장픽/세션블록/에러 사유 포함, swing-main-bbe9).
    # 같은 실행이 라우팅으로 만든 DB run_id 게시물은 저널 게시물이 대체(중복 억제).
    covered = set()
    jposts = []
    for row in _journal_rows():
        lanes, markets, notes, n = [], set(), [], 0
        for st in row.get("steps", []):
            if st.get("label"):
                lanes.append(str(st["label"]))
            if st.get("run_id"):
                covered.add(str(st["run_id"]))
            n += len(st.get("picks") or [])
            if st.get("market"):
                markets.add(str(st["market"]))
            note = str(st.get("note") or "")
            if note and not note.endswith("픽") and not note.startswith("top"):
                notes.append(f"{st.get('label')}: {note.split('.')[0]}")
        jposts.append({"scan_id": str(row.get("scan_id")), "time": _fmt_kst(row.get("time")),
                       "source": "manual", "markets": sorted(m for m in markets if m),
                       "lanes": lanes, "pick_count": n,
                       "note": (" · ".join(notes)[:220] or None)})
    res = list(jposts)
    for rid, p in posts.items():
        if rid in covered:
            continue
        res.append({"scan_id": rid, "time": _fmt_kst(p["time"]),
                    "source": _infer_source(rid, override), "markets": sorted(m for m in p["markets"] if m),
                    "lanes": sorted(p["lanes"]), "pick_count": p["pick_count"], "note": None})
    # B 스캔(b_picks_latest)을 게시물 1건으로
    try:
        bp = json.load(open(os.path.join(REPO, "b_engine/data/b_picks_latest.json")))
        res.append({"scan_id": f"B-{bp.get('scan_date')}", "time": bp.get("scan_date"),
                    "source": "auto", "markets": ["B시장중립"], "lanes": ["B 시장중립"],
                    "pick_count": len(bp.get("picks", []))})
    except Exception:
        pass
    res.sort(key=lambda x: x["time"] or "", reverse=True)
    return res


def scan_detail(scan_id):
    """게시물의 티커카드 — 해당 run_id 픽들(스캔시점 점수/진입)."""
    if scan_id.startswith("MANUAL-"):
        for row in reversed(_journal_rows(120)):
            if str(row.get("scan_id")) != scan_id:
                continue
            cards, notes = [], []
            for st in row.get("steps", []):
                note = str(st.get("note") or "")
                if note and not note.endswith("픽") and not note.startswith("top"):
                    notes.append(f"{st.get('label')}: {note}")
                for p in st.get("picks") or []:
                    t = str(p.get("ticker") or "")
                    code = t.split(".")[0]
                    cards.append({"ticker": t, "code": code.zfill(6) if code.isdigit() else code,
                                  "name": S.resolve_any_name(t, p.get("name")),
                                  "market": str(p.get("market") or S._market_of(t)),
                                  "lane": str(st.get("label") or ""),
                                  "prob": p.get("prob"), "score": None, "entry": p.get("entry")})
            return {"scan_id": scan_id, "time": _fmt_kst(row.get("time")), "cards": cards, "notes": notes}
        return {"scan_id": scan_id, "time": "", "cards": [], "notes": ["저널에 기록 없음"]}
    if scan_id.startswith("B-"):
        bp = json.load(open(os.path.join(REPO, "b_engine/data/b_picks_latest.json")))
        cards = [{"ticker": p["code"], "code": p["code"], "name": p.get("name"),
                  "market": S._market_of(p["code"]),   # B픽도 KR종목 → 시장 배지 표시
                  "lane": "B 시장중립", "prob": p.get("prob_win"), "score": p.get("pred_alpha_5d"),
                  "entry": p.get("close")} for p in bp.get("picks", [])]
        return {"scan_id": scan_id, "time": bp.get("scan_date"), "cards": cards}
    db = S._db()
    cards = []
    time_s = ""
    if db is not None:
        try:
            import json as _j
            q = (db.client.table("scan_deep_reports")
                 .select("ticker,stock_name,market,decision_bucket,scan_mode,prediction,candidate_interpretation,generated_at")
                 .eq("run_id", scan_id).order("generated_at", desc=True).limit(60).execute())
            for r in (q.data or []):
                time_s = _fmt_kst(r.get("generated_at"))
                ci = r.get("candidate_interpretation") or {}; pred = r.get("prediction") or {}
                if isinstance(ci, str): ci = _j.loads(ci) if ci else {}
                if isinstance(pred, str): pred = _j.loads(pred) if pred else {}
                code = str(r.get("ticker", "")).split(".")[0]
                cards.append({"ticker": r.get("ticker"), "code": code if not code.isdigit() else code.zfill(6),
                              "name": S.resolve_any_name(r.get("ticker"), r.get("stock_name")),
                              "market": str(r.get("market") or ""), "lane": _lane_label(r.get("decision_bucket"), r.get("scan_mode"), scan_id),
                              "prob": pred.get("phase25_prob"), "score": pred.get("expected_edge_score"),
                              "entry": ci.get("entry_reference_price")})
        except Exception:
            pass
    return {"scan_id": scan_id, "time": time_s, "cards": cards}


def scan_analyze(scan_id, ticker):
    """정밀분석 패널 — (scan_id,ticker) 로컬캐시. 미스시 생성(스캔컨텍스트 + services.analyze + Gemini) 후 저장."""
    code = str(ticker).split(".")[0]
    code = code.zfill(6) if code.isdigit() else code
    d = os.path.join(CACHE_DIR, scan_id.replace("/", "_"))
    os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, f"{code}.json")
    if os.path.exists(fp):
        try:
            return json.load(open(fp))
        except Exception:
            pass
    base = S.analyze(code)            # 현 데이터 기반 7블록(모델멤버십·차트가능·수급·이벤트·레짐·Gemini)
    base["scan_id"] = scan_id
    base["cached_at"] = time.strftime("%Y-%m-%d %H:%M")
    try:
        json.dump(base, open(fp, "w"), ensure_ascii=False)
    except Exception:
        pass
    return base
