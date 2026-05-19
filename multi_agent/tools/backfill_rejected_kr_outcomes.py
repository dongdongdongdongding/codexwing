#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.missed_winner_postmortem import build_reject_rows_from_diagnostics
from modules.rejected_outcome_backfill import (
    DEFAULT_REJECT_OUTCOME_CSV,
    backfill_reject_outcomes,
    dedupe_reject_rows,
    load_existing_reject_outcomes,
    write_reject_outcomes,
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_diagnostics(artifact_dir: Path, limit_runs: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not artifact_dir.exists():
        return rows
    run_dirs = sorted(
        [path for path in artifact_dir.iterdir() if path.is_dir() and path.name.startswith("RUN-")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[: max(1, int(limit_runs or 300))]
    for run_dir in run_dirs:
        raw = _load_json(run_dir / "raw_scan_results.json")
        summary = _load_json(run_dir / "scan_pipeline_summary.json")
        if not isinstance(raw, dict):
            continue
        ctx = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
        diagnostics = raw.get("diagnostics") if isinstance(raw.get("diagnostics"), dict) else {}
        if diagnostics:
            rows.append(
                {
                    "run_id": str(ctx.get("run_id") or summary.get("run_id") or run_dir.name),
                    "market": str(ctx.get("market") or summary.get("market") or ""),
                    "base_trade_date": str(ctx.get("as_of_date") or ctx.get("created_at") or summary.get("created_at") or "")[:10],
                    **diagnostics,
                }
            )
    return rows


class YFinanceProvider:
    def __init__(self) -> None:
        import yfinance as yf

        self.yf = yf
        self.cache: Dict[tuple[str, str, str], List[Dict[str, Any]]] = {}

    def __call__(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        key = (ticker, start, end)
        if key in self.cache:
            return self.cache[key]
        try:
            hist = self.yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
        except Exception:
            self.cache[key] = []
            return []
        rows: List[Dict[str, Any]] = []
        if hist is not None and len(hist) > 0:
            for idx, item in hist.iterrows():
                rows.append(
                    {
                        "date": str(getattr(idx, "date", lambda: idx)()),
                        "close": item.get("Close"),
                        "high": item.get("High"),
                    }
                )
        self.cache[key] = rows
        return rows


def _merge_rows(existing: List[Dict[str, Any]], new_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = {
        (str(row.get("run_id") or ""), str(row.get("ticker") or ""), str(row.get("base_trade_date") or "")): row
        for row in existing
    }
    for row in new_rows:
        key = (str(row.get("run_id") or ""), str(row.get("ticker") or ""), str(row.get("base_trade_date") or ""))
        merged[key] = row
    return list(merged.values())


def _is_matured(row: Dict[str, Any], *, min_age_days: int = 7) -> bool:
    try:
        base = datetime.strptime(str(row.get("base_trade_date") or "")[:10], "%Y-%m-%d")
    except Exception:
        return False
    return base.date() <= (datetime.now() - timedelta(days=int(min_age_days))).date()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill KR rejected-symbol forward outcomes for full-universe miss analysis.")
    parser.add_argument("--artifact-dir", default="runtime_state/artifacts")
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--max-rows", type=int, default=0, help="0 means all deduped eligible rows.")
    parser.add_argument("--output", default=str(DEFAULT_REJECT_OUTCOME_CSV))
    parser.add_argument("--include-immature", action="store_true", help="Include rows whose 5D outcome is not mature yet.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    diagnostics = _load_diagnostics(Path(args.artifact_dir), int(args.limit_runs))
    reject_rows = dedupe_reject_rows(build_reject_rows_from_diagnostics(diagnostics))
    existing = load_existing_reject_outcomes(Path(args.output))
    existing_keys = {
        (str(row.get("run_id") or ""), str(row.get("ticker") or ""), str(row.get("base_trade_date") or ""))
        for row in existing
        if str(row.get("outcome_available") or "").lower() in {"1", "true", "yes"}
    }
    pending = [
        row
        for row in reject_rows
        if (str(row.get("run_id") or ""), str(row.get("ticker") or ""), str(row.get("base_trade_date") or "")) not in existing_keys
    ]
    immature_count = sum(1 for row in pending if not _is_matured(row))
    if not args.include_immature:
        pending = [row for row in pending if _is_matured(row)]
    if args.max_rows and int(args.max_rows) > 0:
        pending = pending[: int(args.max_rows)]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "eligible_reject_rows": len(reject_rows),
                    "existing_rows": len(existing),
                    "pending_rows": len(pending),
                    "immature_pending_rows": immature_count,
                    "sample": pending[:5],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    provider = YFinanceProvider()
    new_rows = backfill_reject_outcomes(pending, price_provider=provider, existing_rows=existing)
    merged = _merge_rows(existing, new_rows)
    payload = write_reject_outcomes(merged, Path(args.output))
    payload["new_rows_attempted"] = len(new_rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
