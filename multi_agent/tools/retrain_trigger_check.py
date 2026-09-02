#!/usr/bin/env python3
"""Check if accumulated realized outcomes warrant a phase25 retrain.

Intended to run daily via cron/scheduler. Compares the latest realized-outcome
count to the count at last retrain (persisted in retrain_v2_report.json's
trained_at timestamps). If the delta exceeds RETRAIN_MIN_NEW_OUTCOMES, the
script invokes retrain_ml.py.

Exit codes:
  0 — no retrain needed, retrain succeeded, or retrain safely deferred
  1 — retrain command crashed
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "runtime_state/reports/learning/retrain_v2_report.json"
OUTCOMES_PATH = PROJECT_ROOT / "runtime_state/long_term/outcomes/realized_outcomes_updates.jsonl"
STATE_PATH = PROJECT_ROOT / "runtime_state/long_term/learning/retrain_trigger_state.json"


def _last_retrain_ts() -> datetime | None:
    if not REPORT_PATH.exists():
        return None
    try:
        r = json.loads(REPORT_PATH.read_text())
        # generated_at can represent a no-dummy deferred run. Use the latest
        # actual model train timestamp so sample-shortage executions do not
        # suppress future retrain attempts.
        ts = r.get("last_successful_model_train_at")
        if not ts:
            trained_segments = [row for row in r.get("segments", []) if row.get("status") == "trained"]
            ts = max((row.get("trained_at") or r.get("generated_at") for row in trained_segments), default=None)
        if not ts:
            return None
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _count_outcomes_since(cutoff: datetime | None) -> int:
    if not OUTCOMES_PATH.exists():
        return 0
    count = 0
    with OUTCOMES_PATH.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except Exception:
                continue
            # 🔴 2026-09-02: 여기서 `recorded_at`/`outcome_recorded_at`/`created_at` 만 봤는데
            #    실제 행에는 **셋 다 0건**이고 `updated_at` 이 3,430건이다. 모든 행이 건너뛰어져
            #    카운트가 **영원히 0** 이었다 — 모델이 2026-07-03 이후 재학습된 적이 없고,
            #    고치지 않으면 성과가 아무리 쌓여도 영영 안 된다. 센티넬은 산출물 신선도로만
            #    잡아서 「재학습 불필요」라는 정상 응답과 구분되지 않았다.
            ts_raw = (row.get("updated_at") or row.get("recorded_at")
                      or row.get("outcome_recorded_at") or row.get("created_at"))
            if not ts_raw:
                continue
            try:
                row_ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            except Exception:
                continue
            if row_ts.tzinfo is None:
                row_ts = row_ts.replace(tzinfo=timezone.utc)
            if cutoff is None or row_ts > cutoff:
                # 한 행 = 한 성과가 아니라 **한 실행의 요약**이다
                # (`run_id`·`resolved_count`·`expired_count`·`checked_pending`).
                # 행을 세면 실행 횟수를 세게 된다 — 문턱 300 은 성과 수를 뜻하므로
                # 그 실행이 실제로 정산한 건수를 더한다. 실측: 실행 2,080건 = 성과 4,684건.
                count += int(row.get("resolved_count") or 0) if "resolved_count" in row else 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-new", type=int, default=300, help="Trigger retrain when this many new outcomes accumulated")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    last_ts = _last_retrain_ts()
    new_count = _count_outcomes_since(last_ts)
    print(f"last_retrain={last_ts}, new_outcomes={new_count}, threshold={args.min_new}")

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "last_retrain": last_ts.isoformat() if last_ts else None,
        "new_outcomes": new_count,
        "threshold": args.min_new,
        "triggered": new_count >= args.min_new,
    }, indent=2))

    if new_count < args.min_new:
        print("No retrain needed.")
        return 0

    if args.dry_run:
        print(f"DRY RUN — would trigger retrain (new_outcomes={new_count} >= {args.min_new})")
        return 0

    print(f"Triggering retrain — new_outcomes={new_count}")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "retrain_ml.py")],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0 and REPORT_PATH.exists():
        try:
            report = json.loads(REPORT_PATH.read_text())
            if report.get("execution_status") == "deferred_not_failed":
                print("Retrain safely deferred: no dummy model trained; existing models preserved.")
        except Exception:
            pass
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
