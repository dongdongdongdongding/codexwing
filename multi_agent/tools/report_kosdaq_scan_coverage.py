#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


SELECT_COLUMNS = ",".join(
    [
        "id",
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "feature_origin",
        "validation_excluded",
        "is_dummy_data",
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
        "entry_reference_price",
        "trend",
        "tier",
        "position",
        "return_1d_pct",
        "return_2d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "return_7d_pct",
        "return_14d_pct",
        "return_30d_pct",
        "latest_return_pct",
        "base_trade_date",
    ]
)

STRICT_FEATURES = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "whale_score",
    "decision_score",
    "entry_reference_price",
    "volume_ratio",
    "trend",
    "tier",
    "position",
]


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def _load_rows() -> pd.DataFrame:
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(SELECT_COLUMNS)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return pd.DataFrame(rows)


def _not_unknown(series: pd.Series) -> pd.Series:
    return ~series.fillna("").astype(str).str.strip().str.lower().isin({"", "unknown", "nan", "none", "null"})


def _non_null_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").notna()


def _stage_counts(df: pd.DataFrame) -> Dict[str, int]:
    if df.empty:
        return {}
    ticker = df["ticker"].fillna("").astype(str).str.upper()
    kq = ticker.str.endswith(".KQ")
    swing = df["scan_mode"].fillna("").astype(str).str.upper().eq("SWING")
    market_eq = df["market"].fillna("").astype(str).str.upper().eq("KOSDAQ")
    non_dummy = ~df["is_dummy_data"].map(_truthy) if "is_dummy_data" in df.columns else pd.Series(True, index=df.index)
    ret5 = _non_null_numeric(df["return_5d_pct"])
    strict = pd.Series(True, index=df.index)
    for col in ["alpha_score", "tech_score", "ml_prob", "whale_score", "decision_score", "entry_reference_price", "volume_ratio"]:
        strict &= _non_null_numeric(df[col])
    for col in ["trend", "tier", "position"]:
        strict &= _not_unknown(df[col])
    rec = pd.to_datetime(df["recommended_at"].fillna(df["created_at"]), errors="coerce", utc=True)
    aged = rec.notna() & rec.le(datetime.now(timezone.utc) - timedelta(days=8))
    return {
        "all_rows": int(len(df)),
        "ticker_kq_rows": int(kq.sum()),
        "market_eq_kosdaq_rows": int(market_eq.sum()),
        "kq_swing_rows": int((kq & swing).sum()),
        "market_eq_kosdaq_swing_rows": int((market_eq & swing).sum()),
        "kq_swing_non_dummy_rows": int((kq & swing & non_dummy).sum()),
        "kq_swing_return_5d_rows": int((kq & swing & non_dummy & ret5).sum()),
        "kq_swing_strict_feature_rows": int((kq & swing & non_dummy & strict).sum()),
        "kq_swing_strict_feature_return_5d_rows": int((kq & swing & non_dummy & strict & ret5).sum()),
        "kq_swing_aged_missing_return_5d_rows": int((kq & swing & non_dummy & aged & ~ret5).sum()),
    }


def _value_counts(df: pd.DataFrame, col: str, limit: int = 20) -> Dict[str, int]:
    if df.empty or col not in df.columns:
        return {}
    counts = Counter(str(v if v is not None else "NULL") for v in df[col].tolist())
    return dict(counts.most_common(limit))


def _field_coverage(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    if df.empty:
        return out
    for col in STRICT_FEATURES + ["return_5d_pct", "recommended_at", "created_at"]:
        if col in {"trend", "tier", "position"}:
            ok = _not_unknown(df[col])
        elif col in {"recommended_at", "created_at"}:
            ok = df[col].notna() & df[col].astype(str).str.len().gt(0)
        else:
            ok = _non_null_numeric(df[col])
        out[col] = {
            "present": int(ok.sum()),
            "missing": int((~ok).sum()),
            "present_pct": round(float(ok.mean() * 100.0), 3),
        }
    return out


def _missing_breakdown(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {}
    ret5_missing = ~_non_null_numeric(df["return_5d_pct"])
    rec = pd.to_datetime(df["recommended_at"].fillna(df["created_at"]), errors="coerce", utc=True)
    aged = rec.notna() & rec.le(datetime.now(timezone.utc) - timedelta(days=8))
    rec_missing = ~(df["recommended_at"].notna() & df["recommended_at"].astype(str).str.len().gt(0))
    return {
        "return_5d_missing_by_feature_origin": _value_counts(df[ret5_missing], "feature_origin"),
        "aged_return_5d_missing_by_feature_origin": _value_counts(df[ret5_missing & aged], "feature_origin"),
        "recommended_at_missing_by_feature_origin": _value_counts(df[rec_missing], "feature_origin"),
    }


def build_report() -> Dict[str, Any]:
    df = _load_rows()
    if df.empty:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "error": "no rows"}
    ticker = df["ticker"].fillna("").astype(str).str.upper()
    kq_swing = df[ticker.str.endswith(".KQ") & df["scan_mode"].fillna("").astype(str).str.upper().eq("SWING")].copy()
    market_eq_swing = df[
        df["market"].fillna("").astype(str).str.upper().eq("KOSDAQ")
        & df["scan_mode"].fillna("").astype(str).str.upper().eq("SWING")
    ].copy()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_counts": _stage_counts(df),
        "all_market_counts": _value_counts(df, "market"),
        "all_market_type_counts": _value_counts(df, "market_type"),
        "kq_swing_market_counts": _value_counts(kq_swing, "market"),
        "kq_swing_market_type_counts": _value_counts(kq_swing, "market_type"),
        "kq_swing_scan_mode_counts": _value_counts(kq_swing, "scan_mode"),
        "kq_swing_feature_origin_counts": _value_counts(kq_swing, "feature_origin"),
        "kq_swing_decision_bucket_counts": _value_counts(kq_swing, "decision_bucket"),
        "kq_swing_field_coverage": _field_coverage(kq_swing),
        "kq_swing_missing_breakdown": _missing_breakdown(kq_swing),
        "market_eq_kosdaq_swing_field_coverage": _field_coverage(market_eq_swing),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    print(text)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
