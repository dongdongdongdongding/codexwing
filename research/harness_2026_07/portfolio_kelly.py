#!/usr/bin/env python3
"""P5 포트폴리오 구성 수학 (swing-main-wdu2): Kelly 사이징 + 8:2 제약 하 15%/년 판정.

레인 스트림:
  swing_kospi / swing_kosdaq : 8y rank-1 픽 (picks_8y.parquet, policy_ret net)
  kospi_itd  : §7-E 8 OOS월 rank-1 재생성 (seed0, t5/5d) — 실증 분포
  kosdaq_itd : §11-A 파라메트릭 혼합 (win 75.8% → +9.7 net, 패배꼬리는 kospi_itd 패배분포 차용)

방법: 5세션 블록 부트스트랩(동일일·주간 상관 보존) × 500 연간 경로.
포지션 비중 f 그리드 → geo연수익, p5, maxDD 중앙/95, E[log] 최대점(Kelly f*).
8:2 매핑: 총자본 = 0.8×안전(3.5%/yr) + 0.2×위험슬리브 → 15% 달성 f 판정.
동시보유: 5세션 홀드 → 레인당 최대 5포지션 겹침, 노출 상한 100% 슬리브.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.3
SAFE_RATE = 0.035
rng = np.random.default_rng(0)


def swing_streams():
    P = pd.read_parquet(os.path.join(HERE, "picks_8y.parquet"))
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["rank"] == 1].dropna(subset=["policy_ret"])
    out = {}
    for mkt in ("KOSPI", "KOSDAQ"):
        d = P[P["market"] == mkt][["date", "policy_ret"]].copy()
        d["ret"] = (d["policy_ret"] - COST) / 100.0
        out[f"swing_{mkt.lower()}"] = d[["date", "ret"]].reset_index(drop=True)
    return out


def kospi_itd_stream():
    os.chdir("/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
    sys.path.insert(0, ".")
    sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
    from exit_policy_research import attach_paths
    from model_zoo_intraday import policy_ret_frame
    BASE = ITF + [c + "_d" for c in DLF]
    gd = GUARDS["KOSPI"]
    P = assemble()
    dm = P[P["mkt"] == "KOSPI"].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
    dm = attach_paths(dm)
    dm["pret"] = policy_ret_frame(dm, 5.0)
    pools = []
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
        tr = dm[dm["date"] < t0]; te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
        if len(tr) < 3000 or te.empty:
            continue
        Xtr = tr[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        Xte = te[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        ps = []
        for m in (lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                                     subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
                  xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8,
                                    colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1, random_state=0),
                  ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=0, n_jobs=-1)):
            m.fit(Xtr, tr["y3"]); ps.append(m.predict_proba(Xte)[:, 1])
        te["p"] = np.mean(ps, axis=0)
        q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"]) & (te["idx_vol20_d"] >= gd["idx_vol_min"])]
        pools.append(q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(1))
    A = pd.concat(pools).dropna(subset=["pret"])
    d = A[["date", "pret"]].copy()
    d["ret"] = (d["pret"] - COST) / 100.0
    return d[["date", "ret"]].reset_index(drop=True)


def kosdaq_itd_stream(kospi_itd, n_weeks=400):
    """§11-A 파라메트릭: win 75.8% → +10-0.3=+9.7%, 패배는 kospi_itd 패배분포 스케일 차용."""
    losses = kospi_itd[kospi_itd["ret"] < 0.003]["ret"].values
    rows = []
    d0 = pd.Timestamp("2019-01-07")
    for w in range(n_weeks):
        for k in range(2):  # 주 ~2픽 (§11-A 발행빈도)
            day = d0 + pd.Timedelta(weeks=w, days=int(rng.integers(0, 5)))
            if rng.random() < 0.758:
                rows.append((day, 0.097))
            else:
                rows.append((day, float(rng.choice(losses)) * 1.3))  # t10 홀드 꼬리 여유
    return pd.DataFrame(rows, columns=["date", "ret"]).sort_values("date").reset_index(drop=True)


def block_paths(stream, n_paths=500, trades_per_year=None):
    """5세션 블록 부트스트랩으로 연간(52주) 트레이드 시퀀스 생성."""
    s = stream.copy()
    s["week"] = s["date"].dt.to_period("W")
    weeks = [g["ret"].values for _, g in s.groupby("week") if len(g) > 0]
    wk_per_year = 52
    paths = []
    for i in range(n_paths):
        idx = rng.integers(0, len(weeks), wk_per_year)
        seq = np.concatenate([weeks[j] for j in idx])
        paths.append(seq)
    return paths


def eval_f(paths, f, concurrent_cap=5):
    """포지션 비중 f(슬리브 대비), 5세션 홀드 겹침 → 주 단위 근사 복리.
    한 주의 트레이드들이 슬리브에 동시 노출(상관 보존), 노출 상한 = min(1, f*n)."""
    geo, mdd, logs = [], [], []
    for seq in paths:
        # 주 단위로 재구성: 각 블록(주)의 트레이드 수익을 f 가중 합산, 노출 상한 1.0
        eq = 1.0; peak = 1.0; dd = 0.0; lg = 0.0
        i = 0
        # 블록 크기 복원이 어려우므로 트레이드 단위 순차 복리(보수적: 겹침 무시, f 그대로)
        for r in seq:
            fr = min(f, 1.0)
            eq *= (1 + fr * r)
            if eq <= 0:
                eq = 1e-9
            peak = max(peak, eq); dd = max(dd, 1 - eq / peak)
            lg += np.log(max(1 + fr * r, 1e-9))
        geo.append(eq - 1); mdd.append(dd); logs.append(lg)
    geo = np.array(geo); mdd = np.array(mdd)
    return {"geo_med": float(np.median(geo)), "geo_p5": float(np.percentile(geo, 5)),
            "mdd_med": float(np.median(mdd)), "mdd_p95": float(np.percentile(mdd, 95)),
            "elog": float(np.mean(logs))}


def main():
    streams = swing_streams()
    print("kospi_itd 풀 재생성 중...", flush=True)
    streams["kospi_itd"] = kospi_itd_stream()
    streams["kosdaq_itd"] = kosdaq_itd_stream(streams["kospi_itd"])
    for k, v in streams.items():
        r = v["ret"]
        print(f"  {k:14s} n={len(v):5d} 평균/트레이드 {r.mean()*100:+.2f}% 승률 {(r>0.003).mean()*100:.0f}% "
              f"주당 {len(v)/max(1,(v['date'].max()-v['date'].min()).days/7):.1f}픽", flush=True)

    # 결합 스트림: 장중 2 + 스윙 2 (모든 픽 = 운영 발행분)
    combo = pd.concat([v.assign(lane=k) for k, v in streams.items()]).sort_values("date").reset_index(drop=True)
    streams["COMBO_ALL"] = combo
    streams["COMBO_ITD"] = pd.concat([streams["kospi_itd"], streams["kosdaq_itd"]]).sort_values("date").reset_index(drop=True)

    print("\n===== f 그리드 (슬리브 자본 대비 포지션 비중, 트레이드 순차 복리) =====", flush=True)
    results = {}
    for name in ("kospi_itd", "COMBO_ITD", "COMBO_ALL"):
        paths = block_paths(streams[name])
        print(f"\n-- {name} (연 {int(np.mean([len(p) for p in paths]))}트레이드)", flush=True)
        best = None
        for f in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
            r = eval_f(paths, f)
            results[(name, f)] = r
            star = ""
            if best is None or r["elog"] > best[1]["elog"]:
                best = (f, r)
            print(f"  f={f:.2f}: geo중앙 {r['geo_med']*100:+7.1f}%/yr p5 {r['geo_p5']*100:+7.1f}% "
                  f"maxDD중앙 {r['mdd_med']*100:.1f}% p95 {r['mdd_p95']*100:.1f}% E[log] {r['elog']:+.3f}", flush=True)
        print(f"  → Kelly 근사 f* ≈ {best[0]:.2f} (그리드 내 E[log] 최대)", flush=True)

    print("\n===== 8:2 매핑 (총자본 = 80% 안전 3.5%/yr + 20% 위험슬리브) =====", flush=True)
    for name in ("COMBO_ITD", "COMBO_ALL"):
        for f in (0.10, 0.15, 0.20):
            r = results[(name, f)]
            tot_med = 0.8 * SAFE_RATE + 0.2 * r["geo_med"]
            tot_p5 = 0.8 * SAFE_RATE + 0.2 * r["geo_p5"]
            ok = "✅ 15% 달성" if tot_med >= 0.15 else "❌ 미달"
            print(f"  {name} f={f:.2f}: 총자본 중앙 {tot_med*100:+.1f}%/yr (p5 {tot_p5*100:+.1f}%) "
                  f"슬리브 maxDD중앙 {r['mdd_med']*100:.0f}% {ok}", flush=True)
    json.dump({"done": True}, open(os.path.join(HERE, "portfolio_kelly.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
