#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TARGET_TOP5_ACCURACY_PCT = 75.0
TARGET_HIGH_CONVICTION_RETURN_PCT = 15.0
SEGMENTS = ("KOSPI", "KOSDAQ", "NASDAQ", "AMEX")
SCAN_MODES = ("SWING", "INTRADAY")
MODE_TO_METRIC = {
    "SWING": "return_3d_pct",
    "INTRADAY": "return_1d_pct",
}


def _load_env() -> Tuple[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local")
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
    if not url or not key:
        raise SystemExit("Supabase credentials are required in .env.local or environment.")
    return str(url).rstrip("/"), str(key)


def _fetch_rows(
    *,
    base_url: str,
    api_key: str,
    scan_mode: str,
    metric_column: str,
    page_size: int,
    max_rows: int,
) -> List[Dict[str, Any]]:
    endpoint = f"{base_url}/rest/v1/market_scan_results"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Range-Unit": "items",
    }
    params = {
        "select": ",".join(
            [
                "ticker",
                "market",
                "market_type",
                "scan_mode",
                "decision_score",
                "created_at",
                "base_trade_date",
                "validation_excluded",
                metric_column,
            ]
        ),
        "scan_mode": f"eq.{scan_mode}",
        metric_column: "not.is.null",
        "order": "created_at.desc",
    }
    rows: List[Dict[str, Any]] = []
    start = 0
    while start < max_rows:
        headers["Range"] = f"{start}-{start + page_size - 1}"
        resp = requests.get(endpoint, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        batch = list(resp.json() or [])
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


def _infer_market(row: Dict[str, Any]) -> str | None:
    market = str(row.get("market") or "").upper()
    market_type = str(row.get("market_type") or "").upper()
    ticker = str(row.get("ticker") or "").upper()
    if market in SEGMENTS:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if market_type == "AMEX":
        return "AMEX"
    if market_type == "US" and market in {"NASDAQ", "NYSE"}:
        return "NASDAQ"
    return None


def _scan_date(row: Dict[str, Any]) -> str | None:
    base_trade_date = row.get("base_trade_date")
    if base_trade_date:
        return str(base_trade_date)
    created_at = row.get("created_at")
    if created_at:
        return str(created_at)[:10]
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _dedupe_latest(rows: Iterable[Dict[str, Any]], metric_column: str) -> List[Dict[str, Any]]:
    latest: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        scan_date = _scan_date(row)
        ticker = str(row.get("ticker") or "")
        scan_mode = str(row.get("scan_mode") or "SWING").upper()
        if not scan_date or not ticker:
            continue
        key = (scan_date, scan_mode, ticker)
        prev = latest.get(key)
        if prev is None or str(row.get("created_at") or "") > str(prev.get("created_at") or ""):
            latest[key] = row
    return [row for row in latest.values() if row.get(metric_column) is not None]


def _daily_topn_rows(rows: List[Dict[str, Any]], topn: int, metric_column: str) -> Dict[str, List[Dict[str, float]]]:
    grouped: Dict[Tuple[str, str, str], List[Tuple[float, float]]] = defaultdict(list)
    for row in rows:
        if row.get("validation_excluded") is True:
            continue
        market = _infer_market(row)
        scan_mode = str(row.get("scan_mode") or "SWING").upper()
        scan_date = _scan_date(row)
        metric = _safe_float(row.get(metric_column))
        score = _safe_float(row.get("decision_score"))
        if not market or not scan_date or metric is None or score is None:
            continue
        grouped[(market, scan_mode, scan_date)].append((score, metric))

    daily: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for (market, scan_mode, scan_date), values in grouped.items():
        ordered = sorted(values, key=lambda item: (-item[0],))
        picked = ordered[:topn]
        if not picked:
            continue
        metrics = [metric for _, metric in picked]
        daily[f"{market}:{scan_mode}"].append(
            {
                "scan_date": scan_date,
                "samples": float(len(metrics)),
                "positive_rate": sum(v > 0 for v in metrics) / len(metrics),
                "avg_return_pct": sum(metrics) / len(metrics),
                "hit5_rate": sum(v >= 5.0 for v in metrics) / len(metrics),
                "hit10_rate": sum(v >= 10.0 for v in metrics) / len(metrics),
            }
        )
    return daily


def _aggregate(days: List[Dict[str, float]]) -> Dict[str, Any]:
    if not days:
        return {
            "days": 0,
            "topn_samples_per_day": 0,
            "positive_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "hit5_rate_pct": 0.0,
            "hit10_rate_pct": 0.0,
            "accuracy_gap_to_target_pct": -TARGET_TOP5_ACCURACY_PCT,
            "return_gap_to_target_pct": -TARGET_HIGH_CONVICTION_RETURN_PCT,
        }
    return {
        "days": int(len(days)),
        "topn_samples_per_day": int(round(sum(day["samples"] for day in days) / len(days))),
        "positive_rate_pct": round(sum(day["positive_rate"] for day in days) / len(days) * 100.0, 2),
        "avg_return_pct": round(sum(day["avg_return_pct"] for day in days) / len(days), 4),
        "hit5_rate_pct": round(sum(day["hit5_rate"] for day in days) / len(days) * 100.0, 2),
        "hit10_rate_pct": round(sum(day["hit10_rate"] for day in days) / len(days) * 100.0, 2),
        "accuracy_gap_to_target_pct": round(
            sum(day["positive_rate"] for day in days) / len(days) * 100.0 - TARGET_TOP5_ACCURACY_PCT,
            2,
        ),
        "return_gap_to_target_pct": round(
            sum(day["avg_return_pct"] for day in days) / len(days) - TARGET_HIGH_CONVICTION_RETURN_PCT,
            4,
        ),
    }


def _segment_warnings(*, days: int, market: str, scan_mode: str) -> List[str]:
    warnings: List[str] = []
    if days <= 0:
        warnings.append("NO_MATURE_OUTCOMES")
    elif days < 3:
        warnings.append("VERY_LOW_SAMPLE")
    elif days < 7:
        warnings.append("LOW_SAMPLE")
    if market in {"NASDAQ", "AMEX"} and days < 10:
        warnings.append("US_VALIDATION_PARITY_INCOMPLETE")
    if scan_mode == "INTRADAY" and days < 10:
        warnings.append("INTRADAY_MATURITY_THIN")
    return warnings


def build_report(
    *,
    topn: int,
    recent_days: int,
    page_size: int,
    max_rows: int,
) -> Dict[str, Any]:
    base_url, api_key = _load_env()
    matured_rows: List[Dict[str, Any]] = []
    mode_fetch_stats: Dict[str, int] = {}
    for scan_mode, metric_column in MODE_TO_METRIC.items():
        fetched = _fetch_rows(
            base_url=base_url,
            api_key=api_key,
            scan_mode=scan_mode,
            metric_column=metric_column,
            page_size=page_size,
            max_rows=max_rows,
        )
        mode_fetch_stats[scan_mode] = len(fetched)
        matured_rows.extend(_dedupe_latest(fetched, metric_column))

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "supabase.market_scan_results",
        "topn": int(topn),
        "recent_days": int(recent_days),
        "targets": {
            "top5_accuracy_pct": TARGET_TOP5_ACCURACY_PCT,
            "high_conviction_avg_return_pct": TARGET_HIGH_CONVICTION_RETURN_PCT,
        },
        "measurement_horizon_by_mode": MODE_TO_METRIC,
        "fetch_stats": {
            "raw_rows_by_mode": mode_fetch_stats,
            "deduped_mature_rows": int(len(matured_rows)),
        },
        "segments": {},
    }

    daily_by_segment: Dict[str, List[Dict[str, float]]] = {}
    for scan_mode, metric_column in MODE_TO_METRIC.items():
        mode_rows = [row for row in matured_rows if str(row.get("scan_mode") or "SWING").upper() == scan_mode]
        daily_by_segment.update(_daily_topn_rows(mode_rows, topn=topn, metric_column=metric_column))

    for market in SEGMENTS:
        for scan_mode in SCAN_MODES:
            segment_key = f"{market}:{scan_mode}"
            metric_column = MODE_TO_METRIC[scan_mode]
            ordered_days = sorted(daily_by_segment.get(segment_key, []), key=lambda item: str(item["scan_date"]))
            recent = ordered_days[-recent_days:] if recent_days > 0 else ordered_days
            history_block = _aggregate(ordered_days)
            recent_block = _aggregate(recent)
            report["segments"][segment_key] = {
                "market": market,
                "scan_mode": scan_mode,
                "metric_column": metric_column,
                "all_history": history_block,
                "recent_window": recent_block,
                "recent_scan_dates": [str(item["scan_date"]) for item in recent],
                "warnings": _segment_warnings(days=int(recent_block.get("days", 0)), market=market, scan_mode=scan_mode),
            }
    return report


def _segment_sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[float, float, str]:
    key, payload = item
    recent = payload.get("recent_window") or {}
    return (
        float(recent.get("accuracy_gap_to_target_pct", -9999.0)),
        float(recent.get("avg_return_pct", -9999.0)),
        key,
    )


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Segment Top{report['topn']} Validation",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- source: {report['source']}",
        f"- target_top5_accuracy_pct: {report['targets']['top5_accuracy_pct']:.2f}",
        f"- target_high_conviction_avg_return_pct: {report['targets']['high_conviction_avg_return_pct']:.2f}",
        f"- recent_days: {report['recent_days']}",
        f"- measurement_horizon_by_mode: {report['measurement_horizon_by_mode']}",
        f"- fetch_stats: {report['fetch_stats']}",
        "",
        "## Segment Baselines",
    ]
    for segment_key, payload in sorted(report.get("segments", {}).items(), key=_segment_sort_key, reverse=True):
        recent = payload.get("recent_window") or {}
        history = payload.get("all_history") or {}
        lines.extend(
            [
                f"### {segment_key}",
                f"- recent days: {recent.get('days', 0)} | history days: {history.get('days', 0)}",
                f"- recent top{report['topn']} positive-rate: {recent.get('positive_rate_pct', 0.0):.2f}% "
                f"(gap {recent.get('accuracy_gap_to_target_pct', 0.0):+.2f}%)",
                f"- recent top{report['topn']} avg return: {recent.get('avg_return_pct', 0.0):+.2f}% "
                f"(gap {recent.get('return_gap_to_target_pct', 0.0):+.2f}%)",
                f"- recent hit5 / hit10: {recent.get('hit5_rate_pct', 0.0):.2f}% / {recent.get('hit10_rate_pct', 0.0):.2f}%",
                f"- history top{report['topn']} positive-rate: {history.get('positive_rate_pct', 0.0):.2f}%",
                f"- history top{report['topn']} avg return: {history.get('avg_return_pct', 0.0):+.2f}%",
                f"- warnings: {payload.get('warnings', [])}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report realized Top-N validation by market x scan_mode segment.")
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--recent-days", type=int, default=20)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=30000)
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    args = parser.parse_args()

    report = build_report(
        topn=int(args.topn),
        recent_days=int(args.recent_days),
        page_size=int(args.page_size),
        max_rows=int(args.max_rows),
    )
    output_dir = PROJECT_ROOT / str(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"segment_top{int(args.topn)}_validation"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "segments": len(report.get("segments", {})),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
