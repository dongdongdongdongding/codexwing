#!/usr/bin/env python3
"""Report KR INTRADAY archive readiness for model learning.

The generic experimental admission loader is SWING-only. This report reads the
raw scan archive export directly, derives KR market/date fields, and measures
whether KOSPI/KOSDAQ INTRADAY rows are mature enough for model work.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT = PROJECT_ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/validation/intraday_learning_readiness.json"
RETURN_COLS = ("return_1d_pct", "return_3d_pct", "return_5d_pct")
MODEL_READY_MIN_ROWS = 300
MODEL_READY_MIN_DAYS = 10
LATEST_DATA_MAX_LAG_DAYS = 3
KST = ZoneInfo("Asia/Seoul")


def _safe_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(float("nan"), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def _derive_market(ticker: pd.Series, market: pd.Series) -> pd.Series:
    ticker_text = ticker.fillna("").astype(str).str.upper()
    market_text = market.fillna("").astype(str).str.upper()
    out = pd.Series("UNKNOWN", index=ticker.index, dtype="object")
    out = out.mask(ticker_text.str.endswith(".KS"), "KOSPI")
    out = out.mask(ticker_text.str.endswith(".KQ"), "KOSDAQ")
    out = out.mask(out.eq("UNKNOWN") & market_text.isin(["KOSPI", "KOSDAQ"]), market_text)
    return out


def _derive_trade_date(df: pd.DataFrame) -> pd.Series:
    def parse_col(name: str) -> pd.Series:
        raw = df.get(name, pd.Series(index=df.index, dtype=object))
        text = raw.where(raw.notna(), "").astype(str).str.strip()
        cleaned = raw.where(text.ne(""), pd.NA)
        return pd.to_datetime(cleaned, errors="coerce", utc=True)

    rec = parse_col("recommended_at")
    base = parse_col("base_trade_date")
    created = parse_col("created_at")
    return rec.combine_first(base).combine_first(created).dt.strftime("%Y-%m-%d")


def load_intraday_rows(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise SystemExit(f"input not found: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    ticker = df.get("ticker", pd.Series("", index=df.index))
    market = df.get("market", pd.Series("", index=df.index))
    market2 = _derive_market(ticker, market)
    mask = scan_mode.eq("INTRADAY") & market2.isin(["KOSPI", "KOSDAQ"])
    if "is_dummy_data" in df.columns:
        dummy = df["is_dummy_data"].fillna("").astype(str).str.lower().isin({"1", "true", "yes"})
        mask &= ~dummy
    out = df.loc[mask].copy()
    out["market2"] = market2.loc[out.index]
    out["trade_date"] = _derive_trade_date(out)
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    for col in RETURN_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "priority_rank" in out.columns:
        out["priority_rank"] = pd.to_numeric(out["priority_rank"], errors="coerce")
    return out.sort_values(["market2", "trade_date", "ticker"], na_position="last").reset_index(drop=True)


def _cohort_mask(df: pd.DataFrame, cohort: str) -> pd.Series:
    rank = df.get("priority_rank", pd.Series(float("nan"), index=df.index))
    decision = df.get("decision", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    bucket = df.get("decision_bucket", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    exception = bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")
    if cohort == "Top1":
        return rank.eq(1).fillna(False) & ~exception
    if cohort == "Top5":
        return rank.between(1, 5, inclusive="both").fillna(False) & ~exception
    if cohort == "Exception Leader":
        return exception
    return pd.Series(True, index=df.index)


def _return_metrics(df: pd.DataFrame, mask: pd.Series, return_col: str) -> Dict[str, Any]:
    values = _safe_numeric(df.loc[mask], return_col).dropna()
    if values.empty:
        return {"n": 0, "win_pct": None, "avg_pct": None, "min_pct": None, "max_pct": None}
    return {
        "n": int(len(values)),
        "win_pct": round(float(values.gt(0).mean() * 100.0), 4),
        "avg_pct": round(float(values.mean()), 4),
        "min_pct": round(float(values.min()), 4),
        "max_pct": round(float(values.max()), 4),
    }


def build_report(input_path: Path) -> Dict[str, Any]:
    rows = load_intraday_rows(input_path)
    markets: List[Dict[str, Any]] = []
    today_kst = datetime.now(KST).date()
    for market in ("KOSPI", "KOSDAQ"):
        sub = rows[rows["market2"].eq(market)].copy()
        dates = sorted(sub["trade_date"].dropna().astype(str).unique().tolist()) if not sub.empty else []
        latest_data_lag_days = None
        if dates:
            try:
                latest_data_lag_days = (today_kst - datetime.strptime(dates[-1], "%Y-%m-%d").date()).days
            except ValueError:
                latest_data_lag_days = None
        market_payload: Dict[str, Any] = {
            "market": market,
            "rows": int(len(sub)),
            "unique_ticker_dates": int(sub[["ticker", "trade_date"]].drop_duplicates().shape[0]) if not sub.empty else 0,
            "active_days": int(len(dates)),
            "date_min": dates[0] if dates else None,
            "date_max": dates[-1] if dates else None,
            "latest_data_lag_days": latest_data_lag_days,
            "latest_data_fresh": bool(latest_data_lag_days is not None and latest_data_lag_days <= LATEST_DATA_MAX_LAG_DAYS),
            "latest_data_max_lag_days": LATEST_DATA_MAX_LAG_DAYS,
            "model_ready_min_rows": MODEL_READY_MIN_ROWS,
            "model_ready_min_days": MODEL_READY_MIN_DAYS,
            "cohorts": {},
        }
        return_1d = _safe_numeric(sub, "return_1d_pct")
        market_payload["return_1d_rows"] = int(return_1d.notna().sum())
        market_payload["model_row_ready"] = bool(market_payload["return_1d_rows"] >= MODEL_READY_MIN_ROWS)
        market_payload["model_day_ready"] = bool(market_payload["active_days"] >= MODEL_READY_MIN_DAYS)
        market_payload["model_ready"] = bool(market_payload["model_row_ready"] and market_payload["model_day_ready"])
        market_payload["operational_ready"] = bool(market_payload["model_ready"] and market_payload["latest_data_fresh"])
        for cohort in ("All", "Top1", "Top5", "Exception Leader"):
            mask = _cohort_mask(sub, cohort)
            market_payload["cohorts"][cohort] = {
                col: _return_metrics(sub, mask, col)
                for col in RETURN_COLS
            }
        markets.append(market_payload)
    return {
        "report_version": "kr_intraday_learning_readiness_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "rows_total": int(len(rows)),
        "markets": markets,
        "notes": [
            "This report reads the raw archive export directly because the experimental admission loader is SWING-only.",
            "model_ready only means there is enough labeled data to train/test; it is not a production quality approval.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# INTRADAY Learning Readiness",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- rows_total: `{report['rows_total']}`",
        "",
    ]
    for market in report.get("markets") or []:
        lines.extend(
            [
                f"## {market['market']}",
                "",
                (
                    f"- rows: `{market['rows']}` · return_1d_rows: `{market['return_1d_rows']}` · "
                    f"active_days: `{market['active_days']}` · model_ready: `{market['model_ready']}` · "
                    f"operational_ready: `{market['operational_ready']}`"
                ),
                (
                    f"- date_range: `{market['date_min']}` -> `{market['date_max']}` · "
                    f"latest_data_lag_days: `{market['latest_data_lag_days']}` · "
                    f"latest_data_fresh: `{market['latest_data_fresh']}`"
                ),
                "",
                "| Cohort | 1D | 3D | 5D |",
                "|---|---:|---:|---:|",
            ]
        )
        for cohort, metrics in (market.get("cohorts") or {}).items():
            def fmt(col: str) -> str:
                row = metrics.get(col) or {}
                return (
                    f"n={row.get('n')} / win {row.get('win_pct')}% / avg {row.get('avg_pct')}% / "
                    f"min {row.get('min_pct')}% / max {row.get('max_pct')}%"
                )

            lines.append(f"| {cohort} | {fmt('return_1d_pct')} | {fmt('return_3d_pct')} | {fmt('return_5d_pct')} |")
        lines.append("")
    lines.extend(["## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(report, args.output.with_suffix(".md"))
    print(json.dumps({"json": str(args.output), "md": str(args.output.with_suffix(".md"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
