"""Read-only audit of generic KR archive period returns against stored prices.

This does not certify price vendors, corporate actions, executable P&L, or model
eligibility. No archive/DB mutation. Differences are evidence for review, not an
automatic correction. US and model-issued lanes remain explicitly out of scope.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.backfill_kr_intraday import save_json

HORIZONS = (1, 3, 5)
TOLERANCE_PP = .05


def audit(rows, prices, sessions, tolerance=TOLERANCE_PP):
    """Compare exact observed market-session offsets; never compress missing ticker bars."""
    frame = rows.copy()
    frame["ticker"] = frame.ticker.astype(str)
    generic = frame.run_id.astype(str).str.startswith("RUN-")
    kr = frame.ticker.str.fullmatch(r"\d{6}\.(KS|KQ)")
    scope = frame[generic & kr].copy()
    scope["code"] = scope.ticker.str[:6]
    scope["base"] = pd.to_datetime(scope.base_trade_date, errors="coerce").dt.normalize()
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices.date).dt.normalize()
    prices["code"] = prices.code.astype(str).str.zfill(6)
    if prices.duplicated(["code", "date"]).any():
        raise ValueError("duplicate_price_key")
    panel = prices.set_index(["code", "date"])
    calendar = pd.DatetimeIndex(pd.to_datetime(sessions)).normalize().unique().sort_values()
    positions = {day: idx for idx, day in enumerate(calendar)}
    price_asof = prices.date.max()
    # Calendar may be newer than adjusted prices; future target prices must stay unknown.
    summaries, details = {}, []
    day_mismatch = []
    for _, row in scope.iterrows():
        stamp = pd.to_datetime(row.get("recommended_at"), utc=True, errors="coerce")
        if pd.notna(stamp) and pd.notna(row["base"]):
            recommended = stamp.tz_convert("Asia/Seoul").tz_localize(None).normalize()
            if recommended != row["base"]:
                day_mismatch.append({"id": row.get("id"), "ticker": row.ticker,
                                     "base": str(row["base"].date()), "recommended_KST": str(recommended.date())})
    for h in HORIZONS:
        counts = Counter()
        eligible_counts = Counter()
        col = f"return_{h}d_pct"
        for _, row in scope.iterrows():
            base = row["base"]
            stored = pd.to_numeric(row.get(col), errors="coerce")
            record = {"id": row.get("id"), "ticker": row.ticker, "run_id": row.run_id,
                      "base": str(base.date()) if pd.notna(base) else None, "horizon": h,
                      "stored_pct": float(stored) if pd.notna(stored) and np.isfinite(stored) else None}
            status = None
            if base not in positions:
                status = "base_missing_or_not_observed_session"
            elif positions[base]+h >= len(calendar):
                status = "horizon_not_observed_yet"
            else:
                target = calendar[positions[base]+h]
                record["target"] = str(target.date())
                expected = calendar[positions[base]:positions[base]+h+1]
                keys = [(row.code, day) for day in expected]
                if target > price_asof:
                    status = "adjusted_source_not_current_to_horizon"
                elif not all(key in panel.index for key in keys):
                    status = "missing_ticker_session_price"
                else:
                    bars = panel.loc[keys]
                    valid = np.isfinite(bars[["close", "adj_close"]]).all().all() and (bars[["close", "adj_close"]] > 0).all().all()
                    if not valid:
                        status = "invalid_price"
                    else:
                        raw = (bars.close.iloc[-1]/bars.close.iloc[0]-1)*100
                        adj = (bars.adj_close.iloc[-1]/bars.adj_close.iloc[0]-1)*100
                        record.update(raw_pct=float(raw), adjusted_pct=float(adj),
                                      adjusted_base_close=float(bars.adj_close.iloc[0]),
                                      raw_base_close=float(bars.close.iloc[0]),
                                      has_zero_volume_session=bool(bars.volume.eq(0).any()))
                        if pd.isna(stored):
                            status = "stored_label_missing"
                        elif not np.isfinite(stored):
                            status = "invalid_stored_label"
                        elif abs(stored-adj) <= tolerance:
                            status = "matches_adjusted"
                        elif abs(stored-raw) <= tolerance:
                            status = "matches_raw_only"
                        else:
                            status = "mismatch_both"
                        if pd.notna(stored) and np.isfinite(stored):
                            record["adjusted_difference_pp"] = float(stored-adj)
            record["status"] = status
            counts[status] += 1
            excluded = str(row.get("validation_excluded", "")).lower() in {"true", "1", "1.0"}
            record["currently_excluded"] = excluded
            if not excluded:
                eligible_counts[status] += 1
            if status != "matches_adjusted":
                details.append(record)
        summaries[str(h)] = {"all_rows": dict(counts), "not_marked_excluded": dict(eligible_counts)}
    return {"scope": {"archive_rows": len(rows), "generic_KR_rows": len(scope),
                      "generic_non_KR_rows_unreviewed": int((generic & ~kr).sum()),
                      "non_generic_rows_out_of_scope": int((~generic).sum())},
            "price_asof": str(price_asof.date()), "calendar_asof": str(calendar.max().date()),
            "tolerance_percentage_points": tolerance, "horizons": summaries,
            "base_vs_recommended_KST_mismatches": day_mismatch, "differences": details,
            "limitations": ["Observed price sessions are not an independent exchange calendar",
                            "px_delisted adjustment heuristic is not a verified corporate-action ledger",
                            "A matched label does not establish signal timing, execution, or eligibility",
                            "Suspended positive closes are valuations, not executable prices",
                            "US and non-RUN model lanes are not certified by this audit"],
            "mutations": 0}


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--cache", type=Path, default=Path.home()/"research_cache")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    archive = args.root/"runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
    price_path = args.cache/"px_delisted.parquet"
    calendar_path = args.cache/"px_long.parquet"
    paths = [archive, price_path, calendar_path]
    before = {str(path): sha(path) for path in paths}
    columns = ["id", "ticker", "run_id", "recommended_at", "base_trade_date", "validation_excluded"] + [f"return_{h}d_pct" for h in HORIZONS]
    rows = pd.read_csv(archive, usecols=columns, low_memory=False)
    oldest = pd.to_datetime(rows.base_trade_date, errors="coerce").min()
    prices = pd.read_parquet(price_path, columns=["code", "date", "close", "adj_close", "volume"])
    prices = prices[pd.to_datetime(prices.date) >= oldest]
    sessions = pd.read_parquet(calendar_path, columns=["date"]).date.unique()
    report = audit(rows, prices, sessions)
    if before != {str(path): sha(path) for path in paths}:
        raise RuntimeError("source_changed_during_audit; rerun")
    report.update(input_sha256=before, generated_at=datetime.now(timezone.utc).isoformat())
    output = args.output or args.root/"runtime_state/reports/validation/archive_daily_returns_audit.json"
    save_json(output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in {"differences", "base_vs_recommended_KST_mismatches"}}, ensure_ascii=False))
    print(json.dumps({"date_mismatches": len(report["base_vs_recommended_KST_mismatches"]), "report": str(output)}))


if __name__ == "__main__":
    main()
