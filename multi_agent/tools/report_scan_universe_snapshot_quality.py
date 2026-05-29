#!/usr/bin/env python3
"""Report Supabase scan_universe_snapshots coverage and distribution."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "scan_universe_snapshot_quality.json"
TARGET_TABLE = "scan_universe_snapshots"
RETURN_COLUMNS = (
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
    "min_low_return_1d_pct",
    "min_low_return_3d_pct",
    "min_low_return_5d_pct",
)
PATH_LABEL_COLUMNS = (
    "target_hit_1d",
    "target_hit_3d",
    "target_hit_5d",
    "stop_hit_1d",
    "stop_hit_3d",
    "stop_hit_5d",
    "target_before_stop_1d",
    "target_before_stop_3d",
    "target_before_stop_5d",
    "first_touch_1d",
    "first_touch_3d",
    "first_touch_5d",
)


def _fetch_rows(page_size: int) -> tuple[int | None, List[Dict[str, Any]]]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    try:
        count_res = db.client.table(TARGET_TABLE).select("snapshot_key", count="exact").limit(1).execute()
        exact_count = getattr(count_res, "count", None)
    except Exception:
        exact_count = None
    cols = (
        "id,run_id,market,scan_mode,row_role,passed_current_model,outcome_available,reject_reason,"
        "base_trade_date,entry_reference_price,"
        "return_1d_pct,return_3d_pct,return_5d_pct,"
        "max_high_return_1d_pct,max_high_return_3d_pct,max_high_return_5d_pct,"
        "min_low_return_1d_pct,min_low_return_3d_pct,min_low_return_5d_pct,"
        "target_hit_1d,target_hit_3d,target_hit_5d,"
        "stop_hit_1d,stop_hit_3d,stop_hit_5d,"
        "target_before_stop_1d,target_before_stop_3d,target_before_stop_5d,"
        "first_touch_1d,first_touch_3d,first_touch_5d,"
        "feature_coverage_score,feature_missing_keys,has_actual_flow,flow_consensus_buying,retail_dominant,"
        "flow_source,flow_asof,flow_warnings,normalized_feature_version"
    )
    rows: List[Dict[str, Any]] = []
    last_id = 0
    while True:
        batch = (
            db.client.table(TARGET_TABLE)
            .select(cols)
            .order("id")
            .gt("id", last_id)
            .limit(page_size)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if batch:
            last_id = max(int(row.get("id") or last_id) for row in batch)
        if len(batch) < page_size:
            break
    return exact_count, rows


def build_report(page_size: int) -> Dict[str, Any]:
    exact_count, rows = _fetch_rows(page_size)
    total = len(rows)
    by_market = Counter(str(row.get("market") or "") for row in rows)
    by_scan_mode = Counter(str(row.get("scan_mode") or "") for row in rows)
    by_role = Counter(str(row.get("row_role") or "") for row in rows)
    return_fill_counts = {col: sum(1 for row in rows if row.get(col) is not None) for col in RETURN_COLUMNS}
    return_fill_rates = {
        col: round(count / total * 100.0, 2) if total else 0.0 for col, count in return_fill_counts.items()
    }
    path_label_counts = {col: sum(1 for row in rows if row.get(col) is not None) for col in PATH_LABEL_COLUMNS}
    path_label_rates = {
        col: round(count / total * 100.0, 2) if total else 0.0 for col, count in path_label_counts.items()
    }
    feature_coverage_values = [
        float(row.get("feature_coverage_score"))
        for row in rows
        if row.get("feature_coverage_score") is not None
    ]
    feature_missing_key_counter: Counter[str] = Counter()
    for row in rows:
        missing_keys = row.get("feature_missing_keys") or []
        if isinstance(missing_keys, list):
            feature_missing_key_counter.update(str(key) for key in missing_keys)
    incomplete_return_rows = [row for row in rows if any(row.get(col) is None for col in RETURN_COLUMNS)]
    return_5d_missing_rows = [row for row in rows if row.get("return_5d_pct") is None]
    by_market_return_fill: Dict[str, Dict[str, Any]] = {}
    for market in sorted(by_market):
        market_rows = [row for row in rows if str(row.get("market") or "") == market]
        market_total = len(market_rows)
        by_market_return_fill[market] = {
            "total": market_total,
            "outcome_available": sum(1 for row in market_rows if row.get("outcome_available") is True),
            "base_trade_date_missing": sum(1 for row in market_rows if not row.get("base_trade_date")),
            "entry_reference_price_missing": sum(1 for row in market_rows if row.get("entry_reference_price") is None),
            **{
                col: {
                    "filled": sum(1 for row in market_rows if row.get(col) is not None),
                    "fill_rate_pct": round(
                        sum(1 for row in market_rows if row.get(col) is not None) / market_total * 100.0,
                        2,
                    )
                    if market_total
                    else 0.0,
                }
                for col in RETURN_COLUMNS
            },
        }
    top_reject = Counter(
        str(row.get("reject_reason") or "")
        for row in rows
        if str(row.get("row_role") or "") == "rejected"
    ).most_common(15)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table": TARGET_TABLE,
        "exact_count": exact_count,
        "fetched_rows": len(rows),
        "unique_ids": len({row.get("id") for row in rows}),
        "unique_runs": len({row.get("run_id") for row in rows if row.get("run_id")}),
        "by_market": dict(by_market),
        "by_scan_mode": dict(by_scan_mode),
        "by_role": dict(by_role),
        "passed_current_model_rows": sum(1 for row in rows if row.get("passed_current_model") is True),
        "outcome_available_rows": sum(1 for row in rows if row.get("outcome_available") is True),
        "base_trade_date_missing_rows": sum(1 for row in rows if not row.get("base_trade_date")),
        "entry_reference_price_missing_rows": sum(1 for row in rows if row.get("entry_reference_price") is None),
        "return_fill_counts": return_fill_counts,
        "return_fill_rates_pct": return_fill_rates,
        "path_label_counts": path_label_counts,
        "path_label_rates_pct": path_label_rates,
        "feature_quality": {
            "filled_rows": len(feature_coverage_values),
            "avg_feature_coverage_score": round(sum(feature_coverage_values) / len(feature_coverage_values), 6)
            if feature_coverage_values
            else None,
            "has_actual_flow_rows": sum(1 for row in rows if row.get("has_actual_flow") is True),
            "flow_consensus_buying_rows": sum(1 for row in rows if row.get("flow_consensus_buying") is True),
            "retail_dominant_rows": sum(1 for row in rows if row.get("retail_dominant") is True),
            "flow_asof_rows": sum(1 for row in rows if row.get("flow_asof")),
            "flow_source_counts": dict(Counter(str(row.get("flow_source") or "missing") for row in rows)),
            "feature_version_counts": dict(
                Counter(str(row.get("normalized_feature_version") or "missing") for row in rows)
            ),
            "top_missing_feature_keys": dict(feature_missing_key_counter.most_common(20)),
        },
        "by_market_return_fill": by_market_return_fill,
        "incomplete_return_rows": len(incomplete_return_rows),
        "incomplete_return_rows_by_base_trade_date": dict(
            Counter(str(row.get("base_trade_date") or "UNKNOWN") for row in incomplete_return_rows).most_common(15)
        ),
        "return_5d_missing_rows": len(return_5d_missing_rows),
        "return_5d_missing_rows_by_base_trade_date": dict(
            Counter(str(row.get("base_trade_date") or "UNKNOWN") for row in return_5d_missing_rows).most_common(15)
        ),
        "top_reject_reasons": dict(top_reject),
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Scan Universe Snapshot Quality",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- table: `{report.get('table')}`",
        f"- exact_count: `{report.get('exact_count')}`",
        f"- fetched_rows: `{report.get('fetched_rows')}`",
        f"- unique_ids: `{report.get('unique_ids')}`",
        f"- unique_runs: `{report.get('unique_runs')}`",
        f"- passed_current_model_rows: `{report.get('passed_current_model_rows')}`",
        f"- outcome_available_rows: `{report.get('outcome_available_rows')}`",
        f"- base_trade_date_missing_rows: `{report.get('base_trade_date_missing_rows')}`",
        f"- entry_reference_price_missing_rows: `{report.get('entry_reference_price_missing_rows')}`",
        f"- incomplete_return_rows: `{report.get('incomplete_return_rows')}`",
        f"- return_5d_missing_rows: `{report.get('return_5d_missing_rows')}`",
        "",
        "## Distribution",
        f"- by_market: `{report.get('by_market')}`",
        f"- by_scan_mode: `{report.get('by_scan_mode')}`",
        f"- by_role: `{report.get('by_role')}`",
        "",
        "## Return Coverage",
        f"- return_fill_counts: `{report.get('return_fill_counts')}`",
        f"- return_fill_rates_pct: `{report.get('return_fill_rates_pct')}`",
        f"- path_label_counts: `{report.get('path_label_counts')}`",
        f"- path_label_rates_pct: `{report.get('path_label_rates_pct')}`",
        f"- feature_quality: `{report.get('feature_quality')}`",
        f"- by_market_return_fill: `{report.get('by_market_return_fill')}`",
        f"- incomplete_return_rows_by_base_trade_date: `{report.get('incomplete_return_rows_by_base_trade_date')}`",
        f"- return_5d_missing_rows_by_base_trade_date: `{report.get('return_5d_missing_rows_by_base_trade_date')}`",
        "",
        "## Top Reject Reasons",
    ]
    for reason, count in (report.get("top_reject_reasons") or {}).items():
        lines.append(f"- `{reason or 'UNKNOWN'}`: `{count}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()

    report = build_report(page_size=max(1, int(args.page_size)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    out.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
