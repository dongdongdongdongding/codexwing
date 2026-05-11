#!/usr/bin/env python3
"""Build a paper-trade shadow ledger from real scan outcome rows.

This is intentionally not an order simulator with fabricated fills. The first
operational layer is a close-to-close shadow ledger:

- entry anchor: persisted ``entry_reference_price`` / base close from scan data
- exit path: realized close returns already stored on scan archive rows
- no synthetic prices, no dummy outcomes

Rows without enough realized returns remain ``UNRESOLVED``. Later Supabase
storage can upsert this same schema as-is.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_ARCHIVE = PROJECT_ROOT / "runtime_state" / "reports" / "archive" / "scan_archive_learning_dataset_all.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "trading"
RETURN_HORIZONS = (1, 2, 3, 5, 7, 14, 30)
BUY_DECISIONS = {"PRIORITY_WATCHLIST", "WATCHLIST", "WATCHLIST_ONLY", "EXCEPTION_LEADER"}


@dataclass(frozen=True)
class TradePolicy:
    market: str
    scan_mode: str
    entry_model: str
    target_tp_pct: float
    stop_sl_pct: float
    hold_days: int


DEFAULT_POLICIES: Dict[tuple[str, str], TradePolicy] = {
    ("KOSPI", "SWING"): TradePolicy("KOSPI", "SWING", "close_proxy", 20.0, -5.0, 5),
    ("KOSDAQ", "SWING"): TradePolicy("KOSDAQ", "SWING", "close_proxy", 10.0, -10.0, 5),
}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        result = int(float(value))
        return result
    except Exception:
        return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _is_excluded(series: pd.Series) -> pd.Series:
    if series.dtype == "object":
        return series.fillna("").astype(str).str.lower().isin({"true", "1", "yes"})
    return series.fillna(False).astype(bool)


def resolve_trade_policy(row: Dict[str, Any]) -> TradePolicy:
    market = _text(row.get("market")).upper()
    scan_mode = _text(row.get("scan_mode") or "SWING").upper()
    policy = DEFAULT_POLICIES.get((market, scan_mode), TradePolicy(market, scan_mode, "close_proxy", 7.0, -5.0, 5))
    tp = _safe_float(row.get("target_tp_pct"))
    sl = _safe_float(row.get("stop_sl_pct"))
    hold = _safe_int(row.get("hold_days")) or _safe_int(row.get("target_horizon_days"))
    return TradePolicy(
        market=market,
        scan_mode=scan_mode,
        entry_model=policy.entry_model,
        target_tp_pct=float(tp if tp is not None else policy.target_tp_pct),
        stop_sl_pct=float(sl if sl is not None else policy.stop_sl_pct),
        hold_days=int(hold if hold and hold > 0 else policy.hold_days),
    )


def _return_path(row: Dict[str, Any]) -> List[tuple[int, float]]:
    path: List[tuple[int, float]] = []
    for horizon in RETURN_HORIZONS:
        value = _safe_float(row.get(f"return_{horizon}d_pct"))
        if value is not None:
            path.append((horizon, value))
    return path


def simulate_close_proxy_trade(
    row: Dict[str, Any],
    *,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Dict[str, Any]:
    """Simulate exit on actual stored close returns without fabricating fills."""
    policy = resolve_trade_policy(row)
    trade_id = "|".join(
        [
            _text(row.get("run_id")),
            _text(row.get("ticker")),
            _text(row.get("base_trade_date") or row.get("recommended_at") or row.get("created_at"))[:10],
            _text(row.get("priority_rank")),
        ]
    )
    entry_price = _safe_float(row.get("entry_reference_price"))
    rank = _safe_int(row.get("priority_rank"))
    path = [(day, ret) for day, ret in _return_path(row) if day <= policy.hold_days]
    costs_pct = (float(fee_bps) + float(slippage_bps)) * 2.0 / 100.0

    status = "UNRESOLVED"
    exit_reason = "NO_REALIZED_RETURN"
    exit_day: Optional[int] = None
    gross_return: Optional[float] = None
    if entry_price is None or entry_price <= 0:
        exit_reason = "MISSING_ENTRY_REFERENCE_PRICE"
    elif path:
        status = "CLOSED"
        exit_day = path[-1][0]
        gross_return = path[-1][1]
        exit_reason = "TIME_EXIT"
        for day, ret in path:
            if ret >= policy.target_tp_pct:
                exit_day = day
                gross_return = policy.target_tp_pct
                exit_reason = "TAKE_PROFIT_CLOSE_PROXY"
                break
            if ret <= policy.stop_sl_pct:
                exit_day = day
                gross_return = policy.stop_sl_pct
                exit_reason = "STOP_LOSS_CLOSE_PROXY"
                break

    net_return = None if gross_return is None else round(float(gross_return) - costs_pct, 6)
    return {
        "trade_id": trade_id,
        "ledger_mode": "close_to_close_shadow_v1",
        "ticker": _text(row.get("ticker")),
        "stock_name": _text(row.get("stock_name")),
        "market": policy.market,
        "scan_mode": policy.scan_mode,
        "run_id": _text(row.get("run_id")),
        "priority_rank": rank,
        "decision": _text(row.get("decision")).upper(),
        "decision_bucket": _text(row.get("decision_bucket")).lower(),
        "recommended_at": _text(row.get("recommended_at")),
        "base_trade_date": _text(row.get("base_trade_date")),
        "entry_model": policy.entry_model,
        "entry_reference_price": entry_price,
        "target_tp_pct": policy.target_tp_pct,
        "stop_sl_pct": policy.stop_sl_pct,
        "hold_days": policy.hold_days,
        "exit_day": exit_day,
        "exit_reason": exit_reason,
        "trade_status": status,
        "gross_return_pct": None if gross_return is None else round(float(gross_return), 6),
        "net_return_pct": net_return,
        "fee_bps": float(fee_bps),
        "slippage_bps": float(slippage_bps),
        "relative_rank_score": _safe_float(row.get("relative_rank_score")),
        "loss_risk_score": _safe_float(row.get("loss_risk_score")),
        "relative_rank_model": _text(row.get("relative_rank_model")),
        "source_scan_result_id": _text(row.get("id")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_warnings": _trade_warnings(row, path=path, entry_price=entry_price),
    }


def _trade_warnings(row: Dict[str, Any], *, path: List[tuple[int, float]], entry_price: Optional[float]) -> List[str]:
    warnings: List[str] = []
    if entry_price is None or entry_price <= 0:
        warnings.append("MISSING_ENTRY_REFERENCE_PRICE")
    if not path:
        warnings.append("NO_RETURN_WITHIN_HOLD")
    if not _text(row.get("relative_rank_model")):
        warnings.append("MISSING_RELATIVE_RANK_MODEL")
    return warnings


def load_candidate_rows(
    path: Path,
    *,
    market: str,
    scan_mode: str,
    topn: int,
    exclude_validation_excluded: bool = False,
) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "is_dummy_data" in df.columns:
        df = df[~_is_excluded(df["is_dummy_data"])].copy()
    if exclude_validation_excluded and "validation_excluded" in df.columns:
        df = df[~_is_excluded(df["validation_excluded"])].copy()
    df["market"] = df.get("market", "").fillna("").astype(str).str.upper()
    df["scan_mode"] = df.get("scan_mode", "").fillna("").astype(str).str.upper()
    df["decision"] = df.get("decision", "").fillna("").astype(str).str.upper()
    df["decision_bucket"] = df.get("decision_bucket", "").fillna("").astype(str).str.lower()
    df["priority_rank"] = pd.to_numeric(df.get("priority_rank"), errors="coerce")
    if market != "ALL":
        df = df[df["market"].eq(market)].copy()
    if scan_mode != "ALL":
        df = df[df["scan_mode"].eq(scan_mode)].copy()
    df = df[df["priority_rank"].notna() & df["priority_rank"].between(1, int(topn))].copy()
    df = df[df["decision"].isin(BUY_DECISIONS) | df["decision_bucket"].isin({"picked", "exception_leader"})].copy()
    if "base_trade_date" in df.columns:
        trade_date = df["base_trade_date"].fillna("").astype(str).str[:10]
    else:
        trade_date = pd.Series("", index=df.index)
    fallback = df.get("recommended_at", df.get("created_at", "")).fillna("").astype(str).str[:10]
    df["trade_date"] = trade_date.where(trade_date.str.len().ge(8), fallback)
    df = df.sort_values(["trade_date", "market", "priority_rank", "ticker", "created_at"], na_position="last")
    return df


def build_ledger(
    rows: Iterable[Dict[str, Any]],
    *,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> List[Dict[str, Any]]:
    return [simulate_close_proxy_trade(row, fee_bps=fee_bps, slippage_bps=slippage_bps) for row in rows]


def _metrics(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {
            "n": 0,
            "win_pct": None,
            "avg_pct": None,
            "median_pct": None,
            "max_pct": None,
            "min_pct": None,
            "hit5_pct": None,
            "loss5_pct": None,
        }
    series = pd.Series(clean, dtype="float64")
    return {
        "n": int(len(series)),
        "win_pct": round(float(series.gt(0.0).mean() * 100.0), 2),
        "avg_pct": round(float(series.mean()), 4),
        "median_pct": round(float(series.median()), 4),
        "max_pct": round(float(series.max()), 4),
        "min_pct": round(float(series.min()), 4),
        "hit5_pct": round(float(series.ge(5.0).mean() * 100.0), 2),
        "loss5_pct": round(float(series.le(-5.0).mean() * 100.0), 2),
    }


def summarize_ledger(ledger: List[Dict[str, Any]]) -> Dict[str, Any]:
    df = pd.DataFrame(ledger)
    if df.empty:
        return {"rows": 0, "closed_rows": 0, "unresolved_rows": 0, "mode": "close_to_close_shadow_v1", "groups": []}
    closed = df[df["trade_status"].eq("CLOSED")].copy()
    groups: List[Dict[str, Any]] = []
    for keys in [("market",), ("market", "priority_rank"), ("market", "exit_reason")]:
        if closed.empty:
            continue
        for key, group in closed.groupby(list(keys), dropna=False):
            names = key if isinstance(key, tuple) else (key,)
            item = {keys[idx]: names[idx] for idx in range(len(keys))}
            item.update(_metrics(group["net_return_pct"].dropna().tolist()))
            groups.append(item)
    return {
        "rows": int(len(df)),
        "closed_rows": int(len(closed)),
        "unresolved_rows": int(df["trade_status"].ne("CLOSED").sum()),
        "mode": "close_to_close_shadow_v1",
        "groups": groups,
    }


def _markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Paper Trade Shadow Ledger",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- mode: `{summary['mode']}`",
        f"- ledger_rows: `{summary['rows']}`",
        f"- closed_rows: `{summary['closed_rows']}`",
        f"- unresolved_rows: `{summary['unresolved_rows']}`",
        f"- fee_bps: `{report['fee_bps']}`",
        f"- slippage_bps: `{report['slippage_bps']}`",
        "",
        "## Market Metrics",
    ]
    for row in summary["groups"]:
        if set(row.keys()) >= {"market", "priority_rank"} or set(row.keys()) >= {"market", "exit_reason"}:
            continue
        lines.append(
            f"- {row['market']}: n={row['n']} win={row['win_pct']} avg={row['avg_pct']} "
            f"median={row['median_pct']} max={row['max_pct']} min={row['min_pct']} "
            f"hit5={row['hit5_pct']} loss5={row['loss5_pct']}"
        )
    lines.extend(["", "## Rank Metrics"])
    rank_rows = [r for r in summary["groups"] if "priority_rank" in r]
    rank_rows.sort(key=lambda r: (str(r.get("market")), int(r.get("priority_rank") or 999)))
    for row in rank_rows:
        lines.append(
            f"- {row['market']} rank {int(row['priority_rank'])}: n={row['n']} "
            f"win={row['win_pct']} avg={row['avg_pct']} median={row['median_pct']} "
            f"max={row['max_pct']} min={row['min_pct']}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "- This is a real-data shadow ledger, not a broker fill ledger.",
            "- Rows without realized return data remain unresolved instead of being filled as losses or wins.",
            "- The schema is Supabase-friendly and can be upserted when the execution table is added.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build real-data paper trade shadow ledger from scan archive.")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--fee-bps", type=float, default=0.0)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument(
        "--exclude-validation-excluded",
        action="store_true",
        help="Exclude rows marked validation_excluded. Off by default because live trade ledger must reflect what the UI actually recommended.",
    )
    args = parser.parse_args()

    rows = load_candidate_rows(
        Path(args.archive),
        market=args.market,
        scan_mode=args.scan_mode,
        topn=args.topn,
        exclude_validation_excluded=bool(args.exclude_validation_excluded),
    )
    ledger = build_ledger(rows.to_dict("records"), fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    summary = summarize_ledger(ledger)
    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "generated_at": generated_at,
        "source": str(Path(args.archive)),
        "market": args.market,
        "scan_mode": args.scan_mode,
        "topn": int(args.topn),
        "fee_bps": float(args.fee_bps),
        "slippage_bps": float(args.slippage_bps),
        "summary": summary,
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"paper_trade_ledger_{args.market.lower()}_{args.scan_mode.lower()}_top{args.topn}"
    csv_path = out_dir / f"{stem}.csv"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    pd.DataFrame(ledger).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps({**report, "ledger": ledger[:200]}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"csv_path": str(csv_path), "json_path": str(json_path), "md_path": str(md_path), **summary},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
