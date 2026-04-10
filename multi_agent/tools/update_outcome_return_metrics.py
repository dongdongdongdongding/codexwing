from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

HORIZONS = (1, 2, 3, 5, 7)
INTRADAY_MINUTE_HORIZONS = ((30, "return_30m_pct"), (60, "return_1h_pct"))
KR_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")

try:
    import FinanceDataReader as fdr  # type: ignore
except Exception:  # pragma: no cover
    fdr = None


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _infer_market(row: Dict[str, Any], run_market: str = "") -> str:
    ticker = str(row.get("ticker") or "").upper()
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return str(run_market or "NASDAQ").upper()


def _market_tz(market: str) -> ZoneInfo:
    return KR_TZ if market in {"KOSPI", "KOSDAQ"} else US_TZ


def _recommended_trade_date(row: Dict[str, Any], market: str) -> Optional[datetime.date]:
    rec_dt = _parse_iso(row.get("recommended_at"))
    if rec_dt is None:
        return None
    return rec_dt.astimezone(_market_tz(market)).date()


def _fetch_history(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    source_ticker = str(ticker or "").strip()
    if not source_ticker:
        return None
    if (source_ticker.endswith(".KS") or source_ticker.endswith(".KQ")) and fdr is not None:
        try:
            hist = fdr.DataReader(source_ticker.split(".")[0], start, end)
            if hist is not None and not hist.empty:
                hist = hist.copy()
                hist["trade_date"] = hist.index.date
                return hist
        except Exception:
            pass
    try:
        hist = yf.Ticker(source_ticker).history(start=start, end=end, auto_adjust=False, timeout=10)
        if hist is None or hist.empty:
            return None
        hist = hist.copy()
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        hist["trade_date"] = hist.index.date
        return hist
    except Exception:
        return None


def _fetch_intraday_history(ticker: str, start_dt: datetime, end_dt: datetime, interval: str = "30m") -> Optional[pd.DataFrame]:
    source_ticker = str(ticker or "").strip()
    if not source_ticker:
        return None
    try:
        hist = yf.Ticker(source_ticker).history(
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            interval=interval,
            auto_adjust=False,
            timeout=10,
            prepost=False,
        )
        if hist is None or hist.empty:
            return None
        hist = hist.copy()
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        return hist.sort_index()
    except Exception:
        return None


def _iter_runs(shared_dir: Path, run_ids: List[str], limit_runs: int) -> List[Path]:
    if run_ids:
        return [shared_dir / rid for rid in run_ids if (shared_dir / rid).exists()]
    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")] if shared_dir.exists() else []
    runs = sorted(runs, key=lambda p: p.name)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        if pd.isna(out):
            return None
        return out
    except Exception:
        return None


def _compute_intraday_row_returns(row: Dict[str, Any], market: str) -> bool:
    if str(row.get("scan_mode", "SWING")).upper() != "INTRADAY":
        return False
    rec_dt = _parse_iso(row.get("recommended_at"))
    entry_price = _safe_float(row.get("entry_reference_price"))
    if rec_dt is None or entry_price is None or entry_price <= 0:
        return False

    market_tz = _market_tz(market)
    rec_local = rec_dt.astimezone(market_tz)
    start_dt = rec_local.astimezone(timezone.utc) - timedelta(hours=2)
    end_dt = (rec_local + timedelta(days=2)).astimezone(timezone.utc)
    intraday_hist = _fetch_intraday_history(str(row.get("ticker") or ""), start_dt=start_dt, end_dt=end_dt, interval="30m")
    changed = False

    if intraday_hist is not None and not intraday_hist.empty:
        local_idx = intraday_hist.index.tz_convert(market_tz)
        intraday_hist = intraday_hist.copy()
        intraday_hist["local_ts"] = local_idx
        same_day = intraday_hist[local_idx.date == rec_local.date()]
        if not same_day.empty:
            for minutes, key in INTRADAY_MINUTE_HORIZONS:
                target_dt = rec_local + timedelta(minutes=minutes)
                eligible = same_day[same_day["local_ts"] >= target_dt]
                value = None
                if not eligible.empty:
                    close_val = _safe_float(eligible["Close"].iloc[0])
                    if close_val is not None and entry_price > 0:
                        value = round(((close_val / entry_price) - 1.0) * 100.0, 6)
                if row.get(key) != value:
                    row[key] = value
                    changed = True

            close_rows = same_day.sort_values("local_ts")
            close_value = None
            if not close_rows.empty:
                close_val = _safe_float(close_rows["Close"].iloc[-1])
                if close_val is not None and entry_price > 0:
                    close_value = round(((close_val / entry_price) - 1.0) * 100.0, 6)
            if row.get("return_close_pct") != close_value:
                row["return_close_pct"] = close_value
                changed = True

    if changed:
        row["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def _compute_row_returns(row: Dict[str, Any], hist: pd.DataFrame, market: str) -> bool:
    trade_date = _recommended_trade_date(row, market)
    if trade_date is None or hist is None or hist.empty:
        return False
    eligible = hist[hist["trade_date"] >= trade_date]
    if eligible.empty:
        return False
    base_idx = eligible.index[0]
    base_pos = int(hist.index.get_loc(base_idx))
    base_close = pd.to_numeric(hist["Close"], errors="coerce").iloc[base_pos]
    if pd.isna(base_close) or float(base_close) <= 0:
        return False

    changed = False
    base_trade_date = str(hist.loc[base_idx, "trade_date"])
    if row.get("base_trade_date") != base_trade_date:
        row["base_trade_date"] = base_trade_date
        changed = True
    if row.get("entry_reference_price") != round(float(base_close), 6):
        row["entry_reference_price"] = round(float(base_close), 6)
        changed = True

    closes = pd.to_numeric(hist["Close"], errors="coerce")
    for horizon in HORIZONS:
        key = f"return_{horizon}d_pct"
        target_pos = base_pos + horizon
        value = None
        if target_pos < len(hist):
            close_val = closes.iloc[target_pos]
            if pd.notna(close_val) and float(base_close) > 0:
                value = round(((float(close_val) / float(base_close)) - 1.0) * 100.0, 6)
        if row.get(key) != value:
            row[key] = value
            changed = True

    latest_close = closes.iloc[-1] if len(closes) > 0 else None
    latest_trade_date = hist["trade_date"].iloc[-1] if len(hist) > 0 else None
    latest_return = None
    if latest_close is not None and pd.notna(latest_close) and float(base_close) > 0:
        latest_return = round(((float(latest_close) / float(base_close)) - 1.0) * 100.0, 6)
    if row.get("latest_return_pct") != latest_return:
        row["latest_return_pct"] = latest_return
        changed = True
    latest_trade_date_str = str(latest_trade_date) if latest_trade_date is not None else None
    if row.get("latest_trade_date") != latest_trade_date_str:
        row["latest_trade_date"] = latest_trade_date_str
        changed = True
    if changed:
        row["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return changed


def run_update(shared_dir: Path, run_ids: List[str], limit_runs: int, dry_run: bool) -> Dict[str, Any]:
    targets = _iter_runs(shared_dir=shared_dir, run_ids=run_ids, limit_runs=limit_runs)
    ticker_windows: Dict[str, Dict[str, Any]] = {}
    run_payloads: List[tuple[Path, Dict[str, Any], str]] = []

    for run_dir in targets:
        payload = _load_json(run_dir / "realized_outcomes.json")
        if not payload:
            continue
        scanner_payload = _load_json(run_dir / "scanner_handoff.json")
        run_ctx = scanner_payload.get("run_context", {}) if isinstance(scanner_payload.get("run_context"), dict) else {}
        run_market = str(run_ctx.get("market", "")).upper()
        summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload.get("summary"), dict) else {}
        input_meta = summary.get("input_meta", {}) if isinstance(summary.get("input_meta"), dict) else {}
        run_scan_mode = str(input_meta.get("scan_mode") or summary.get("scan_mode") or "SWING").upper()
        run_payloads.append((run_dir, payload, run_market, run_scan_mode))
        for row in payload.get("outcomes", []):
            if not isinstance(row, dict):
                continue
            if row.get("scan_mode") != run_scan_mode:
                row["scan_mode"] = run_scan_mode
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            market = _infer_market(row, run_market=run_market)
            trade_date = _recommended_trade_date(row, market)
            if trade_date is None:
                continue
            state = ticker_windows.setdefault(
                ticker,
                {
                    "market": market,
                    "start": trade_date,
                    "end": trade_date + timedelta(days=14),
                },
            )
            if trade_date < state["start"]:
                state["start"] = trade_date
            if trade_date + timedelta(days=14) > state["end"]:
                state["end"] = trade_date + timedelta(days=14)

    history_map: Dict[str, pd.DataFrame] = {}
    for ticker, state in ticker_windows.items():
        hist = _fetch_history(
            ticker=ticker,
            start=(state["start"] - timedelta(days=7)).isoformat(),
            end=(max(state["end"], datetime.now().date() + timedelta(days=2))).isoformat(),
        )
        if hist is not None and not hist.empty:
            history_map[ticker] = hist

    stats = {
        "runs_seen": len(targets),
        "runs_with_file": 0,
        "rows_seen": 0,
        "rows_updated": 0,
        "files_updated": 0,
        "tickers_with_history": len(history_map),
        "db_rows_upserted": 0,
        "scan_archive_rows_synced": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "run_stats": [],
    }
    db = None
    try:
        from modules.db_manager import DBManager

        db = DBManager()
    except Exception:
        db = None

    for run_dir, payload, run_market, run_scan_mode in run_payloads:
        outcomes = payload.get("outcomes", []) if isinstance(payload.get("outcomes"), list) else []
        if not outcomes:
            continue
        stats["runs_with_file"] += 1
        changed = False
        updated_rows = 0
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            stats["rows_seen"] += 1
            ticker = str(row.get("ticker") or "").strip()
            market = _infer_market(row, run_market=run_market)
            hist = history_map.get(ticker)
            if hist is None:
                continue
            row_changed = False
            if _compute_row_returns(row, hist, market):
                row_changed = True
            if _compute_intraday_row_returns(row, market):
                row_changed = True
            if row_changed:
                changed = True
                updated_rows += 1
                stats["rows_updated"] += 1

        if changed and not dry_run:
            payload["summary"] = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
            payload["summary"]["performance_last_updated_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(run_dir / "realized_outcomes.json", payload)
            stats["files_updated"] += 1
        if not dry_run and db is not None and getattr(db, "client", None) is not None:
            try:
                db.save_agent_run_summary(
                    {
                        "run_id": run_dir.name,
                        "market": run_market,
                        "strategy_version": "outcome-return-sync",
                        "model_version": "outcome-return-sync",
                        "code_version": "outcome-return-sync",
                        "artifact_refs": {},
                    }
                )
            except Exception:
                pass
            try:
                stats["db_rows_upserted"] += int(db.save_agent_realized_outcomes(run_dir.name, outcomes) or 0)
            except Exception:
                pass
            try:
                stats["scan_archive_rows_synced"] += int(db.upsert_scan_archive_outcomes(run_dir.name, run_market, outcomes) or 0)
            except Exception:
                pass
        stats["run_stats"].append({"run_id": run_dir.name, "updated_rows": updated_rows, "changed": changed})

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Update realized outcome rows with 1/2/3/5 day return metrics.")
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working")
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--limit-runs", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_update(
        shared_dir=Path(args.shared_dir),
        run_ids=list(args.run_id or []),
        limit_runs=int(args.limit_runs),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
