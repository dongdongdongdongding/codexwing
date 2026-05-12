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
4. Top Deep parity: local Top Deep Reports must match scan-time Top-N.
5. Feature origin: report what fraction of DB rows are scanner-full vs outcome
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

    Special bucket 'watchlist_field': pulls from PlannerHandoff.watchlist (a
    flat ticker list) and PlannerHandoff.watchlist_meta (with priority_rank).
    Use this when the planner downgraded all active decisions to
    watchlist-only via MARKET_POLICY_WATCHLIST_ONLY — the 'decisions' list is
    empty but watchlist still carries the user-facing tickers.
    """
    if bucket == "watchlist_field":
        meta = payload.get("watchlist_meta") or []
        items = [
            (int(m.get("priority_rank") or i + 1), str(m.get("ticker")))
            for i, m in enumerate(meta)
            if m.get("ticker")
        ]
        if not items:
            wl = payload.get("watchlist") or []
            items = [(i + 1, str(t)) for i, t in enumerate(wl) if t]
        items.sort(key=lambda x: x[0])
        return items[:n]
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
    # 'watchlist_field' is the planner-side flat watchlist; on the DB side the
    # corresponding rows live as decision_bucket='watchlist'.
    db_bucket = "watchlist" if bucket == "watchlist_field" else bucket
    if db_bucket:
        q = q.eq("decision_bucket", db_bucket)
    res = q.order("priority_rank", desc=False).execute()
    return res.data or []


def _deep_top_for_run(run_id: str, n: int, report_dir: Path) -> List[Tuple[int, str]]:
    path = report_dir / f"{run_id}.json"
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(rows, list):
        return []
    items = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip()
        if not ticker:
            continue
        try:
            rank = int(row.get("rank") or idx)
        except Exception:
            rank = idx
        items.append((rank, ticker))
    items.sort(key=lambda x: x[0])
    return items[:n]


def _compare_top_by_rank(
    left: List[Tuple[int, str]],
    right: List[Tuple[int, str]],
    *,
    left_name: str,
    right_name: str,
) -> Dict[str, Any]:
    left_by_rank = {rank: tk for rank, tk in left}
    right_by_rank = {rank: tk for rank, tk in right}
    matches = []
    mismatches = []
    left_only = []
    right_only = []
    for rank, left_tk in left_by_rank.items():
        right_tk = right_by_rank.get(rank)
        if right_tk is None:
            left_only.append((rank, left_tk))
        elif right_tk == left_tk:
            matches.append((rank, left_tk))
        else:
            mismatches.append({"rank": rank, left_name: left_tk, right_name: right_tk})
    for rank, right_tk in right_by_rank.items():
        if rank not in left_by_rank:
            right_only.append((rank, right_tk))
    return {
        "matches": matches,
        "mismatches": mismatches,
        "left_only": left_only,
        "right_only": right_only,
    }


def _verify_run(
    db: DBManager,
    run_dir: Path,
    n: int,
    bucket: Optional[str] = "picked",
    deep_report_dir: Path = Path("runtime_state/reports/top_deep"),
) -> Dict[str, Any]:
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
    db_cmp = _compare_top_by_rank(planner_top, db_top, left_name="planner", right_name="db")
    deep_top = _deep_top_for_run(str(run_id), n, deep_report_dir)
    deep_cmp = (
        _compare_top_by_rank(planner_top, deep_top, left_name="planner", right_name="deep")
        if deep_top
        else {"matches": [], "mismatches": [], "left_only": planner_top, "right_only": []}
    )

    origins = Counter(r.get("feature_origin") for r in db_rows)
    return {
        "run_dir": str(run_dir),
        "run_id": run_id,
        "market": market,
        "scan_mode": scan_mode,
        "status": "checked",
        "planner_count": len(payload.get("decisions", []) or []),
        "db_count": len(db_rows),
        "deep_count": len(deep_top),
        "topN": n,
        "ranks_match": len(db_cmp["matches"]),
        "rank_mismatches": db_cmp["mismatches"],
        "planner_only": db_cmp["left_only"],
        "db_only": db_cmp["right_only"],
        "deep_ranks_match": len(deep_cmp["matches"]),
        "deep_rank_mismatches": deep_cmp["mismatches"],
        "planner_only_deep": deep_cmp["left_only"],
        "deep_only": deep_cmp["right_only"],
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
    parser.add_argument("--deep-report-dir", default="runtime_state/reports/top_deep")
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
    deep_report_dir = Path(args.deep_report_dir)
    results = []
    for d in run_dirs:
        try:
            r = _verify_run(db, d, args.top_n, bucket=bucket, deep_report_dir=deep_report_dir)
        except Exception as exc:
            r = {"run_dir": str(d), "status": "error", "error": str(exc)}
        results.append(r)
        if args.verbose:
            print(json.dumps(r, ensure_ascii=False, indent=2))

    summary = Counter(r["status"] for r in results)
    checked = [r for r in results if r["status"] == "checked"]
    empty_bucket = [r for r in results if r["status"] == "empty_planner_for_bucket"]
    perfect = [
        r for r in checked
        if not r["rank_mismatches"]
        and not r["planner_only"]
        and not r["db_only"]
        and not r.get("deep_rank_mismatches")
        and not r.get("planner_only_deep")
        and not r.get("deep_only")
    ]
    rank_mismatch_runs = [r for r in checked if r["rank_mismatches"]]
    missing_db_rows = [r for r in checked if r["planner_only"]]
    extra_db_rows = [r for r in checked if r["db_only"]]
    deep_mismatch_runs = [r for r in checked if r.get("deep_rank_mismatches")]
    missing_deep_rows = [r for r in checked if r.get("planner_only_deep")]
    extra_deep_rows = [r for r in checked if r.get("deep_only")]
    no_db_rows = [r for r in results if r["status"] == "no_db_rows"]
    error_runs = [r for r in results if r["status"] == "error"]
    no_scanner_full = [
        r for r in checked
        if "scanner_full" not in (r.get("feature_origin_dist") or {})
    ]

    print("\n=== Scan ↔ archive top-N consistency ===")
    print(f"Bucket         : {bucket or 'ALL'}")
    print(f"Runs scanned   : {len(results)}")
    print(f"Status counts  : {dict(summary)}")
    print(f"Checked        : {len(checked)}")
    print(f"  perfect      : {len(perfect)}")
    print(f"  rank mismatch: {len(rank_mismatch_runs)}")
    print(f"  planner-only : {len(missing_db_rows)} (rows in planner_handoff but not in DB)")
    print(f"  db-only      : {len(extra_db_rows)} (rows in DB but not in planner top-N)")
    print(f"  deep mismatch: {len(deep_mismatch_runs)}")
    print(f"  planner-only deep: {len(missing_deep_rows)} (rows in planner_handoff but not in Top Deep)")
    print(f"  deep-only    : {len(extra_deep_rows)} (rows in Top Deep but not in planner top-N)")
    print(f"  no scanner_full origin: {len(no_scanner_full)} (only stubs in DB)")
    if bucket == "picked" and empty_bucket and not checked:
        print(f"\n⚠️ FAIL-LOUD: every inspected run had ZERO picked decisions.")
        print(f"   The model gate is publishing OBSERVE/AVOID only — no live")
        print(f"   trading signal has been emitted. Until at least one run")
        print(f"   yields picked rows, scan↔archive consistency is unverifiable.")
        return 3

    for r in rank_mismatch_runs[:5]:
        print(f"\n[MISMATCH] {r['run_id']} ({r.get('market')}/{r.get('scan_mode')})")
        for m in r["rank_mismatches"][:5]:
            print(f"  rank {m['rank']}: planner={m['planner']} db={m['db']}")

    for r in missing_db_rows[:5]:
        print(f"\n[DB-MISSING] {r['run_id']} ({r.get('market')}/{r.get('scan_mode')})")
        for rank, ticker in r["planner_only"][:5]:
            print(f"  rank {rank}: planner={ticker} db=<missing>")

    for r in deep_mismatch_runs[:5]:
        print(f"\n[DEEP-MISMATCH] {r['run_id']} ({r.get('market')}/{r.get('scan_mode')})")
        for m in r["deep_rank_mismatches"][:5]:
            print(f"  rank {m['rank']}: planner={m['planner']} deep={m['deep']}")

    fail = bool(
        rank_mismatch_runs
        or missing_db_rows
        or extra_db_rows
        or deep_mismatch_runs
        or missing_deep_rows
        or extra_deep_rows
        or no_db_rows
        or error_runs
    )
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
