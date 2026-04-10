from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _infer_decision_bucket(df: pd.DataFrame) -> pd.Series:
    if "decision" in df.columns:
        decision = df["decision"].fillna("").astype(str).str.upper()
        inferred = pd.Series("unknown", index=df.index, dtype="object")
        inferred = inferred.mask(decision.eq("EXCEPTION_LEADER"), "exception_leader")
        inferred = inferred.mask(decision.isin(["WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"]), "watchlist")
        inferred = inferred.mask(decision.isin(["PRIORITY_WATCHLIST"]), "picked")
        return inferred.fillna("unknown").astype(str)
    if "decision_bucket" in df.columns:
        return df["decision_bucket"].fillna("unknown").astype(str)
    return pd.Series("unknown", index=df.index, dtype="object")


def _price_band(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    out = pd.Series("unknown", index=series.index, dtype="object")
    out = out.mask(numeric.gt(0) & numeric.le(7), "le_7")
    out = out.mask(numeric.gt(7) & numeric.le(15), "7_15")
    out = out.mask(numeric.gt(15), "gt_15")
    return out


def _infer_selection_lane(df: pd.DataFrame) -> pd.Series:
    existing = df["selection_lane"] if "selection_lane" in df.columns else pd.Series(index=df.index, dtype="object")
    lane = existing.fillna("").astype(str).str.lower()
    horizon = df["target_horizon_days"] if "target_horizon_days" in df.columns else pd.Series(index=df.index, dtype="float")
    scan_mode = df["scan_mode"] if "scan_mode" in df.columns else pd.Series(index=df.index, dtype="object")
    scan_mode = scan_mode.fillna("").astype(str).str.upper()
    horizon_numeric = pd.to_numeric(horizon, errors="coerce")

    inferred = pd.Series("3d", index=df.index, dtype="object")
    inferred = inferred.mask(scan_mode.eq("INTRADAY"), "1d")
    inferred = inferred.mask(horizon_numeric.le(1), "1d")
    inferred = inferred.mask(lane.isin(["1d", "3d"]), lane)
    return inferred


def _infer_target_horizon_days(df: pd.DataFrame) -> pd.Series:
    if "target_horizon_days" in df.columns:
        existing = pd.to_numeric(df["target_horizon_days"], errors="coerce")
    else:
        existing = pd.Series(index=df.index, dtype="float")
    inferred_lane = _infer_selection_lane(df)
    fallback = inferred_lane.map({"1d": 1, "3d": 3}).fillna(3)
    return existing.fillna(fallback).astype(int)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export enriched scan archive dataset for backtest/model learning.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ", "NASDAQ", "AMEX"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--strategy-family", default=None)
    parser.add_argument("--output-dir", type=str, default="runtime_state/reports/archive")
    args = parser.parse_args()

    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    market = str(args.market).upper()
    remaining = int(args.limit or 0)
    page_size = 1000
    page = 0
    rows = []
    while True:
        batch_size = page_size if remaining <= 0 else min(page_size, remaining)
        query = (
            db.client.table("market_scan_results")
            .select("*")
            .order("created_at", desc=True)
            .range(page * page_size, page * page_size + batch_size - 1)
        )
        if market == "KOSPI":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KS")
        elif market == "KOSDAQ":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KQ")
        elif market == "NASDAQ":
            query = query.eq("market_type", "US")
        elif market == "AMEX":
            query = query.eq("market_type", "AMEX")
        if args.strategy_family:
            query = query.eq("strategy_family", str(args.strategy_family))
        res = query.execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        page += 1
        if remaining > 0:
            remaining -= len(batch)
            if remaining <= 0:
                break
    df = pd.DataFrame(rows)
    if not df.empty and str(args.scan_mode).upper() != "ALL" and "scan_mode" in df.columns:
        df = df[df["scan_mode"].fillna("SWING").str.upper() == str(args.scan_mode).upper()]
    if not df.empty:
        df["decision_bucket"] = _infer_decision_bucket(df)
        df["selection_lane"] = _infer_selection_lane(df)
        df["target_horizon_days"] = _infer_target_horizon_days(df)
        if "entry_reference_price" in df.columns:
            df["price_band"] = _price_band(df["entry_reference_price"])
            df["is_sub7"] = (df["price_band"] == "le_7").astype(int)

    return_cols = [
        "return_30m_pct",
        "return_1h_pct",
        "return_close_pct",
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "return_7d_pct",
    ]
    if not df.empty:
        available_return_cols = [col for col in return_cols if col in df.columns]
        if available_return_cols:
            numeric = df[available_return_cols].apply(pd.to_numeric, errors="coerce")
            df["max_return_observed_pct"] = numeric.max(axis=1, skipna=True)
            df["label_win_close"] = numeric.get("return_close_pct", pd.Series(index=df.index)).fillna(0).gt(0).astype(int)
            df["label_win_1d"] = numeric.get("return_1d_pct", pd.Series(index=df.index)).fillna(0).gt(0).astype(int)
            df["label_win_3d"] = numeric.get("return_3d_pct", pd.Series(index=df.index)).fillna(0).gt(0).astype(int)
            df["label_hit_5pct"] = df["max_return_observed_pct"].fillna(0).ge(5).astype(int)
            df["label_hit_10pct"] = df["max_return_observed_pct"].fillna(0).ge(10).astype(int)
            df["label_hit_20pct"] = df["max_return_observed_pct"].fillna(0).ge(20).astype(int)
            df["label_hit_50pct"] = df["max_return_observed_pct"].fillna(0).ge(50).astype(int)
            df["label_hit_100pct"] = df["max_return_observed_pct"].fillna(0).ge(100).astype(int)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix_parts = [market.lower()]
    if str(args.scan_mode).upper() != "ALL":
        suffix_parts.append(str(args.scan_mode).lower())
    if args.strategy_family:
        suffix_parts.append(str(args.strategy_family).lower())
    suffix = "_".join([part for part in suffix_parts if part and part != "all"]) or "all"
    csv_path = out_dir / f"scan_archive_learning_dataset_{suffix}.csv"
    json_path = out_dir / f"scan_archive_learning_dataset_{suffix}.json"
    if not df.empty:
        df.to_csv(csv_path, index=False)
        json_path.write_text(df.to_json(orient="records", force_ascii=False), encoding="utf-8")
    else:
        csv_path.write_text("", encoding="utf-8")
        json_path.write_text("[]", encoding="utf-8")

    print(
        json.dumps(
            {
                "rows": int(len(df)),
                "csv_path": str(csv_path),
                "json_path": str(json_path),
                "market": market,
                "scan_mode": str(args.scan_mode).upper(),
                "strategy_family": args.strategy_family,
                "columns": sorted(df.columns.tolist()) if not df.empty else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
