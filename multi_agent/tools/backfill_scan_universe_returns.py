#!/usr/bin/env python3
"""Backfill forward returns for scan_universe_snapshots.

The scan_universe_snapshots table contains every emitted and rejected symbol.
This tool attaches 1/3/5 trading-day close returns plus 1/3/5 day max-high
returns without using market_scan_results as the source of truth.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_TABLE = "scan_universe_snapshots"
BACKFILL_VERSION = "scan_universe_forward_returns_v1"
DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "scan_universe_return_backfill.json"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "runtime_state" / "artifacts"
RETURN_COLUMNS = (
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
)
HORIZONS = (1, 3, 5)


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


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    return text[:10]


def _parse_date(value: Any) -> date | None:
    text = _date_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_run_date_index(artifact_dir: Path) -> Dict[str, str]:
    index: Dict[str, str] = {}
    if not artifact_dir.exists():
        return index
    for run_dir in artifact_dir.glob("RUN-*"):
        if not run_dir.is_dir():
            continue
        summary = _load_json(run_dir / "scan_pipeline_summary.json")
        raw = _load_json(run_dir / "raw_scan_results.json")
        summary = summary if isinstance(summary, dict) else {}
        raw = raw if isinstance(raw, dict) else {}
        run_context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
        run_id = str(summary.get("run_id") or run_context.get("run_id") or run_dir.name).strip()
        base = _date_text(
            summary.get("created_at")
            or run_context.get("as_of_date")
            or run_context.get("created_at")
            or raw.get("created_at")
        )
        if run_id and base:
            index[run_id] = base
    return index


def _resolved_base_date(row: Dict[str, Any], run_date_index: Dict[str, str] | None = None) -> date | None:
    return (
        _parse_date(row.get("base_trade_date"))
        or _parse_date(row.get("scanned_at"))
        or _parse_date((run_date_index or {}).get(str(row.get("run_id") or "").strip()))
    )


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


def _ticker_code(ticker: str) -> str:
    return str(ticker or "").strip().split(".")[0]


class _FetchTimeout(RuntimeError):
    pass


def _run_with_timeout(seconds: float, fn):
    if seconds <= 0:
        return fn()
    previous = signal.getsignal(signal.SIGALRM)

    def _handler(_signum, _frame):
        raise _FetchTimeout("price_fetch_timeout")

    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class PriceHistoryProvider:
    def __init__(self, *, provider: str = "fdr", sleep_sec: float = 0.0, fetch_timeout: float = 12.0) -> None:
        self.provider = str(provider or "fdr").lower()
        self.sleep_sec = max(0.0, float(sleep_sec or 0.0))
        self.fetch_timeout = max(0.0, float(fetch_timeout or 0.0))
        self.cache: Dict[tuple[str, str, str], List[Dict[str, Any]]] = {}
        self.fetch_counts: Counter[str] = Counter()
        self.fetch_failures: Counter[str] = Counter()
        try:
            import FinanceDataReader as fdr  # type: ignore
        except Exception:
            fdr = None
        try:
            import yfinance as yf  # type: ignore
        except Exception:
            yf = None
        self.fdr = fdr
        self.yf = yf

    def fetch(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        key = (str(ticker), str(start), str(end))
        if key in self.cache:
            return self.cache[key]
        rows: List[Dict[str, Any]] = []
        if self.provider in {"fdr", "auto"}:
            rows = self._fetch_fdr(ticker, start, end)
        if not rows and self.provider in {"yf", "yfinance", "auto", "fdr"}:
            rows = self._fetch_yfinance(ticker, start, end)
        self.cache[key] = rows
        if self.sleep_sec > 0:
            import time

            time.sleep(self.sleep_sec)
        return rows

    def _fetch_fdr(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        if self.fdr is None:
            self.fetch_failures["fdr_unavailable"] += 1
            return []
        try:
            hist = _run_with_timeout(
                self.fetch_timeout,
                lambda: self.fdr.DataReader(_ticker_code(ticker), start, end),
            )
        except _FetchTimeout:
            self.fetch_failures["fdr_timeout"] += 1
            return []
        except Exception:
            self.fetch_failures["fdr_exception"] += 1
            return []
        if hist is None or hist.empty:
            self.fetch_failures["fdr_empty"] += 1
            return []
        self.fetch_counts["fdr"] += 1
        return _history_frame_to_bars(hist)

    def _fetch_yfinance(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        if self.yf is None:
            self.fetch_failures["yf_unavailable"] += 1
            return []
        try:
            hist = _run_with_timeout(
                self.fetch_timeout,
                lambda: self.yf.Ticker(str(ticker)).history(start=start, end=end, auto_adjust=False, timeout=10),
            )
        except _FetchTimeout:
            self.fetch_failures["yf_timeout"] += 1
            return []
        except Exception:
            self.fetch_failures["yf_exception"] += 1
            return []
        if hist is None or hist.empty:
            self.fetch_failures["yf_empty"] += 1
            return []
        self.fetch_counts["yfinance"] += 1
        return _history_frame_to_bars(hist)


def _history_frame_to_bars(hist: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if hist is None or getattr(hist, "empty", True):
        return rows
    for idx, item in hist.iterrows():
        try:
            trade_date = idx.date().isoformat()
        except Exception:
            trade_date = str(idx)[:10]
        close = _safe_float(item.get("Close"))
        high = _safe_float(item.get("High"))
        if not trade_date or close is None:
            continue
        rows.append({"date": trade_date, "close": close, "high": high if high is not None else close})
    rows.sort(key=lambda row: str(row.get("date") or ""))
    return rows


def _row_needs_backfill(row: Dict[str, Any], *, overwrite: bool) -> bool:
    if overwrite:
        return True
    return any(row.get(col) is None for col in RETURN_COLUMNS)


def _compute_return_payload(
    row: Dict[str, Any],
    bars: Sequence[Dict[str, Any]],
    *,
    overwrite: bool,
    run_date_index: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    base = _resolved_base_date(row, run_date_index)
    if base is None:
        return {}
    eligible = [bar for bar in bars if _parse_date(bar.get("date")) and _parse_date(bar.get("date")) >= base]
    if not eligible:
        return {}
    entry_bar = eligible[0]
    entry = _safe_float(row.get("entry_reference_price"))
    if entry is None or entry <= 0:
        entry = _safe_float(entry_bar.get("close"))
    if entry is None or entry <= 0:
        return {}
    future = eligible[1:]
    payload: Dict[str, Any] = {}
    for horizon in HORIZONS:
        ret_col = f"return_{horizon}d_pct"
        high_col = f"max_high_return_{horizon}d_pct"
        if len(future) >= horizon:
            close = _safe_float(future[horizon - 1].get("close"))
            if close is not None and (overwrite or row.get(ret_col) is None):
                payload[ret_col] = round((close - entry) / entry * 100.0, 6)
            highs = [_safe_float(bar.get("high")) for bar in future[:horizon]]
            highs = [value for value in highs if value is not None]
            if highs and (overwrite or row.get(high_col) is None):
                payload[high_col] = round((max(highs) - entry) / entry * 100.0, 6)
    if payload:
        payload["base_trade_date"] = base.isoformat()
        payload["entry_reference_price"] = entry
        payload["outcome_available"] = True
        payload["outcome_source"] = "scan_universe_price_history"
        payload["backfill_version"] = BACKFILL_VERSION
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def fetch_snapshot_rows(*, market: str, scan_mode: str, page_size: int) -> List[Dict[str, Any]]:
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    cols = (
        "id,snapshot_key,run_id,ticker,market,scan_mode,row_role,base_trade_date,scanned_at,entry_reference_price,"
        "return_1d_pct,return_3d_pct,return_5d_pct,"
        "max_high_return_1d_pct,max_high_return_3d_pct,max_high_return_5d_pct"
    )
    rows: List[Dict[str, Any]] = []
    page = 0
    while True:
        query = db.client.table(TARGET_TABLE).select(cols).order("id").range(page * page_size, page * page_size + page_size - 1)
        if market != "ALL":
            query = query.eq("market", market)
        if scan_mode != "ALL":
            query = query.eq("scan_mode", scan_mode)
        batch = query.execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return rows


def build_updates(
    rows: Iterable[Dict[str, Any]],
    *,
    provider: PriceHistoryProvider,
    overwrite: bool,
    max_tickers: int,
    run_date_index: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    run_date_index = run_date_index or {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    repaired_base_date_candidates = 0
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        if not ticker or not _row_needs_backfill(row, overwrite=overwrite):
            continue
        base_date = _resolved_base_date(row, run_date_index)
        if base_date is None:
            continue
        if not row.get("base_trade_date"):
            repaired_base_date_candidates += 1
        grouped[ticker].append(row)

    tickers = sorted(grouped)
    if max_tickers and max_tickers > 0:
        tickers = tickers[:max_tickers]

    updates: List[Dict[str, Any]] = []
    no_history = 0
    no_payload = 0
    by_market: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    for idx, ticker in enumerate(tickers, start=1):
        ticker_rows = grouped[ticker]
        dates = [_resolved_base_date(row, run_date_index) for row in ticker_rows]
        dates = [item for item in dates if item is not None]
        if not dates:
            no_payload += len(ticker_rows)
            continue
        start = (min(dates) - timedelta(days=3)).isoformat()
        end = (max(dates) + timedelta(days=14)).isoformat()
        bars = provider.fetch(ticker, start, end)
        if not bars:
            no_history += len(ticker_rows)
            continue
        for row in ticker_rows:
            payload = _compute_return_payload(row, bars, overwrite=overwrite, run_date_index=run_date_index)
            if not payload:
                no_payload += 1
                continue
            payload["id"] = row.get("id")
            payload["snapshot_key"] = row.get("snapshot_key")
            payload["run_id"] = row.get("run_id")
            payload["ticker"] = row.get("ticker")
            updates.append(_json_safe(payload))
            by_market[str(row.get("market") or "")] += 1
            by_role[str(row.get("row_role") or "")] += 1
        if idx % 100 == 0:
            print(f"[INFO] priced {idx}/{len(tickers)} tickers, updates={len(updates)}", flush=True)

    return {
        "updates": updates,
        "ticker_count": len(tickers),
        "candidate_rows": sum(len(grouped[ticker]) for ticker in tickers),
        "no_history_rows": no_history,
        "no_payload_rows": no_payload,
        "updates_by_market": dict(by_market),
        "updates_by_role": dict(by_role),
        "repaired_base_date_candidates": repaired_base_date_candidates,
        "price_fetch_counts": dict(provider.fetch_counts),
        "price_fetch_failures": dict(provider.fetch_failures),
    }


def upsert_updates(updates: List[Dict[str, Any]], *, batch_size: int) -> int:
    if not updates:
        return 0
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    writable = set(RETURN_COLUMNS) | {
        "base_trade_date",
        "entry_reference_price",
        "outcome_available",
        "outcome_source",
        "backfill_version",
        "updated_at",
    }
    written = 0
    for item in updates:
        row_id = item.get("id")
        if row_id is None:
            continue
        payload = {key: value for key, value in item.items() if key in writable}
        if not payload:
            continue
        db.client.table(TARGET_TABLE).update(payload).eq("id", row_id).execute()
        written += 1
        if written % max(1, int(batch_size)) == 0 or written == len(updates):
            print(f"[INFO] updated returns {written}/{len(updates)}", flush=True)
    return written


def _write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Scan Universe Return Backfill",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- candidate_rows: `{report.get('candidate_rows')}`",
        f"- ticker_count: `{report.get('ticker_count')}`",
        f"- updates_built: `{report.get('updates_built')}`",
        f"- rows_written: `{report.get('rows_written')}`",
        f"- dry_run: `{report.get('dry_run')}`",
        f"- overwrite: `{report.get('overwrite')}`",
        f"- no_history_rows: `{report.get('no_history_rows')}`",
        f"- no_payload_rows: `{report.get('no_payload_rows')}`",
        f"- repaired_base_date_candidates: `{report.get('repaired_base_date_candidates')}`",
        f"- run_date_index_size: `{report.get('run_date_index_size')}`",
        "",
        "## Distribution",
        f"- updates_by_market: `{report.get('updates_by_market')}`",
        f"- updates_by_role: `{report.get('updates_by_role')}`",
        f"- price_fetch_counts: `{report.get('price_fetch_counts')}`",
        f"- price_fetch_failures: `{report.get('price_fetch_failures')}`",
    ]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--provider", choices=["fdr", "yfinance", "auto"], default="fdr")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--fetch-timeout", type=float, default=12.0)
    parser.add_argument("--max-tickers", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    args = parser.parse_args()

    rows = fetch_snapshot_rows(market=args.market, scan_mode=args.scan_mode, page_size=max(1, int(args.page_size)))
    run_date_index = _load_run_date_index(Path(args.artifact_dir))
    provider = PriceHistoryProvider(
        provider=args.provider,
        sleep_sec=float(args.sleep or 0.0),
        fetch_timeout=float(args.fetch_timeout or 0.0),
    )
    result = build_updates(
        rows,
        provider=provider,
        overwrite=bool(args.overwrite),
        max_tickers=int(args.max_tickers or 0),
        run_date_index=run_date_index,
    )
    updates = result.pop("updates")
    rows_written = 0 if args.dry_run else upsert_updates(updates, batch_size=max(1, int(args.batch_size)))
    report = {
        "version": BACKFILL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(rows),
        "updates_built": len(updates),
        "rows_written": rows_written,
        "dry_run": bool(args.dry_run),
        "overwrite": bool(args.overwrite),
        "market": args.market,
        "scan_mode": args.scan_mode,
        "run_date_index_size": len(run_date_index),
        **result,
        "sample_updates": updates[:10],
    }
    _write_report(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BACKFILL_VERSION",
    "PriceHistoryProvider",
    "_compute_return_payload",
    "build_updates",
    "fetch_snapshot_rows",
]
