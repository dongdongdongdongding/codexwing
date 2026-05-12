#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager

try:
    import FinanceDataReader as fdr  # type: ignore
except Exception:  # pragma: no cover
    fdr = None


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "learning"

SELECT_COLUMNS = ",".join(
    [
        "id",
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "feature_origin",
        "recommended_at",
        "created_at",
        "decision",
        "decision_bucket",
        "priority_rank",
        "alpha_score",
        "tech_score",
        "ml_prob",
        "prob_clean",
        "decision_score",
        "whale_score",
        "volume_ratio",
        "expected_edge_score",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "relative_rank_score",
        "relative_rank_pct",
        "loss_risk_score",
        "low_model_prob_score",
        "low_prob_high_score",
        "expected_edge_inversion_score",
        "entry_reference_price",
        "trend",
        "tier",
        "position",
        "strategy_family",
        "selection_lane",
        "scanner_timeframe_profile",
        "kr_universe_role",
        "theme_routing_path",
        "phase25_variant",
        "phase25_prob",
        "phase25_recommended_threshold",
        "return_1d_pct",
        "return_2d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "return_7d_pct",
        "latest_return_pct",
        "base_trade_date",
    ]
)

NUMERIC_COLUMNS = [
    "priority_rank",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "decision_score",
    "whale_score",
    "volume_ratio",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "relative_rank_score",
    "relative_rank_pct",
    "loss_risk_score",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
    "entry_reference_price",
    "phase25_prob",
    "phase25_recommended_threshold",
    "return_1d_pct",
    "return_2d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "latest_return_pct",
]

CATEGORICAL_COLUMNS = [
    "decision_bucket",
    "feature_origin",
    "trend",
    "tier",
    "position",
    "strategy_family",
    "selection_lane",
    "scanner_timeframe_profile",
    "kr_universe_role",
    "theme_routing_path",
    "phase25_variant",
]


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) >= 10:
        return text[:10]
    return None


def _load_rows(limit: int = 0) -> pd.DataFrame:
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    remaining = int(limit or 0)
    while True:
        batch_size = page_size if remaining <= 0 else min(page_size, remaining)
        res = (
            db.client.table("market_scan_results")
            .select(SELECT_COLUMNS)
            .eq("market_type", "KR")
            .ilike("ticker", "%.KQ")
            .eq("scan_mode", "SWING")
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + batch_size - 1)
            .execute()
        )
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
    if df.empty:
        return df
    ticker = df["ticker"].fillna("").astype(str).str.upper()
    df = df[ticker.str.endswith(".KQ")].copy()
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna("UNKNOWN").astype(str)
    rec = df.get("recommended_at", pd.Series(index=df.index, dtype=object))
    created = df.get("created_at", pd.Series(index=df.index, dtype=object))
    df["scan_date"] = rec.where(rec.notna() & rec.astype(str).str.len().gt(0), created).map(_date_text)
    df = df[df["scan_date"].notna()].copy()
    return df.reset_index(drop=True)


def _fetch_kr_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    if fdr is None:
        return pd.DataFrame()
    code = ticker.split(".")[0]
    try:
        hist = fdr.DataReader(code, start, end)
    except Exception:
        return pd.DataFrame()
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.copy()
    hist["trade_date"] = [d.date().isoformat() for d in hist.index]
    return hist.reset_index(drop=True)


def _label_ticker(group: pd.DataFrame, include_signal_day: bool = False) -> pd.DataFrame:
    ticker = str(group["ticker"].iloc[0])
    dates = sorted(d for d in group["scan_date"].dropna().astype(str).unique().tolist() if len(d) >= 10)
    if not dates:
        return group
    start = (date.fromisoformat(dates[0]) - timedelta(days=3)).isoformat()
    end = (date.fromisoformat(dates[-1]) + timedelta(days=14)).isoformat()
    hist = _fetch_kr_history(ticker, start, end)
    out = group.copy()
    out["mfe_5d_high_pct"] = np.nan
    out["mae_5d_low_pct"] = np.nan
    out["touch_5pct_5d"] = np.nan
    out["future_bars_5d"] = 0
    if hist.empty:
        return out
    trade_dates = hist["trade_date"].astype(str).tolist()
    date_to_pos = {d: i for i, d in enumerate(trade_dates)}
    highs = pd.to_numeric(hist["High"], errors="coerce")
    lows = pd.to_numeric(hist["Low"], errors="coerce")
    closes = pd.to_numeric(hist["Close"], errors="coerce")
    for idx, row in out.iterrows():
        scan_date = str(row.get("scan_date") or "")
        base_pos = None
        for pos, d in enumerate(trade_dates):
            if d >= scan_date:
                base_pos = pos
                break
        if base_pos is None:
            continue
        entry = _safe_float(row.get("entry_reference_price"))
        if entry is None or entry <= 0:
            entry = _safe_float(closes.iloc[base_pos])
        if entry is None or entry <= 0:
            continue
        start_pos = base_pos if include_signal_day else base_pos + 1
        end_pos = min(len(hist) - 1, start_pos + 4)
        if start_pos > end_pos:
            continue
        high_window = highs.iloc[start_pos : end_pos + 1].dropna()
        low_window = lows.iloc[start_pos : end_pos + 1].dropna()
        if high_window.empty:
            continue
        mfe = ((float(high_window.max()) / entry) - 1.0) * 100.0
        mae = ((float(low_window.min()) / entry) - 1.0) * 100.0 if not low_window.empty else np.nan
        out.at[idx, "mfe_5d_high_pct"] = round(mfe, 6)
        out.at[idx, "mae_5d_low_pct"] = round(mae, 6) if not pd.isna(mae) else np.nan
        out.at[idx, "touch_5pct_5d"] = int(mfe >= 5.0)
        out.at[idx, "future_bars_5d"] = int(end_pos - start_pos + 1)
    return out


def build_touch_labels(df: pd.DataFrame, include_signal_day: bool = False) -> pd.DataFrame:
    parts: List[pd.DataFrame] = []
    for _, group in df.groupby("ticker", sort=False):
        parts.append(_label_ticker(group.copy(), include_signal_day=include_signal_day))
    if not parts:
        return df
    labeled = pd.concat(parts, ignore_index=True)
    labeled = labeled[pd.to_numeric(labeled["future_bars_5d"], errors="coerce").ge(3)].copy()
    return labeled


def _metrics(df: pd.DataFrame, name: str, mask: pd.Series) -> Dict[str, Any] | None:
    sub = df[mask].copy()
    sub = sub[pd.to_numeric(sub["touch_5pct_5d"], errors="coerce").notna()].copy()
    if sub.empty:
        return None
    touch = pd.to_numeric(sub["touch_5pct_5d"], errors="coerce")
    mfe = pd.to_numeric(sub["mfe_5d_high_pct"], errors="coerce")
    close5 = pd.to_numeric(sub.get("return_5d_pct", pd.Series(index=sub.index)), errors="coerce")
    return {
        "slice": name,
        "n": int(len(sub)),
        "touch_5pct_5d_pct": round(float(touch.mean() * 100.0), 3),
        "avg_mfe_5d_high_pct": round(float(mfe.mean()), 4),
        "median_mfe_5d_high_pct": round(float(mfe.median()), 4),
        "avg_return_5d_close_pct": round(float(close5.mean()), 4) if close5.notna().any() else None,
        "win_close_5d_pct": round(float(close5.gt(0).mean() * 100.0), 3) if close5.notna().any() else None,
    }


def _candidate_masks(df: pd.DataFrame) -> List[Tuple[str, pd.Series]]:
    masks: List[Tuple[str, pd.Series]] = [("all_labeled", pd.Series(True, index=df.index))]
    for col in CATEGORICAL_COLUMNS:
        if col not in df.columns:
            continue
        counts = df[col].fillna("UNKNOWN").astype(str).value_counts()
        for val, cnt in counts.items():
            if cnt >= 20 and str(val).upper() not in {"", "UNKNOWN", "NAN", "NONE"}:
                masks.append((f"{col}={val}", df[col].fillna("UNKNOWN").astype(str).eq(str(val))))
    threshold_specs = {
        "priority_rank": [1, 2, 3, 5, 10],
        "alpha_score": [70, 75, 80, 85, 90, 95],
        "tech_score": [40, 50, 60, 70, 80],
        "ml_prob": [20, 30, 40, 50, 60],
        "prob_clean": [20, 30, 40, 50, 60],
        "decision_score": [70, 80, 85, 90, 95],
        "whale_score": [40, 50, 60, 70, 80],
        "volume_ratio": [1.2, 1.5, 2, 3, 5],
        "expected_edge_score": [4, 5, 6, 7, 8, 9, 10],
        "loss_risk_score": [30, 40, 50, 60, 70],
        "low_model_prob_score": [15, 20, 25, 30],
        "low_prob_high_score": [30, 40, 50, 60],
        "phase25_prob": [20, 30, 40, 50, 60, 70],
    }
    for col, thresholds in threshold_specs.items():
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        for thr in thresholds:
            if col in {"priority_rank", "loss_risk_score"}:
                masks.append((f"{col}<={thr}", series.le(thr)))
            else:
                masks.append((f"{col}>={thr}", series.ge(thr)))
    if {"phase25_prob", "phase25_recommended_threshold"}.issubset(df.columns):
        gap = pd.to_numeric(df["phase25_prob"], errors="coerce") - pd.to_numeric(
            df["phase25_recommended_threshold"], errors="coerce"
        )
        for thr in [-20, -10, 0, 5, 10]:
            masks.append((f"phase25_gap>={thr}", gap.ge(thr)))
    return masks


def search_slices(df: pd.DataFrame, min_n: int) -> List[Dict[str, Any]]:
    base_masks = _candidate_masks(df)
    rows: List[Dict[str, Any]] = []
    for name, mask in base_masks:
        row = _metrics(df, name, mask)
        if row and row["n"] >= min_n:
            rows.append(row)
    # Pairwise intersections from useful base masks only; keeps search broad but bounded.
    useful = []
    for name, mask in base_masks:
        cnt = int(mask.fillna(False).sum())
        if min_n <= cnt <= int(len(df) * 0.85):
            useful.append((name, mask.fillna(False)))
    for i, (name_a, mask_a) in enumerate(useful):
        for name_b, mask_b in useful[i + 1 :]:
            if name_a.split("=")[0] == name_b.split("=")[0] and "=" in name_a and "=" in name_b:
                continue
            combo = mask_a & mask_b
            cnt = int(combo.sum())
            if cnt < min_n:
                continue
            row = _metrics(df, f"{name_a} AND {name_b}", combo)
            if row:
                rows.append(row)
    rows = sorted(rows, key=lambda r: (-r["touch_5pct_5d_pct"], -r["avg_mfe_5d_high_pct"], -r["n"]))
    seen = set()
    unique: List[Dict[str, Any]] = []
    for row in rows:
        key = row["slice"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KOSDAQ 5D +5% Touch Slice Search",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- rows_loaded: `{report['rows_loaded']}`",
        f"- rows_labeled: `{report['rows_labeled']}`",
        f"- label: `next 5 trading days High >= entry_reference_price * 1.05`",
        f"- include_signal_day: `{report['include_signal_day']}`",
        f"- target: `touch_5pct_5d >= 70%, avg_mfe_5d_high >= +5%`",
        "",
        "## Target-Passing Slices",
        "",
    ]
    if report["target_pass_slices"]:
        for row in report["target_pass_slices"][:20]:
            lines.append(
                f"- {row['slice']}: n={row['n']}, touch5={row['touch_5pct_5d_pct']}%, "
                f"avg_mfe={row['avg_mfe_5d_high_pct']}%, close5_avg={row.get('avg_return_5d_close_pct')}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Best By Touch", ""])
    for row in report["best_by_touch"][:20]:
        lines.append(
            f"- {row['slice']}: n={row['n']}, touch5={row['touch_5pct_5d_pct']}%, "
            f"avg_mfe={row['avg_mfe_5d_high_pct']}%, close5_avg={row.get('avg_return_5d_close_pct')}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=30)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--include-signal-day", action="store_true")
    args = parser.parse_args()

    df = _load_rows(limit=args.limit)
    labeled = build_touch_labels(df, include_signal_day=bool(args.include_signal_day))
    slices = search_slices(labeled, min_n=int(args.min_n))
    target_pass = [
        row
        for row in slices
        if row["touch_5pct_5d_pct"] >= 70.0 and row["avg_mfe_5d_high_pct"] >= 5.0
    ]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows_loaded": int(len(df)),
        "rows_labeled": int(len(labeled)),
        "include_signal_day": bool(args.include_signal_day),
        "min_n": int(args.min_n),
        "feature_origin_counts": dict(Counter(labeled.get("feature_origin", pd.Series(dtype=object)).fillna("UNKNOWN"))),
        "baseline": _metrics(labeled, "all_labeled", pd.Series(True, index=labeled.index)),
        "target_pass_slices": target_pass,
        "best_by_touch": slices[:100],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "incl_signal_day" if args.include_signal_day else "next5d"
    json_path = REPORT_DIR / f"kosdaq_5d_touch_slice_search_{suffix}.json"
    md_path = REPORT_DIR / f"kosdaq_5d_touch_slice_search_{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps({"json": str(json_path), "md": str(md_path), "target_pass_slices": len(target_pass)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
