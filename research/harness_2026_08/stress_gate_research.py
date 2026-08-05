#!/usr/bin/env python3
"""A1 (swing-main-2aac): KOFIA stress axis — crash early-detection incremental validation.

Pre-registered hypotheses (see task doc / RESEARCH_LOG):
  H1 (lead): stress z-spike days (forced_sell z60>2 / margin_unpaid z60>2 /
      deposit 5d-change z60<-2, each PIT-lagged 2 trading days) lead RISK_OFF
      entry events. Kill: median lead <= 0 trading days after lag.
  H2 (conditional EV): within regime cell (RISK_OFF-only, NORMAL-only), pick net
      EV on stress top-tercile days vs bottom-tercile days, date-level
      decomposition + bootstrap CI. Kill: |diff| < 0.3%p or CI contains 0.
  H3 (placebo): 100 date-shuffles of the stress score within cell; actual diff
      must exceed the placebo distribution.

Regime = LIVE definition (multi_agent/tools/report_kospi_intraday_swing.py::
market_drawdown_state): equal-weight liquid-pool (KOSPI liq>=100e8) cumulated
ret_1d from px_long; RISK_OFF iff dd20 < -5% OR ret5 < -3%.
NOTE: task brief said "FDR KS11" but the live code uses the px_long pool — the
live definition wins (per brief: "라이브 정의와 동일하게").

PIT discipline: KOFIA publishes T+1~2 → all stress signals shifted +2 trading
days before use.

Outputs: runtime_state/reports/validation/stress_gate_research_latest.md
Research only — no deploy/code changes.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path("~/research_cache").expanduser()
REPO = Path(__file__).resolve().parents[2]
OUT_MD = REPO / "runtime_state" / "reports" / "validation" / "stress_gate_research_latest.md"

COST_PCT = 0.3          # net = policy_ret - 0.3
Z_WIN = 60              # rolling z window (trading days)
PIT_LAG = 2             # trading-day publication lag
Z_TH = 2.0              # spike threshold
EPISODE_GAP = 10        # trading days of non-RISK_OFF required before a new entry event
H1_WINDOW = 15          # +/- trading days searched around an entry for nearest fire
MIN_LEAD_KILL = 0       # median lead <= this => kill
EV_FLOOR = 0.3          # %p measurement floor (§19)
N_BOOT = 2000
N_PLACEBO = 100
CRASH_CUT = pd.Timestamp("2026-06-01")  # 2026-06 regime crack + 2026-07 crash window
RNG = np.random.default_rng(20260805)


# ---------------------------------------------------------------- data
def load_regime() -> pd.DataFrame:
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["date", "market", "liq", "ret_1d"])
    d = px[(px["market"] == "KOSPI") & (px["liq"] >= 100e8)].copy()
    d["date"] = pd.to_datetime(d["date"])
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    dd20 = (lvl / lvl.rolling(20).max() - 1) * 100
    ret5 = (lvl / lvl.shift(5) - 1) * 100
    st = pd.DataFrame({"dd20": dd20, "ret5": ret5})
    st["risk_off"] = (st["dd20"] < -5.0) | (st["ret5"] < -3.0)
    st = st.dropna(subset=["dd20", "ret5"])
    return st


def load_stress(cal: pd.DatetimeIndex) -> pd.DataFrame:
    k = pd.read_parquet(CACHE / "kofia_stress.parquet")
    dep = (k[k["kind"] == "deposit"]
           .set_index("date")[["investor_deposit", "margin_unpaid", "forced_sell_amt", "forced_sell_pct"]]
           .sort_index())
    cr = k[k["kind"] == "credit"].set_index("date")[["credit_loan"]].sort_index()
    s = dep.join(cr, how="outer").sort_index()
    # align onto trading calendar (ffill across holidays, small limit)
    s = s.reindex(cal.union(s.index)).ffill(limit=3).reindex(cal)

    def z60(x: pd.Series) -> pd.Series:
        m = x.rolling(Z_WIN).mean()
        sd = x.rolling(Z_WIN).std()
        return (x - m) / sd.replace(0, np.nan)

    out = pd.DataFrame(index=cal)
    out["z_fs"] = z60(s["forced_sell_amt"])
    out["z_mu"] = z60(s["margin_unpaid"])
    out["dep5"] = s["investor_deposit"].pct_change(5) * 100
    out["z_dep5"] = z60(out["dep5"])
    out["z_cr5"] = z60(s["credit_loan"].pct_change(5) * 100)  # appendix only, not pre-registered
    # spike flags (pre-registered)
    out["fire_fs"] = out["z_fs"] > Z_TH
    out["fire_mu"] = out["z_mu"] > Z_TH
    out["fire_dep"] = out["z_dep5"] < -Z_TH
    out["fire_any"] = out[["fire_fs", "fire_mu", "fire_dep"]].any(axis=1)
    # composite continuous stress score for H2 terciles
    out["stress_score"] = out[["z_fs", "z_mu"]].mean(axis=1) - out["z_dep5"] / 2
    # PIT lag: value published T+1~2 -> usable from t+2
    lagged = out.shift(PIT_LAG)
    lagged.columns = [c + "_L" for c in lagged.columns]
    return pd.concat([out, lagged], axis=1)


def load_picks() -> pd.DataFrame:
    p = pd.read_parquet(CACHE / "picks_8y_swing.parquet")
    p["date"] = pd.to_datetime(p["date"])
    p = p.dropna(subset=["policy_ret"])
    p["net"] = p["policy_ret"] - COST_PCT
    return p


# ---------------------------------------------------------------- H1
def h1_lead_lag(st: pd.DataFrame, sx: pd.DataFrame) -> dict:
    cal = st.index
    ro = st["risk_off"].values
    # entry events: RISK_OFF today, no RISK_OFF in prior EPISODE_GAP trading days
    entries = []
    for i in range(EPISODE_GAP, len(cal)):
        if ro[i] and not ro[max(0, i - EPISODE_GAP):i].any():
            entries.append(i)
    res = {}
    for name, col in [("forced_sell", "fire_fs_L"), ("margin_unpaid", "fire_mu_L"),
                      ("deposit_5d", "fire_dep_L"), ("any", "fire_any_L")]:
        fires = sx[col].reindex(cal).eq(True).values
        leads, matched = [], 0
        for i in entries:
            lo, hi = max(0, i - H1_WINDOW), min(len(cal) - 1, i + H1_WINDOW)
            idxs = [j for j in range(lo, hi + 1) if fires[j]]
            if not idxs:
                continue
            j = min(idxs, key=lambda j: (abs(i - j), j))  # nearest, tie -> earlier
            leads.append(i - j)  # >0 = signal leads
            matched += 1
        res[name] = {
            "n_episodes": len(entries),
            "n_matched": matched,
            "leads": leads,
            "median_lead": float(np.median(leads)) if leads else None,
            "mean_lead": float(np.mean(leads)) if leads else None,
            "pct_lead_pos": float(np.mean([l > 0 for l in leads]) * 100) if leads else None,
        }
    res["_entry_dates"] = [str(cal[i].date()) for i in entries]
    return res


# ---------------------------------------------------------------- H2/H3
def daily_net(picks: pd.DataFrame) -> pd.Series:
    return picks.groupby("date")["net"].mean()


def tercile_diff(day_ret: pd.Series, score: pd.Series) -> dict | None:
    df = pd.DataFrame({"ret": day_ret, "s": score}).dropna()
    if len(df) < 30:
        return None
    q1, q2 = df["s"].quantile([1 / 3, 2 / 3])
    top, bot = df[df["s"] >= q2], df[df["s"] <= q1]
    if len(top) < 10 or len(bot) < 10:
        return None
    diff = top["ret"].mean() - bot["ret"].mean()
    # bootstrap over days
    boots = np.empty(N_BOOT)
    tv, bv = top["ret"].values, bot["ret"].values
    for b in range(N_BOOT):
        boots[b] = (RNG.choice(tv, len(tv)).mean() - RNG.choice(bv, len(bv)).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # placebo: shuffle score across days
    plc = np.empty(N_PLACEBO)
    sv = df["s"].values.copy()
    for b in range(N_PLACEBO):
        RNG.shuffle(sv)
        d2 = df.copy()
        d2["s"] = sv
        t2, b2 = d2[d2["s"] >= q2], d2[d2["s"] <= q1]
        plc[b] = t2["ret"].mean() - b2["ret"].mean() if len(t2) and len(b2) else np.nan
    plc = plc[~np.isnan(plc)]
    p_plc = float(np.mean(np.abs(plc) >= abs(diff))) if len(plc) else None
    return {
        "n_days": len(df), "n_top": len(top), "n_bot": len(bot),
        "top_mean": float(top["ret"].mean()), "bot_mean": float(bot["ret"].mean()),
        "diff": float(diff), "ci_lo": float(lo), "ci_hi": float(hi),
        "placebo_p": p_plc, "placebo_abs_q95": float(np.percentile(np.abs(plc), 95)) if len(plc) else None,
    }


def h2_h3(picks: pd.DataFrame, st: pd.DataFrame, sx: pd.DataFrame, exclude_crash: bool) -> dict:
    day = daily_net(picks)
    df = pd.DataFrame({"ret": day}).join(st[["risk_off"]], how="inner")
    if exclude_crash:
        df = df[df.index < CRASH_CUT]
    out = {}
    for cell, mask in [("RISK_OFF", df["risk_off"]), ("NORMAL", ~df["risk_off"])]:
        sub = df[mask]
        cell_res = {}
        for axis, col in [("composite", "stress_score_L"), ("forced_sell_z", "z_fs_L"),
                          ("margin_unpaid_z", "z_mu_L"), ("deposit5d_z_neg", "z_dep5_L")]:
            score = sx[col].reindex(sub.index)
            if axis == "deposit5d_z_neg":
                score = -score  # high stress = deposit falling
            cell_res[axis] = tercile_diff(sub["ret"], score)
        out[cell] = {"n_days": len(sub), "axes": cell_res}
    return out


# ---------------------------------------------------------------- report
def fmt_h2_table(res: dict) -> str:
    rows = ["| cell | axis | n(days) | top mean | bot mean | diff (%p) | 95% CI | placebo p | verdict |",
            "|---|---|---|---|---|---|---|---|---|"]
    for cell, cd in res.items():
        for axis, r in cd["axes"].items():
            if r is None:
                rows.append(f"| {cell} | {axis} | {cd['n_days']} | - | - | - | - | - | insufficient |")
                continue
            ci0 = r["ci_lo"] <= 0 <= r["ci_hi"]
            small = abs(r["diff"]) < EV_FLOOR
            verdict = "KILL" if (ci0 or small) else "alive"
            rows.append(
                f"| {cell} | {axis} | {r['n_days']} ({r['n_top']}/{r['n_bot']}) | "
                f"{r['top_mean']:+.2f} | {r['bot_mean']:+.2f} | {r['diff']:+.2f} | "
                f"[{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}] | {r['placebo_p']:.2f} | {verdict} |")
    return "\n".join(rows)


def main() -> None:
    st = load_regime()
    sx = load_stress(st.index)
    picks = load_picks()

    h1 = h1_lead_lag(st, sx)
    # H1 excluding crash-window episodes: recompute over entries before CRASH_CUT
    st_ex = st[st.index < CRASH_CUT]
    h1_ex = h1_lead_lag(st_ex, sx)

    h2_full = h2_h3(picks, st, sx, exclude_crash=False)
    h2_ex = h2_h3(picks, st, sx, exclude_crash=True)

    ro_days = int(st["risk_off"].sum())
    lines = []
    lines.append("# Stress gate research — KOFIA 스트레스 축 크래시 조기감지 증분 검증 (A1, swing-main-2aac)")
    lines.append("")
    lines.append(f"date: {pd.Timestamp.now():%Y-%m-%d} | harness: research/harness_2026_08/stress_gate_research.py")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- 레짐: 라이브 market_drawdown_state 정의 재구성 (px_long KOSPI liq>=100억 equal-weight pool, "
                 f"RISK_OFF iff dd20<-5 or ret5<-3). 주의: 과제문서의 'FDR KS11'은 라이브 코드와 불일치 — 라이브 정의 사용.")
    lines.append(f"- 레짐 표본: {st.index.min():%Y-%m-%d} ~ {st.index.max():%Y-%m-%d}, {len(st)}일, RISK_OFF {ro_days}일 ({ro_days/len(st)*100:.1f}%)")
    lines.append(f"- 스트레스 신호: z60 롤링, 스파이크=z>{Z_TH} (예탁금은 5d 변화 z<-{Z_TH}), PIT 래그 {PIT_LAG}거래일")
    lines.append(f"- composite score = mean(z_fs, z_mu) - z_dep5/2 (하니스 고정, 결과 확인 전 정의)")
    lines.append(f"- 픽: picks_8y_swing.parquet, net = policy_ret - {COST_PCT}, 날짜단위 분해(일평균)")
    lines.append(f"- 크래시 제외 변형: {CRASH_CUT:%Y-%m-%d} 이후 제거 (2026-06 레짐균열 + 2026-07 크래시)")
    lines.append("")

    lines.append("## H1 — 선행성 (lead>0 = 스트레스가 RISK_OFF 진입을 선행, 거래일)")
    lines.append("")
    lines.append("| signal | episodes | matched | median lead | mean lead | %lead>0 | leads |")
    lines.append("|---|---|---|---|---|---|---|")
    for tag, h in [("full", h1), (f"ex-crash(<{CRASH_CUT:%Y-%m})", h1_ex)]:
        for name in ["forced_sell", "margin_unpaid", "deposit_5d", "any"]:
            r = h[name]
            ml = f"{r['median_lead']:+.1f}" if r["median_lead"] is not None else "-"
            mn = f"{r['mean_lead']:+.1f}" if r["mean_lead"] is not None else "-"
            pp = f"{r['pct_lead_pos']:.0f}%" if r["pct_lead_pos"] is not None else "-"
            lines.append(f"| [{tag}] {name} | {r['n_episodes']} | {r['n_matched']} | {ml} | {mn} | {pp} | {r['leads']} |")
    lines.append("")
    lines.append(f"- RISK_OFF 진입 에피소드({EPISODE_GAP}거래일 무-RO 선행 조건): {h1['_entry_dates']}")
    lines.append(f"- 킬 기준: 래그 반영 후 median lead <= 0 → 동행/후행 판정")
    lines.append("- 주의: 2026-07 크래시는 별도 에피소드가 아님 — RISK_OFF가 2026-05-15 진입 후 2026-08-04까지 사실상 연속"
                 "(무-RO 갭 < 10거래일). 따라서 H1의 full과 ex-crash가 동일(전 에피소드가 2026-06 이전 진입). "
                 "해당 에피소드(2026-05-15) 개별 lead: forced_sell +2 (2026-05-13 발화, 래그 반영 후), "
                 "margin_unpaid -1, deposit_5d 무발화 — 크래시 자체에선 반대매매가 2일 선행한 단일 사례이나 "
                 "8y 분포의 중앙값은 음수.")
    lines.append("")

    lines.append("## H2/H3 — 같은 레짐 셀 내 조건부 EV 차등 (top vs bottom tercile, 날짜단위, 부트스트랩 CI, 플라시보 100회)")
    lines.append("")
    lines.append("### 전체 표본")
    lines.append(fmt_h2_table(h2_full))
    lines.append("")
    lines.append(f"### 크래시 제외 (< {CRASH_CUT:%Y-%m-%d}; 픽 표본은 2026-06-30까지라 6월만 제거됨)")
    lines.append(fmt_h2_table(h2_ex))
    lines.append("")
    lines.append(f"- 킬 기준: |diff| < {EV_FLOOR}%p (§19 측정하한) 또는 CI가 0 포함")
    lines.append("- 픽 표본은 2026-06-30까지 → 2026-07 크래시 본체는 H2 표본에 없음. 크래시 제외 변형은 2026-06"
                 " 레짐균열 구간(RISK_OFF 18일)만 제거.")
    lines.append("")

    lines.append("## 판정 (사전등록 킬 기준 적용)")
    lines.append("")
    lines.append("- **H1: KILL — 동행/후행, dd20 중복.** 전 신호 median lead 음수(forced_sell -3, margin_unpaid -3,"
                 " deposit_5d -1, any -1). 스파이크는 RISK_OFF 진입 후 1~3거래일에 발화 — KOFIA 축은 dd20 기반"
                 " 레짐 전환을 선행하지 못함. PIT 래그 2일이 원래 있던 소폭의 동행성마저 소거"
                 " (COVID 사례: 진입 2020-02-24, z_fs 스파이크 02-25, 래그 후 발화 02-27).")
    lines.append("- **H2: KILL (사전등록 primary=composite 기준).** composite는 RISK_OFF/NORMAL 양 셀, 크래시"
                 " 포함/제외 전부 CI 0 포함. NORMAL 셀은 전 축 |diff|<0.3%p 수준의 무신호.")
    lines.append("- 주변부 관찰(포장 아님, 판정에 불사용): ① RISK_OFF에서 margin_unpaid 상위 tercile 날의 픽 EV가"
                 " 오히려 **높음**(+1.25%p, placebo p=0.03, 단 CI 0 포함) — 스트레스 스파이크가 투매 바닥"
                 "(반등베타)을 마킹하는 방향. '스트레스 높으면 회피' 게이트는 RISK_OFF 최고 EV 날을 잘라낼 위험."
                 " ② deposit5d 축만 게이트 방향(-1.24%p, CI [-2.45,-0.02])이나 크래시 제외 시 사망(CI 0 포함),"
                 " 8개 검정 중 1개 p=0.04 — 다중비교 아티팩트 범위, 타 축과 부호 불일치.")
    lines.append("- **종합: 게이트 후보 기각.** 배포 제안 조건(H1·H2 동시 생존) 미충족 — H1·H2 모두 사망."
                 " 사전등록 기준상 '하나 생존 시 관측 지속'에도 미달(deposit5d 단독 생존은 크래시 포함 표본"
                 " 한정·비강건으로 생존 인정 불가). KOFIA 스트레스 축은 크래시 조기감지 증분 없음 — 현행"
                 " dd20/ret5 레짐 정의로 충분.")
    lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD}")
    print(json.dumps({"h1_median_any_full": h1["any"]["median_lead"],
                      "h1_median_any_ex": h1_ex["any"]["median_lead"]}, indent=2))


if __name__ == "__main__":
    main()
