#!/usr/bin/env python3
"""데이터 파이프라인 매니페스트 (2026-07-19 운영자 지시 — 수집 체계화).

모든 학습용 데이터 자산을 한 곳에 선언: 경로·갱신 주체·기대 신선도. 매일 ops에서 실행해
STALE 발견 시 bd 티켓 자동 발행(dedup) — 수급 3일 정지 사태(§ops 재배열)의 재발 방지 장치.
자동 엣지 학습 루프(게이트→부검→재개봉 큐)의 연료가 이 자산들이다.

  python3 multi_agent/tools/report_data_manifest.py [--no-tickets]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.path.expanduser("~/research_cache"))
OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "data_manifest_latest.json"
STATE = PROJECT_ROOT / "runtime_state" / "long_term" / "learning" / "data_manifest_state.json"

# (이름, 종류, 최신일 추출자, 허용 지연 [영업일 근사 = 달력일], 갱신 주체)
def _pq_max(fp, col):
    import pandas as pd
    d = pd.read_parquet(fp, columns=[col])
    return pd.to_datetime(d[col].astype(str), errors="coerce").max()


def _dir_latest_mtime(pattern):
    fs = glob.glob(str(pattern))
    if not fs:
        return None
    return datetime.fromtimestamp(max(os.path.getmtime(f) for f in fs))


def _jsonl_max_date(fp, key="date"):
    mx = None
    for ln in open(fp, encoding="utf-8"):
        if ln.strip():
            try:
                v = json.loads(ln).get(key)
                if v and (mx is None or str(v) > str(mx)):
                    mx = str(v)
            except Exception:
                pass
    import pandas as pd
    return pd.to_datetime(mx) if mx else None


MANIFEST = [
    ("px_long (일봉 피처·라벨 8y)", lambda: _pq_max(CACHE / "px_long.parquet", "date"), 4, "ops: px_long_refresh"),
    ("ohlc_daily (최근 경로)", lambda: _pq_max(CACHE / "ohlc_daily.parquet", "date"), 4, "ops: update_ohlc_daily"),
    ("ohlc_full (8y 경로)", lambda: _pq_max(CACHE / "ohlc_full.parquet", "date"), 6, "ops: bench ohlc_full_backfill"),
    ("flow (수급)", lambda: _pq_max(CACHE / "flow.parquet", "date"), 4, "ops: flow_update"),
    ("credit (신용/대주)", lambda: _pq_max(CACHE / "credit.parquet", "date"), 8, "ops: credit_update (소스 T+3)"),
    ("short (공매도)", lambda: _pq_max(CACHE / "short.parquet", "date"), 4, "ops: short_update"),
    ("dart (공시)", lambda: _pq_max(CACHE / "dart_events.parquet", "ann"), 6, "ops: dart_update"),
    ("intraday 분봉", lambda: _dir_latest_mtime(CACHE / "intraday" / "*.parquet"), 4, "ops: intraday_backfill (예산 2h)"),
    ("intraday_ext 확장세션", lambda: _dir_latest_mtime(CACHE / "intraday_ext" / "*.parquet"), 5, "ops: intraday_ext_update"),
    ("US hourly", lambda: _dir_latest_mtime(CACHE / "us_daily" / "hourly" / "*.parquet"), 5, "ops: update_us_hourly"),
    ("scan archive 학습셋", lambda: _dir_latest_mtime(PROJECT_ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"), 4, "ops: export_scan_archive (phase25 수집 유지분)"),
    ("스윙 원장", lambda: _jsonl_max_date(PROJECT_ROOT / "runtime_state/reports/experimental/kr_swing_candidate_ledger.jsonl"), 4, "레인 자동"),
    ("코스피 장중 원장", lambda: _jsonl_max_date(PROJECT_ROOT / "runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl"), 4, "레인 자동"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tickets", action="store_true")
    args = ap.parse_args()
    now = datetime.now()
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        state = {}
    rows, stale = [], []
    for name, getter, max_lag, owner in MANIFEST:
        try:
            latest = getter()
            lag = (now - latest.to_pydatetime() if hasattr(latest, "to_pydatetime") else now - latest).days if latest is not None else None
            ok = latest is not None and lag <= max_lag
            rows.append({"asset": name, "latest": str(latest)[:16] if latest is not None else None,
                         "lag_days": lag, "max_lag": max_lag, "owner": owner, "status": "OK" if ok else "STALE"})
            if not ok:
                stale.append(name)
        except Exception as exc:
            rows.append({"asset": name, "error": repr(exc)[:80], "owner": owner, "status": "ERROR"})
            stale.append(name)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "assets": rows,
              "ok": len(rows) - len(stale), "stale": stale}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # STALE 티켓 (자산별 1회, 해소 시 상태 리셋)
    for name in list(state.keys()):
        if name not in stale:
            state.pop(name, None)
    if not args.no_tickets:
        for name in stale:
            if state.get(name):
                continue
            row = next(r for r in rows if r["asset"] == name)
            try:
                r = subprocess.run([os.environ.get("BD_BIN", "/Users/dongdong/.local/bin/bd"), "create",
                                    f"--title=[데이터정체] {name} — {row.get('lag_days','?')}일 지연",
                                    f"--description=Why: 데이터 매니페스트 자동 감지 — {name} 최신 {row.get('latest')} (허용 {row.get('max_lag')}일). 갱신 주체: {row.get('owner')}. What: 갱신 경로 점검·복구. (report_data_manifest 자동 발행)",
                                    "--type=bug", "--priority=1"], capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    state[name] = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    print(json.dumps({"ok": report["ok"], "stale": stale}, ensure_ascii=False))


if __name__ == "__main__":
    main()
