#!/usr/bin/env python3
"""Emit daily snapshot of segment-level backtest metrics for drift monitoring.

Reads the latest retrain_v2_report.json (segment metrics: AUC, win-rate@threshold,
signal_direction, threshold_sweep) and appends one JSON line per segment to
runtime_state/reports/data_health/daily_backtest.jsonl, then evaluates drift
triggers and (optionally) posts a webhook alert.

Two record kinds are written to the same jsonl:
- kind=segment_metric — model-side health (AUC/threshold sweep) per phase25 segment
- kind=picked_realized — production-side health: realized win_rate / avg_return /
  hit_rate computed from market_scan_results rows where decision_bucket='picked'
  (PRIORITY_WATCHLIST) over a trailing window. Computed separately for
  exception_leader bucket so Stream A vs Stream B health is distinguishable.

Drift triggers (multi-layer, validator-first to suppress false positives):
- INVERTED        — signal_direction == 'inverted' on latest segment snapshot
- AUC_DECAY       — raw_auc < 0.5 for N consecutive snapshots (default 3),
                    only when rows >= sample_floor (default 200)
- PICKED_WIN_DROP — picked_realized.win_rate < 50% for K consecutive snapshots
                    (default 5), only when picked_resolved >= 30
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.workflows.alerts import _post_webhook  # noqa: E402

RETRAIN_REPORT_PATH = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "retrain_v2_report.json"
DAILY_BACKTEST_JSONL = PROJECT_ROOT / "runtime_state" / "reports" / "data_health" / "daily_backtest.jsonl"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _append_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _pick_threshold_row(segment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    best = segment.get("best_threshold_row")
    if isinstance(best, dict) and "threshold" in best:
        return best
    rec_thr = segment.get("recommended_probability_threshold")
    sweep = segment.get("threshold_sweep") or []
    if rec_thr is None or not isinstance(sweep, list):
        return None
    for row in sweep:
        if isinstance(row, dict) and float(row.get("threshold", -1)) == float(rec_thr):
            return row
    return None


def _to_snapshot_row(
    segment: Dict[str, Any],
    snapshot_date: str,
    generated_at: str,
) -> Optional[Dict[str, Any]]:
    name = segment.get("name")
    if not name:
        return None
    if str(segment.get("status", "")).lower() != "trained":
        return {
            "kind": "segment_metric",
            "date": snapshot_date,
            "generated_at": generated_at,
            "segment": str(name),
            "status": str(segment.get("status", "")),
            "rows": int(segment.get("rows") or 0),
            "raw_auc": None,
            "cv_median_auc": None,
            "signal_direction": None,
            "threshold": None,
            "picks": None,
            "win_rate": None,
            "avg_return": None,
            "hit_rate": None,
            "return_col": segment.get("return_col"),
        }
    thr_row = _pick_threshold_row(segment) or {}
    return {
        "kind": "segment_metric",
        "date": snapshot_date,
        "generated_at": generated_at,
        "segment": str(name),
        "status": "trained",
        "rows": int(segment.get("rows") or 0),
        "raw_auc": _safe_float(segment.get("raw_auc")),
        "cv_median_auc": _safe_float(segment.get("cv_median_auc")),
        "signal_direction": segment.get("signal_direction"),
        "threshold": _safe_float(thr_row.get("threshold")),
        "picks": _safe_int(thr_row.get("picks")),
        "win_rate": _safe_float(thr_row.get("win_rate")),
        "avg_return": _safe_float(thr_row.get("avg_return")),
        "hit_rate": _safe_float(thr_row.get("hit_rate")),
        "return_col": segment.get("return_col"),
    }


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _collect_picked_realized(
    *,
    snapshot_date: str,
    generated_at: str,
    window_days: int,
    bucket_label: str,
    decision_filter: List[str],
) -> Optional[Dict[str, Any]]:
    """Aggregate realized win_rate / avg_return / hit_rate for production picks.

    Window is trailing window_days ending at the snapshot_date. We use
    Rows are eligible only when the realized return column for the row's model
    horizon is non-null. KOSDAQ swing Phase25 bundles use a 5d label, while
    KOSPI swing keeps the 3d label.
    """
    from datetime import timedelta

    try:
        from modules.db_manager import DBManager
    except Exception:
        return None
    db = DBManager()
    if not getattr(db, "client", None):
        return None
    try:
        end_dt = datetime.fromisoformat(snapshot_date)
    except Exception:
        end_dt = datetime.now(timezone.utc)
    end_iso = end_dt.replace(tzinfo=timezone.utc).isoformat() if end_dt.tzinfo is None else end_dt.isoformat()
    start_iso = (end_dt - timedelta(days=int(window_days))).replace(
        tzinfo=timezone.utc
    ).isoformat() if end_dt.tzinfo is None else (end_dt - timedelta(days=int(window_days))).isoformat()

    rows: List[Dict[str, Any]] = []
    page_size = 1000
    page = 0
    while True:
        try:
            res = (
                db.client.table("market_scan_results")
                .select(
                    "decision,decision_bucket,return_1d_pct,return_3d_pct,return_5d_pct,"
                    "market_type,scan_mode,phase25_variant,created_at"
                )
                .gte("created_at", start_iso)
                .lt("created_at", end_iso)
                .in_("decision", decision_filter)
                .range(page * page_size, page * page_size + page_size - 1)
                .execute()
            )
        except Exception as exc:
            print(f"[WARN] picked_realized query failed: {exc}")
            return None
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
        if page > 20:
            break

    resolved_returns: List[float] = []
    return_columns = defaultdict(int)
    for r in rows:
        value, return_col = _resolved_return_for_row(r)
        if value is None:
            continue
        resolved_returns.append(value)
        return_columns[return_col] += 1

    resolved = len(resolved_returns)
    if resolved == 0:
        return {
            "kind": "picked_realized",
            "date": snapshot_date,
            "generated_at": generated_at,
            "bucket": bucket_label,
            "window_days": int(window_days),
            "resolved_rows": 0,
            "win_rate": None,
            "avg_return": None,
            "hit_rate_5pct": None,
            "hit_rate_10pct": None,
            "median_return": None,
            "decision_filter": list(decision_filter),
            "return_columns": {},
        }
    wins = 0
    hit5 = 0
    hit10 = 0
    for v in resolved_returns:
        if v > 0:
            wins += 1
        if v >= 5.0:
            hit5 += 1
        if v >= 10.0:
            hit10 += 1
    returns_sorted = sorted(resolved_returns)
    median = returns_sorted[len(returns_sorted) // 2]
    avg = sum(resolved_returns) / len(resolved_returns)
    return {
        "kind": "picked_realized",
        "date": snapshot_date,
        "generated_at": generated_at,
        "bucket": bucket_label,
        "window_days": int(window_days),
        "resolved_rows": resolved,
        "win_rate": round(100.0 * wins / resolved, 4),
        "avg_return": round(avg, 4),
        "median_return": round(median, 4),
        "hit_rate_5pct": round(100.0 * hit5 / resolved, 4),
        "hit_rate_10pct": round(100.0 * hit10 / resolved, 4),
        "decision_filter": list(decision_filter),
        "return_columns": dict(sorted(return_columns.items())),
    }


def _resolved_return_for_row(row: Dict[str, Any]) -> Tuple[Optional[float], str]:
    """Return the realized pct using the row's Phase25 label horizon."""
    variant = str(row.get("phase25_variant") or "").lower()
    market = str(row.get("market_type") or "").upper()
    mode = str(row.get("scan_mode") or "").upper()
    if mode == "INTRADAY":
        candidates = ("return_1d_pct", "return_3d_pct")
    elif "kosdaq_swing" in variant:
        candidates = ("return_5d_pct", "return_3d_pct")
    elif "kospi_swing" in variant:
        candidates = ("return_3d_pct", "return_5d_pct")
    elif market == "KOSDAQ" and mode == "SWING":
        candidates = ("return_5d_pct", "return_3d_pct")
    else:
        candidates = ("return_3d_pct", "return_5d_pct")
    for col in candidates:
        value = _safe_float(row.get(col))
        if value is not None:
            return value, col
    return None, candidates[0]


def _evaluate_picked_triggers(
    history: List[Dict[str, Any]],
    *,
    consecutive: int,
    win_rate_floor: float,
    resolved_floor: int,
) -> List[Dict[str, Any]]:
    """Fire PICKED_WIN_DROP when win_rate < floor for K consecutive snapshots
    on the same bucket, gated by resolved_floor to suppress small-sample noise."""
    by_bucket: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in history:
        if row.get("kind") != "picked_realized":
            continue
        bucket = row.get("bucket")
        if not bucket:
            continue
        by_bucket[str(bucket)].append(row)
    for bucket in by_bucket:
        by_bucket[bucket].sort(key=lambda r: (str(r.get("date", "")), str(r.get("generated_at", ""))))

    alerts: List[Dict[str, Any]] = []
    for bucket, rows in by_bucket.items():
        eligible = [r for r in rows if r.get("win_rate") is not None and int(r.get("resolved_rows") or 0) >= int(resolved_floor)]
        tail = eligible[-consecutive:]
        if len(tail) < consecutive:
            continue
        if all(float(r["win_rate"]) < float(win_rate_floor) for r in tail):
            wr = [round(float(r["win_rate"]), 2) for r in tail]
            latest = tail[-1]
            alerts.append(
                {
                    "type": "PICKED_WIN_DROP",
                    "bucket": bucket,
                    "date": latest.get("date"),
                    "consecutive": int(consecutive),
                    "win_rate_floor_pct": float(win_rate_floor),
                    "win_rate_window_pct": wr,
                    "resolved_rows": latest.get("resolved_rows"),
                    "message": (
                        f"[picked:{bucket}] win_rate<{win_rate_floor}% for {consecutive} consecutive snapshots "
                        f"({wr}%) latest_resolved={latest.get('resolved_rows')}"
                    ),
                }
            )
    return alerts


def _evaluate_triggers(
    history: List[Dict[str, Any]],
    *,
    auc_decay_consecutive: int,
    sample_floor: int,
) -> List[Dict[str, Any]]:
    by_segment: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in history:
        # Skip picked_realized rows — handled by _evaluate_picked_triggers
        if row.get("kind") == "picked_realized":
            continue
        seg = row.get("segment")
        if not seg:
            continue
        by_segment[str(seg)].append(row)
    for seg in by_segment:
        by_segment[seg].sort(key=lambda r: (str(r.get("date", "")), str(r.get("generated_at", ""))))

    alerts: List[Dict[str, Any]] = []
    for seg, rows in by_segment.items():
        if not rows:
            continue
        latest = rows[-1]
        if latest.get("status") != "trained":
            continue

        if str(latest.get("signal_direction", "")).lower() == "inverted":
            alerts.append(
                {
                    "type": "INVERTED",
                    "segment": seg,
                    "date": latest.get("date"),
                    "rows": latest.get("rows"),
                    "raw_auc": latest.get("raw_auc"),
                    "signal_direction": latest.get("signal_direction"),
                    "message": (
                        f"[{seg}] signal_direction=inverted "
                        f"(rows={latest.get('rows')} raw_auc={latest.get('raw_auc')})"
                    ),
                }
            )

        if int(latest.get("rows") or 0) < int(sample_floor):
            continue
        tail = [r for r in rows[-auc_decay_consecutive:] if r.get("status") == "trained"]
        if len(tail) < auc_decay_consecutive:
            continue
        if all(
            (r.get("raw_auc") is not None and float(r["raw_auc"]) < 0.5)
            and int(r.get("rows") or 0) >= int(sample_floor)
            for r in tail
        ):
            aucs = [float(r["raw_auc"]) for r in tail]
            alerts.append(
                {
                    "type": "AUC_DECAY",
                    "segment": seg,
                    "date": latest.get("date"),
                    "rows": latest.get("rows"),
                    "consecutive": auc_decay_consecutive,
                    "raw_auc_window": aucs,
                    "message": (
                        f"[{seg}] raw_auc<0.5 for {auc_decay_consecutive} consecutive snapshots "
                        f"({aucs}) rows={latest.get('rows')}"
                    ),
                }
            )

    return alerts


def _build_alert_payload(
    *,
    snapshot_date: str,
    alerts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "alert_type": "model_drift",
        "snapshot_date": snapshot_date,
        "alert_count": len(alerts),
        "alerts": alerts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append daily segment-level backtest snapshot and evaluate drift triggers."
    )
    parser.add_argument(
        "--retrain-report",
        type=str,
        default=str(RETRAIN_REPORT_PATH),
        help="Path to retrain_v2_report.json (default: runtime_state/reports/learning/retrain_v2_report.json)",
    )
    parser.add_argument(
        "--out-jsonl",
        type=str,
        default=str(DAILY_BACKTEST_JSONL),
        help="Path to daily_backtest.jsonl (default: runtime_state/reports/data_health/daily_backtest.jsonl)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=date.today().isoformat(),
        help="Snapshot date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--auc-decay-consecutive",
        type=int,
        default=3,
        help="Consecutive snapshots required for AUC_DECAY trigger (default 3).",
    )
    parser.add_argument(
        "--sample-floor",
        type=int,
        default=200,
        help="Minimum rows for AUC_DECAY trigger to fire (default 200).",
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=os.environ.get("AG_DRIFT_ALERT_WEBHOOK_URL", ""),
        help="Webhook URL (defaults to AG_DRIFT_ALERT_WEBHOOK_URL env).",
    )
    parser.add_argument(
        "--picked-window-days",
        type=int,
        default=30,
        help="Trailing window for picked-row realized rollup (default 30).",
    )
    parser.add_argument(
        "--picked-win-rate-floor",
        type=float,
        default=50.0,
        help="Win-rate floor (%%) for PICKED_WIN_DROP trigger (default 50.0).",
    )
    parser.add_argument(
        "--picked-resolved-floor",
        type=int,
        default=30,
        help="Min resolved rows for PICKED_WIN_DROP to fire (default 30).",
    )
    parser.add_argument(
        "--picked-consecutive",
        type=int,
        default=5,
        help="Consecutive snapshots for PICKED_WIN_DROP (default 5).",
    )
    parser.add_argument(
        "--no-picked",
        action="store_true",
        help="Skip the picked-realized rollup (segment metrics only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip jsonl append; print snapshot rows and alerts only.",
    )
    args = parser.parse_args()

    retrain_path = Path(args.retrain_report)
    out_path = Path(args.out_jsonl)
    snapshot_date = str(args.date)

    report = _load_json(retrain_path)
    if not report:
        print(json.dumps({"status": "skip", "reason": "missing_retrain_report", "path": str(retrain_path)}))
        return 1

    generated_at = str(report.get("generated_at") or datetime.now(timezone.utc).isoformat())
    segments = report.get("segments") or []
    if not isinstance(segments, list) or not segments:
        print(json.dumps({"status": "skip", "reason": "no_segments"}))
        return 1

    rows: List[Dict[str, Any]] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        row = _to_snapshot_row(seg, snapshot_date=snapshot_date, generated_at=generated_at)
        if row:
            rows.append(row)

    if not rows:
        print(json.dumps({"status": "skip", "reason": "no_valid_segments"}))
        return 1

    picked_rows: List[Dict[str, Any]] = []
    if not args.no_picked:
        for bucket_label, decision_filter in (
            ("picked", ["PRIORITY_WATCHLIST"]),
            ("exception_leader", ["EXCEPTION_LEADER"]),
        ):
            picked_row = _collect_picked_realized(
                snapshot_date=snapshot_date,
                generated_at=generated_at,
                window_days=int(args.picked_window_days),
                bucket_label=bucket_label,
                decision_filter=decision_filter,
            )
            if picked_row:
                picked_rows.append(picked_row)

    history = _read_jsonl(out_path)

    def _row_key(r: Dict[str, Any]) -> Tuple[str, str, str]:
        kind = str(r.get("kind") or "segment_metric")
        if kind == "picked_realized":
            return (str(r.get("date")), kind, str(r.get("bucket")))
        return (str(r.get("date")), kind, str(r.get("segment")))

    existing_keys = {_row_key(r) for r in history}
    all_new = rows + picked_rows
    new_rows = [r for r in all_new if _row_key(r) not in existing_keys]
    skipped_rows = len(all_new) - len(new_rows)

    if not args.dry_run and new_rows:
        _append_jsonl(out_path, new_rows)

    combined_history = history + new_rows
    alerts = _evaluate_triggers(
        combined_history,
        auc_decay_consecutive=int(args.auc_decay_consecutive),
        sample_floor=int(args.sample_floor),
    )
    alerts.extend(
        _evaluate_picked_triggers(
            combined_history,
            consecutive=int(args.picked_consecutive),
            win_rate_floor=float(args.picked_win_rate_floor),
            resolved_floor=int(args.picked_resolved_floor),
        )
    )

    webhook_result: Optional[Dict[str, Any]] = None
    if alerts and args.webhook_url and not args.dry_run:
        payload = _build_alert_payload(snapshot_date=snapshot_date, alerts=alerts)
        try:
            webhook_result = _post_webhook(url=args.webhook_url, payload=payload, timeout_sec=6)
        except Exception as exc:
            webhook_result = {"error": str(exc)}

    summary = {
        "status": "ok",
        "snapshot_date": snapshot_date,
        "appended_rows": 0 if args.dry_run else len(new_rows),
        "skipped_existing": skipped_rows,
        "segments_total": len(rows),
        "picked_rows_total": len(picked_rows),
        "picked_buckets": [r.get("bucket") for r in picked_rows],
        "alerts": alerts,
        "alert_count": len(alerts),
        "webhook_dispatched": bool(webhook_result is not None and not webhook_result.get("error")),
        "webhook_result": webhook_result,
        "dry_run": bool(args.dry_run),
        "out_jsonl": str(out_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
