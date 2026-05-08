#!/usr/bin/env python3
"""Dedupe market_scan_results on (ticker, recommended_at::date, market, scan_mode).

Why this exists
---------------
2026-05-08 horizon 진단에서 4,596 KR PRIORITY_WATCHLIST 행 중 unique
(ticker,date) 키 464개 — 90% 중복, max 82회 중복 발견. 모든 production
KPI(win_rate/avg_return)이 같은 행을 여러 번 세서 부풀려진 통계로 측정됨.

원인: db_manager.upsert_scan_archive_outcomes의 fallback 경로가 ±2h
window NULL run_id 매칭에 실패했을 때 새 INSERT를 만들고, batch 간(다른
RUN) 중복 방지 로직 없음. 코드 주석에 'consumed_row_ids set'으로 batch
내 dedup 흔적은 있으나 batch 간은 못 막음.

What this does
--------------
1. SELECT all rows since 2026-01-01 (또는 --since)
2. (ticker, recommended_at::date, market, scan_mode) 키로 그룹화
3. 그룹 내 best 행 1개만 keep, 나머지 DELETE
   - score: alpha_score 채워짐(+4), phase25_prob 채워짐(+2),
            return_5d_pct 채워짐(+2), feature_origin=scanner_full(+3),
            run_id 채워짐(+1), recent created_at(tiebreaker)
4. --dry-run / --apply 모드
5. summary 출력

Safety
------
- DELETE는 같은 키 그룹의 잉여 행만. winning row 보존.
- outcome 데이터가 잉여 행에만 있고 winner에는 없는 경우(rare) 보호:
  winner가 outcome 없고 잉여 행 중 outcome 있는 행이 있으면, winner에
  outcome 컬럼 UPDATE 후 잉여 행 DELETE.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTCOME_COLS = (
    "return_1d_pct", "return_2d_pct", "return_3d_pct", "return_5d_pct", "return_7d_pct",
    "return_close_pct", "return_30m_pct", "return_1h_pct", "latest_return_pct",
    "outcome_status", "outcome_recorded_at", "performance_updated_at",
)

SELECT_COLS = (
    "id,ticker,recommended_at,market,scan_mode,decision,run_id,feature_origin,created_at,"
    "alpha_score,phase25_prob,phase25_oos_win_rate_pct,return_5d_pct,return_3d_pct,"
    "outcome_status,outcome_recorded_at,performance_updated_at,latest_return_pct"
)


def _load_local_env() -> None:
    for candidate in (Path(".env.local"), Path(".env")):
        if not candidate.exists():
            continue
        try:
            for raw in candidate.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            continue


def _row_score(row: dict) -> tuple:
    has_alpha = 1 if row.get("alpha_score") is not None else 0
    has_p25 = 1 if row.get("phase25_prob") is not None else 0
    has_p25_oos = 1 if row.get("phase25_oos_win_rate_pct") is not None else 0
    has_r5 = 1 if row.get("return_5d_pct") is not None else 0
    has_run = 1 if row.get("run_id") else 0
    fo = row.get("feature_origin") or ""
    fo_score = {"scanner_full": 5, "scanner_partial_legacy": 3, "scanner_archive_outcome": 2,
                "outcome_sync_partial": 1}.get(fo, 0)
    created = row.get("created_at") or row.get("recommended_at") or ""
    return (
        has_alpha * 4 + has_p25 * 2 + has_p25_oos * 1 + has_r5 * 2 + fo_score + has_run,
        str(created),
    )


def _fetch_all(client, since: str):
    out = []
    last = since
    op = "gte"
    while True:
        q = client.table("market_scan_results").select(SELECT_COLS).order("recommended_at")
        q = q.gte("recommended_at", last) if op == "gte" else q.gt("recommended_at", last)
        page = (q.limit(1000).execute().data or [])
        if not page:
            break
        out.extend(page)
        if len(page) < 1000:
            break
        last = page[-1]["recommended_at"]
        op = "gt"
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--since", default="2026-01-01T00:00:00")
    p.add_argument("--apply", action="store_true", help="Actually delete (default dry-run)")
    p.add_argument("--limit-deletes", type=int, default=None)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    _load_local_env()

    import warnings
    warnings.filterwarnings("ignore")
    from modules.db_manager import DBManager

    dm = DBManager()
    if not dm.client:
        print("No client", file=sys.stderr)
        return 2

    rows = _fetch_all(dm.client, args.since)
    print(f"Fetched rows since {args.since}: {len(rows)}")

    groups: dict = defaultdict(list)
    for r in rows:
        key = (r.get("ticker"), str(r.get("recommended_at", ""))[:10],
               r.get("market"), r.get("scan_mode"))
        if not key[0] or not key[1]:
            continue
        groups[key].append(r)

    total_keys = len(groups)
    multi_keys = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Unique keys: {total_keys}, multi-row keys: {len(multi_keys)}")

    deletes_planned = []
    outcome_merges = []  # (winner_id, patch dict)
    for key, group in multi_keys.items():
        sorted_group = sorted(group, key=_row_score, reverse=True)
        winner = sorted_group[0]
        loser_rows = sorted_group[1:]

        # Outcome rescue: winner missing outcome but some loser has it
        winner_has_outcome = any(winner.get(c) is not None for c in OUTCOME_COLS)
        if not winner_has_outcome:
            for loser in loser_rows:
                if any(loser.get(c) is not None for c in OUTCOME_COLS):
                    patch = {c: loser[c] for c in OUTCOME_COLS if loser.get(c) is not None}
                    if patch:
                        outcome_merges.append((winner["id"], patch))
                    break

        for loser in loser_rows:
            deletes_planned.append(loser["id"])

    print(f"\nDeletes planned: {len(deletes_planned)}")
    print(f"Outcome merges (winner gets loser's outcome): {len(outcome_merges)}")

    if args.limit_deletes:
        deletes_planned = deletes_planned[: args.limit_deletes]
        print(f"  limited to {len(deletes_planned)}")

    if not args.apply:
        # Sample
        print("\n--- DRY-RUN sample (first 10 keys) ---")
        for key, group in list(multi_keys.items())[:10]:
            sorted_group = sorted(group, key=_row_score, reverse=True)
            winner = sorted_group[0]
            print(f"  {key}: keep id={winner['id']} (score={_row_score(winner)[0]} "
                  f"fo={winner.get('feature_origin')} alpha={winner.get('alpha_score')}) "
                  f"delete {len(group)-1} losers")
        print(f"\nDRY-RUN summary: would delete {len(deletes_planned)} rows, "
              f"merge {len(outcome_merges)} outcomes. Pass --apply to execute.")
        return 0

    # Apply outcome merges first
    merge_done = 0
    for wid, patch in outcome_merges:
        try:
            dm.client.table("market_scan_results").update(patch).eq("id", wid).execute()
            merge_done += 1
        except Exception as e:
            if args.verbose:
                print(f"  merge_err id={wid}: {str(e)[:120]}")
    print(f"Outcome merges applied: {merge_done}/{len(outcome_merges)}")

    # Delete in batches of 500
    delete_done = 0
    for i in range(0, len(deletes_planned), 500):
        batch = deletes_planned[i: i + 500]
        try:
            dm.client.table("market_scan_results").delete().in_("id", batch).execute()
            delete_done += len(batch)
            if args.verbose or i % 5000 == 0:
                print(f"  deleted {delete_done}/{len(deletes_planned)} ...")
        except Exception as e:
            print(f"  batch_err i={i}: {str(e)[:150]}", file=sys.stderr)
    print(f"Deletes applied: {delete_done}/{len(deletes_planned)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
