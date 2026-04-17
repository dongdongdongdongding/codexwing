#!/usr/bin/env python3
"""
verify_pipeline_e2e.py
────────────────────────────────────────────────────────────
End-to-end 파이프라인 검증 도구.

Scanner → Aggregation → MarketNews → Orchestrator 전체 흐름이
실제로 완주하는지, 각 핸드오프 파일이 정상 생성되는지 검증한다.

사용:
  python multi_agent/tools/verify_pipeline_e2e.py
  python multi_agent/tools/verify_pipeline_e2e.py --market KOSPI
  python multi_agent/tools/verify_pipeline_e2e.py --scanner-input path/to/scan.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HANDOFF_FILES = [
    "scanner_handoff.json",
    "market_context_handoff.json",
    "aggregation_handoff.json",
    "orchestrator_report.json",
    "orchestrator_compact_summary.json",
]

OPTIONAL_FILES = [
    "backtest_handoff.json",
    "planner_handoff.json",
    "postmortem_report.json",
]


def _find_latest_bridge_input() -> str | None:
    """가장 최신 bridge legacy_scan_results.json 경로 반환."""
    bridge_dir = ROOT / "runtime_state" / "local_short_term" / "orchestrator_bridge"
    if not bridge_dir.exists():
        return None
    candidates = sorted(
        bridge_dir.iterdir(),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for b in candidates:
        f = b / "legacy_scan_results.json"
        if f.exists():
            return str(f)
    return None


def _check_handoff(path: Path) -> dict:
    if not path.exists():
        return {"status": "MISSING", "size_bytes": 0, "keys": []}
    try:
        size = path.stat().st_size
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = list(data.keys()) if isinstance(data, dict) else ["<list>"]
        # 경고 신호: candidates / results가 비어있는지
        candidates = data.get("candidates", data.get("results", data.get("rows", None)))
        empty_warn = (
            isinstance(candidates, list) and len(candidates) == 0
        )
        return {
            "status": "EMPTY_CANDIDATES" if empty_warn else "OK",
            "size_bytes": size,
            "keys": keys[:8],
            "n_candidates": len(candidates) if isinstance(candidates, list) else None,
        }
    except Exception as exc:
        return {"status": f"ERROR: {exc}", "size_bytes": 0, "keys": []}


def run_verification(market: str = "KR", scanner_input: str | None = None) -> dict:
    print(f"\n{'=' * 60}")
    print(f"  End-to-End Pipeline Verification")
    print(f"  Market: {market}  |  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'=' * 60}")

    # scanner input 자동 탐색
    if scanner_input is None:
        scanner_input = _find_latest_bridge_input()
        if scanner_input:
            print(f"  Auto-selected scanner input: {scanner_input}")
        else:
            print("  WARNING: No scanner input found. Pipeline will use placeholder.")

    print("\n[1/3] 파이프라인 실행 중...")
    t0 = time.time()
    run_id = ""
    pipeline_error = None

    try:
        from multi_agent.workflows.scaffold_run import run_scaffold_pipeline
        run_id = run_scaffold_pipeline(
            market=market,
            scanner_input_path=scanner_input,
        )
        elapsed = round(time.time() - t0, 2)
        print(f"  완료: run_id={run_id}  ({elapsed}s)")
    except Exception as exc:
        pipeline_error = str(exc)
        elapsed = round(time.time() - t0, 2)
        print(f"  FAILED ({elapsed}s): {exc}")

    # run_dir 탐색
    run_dir = ROOT / "runtime_state" / "shared_working" / str(run_id)
    if not run_dir.exists() and not run_id:
        # 가장 최신 run_dir 폴백
        sw = ROOT / "runtime_state" / "shared_working"
        if sw.exists():
            dirs = sorted(sw.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            if dirs:
                run_dir = dirs[0]
                run_id = run_dir.name

    print(f"\n[2/3] 핸드오프 파일 검증: {run_dir}")
    print(f"{'─' * 60}")

    results = {}
    all_ok = True

    for fname in HANDOFF_FILES:
        check = _check_handoff(run_dir / fname)
        status = check["status"]
        icon = "✅" if status == "OK" else ("⚠️" if status == "EMPTY_CANDIDATES" else "❌")
        n = f"  n={check['n_candidates']}" if check["n_candidates"] is not None else ""
        print(f"  {icon} {fname:<45} {status}{n}")
        results[fname] = check
        if status not in ("OK", "EMPTY_CANDIDATES"):
            all_ok = False

    print(f"\n  [Optional]")
    for fname in OPTIONAL_FILES:
        check = _check_handoff(run_dir / fname)
        icon = "✅" if check["status"] == "OK" else "⬜"
        print(f"  {icon} {fname:<45} {check['status']}")
        results[fname] = check

    # Orchestrator report 상세
    report_path = run_dir / "orchestrator_report.json"
    agent_summary = []
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            assignments = report.get("assignments", [])
            print(f"\n[3/3] Agent 실행 결과:")
            print(f"{'─' * 60}")
            for a in assignments:
                st = a.get("status", "unknown")
                icon = "✅" if st == "completed" else "❌"
                name = a.get("agent_name", "?")
                out = Path(a.get("output_ref", "")).name if a.get("output_ref") else "-"
                notes = "; ".join(a.get("notes", []))[:60] if a.get("notes") else ""
                print(f"  {icon} {name:<35} {st}  → {out}")
                if notes:
                    print(f"       ↳ {notes}")
                agent_summary.append({"agent": name, "status": st})
        except Exception as exc:
            print(f"  리포트 파싱 실패: {exc}")

    # 최종 판정
    print(f"\n{'=' * 60}")
    pipeline_ok = pipeline_error is None and all_ok
    verdict = "PASS ✅" if pipeline_ok else ("PARTIAL ⚠️" if not pipeline_error else "FAIL ❌")
    print(f"  최종 판정: {verdict}")
    if pipeline_error:
        print(f"  파이프라인 에러: {pipeline_error}")
    print(f"  run_id: {run_id}")
    print(f"{'=' * 60}\n")

    # 검증 결과 저장
    output = {
        "verified_at": datetime.now().isoformat(),
        "market": market,
        "run_id": run_id,
        "pipeline_error": pipeline_error,
        "verdict": verdict.split()[0],  # PASS / PARTIAL / FAIL
        "handoffs": results,
        "agents": agent_summary,
    }
    out_path = ROOT / "runtime_state" / "reports" / "validation" / "e2e_pipeline_verification.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  결과 저장: {out_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end pipeline verification")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--scanner-input", default=None)
    args = parser.parse_args()
    result = run_verification(market=args.market, scanner_input=args.scanner_input)
    sys.exit(0 if result["verdict"] in ("PASS", "PARTIAL") else 1)
