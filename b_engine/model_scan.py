"""B 엔진 스캔 — 매일 top10 픽 생성 + forward-shadow(관측전용) 로깅/채점.
  scan   : 최신일 픽 → data/b_picks_latest.json + b_shadow.jsonl 기록
  settle : 5거래일 경과 픽을 실현수익(절대 + 시장중립 알파)로 채점 → 라이브 승률/수익 추적

⚠️ 관측전용. 실자본 전 라이브 Sharpe 확인용.
CLI: python -m b_engine.model_scan scan|settle
"""
from __future__ import annotations
import os, sys, json
from datetime import datetime
import numpy as np
import pandas as pd
from b_engine import model_engine as E

PICKS = os.path.join(E.DATA, "b_picks_latest.json")
SHADOW = os.path.join(E.DATA, "b_shadow.jsonl")


def scan(as_of=None):
    out = E.pick(as_of)
    if not out:
        return None
    out["generated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(E.META_PATH) as f:
        out["model_meta"] = json.load(f)
    with open(PICKS, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    _log_shadow(out)
    print(f"B scan {out['scan_date']}: top{out['top_n']} 픽 생성 → {PICKS}", flush=True)
    for p in out["picks"]:
        print(f"  {p['code']} predα {p['pred_alpha_5d']:+.2f} close {p['close']} smart5 {p['smart5']}", flush=True)
    return out


def _log_shadow(out):
    seen = set()
    if os.path.exists(SHADOW):
        with open(SHADOW) as f:
            for ln in f:
                try:
                    r = json.loads(ln); seen.add((r["code"], r["scan_date"]))
                except Exception:
                    pass
    with open(SHADOW, "a") as f:
        for p in out["picks"]:
            key = (p["code"], out["scan_date"])
            if key in seen:
                continue
            rec = {"code": p["code"], "scan_date": out["scan_date"], "signal_class": "B",
                   "pred_alpha_5d": p["pred_alpha_5d"], "entry_close": p["close"], "hold_days": E.HOLD,
                   "rank": p.get("rank"), "tier": p.get("tier"),
                   "logged_at": datetime.now().isoformat(timespec="seconds"),
                   "status": "open", "abs_ret": None, "alpha": None, "win": None}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def settle():
    if not os.path.exists(SHADOW):
        print("shadow 없음", flush=True); return
    recs = [json.loads(l) for l in open(SHADOW) if l.strip()]
    px = pd.read_parquet(E.PX_LONG, columns=["code", "date", "close"])
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["code", "date"])
    g = px.groupby("code")
    px["entry"] = g["close"].shift(-1); px["exitp"] = g["close"].shift(-(E.HOLD + 1))
    px["fret"] = (px["exitp"] / px["entry"] - 1) * 100
    px["mkt"] = px.groupby("date")["fret"].transform("mean")   # 시장중립 기준(당일 전종목 평균)
    idx = px.set_index(["code", "date"])
    changed = 0
    last_date = px["date"].max()
    for r in recs:
        if r.get("status") != "open":
            continue
        d = pd.Timestamp(r["scan_date"])
        # 충분히 경과해야 채점 (보유기간 + 1일 진입)
        if (last_date - d).days < E.HOLD + 2:
            continue
        try:
            row = idx.loc[(r["code"], d)]
        except KeyError:
            continue
        if pd.isna(row["fret"]):
            continue
        r["abs_ret"] = round(float(row["fret"]), 2)
        r["alpha"] = round(float(row["fret"] - row["mkt"]), 2)
        r["win"] = int(row["fret"] - row["mkt"] > 0)
        r["abs_win"] = int(row["fret"] > 0)
        r["status"] = "settled"; r["settled_at"] = datetime.now().isoformat(timespec="seconds")
        changed += 1
    if changed:
        with open(SHADOW, "w") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    st = [r for r in recs if r.get("status") == "settled"]
    if st:
        alpha = np.mean([r["alpha"] for r in st]); aw = np.mean([r["win"] for r in st]) * 100
        absr = np.mean([r["abs_ret"] for r in st]); abw = np.mean([r.get("abs_win", 0) for r in st]) * 100
        print(f"settle: +{changed}채점 · 누적 {len(st)} | 알파 {alpha:+.2f}% 시장초과승 {aw:.0f}% | 절대 {absr:+.2f}% 상승승 {abw:.0f}%", flush=True)
    else:
        print(f"settle: +{changed} · 채점완료 0 (경과대기)", flush=True)


def shadow_summary():
    """대시보드용 라이브 성과 요약."""
    if not os.path.exists(SHADOW):
        return {"settled": 0, "open": 0}
    recs = [json.loads(l) for l in open(SHADOW) if l.strip()]
    st = [r for r in recs if r.get("status") == "settled"]
    op = [r for r in recs if r.get("status") == "open"]
    out = {"settled": len(st), "open": len(op)}
    if st:
        out.update({
            "alpha_mean": round(float(np.mean([r["alpha"] for r in st])), 2),
            "alpha_winrate": round(float(np.mean([r["win"] for r in st])) * 100, 0),
            "abs_mean": round(float(np.mean([r["abs_ret"] for r in st])), 2),
            "abs_winrate": round(float(np.mean([r.get("abs_win", 0) for r in st])) * 100, 0),
        })
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        scan(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "settle":
        settle()
    elif cmd == "summary":
        print(json.dumps(shadow_summary(), ensure_ascii=False, indent=2))
