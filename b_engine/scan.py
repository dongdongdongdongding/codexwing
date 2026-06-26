"""B 엔진 스캐너 — 실시간 점화 탐지 → 스코어 → top2 픽 + forward-shadow 채점.

두 모드:
  scan   : 오늘(또는 지정일) 분봉에서 점화 탐지 → 모델 스코어 → top2 픽 → data/picks_latest.json
           + data/shadow.jsonl 에 픽 기록(관측전용, signal_class=B)
  settle : 기록된 shadow 픽 중 미채점 건을 분봉경로로 TP5/SL5 first-touch 채점 → 갱신

데이터 소스 (env B_LIVE=1 이면 KIS 실시간, 아니면 분봉캐시):
  - 캐시: ~/research_cache/intraday/{code}.parquet  (백필된 1분봉)
  - 라이브: modules.kis_openapi 로 당일 분봉 머지 (장중 갱신)

CLI:
  python -m b_engine.scan scan [YYYY-MM-DD]
  python -m b_engine.scan settle
"""
from __future__ import annotations
import os, sys, json, glob
from datetime import datetime
import numpy as np
import pandas as pd

from b_engine import engine
from b_engine.engine import (
    DATA, PX_LONG, INTRADAY_DIR, DAILY_CTX, FEATURES, TP_PCT, SL_PCT,
    HOLD_DAYS, TOP_K, COST_PCT, detect_ignition, barrier_outcome,
)

PICKS_PATH = os.path.join(DATA, "picks_latest.json")
SHADOW_PATH = os.path.join(DATA, "shadow.jsonl")


def _daily_context():
    """px_long → {code: {pc, ctx{...}, date}} 최신 거래일 + 전일 lag 피처."""
    cols = ["code", "date", "close", "liq"] + DAILY_CTX
    px = pd.read_parquet(PX_LONG, columns=cols)
    px["code"] = px["code"].astype(str)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["code", "date"])
    g = px.groupby("code")
    px["pc"] = g["close"].shift(1)
    for k in DAILY_CTX:
        px["L_" + k] = g[k].shift(1)
    return px


def _minute_for(code: str, day: pd.Timestamp, live: bool):
    """해당 종목·일의 분봉(09:00~). live=True면 KIS 당일, 아니면 캐시."""
    if live:
        try:
            return _fetch_live_minute(code, day)
        except Exception:
            return None
    fp = os.path.join(INTRADAY_DIR, f"{code}.parquet")
    if not os.path.exists(fp):
        return None
    try:
        df = pd.read_parquet(fp)
        df.index = pd.to_datetime(df.index)
    except Exception:
        return None
    day = pd.Timestamp(day).normalize()
    sel = df[df.index.normalize() == day]
    return sel.sort_index() if len(sel) else None


def _fetch_live_minute(code: str, day: pd.Timestamp):
    """KIS 당일 분봉 (정규장). intraday_backfill 패턴 재사용."""
    from modules.kis_openapi import KISOpenAPIClient
    from modules.kis_operational_adapter import normalize_kis_minute_bars
    dt = pd.Timestamp(day).strftime("%Y%m%d")
    cli = _live_client()
    parts = []
    for hh in ["153000", "133000", "113000", "100000"]:
        try:
            pl = cli.daily_minute_bars(code, trade_date=dt, input_hour=hh, include_past=True)
            fr = normalize_kis_minute_bars(code, pl, trade_date=dt)
            if len(fr):
                parts.append(fr)
        except Exception:
            pass
    if not parts:
        return None
    full = pd.concat(parts)
    full = full[~full.index.duplicated(keep="first")].sort_index()
    idx = pd.to_datetime(full.index)
    keep = (idx.strftime("%Y%m%d") == dt) & (idx.time >= pd.Timestamp("09:00").time()) & (idx.time <= pd.Timestamp("15:30").time())
    full = full[keep]
    return full if len(full) else None


_CLIENT = None
def _live_client():
    global _CLIENT
    if _CLIENT is None:
        os.environ.setdefault("KIS_ENABLE_LIVE_CALLS", "1")
        from modules.kis_openapi import KISOpenAPIClient
        _CLIENT = KISOpenAPIClient(timeout=10.0)
        _CLIENT.get_access_token()
    return _CLIENT


def scan(day=None, live=None):
    """점화 탐지 → 스코어 → top2 픽. day=None이면 캐시 최신일."""
    live = (os.environ.get("B_LIVE", "0") == "1") if live is None else live
    model, meta = engine.load_model()
    px = _daily_context()

    # 대상일
    if day is None:
        day = px["date"].max()
    day = pd.Timestamp(day).normalize()

    # 유니버스 (학습과 동일 기준)
    liq = px[px["date"] >= px["date"].max() - pd.Timedelta(days=90)].groupby("code")["liq"].median()
    min_liq = float(os.environ.get("B_MIN_LIQ", 100e8))
    universe_n = int(os.environ.get("B_UNIVERSE_N", 150))
    codes = liq[liq >= min_liq].index.astype(str).tolist()[:universe_n]

    # 당일 행 인덱스 (pc + 전일 lag ctx)
    rows_idx = px[px["date"] == day].set_index("code")
    cands = []
    for code in codes:
        if code not in rows_idx.index:
            continue
        r = rows_idx.loc[code]
        pc = r["pc"]
        if pd.isna(pc) or pc <= 0:
            continue
        bars = _minute_for(code, day, live)
        if bars is None or len(bars) < engine.MIN_DAY_BARS:
            continue
        ctx = {k: r["L_" + k] for k in DAILY_CTX}
        igs = detect_ignition(bars, float(pc), ctx)
        for ig in igs:
            row = {f: ig[f] for f in FEATURES}
            row.update({
                "code": code, "date": str(day.date()),
                "entry": round(float(ig["entry"]), 2),
                "ignition_time": str(ig["ignition_time"]),
                "prev_close": round(float(pc), 2),
                "thr": float(ig["thr"]),
            })
            cands.append(row)

    picks = []
    if cands:
        cdf = pd.DataFrame(cands)
        cdf["prob"] = engine.score_features(cdf, model)
        # 같은 종목 중복점화(8/10%)는 확률 높은 쪽만
        cdf = cdf.sort_values("prob", ascending=False).drop_duplicates("code", keep="first")
        cdf = cdf.sort_values("prob", ascending=False)
        top = cdf.head(TOP_K)
        for _, x in top.iterrows():
            picks.append({
                "code": x["code"], "date": x["date"], "signal_class": "B",
                "prob": round(float(x["prob"]), 4),
                "entry": float(x["entry"]),
                "tp_price": round(float(x["entry"]) * (1 + TP_PCT / 100), 2),
                "sl_price": round(float(x["entry"]) * (1 - SL_PCT / 100), 2),
                "tp_pct": TP_PCT, "sl_pct": SL_PCT, "hold_days": HOLD_DAYS,
                "ignition_threshold_pct": float(x["thr"]),
                "ignition_time": x["ignition_time"],
                "prev_close": float(x["prev_close"]),
            })

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scan_date": str(day.date()),
        "live": bool(live),
        "signal_class": "B",
        "engine": "ignition_barrier_v1",
        "n_candidates": len(cands),
        "top_k": TOP_K,
        "picks": picks,
        "validation": meta.get("oos_validation", {}),
    }
    with open(PICKS_PATH, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _append_shadow(picks)
    print(f"scan {day.date()} live={live}: 후보 {len(cands)} → top{TOP_K} 픽 {len(picks)}", flush=True)
    for p in picks:
        print(f"  {p['code']} prob={p['prob']:.2f} entry={p['entry']} TP={p['tp_price']} SL={p['sl_price']} ({p['ignition_threshold_pct']:.0f}% @{p['ignition_time'][-8:]})", flush=True)
    return payload


def _append_shadow(picks):
    """관측전용 forward-shadow 로그(중복 키 skip)."""
    existing = set()
    if os.path.exists(SHADOW_PATH):
        with open(SHADOW_PATH) as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                    existing.add((r["code"], r["date"]))
                except Exception:
                    pass
    with open(SHADOW_PATH, "a") as f:
        for p in picks:
            key = (p["code"], p["date"])
            if key in existing:
                continue
            rec = dict(p)
            rec["logged_at"] = datetime.now().isoformat(timespec="seconds")
            rec["status"] = "open"
            rec["outcome_pct"] = None
            rec["settled_at"] = None
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def settle(live=None):
    """미채점 shadow 픽을 분봉경로로 TP5/SL5 first-touch 채점."""
    live = (os.environ.get("B_LIVE", "0") == "1") if live is None else live
    if not os.path.exists(SHADOW_PATH):
        print("shadow 없음", flush=True)
        return
    recs = []
    with open(SHADOW_PATH) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                recs.append(json.loads(ln))
    changed = 0
    for r in recs:
        if r.get("status") != "open":
            continue
        code = r["code"]; day = pd.Timestamp(r["date"]).normalize()
        entry = float(r["entry"])
        # 점화일~+HOLD_DAYS 분봉 경로 수집
        fp = os.path.join(INTRADAY_DIR, f"{code}.parquet")
        if not os.path.exists(fp):
            continue
        try:
            df = pd.read_parquet(fp); df.index = pd.to_datetime(df.index)
        except Exception:
            continue
        df = df.sort_index()
        days = np.array(sorted(df.index.normalize().unique()))
        di = np.where(days == day)[0]
        if len(di) == 0:
            continue
        di = int(di[0])
        # 점화 이후 봉만 (점화시각 이후) ~ +HOLD_DAYS 거래일
        end_day = days[min(di + HOLD_DAYS - 1, len(days) - 1)]
        ig_time = pd.Timestamp(r.get("ignition_time")) if r.get("ignition_time") else day
        path = df[(df.index > ig_time) & (df.index.normalize() <= end_day)]
        # 마지막 관측일이 아직 미래면 보류 (충분히 경과해야 채점)
        if days[min(di + HOLD_DAYS - 1, len(days) - 1)] >= days[-1] and di + HOLD_DAYS - 1 >= len(days) - 1:
            # 데이터가 아직 hold기간 다 안 쌓임 → 보류
            if (days[-1] - day).astype("timedelta64[D]").astype(int) < HOLD_DAYS:
                continue
        if len(path) < 3:
            continue
        ret = barrier_outcome(
            path["High"].to_numpy(float), path["Low"].to_numpy(float),
            path["Close"].to_numpy(float), entry,
        )
        r["status"] = "settled"
        r["outcome_pct"] = round(float(ret), 2)
        r["outcome_net_pct"] = round(float(ret) - COST_PCT, 2)
        r["win"] = int(ret > 0)
        r["settled_at"] = datetime.now().isoformat(timespec="seconds")
        changed += 1
    if changed:
        with open(SHADOW_PATH, "w") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    settled = [r for r in recs if r.get("status") == "settled"]
    if settled:
        wins = sum(r.get("win", 0) for r in settled)
        ev = np.mean([r["outcome_net_pct"] for r in settled])
        print(f"settle: {changed} 신규채점 · 누적 {len(settled)}건 승률 {wins/len(settled)*100:.0f}% EV {ev:+.2f}%", flush=True)
    else:
        print(f"settle: {changed} 신규채점 · 채점완료 0", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        day = sys.argv[2] if len(sys.argv) > 2 else None
        scan(day)
    elif cmd == "settle":
        settle()
    else:
        print(f"unknown: {cmd} (scan|settle)")
