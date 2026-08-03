#!/usr/bin/env python3
"""PKG-C ① (§40): 정산 원장 픽에 공시 이력 소급 라벨 → 실측 차등 측정.

킬 대조 판정: '발행 전 악재 게이트'는 원장에서 한 번도 측정된 적 없고, §40 무악재 역효과
(무악재군이 오히려 열위)가 "악재=회피" 직관에 반례를 냈다 — 게이트/필터를 만들기 전에
우리 픽 분포에서 실제 차등이 있는지부터 잰다 (연구 규율: 문헌이 있어도 우리 원장에서 실측).

라벨 (dart_events.parquet, 2023-10+ 커버):
  neg_60d   : 픽 직전 60일(달력) 내 악재(edir '-') 공시 존재
  cap_180d  : 픽 직전 180일 내 유상증자/CB/BW 공시 존재 (자본조달 이력 — 문헌상 장기 저성과)
  any_5d    : 픽 직전 5일 내 아무 공시 (이벤트 활성 종목)
경보(투자경고) 이력은 로컬 데이터 부재 — 데이터 갭으로 기록(KIND 수집 트랙 대상).
판정 기준: 라벨군 vs 비라벨군 net EV 차 + 부트스트랩. n이 작으므로 §19 하한(+0.3%p 미만
증분 주장 불가) 적용 — 차등이 그 미만이면 게이트/필터 후보 종결.
산출: runtime_state/reports/validation/ledger_retro_labels_latest.{json,md}
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "runtime_state" / "reports" / "experimental"
OUT_J = ROOT / "runtime_state" / "reports" / "validation" / "ledger_retro_labels_latest.json"
OUT_M = ROOT / "runtime_state" / "reports" / "validation" / "ledger_retro_labels_latest.md"

LANES = [
    ("swing_candidate", EXP / "kr_swing_candidate_ledger.jsonl", "policy_ret", 0.3),
    ("kospi_intraday_t5", EXP / "kospi_intraday_swing_ledger.jsonl", "exit_t5_h5", 0.3),
]
CAP_TYPES = {"유상증자", "전환사채", "BW"}


def _rows(fp):
    out = []
    for l in Path(fp).read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def main():
    ev = pd.read_parquet(os.path.expanduser("~/research_cache/dart_events.parquet"))
    ev["ann"] = pd.to_datetime(ev["ann"], format="%Y%m%d")
    ev["code"] = ev["code"].astype(str).str.zfill(6)
    by_code = dict(tuple(ev.groupby("code")))

    out = {}
    for lane, fp, field, cost in LANES:
        recs = []
        for r in _rows(fp):
            v = r.get(field)
            if not isinstance(v, (int, float)):
                continue
            code = str(r.get("ticker", "")).split(".")[0].zfill(6)
            d = pd.Timestamp(str(r["date"])[:10])
            e = by_code.get(code)
            neg60 = cap180 = any5 = False
            if e is not None:
                prior = e[e["ann"] < d]
                neg60 = bool(((d - prior["ann"]).dt.days.le(60) & (prior["edir"] == "-")).any())
                cap180 = bool(((d - prior["ann"]).dt.days.le(180) & prior["etype"].isin(CAP_TYPES)).any())
                any5 = bool((d - prior["ann"]).dt.days.le(5).any())
            recs.append({"ret": float(v) - cost, "neg_60d": neg60, "cap_180d": cap180, "any_5d": any5})
        df = pd.DataFrame(recs)
        lane_out = {"n": len(df), "ev_all": round(float(df["ret"].mean()), 2)}
        rng = np.random.default_rng(0)
        for lab in ("neg_60d", "cap_180d", "any_5d"):
            a, b = df[df[lab]]["ret"].to_numpy(), df[~df[lab]]["ret"].to_numpy()
            if len(a) < 5 or len(b) < 5:
                lane_out[lab] = {"n_label": int(len(a)), "verdict": "표본 부족 (n<5)"}
                continue
            diff = float(a.mean() - b.mean())
            bs = [rng.choice(a, len(a), True).mean() - rng.choice(b, len(b), True).mean() for _ in range(500)]
            lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
            verdict = ("차등 없음(CI 0 포함)" if lo <= 0 <= hi else
                       ("라벨군 열위 — 게이트 후보" if diff < -0.3 else
                        ("라벨군 우위(!) — 회피 역방향" if diff > 0.3 else "차등 §19 하한 미만 — 종결")))
            lane_out[lab] = {"n_label": int(len(a)), "ev_label": round(float(a.mean()), 2),
                             "ev_rest": round(float(b.mean()), 2), "diff": round(diff, 2),
                             "diff_ci": [round(lo, 2), round(hi, 2)], "verdict": verdict}
        out[lane] = lane_out

    rep = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "method": "정산 픽 net 수익 vs 공시 이력 라벨 (dart_events 2023-10+). 부트스트랩 500. "
                     "§19 하한: |diff|<0.3%p면 주장 불가. 경보(KIND) 이력은 데이터 갭 — 미측정.",
           "results": out}
    OUT_J.parent.mkdir(parents=True, exist_ok=True)
    OUT_J.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 원장 소급 공시 라벨 측정 — {rep['generated_at'][:10]}", "", rep["method"], ""]
    for lane, lo in out.items():
        lines += [f"## {lane} (n={lo['n']}, EV {lo['ev_all']})",
                  "| 라벨 | n | EV(라벨) | EV(나머지) | Δ | CI | 판정 |", "|---|---:|---:|---:|---:|---|---|"]
        for lab in ("neg_60d", "cap_180d", "any_5d"):
            v = lo.get(lab, {})
            if "diff" in v:
                lines.append(f"| {lab} | {v['n_label']} | {v['ev_label']} | {v['ev_rest']} | {v['diff']} | "
                             f"{v['diff_ci']} | {v['verdict']} |")
            else:
                lines.append(f"| {lab} | {v.get('n_label','-')} | - | - | - | - | {v.get('verdict','')} |")
        lines.append("")
    OUT_M.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(rep["results"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
