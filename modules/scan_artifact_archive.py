from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ARTIFACT_DIR = Path("runtime_state/artifacts")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except Exception:
        return None


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _market_type(market: str) -> str:
    market = str(market or "").upper()
    if market in {"KOSPI", "KOSDAQ", "KR"}:
        return "KR"
    if market in {"NASDAQ", "S&P500", "AMEX", "US"}:
        return "US"
    return market or "UNKNOWN"


def _iter_run_dirs(artifact_dir: Path) -> Iterable[Path]:
    if not artifact_dir.exists():
        return []
    return sorted(
        [path for path in artifact_dir.iterdir() if path.is_dir() and path.name.startswith("RUN-")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def normalize_artifact_scan_row(
    row: Dict[str, Any],
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    created_at: str,
    rank: int,
) -> Dict[str, Any]:
    ticker = str(_first_present(row, "ticker", "Ticker", "symbol", "Symbol", "티커") or "").strip()
    stock_name = str(_first_present(row, "stock_name", "name", "Name", "Stock Name", "종목명") or ticker)
    decision = _first_present(row, "decision", "Decision", "signal_label", "Strategy", "strategy")
    decision_score = _safe_float(_first_present(row, "decision_score", "Decision Score", "buy_score", "Score"))
    alpha_score = _safe_float(_first_present(row, "alpha_score", "Antigrav", "Alpha"))
    day_return = _safe_float(_first_present(row, "day_return_pct", "day_change_pct", "Change %", "전일비"))
    entry = _safe_float(_first_present(row, "entry_reference_price", "Entry Price", "Entry(-2%)", "매수가(-2%)"))
    return {
        **row,
        "ticker": ticker,
        "stock_name": stock_name,
        "name": stock_name,
        "run_id": str(run_id),
        "market": str(market or ""),
        "market_type": _market_type(market),
        "scan_mode": str(scan_mode or "SWING").upper(),
        "created_at": created_at,
        "recommended_at": _first_present(row, "recommended_at") or created_at,
        "base_trade_date": str(created_at)[:10],
        "priority_rank": _safe_int(_first_present(row, "priority_rank", "rank", "Rank")) or rank,
        "decision": str(decision or ""),
        "decision_score": decision_score,
        "alpha_score": alpha_score,
        "day_return_pct": day_return,
        "entry_reference_price": entry,
        "target_tp_pct": _safe_float(_first_present(row, "target_tp_pct")),
        "stop_sl_pct": _safe_float(_first_present(row, "stop_sl_pct")),
        "hold_days": _safe_int(_first_present(row, "hold_days")),
        "feature_origin": _first_present(row, "feature_origin") or "local_scan_artifact",
        "source_ref": _first_present(row, "source_ref") or f"local_artifact:{run_id}:{ticker}",
    }


def load_local_scan_archive_rows(*, artifact_dir: Path = ARTIFACT_DIR, limit_runs: int = 300) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for run_dir in list(_iter_run_dirs(artifact_dir))[: max(1, int(limit_runs or 300))]:
        summary_path = run_dir / "scan_pipeline_summary.json"
        raw_path = run_dir / "raw_scan_results.json"
        summary = _load_json(summary_path)
        raw = _load_json(raw_path)
        if not isinstance(summary, dict) or not isinstance(raw, dict):
            continue
        run_id = str(summary.get("run_id") or run_dir.name)
        market = str(summary.get("market") or "")
        scan_mode = str(summary.get("scan_mode") or "SWING")
        created_at = str(summary.get("created_at") or _mtime_iso(summary_path))
        result_rows = raw.get("results_sorted")
        if not isinstance(result_rows, list):
            scan_result = raw.get("scan_result") if isinstance(raw.get("scan_result"), dict) else {}
            result_rows = scan_result.get("results")
        if not isinstance(result_rows, list):
            continue
        for idx, row in enumerate(result_rows, start=1):
            if not isinstance(row, dict):
                continue
            normalized = normalize_artifact_scan_row(
                row,
                run_id=run_id,
                market=market,
                scan_mode=scan_mode,
                created_at=created_at,
                rank=idx,
            )
            if normalized.get("ticker"):
                rows.append(normalized)
    return rows


def merge_archive_rows_with_local_artifacts(
    db_rows: List[Dict[str, Any]],
    local_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged = list(db_rows or [])
    seen = {
        (str(row.get("run_id") or ""), str(row.get("ticker") or ""))
        for row in merged
        if str(row.get("run_id") or "") and str(row.get("ticker") or "")
    }
    for row in local_rows or []:
        key = (str(row.get("run_id") or ""), str(row.get("ticker") or ""))
        if key[0] and key[1] and key in seen:
            continue
        merged.append(row)
        if key[0] and key[1]:
            seen.add(key)
    return merged


__all__ = [
    "load_local_scan_archive_rows",
    "merge_archive_rows_with_local_artifacts",
    "normalize_artifact_scan_row",
]
