#!/usr/bin/env python3
"""tail_p 서빙 스코어러 (§16 tail 사전탐지, swing-main-clbb) — 관측 전용.

build_tail_p_model.py 가 저장한 번들(models/tail_p/tail_p_lgbm.pkl)로 픽 시점
P(policy_ret <= -10)을 계산한다. web/backend/services.py _pick_row 가
AG_TAIL_P_OBS=1 일 때만 호출 — 발행/사이징/베토/랭킹에 일절 개입하지 않는다.

피처 소스: ~/research_cache/px_long.parquet 최근 창(코드×날짜 leak-free 피처) +
학습과 동일한 인과적 시장상태(mkt_dd20/mkt_ret5, 유동성필터 등가중 누적) + 픽 확신 p.
실패는 전부 None 반환(fail-safe) — 웹 페이로드에 필드 자체가 빠질 뿐 다른 영향 없음.

forward 추적: log_tail_p_obs()가 사이드카 jsonl에 append (기존 원장 스키마 불변) —
후행으로 원장 실현수익과 (scan_date, code) 조인해 상관 계산 (meta의 forward_tracking 참조).
"""
from __future__ import annotations
import os, json, pickle, threading
from datetime import datetime, timezone
from functools import lru_cache

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.expanduser("~/research_cache")
BUNDLE_FP = os.path.join(REPO, "models/tail_p/tail_p_lgbm.pkl")
OBS_FP = os.path.join(REPO, "runtime_state/reports/experimental/tail_p_obs.jsonl")
PANEL_DAYS = 180          # 시장상태 rolling(20)·shift(5) 여유 포함 최근 창
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}   # 학습(swing_firsttouch_ranker_8y.LIQ)과 동일

_lock = threading.Lock()
_obs_seen: set = set()    # (scan_date, code, lane) 프로세스 내 중복 방지


@lru_cache(maxsize=1)
def _bundle():
    with open(BUNDLE_FP, "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def warn_threshold() -> float:
    """경고 배지 경계 — 학습 시 기록된 OOS 상위 20% 경계(번들 warn_threshold).
    재학습하면 번들 값이 따라 움직인다. AG_TAIL_P_WARN 로 임시 override 가능."""
    env = os.environ.get("AG_TAIL_P_WARN")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    try:
        return float(_bundle()["warn_threshold"])
    except Exception:
        return 1.0   # 번들 미상시 경고 억제 (관측 필드만 노출)


@lru_cache(maxsize=1)
def _panel():
    """px_long 최근 창 로드(1회 캐시): (code,date)→피처 행 + 시장별 mkt_dd20/mkt_ret5."""
    import pandas as pd
    feats = [f for f in _bundle()["features"] if f not in ("liq_log", "p", "mkt_dd20", "mkt_ret5")]
    cols = list(dict.fromkeys(["code", "date", "market", "liq", "ret_1d"] + feats))
    px = pd.read_parquet(os.path.join(CACHE, "px_long.parquet"), columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px = px[px["date"] >= px["date"].max() - pd.Timedelta(days=PANEL_DAYS)].copy()
    # 학습과 동일한 인과적 시장상태: 시장별 유동성필터 등가중 일수익 누적 (스케일 불변 → 창 내 계산 OK)
    st = {}
    for mkt, thr in LIQ.items():
        d = px[(px["market"] == mkt) & (px["liq"] >= thr)]
        mret = d.groupby("date")["ret_1d"].mean().sort_index()
        lvl = (1 + mret / 100).cumprod()
        st[mkt] = pd.DataFrame({"mkt_dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                                "mkt_ret5": (lvl / lvl.shift(5) - 1) * 100})
    px = px.sort_values("date")
    return px, st


def tail_p_for_pick(code: str, scan_date, prob=None, market: str | None = None):
    """픽 1건의 tail_p (float 0-1) — 실패/피처부재 시 None (fail-safe, 관측 전용)."""
    try:
        import numpy as np
        import pandas as pd
        bundle = _bundle()
        px, st = _panel()
        code6 = str(code).split(".")[0].zfill(6)
        d = pd.Timestamp(scan_date)
        rows = px[(px["code"] == code6) & (px["date"] <= d)]
        if rows.empty:
            return None
        r = rows.iloc[-1]
        if (d - r["date"]).days > 7:   # 스캔일에서 너무 먼 stale 피처는 신뢰 불가
            return None
        mkt = str(market or r["market"] or "").upper()
        mkt = "KOSPI" if "KOSPI" in mkt else ("KOSDAQ" if "KOSDAQ" in mkt else None)
        m_row = None
        if mkt and mkt in st:
            m = st[mkt]
            m_idx = m.index[m.index <= r["date"]]
            if len(m_idx):
                m_row = m.loc[m_idx[-1]]
        p = None
        if prob is not None:
            p = float(prob) / 100.0 if float(prob) > 1.5 else float(prob)  # % 표기 정규화
        vals = {}
        for f in bundle["features"]:
            if f == "liq_log":
                vals[f] = float(np.log10(max(float(r["liq"]), 1.0)))
            elif f == "p":
                vals[f] = p
            elif f in ("mkt_dd20", "mkt_ret5"):
                vals[f] = float(m_row[f]) if m_row is not None else None
            else:
                vals[f] = float(r[f]) if pd.notna(r[f]) else None
        X = pd.DataFrame([vals], columns=bundle["features"]).fillna(0)  # 학습과 동일 fillna(0)
        return float(bundle["model"].predict_proba(X)[0, 1])
    except Exception:
        return None


def log_tail_p_obs(row: dict) -> None:
    """forward 상관 추적용 사이드카 append (관측 전용, 기존 원장 스키마 불변).
    (scan_date, code, lane) 프로세스 내 dedupe — 웹 조회 반복으로 인한 중복 억제."""
    try:
        key = (row.get("scan_date"), row.get("code"), row.get("lane"))
        with _lock:
            if key in _obs_seen:
                return
            _obs_seen.add(key)
            rec = {"logged_at": datetime.now(timezone.utc).isoformat(),
                   "scan_date": row.get("scan_date"), "code": row.get("code"),
                   "lane": row.get("lane"), "tail_p": row.get("tail_p")}
            with open(OBS_FP, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="tail_p 단건 조회 (관측 전용)")
    ap.add_argument("code")
    ap.add_argument("scan_date")
    ap.add_argument("--prob", type=float, default=None)
    ap.add_argument("--market", default=None)
    a = ap.parse_args()
    print(tail_p_for_pick(a.code, a.scan_date, prob=a.prob, market=a.market))
