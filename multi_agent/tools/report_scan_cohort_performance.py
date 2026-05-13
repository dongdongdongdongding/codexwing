#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.practical_entry_gate import evaluate_practical_entry_gate


DEFAULT_INPUT = PROJECT_ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runtime_state/reports/validation"

NUMERIC_COLUMNS = [
    "priority_rank",
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "min_return_observed_pct",
    "max_high_return_5d_pct",
    "decision_score",
    "expected_edge_score",
    "loss_risk_score",
    "whale_score",
    "prob_clean",
    "tech_score",
    "day_return_pct",
]


def _bool_series(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "yes", "y"})


def _pct(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
        if result != result:
            return None
        return round(result * 100.0, 3)
    except Exception:
        return None


def _round(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
        if result != result:
            return None
        return round(result, digits)
    except Exception:
        return None


def _load_rows(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["is_dummy_data", "validation_excluded", "label_stop_loss_5pct"]:
        if col in df.columns:
            df[f"{col}_bool"] = _bool_series(df[col])
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    mask = scan_mode.eq("SWING") & (ticker.str.endswith(".KS") | ticker.str.endswith(".KQ"))
    if "is_dummy_data_bool" in df.columns:
        mask &= ~df["is_dummy_data_bool"]
    out = df.loc[mask].copy()
    out["market2"] = "KOSDAQ"
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    return out


def _prepare_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    stop = pd.Series(False, index=out.index)
    if "min_return_observed_pct" in out.columns:
        stop |= out["min_return_observed_pct"].le(-5.0).fillna(False)
    if "label_stop_loss_5pct_bool" in out.columns:
        stop |= out["label_stop_loss_5pct_bool"].fillna(False)
    out["stop_hit_5pct_proxy"] = stop
    out["clean_riser"] = (
        out["return_1d_pct"].ge(-1.0)
        & out["return_3d_pct"].ge(out["return_1d_pct"])
        & out["return_5d_pct"].ge(out["return_3d_pct"])
        & out["return_5d_pct"].ge(5.0)
        & ~stop
    )
    out["bad_path"] = stop | out["return_1d_pct"].lt(-3.0) | out["return_5d_pct"].lt(0.0)
    out["practical_win"] = out["return_5d_pct"].gt(0) & out["return_1d_pct"].ge(-1.0) & ~stop
    out["exception_leader"] = (
        out.get("decision_bucket", pd.Series("", index=out.index)).fillna("").astype(str).str.lower().eq("exception_leader")
        | out.get("decision", pd.Series("", index=out.index)).fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
    )
    out["practical_gate_level"] = [
        evaluate_practical_entry_gate(row).get("level")
        for row in out.to_dict("records")
    ]
    out["practical_gate_candidate"] = out["practical_gate_level"].isin(["pass", "near", "small_sample"])
    return out


def _cohort_masks(df: pd.DataFrame) -> Dict[str, pd.Series]:
    return {
        "Top1": df["priority_rank"].eq(1) if "priority_rank" in df.columns else pd.Series(False, index=df.index),
        "Top5": df["priority_rank"].between(1, 5, inclusive="both") if "priority_rank" in df.columns else pd.Series(False, index=df.index),
        "Exception Leader": df["exception_leader"],
        "Practical 80 Gate": df["practical_gate_candidate"],
    }


def _horizon_summary(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    returns = df[col].dropna()
    if returns.empty:
        return {"n": 0, "win_pct": None, "avg_pct": None, "median_pct": None}
    return {
        "n": int(len(returns)),
        "win_pct": _pct(returns.gt(0).mean()),
        "avg_pct": _round(returns.mean(), 4),
        "median_pct": _round(returns.median(), 4),
    }


def _cohort_summary(df: pd.DataFrame) -> Dict[str, Any]:
    resolved_path = df.dropna(subset=["return_1d_pct", "return_3d_pct", "return_5d_pct"]).copy()
    summary = {
        "rows": int(len(df)),
        "horizons": {
            "1D": _horizon_summary(df, "return_1d_pct"),
            "3D": _horizon_summary(df, "return_3d_pct"),
            "5D": _horizon_summary(df, "return_5d_pct"),
        },
        "path": {
            "resolved_rows": int(len(resolved_path)),
            "practical_win_pct": _pct(resolved_path["practical_win"].mean()) if len(resolved_path) else None,
            "clean_riser_pct": _pct(resolved_path["clean_riser"].mean()) if len(resolved_path) else None,
            "bad_path_pct": _pct(resolved_path["bad_path"].mean()) if len(resolved_path) else None,
            "avg_min_drawdown_pct": _round(resolved_path["min_return_observed_pct"].mean(), 4)
            if "min_return_observed_pct" in resolved_path.columns and len(resolved_path)
            else None,
            "avg_max_high_5d_pct": _round(resolved_path["max_high_return_5d_pct"].mean(), 4)
            if "max_high_return_5d_pct" in resolved_path.columns and len(resolved_path)
            else None,
        },
    }
    return summary


def build_report(df: pd.DataFrame) -> Dict[str, Any]:
    prepared = _prepare_labels(df)
    markets: Dict[str, Any] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        market_df = prepared.loc[prepared["market2"].eq(market)].copy()
        cohorts = {}
        for name, mask in _cohort_masks(market_df).items():
            cohorts[name] = _cohort_summary(market_df.loc[mask])
        markets[market] = {
            "rows": int(len(market_df)),
            "cohorts": cohorts,
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DEFAULT_INPUT),
        "definition": {
            "Top1": "priority_rank == 1",
            "Top5": "priority_rank between 1 and 5",
            "Exception Leader": "decision_bucket == exception_leader or decision == EXCEPTION_LEADER",
            "Practical 80 Gate": "scan-time practical_entry_gate level in pass/near/small_sample",
            "clean_riser": "1D >= -1, 3D >= 1D, 5D >= 3D, 5D >= +5, no 5% stop proxy",
            "bad_path": "5% stop proxy hit OR 1D < -3 OR 5D < 0",
        },
        "rows": {
            "input_rows": int(len(df)),
            "prepared_rows": int(len(prepared)),
        },
        "markets": markets,
    }


def _fmt_horizon(row: Dict[str, Any]) -> str:
    if not row or not row.get("n"):
        return "-"
    return f"n={row.get('n')} / win {row.get('win_pct')}% / avg {row.get('avg_pct'):+.2f}%"


def _fmt_path(row: Dict[str, Any]) -> str:
    if not row or not row.get("resolved_rows"):
        return "-"
    return (
        f"resolved={row.get('resolved_rows')} / practical {row.get('practical_win_pct')}% / "
        f"clean {row.get('clean_riser_pct')}% / bad {row.get('bad_path_pct')}%"
    )


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Scan Cohort Performance",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source: `{report.get('source')}`",
        f"- input_rows: `{report.get('rows', {}).get('input_rows')}`",
        f"- prepared_rows: `{report.get('rows', {}).get('prepared_rows')}`",
        "",
        "## Definitions",
        "",
    ]
    for key, value in report.get("definition", {}).items():
        lines.append(f"- {key}: `{value}`")

    for market, payload in report.get("markets", {}).items():
        lines.extend(["", f"## {market}", ""])
        lines.append(f"- rows: `{payload.get('rows')}`")
        lines.extend(["", "| Cohort | 1D | 3D | 5D | Path Quality |", "|---|---:|---:|---:|---:|"])
        for cohort, row in payload.get("cohorts", {}).items():
            horizons = row.get("horizons", {})
            lines.append(
                f"| {cohort} | {_fmt_horizon(horizons.get('1D', {}))} | "
                f"{_fmt_horizon(horizons.get('3D', {}))} | "
                f"{_fmt_horizon(horizons.get('5D', {}))} | "
                f"{_fmt_path(row.get('path', {}))} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Track Top1/Top5/Exception/Practical-gate cohort performance.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    df = _load_rows(Path(args.input))
    report = build_report(df)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "scan_cohort_performance.json"
    md_path = output_dir / "scan_cohort_performance.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "md": str(md_path), "prepared_rows": report["rows"]["prepared_rows"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
