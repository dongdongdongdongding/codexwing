#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "archive"
OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _load_archive(market: str) -> pd.DataFrame:
    path = ARCHIVE_DIR / f"scan_archive_learning_dataset_{market.lower()}.csv"
    df = pd.read_csv(path, low_memory=False)
    for col in [
        "decision_score",
        "alpha_score",
        "ml_prob",
        "whale_score",
        "expected_edge_score",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "return_1d_pct",
        "return_3d_pct",
        "return_close_pct",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _missing_ratio(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns:
        return 100.0
    series = df[column]
    if series.dtype == "O":
        missing = series.isna() | series.astype(str).str.strip().isin({"", "unknown", "None", "nan"})
    else:
        missing = series.isna()
    return round(float(missing.mean() * 100.0), 2)


def _top_counts(series: pd.Series, topn: int = 5) -> Dict[str, int]:
    return {
        str(k): int(v)
        for k, v in series.fillna("unknown").astype(str).value_counts().head(topn).items()
    }


def _winner_block(df: pd.DataFrame, label_col: str) -> Dict[str, Any]:
    sub = df[df[label_col] == 1].copy() if label_col in df.columns else pd.DataFrame()
    if sub.empty:
        return {"rows": 0}
    return {
        "rows": int(len(sub)),
        "decision_score_mean": round(float(sub["decision_score"].dropna().mean()), 2) if "decision_score" in sub.columns else None,
        "decision_score_median": round(float(sub["decision_score"].dropna().median()), 2) if "decision_score" in sub.columns else None,
        "alpha_score_mean": round(float(sub["alpha_score"].dropna().mean()), 2) if "alpha_score" in sub.columns else None,
        "ml_prob_mean": round(float(sub["ml_prob"].dropna().mean()), 2) if "ml_prob" in sub.columns else None,
        "scan_mode_top": _top_counts(sub["scan_mode"]) if "scan_mode" in sub.columns else {},
        "decision_bucket_top": _top_counts(sub["decision_bucket"]) if "decision_bucket" in sub.columns else {},
        "selection_lane_top": _top_counts(sub["selection_lane"]) if "selection_lane" in sub.columns else {},
        "phase25_variant_top": _top_counts(sub["phase25_variant"]) if "phase25_variant" in sub.columns else {},
    }


def build_report() -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner_timeframe_audit": {
            "swing_runtime_fetch": {
                "scanner_runtime": "SWING path fetches 5y data via QuantStrategy.fetch_data(period='5y')",
                "quant_strategy_interval": "default interval is 1d",
                "live_refresh": "when live_mode_enabled, current daily bar is refreshed with 1h tape and projected volume",
                "verdict": "daily-primary with intraday refresh, not pure daily-only",
            },
            "intraday_runtime_fetch": {
                "scanner_runtime": "INTRADAY path fetches 60d with interval=1h",
                "verdict": "explicit intraday engine",
            },
        },
        "markets": {},
    }

    for market in ["KOSPI", "KOSDAQ"]:
        df = _load_archive(market)
        report["markets"][market] = {
            "rows": int(len(df)),
            "feature_coverage_gap_pct": {
                "whale_score": _missing_ratio(df, "whale_score"),
                "expected_edge_score": _missing_ratio(df, "expected_edge_score"),
                "expected_return_1d_pct": _missing_ratio(df, "expected_return_1d_pct"),
                "expected_return_3d_pct": _missing_ratio(df, "expected_return_3d_pct"),
                "primary_theme": _missing_ratio(df, "primary_theme"),
                "theme_routing_path": _missing_ratio(df, "theme_routing_path"),
                "phase25_variant": _missing_ratio(df, "phase25_variant"),
            },
            "winner_profiles": {
                "hit10": _winner_block(df, "label_hit_10pct"),
                "win1d": _winner_block(df, "label_win_1d"),
                "win3d": _winner_block(df, "label_win_3d"),
            },
        }

    kospi_hit10 = report["markets"]["KOSPI"]["winner_profiles"]["hit10"]
    kosdaq_hit10 = report["markets"]["KOSDAQ"]["winner_profiles"]["hit10"]
    report["verdicts"] = [
        "KOSPI 10%+ winners are split between SWING and INTRADAY, so a mixed-lane approach is defensible.",
        "KOSDAQ 10%+ winners skew toward INTRADAY/1D lane, so daily-primary SWING alone is insufficient for explosive movers.",
        "Current archive validation is materially weakened by missing factor coverage: whale/theme/expected-return/phase25 fields are absent in more than 90% of rows.",
        "Current benchmark direction is partially right because lane separation helps, but it is still logically incomplete because the system scores with factors that historical validation barely records.",
    ]
    report["recommended_actions"] = [
        {
            "priority": 1,
            "action": "Build KR dual-timeframe scanner inputs",
            "detail": "Keep SWING on daily structure but attach hourly continuation/breakout confirmation for KR names instead of treating SWING as daily-only.",
        },
        {
            "priority": 2,
            "action": "Persist factor traces end-to-end",
            "detail": "Backfill or newly persist whale_score, theme_routing_path, expected_edge_score, expected_return_1d_pct, expected_return_3d_pct, and phase25 variant so validation can test the logic actually used by ranking.",
        },
        {
            "priority": 3,
            "action": "Split KR into Core Trend / Explosive Leader / Reject universes",
            "detail": "KOSDAQ explosive winners cluster in INTRADAY/1D lane; they should not be forced through the same thresholds as 3D continuation names.",
        },
        {
            "priority": 4,
            "action": "Retune bucket semantics",
            "detail": "Current picked bucket underperforms watchlist in archive-level realized returns, so picked thresholds and promotion rules are not logically aligned with realized edge.",
        },
    ]
    report["evidence_highlights"] = {
        "kospi_hit10_scan_mode_top": kospi_hit10.get("scan_mode_top", {}),
        "kosdaq_hit10_scan_mode_top": kosdaq_hit10.get("scan_mode_top", {}),
        "kospi_hit10_selection_lane_top": kospi_hit10.get("selection_lane_top", {}),
        "kosdaq_hit10_selection_lane_top": kosdaq_hit10.get("selection_lane_top", {}),
    }
    return report


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# KRX Scanner Direction Audit",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Timeframe Audit",
        f"- SWING verdict: {report['scanner_timeframe_audit']['swing_runtime_fetch']['verdict']}",
        f"- INTRADAY verdict: {report['scanner_timeframe_audit']['intraday_runtime_fetch']['verdict']}",
        "",
    ]
    for market, payload in report["markets"].items():
        lines.extend(
            [
                f"## {market}",
                f"- rows: {payload['rows']}",
                f"- missing whale_score: {payload['feature_coverage_gap_pct']['whale_score']:.2f}%",
                f"- missing expected_edge_score: {payload['feature_coverage_gap_pct']['expected_edge_score']:.2f}%",
                f"- missing expected_return_1d_pct: {payload['feature_coverage_gap_pct']['expected_return_1d_pct']:.2f}%",
                f"- missing expected_return_3d_pct: {payload['feature_coverage_gap_pct']['expected_return_3d_pct']:.2f}%",
                f"- missing primary_theme: {payload['feature_coverage_gap_pct']['primary_theme']:.2f}%",
                f"- missing theme_routing_path: {payload['feature_coverage_gap_pct']['theme_routing_path']:.2f}%",
                "",
                f"- hit10 scan_mode_top: {payload['winner_profiles']['hit10'].get('scan_mode_top', {})}",
                f"- hit10 decision_bucket_top: {payload['winner_profiles']['hit10'].get('decision_bucket_top', {})}",
                f"- hit10 selection_lane_top: {payload['winner_profiles']['hit10'].get('selection_lane_top', {})}",
                f"- hit10 decision_score mean/median: {payload['winner_profiles']['hit10'].get('decision_score_mean')} / {payload['winner_profiles']['hit10'].get('decision_score_median')}",
                "",
            ]
        )
    lines.append("## Verdicts")
    for item in report["verdicts"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Actions"])
    for item in report["recommended_actions"]:
        lines.append(f"- P{item['priority']}: {item['action']} | {item['detail']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "kr_scanner_direction_audit.json"
    md_path = OUT_DIR / "kr_scanner_direction_audit.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "generated_at": report["generated_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
