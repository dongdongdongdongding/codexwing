#!/usr/bin/env python3
"""NASDAQ session-tape shadow lane (swing-main-f9yw, RESEARCH_LOG §12-D). OBSERVATION-ONLY.

Research basis (29mo walk-forward, 351 liquid syms): session-tape rank-1 win 79.3% vs
label-shuffle placebo 69.9% (+9.4pp ~ 5 sigma), EV 1.68 net vs placebo 1.12 — honest true
edge ~+0.5-1.0/trade (half the raw EV is vol-tilt/survivorship/bull-window artifact).
Contract: close(t) entry -> +5% touch within 5 sessions (fill max(open,target)) else 5d close.

Self-consistent single data source: ~/research_cache/us_daily/hourly/{SYM}.parquet — session
features AND daily context are both derived from the hourly cache (no panel-parity risk).
Trains in-process on the full cache (like the KOSPI lane), scores the latest US session,
appends rank-1 to a ledger, auto-resolves with yfinance daily bars. Never routed to buy lists.

  python3 multi_agent/tools/update_us_hourly.py   # refresh cache first (daily ops)
  python3 multi_agent/tools/report_nasdaq_session_tape.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")
import numpy as np
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 🔴 2026-08-24 원천 교체 — 시간봉 351종목 고정 캐시 → 일별 패널 3,932종목.
# 왜: `glob(hourly/*.parquet)` 로 잡던 유니버스가 **2025-08 유동성으로 한 번 뽑힌 351종목 고정 목록**
# 이었다(파일 내용은 매일 갱신되는데 구성이 안 바뀐다). 새로 유동해진 종목은 영원히 못 들어오고,
# 그 목록으로 과거를 백테스트한 것이 오라클이다(고ATR 선택 프리미엄 +6.17pp · 이후 이탈률 0.3%
# vs 캐시밖 45.0%). 사양: research/X/SOURCE_SWAP_SPEC.md ([X] 작성, 조정관 이식).
# ⚠️ 시간봉 세션피처 9종(`s_day_ret` 등)은 사라진다. 대가는 [X] §6 에서 쟀다.
PANELD = os.path.expanduser("~/research_cache/us_daily/NASDAQ")
PANEL_PREFIX = "daily_features_"
T1_PATH = os.path.expanduser("~/research_cache/T1_nasdaq_listing_snapshots.parquet")
# 부정목록 — 워런트·유닛·우선주·채권성만 뺀다. **ADR·Ordinary Shares 는 남긴다**([X] §6-D).
# 🔴 `"Common Stock"` 정확일치로 거르지 마라 — 원장에 `"Common stock"`(소문자 s)이 섞여 있어
# UPST·RGTI 가 통째로 빠진다. [X] 가 1차에 밟은 함정이고 부정목록 방식이 정본이다.
T1_EXCLUDE = re.compile(
    r"warrant|right(s)?\s|[- ]unit(s)?\b|\sunit$|preferred|"
    r"depositary share.*preferred|notes?\s+due|debenture|contingent value|subordinated",
    re.IGNORECASE)
MIN_CLOSE = 5.0          # [M] §6 — 현행 라이브엔 없었다. 실측 48픽 중 7건 위반, 최저 $3.38
MIN_LIQ20 = 1e8
ADMIT_Q = 0.10           # 편입자격: `univ_frac250` 의 **그날 횡단면 분위**. 절대컷 아님(규율 3)
UNIV_W, UNIV_MINP = 250, 60
CONTRACT_H = 20          # TP +5% / H=20세션 (기존 5세션에서 교체)
USR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
LEDGER = USR / "nasdaq_session_tape_ledger.jsonl"
REPORT_JSON = USR / "nasdaq_session_tape_latest.json"
REPORT_MD = USR / "nasdaq_session_tape_latest.md"
from modules.trading_costs import US_ROUNDTRIP_COST_PCT as COST  # 🔴 US 는 실측 아님(가정치)
def _features():
    """생산 피처 49종. `research_nasdaq_daily_edge.FEATURES` 를 단일 출처로 쓴다 —
    복제하면 두 곳이 어긋나고, 이 리포는 그 실패 계열을 반복해서 겪었다."""
    from research_nasdaq_daily_edge import FEATURES
    return list(FEATURES)




# `build_symbol()` 삭제(2026-08-24): 시간봉 → 일별 재구성 81줄. 이제 일별 패널을 그대로 읽는다.
# 시간봉 캐시는 지우지 않는다 — 롤백 경로이자 [X] 의 오라클 진단 근거다.

def _read_ledger() -> List[Dict[str, Any]]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resolve_pending(today: pd.Timestamp) -> Dict[str, Any]:
    import yfinance as yf
    rows = _read_ledger()
    changed = False
    for row in rows:
        if row.get("policy_ret") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        # 🔴 **발행 당시 계약으로 채점한다.** 계약을 H5 → H20 으로 바꾸면서 원장의 미정산 과거 픽까지
        # 새 창으로 재면 그 픽이 약속하지 않은 창으로 채점하는 것이고 전진 기록이 소급 변조된다.
        # `contract_h` 가 없는 행 = 2026-08-24 이전 발행 = H5 계약이다. (KR 레인에서 같은 조치를 했다)
        _H = int(row.get("contract_h") or 5)
        _wait = 10 if _H <= 5 else 32     # 창이 끝나기 전에 정산하면 미완성 계약을 채점한다
        if pd.isna(d) or (today - d).days < _wait:
            continue
        try:
            h = yf.download(row["symbol"], start=str(d.date()), progress=False, auto_adjust=False)
            if h is None or h.empty:
                continue
            h.columns = [c[0] if isinstance(c, tuple) else c for c in h.columns]
            h = h[h.index > d]
            if len(h) < _H:
                continue
            entry = float(row["entry"])
            tgt = entry * 1.05
            win5 = h.iloc[:_H]
            ret = (float(win5["Close"].iloc[-1]) / entry - 1) * 100
            touched = 0
            for k in range(_H):
                if float(win5["High"].iloc[k]) >= tgt:
                    o = float(win5["Open"].iloc[k])
                    # 갭 보너스는 **모든 세션에** 붙는다 (k=0 포함).
                    #
                    # 2026-08-22 수정. 이전 코드는 `k > 0` 을 요구해 1일차 터치에서 보너스를 거부했다.
                    # 그 가드는 **익일시가 진입 계약에서만 옳다** — 그때는 k=0 의 시가가 곧 진입가라
                    # 자기 위로 갭업할 수 없다(KR `report_kr_swing_candidate.py:resolve_pending` 이 그 경우다).
                    # **이 레인은 `close(t)` 진입이다**(위 Contract 줄). `h[h.index > d]` 로 신호일
                    # **다음** 세션부터 창을 잡으므로 k=0 은 이미 진입 다음 세션이고, 그 시가는 전일
                    # 종가(=진입가) 위로 얼마든지 갭업한다. 거부하면 실현수익을 깎아 기록하게 된다.
                    #
                    # 실측 영향: 정산 48건 중 터치 34건, 그중 21건이 1일차 터치이고 평균 보너스 +1.79pp.
                    # 21×1.79/48 = **+0.78pp** — 이 레인의 전진 기록 전체가 그만큼 축소돼 있었다
                    # (+0.23 → 약 +1.01. [X] 가 정본 재채점으로 얻은 +1.01 과 독립 일치).
                    # ⚠️ 이 수정은 **앞으로 정산할 행에만** 적용된다. 이미 `policy_ret` 이 채워진
                    # 과거 행은 그대로다 — 원장 소급 재정산은 라이브 데이터 변형이라 OD-20 승인 대상.
                    fill = max(tgt, o) if (np.isfinite(o) and o > 0) else tgt
                    ret = (fill / entry - 1) * 100
                    touched = 1
                    break
            row["touch5"] = touched
            row["contract_h"] = _H
            row["policy_ret"] = round(ret, 2)
            changed = True
        except Exception:
            continue
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("policy_ret") is not None]
    if not res:
        return {"resolved": 0}

    def _stats(sub):
        if not sub:
            return {"resolved": 0}
        r = [float(x["policy_ret"]) - COST for x in sub]
        return {"resolved": len(sub),
                "touch5_pct": round(float(np.mean([x["touch5"] for x in sub])) * 100, 1),
                "ev_net_avg": round(float(np.mean(r)), 2), "worst": round(float(np.min(r)), 2)}

    # 구성 전환 경계. 표지는 `xq` 다 — **편입자격 컷(A1)이 발행 시점에 쓰는 필드**이고
    # 그 코드가 들어오기 전 픽에는 없다. `contract_h` 는 표지가 아니다: KR 레인에서 확인했듯
    # 정산 시점에도 찍힐 수 있어 전환 이전 픽에 붙는다.
    #
    # 왜 필요한가: 전체를 뭉치면 옛 배선(터치 계약 5세션·편입컷 없음)의 성적이 A1 셀의
    # 성적처럼 읽힌다. 실측 시점 기준 정산 56건 중 **55건이 전환 이전**이었다.
    cur = [r for r in res if r.get("xq") is not None]
    prev = [r for r in res if r.get("xq") is None]
    out = dict(_stats(res))
    out["epoch"] = {"current": _stats(cur), "previous": _stats(prev),
                    "current_picks": sum(1 for r in rows if r.get("xq") is not None)}
    if len(cur) < 30:
        out["epoch_note"] = (
            f"위 수치는 **구성 전환 이전** 픽이 지배한다(정산 {len(prev)}건). "
            f"현행 A1 구성은 픽 {out['epoch']['current_picks']}건 · 정산 {len(cur)}건 — "
            f"**아직 판정 표본이 아니다**(레인 자체 승격 기준: forward n>=30).")
    return out


def _latest_panel() -> str:
    """소비자와 **같은 규칙**으로 고른다: `{prefix}_*.parquet` glob → `_latest_` 제외 → mtime 최신.
    `_latest_` 파일로 판정하면 소비자가 절대 안 여는 파일을 보게 된다(seaslug f2639e0 의 교훈)."""
    fs = [p for p in glob.glob(os.path.join(PANELD, PANEL_PREFIX + "*.parquet")) if "_latest_" not in p]
    if not fs:
        raise FileNotFoundError(f"no daily panel under {PANELD}")
    return max(fs, key=os.path.getmtime)


def _listed_pit(P: pd.DataFrame) -> pd.Series:
    """시점기준 상장 여부. 각 (symbol, date) 에 대해 **`snapshot_ts <= date` 인 최신 스냅샷**을 보고
    거기 있으면서 `test_issue=N ∧ etf=N ∧ 부정목록 미해당` 이면 True.

    이것이 오라클을 없애는 부품이다 — 오늘의 종목 목록으로 과거를 거래하지 않는다.
    ⚠️ 스냅샷 간격 중앙 45일·최대 273일이라 **상폐 종목이 최대 273일 남을 수 있다.**
    방향은 보수적이다(죽은 종목을 더 오래 살려두므로 EV 를 낮추는 쪽)."""
    t1 = pd.read_parquet(T1_PATH, columns=["snapshot_ts", "symbol", "security_name", "test_issue", "etf"])
    t1["snapshot_ts"] = pd.to_datetime(t1["snapshot_ts"])
    ok = (t1["test_issue"].astype(str).str.upper().isin(["N", "FALSE", "0"])
          & t1["etf"].astype(str).str.upper().isin(["N", "FALSE", "0"])
          & ~t1["security_name"].astype(str).str.contains(T1_EXCLUDE, na=False))
    t1 = t1.loc[ok, ["snapshot_ts", "symbol"]].assign(_pit=True).sort_values("snapshot_ts")
    # 🔴 `merge_asof` 는 왼쪽을 `on` 키로 정렬해야 한다. 정렬한 결과를 그대로 돌려주면
    # 호출부(=(symbol,date) 정렬)와 **행 순서가 어긋나** 엉뚱한 종목에 판정이 붙는다.
    # 첫 이식에서 이 버그로 AAPL 이 탈락했다(검증벡터 2/10). 원본 인덱스를 들고 다녀 복원한다.
    left = P[["date", "symbol"]].copy()
    left["_ix"] = np.arange(len(left))
    left = left.sort_values("date")
    out = pd.merge_asof(left, t1, left_on="date", right_on="snapshot_ts",
                        by="symbol", direction="backward")
    pit = out["_pit"].fillna(False).to_numpy()
    restored = np.empty(len(P), dtype=bool)
    restored[out["_ix"].to_numpy()] = pit
    return restored


def _admit(P: pd.DataFrame) -> pd.DataFrame:
    """5조건 편입 + `univ_frac250` 편입자격. `P` 는 (symbol, date) 정렬 가정.

    `univ_frac250` 은 **자기 자격 이력의 비율**이고 `shift(1)` 로 당일을 뺀다 — 안 그러면 자기참조다.
    `min_periods=60` 이라 자격 이력 60거래일 미만은 NaN = 편입 불가(웜업).
    편입은 **절대컷이 아니라 그날 횡단면 분위**다(규율 3 · [!][P] 절대임계 함정 5번째 사례 회피)."""
    P = P.sort_values(["symbol", "date"]).reset_index(drop=True)
    elig = ((P["liq20"] >= MIN_LIQ20) & (P["close"] >= MIN_CLOSE)
            & (P["feature_ready"] == 1) & _listed_pit(P)).astype(float)
    P["tradable"] = elig.to_numpy() > 0
    P["univ_frac250"] = (elig.groupby(P["symbol"], sort=False)
                         .transform(lambda x: x.shift(1).rolling(UNIV_W, min_periods=UNIV_MINP).mean()))
    return P


def main() -> None:
    import lightgbm as lgb
    FEAT = _features()
    panel = _latest_panel()
    P = pd.read_parquet(panel, columns=list(dict.fromkeys(
        ["symbol", "date", "close", "liq20", "feature_ready", "fwd_high_ret_20d"] + FEAT)))
    P["date"] = pd.to_datetime(P["date"])
    P = _admit(P)
    latest = P["date"].max()
    # 라벨 교체: +5% 터치/5세션 → `t_15_20` = 20세션 내 최고가가 +15% 이상 ([J] §12-3)
    P["y"] = (P["fwd_high_ret_20d"] >= 15).astype(float).where(P["fwd_high_ret_20d"].notna())
    tr = P.dropna(subset=["y"] + FEAT)
    # 편입: 5조건 통과 ∧ 그날 횡단면 분위 >= ADMIT_Q. NaN 은 자동 탈락.
    te = P[(P["date"] == latest) & P["tradable"]].dropna(subset=FEAT).copy()
    te["xq"] = te["univ_frac250"].rank(pct=True, method="average")
    te = te[te["xq"] >= ADMIT_Q]
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                           subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
    m.fit(tr[FEAT].clip(-1e6, 1e6), tr["y"])
    te["p"] = m.predict_proba(te[FEAT].clip(-1e6, 1e6))[:, 1]
    top = te.nlargest(1, "p")
    now = datetime.now(timezone.utc)
    picks = [{"date": str(latest.date()), "symbol": str(r["symbol"]), "p": round(float(r["p"]), 4),
              "entry": round(float(r["close"]), 2), "tier": "SHADOW",
              "contract": f"+5% touch within {CONTRACT_H} sessions else {CONTRACT_H}d close (close entry)",
              "contract_h": CONTRACT_H, "univ_frac250": round(float(r["univ_frac250"]), 4),
              "xq": round(float(r["xq"]), 4), "panel": os.path.basename(panel)}
             for _, r in top.iterrows()]
    existing = {(r.get("date"), r.get("symbol")) for r in _read_ledger()}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            if (p["date"], p["symbol"]) not in existing:
                fh.write(json.dumps({**p, "touch5": None, "policy_ret": None,
                                     "logged_at": now.isoformat()}) + "\n")
    summary = resolve_pending(pd.Timestamp(now.date()))
    report = {"generated_at": now.isoformat(), "as_of": str(latest.date()),
              "capital_status": "observation_only_shadow",
              "expectation": "backtest: rank-1 win 79.3%, EV 1.68 net (placebo-separated +9.4pp/5sig); "
                             "honest true edge ~+0.5-1.0/trade — no capital before forward n>=30",
              "train_rows": int(len(tr)), "universe": int(te["symbol"].nunique()),
              "picks": picks, "forward_summary": summary}
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [f"# NASDAQ session-tape shadow — {report['as_of']}", "",
             f"- observation-only | forward: {summary}", "",
             "| Symbol | p | entry |", "|---|---:|---:|"]
    for p in picks:
        lines.append(f"| {p['symbol']} | {p['p']} | {p['entry']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"as_of": report["as_of"], "picks": picks, "forward": summary}))


if __name__ == "__main__":
    main()
