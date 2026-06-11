#!/usr/bin/env python3
"""Build a trainer-compatible prepared cache from local scan CSV plus KIS label JSONL."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_agent.tools.train_scan_universe_admission_challenger import (
    _dataset_cache_signature,
    _date_text,
    prepare_dataset,
    write_prepared_dataset_cache,
)


def _read_updates_jsonl(path: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            if isinstance(row, dict):
                rows.append(row)
    return pd.DataFrame(rows)


def _filter_source(
    frame: pd.DataFrame,
    *,
    market: str,
    scan_mode: str,
    min_base_date: str,
    max_base_date: str,
    base_date: str,
    limit: int,
) -> pd.DataFrame:
    out = frame.copy()
    if market != "ALL" and "market" in out.columns:
        out = out[out["market"].fillna("").astype(str).eq(market)]
    if scan_mode != "ALL" and "scan_mode" in out.columns:
        out = out[out["scan_mode"].fillna("").astype(str).eq(scan_mode)]
    dates = out.get("base_trade_date", pd.Series("", index=out.index)).fillna("").astype(str).str[:10]
    if base_date:
        out = out[dates.eq(base_date)]
        dates = dates.reindex(out.index)
    if min_base_date:
        out = out[dates.reindex(out.index).fillna("").ge(min_base_date)]
        dates = dates.reindex(out.index)
    if max_base_date:
        out = out[dates.reindex(out.index).fillna("").le(max_base_date)]
    if limit and len(out) > int(limit):
        out = out.head(int(limit)).copy()
    return out


def _merge_updates(source: pd.DataFrame, updates: pd.DataFrame) -> pd.DataFrame:
    if source.empty or updates.empty or "snapshot_key" not in source.columns or "snapshot_key" not in updates.columns:
        return source.copy()
    base = source.copy()
    update = updates.dropna(subset=["snapshot_key"]).drop_duplicates("snapshot_key", keep="last").copy()
    base = base.set_index("snapshot_key", drop=False)
    update = update.set_index("snapshot_key", drop=False)
    common = base.index.intersection(update.index)
    for column in update.columns:
        if column == "id":
            continue
        if column not in base.columns:
            base[column] = None
        base.loc[common, column] = update.loc[common, column]
    return base.reset_index(drop=True)


def _label_coverage(frame: pd.DataFrame) -> Dict[str, Any]:
    out: Dict[str, Any] = {"rows": int(len(frame))}
    for column in (
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "max_high_return_1d_pct",
        "max_high_return_3d_pct",
        "max_high_return_5d_pct",
        "target_before_stop_5d",
        "buy_premium_target_before_stop_5d",
    ):
        if column in frame.columns:
            out[f"{column}_present"] = int(frame[column].notna().sum())
    if "market" in frame.columns:
        by_market: Dict[str, Any] = {}
        for market, rows in frame.groupby(frame["market"].fillna("UNKNOWN").astype(str)):
            by_market[str(market)] = _label_coverage(rows.drop(columns=["market"], errors="ignore"))
        out["by_market"] = by_market
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--updates-jsonl", required=True)
    parser.add_argument("--prepared-cache", required=True)
    parser.add_argument("--report-json", required=True)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--max-id", type=int, default=0)
    parser.add_argument("--base-date", default="")
    parser.add_argument("--min-base-date", default="")
    parser.add_argument("--max-base-date", default="")
    parser.add_argument("--client-filter", action="store_true")
    parser.add_argument("--max-fetch-chunks", type=int, default=0)
    parser.add_argument("--return-sanity", choices=["kr_price_limit", "off"], default="kr_price_limit")
    args = parser.parse_args()

    source = pd.read_csv(args.input_csv, low_memory=False)
    filtered = _filter_source(
        source,
        market=args.market,
        scan_mode=args.scan_mode,
        min_base_date=_date_text(args.min_base_date) or "",
        max_base_date=_date_text(args.max_base_date) or "",
        base_date=_date_text(args.base_date) or "",
        limit=int(args.limit or 0),
    )
    updates = _read_updates_jsonl(Path(args.updates_jsonl))
    merged = _merge_updates(filtered, updates)
    prepared, return_sanity = prepare_dataset(merged, return_sanity=args.return_sanity)
    fetch_filters = {
        "market": args.market,
        "scan_mode": args.scan_mode,
        "page_size": max(1, int(args.page_size)),
        "min_id": int(args.min_id or 0),
        "max_id": int(args.max_id or 0),
        "base_date": _date_text(args.base_date),
        "min_base_date": _date_text(args.min_base_date),
        "max_base_date": _date_text(args.max_base_date),
        "limit": int(args.limit or 0),
        "client_filter": bool(args.client_filter),
        "max_fetch_chunks": int(args.max_fetch_chunks or 0),
    }
    signature = _dataset_cache_signature(fetch_filters, return_sanity=args.return_sanity)
    cache_info = write_prepared_dataset_cache(
        Path(args.prepared_cache),
        signature=signature,
        data=prepared,
        raw_rows=int(len(merged)),
        return_sanity=return_sanity,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_csv": args.input_csv,
        "updates_jsonl": args.updates_jsonl,
        "source_rows": int(len(source)),
        "filtered_rows": int(len(filtered)),
        "updates_rows": int(len(updates)),
        "merged_rows": int(len(merged)),
        "prepared_rows": int(len(prepared)),
        "cache": cache_info,
        "fetch_filters": fetch_filters,
        "return_sanity": return_sanity,
        "label_coverage": _label_coverage(prepared),
    }
    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    report_path.with_suffix(".md").write_text(
        "\n".join(
            [
                "# Prepared Cache From CSV Updates",
                "",
                f"- generated_at: `{report['generated_at']}`",
                f"- filtered_rows: `{report['filtered_rows']}`",
                f"- updates_rows: `{report['updates_rows']}`",
                f"- prepared_rows: `{report['prepared_rows']}`",
                f"- cache: `{cache_info.get('path')}`",
                f"- label_coverage: `{report['label_coverage']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
