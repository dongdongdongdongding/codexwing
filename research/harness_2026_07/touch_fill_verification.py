#!/usr/bin/env python3
"""PKG-B ③ (§40): 터치익절 체결 가정 검증 — fill=max(tgt,open)은 지정가 대기 체결을 전제한다.

완전성 비판 (4): 원장 채점은 5일 내 High≥목표가면 목표가 체결로 간주하지만, 고가가 목표를
스치기만 하고 반락한 날은 실제 체결 확률이 100%가 아니다. B트랙 '현실 진입가' 교훈이 진입에는
적용됐지만 청산에는 미적용 상태였다. 승리 +5 캡 비대칭 계약에서 승리 체결률 하락은 EV를 직접
잠식하므로, 보유 분봉(~/research_cache/intraday/, 2025-07~)으로 터치일의 체결 현실성을 실측한다.

방법: 터치 승리 픽별로 진입일~+5거래일 분봉을 스캔 →
  - first-touch 분: High ≥ target 첫 등장
  - overshoot: 윈도우 내 max(High)/target − 1 (%) — 목표가를 '뚫고' 갔는가
  - at_or_above_min: High ≥ target 분 수 / above_vol: 그 분들의 거래량 합
  - thin touch 판정: overshoot < 0.2% AND at-or-above ≤ 2분 — 지정가 미체결 위험 구간
EV 임팩트: thin touch가 절반 미체결이라 가정하면(그 픽은 5d 종가 청산으로 강등) EV 변화를 계산.
산출: runtime_state/reports/validation/touch_fill_verification_latest.{json,md}
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "runtime_state" / "reports" / "experimental"
CACHE = Path(os.path.expanduser("~/research_cache/intraday"))
OUT_J = ROOT / "runtime_state" / "reports" / "validation" / "touch_fill_verification_latest.json"
OUT_M = ROOT / "runtime_state" / "reports" / "validation" / "touch_fill_verification_latest.md"

THIN_OVERSHOOT_PCT = 0.2   # 목표 초과폭 미만이면 '뚫지 못함'
THIN_MINUTES = 2           # 목표가 이상 체류 분


def _rows(fp):
    out = []
    for l in Path(fp).read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def load_minutes(code):
    code = str(code).split(".")[0]  # '066570.KS' → '066570'
    fp = CACHE / f"{str(code).zfill(6)}.parquet"
    if not fp.exists():
        return None
    df = pd.read_parquet(fp)
    df.index = pd.to_datetime(df.index)
    return df


def analyze(picks, label):
    res = []
    for p in picks:
        code, entry, tgt_pct, d0 = p["code"], p["entry"], p["tgt_pct"], pd.Timestamp(p["date"])
        target = entry * (1 + tgt_pct / 100.0)
        m = load_minutes(code)
        if m is None:
            continue
        days = sorted({d.date() for d in m.index if d.date() > d0.date()})[:5]  # 진입 익일부터 5거래일
        if label != "swing":  # 장중 레인은 당일 15:00 진입 → 당일 포함
            days = sorted({d.date() for d in m.index if d.date() >= d0.date()})[:5]
        if not days:
            continue
        w = m[pd.Series([d.date() for d in m.index], index=m.index).isin(days)]
        hit = w[w["High"] >= target]
        if hit.empty:
            continue  # 원장상 터치인데 분봉에 없으면 스킵(데이터 갭)
        overshoot = (w["High"].max() / target - 1) * 100
        at_min = int(len(hit))
        above_vol = float(hit["Volume"].sum())
        close_settles = bool(w.loc[hit.index[0]:]["Close"].iloc[-1] >= target)
        thin = (overshoot < THIN_OVERSHOOT_PCT) and (at_min <= THIN_MINUTES)
        res.append({"code": code, "date": str(d0.date()), "overshoot_pct": round(float(overshoot), 3),
                    "at_or_above_min": at_min, "above_vol": above_vol, "thin_touch": bool(thin),
                    "fallback_ret_net": p.get("fallback_ret"), "win_ret_net": p.get("win_ret")})
    return res


def main():
    # 스윙: ft_touch5 승리 픽 (KOSPI/KOSDAQ, 계약 tp는 contract 필드)
    swing_picks = []
    for r in _rows(EXP / "kr_swing_candidate_ledger.jsonl"):
        if not r.get("ft_touch5") or not isinstance(r.get("policy_ret"), (int, float)):
            continue
        tp = 10.0 if "t10" in str(r.get("contract", "")) else 5.0
        entry = r.get("entry_open") or r.get("close")
        if not entry:
            continue
        # fallback: 터치 미체결 시 5d 종가 수익(ret_5d 미보관 → policy_ret 대비 근사 불가면 None)
        swing_picks.append({"code": r["ticker"], "date": r["date"], "entry": float(entry),
                            "tgt_pct": tp, "win_ret": float(r["policy_ret"]) - 0.3,
                            "fallback_ret": None})
    # 코스피 장중: exit_t5_h5 == +5 (터치 승리), 진입 entry_reference_price(15:00 부근)
    itd_picks = []
    for r in _rows(EXP / "kospi_intraday_swing_ledger.jsonl"):
        v = r.get("exit_t5_h5")
        if not isinstance(v, (int, float)) or v < 4.99:
            continue
        entry = r.get("entry_reference_price") or r.get("close_vwap")
        if not entry:
            continue
        fb = r.get("ret5d")
        itd_picks.append({"code": r["ticker"], "date": r["date"], "entry": float(entry),
                          "tgt_pct": 5.0, "win_ret": v - 0.3,
                          "fallback_ret": (float(fb) - 0.3) if isinstance(fb, (int, float)) else None})

    out = {}
    for label, picks in (("swing", swing_picks), ("kospi_intraday", itd_picks)):
        r = analyze(picks, label)
        if not r:
            out[label] = {"n": 0}
            continue
        df = pd.DataFrame(r)
        thin_rate = float(df["thin_touch"].mean())
        # EV 임팩트: thin 픽 절반이 미체결 → 5d 종가 청산(fallback). fallback 미보유 시 0% 가정(보수).
        fb = df["fallback_ret_net"].astype(float)
        fb = fb.fillna(0.0)
        win = df["win_ret_net"].astype(float)
        ev_assumed = float(win.mean())
        adj = win.copy()
        thin_idx = df.index[df["thin_touch"]]
        adj.loc[thin_idx] = 0.5 * win.loc[thin_idx] + 0.5 * fb.loc[thin_idx]
        out[label] = {"n": len(df), "coverage": f"{len(df)}/{len(picks)}",
                      "thin_touch_rate_pct": round(thin_rate * 100, 1),
                      "median_overshoot_pct": round(float(df["overshoot_pct"].median()), 2),
                      "median_at_or_above_min": int(df["at_or_above_min"].median()),
                      "ev_win_assumed": round(ev_assumed, 2),
                      "ev_win_adjusted": round(float(adj.mean()), 2),
                      "ev_impact_pp": round(float(adj.mean()) - ev_assumed, 2),
                      "thin_examples": df[df["thin_touch"]][["code", "date", "overshoot_pct",
                                                            "at_or_above_min"]].to_dict("records")[:8]}
    rep = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "method": f"thin touch = overshoot<{THIN_OVERSHOOT_PCT}% AND at-or-above<={THIN_MINUTES}분; "
                     "EV 임팩트 = thin 절반 미체결 가정(미체결분은 5d 종가, fallback 미보유 시 0% 보수 가정)",
           "results": out}
    OUT_J.parent.mkdir(parents=True, exist_ok=True)
    OUT_J.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 터치익절 체결 검증 — {rep['generated_at'][:10]}", "", rep["method"], "",
             "| 레인 | n(커버) | thin% | 중앙 overshoot% | 중앙 체류분 | EV(가정) | EV(조정) | Δ |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for k, v in out.items():
        if not v.get("n"):
            lines.append(f"| {k} | 0 | - | - | - | - | - | - |")
            continue
        lines.append(f"| {k} | {v['coverage']} | {v['thin_touch_rate_pct']} | {v['median_overshoot_pct']} | "
                     f"{v['median_at_or_above_min']} | {v['ev_win_assumed']} | {v['ev_win_adjusted']} | "
                     f"{v['ev_impact_pp']} |")
    OUT_M.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "thin_examples"} for k, v in out.items()},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
