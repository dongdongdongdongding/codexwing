#!/usr/bin/env python3
"""PKG-B ④ (§40): 포트폴리오 노출 계기판 — 동시보유 × 사이징 = 현재 노출, 슬리브 자본곡선.

완전성 비판 (5): 시스템은 픽 단위 원장만 기록해 8:2(위험 20%) 예산 준수가 측정 불능이었다.
§20이 경고한 슬리브 DD를 7월 크래시가 실현했는데 아무도 동시노출을 계산하지 않았다.
이 도구는 매일 ops에서:
  1) 각 레인 원장의 미정산(open) 픽 수 × 현행 사이징(2%) = 권고-추종 시 현재 노출 %p
  2) 위험슬리브 예산 20% 대비 초과 여부 플래그
  3) 정산 픽의 일별 합산 수익 × 사이징 누적 = 슬리브 자본곡선(전 기간) + maxDD
산출: runtime_state/reports/validation/portfolio_exposure_latest.{json,md}
주의: '사용자 실제 체결'이 아니라 '권고 추종 가정' 노출 — 실현손익 대사는 KIS 계좌 API
연동(후속, PKG-B 잔여)이 담당.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "runtime_state" / "reports" / "experimental"
OUT_J = ROOT / "runtime_state" / "reports" / "validation" / "portfolio_exposure_latest.json"
OUT_M = ROOT / "runtime_state" / "reports" / "validation" / "portfolio_exposure_latest.md"

SIZING_PCT = 2.0    # PKG-A 원복 후 픽당 총자본 %
SLEEVE_PCT = 20.0   # 8:2 위험 예산
LANES = [
    ("swing_candidate", EXP / "kr_swing_candidate_ledger.jsonl", "policy_ret"),
    ("kospi_intraday_t5", EXP / "kospi_intraday_swing_ledger.jsonl", "exit_t5_h5"),
    ("kosdaq_vwap_guard", EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5"),
]
COSTS = {"swing_candidate": 0.3, "kospi_intraday_t5": 0.3, "kosdaq_vwap_guard": 0.33}


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


def main():
    lanes_out, open_total = [], 0
    settled_frames = []
    for name, fp, field in LANES:
        rows = _rows(fp)
        opened = [r for r in rows if r.get(field) is None]
        settled = [r for r in rows if isinstance(r.get(field), (int, float))]
        open_n = len(opened)
        open_total += open_n
        lanes_out.append({"lane": name, "open_picks": open_n,
                          "open_dates": sorted({str(r.get("date"))[:10] for r in opened}),
                          "exposure_pp": round(open_n * SIZING_PCT, 1)})
        if settled:
            df = pd.DataFrame([(str(r.get("date"))[:10], float(r[field]) - COSTS[name]) for r in settled],
                              columns=["date", "ret"])
            settled_frames.append(df)
    exposure_pp = round(open_total * SIZING_PCT, 1)
    over = exposure_pp > SLEEVE_PCT

    # 슬리브 자본곡선: 일별 합산 (픽당 f=2%, 단리 근사) — maxDD 포함
    curve, maxdd = [], None
    if settled_frames:
        allf = pd.concat(settled_frames).groupby("date")["ret"].sum().sort_index()
        eq = (allf * SIZING_PCT / 100.0).cumsum()          # 총자본 %p 누적
        peak = eq.cummax()
        dd = eq - peak
        maxdd = round(float(dd.min()), 2)
        curve = [{"date": d, "equity_pp": round(float(v), 2)} for d, v in eq.items()]

    rep = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "sizing_pct": SIZING_PCT, "sleeve_budget_pp": SLEEVE_PCT,
           "open_picks_total": open_total, "exposure_pp": exposure_pp,
           "sleeve_over_budget": bool(over),
           "sleeve_equity_maxdd_pp": maxdd,
           "lanes": lanes_out, "sleeve_equity_curve": curve[-60:],
           "note": "권고-추종 가정 노출. 실제 체결 대사는 KIS 계좌 API 연동 대기."}
    OUT_J.parent.mkdir(parents=True, exist_ok=True)
    OUT_J.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 포트폴리오 노출 계기판 — {rep['generated_at'][:10]}", "",
             f"- 미정산 픽 합계: **{open_total}** × {SIZING_PCT}% = 노출 **{exposure_pp}%p** "
             f"(슬리브 예산 {SLEEVE_PCT}%p — {'⚠️ 초과' if over else 'OK'})",
             f"- 슬리브 자본곡선 maxDD(전 기간, f={SIZING_PCT}%): **{maxdd}%p**", "",
             "| 레인 | open | 노출 %p | open 날짜 |", "|---|---:|---:|---|"]
    for l in lanes_out:
        dates = ", ".join(l["open_dates"][-5:]) or "-"
        lines.append(f"| {l['lane']} | {l['open_picks']} | {l['exposure_pp']} | {dates} |")
    OUT_M.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"open": open_total, "exposure_pp": exposure_pp, "over_budget": bool(over),
                      "maxdd_pp": maxdd}, ensure_ascii=False))


if __name__ == "__main__":
    main()
