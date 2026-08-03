#!/usr/bin/env python3
"""PKG-B ① (§40, 운영자 승인): §20 구성수학의 forward 재계산 — '정직한 현재 연환산 기대'.

§20(07-07)은 백테스트 EV(코스피 장중 +3.30, 스윙 +0.52/0.33)와 연 ~578트레이드로
총자본 +15.6%/yr 중앙을 도출했다. 그 입력이 forward에서 붕괴(부호 반전+빈도 붕괴)했으므로
같은 산수를 forward 원장(성숙분, net)으로 다시 돌린다. 시나리오:
  S0 현 발행 스트림 (PKG-A 이후: DEGRADE 스트림 제외 → kosdaq guard만 실사이징)
  S1 DEGRADE 원복 가정 (전 레인 forward EV 그대로 발행) — 반면교사
  S2 스윙 수리 성공 가정 (§39 섹터 수리로 크래시 손실 재발 방지 = 크래시 제외 EV)
  S3 kr_selective top-1 승격 가정 (shadow n=21 EV 유지 가정 — 낙관 상한)
산출: runtime_state/reports/validation/portfolio_honest_expectation_latest.{json,md}
주의: 전부 소표본 — 이 수치는 '목표 대비 현위치'의 산수이지 예측이 아님.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "runtime_state" / "reports" / "experimental"
OUT_J = ROOT / "runtime_state" / "reports" / "validation" / "portfolio_honest_expectation_latest.json"
OUT_M = ROOT / "runtime_state" / "reports" / "validation" / "portfolio_honest_expectation_latest.md"

SAFE_RATE = 0.035   # §20: 안전 80% 슬리브 수익률/yr
RISK_W = 0.20       # 8:2
TRADING_DAYS = 245
CRASH_LO, CRASH_HI = "2026-07-16", "2026-07-24"  # §39 크래시 진입창


def _rows(fp: Path):
    out = []
    if not fp.exists():
        return out
    for l in fp.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


HOLD_DAYS = 5  # 전 레인 5d 계약 (보수적 상한)


def stream(fp: Path, field: str, cost: float, label: str, drop_crash=False):
    rows = _rows(fp)
    # 빈도는 '발행' 기준: 원장 전체 행(미정산 포함)의 날짜 범위로 연환산. span 하한 30일
    # (정산분만 쓰면 kosdaq guard처럼 3일 span에 608/yr 같은 왜곡이 남 — 1차 실행에서 확인).
    all_dates = pd.to_datetime([r.get("date") for r in rows if r.get("date")]).normalize()
    rec = [(r.get("date"), float(r[field]) - cost) for r in rows
           if isinstance(r.get(field), (int, float))]
    if drop_crash:
        rec = [(d, v) for d, v in rec if not (d and CRASH_LO <= str(d)[:10] <= CRASH_HI)]
    if not rec or not len(all_dates):
        return None
    df = pd.DataFrame(rec, columns=["date", "ret"])
    span_days = max((all_dates.max() - all_dates.min()).days, 30)
    freq_yr = len(rows) / span_days * 365.0
    return {"label": label, "n": len(df), "n_issued": len(rows),
            "ev_net": round(float(df["ret"].mean()), 2),
            "win": round(float((df["ret"] > 0.3).mean()) * 100, 1),
            "freq_yr": round(freq_yr, 0), "rets": df["ret"].to_numpy(),
            "span_days": int(span_days)}


def annual(streams, sizing_pct):
    """산수: Σ freq × EV × f (총자본 %p), 슬리브 용량 캡 적용 + 부트스트랩 분위.

    노출 상한(§20 8:2): 위험슬리브 20% ÷ 픽당 f = 최대 동시보유 → ×(245/hold) = 연 최대
    체결 가능 트레이드. 원장 발행 빈도가 이를 넘으면 비례 축소(전부 살 수 없음 — 완전성
    비판 (5)의 동시노출 문제를 산수에 반영)."""
    capacity = (RISK_W / (sizing_pct / 100.0)) * (TRADING_DAYS / HOLD_DAYS)
    raw_freq = sum(s["freq_yr"] for s in streams)
    scale = min(1.0, capacity / raw_freq) if raw_freq > 0 else 0.0
    arith = sum(s["freq_yr"] * scale * (s["ev_net"] / 100.0) * (sizing_pct / 100.0) for s in streams)
    boot = []
    rng = np.random.default_rng(0)
    for _ in range(1000):
        tot = 0.0
        for s in streams:
            k = rng.poisson(s["freq_yr"] * scale)
            if k and len(s["rets"]):
                tot += rng.choice(s["rets"], k, replace=True).sum() / 100.0 * (sizing_pct / 100.0)
        boot.append(tot)
    b = np.array(boot) * 100
    safe_pp = (1 - RISK_W) * SAFE_RATE * 100
    return {"capacity_trades_yr": round(capacity, 0), "raw_freq_yr": round(raw_freq, 0),
            "capacity_scale": round(scale, 3),
            "risk_sleeve_pp": round(arith * 100, 1),
            "total_with_safe_pp": round(safe_pp + arith * 100, 1),
            "boot_p5": round(float(np.percentile(b, 5)) + safe_pp, 1),
            "boot_p50": round(float(np.percentile(b, 50)) + safe_pp, 1),
            "boot_p95": round(float(np.percentile(b, 95)) + safe_pp, 1)}


def main():
    swing = stream(EXP / "kr_swing_candidate_ledger.jsonl", "policy_ret", 0.3, "swing_candidate")
    swing_fix = stream(EXP / "kr_swing_candidate_ledger.jsonl", "policy_ret", 0.3,
                       "swing_candidate(크래시제외=수리가정)", drop_crash=True)
    kospi_itd = stream(EXP / "kospi_intraday_swing_ledger.jsonl", "exit_t5_h5", 0.3, "kospi_intraday_t5")
    kosdaq_g = stream(EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5", 0.33,
                      "kosdaq_vwap_guard")
    # kr_selective: 원장이 아니라 최신 리포트의 rank-1 KOSPI 수치 사용 (n=21 EV gross +1.39 → net)
    sel = {"label": "kr_selective_top1_KOSPI(shadow)", "n": 21, "n_issued": 21,
           "ev_net": round(1.39 - 0.3, 2), "win": 71.4,
           "freq_yr": 250.0, "rets": np.repeat(1.39 - 0.3, 21), "span_days": 0,
           "note": "§40 shadow 실측 n=21 — 분산 미반영 점추정(낙관 상한)"}

    live = [s for s in (kosdaq_g,) if s]                      # S0: DEGRADE 제외 후 실사이징 스트림
    all_fwd = [s for s in (swing, kospi_itd, kosdaq_g) if s]  # S1
    repaired = [s for s in (swing_fix, kosdaq_g) if s]        # S2 (kospi_itd는 크래시 무관 음수라 제외)
    promoted = [s for s in (swing_fix, kosdaq_g, sel) if s]   # S3

    scen = {
        "S0_current_after_pkgA": {"streams": [s["label"] for s in live], "sizing_pct": 2.0, **annual(live, 2.0)},
        "S1_degrade_restored": {"streams": [s["label"] for s in all_fwd], "sizing_pct": 2.0, **annual(all_fwd, 2.0)},
        "S2_swing_repaired": {"streams": [s["label"] for s in repaired], "sizing_pct": 2.0, **annual(repaired, 2.0)},
        "S3_selective_promoted": {"streams": [s["label"] for s in promoted], "sizing_pct": 2.0, **annual(promoted, 2.0)},
    }
    streams_out = [{k: v for k, v in s.items() if k != "rets"} for s in (swing, swing_fix, kospi_itd, kosdaq_g, sel) if s]
    rep = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "method": "§20 재계산 — forward 원장 net(비용 차감), freq=관측 span 연환산, "
                     "annual=(1-0.2)*3.5% 안전 + Σ freq×EV×f. 부트스트랩=포아송 빈도×트레이드 재표집 1000회.",
           "caveats": ["전 스트림 소표본 — 산수이지 예측 아님", "S3 selective는 분산 미반영 점추정",
                       "kosdaq guard freq는 가드 억제로 붕괴 상태가 그대로 반영됨",
                       "빈도는 슬리브 용량(20%÷f × 245/5d)으로 캡 — 동시노출 상한 반영",
                       "swing류 다픽 발행은 용량 캡에 걸림 — '높은 승률×충분한 빈도 양립'이 병목(§20 계승)"],
           "streams": streams_out, "scenarios": scen, "target_pct_yr": 15.0}
    OUT_J.parent.mkdir(parents=True, exist_ok=True)
    OUT_J.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 정직한 연환산 기대 (forward 재계산) — {rep['generated_at'][:10]}", "",
             "| 스트림 | n | net EV | win% | freq/yr |", "|---|---:|---:|---:|---:|"]
    for s in streams_out:
        lines.append(f"| {s['label']} | {s['n']} | {s['ev_net']} | {s['win']} | {s['freq_yr']:.0f} |")
    lines += ["", "| 시나리오 | 스트림 | 연환산(안전 80% 포함) | boot p5/p50/p95 |", "|---|---|---:|---|"]
    for k, v in scen.items():
        lines.append(f"| {k} | {len(v['streams'])}개 | **{v['total_with_safe_pp']}%** | "
                     f"{v['boot_p5']} / {v['boot_p50']} / {v['boot_p95']} |")
    lines += ["", "목표 15%/yr · " + " · ".join(rep["caveats"])]
    OUT_M.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v["total_with_safe_pp"] for k, v in scen.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
