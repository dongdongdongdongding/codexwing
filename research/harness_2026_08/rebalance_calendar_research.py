# -*- coding: utf-8 -*-
"""
연구 과제 A5: KOSPI200/MSCI 편출입 기계적 수급 캘린더 — H1~H3 검증 하니스
사전등록: docs/research/PREREG_MECH_FLOW_CALENDAR_2026-08.md (게이트/킬 기준 그대로 적용)

가설:
  H1 발표→효력 드리프트: 발표 익일 시가 진입 → 효력일 종가 청산 (편입 long / 편출 drift 측정)
  H2 효력일 반전: 효력일 종가 → +5거래일 종가 (편입 음 / 편출 양 기대)
  H3 효력일 왜곡: 효력일 거래량/변동성 vs 통상일 (측정 — 장중 레인 회피 게이트 근거)

게이트 (사전등록):
  - 시장초과 = 패널 내부 유동성(거래대금)가중 벤치마크 (외부지수 금지; cap 데이터 부재로
    liq(20d 거래대금)가중을 cap가중 프록시로 사용 — 보고서에 명시)
  - 같은날 랜덤 종목 플라시보 (동일 날짜 × 동수, 유동성 매칭 0.5x~2x)
  - 연도별 분해: 양수 연도 < 60% → 기각
  - 효력일 종가 = 동시호가 (리밸런스일 종가 물량 最대 — 체결 현실성 양호) 명시
  - 클러스터 부트스트랩(회차 단위) — 같은 회차 내 이벤트는 상관됨

산출: runtime_state/reports/validation/rebalance_calendar_research_latest.{md,json}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path.home() / "research_cache"
REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "runtime_state" / "reports" / "validation"
import os
EVENTS_CSV = Path(os.environ.get("REBAL_EVENTS", CACHE / "index_rebalance_events.csv"))
PANEL = CACHE / "px_long.parquet"

COST_RT = 0.30  # % 왕복 비용 (수수료+세금+슬리피지 보수 가정)
N_BOOT = 10000
N_PLACEBO = 300
RNG = np.random.default_rng(20260805)


def load_panel():
    cols = ["date", "code", "close", "gap", "ret_1d", "liq", "vol_ratio", "atr_pct", "vol20", "market"]
    px = pd.read_parquet(PANEL, columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["code"] = px["code"].astype(str)
    return px


def build_bench(px):
    """패널 내부 liq가중 벤치마크 (KOSPI 종목만 — 이벤트 유니버스와 정합)."""
    k = px[(px["market"] == "KOSPI") & px["ret_1d"].notna() & px["liq"].notna() & (px["liq"] > 0)]
    g = k.assign(wr=k["ret_1d"] * k["liq"]).groupby("date")[["wr", "liq"]].sum()
    bench = (g["wr"] / g["liq"]).rename("bench_ret")  # % 단위
    ew = k.groupby("date")["ret_1d"].mean().rename("bench_ew")
    logc = np.log1p(bench / 100.0).cumsum()
    return bench, ew, logc


def bench_window(logc, cal, d_from_excl, d_to_incl):
    """(d_from_excl, d_to_incl] 구간 벤치마크 누적수익 % (close[d_from]→close[d_to])."""
    try:
        a = logc.loc[d_from_excl]
        b = logc.loc[d_to_incl]
    except KeyError:
        return np.nan
    return (np.exp(b - a) - 1.0) * 100.0


class Px:
    """종목별 시계열 접근기."""

    def __init__(self, px, codes):
        sub = px[px["code"].isin(codes)].sort_values(["code", "date"])
        self.frames = {c: g.set_index("date") for c, g in sub.groupby("code")}

    def get(self, code):
        return self.frames.get(code)


def next_trading_day(cal, d):
    i = cal.searchsorted(d, side="right")
    return cal[i] if i < len(cal) else None


def shift_trading(cal, d, n):
    i = cal.searchsorted(d)
    if i >= len(cal) or cal[i] != d:
        return None
    j = i + n
    return cal[j] if 0 <= j < len(cal) else None


def h1_return(f, cal, logc, announce, effective):
    """발표 익일 시가 → 효력일 종가. (stock%, bench%, entry_date) 반환."""
    t_entry = next_trading_day(cal, announce)
    if t_entry is None or t_entry > effective:
        return None
    if t_entry not in f.index or effective not in f.index:
        return None
    row = f.loc[t_entry]
    prev_i = f.index.get_loc(t_entry) - 1
    if prev_i < 0:
        return None
    prev_close = f["close"].iloc[prev_i]
    if not np.isfinite(row["gap"]) or not np.isfinite(prev_close):
        return None
    open_entry = prev_close * (1 + row["gap"] / 100.0)
    exit_close = f.loc[effective, "close"]
    if not (np.isfinite(open_entry) and np.isfinite(exit_close) and open_entry > 0):
        return None
    stock = (exit_close / open_entry - 1) * 100.0
    # 벤치: close[t_entry-1] → close[effective] (진입 전일 종가 기준; 시장 시가 부재로
    # 오버나이트 1일치가 벤치에 포함 — 전략에 보수적)
    prev_date = f.index[prev_i]
    bench = bench_window(logc, cal, prev_date, effective)
    if not np.isfinite(bench):
        return None
    return stock, bench, t_entry


def h2_return(f, cal, logc, effective, horizon=5):
    """효력일 종가 → +5거래일 종가."""
    d5 = shift_trading(cal, effective, horizon)
    if d5 is None or effective not in f.index or d5 not in f.index:
        return None
    c0 = f.loc[effective, "close"]
    c1 = f.loc[d5, "close"]
    if not (np.isfinite(c0) and np.isfinite(c1) and c0 > 0):
        return None
    stock = (c1 / c0 - 1) * 100.0
    bench = bench_window(logc, cal, effective, d5)
    if not np.isfinite(bench):
        return None
    return stock, bench, d5


def cluster_boot_ci(vals, clusters, n_boot=N_BOOT, rng=RNG):
    """회차(cluster) 단위 부트스트랩 95% CI."""
    df = pd.DataFrame({"v": vals, "c": clusters}).dropna()
    if df.empty:
        return np.nan, np.nan, np.nan
    groups = [g["v"].values for _, g in df.groupby("c")]
    k = len(groups)
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, k, k)
        pool = np.concatenate([groups[i] for i in idx])
        means[b] = pool.mean()
    return df["v"].mean(), np.percentile(means, 2.5), np.percentile(means, 97.5)


def yearly_decomp(vals, years):
    df = pd.DataFrame({"v": vals, "y": years}).dropna()
    if df.empty:
        return {}, np.nan
    ym = df.groupby("y")["v"].agg(["mean", "count"])
    pos_frac = float((ym["mean"] > 0).mean())
    return {int(y): {"mean": round(r["mean"], 3), "n": int(r["count"])} for y, r in ym.iterrows()}, pos_frac


def liq_matched_placebo(px_kospi_by_date, date, liq_target, n_pick, rng):
    """해당 날짜 KOSPI 종목 중 liq 0.5x~2x 범위에서 랜덤 추출."""
    day = px_kospi_by_date.get(date)
    if day is None or not np.isfinite(liq_target):
        return []
    cand = day[(day["liq"] >= liq_target * 0.5) & (day["liq"] <= liq_target * 2.0)]
    if len(cand) < n_pick:
        cand = day
    if cand.empty:
        return []
    return list(rng.choice(cand["code"].values, size=min(n_pick, len(cand)), replace=False))


def main():
    if not EVENTS_CSV.exists():
        print(f"이벤트 파일 없음: {EVENTS_CSV}", file=sys.stderr)
        sys.exit(1)
    ev = pd.read_csv(EVENTS_CSV, dtype={"code": str})
    ev["announce_date"] = pd.to_datetime(ev["announce_date"])
    ev["effective_date"] = pd.to_datetime(ev["effective_date"])
    ev["code"] = ev["code"].str.zfill(6)

    px = load_panel()
    cal = np.array(sorted(px.loc[px["market"] == "KOSPI", "date"].unique()))
    bench, bench_ew, logc = build_bench(px)

    in_panel = set(px["code"].unique())
    ev["in_panel"] = ev["code"].isin(in_panel)
    cov = (
        ev.assign(year=ev["effective_date"].dt.year)
        .groupby(["index", "year", "direction"])
        .agg(n=("code", "size"), n_panel=("in_panel", "sum"))
    )

    evp = ev[ev["in_panel"]].copy()
    evp["round"] = evp["index"] + "_" + evp["effective_date"].dt.strftime("%Y-%m")
    evp["year"] = evp["effective_date"].dt.year

    # 이벤트 + 전체 KOSPI(플라시보용) 프레임 접근기
    kospi_codes = set(px.loc[px["market"] == "KOSPI", "code"].unique())
    pxs_all = Px(px, kospi_codes | set(evp["code"]))
    pxs = pxs_all

    # 빠른 placebo용: 날짜별 KOSPI 단면
    pk = px[(px["market"] == "KOSPI") & px["liq"].notna()]
    px_by_date = {d: g[["code", "liq"]] for d, g in pk.groupby("date")}

    results = {"coverage": cov.reset_index().to_dict("records"), "cost_rt_pct": COST_RT}

    # ---------- H1 / H2 이벤트 수익 계산 ----------
    # 체결 현실성: 패시브 플로우는 '적용일 전 거래일'(K200 선물만기일 / MSCI rebalance일)
    # 마감 동시호가에서 거래됨 → H1 청산/H2 진입/H3 측정은 flow_date 종가 기준.
    def flow_date_of(eff):
        i = cal.searchsorted(eff)
        if i >= len(cal) or cal[i] != eff:
            i -= 1  # 적용일이 거래일이 아니면 직전 거래일을 적용 세션으로
        return cal[i - 1] if i >= 1 else None

    rows = []
    for _, e in evp.iterrows():
        f = pxs.get(e["code"])
        if f is None:
            continue
        flow = flow_date_of(e["effective_date"])
        if flow is None:
            continue
        rec = {
            "index": e["index"], "round": e["round"], "year": e["year"],
            "code": e["code"], "name": e.get("name"), "direction": e["direction"],
            "announce": e["announce_date"], "effective": flow,
        }
        r1 = h1_return(f, cal, logc, e["announce_date"], flow)
        if r1:
            rec["h1_stock"], rec["h1_bench"], rec["h1_entry"] = r1
            rec["h1_excess"] = r1[0] - r1[1]
            # 진입 시점 liq (플라시보 매칭용)
            try:
                rec["liq_entry"] = f.loc[r1[2], "liq"]
            except KeyError:
                rec["liq_entry"] = np.nan
        r2 = h2_return(f, cal, logc, flow)
        if r2:
            rec["h2_stock"], rec["h2_bench"] = r2[0], r2[1]
            rec["h2_excess"] = r2[0] - r2[1]
        # H3 재료: flow일 vol_ratio, |ret|, atr 대비
        if flow in f.index:
            er = f.loc[flow]
            rec["h3_vol_ratio"] = er["vol_ratio"]
            rec["h3_absret"] = abs(er["ret_1d"]) if np.isfinite(er["ret_1d"]) else np.nan
            rec["h3_vol20"] = er["vol20"]
        rows.append(rec)
    R = pd.DataFrame(rows)
    if R.empty:
        print("패널 매칭 이벤트 0건", file=sys.stderr)
        sys.exit(1)

    # ---------- 가설별 판정 ----------
    def judge(colname, sub, label, expect_sign=+1):
        """expect_sign: 가설이 기대하는 부호(+1 양의 초과 기대)."""
        v = sub[colname].dropna()
        if len(v) < 5:
            return {"label": label, "n": int(len(v)), "verdict": "검정력없음(n<5)"}
        mean, lo, hi = cluster_boot_ci(sub[colname].values, sub["round"].values)
        yd, pos_frac = yearly_decomp(sub[colname].values, sub["year"].values)
        net = mean - COST_RT * expect_sign if expect_sign != 0 else mean
        ci_excl0 = (lo > 0 and hi > 0) if expect_sign >= 0 else (lo < 0 and hi < 0)
        year_pass = pos_frac >= 0.6 if expect_sign >= 0 else (1 - pos_frac) >= 0.6
        return {
            "label": label, "n": int(len(v)), "mean_excess": round(mean, 3),
            "ci95": [round(lo, 3), round(hi, 3)], "net_after_cost": round(net, 3),
            "win_rate": round(float((v > 0).mean() if expect_sign >= 0 else (v < 0).mean()), 3),
            "yearly": yd, "pos_year_frac": round(pos_frac, 3),
            "gate_ci": bool(ci_excl0), "gate_year": bool(year_pass),
        }

    H = {}
    for idx_name, sub_idx in R.groupby("index"):
        H[idx_name] = {}
        for d in ["in", "out"]:
            s = sub_idx[sub_idx["direction"] == d]
            H[idx_name][f"H1_{d}"] = judge("h1_excess", s, f"H1 {idx_name} {d}",
                                           expect_sign=+1 if d == "in" else -1)
            H[idx_name][f"H2_{d}"] = judge("h2_excess", s, f"H2 {idx_name} {d}",
                                           expect_sign=-1 if d == "in" else +1)
    results["hypotheses"] = H

    # ---------- 플라시보 (H1/H2, 같은날 × 동수 × liq매칭) ----------
    placebo = {}
    for (idx_name, d), s in R.groupby(["index", "direction"]):
        s1 = s.dropna(subset=["h1_excess"])
        if len(s1) < 5:
            continue
        p_means_h1, p_means_h2 = [], []
        for rep in range(N_PLACEBO):
            vals1, vals2 = [], []
            for _, e in s1.iterrows():
                cands = liq_matched_placebo(px_by_date, e["h1_entry"], e.get("liq_entry", np.nan), 1, RNG)
                if not cands:
                    continue
                pf = pxs_all.get(cands[0])
                if pf is None:
                    continue
                r1 = h1_return(pf, cal, logc, e["announce"], e["effective"])
                if r1:
                    vals1.append(r1[0] - r1[1])
                r2 = h2_return(pf, cal, logc, e["effective"])
                if r2:
                    vals2.append(r2[0] - r2[1])
            if vals1:
                p_means_h1.append(np.mean(vals1))
            if vals2:
                p_means_h2.append(np.mean(vals2))
        def pct_rank(actual, dist):
            dist = np.asarray(dist)
            return float((dist < actual).mean()) if len(dist) else np.nan
        a1 = s1["h1_excess"].mean()
        a2 = s.dropna(subset=["h2_excess"])["h2_excess"].mean()
        placebo[f"{idx_name}_{d}"] = {
            "h1_actual": round(a1, 3),
            "h1_placebo_mean": round(float(np.mean(p_means_h1)), 3) if p_means_h1 else None,
            "h1_placebo_p95": round(float(np.percentile(p_means_h1, 95)), 3) if p_means_h1 else None,
            "h1_pct_rank": round(pct_rank(a1, p_means_h1), 3),
            "h2_actual": round(a2, 3) if np.isfinite(a2) else None,
            "h2_placebo_mean": round(float(np.mean(p_means_h2)), 3) if p_means_h2 else None,
            "h2_pct_rank": round(pct_rank(a2, p_means_h2), 3) if np.isfinite(a2) else None,
            "n_reps": len(p_means_h1),
        }
    results["placebo"] = placebo

    # ---------- H3 효력일 왜곡 ----------
    h3 = {}
    s3 = R.dropna(subset=["h3_vol_ratio"])
    if len(s3) >= 5:
        # 대조: 같은 효력일들의 랜덤 KOSPI 종목 vol_ratio / |ret|
        ctrl_vr, ctrl_ar = [], []
        for eff_d, grp in s3.groupby("effective"):
            day = px[(px["date"] == eff_d) & (px["market"] == "KOSPI")]
            day = day[day["vol_ratio"].notna()]
            if day.empty:
                continue
            take = day.sample(n=min(len(grp) * 20, len(day)), random_state=42)
            ctrl_vr += list(take["vol_ratio"])
            ctrl_ar += list(take["ret_1d"].abs().dropna())
        h3 = {
            "n_event": int(len(s3)),
            "event_vol_ratio_median": round(float(s3["h3_vol_ratio"].median()), 3),
            "event_vol_ratio_mean": round(float(s3["h3_vol_ratio"].mean()), 3),
            "ctrl_same_day_vol_ratio_median": round(float(np.median(ctrl_vr)), 3) if ctrl_vr else None,
            "event_absret_median": round(float(s3["h3_absret"].median()), 3),
            "ctrl_same_day_absret_median": round(float(np.median(ctrl_ar)), 3) if ctrl_ar else None,
            "event_absret_over_vol20_median": round(float((s3["h3_absret"] / s3["h3_vol20"]).median()), 3),
        }
    results["H3"] = h3

    # ---------- 연간 기여 상한 ----------
    contrib = {}
    for idx_name in R["index"].unique():
        s = R[R["index"] == idx_name]
        yrs = s["year"].nunique()
        # (가설, 방향, 트레이드 부호): H1 in=long(+), H1 out=short(-), H2 in=short(-), H2 out=long(+)
        for key, d, sign in [("H1_in", "in", 1), ("H1_out", "out", -1),
                             ("H2_in", "in", -1), ("H2_out", "out", 1)]:
            j = H.get(idx_name, {}).get(key, {})
            if "mean_excess" not in j:
                continue
            n_per_year = j["n"] / max(yrs, 1)
            ev_net = sign * j["mean_excess"] - COST_RT  # 방향 실행 가정 후 net
            contrib[f"{idx_name}_{key}"] = {
                "events_per_year": round(n_per_year, 1),
                "ev_net_pct": round(ev_net, 3),
                "annual_contrib_pctpt": round(n_per_year * max(ev_net, 0) * 0.02, 4),  # 포지션 2% 가정
                "supporting_role": bool(n_per_year * max(ev_net, 0) * 0.02 < 1.0),
            }
    results["annual_contribution_cap"] = contrib

    # ---------- 저장 ----------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "rebalance_calendar_research_latest.json", "w") as fjson:
        json.dump(results, fjson, ensure_ascii=False, indent=2, default=str)
    R.to_csv(CACHE / "rebalance_event_returns.csv", index=False)
    print(json.dumps(results["hypotheses"], ensure_ascii=False, indent=1, default=str))
    print("\nH3:", json.dumps(results["H3"], ensure_ascii=False))
    print("\nplacebo:", json.dumps(results["placebo"], ensure_ascii=False, indent=1))
    print("\ncontrib:", json.dumps(results["annual_contribution_cap"], ensure_ascii=False, indent=1))
    return results


if __name__ == "__main__":
    main()
