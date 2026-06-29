"""A 라이브 모델레인 픽 현재기준 성과 측정 — 중복제거 + 시장대비 알파(베타 분리) + 종목명.

원장: runtime_state/reports/experimental/{swing_ensemble,kospi_intraday_swing,
      kosdaq_intraday_1500_3d_t5_vwap_guard}_ledger.jsonl (date·ticker·entry_reference_price).
현재가/시장베이스라인: ~/research_cache/px_long.parquet 최신 종가. 종목명: modules.ticker_names.

절대수익은 시장 베타 포함 → 모델 실력은 '시장대비 알파'로 봐야 함(롱온리라 하락장엔 베타로 같이 빠짐).
CLI: python -m multi_agent.tools.measure_model_lane_picks
"""
from __future__ import annotations
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from modules.ticker_names import resolve_name

CACHE = os.path.expanduser("~/research_cache")
EXP = os.path.join(BASE, "runtime_state/reports/experimental")
LEDGERS = {
    "SWING": "swing_ensemble_ledger.jsonl",
    "KOSPI장중": "kospi_intraday_swing_ledger.jsonl",
    "KOSDAQ장중": "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl",
}


def main():
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=["code", "date", "close", "liq"])
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"])
    cur_date = px["date"].max()
    cur = px[px["date"] == cur_date].set_index("code")["close"].to_dict()
    liq = px[px["date"] >= cur_date - pd.Timedelta(days=120)].groupby("code")["liq"].median()
    uni = set(liq[liq >= 100e8].index.astype(str))
    pv = px[px["code"].isin(uni)].pivot_table(index="date", columns="code", values="close")

    def mkt_ret(d):  # 진입일 → 현재 유니버스 평균(시장 베이스라인)
        d = pd.Timestamp(d)
        if d not in pv.index:
            prev = pv.index[pv.index <= d]
            if not len(prev):
                return np.nan
            d = prev.max()
        return float(((pv.loc[cur_date] / pv.loc[d] - 1) * 100).mean())

    rows = []
    for lane, fn in LEDGERS.items():
        fp = os.path.join(EXP, fn)
        if not os.path.exists(fp):
            continue
        for r in (json.loads(l) for l in open(fp) if l.strip()):
            code = str(r.get("ticker", "")).split(".")[0].zfill(6)
            e = r.get("entry_reference_price")
            if not e or code not in cur:
                continue
            rows.append({"lane": lane, "date": r.get("date"), "code": code,
                         "name": resolve_name(code, default=code), "entry": e})
    if not rows:
        print("픽 없음 (원장 비어있음)"); return
    A = pd.DataFrame(rows).drop_duplicates(["lane", "date", "code"])
    A["ret"] = A.apply(lambda x: (cur[x["code"]] / x["entry"] - 1) * 100, axis=1)
    A["mkt"] = A["date"].apply(mkt_ret)
    A["alpha"] = A["ret"] - A["mkt"]
    A["days"] = (cur_date - pd.to_datetime(A["date"])).dt.days

    print(f"현재 기준일 {cur_date.date()} · 중복제거 후 {len(A)}픽\n")
    for lane, d in A.groupby("lane"):
        print(f"=== {lane}: {len(d)}픽 ({d['date'].min()}~{d['date'].max()}) ===")
        print(f"  절대 승률 {(d['ret']>0).mean()*100:.0f}% 평균 {d['ret'].mean():+.2f}% | "
              f"시장대비 알파 승률 {(d['alpha']>0).mean()*100:.0f}% 평균 {d['alpha'].mean():+.2f}%")
        for _, x in d.sort_values("ret", ascending=False).iterrows():
            print(f"    {x['date']} {x['name']}({x['code']}) {x['entry']:.0f}→{cur[x['code']]:.0f} "
                  f"{x['ret']:+.1f}% (α{x['alpha']:+.1f})")
        print()
    print("=" * 56)
    print(f"【A 전체】 {len(A)}픽 · 절대 승률 {(A['ret']>0).mean()*100:.0f}% 평균 {A['ret'].mean():+.2f}% "
          f"(시장 {A['mkt'].mean():+.2f}%) · 알파 승률 {(A['alpha']>0).mean()*100:.0f}% 평균 {A['alpha'].mean():+.2f}%")
    nimmature = int((A["days"] < 3).sum())
    if nimmature:
        print(f"  ⚠️ 보유 3일미만 {nimmature}픽 포함 — 평가 미성숙(보유 3-5일 목표). 절대수익엔 시장 베타 포함.")


if __name__ == "__main__":
    main()
