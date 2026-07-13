#!/usr/bin/env python3
"""Recursive research gate (모델 연구 재귀 루프의 심판자).

Every lane already auto-scores its forward outcomes into a ledger. This tool closes the
loop: per lane it compares matured forward results against the lane's frozen backtest
expectation and issues a verdict —
  OBSERVING  n < n_min (표본 미성숙)
  CONFIRM    forward CI가 백테스트 기대의 절반 이상을 지지 (계속 + 표본 확대)
  DEGRADE    forward CI 상단 < 기대EV의 50% (사이징 축소 권고 + 재연구 beads 티켓 자동 발행)
  EXCEED     forward 평균 > 기대EV*1.5 (승격/확대 검토 티켓)
Ticket dedup via state file — one ticket per lane per verdict-change. Runs in daily ops.

  python3 multi_agent/tools/report_research_recursion_gate.py [--no-tickets]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
USR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
OUT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.json"
OUT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "research_recursion_gate_latest.md"
STATE = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "recursion_gate_state.json"

# 레인별: 원장, 실현수익 필드, 동결된 백테스트 기대(연구 로그 근거), 성숙 표본 수
LANES: Dict[str, Dict[str, Any]] = {
    "kospi_intraday_t5": {
        "ledger": EXP / "kospi_intraday_swing_ledger.jsonl", "field": "exit_t5_h5",
        "expect_ev": 5.65, "expect_win": 92.0, "n_min": 20,
        "basis": "§28 q0.5 승격 (2026-07-13) — 8 OOS월 rank-1 선별 q0.5 티어+터치익절"},
    "kosdaq_intraday_t10": {
        "ledger": EXP / "kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "field": "exit_t10_h5",
        "expect_ev": 3.14, "expect_win": 75.8, "n_min": 20,
        "basis": "§11-A 15:00 실파이프라인 재검증"},
    "swing_candidate": {
        "ledger": EXP / "kr_swing_candidate_ledger.jsonl", "field": "policy_ret",
        "expect_ev": 0.65, "expect_win": 62.0, "n_min": 30,
        "basis": "§7-A 8년 분기 walk-forward (플라시보 사망)"},
    "swing_ensemble": {
        "ledger": EXP / "swing_ensemble_ledger.jsonl", "field": "first_touch_ret",
        "expect_ev": 0.65, "expect_win": 60.0, "n_min": 30,
        "basis": "일봉 횡단면 8년 천장(§8) — 이 이하면 교체 검토(스윙 후보로)"},
    "b_primary_top3": {
        "ledger": PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", "field": "alpha",
        "filter": {"status": "settled", "tier": "PRIMARY"},
        "expect_ev": 2.18, "expect_win": 55.0, "n_min": 30,
        "basis": "§11-B 24폴드 (top3 집중, α/트레이드)"},
    "b_all_top10": {
        # 2026-07-10: 전체 스트림 감시 추가 — PRIMARY 정산 대기 중 top10 전체가 α −5.1로 붕괴한
        # 사각지대 발견(운영자 질의). tier 스탬프 이전 정산분 포함 전체를 게이트가 공식 판정.
        "ledger": PROJECT_ROOT / "b_engine" / "data" / "b_shadow.jsonl", "field": "alpha",
        "filter": {"status": "settled"},
        "expect_ev": 1.20, "expect_win": 55.0, "n_min": 30,
        "basis": "§11-B 24폴드 (top10 전체, α/트레이드)"},
    "nasdaq_session_tape": {
        "ledger": USR / "nasdaq_session_tape_ledger.jsonl", "field": "policy_ret",
        "expect_ev": 0.75, "expect_win": 79.3, "n_min": 30,
        "basis": "§12-D 29개월 (정직 추정 +0.5~1.0 — 기대는 중간값 0.75)"},
}


def _rows(fp: Path) -> List[Dict[str, Any]]:
    if not fp.exists():
        return []
    out = []
    for l in fp.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def _load_state() -> Dict[str, str]:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _bd_create(title: str, desc: str) -> bool:
    try:
        r = subprocess.run(["bd", "create", f"--title={title}", f"--description={desc}",
                            "--type=task", "--priority=1"], capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def evaluate(name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    rows = _rows(cfg["ledger"])
    flt = cfg.get("filter") or {}
    rows = [r for r in rows if all(r.get(k) == v for k, v in flt.items())]
    vals = [float(r[cfg["field"]]) for r in rows if isinstance(r.get(cfg["field"]), (int, float))]
    res: Dict[str, Any] = {"lane": name, "basis": cfg["basis"], "n": len(vals),
                           "expect_ev": cfg["expect_ev"], "expect_win": cfg["expect_win"], "n_min": cfg["n_min"]}
    if len(vals) < 5:
        res.update(verdict="OBSERVING", note=f"n={len(vals)} (표본 축적 중)")
        return res
    arr = np.array(vals)
    bs = [np.random.default_rng(s).choice(arr, len(arr), True).mean() for s in range(400)]
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    res.update(fwd_ev=round(float(arr.mean()), 2), fwd_win=round(float((arr > 0.3).mean()) * 100, 1),
               fwd_ci=[round(lo, 2), round(hi, 2)], worst=round(float(arr.min()), 2))
    if len(vals) < cfg["n_min"]:
        res.update(verdict="OBSERVING", note=f"n={len(vals)}<{cfg['n_min']} — 참고치만")
        return res
    if hi < cfg["expect_ev"] * 0.5 or arr.mean() <= 0:
        why = "forward 평균 <= 0" if arr.mean() <= 0 else "forward CI 상단 < 기대EV 50%"
        res.update(verdict="DEGRADE", note=f"{why} — 사이징 축소 + 재연구")
    elif arr.mean() > cfg["expect_ev"] * 1.5:
        res.update(verdict="EXCEED", note="기대 초과 — 승격/확대 검토")
    else:
        res.update(verdict="CONFIRM", note="백테스트 기대와 정합")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tickets", action="store_true")
    args = ap.parse_args()
    state = _load_state()
    results = [evaluate(name, cfg) for name, cfg in LANES.items()]
    tickets = []
    for r in results:
        if r["verdict"] in ("DEGRADE", "EXCEED") and state.get(r["lane"]) != r["verdict"] and not args.no_tickets:
            title = f"[재귀게이트:{r['verdict']}] {r['lane']} forward {r.get('fwd_ev')} vs 기대 {r['expect_ev']}"
            desc = (f"Why: 재귀 연구 게이트 자동 발행 — {r['lane']} forward n={r['n']} EV {r.get('fwd_ev')} "
                    f"CI {r.get('fwd_ci')} vs 백테스트 기대 {r['expect_ev']} ({r['basis']}). "
                    f"What: {'열화 원인 진단(레짐/드리프트/계약) 후 재연구 or 레인 축소' if r['verdict']=='DEGRADE' else '승격/사이징 확대 검토 + 과최적화 점검'}. "
                    f"판정 근거: {r['note']}")
            if _bd_create(title, desc):
                tickets.append(title)
        state[r["lane"]] = r["verdict"]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "results": results, "tickets_created": tickets}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Research recursion gate — {report['generated_at'][:10]}", "",
             "| Lane | verdict | fwd n | fwd EV | CI | 기대EV | note |", "|---|---|---:|---:|---|---:|---|"]
    for r in results:
        lines.append(f"| {r['lane']} | **{r['verdict']}** | {r['n']} | {r.get('fwd_ev','–')} | "
                     f"{r.get('fwd_ci','–')} | {r['expect_ev']} | {r['note']} |")
    if tickets:
        lines += ["", "## Auto tickets", *[f"- {t}" for t in tickets]]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({r["lane"]: r["verdict"] for r in results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
