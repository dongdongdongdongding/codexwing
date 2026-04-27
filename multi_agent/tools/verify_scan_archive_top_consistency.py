#!/usr/bin/env python3
"""Verify scan-time top-N picks match the archive (DB) top-N for each run.

Why this exists
---------------
The system stores picks twice: (1) planner_handoff.json on disk at scan time,
which is what the user sees in UI, and (2) market_scan_results in Supabase,
which is what training and evaluation read. If these two diverge — different
tickers at the same priority_rank, or missing rows on either side — the model
is trained on a different population than the trader sees, and any reported
win-rate / return is from a parallel universe.

Checks per run
--------------
1. Count parity: len(planner.decisions) == DB row count for that run_id.
2. Top-N membership: every ticker in planner top-N appears in DB top-N.
3. Rank exactness: planner.priority_rank == DB.priority_rank for matching ticker.
4. Feature origin: report what fraction of DB rows are scanner-full vs outcome
   sync stub — divergence here is the swing-main-emp pattern.

Output
------
Prints summary per run + aggregate. Exit 0 if all runs pass top-N parity,
exit 1 if any run shows mismatch.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


def _load_planner(run_dir: Path) -> Optional[Dict[str, Any]]:
    p = run_dir / "planner_handoff.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _planner_top(payload: Dict[str, Any], n: int, bucket: Optional[str] = "picked") -> List[Tuple[int, str]]:
    """Return [(rank, ticker)] for the requested decision bucket only.

    Bucket namespaces are distinct in archive: picked rank=1 and
    exception_leader rank=1 coexist legitimately. Earlier verify code mixed
    them and produced false-positive 'rank mismatch' alarms.
    """
    decisions = payload.get("decisions", []) or []
    if bucket:
        decisions = [
            d for d in decisions
            if str(d.get("decision_bucket") or "").lower() == bucket
            or (bucket == "picked" and str(d.get("decision") or "").upper() in ("PICK", "BUY", "STRONG_BUY"))
        ]
    items = [
        (int(d.get("priority_rank")), str(d.get("ticker")))
        for d in decisions
        if d.get("priority_rank") is not None and d.get("ticker")
    ]
    items.sort(key=lambda x: x[0])
    return items[:n]


def _db_rows_for_run(db: DBManager, run_id: str, bucket: Optional[str] = "picked") -> List[Dict[str, Any]]:
    q = (
        db.client.table("market_scan_results")
        .select("ticker,priority_rank,alpha_score,decision,decision_bucket,feature_origin")
        .eq("run_id", run_id)
    )
    if bucket:
        q = q.eq("decision_bucket", bucket)
    res = q.order("priority_rank", desc=False).execute()
    return res.data or []


def _verify_run(db: DBManager, run_dir: Path, n: int, bucket: Optional[str] = "picked") -> Dict[str, Any]:
    payload = _load_planner(run_dir)
    if not payload:
        return {"run_dir": str(run_dir), "status": "no_planner_handoff"}
    ctx = payload.get("run_context", {}) or {}
    run_id = ctx.get("run_id") or run_dir.name
    market = ctx.get("market")
    scan_mode = ctx.get("scan_mode")
    planner_top = _planner_top(payload, n, bucket=bucket)
    if not planner_top:
        return {"run_dir": str(run_dir), "run_id": run_id, "status": "empty_planner_for_bucket"}

    db_rows = _db_rows_for_run(db, run_id, bucket=bucket)
    if not db_rows:
        return {
            "run_dir": str(run_dir),
            "run_id": run_id,
            "market": market,
            "scan_mode": scan_mode,
            "status": "no_db_rows",
            "planner_count": len(planner_top),
        }

    db_top = [(int(r.get("priority_rank") or 0), str(r.get("ticker") or "")) for r in db_rows[:n] if r.get("priority_rank")]
    db_top_by_rank = {rank: tk for rank, tk in db_top}
    planner_top_by_rank = {rank: tk for rank, tk in planner_top}

    ranks_match = []
    rank_mismatches = []
    planner_only = []
    db_only = []
    for rank, planner_tk in planner_top_by_rank.items():
        db_tk = db_top_by_rank.get(rank)
        if db_tk is None:
            planner_only.append((rank, planner_tk))
        elif db_tk == planner_tk:
            ranks_match.append((rank, planner_tk))
        else:
            rank_mismatches.append({"rank": rank, "planner": planner_tk, "db": db_tk})
    for rank, db_tk in db_top_by_rank.items():
        if rank not in planner_top_by_rank:
            db_only.append((rank, db_tk))

    origins = Counter(r.get("feature_origin") for r in db_rows)
    return {
        "run_dir": str(run_dir),
        "run_id": run_id,
        "market": market,
        "scan_mode": scan_mode,
        "status": "checked",
        "planner_count": len(payload.get("decisions", []) or []),
        "db_count": len(db_rows),
        "topN": n,
        "ranks_match": len(ranks_match),
        "rank_mismatches": rank_mismatches,
        "planner_only": planner_only,
        "db_only": db_only,
        "feature_origin_dist": dict(origins),
        "scanner_full_pct": round(
            (origins.get("scanner_full", 0) / max(len(db_rows), 1)) * 100, 1
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--limit-runs", type=int, default=50)
    parser.add_argument("--bucket", default="picked", help="decision_bucket to compare (default: picked). 'all' to mix.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    shared = Path(args.shared_dir)
    if not shared.exists():
        print(f"shared dir not found: {shared}", file=sys.stderr)
        return 2

    run_dirs = sorted(
        [d for d in shared.iterdir() if d.is_dir() and d.name.startswith("RUN-")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[: args.limit_runs]

    db = DBManager()
    if not db.client:
        print("Supabase client unavailable.", file=sys.stderr)
        return 2

    bucket = None if args.bucket == "all" else args.bucket
    results = []
    for d in run_dirs:
        try:
            r = _verify_run(db, d, args.top_n, bucket=bucket)
        except Exception as exc:
            r = {"run_dir": str(d), "status": "error", "error": str(exc)}
        results.append(r)
        if args.verbose:
            print(json.dumps(r, ensure_ascii=False, indent=2))

    summary = Counter(r["status"] for r in results)
    checked = [r for r in results if r["status"] == "checked"]
    perfect = [r for r in checked if not r["rank_mismatches"] and not r["planner_only"] and not r["db_only"]]
    rank_mismatch_runs = [r for r in checked if r["rank_mismatches"]]
    missing_db_rows = [r for r in checked if r["planner_only"]]
    extra_db_rows = [r for r in checked if r["db_only"]]
    no_scanner_full = [
        r for r in checked
        if "scanner_full" not in (r.get("feature_origin_dist") or {})
    ]

    print("\n=== Scan ↔ archive top-N consistency ===")
    print(f"Runs scanned   : {len(results)}")
    print(f"Status counts  : {dict(summary)}")
    print(f"Checked        : {len(checked)}")
    print(f"  perfect      : {len(perfect)}")
    print(f"  rank mismatch: {len(rank_mismatch_runs)}")
    print(f"  planner-only : {len(missing_db_rows)} (rows in planner_handoff but not in DB)")
    print(f"  db-only      : {len(extra_db_rows)} (rows in DB but not in planner top-N)")
    print(f"  no scanner_full origin: {len(no_scanner_full)} (only stubs in DB)")

    for r in rank_mismatch_runs[:5]:
        print(f"\n[MISMATCH] {r['run_id']} ({r.get('market')}/{r.get('scan_mode')})")
        for m in r["rank_mismatches"][:5]:
            print(f"  rank {m['rank']}: planner={m['planner']} db={m['db']}")

    return 0 if not rank_mismatch_runs else 1


if __name__ == "__main__":
    sys.exit(main())
