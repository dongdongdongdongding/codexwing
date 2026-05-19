from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List


BACKFILL_VERSION = "kr_rejected_symbol_outcome_backfill_v1"
DEFAULT_REJECT_OUTCOME_CSV = Path("runtime_state/reports/validation/kr_rejected_symbol_outcomes.csv")
DEFAULT_REJECT_OUTCOME_JSON = Path("runtime_state/reports/validation/kr_rejected_symbol_outcomes.json")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        numeric = float(str(value).replace(",", "").replace("%", "").strip())
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _ticker(row: Dict[str, Any]) -> str:
    return _text(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커")).upper()


def _market(row: Dict[str, Any]) -> str:
    market = _text(row.get("market") or row.get("liquidity_market")).upper()
    ticker = _ticker(row)
    if market in {"KOSPI", "KOSDAQ"}:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return market


def _base_date(row: Dict[str, Any]) -> str:
    return _text(row.get("base_trade_date") or row.get("as_of_date") or row.get("created_at"))[:10]


def _join_reasons(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(item) for item in value if item)
    return str(value)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except Exception:
        return None


def load_existing_reject_outcomes(path: Path = DEFAULT_REJECT_OUTCOME_CSV) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def dedupe_reject_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        ticker = _ticker(row)
        market = _market(row)
        base_date = _base_date(row)
        if market not in {"KOSPI", "KOSDAQ"} or not ticker or not base_date:
            continue
        key = (_text(row.get("run_id")), ticker, base_date)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "run_id": _text(row.get("run_id")),
                "ticker": ticker,
                "market": market,
                "base_trade_date": base_date,
                "stock_name": row.get("stock_name") or row.get("name"),
                "entry_reference_price": _num(row.get("curr_price") or row.get("entry_reference_price")),
                "reject_stage": row.get("reject_stage") or row.get("stage"),
                "reject_reason": _join_reasons(row.get("reject_reasons")),
                "turnover": _num(row.get("turnover")),
                "emitted": False,
            }
        )
    return out


def compute_forward_returns(row: Dict[str, Any], price_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    base = _parse_date(_base_date(row))
    prices = []
    for item in price_rows or []:
        if not isinstance(item, dict):
            continue
        dt = _parse_date(_text(item.get("date")))
        close = _num(item.get("close"))
        high = _num(item.get("high"))
        if dt is None or close is None:
            continue
        if base is None or dt.date() >= base.date():
            prices.append({"date": dt, "close": close, "high": high if high is not None else close})
    prices = sorted(prices, key=lambda item: item["date"])
    entry = _num(row.get("entry_reference_price"))
    if entry is None and prices:
        entry = prices[0]["close"]
    result = {**row, "backfill_version": BACKFILL_VERSION, "outcome_available": False}
    if entry is None or entry <= 0 or len(prices) < 2:
        result["backfill_status"] = "price_history_unavailable"
        return result
    future = prices[1:]
    result["outcome_available"] = True
    result["backfill_status"] = "ok"
    result["entry_reference_price"] = entry
    for horizon in (1, 3, 5):
        if len(future) >= horizon:
            close = future[horizon - 1]["close"]
            result[f"return_{horizon}d_pct"] = round((close - entry) / entry * 100.0, 6)
            high = max(item["high"] for item in future[:horizon])
            result[f"max_high_return_{horizon}d_pct"] = round((high - entry) / entry * 100.0, 6)
        else:
            result[f"return_{horizon}d_pct"] = None
            result[f"max_high_return_{horizon}d_pct"] = None
    return result


PriceProvider = Callable[[str, str, str], List[Dict[str, Any]]]


def backfill_reject_outcomes(
    reject_rows: Iterable[Dict[str, Any]],
    *,
    price_provider: PriceProvider,
    existing_rows: Iterable[Dict[str, Any]] | None = None,
    max_rows: int | None = None,
) -> List[Dict[str, Any]]:
    existing = {
        (_text(row.get("run_id")), _ticker(row), _text(row.get("base_trade_date"))): row
        for row in existing_rows or []
        if isinstance(row, dict) and _ticker(row)
    }
    rows = dedupe_reject_rows(reject_rows)
    if max_rows is not None:
        rows = rows[: max(0, int(max_rows))]
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = (_text(row.get("run_id")), _ticker(row), _text(row.get("base_trade_date")))
        if key in existing and existing[key].get("outcome_available") in {True, "True", "true", "1"}:
            out.append(existing[key])
            continue
        start_dt = _parse_date(str(row.get("base_trade_date")))
        end = (start_dt + timedelta(days=12)).strftime("%Y-%m-%d") if start_dt else ""
        history = price_provider(str(row.get("ticker")), str(row.get("base_trade_date")), end)
        out.append(compute_forward_returns(row, history))
    return out


def write_reject_outcomes(rows: List[Dict[str, Any]], csv_path: Path = DEFAULT_REJECT_OUTCOME_CSV) -> Dict[str, Any]:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "ticker",
        "market",
        "base_trade_date",
        "stock_name",
        "entry_reference_price",
        "reject_stage",
        "reject_reason",
        "turnover",
        "emitted",
        "outcome_available",
        "backfill_status",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "max_high_return_1d_pct",
        "max_high_return_3d_pct",
        "max_high_return_5d_pct",
        "backfill_version",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    json_path = csv_path.with_suffix(".json")
    payload = {
        "version": BACKFILL_VERSION,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "csv_path": str(csv_path),
        "rows": len(rows),
        "outcome_available_rows": sum(1 for row in rows if _truthy(row.get("outcome_available"))),
        "rows_sample": rows[:20],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload


__all__ = [
    "BACKFILL_VERSION",
    "DEFAULT_REJECT_OUTCOME_CSV",
    "DEFAULT_REJECT_OUTCOME_JSON",
    "backfill_reject_outcomes",
    "compute_forward_returns",
    "dedupe_reject_rows",
    "load_existing_reject_outcomes",
    "write_reject_outcomes",
]
