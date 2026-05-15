from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT_DIR = ROOT / "runtime_state/reports/validation"


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _false_or_missing(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"", "0", "false", "none", "null", "no"})


def _true_values(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "yes"})


def _base_swing_mask(df: pd.DataFrame, market: str, *, strict_quality: bool) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    if "scan_mode" in df.columns:
        mask &= df["scan_mode"].fillna("").astype(str).str.upper().eq("SWING")
    if "market_type" in df.columns:
        mask &= df["market_type"].fillna("").astype(str).str.upper().eq("KR")
    ticker = df["ticker"].fillna("").astype(str) if "ticker" in df.columns else pd.Series("", index=df.index)
    if market == "KOSPI":
        mask &= ticker.str.upper().str.endswith(".KS")
    elif market == "KOSDAQ":
        mask &= ticker.str.upper().str.endswith(".KQ")
    if strict_quality and "validation_excluded" in df.columns:
        mask &= _false_or_missing(df["validation_excluded"])
    if "is_dummy_data" in df.columns:
        mask &= _false_or_missing(df["is_dummy_data"])
    return mask


def _policy_mask(df: pd.DataFrame, market: str, *, strict_quality: bool) -> pd.Series:
    mask = _base_swing_mask(df, market, strict_quality=strict_quality)
    bucket = (
        df["decision_bucket"].fillna("").astype(str).str.lower()
        if "decision_bucket" in df.columns
        else pd.Series("", index=df.index)
    )
    decision = (
        df["decision"].fillna("").astype(str).str.upper()
        if "decision" in df.columns
        else pd.Series("", index=df.index)
    )
    exception = bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")
    if market == "KOSPI":
        edge = _as_numeric(df["expected_edge_score"]) if "expected_edge_score" in df.columns else pd.Series(float("nan"), index=df.index)
        return mask & (exception | edge.ge(5.0))
    if market == "KOSDAQ":
        trend = (
            df["trend"].fillna("").astype(str).str.upper()
            if "trend" in df.columns
            else pd.Series("", index=df.index)
        )
        return mask & exception & trend.eq("UP")
    return mask


def _metric_block(df: pd.DataFrame, market: str, *, strict_quality: bool) -> Dict[str, Any]:
    policy = _policy_mask(df, market, strict_quality=strict_quality)
    sub = df.loc[policy].copy()
    ret5 = _as_numeric(sub["return_5d_pct"]) if "return_5d_pct" in sub.columns else pd.Series(dtype="float")
    ret5 = ret5.dropna()
    target_definition = "forward_high_within_5d"
    if "max_high_return_5d_pct" in sub.columns:
        target_source = _as_numeric(sub.loc[:, "max_high_return_5d_pct"]).dropna()
        if "hit_5pct_within_5d" in sub.columns:
            target_hit_series = _true_values(sub.loc[target_source.index, "hit_5pct_within_5d"])
        else:
            target_hit_series = target_source.ge(5.0)
    elif "max_return_observed_pct" in sub.columns:
        target_definition = "legacy_max_close_return_observed"
        target_source = _as_numeric(sub.loc[ret5.index, "max_return_observed_pct"]).dropna()
        target_hit_series = target_source.ge(5.0)
    else:
        target_definition = "fallback_return_5d_close"
        target_source = ret5
        target_hit_series = target_source.ge(5.0)
    rows = int(len(ret5))
    target_rows = int(len(target_source))
    win_rate = float((ret5.gt(0).mean() * 100.0)) if rows else None
    avg_return = float(ret5.mean()) if rows else None
    median_return = float(ret5.median()) if rows else None
    min_return = float(ret5.min()) if rows else None
    max_return = float(ret5.max()) if rows else None
    loss5_rate = float((ret5.le(-5.0).mean() * 100.0)) if rows else None
    hit5_close_rate = float((ret5.ge(5.0).mean() * 100.0)) if rows else None
    target_hit = float((target_hit_series.mean() * 100.0)) if target_rows else None
    avg_target_return = float(target_source.mean()) if target_rows else None
    median_target_return = float(target_source.median()) if target_rows else None
    min_target_return = float(target_source.min()) if target_rows else None
    max_target_return = float(target_source.max()) if target_rows else None
    target_pass = (
        target_rows >= 30
        and avg_target_return is not None
        and target_hit is not None
        and target_hit >= 70.0
        and avg_target_return >= 5.0
    )
    close_quality_pass = (
        rows >= 30
        and target_rows >= 30
        and win_rate is not None
        and target_hit is not None
        and avg_return is not None
        and win_rate >= 70.0
        and target_hit >= 70.0
        and avg_return >= 5.0
    )
    policy_label = "exception_leader OR expected_edge_score>=5" if market == "KOSPI" else "exception_leader AND trend=UP"
    return {
        "market": market,
        "policy": policy_label,
        "rows": rows,
        "target_rows": target_rows,
        "target_definition": target_definition,
        "win_5d_pct": round(win_rate, 3) if win_rate is not None else None,
        "hit_5pct_within_5d_high_pct": round(target_hit, 3) if target_hit is not None else None,
        "avg_max_high_return_5d_pct": round(avg_target_return, 4) if avg_target_return is not None else None,
        "median_max_high_return_5d_pct": round(median_target_return, 4) if median_target_return is not None else None,
        "min_max_high_return_5d_pct": round(min_target_return, 4) if min_target_return is not None else None,
        "max_max_high_return_5d_pct": round(max_target_return, 4) if max_target_return is not None else None,
        "hit_5pct_within_observed_5d_pct": round(target_hit, 3) if target_hit is not None else None,
        "avg_return_5d_pct": round(avg_return, 4) if avg_return is not None else None,
        "median_return_5d_pct": round(median_return, 4) if median_return is not None else None,
        "min_return_5d_pct": round(min_return, 4) if min_return is not None else None,
        "max_return_5d_pct": round(max_return, 4) if max_return is not None else None,
        "loss_5pct_or_worse_5d_pct": round(loss5_rate, 3) if loss5_rate is not None else None,
        "hit_5pct_or_better_close_5d_pct": round(hit5_close_rate, 3) if hit5_close_rate is not None else None,
        "avg_max_return_observed_5d_pct": round(avg_target_return, 4) if avg_target_return is not None else None,
        "passes_goal": bool(target_pass),
        "close_5d_quality_pass": bool(close_quality_pass),
    }


def build_live_policy_report(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": int(len(df)),
        "quality_scope": "observed_archive",
        "quality_note": "Observed policy performance ignores legacy validation_excluded flags so old resolved rows can be audited. Use --strict-quality for gold-style feature-complete validation.",
        "goal": {
            "win_5d_pct_min": 70.0,
            "hit_5pct_within_5d_high_pct_min": 70.0,
            "avg_max_high_return_5d_pct_min": 5.0,
            "min_rows": 30,
        },
        "policies": [
            _metric_block(df, "KOSPI", strict_quality=False),
            _metric_block(df, "KOSDAQ", strict_quality=False),
        ],
    }


def build_strict_live_policy_report(df: pd.DataFrame) -> Dict[str, Any]:
    report = build_live_policy_report(df)
    report["quality_scope"] = "strict_feature_complete"
    report["quality_note"] = "Strict policy performance excludes validation_excluded and dummy rows."
    report["policies"] = [
        _metric_block(df, "KOSPI", strict_quality=True),
        _metric_block(df, "KOSDAQ", strict_quality=True),
    ]
    return report


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Live Swing Policy Performance",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- quality_scope: `{report.get('quality_scope')}`",
        f"- quality_note: {report.get('quality_note')}",
        "- goal: source OHLCV High 기준 hit_5pct_within_5d >= 70%, avg_max_high_return_5d >= +5%, target_rows >= 30",
        "",
        "## Policies",
    ]
    for row in report.get("policies", []) or []:
        lines.extend(
            [
                "",
                f"### {row.get('market')}",
                f"- policy: `{row.get('policy')}`",
                f"- rows: `{row.get('rows')}`",
                f"- target_rows: `{row.get('target_rows')}`",
                f"- target_definition: `{row.get('target_definition')}`",
                f"- win_5d_pct: `{row.get('win_5d_pct')}`",
                f"- hit_5pct_within_5d_high_pct: `{row.get('hit_5pct_within_5d_high_pct')}`",
                f"- avg_max_high_return_5d_pct: `{row.get('avg_max_high_return_5d_pct')}`",
                f"- median_max_high_return_5d_pct: `{row.get('median_max_high_return_5d_pct')}`",
                f"- min_max_high_return_5d_pct: `{row.get('min_max_high_return_5d_pct')}`",
                f"- max_max_high_return_5d_pct: `{row.get('max_max_high_return_5d_pct')}`",
                f"- hit_5pct_within_observed_5d_pct: `{row.get('hit_5pct_within_observed_5d_pct')}`",
                f"- avg_return_5d_pct: `{row.get('avg_return_5d_pct')}`",
                f"- median_return_5d_pct: `{row.get('median_return_5d_pct')}`",
                f"- min_return_5d_pct: `{row.get('min_return_5d_pct')}`",
                f"- max_return_5d_pct: `{row.get('max_return_5d_pct')}`",
                f"- loss_5pct_or_worse_5d_pct: `{row.get('loss_5pct_or_worse_5d_pct')}`",
                f"- hit_5pct_or_better_close_5d_pct: `{row.get('hit_5pct_or_better_close_5d_pct')}`",
                f"- avg_max_return_observed_5d_pct: `{row.get('avg_max_return_observed_5d_pct')}`",
                f"- passes_goal: `{row.get('passes_goal')}`",
                f"- close_5d_quality_pass: `{row.get('close_5d_quality_pass')}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate live KOSPI/KOSDAQ swing policy performance.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--strict-quality", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"input not found: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    report = build_strict_live_policy_report(df) if args.strict_quality else build_live_policy_report(df)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "strict" if args.strict_quality else "observed"
    json_path = out_dir / f"live_swing_policy_performance_{suffix}.json"
    md_path = out_dir / f"live_swing_policy_performance_{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
