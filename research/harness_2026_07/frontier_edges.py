#!/usr/bin/env python3
"""프론티어 엣지 자동연구 (swing-main-7m9y). 운영 레인 밖 5축, 사전등록 킬기준.

통일 평가: 표준계약 policy_ret(ft_5_5→+5 else exec_5d) net(비용 0.3), 터치승률,
부트스트랩 CI, 연도별 일관성, 시그널 셔플 플라시보.
판정 ALIVE = net EV CI>0 AND 연도 6/8+ 양수 AND 플라시보와 분리.

T1 오버나이트 구조: trailing 60d (gap 누적 − 장중 누적) 상/하위 → forward 계약
T2 볼륨 클라이맥스: turn_z>=3 & |ret_1d|>=8 이벤트 → 방향별 forward
T3 신용 크라우딩: Δloan_rate/Δstln_rate 20d (T+3 지연) → 5d/20d 시장초과
T4 산업 리드-래그: 산업 내 최대유동 종목 +5%↑ 날 → 미동(<+1%) 후속주 익일 → 랜덤산업 플라시보
T5 요일 구조: 요일별 계약 EV 스캔
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)


def load():
    cols = ["code", "date", "market", "industry", "liq", "close", "ret_1d", "gap",
            "turn_z", "vol_ratio", "ft_5_5", "exec_5d", "ret_5d", "ret_20d"]
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    liq_ok = ((px["market"] == "KOSPI") & (px["liq"] >= 100e8)) | ((px["market"] == "KOSDAQ") & (px["liq"] >= 30e8))
    px = px[liq_ok].copy()
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    px["intraday_ret"] = px["ret_1d"] - px["gap"]
    return px.sort_values(["code", "date"]).reset_index(drop=True)


def evaluate(picks, name, full_years=None):
    """picks: DataFrame with policy_ret, date. 반환: 판정 문자열."""
    d = picks.dropna(subset=["policy_ret"])
    if len(d) < 200:
        print(f"  {name:44s} n={len(d)} — 표본 부족, 판정 불가")
        return None
    net = d["policy_ret"] - COST
    arr = net.values
    bs = [rng.choice(arr, len(arr), True).mean() for _ in range(300)]
    lo, hi = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
    yr = net.groupby(d["date"].dt.year).mean()
    win = (d["ft_5_5"] == 1).mean() * 100 if "ft_5_5" in d else float("nan")
    print(f"  {name:44s} n={len(d):6d} EV={net.mean():+.3f} CI[{lo:+.2f},{hi:+.2f}] "
          f"터치={win:.1f}% yr+={int((yr>0).sum())}/{len(yr)}")
    return {"n": len(d), "ev": float(net.mean()), "ci": [float(lo), float(hi)],
            "yr_pos": int((yr > 0).sum()), "yr_n": len(yr)}


def t1_overnight(px):
    print("\n===== T1 오버나이트 구조 (60d 누적 gap − 장중, 8y) =====", flush=True)
    g = px.groupby("code", group_keys=False)
    on = g["gap"].apply(lambda s: s.rolling(60, min_periods=40).sum().shift(1))
    it = g["intraday_ret"].apply(lambda s: s.rolling(60, min_periods=40).sum().shift(1))
    px = px.assign(on_spread=(on - it))
    d = px.dropna(subset=["on_spread", "policy_ret"])
    q = d.groupby("date")["on_spread"].rank(pct=True)
    evaluate(d[q >= 0.9], "상위10% (오버나이트 프리미엄 종목)")
    evaluate(d[q <= 0.1], "하위10% (장중 프리미엄 종목)")
    plc = d.copy()
    plc["on_spread"] = plc.groupby("date")["on_spread"].transform(lambda s: rng.permutation(s.values))
    qp = plc.groupby("date")["on_spread"].rank(pct=True)
    evaluate(plc[qp >= 0.9], "플라시보 상위10% (일내셔플)")
    # 순수 오버나이트 수확(종가매수→익일시가매도, 비용 0.3): 상위10%의 익일 gap
    nx = px.assign(next_gap=px.groupby("code")["gap"].shift(-1)).dropna(subset=["on_spread", "next_gap"])
    qn = nx.groupby("date")["on_spread"].rank(pct=True)
    hg = nx[qn >= 0.9]
    print(f"  순수 오버나이트(상위10%): 평균 익일 gap {hg['next_gap'].mean():+.3f}% − 비용 0.3 = "
          f"{hg['next_gap'].mean()-0.3:+.3f}% → {'생존' if hg['next_gap'].mean() > 0.35 else '비용 사망'}")


def t2_climax(px):
    print("\n===== T2 볼륨 클라이맥스 (turn_z>=3 & |ret_1d|>=8) =====", flush=True)
    ev = px[(px["turn_z"] >= 3)]
    up = ev[ev["ret_1d"] >= 8]
    dn = ev[ev["ret_1d"] <= -8]
    evaluate(up, "상승 클라이맥스 직후")
    evaluate(dn, "하락 클라이맥스 직후")
    base = px.sample(min(len(px), 200_000), random_state=0)
    evaluate(base, "무조건 베이스라인(전체)")
    # 클라이맥스 '다음' 조용한 날 진입 (이벤트+1일, 저변동 소화 후)
    px2 = px.assign(ev_up=((px["turn_z"] >= 3) & (px["ret_1d"] >= 8)).astype(int))
    px2["ev_up_prev"] = px2.groupby("code")["ev_up"].shift(1)
    calm = px2[(px2["ev_up_prev"] == 1) & (px2["ret_1d"].abs() < 2)]
    evaluate(calm, "상승클라이맥스 +1일 소화(|ret|<2) 후")


def t3_credit(px):
    print("\n===== T3 신용/대차 크라우딩 (T+3 지연, 20d 변화) =====", flush=True)
    cr = pd.read_parquet(f"{CACHE}/credit.parquet")
    cr["date"] = pd.to_datetime(cr["date"])
    cr = cr.sort_values(["code", "date"])
    g = cr.groupby("code", group_keys=False)
    cr["d_loan"] = g["loan_rate"].apply(lambda s: s - s.shift(20))
    cr["d_stln"] = g["stln_rate"].apply(lambda s: s - s.shift(20))
    # T+3 지연 (공표 지연 보수적)
    cr["sig_date"] = cr.groupby("code")["date"].shift(-3)
    m = px.merge(cr[["code", "sig_date", "d_loan", "d_stln"]].rename(columns={"sig_date": "date"}),
                 on=["code", "date"], how="inner")
    print(f"  병합 표본 {len(m)} ({m['date'].min().date()}..{m['date'].max().date()})")
    # 시장초과 20d (베타 교훈: 절대수익 주장 금지)
    mret = px.groupby("date")["ret_20d"].mean().rename("mkt20")
    m = m.join(mret, on="date")
    m["fwd20_ex"] = -(m["ret_20d"] - m["mkt20"])  # ret_20d는 과거 20d — forward 필요
    # forward 20d: shift(-20) of cum — 근사로 policy(5d) + 시장초과 5d 사용
    m5 = px.groupby("date")["policy_ret"].mean().rename("mkt_pol5")
    m = m.join(m5, on="date")
    m["pol_ex"] = m["policy_ret"] - m["mkt_pol5"]
    for sig, nm in (("d_loan", "신용융자 급증(상위10%)"), ("d_stln", "대차잔고 급증(상위10%)")):
        d = m.dropna(subset=[sig, "pol_ex"])
        q = d.groupby("date")[sig].rank(pct=True)
        top = d[q >= 0.9].copy(); bot = d[q <= 0.1].copy()
        top["policy_ret"] = top["pol_ex"]; bot["policy_ret"] = bot["pol_ex"]  # 시장초과로 평가
        evaluate(top, f"{nm} → 5d 시장초과")
        evaluate(bot, f"{nm.replace('급증','급감')}(하위10%) → 5d 시장초과")


def t4_leadlag(px):
    print("\n===== T4 산업 내 리드-래그 (랜덤산업 플라시보 필수) =====", flush=True)
    d = px.dropna(subset=["industry", "policy_ret"]).copy()
    d = d[d["industry"].astype(str).str.len() > 0]

    def run(frame, label):
        f = frame.copy()
        lead_liq = f.groupby(["date", "industry"])["liq"].transform("max")
        f["is_leader"] = f["liq"] == lead_liq
        lead_ret = f[f["is_leader"]].set_index(["date", "industry"])["ret_1d"]
        f = f.join(lead_ret.rename("leader_ret"), on=["date", "industry"])
        # 신호일: 대장 +5%↑ & 본인 <+1% & 대장 아님 → 익일 진입이므로 policy를 next day로
        f = f.sort_values(["code", "date"])
        f["pol_next"] = f.groupby("code")["policy_ret"].shift(-1)
        sig = f[(f["leader_ret"] >= 5) & (f["ret_1d"] < 1) & (~f["is_leader"])].copy()
        sig["policy_ret"] = sig["pol_next"]
        return evaluate(sig, label)

    run(d, "진짜 산업그룹")
    dp = d.copy()
    ind_map = dp[["code", "industry"]].drop_duplicates("code")
    dp = dp.drop(columns=["industry"]).merge(
        ind_map.assign(industry=rng.permutation(ind_map["industry"].values))[["code", "industry"]], on="code")
    run(dp, "플라시보(랜덤 산업 재배정)")


def t5_dow(px):
    print("\n===== T5 요일 구조 =====", flush=True)
    d = px.dropna(subset=["policy_ret"])
    for dow, nm in enumerate(["월", "화", "수", "목", "금"]):
        s = d[d["date"].dt.dayofweek == dow]
        net = s["policy_ret"] - COST
        yr = net.groupby(s["date"].dt.year).mean()
        print(f"  {nm}요일 신호: n={len(s):6d} EV={net.mean():+.3f} yr+={int((yr>0).sum())}/{len(yr)}")


def main():
    px = load()
    print(f"패널: {len(px)} rows, {px['date'].min().date()}..{px['date'].max().date()}", flush=True)
    t1_overnight(px)
    t2_climax(px)
    try:
        t3_credit(px)
    except Exception as e:
        print(f"  T3 실패: {e}")
    t4_leadlag(px)
    t5_dow(px)
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump({"done": True}, open(os.path.join(here, "frontier_edges.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
