#!/usr/bin/env python3
"""Build and backfill full-universe scan snapshots from local RUN artifacts.

This intentionally bypasses ``market_scan_results`` as a learning source.
``market_scan_results`` is candidate/archive oriented; this tool normalizes
both emitted candidates and rejected symbols from raw scan diagnostics so
research models can learn from the actual scan universe.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "runtime_state" / "artifacts"
DEFAULT_SHARED_DIR = PROJECT_ROOT / "runtime_state" / "shared_working"
DEFAULT_REJECT_OUTCOME_CSV = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "kr_rejected_symbol_outcomes.csv"
DEFAULT_OUTPUT_CSV = PROJECT_ROOT / "runtime_state" / "reports" / "archive" / "scan_universe_snapshots_kr.csv"
DEFAULT_REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "scan_universe_snapshot_backfill.json"

BACKFILL_VERSION = "scan_universe_snapshot_backfill_v1"
TARGET_TABLE = "scan_universe_snapshots"
KR_MARKETS = {"KOSPI", "KOSDAQ"}
OUTCOME_COLUMNS = (
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
)


def _load_local_env() -> None:
    for candidate in (PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "NaN", "None"):
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _date_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if len(text) >= 10:
        return text[:10]
    return None


def _timestamp_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if len(text) == 10:
        return f"{text}T00:00:00+00:00"
    if text.endswith("Z"):
        return text[:-1] + "+00:00"
    return text


def _market_from(market: Any, ticker: str = "") -> str:
    value = _text(market).upper()
    if value in KR_MARKETS:
        return value
    ticker = _text(ticker).upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return value


def _ticker(row: Dict[str, Any], fallback: Any = "") -> str:
    return _text(_first_present(row, "ticker", "Ticker", "symbol", "Symbol", "티커") or fallback).upper()


def _normalize_reason_codes(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        parts = [part.strip() for part in value.replace(",", "|").split("|")]
        return [part for part in parts if part]
    if isinstance(value, dict):
        return [str(k) for k, v in value.items() if v]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def _feature_number(row: Dict[str, Any], *keys: str) -> float | None:
    return _safe_float(_first_present(row, *keys))


def _extract_feature_columns(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "alpha_score": _feature_number(row, "alpha_score", "Antigrav", "Alpha", "alpha"),
        "tech_score": _feature_number(row, "tech_score", "technical_score", "Tech"),
        "ml_prob": _feature_number(row, "ml_prob", "prob_5", "phase25_prob", "probability"),
        "prob_clean": _feature_number(row, "prob_clean", "phase25_prob_clean", "clean_prob"),
        "whale_score": _feature_number(row, "whale_score", "whale", "Whale"),
        "decision_score": _feature_number(row, "decision_score", "Decision Score", "score", "buy_score"),
        "day_return_pct": _feature_number(row, "day_return_pct", "day_change_pct", "day_ret", "Change %", "전일비"),
        "volume_ratio": _feature_number(row, "volume_ratio", "vol_ratio", "volume", "Volume Ratio"),
        "turnover": _feature_number(row, "turnover", "trading_value", "amount", "거래대금"),
        "foreigner_1d": _feature_number(row, "foreigner_1d", "foreign_1d", "foreign_flow_1d"),
        "institution_1d": _feature_number(row, "institution_1d", "inst_1d", "institution_flow_1d"),
        "retail_1d": _feature_number(row, "retail_1d", "individual_1d"),
        "foreigner_3d": _feature_number(row, "foreigner_3d", "foreign_3d"),
        "institution_3d": _feature_number(row, "institution_3d", "inst_3d"),
        "retail_3d": _feature_number(row, "retail_3d", "individual_3d"),
        "foreigner_10d": _feature_number(row, "foreigner_10d", "foreign_10d"),
        "institution_10d": _feature_number(row, "institution_10d", "inst_10d"),
        "retail_10d": _feature_number(row, "retail_10d", "individual_10d"),
        "primary_theme": _first_present(row, "primary_theme", "theme", "Theme", "테마"),
        "theme_source": _first_present(row, "theme_source"),
        "theme_inference_status": _first_present(row, "theme_inference_status"),
        "kr_universe_role": _first_present(row, "kr_universe_role"),
        "scanner_timeframe_profile": _first_present(row, "scanner_timeframe_profile"),
        "entry_reference_price": _feature_number(row, "entry_reference_price", "scan_entry_reference_price", "curr_price", "price"),
    }


def _load_realized_outcomes(shared_dir: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not shared_dir.exists():
        return index
    for path in shared_dir.glob("RUN-*/realized_outcomes.json"):
        payload = _load_json(path)
        if not isinstance(payload, dict):
            continue
        run_id = _text(payload.get("run_id") or path.parent.name)
        outcomes = payload.get("outcomes")
        if not isinstance(outcomes, list):
            continue
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            ticker = _ticker(row)
            if not run_id or not ticker:
                continue
            subset = {
                col: _safe_float(row.get(col))
                for col in (
                    "return_1d_pct",
                    "return_3d_pct",
                    "return_5d_pct",
                    "mfe_5d_pct",
                    "mae_5d_pct",
                )
            }
            subset["entry_reference_price"] = _safe_float(row.get("entry_reference_price") or row.get("scan_entry_reference_price"))
            subset["base_trade_date"] = _date_text(row.get("base_trade_date") or row.get("recommended_at"))
            subset["outcome_available"] = any(subset.get(col) is not None for col in ("return_1d_pct", "return_3d_pct", "return_5d_pct"))
            subset["outcome_source"] = "realized_outcomes"
            index[(run_id, ticker)] = subset
    return index


def _load_reject_outcomes(path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not path.exists():
        return index
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            run_id = _text(row.get("run_id"))
            ticker = _ticker(row)
            if not run_id or not ticker:
                continue
            subset = {
                col: _safe_float(row.get(col))
                for col in OUTCOME_COLUMNS
            }
            subset["entry_reference_price"] = _safe_float(row.get("entry_reference_price"))
            subset["base_trade_date"] = _date_text(row.get("base_trade_date"))
            subset["outcome_available"] = str(row.get("outcome_available") or "").strip().lower() in {"1", "true", "yes"} or any(
                subset.get(col) is not None for col in ("return_1d_pct", "return_3d_pct", "return_5d_pct")
            )
            subset["outcome_source"] = "kr_rejected_symbol_outcomes"
            subset["backfill_version"] = row.get("backfill_version")
            index[(run_id, ticker)] = subset
    return index


def _apply_outcome(row: Dict[str, Any], outcome: Dict[str, Any] | None) -> Dict[str, Any]:
    if not outcome:
        row["outcome_available"] = False
        return row
    for col in OUTCOME_COLUMNS:
        if outcome.get(col) is not None:
            row[col] = outcome.get(col)
    if outcome.get("return_5d_pct") is None and outcome.get("mfe_5d_pct") is not None:
        row["max_high_return_5d_pct"] = outcome.get("mfe_5d_pct")
    if outcome.get("entry_reference_price") is not None:
        row["entry_reference_price"] = outcome.get("entry_reference_price")
    if outcome.get("base_trade_date"):
        row["base_trade_date"] = outcome.get("base_trade_date")
    row["outcome_available"] = bool(outcome.get("outcome_available"))
    row["outcome_source"] = outcome.get("outcome_source")
    row["backfill_version"] = outcome.get("backfill_version") or row.get("backfill_version")
    return row


def _result_rows(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = raw.get("results_sorted")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    scan_result = raw.get("scan_result") if isinstance(raw.get("scan_result"), dict) else {}
    rows = scan_result.get("results")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _diagnostics(raw: Dict[str, Any]) -> Dict[str, Any]:
    diagnostics = raw.get("diagnostics")
    if isinstance(diagnostics, dict) and diagnostics:
        return diagnostics
    scan_result = raw.get("scan_result") if isinstance(raw.get("scan_result"), dict) else {}
    diagnostics = scan_result.get("diagnostics")
    return diagnostics if isinstance(diagnostics, dict) else {}


def _total_scans(raw: Dict[str, Any], summary: Dict[str, Any], diagnostics: Dict[str, Any], result_count: int) -> int | None:
    scan_result = raw.get("scan_result") if isinstance(raw.get("scan_result"), dict) else {}
    for value in (scan_result.get("total_scans"), summary.get("total_scans")):
        parsed = _safe_int(value)
        if parsed is not None:
            return parsed
    filtered = _safe_int(diagnostics.get("filtered_count"))
    if filtered is not None:
        return int(filtered + result_count)
    return None


def _iter_run_dirs(artifact_dir: Path, limit_runs: int) -> List[Path]:
    if not artifact_dir.exists():
        return []
    run_dirs = [path for path in artifact_dir.iterdir() if path.is_dir() and path.name.startswith("RUN-")]
    run_dirs = sorted(run_dirs, key=lambda path: path.stat().st_mtime, reverse=True)
    if limit_runs > 0:
        run_dirs = run_dirs[:limit_runs]
    return run_dirs


def build_snapshot_rows(
    *,
    artifact_dir: Path,
    shared_dir: Path,
    reject_outcome_csv: Path,
    limit_runs: int,
    market_filter: str,
    scan_mode_filter: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    realized_index = _load_realized_outcomes(shared_dir)
    reject_outcome_index = _load_reject_outcomes(reject_outcome_csv)
    rows: List[Dict[str, Any]] = []
    run_count = 0
    pass_count = 0
    reject_count = 0
    skipped_non_kr = 0
    skipped_mode = 0

    for run_dir in _iter_run_dirs(artifact_dir, limit_runs):
        raw = _load_json(run_dir / "raw_scan_results.json")
        summary = _load_json(run_dir / "scan_pipeline_summary.json")
        if not isinstance(raw, dict) or not isinstance(summary, dict):
            continue
        run_context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
        run_id = _text(summary.get("run_id") or run_dir.name)
        market = _market_from(summary.get("market"))
        scan_mode = _text(summary.get("scan_mode") or "SWING").upper()
        if market not in KR_MARKETS:
            skipped_non_kr += 1
            continue
        if market_filter != "ALL" and market != market_filter:
            skipped_non_kr += 1
            continue
        if scan_mode_filter != "ALL" and scan_mode != scan_mode_filter:
            skipped_mode += 1
            continue
        created_at = _timestamp_text(
            summary.get("created_at")
            or run_context.get("created_at")
            or run_context.get("as_of_date")
            or raw.get("created_at")
        )
        base_trade_date = _date_text(
            summary.get("created_at")
            or run_context.get("as_of_date")
            or run_context.get("created_at")
            or raw.get("created_at")
        )
        diagnostics = _diagnostics(raw)
        result_rows = _result_rows(raw)
        total_scans = _total_scans(raw, summary, diagnostics, len(result_rows))
        filtered_count = _safe_int(diagnostics.get("filtered_count"))
        run_count += 1

        emitted_tickers = set()
        for idx, source_row in enumerate(result_rows, start=1):
            ticker = _ticker(source_row)
            if not ticker:
                continue
            emitted_tickers.add(ticker)
            feature_snapshot = _json_safe(source_row)
            priority_rank = _safe_int(_first_present(source_row, "priority_rank", "rank", "Rank")) or idx
            row = {
                "snapshot_key": f"{run_id}:{ticker}",
                "run_id": run_id,
                "ticker": ticker,
                "stock_name": _first_present(source_row, "stock_name", "name", "Name", "종목명") or ticker,
                "market": _market_from(_first_present(source_row, "market", "market_subtype"), ticker) or market,
                "scan_mode": scan_mode,
                "base_trade_date": base_trade_date,
                "scanned_at": created_at,
                "row_role": "emitted",
                "passed_current_model": True,
                "priority_rank": priority_rank,
                "decision": _first_present(source_row, "decision", "Decision", "strategy"),
                "decision_bucket": _first_present(source_row, "decision_bucket", "selection_lane"),
                "reject_stage": None,
                "reject_reason": None,
                "reject_reason_codes": [],
                "reject_detail_history": [],
                "feature_snapshot": feature_snapshot,
                "feature_origin": _first_present(source_row, "feature_origin") or "raw_scan_results",
                "source_ref": _first_present(source_row, "source_ref") or f"artifact:{run_id}:{ticker}:emitted",
                "total_scans": total_scans,
                "filtered_count": filtered_count,
                "backfill_version": BACKFILL_VERSION,
            }
            row.update(_extract_feature_columns(source_row))
            row = _apply_outcome(row, realized_index.get((run_id, ticker)))
            rows.append(_json_safe(row))
            pass_count += 1

        details_by_symbol = diagnostics.get("reject_details_by_symbol") if isinstance(diagnostics.get("reject_details_by_symbol"), dict) else {}
        reasons_by_symbol = diagnostics.get("reject_reasons_by_symbol") if isinstance(diagnostics.get("reject_reasons_by_symbol"), dict) else {}
        for raw_ticker, detail_list in details_by_symbol.items():
            ticker = _text(raw_ticker).upper()
            if not ticker or ticker in emitted_tickers:
                continue
            if isinstance(detail_list, list):
                history = [item for item in detail_list if isinstance(item, dict)]
            elif isinstance(detail_list, dict):
                history = [detail_list]
            else:
                history = []
            terminal = history[-1] if history else {}
            reason_codes = _normalize_reason_codes(reasons_by_symbol.get(raw_ticker) or terminal.get("reason") or terminal.get("reject_reason"))
            reject_reason = "|".join(reason_codes) if reason_codes else _text(terminal.get("reason") or terminal.get("reject_reason")) or None
            row = {
                "snapshot_key": f"{run_id}:{ticker}",
                "run_id": run_id,
                "ticker": ticker,
                "stock_name": _first_present(terminal, "stock_name", "name", "Name", "종목명") or ticker,
                "market": _market_from(_first_present(terminal, "market", "liquidity_market"), ticker) or market,
                "scan_mode": scan_mode,
                "base_trade_date": base_trade_date,
                "scanned_at": created_at,
                "row_role": "rejected",
                "passed_current_model": False,
                "priority_rank": None,
                "decision": None,
                "decision_bucket": "rejected",
                "reject_stage": _first_present(terminal, "stage", "reject_stage"),
                "reject_reason": reject_reason,
                "reject_reason_codes": reason_codes,
                "reject_detail_history": _json_safe(history),
                "feature_snapshot": _json_safe(terminal),
                "feature_origin": "raw_reject_diagnostics",
                "source_ref": f"artifact:{run_id}:{ticker}:rejected",
                "total_scans": total_scans,
                "filtered_count": filtered_count,
                "backfill_version": BACKFILL_VERSION,
            }
            row.update(_extract_feature_columns(terminal))
            row = _apply_outcome(row, reject_outcome_index.get((run_id, ticker)))
            rows.append(_json_safe(row))
            reject_count += 1

    summary = {
        "version": BACKFILL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(artifact_dir),
        "shared_dir": str(shared_dir),
        "reject_outcome_csv": str(reject_outcome_csv),
        "limit_runs": int(limit_runs),
        "market_filter": market_filter,
        "scan_mode_filter": scan_mode_filter,
        "runs_seen": run_count,
        "rows_built": len(rows),
        "emitted_rows": pass_count,
        "rejected_rows": reject_count,
        "outcome_available_rows": sum(1 for row in rows if row.get("outcome_available")),
        "skipped_non_kr_or_market": skipped_non_kr,
        "skipped_scan_mode": skipped_mode,
        "by_market": dict(Counter(str(row.get("market") or "") for row in rows)),
        "by_scan_mode": dict(Counter(str(row.get("scan_mode") or "") for row in rows)),
        "by_role": dict(Counter(str(row.get("row_role") or "") for row in rows)),
        "top_reject_reasons": dict(Counter(str(row.get("reject_reason") or "") for row in rows if row.get("row_role") == "rejected").most_common(12)),
        "realized_outcome_index_keys": len(realized_index),
        "reject_outcome_index_keys": len(reject_outcome_index),
    }
    return rows, summary


def write_local_outputs(rows: List[Dict[str, Any]], csv_path: Path, report_path: Path, summary: Dict[str, Any]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "snapshot_key",
        "run_id",
        "ticker",
        "stock_name",
        "market",
        "scan_mode",
        "base_trade_date",
        "scanned_at",
        "row_role",
        "passed_current_model",
        "priority_rank",
        "decision",
        "decision_bucket",
        "reject_stage",
        "reject_reason",
        "alpha_score",
        "tech_score",
        "ml_prob",
        "prob_clean",
        "whale_score",
        "decision_score",
        "day_return_pct",
        "volume_ratio",
        "turnover",
        "foreigner_1d",
        "institution_1d",
        "retail_1d",
        "foreigner_3d",
        "institution_3d",
        "retail_3d",
        "foreigner_10d",
        "institution_10d",
        "retail_10d",
        "primary_theme",
        "theme_source",
        "theme_inference_status",
        "kr_universe_role",
        "scanner_timeframe_profile",
        "entry_reference_price",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "max_high_return_1d_pct",
        "max_high_return_3d_pct",
        "max_high_return_5d_pct",
        "outcome_available",
        "outcome_source",
        "source_ref",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    report_payload = {
        **summary,
        "local_csv": str(csv_path),
        "supabase_table": TARGET_TABLE,
        "sample_rows": rows[:10],
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path = report_path.with_suffix(".md")
    md_path.write_text(_markdown_report(report_payload), encoding="utf-8")


def _markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Scan Universe Snapshot Backfill",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- runs_seen: `{report.get('runs_seen')}`",
        f"- rows_built: `{report.get('rows_built')}`",
        f"- emitted_rows: `{report.get('emitted_rows')}`",
        f"- rejected_rows: `{report.get('rejected_rows')}`",
        f"- outcome_available_rows: `{report.get('outcome_available_rows')}`",
        f"- supabase_rows_upserted: `{report.get('supabase_rows_upserted', 0)}`",
        f"- supabase_table: `{report.get('supabase_table')}`",
        f"- local_csv: `{report.get('local_csv')}`",
        "",
        "## Distribution",
        f"- by_market: `{report.get('by_market')}`",
        f"- by_scan_mode: `{report.get('by_scan_mode')}`",
        f"- by_role: `{report.get('by_role')}`",
        "",
        "## Top Reject Reasons",
    ]
    for reason, count in (report.get("top_reject_reasons") or {}).items():
        lines.append(f"- `{reason or 'UNKNOWN'}`: `{count}`")
    return "\n".join(lines) + "\n"


def upsert_supabase(rows: List[Dict[str, Any]], *, batch_size: int) -> int:
    if not rows:
        return 0
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")

    upserted = 0
    now_ts = datetime.now(timezone.utc).isoformat()
    for start in range(0, len(rows), max(1, int(batch_size))):
        batch = []
        for row in rows[start:start + max(1, int(batch_size))]:
            payload = dict(row)
            payload["updated_at"] = now_ts
            batch.append(_json_safe(payload))
        db.client.table(TARGET_TABLE).upsert(batch, on_conflict="snapshot_key").execute()
        upserted += len(batch)
        print(f"[INFO] upserted {upserted}/{len(rows)} into {TARGET_TABLE}", flush=True)
    return upserted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--shared-dir", default=str(DEFAULT_SHARED_DIR))
    parser.add_argument("--reject-outcomes-csv", default=str(DEFAULT_REJECT_OUTCOME_CSV))
    parser.add_argument("--limit-runs", type=int, default=0, help="0 means all RUN-* artifacts.")
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    rows, summary = build_snapshot_rows(
        artifact_dir=Path(args.artifact_dir),
        shared_dir=Path(args.shared_dir),
        reject_outcome_csv=Path(args.reject_outcomes_csv),
        limit_runs=int(args.limit_runs),
        market_filter=str(args.market),
        scan_mode_filter=str(args.scan_mode),
    )
    summary["dry_run"] = bool(args.dry_run)
    summary["write_db"] = bool(args.write_db)
    if args.write_db and not args.dry_run:
        summary["supabase_rows_upserted"] = upsert_supabase(rows, batch_size=int(args.batch_size))
    else:
        summary["supabase_rows_upserted"] = 0
    write_local_outputs(rows, Path(args.output_csv), Path(args.report_json), summary)
    print(json.dumps({k: summary.get(k) for k in (
        "runs_seen",
        "rows_built",
        "emitted_rows",
        "rejected_rows",
        "outcome_available_rows",
        "supabase_rows_upserted",
        "by_market",
        "by_scan_mode",
        "by_role",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
