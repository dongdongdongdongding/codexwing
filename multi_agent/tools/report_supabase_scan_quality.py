#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
REQUIRED_SCAN_COLUMNS = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "trend",
    "tier",
    "volume",
    "volume_ratio",
    "volume_confirmed",
    "position",
    "entry_reference_price",
    "feature_origin",
    "feature_quality",
    "feature_completeness",
    "feature_missing_fields",
    "validation_excluded",
    "validation_excluded_reason",
    "is_dummy_data",
    "inference_failed",
]


def _infer_submarket(ticker: Any, market_type: Any) -> str:
    t = str(ticker or "").upper()
    mt = str(market_type or "").upper()
    if t.endswith(".KS"):
        return "KOSPI"
    if t.endswith(".KQ"):
        return "KOSDAQ"
    if mt in {"KOSPI", "KOSDAQ"}:
        return mt
    if mt == "KR":
        return "KR"
    return mt or "UNKNOWN"


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == "object":
        return series.fillna("").astype(str).str.lower().isin({"true", "1", "yes"})
    return series.fillna(False).astype(bool)


def _load_table() -> pd.DataFrame:
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select("*")
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return pd.DataFrame(rows)


def _missing_rates(frame: pd.DataFrame, cols: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    total = max(len(frame), 1)
    for col in cols:
        if col not in frame.columns:
            out[col] = 100.0
            continue
        out[col] = round(float(frame[col].isna().sum() / total * 100.0), 3)
    return out


def _return_summary(frame: pd.DataFrame, return_col: str) -> Dict[str, Any]:
    if return_col not in frame.columns:
        return {}
    ret = pd.to_numeric(frame[return_col], errors="coerce").dropna()
    if ret.empty:
        return {"n": 0}
    return {
        "n": int(len(ret)),
        "avg_return_pct": round(float(ret.mean()), 4),
        "win_rate_pct": round(float(ret.gt(0).mean() * 100.0), 3),
    }


def _computed_complete_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    mask = pd.Series(True, index=frame.index)
    for col in ["alpha_score", "tech_score", "ml_prob", "whale_score", "decision_score", "entry_reference_price"]:
        if col not in frame.columns:
            return pd.Series(False, index=frame.index)
        mask &= pd.to_numeric(frame[col], errors="coerce").notna()
    for col in ["trend", "tier", "position"]:
        if col not in frame.columns:
            return pd.Series(False, index=frame.index)
        mask &= frame[col].fillna("").astype(str).str.strip().ne("")
    volume_ok = pd.Series(False, index=frame.index)
    if "volume_ratio" in frame.columns:
        volume_ok |= pd.to_numeric(frame["volume_ratio"], errors="coerce").notna()
    if "volume" in frame.columns:
        volume_ok |= frame["volume"].fillna("").astype(str).str.extract(r"(-?\d+(?:\.\d+)?)", expand=False).notna()
    mask &= volume_ok
    return mask


def _group_return_table(frame: pd.DataFrame, return_col: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if return_col not in frame.columns:
        return rows
    for (submarket, bucket), group in frame.groupby(["submarket", "decision_bucket"], dropna=False):
        summary = _return_summary(group, return_col)
        if not summary or summary.get("n", 0) == 0:
            continue
        rows.append({"submarket": str(submarket), "bucket": str(bucket), **summary})
    return sorted(rows, key=lambda row: (row["submarket"], row["bucket"]))


def _rank_band_table(frame: pd.DataFrame, return_col: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if return_col not in frame.columns or "priority_rank" not in frame.columns:
        return rows
    work = frame.copy()
    rank = pd.to_numeric(work["priority_rank"], errors="coerce")
    work["rank_band"] = "unknown"
    work.loc[rank.between(1, 5, inclusive="both"), "rank_band"] = "top5"
    work.loc[rank.between(6, 10, inclusive="both"), "rank_band"] = "top6_10"
    work.loc[rank.gt(10), "rank_band"] = "rank_gt10"
    for (submarket, band), group in work.groupby(["submarket", "rank_band"], dropna=False):
        summary = _return_summary(group, return_col)
        if not summary or summary.get("n", 0) == 0:
            continue
        rows.append({"submarket": str(submarket), "rank_band": str(band), **summary})
    return sorted(rows, key=lambda row: (row["submarket"], row["rank_band"]))


def _build_report(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "rows": 0}
    df = df.copy()
    df["scan_mode"] = df.get("scan_mode", "SWING").fillna("SWING").astype(str).str.upper()
    df["decision_bucket"] = df.get("decision_bucket", "unknown").fillna("unknown").astype(str)
    df["submarket"] = [
        _infer_submarket(ticker, market_type)
        for ticker, market_type in zip(df.get("ticker", pd.Series(dtype=object)), df.get("market_type", pd.Series(dtype=object)))
    ]
    kr_swing = df[df["scan_mode"].eq("SWING") & df["submarket"].isin(["KOSPI", "KOSDAQ"])].copy()
    schema_columns = sorted(df.columns.tolist())
    schema_missing = [col for col in REQUIRED_SCAN_COLUMNS if col not in df.columns]
    if "validation_excluded" in kr_swing.columns:
        validation_excluded = int(_bool_series(kr_swing["validation_excluded"]).sum())
    else:
        validation_excluded = 0
    if "is_dummy_data" in kr_swing.columns:
        dummy_rows = int(_bool_series(kr_swing["is_dummy_data"]).sum())
    else:
        dummy_rows = 0
    computed_complete = _computed_complete_mask(kr_swing)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table": "market_scan_results",
        "total_rows": int(len(df)),
        "column_count": int(len(schema_columns)),
        "schema_missing_required_columns": schema_missing,
        "kr_swing_rows": int(len(kr_swing)),
        "kr_swing_by_submarket": kr_swing["submarket"].value_counts(dropna=False).to_dict(),
        "kr_swing_by_bucket": kr_swing["decision_bucket"].value_counts(dropna=False).to_dict(),
        "kr_swing_validation_excluded_rows": validation_excluded,
        "kr_swing_dummy_rows": dummy_rows,
        "kr_swing_computed_complete_rows": int(computed_complete.sum()),
        "kr_swing_computed_complete_with_return3d_rows": int(
            (
                computed_complete
                & pd.to_numeric(
                    kr_swing.get("return_3d_pct", pd.Series(index=kr_swing.index, dtype=float)),
                    errors="coerce",
                ).notna()
            ).sum()
        ),
        "missing_rates_all_kr_swing_pct": _missing_rates(kr_swing, REQUIRED_SCAN_COLUMNS),
        "missing_rates_by_submarket_pct": {
            str(submarket): _missing_rates(group, REQUIRED_SCAN_COLUMNS)
            for submarket, group in kr_swing.groupby("submarket", dropna=False)
        },
        "returns_by_bucket": {
            col: _group_return_table(kr_swing, col)
            for col in ["return_1d_pct", "return_3d_pct", "return_5d_pct", "return_7d_pct"]
        },
        "returns_by_rank_band": {
            col: _rank_band_table(kr_swing, col)
            for col in ["return_1d_pct", "return_3d_pct", "return_5d_pct", "return_7d_pct"]
        },
    }
    return report


def _write_markdown(report: Dict[str, Any], md_path: Path) -> None:
    lines = [
        "# Supabase Scan Data Quality",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- table_rows: `{report.get('total_rows', 0):,}`",
        f"- column_count: `{report.get('column_count', 0)}`",
        f"- kr_swing_rows: `{report.get('kr_swing_rows', 0):,}`",
        f"- schema_missing_required_columns: `{', '.join(report.get('schema_missing_required_columns', [])) or 'none'}`",
        f"- kr_swing_validation_excluded_rows: `{report.get('kr_swing_validation_excluded_rows', 0):,}`",
        f"- kr_swing_dummy_rows: `{report.get('kr_swing_dummy_rows', 0):,}`",
        f"- kr_swing_computed_complete_rows: `{report.get('kr_swing_computed_complete_rows', 0):,}`",
        f"- kr_swing_computed_complete_with_return3d_rows: `{report.get('kr_swing_computed_complete_with_return3d_rows', 0):,}`",
        "",
        "## KR SWING Counts",
        "",
        f"- by_submarket: `{report.get('kr_swing_by_submarket', {})}`",
        f"- by_bucket: `{report.get('kr_swing_by_bucket', {})}`",
        "",
        "## Missing Rates",
        "",
    ]
    missing = report.get("missing_rates_all_kr_swing_pct", {})
    for key, value in missing.items():
        if float(value) > 0:
            lines.append(f"- {key}: `{value}%`")
    lines.extend(["", "## Return Summary", ""])
    for col, rows in (report.get("returns_by_bucket", {}) or {}).items():
        lines.append(f"### {col} by bucket")
        for row in rows:
            lines.append(
                f"- {row['submarket']} / {row['bucket']}: n={row['n']}, avg={row['avg_return_pct']}%, win={row['win_rate_pct']}%"
            )
        lines.append("")
    for col, rows in (report.get("returns_by_rank_band", {}) or {}).items():
        lines.append(f"### {col} by rank band")
        for row in rows:
            lines.append(
                f"- {row['submarket']} / {row['rank_band']}: n={row['n']}, avg={row['avg_return_pct']}%, win={row['win_rate_pct']}%"
            )
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = _load_table()
    report = _build_report(df)
    json_path = REPORT_DIR / "supabase_scan_data_quality.json"
    md_path = REPORT_DIR / "supabase_scan_data_quality.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"json": str(json_path), "md": str(md_path), "kr_swing_rows": report.get("kr_swing_rows", 0)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
