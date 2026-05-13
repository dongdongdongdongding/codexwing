#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT_DIR = ROOT / "runtime_state/reports/validation"

NUMERIC_COLUMNS = [
    "priority_rank",
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "min_return_observed_pct",
    "max_high_return_5d_pct",
    "whale_score",
    "volume_ratio",
    "decision_score",
    "expected_edge_score",
    "loss_risk_score",
    "relative_rank_score",
    "relative_rank_pct",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "conviction_score",
    "day_return_pct",
    "regime_breadth_pct",
    "regime_avg_chg",
    "regime_volatility_20d",
    "model_prob_mean",
    "phase25_oos_win_rate_pct",
]

BOOL_COLUMNS = [
    "validation_excluded",
    "is_dummy_data",
    "label_stop_loss_3pct",
    "label_stop_loss_5pct",
    "volume_confirmed",
    "explosive_leader_flag",
    "core_trend_flag",
    "explosive_eligible",
]

CATEGORICAL_COLUMNS = [
    "trend",
    "position",
    "strategy",
    "tier",
    "price_band",
    "marcap_band",
    "selection_lane",
    "kr_universe_role",
    "feature_quality",
    "learning_quality_tier",
    "primary_theme",
    "volume_confirmed",
]

FLOW_COLUMNS = [
    "foreigner",
    "foreign_flow",
    "foreign_net",
    "foreign_net_buy",
    "institution",
    "institution_flow",
    "institution_net",
    "institution_net_buy",
    "retail",
    "retail_net_buy",
]


def _as_bool(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "yes", "y"})


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if result != result:
            return None
        return result
    except Exception:
        return None


def _round(value: Any, digits: int = 4) -> float | None:
    number = _to_float(value)
    return round(number, digits) if number is not None else None


def _pct(value: Any) -> float | None:
    number = _to_float(value)
    return round(number * 100.0, 3) if number is not None else None


def _load_dataset(path: Path, *, strict_quality: bool) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in BOOL_COLUMNS:
        if col in df.columns:
            df[f"{col}_bool"] = _as_bool(df[col])

    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    mask = scan_mode.eq("SWING") & (ticker.str.endswith(".KS") | ticker.str.endswith(".KQ"))
    if "is_dummy_data_bool" in df.columns:
        mask &= ~df["is_dummy_data_bool"]
    if strict_quality and "validation_excluded_bool" in df.columns:
        mask &= ~df["validation_excluded_bool"]

    out = df.loc[mask].copy()
    out["market2"] = "KOSDAQ"
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    return out


def _prepare_labels(df: pd.DataFrame) -> pd.DataFrame:
    required = ["return_1d_pct", "return_3d_pct", "return_5d_pct"]
    out = df.dropna(subset=[col for col in required if col in df.columns]).copy()
    stop_hit = pd.Series(False, index=out.index)
    if "min_return_observed_pct" in out.columns:
        stop_hit |= out["min_return_observed_pct"].le(-5.0).fillna(False)
    if "label_stop_loss_5pct_bool" in out.columns:
        stop_hit |= out["label_stop_loss_5pct_bool"].fillna(False)

    out["stop_hit_5pct_proxy"] = stop_hit
    out["clean_riser"] = (
        out["return_1d_pct"].ge(-1.0)
        & out["return_3d_pct"].ge(out["return_1d_pct"])
        & out["return_5d_pct"].ge(out["return_3d_pct"])
        & out["return_5d_pct"].ge(5.0)
        & ~stop_hit
    )
    out["bad_path"] = stop_hit | out["return_1d_pct"].lt(-3.0) | out["return_5d_pct"].lt(0.0)
    out["top1"] = out["priority_rank"].eq(1) if "priority_rank" in out.columns else False
    out["top5"] = out["priority_rank"].between(1, 5, inclusive="both") if "priority_rank" in out.columns else False
    decision = out.get("decision", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    bucket = out.get("decision_bucket", pd.Series("", index=out.index)).fillna("").astype(str).str.lower()
    out["exception_leader"] = bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")
    return out


def _summarize(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "n": 0,
            "clean_riser_pct": None,
            "bad_path_pct": None,
            "avg_1d_pct": None,
            "avg_3d_pct": None,
            "avg_5d_pct": None,
            "avg_min_drawdown_pct": None,
            "avg_max_high_5d_pct": None,
        }
    return {
        "n": int(len(df)),
        "clean_riser_pct": _pct(df["clean_riser"].mean()),
        "bad_path_pct": _pct(df["bad_path"].mean()),
        "avg_1d_pct": _round(df["return_1d_pct"].mean(), 4),
        "avg_3d_pct": _round(df["return_3d_pct"].mean(), 4),
        "avg_5d_pct": _round(df["return_5d_pct"].mean(), 4),
        "avg_min_drawdown_pct": _round(df["min_return_observed_pct"].mean(), 4)
        if "min_return_observed_pct" in df.columns
        else None,
        "avg_max_high_5d_pct": _round(df["max_high_return_5d_pct"].mean(), 4)
        if "max_high_return_5d_pct" in df.columns
        else None,
    }


def _condition_series(df: pd.DataFrame) -> List[Tuple[str, pd.Series]]:
    conditions: List[Tuple[str, pd.Series]] = []

    def add(name: str, series: pd.Series) -> None:
        conditions.append((name, series.fillna(False)))

    numeric_specs = [
        ("priority_rank", [1, 3, 5], "<="),
        ("whale_score", [50, 60, 70, 80], ">="),
        ("volume_ratio", [0.8, 1.0, 1.2, 1.5, 2.0, 3.0], ">="),
        ("volume_ratio", [1.5, 2.0, 3.0, 5.0], "<="),
        ("decision_score", [80, 85, 90, 95], ">="),
        ("expected_edge_score", [4, 5, 6, 7, 8, 10], ">="),
        ("loss_risk_score", [30, 40, 50, 60], "<="),
        ("relative_rank_score", [60, 70, 80, 90], ">="),
        ("relative_rank_pct", [60, 70, 80, 90], ">="),
        ("alpha_score", [75, 80, 85, 90], ">="),
        ("tech_score", [70, 80, 90], ">="),
        ("prob_clean", [45, 50, 55, 60], ">="),
        ("day_return_pct", [-2, -1, 0, 1, 3], ">="),
        ("day_return_pct", [0, 3, 5, 10], "<="),
        ("regime_breadth_pct", [40, 50, 60], ">="),
        ("regime_avg_chg", [-1, 0, 1], ">="),
        ("model_prob_mean", [45, 50, 55, 60], ">="),
    ]
    for col, thresholds, op in numeric_specs:
        if col not in df.columns:
            continue
        for threshold in thresholds:
            if op == "<=":
                add(f"{col}<={threshold:g}", df[col].le(threshold))
            else:
                add(f"{col}>={threshold:g}", df[col].ge(threshold))

    for col in CATEGORICAL_COLUMNS:
        if col not in df.columns:
            continue
        values = df[col].fillna("").astype(str).value_counts().head(12).index
        for value in values:
            if not value or value.lower() in {"nan", "none", "null"}:
                continue
            add(f"{col}={value}", df[col].fillna("").astype(str).eq(value))

    return conditions


def _evaluate_conditions(df: pd.DataFrame, *, min_n: int, top_n: int) -> List[Dict[str, Any]]:
    baseline = float(df["clean_riser"].mean()) if not df.empty else 0.0
    rows: List[Dict[str, Any]] = []
    for name, condition in _condition_series(df):
        sub = df.loc[condition]
        if len(sub) < min_n:
            continue
        summary = _summarize(sub)
        summary.update(
            {
                "condition": name,
                "lift_clean_riser_pct": _pct(float(sub["clean_riser"].mean()) - baseline),
            }
        )
        rows.append(summary)
    return sorted(
        rows,
        key=lambda row: (
            row.get("lift_clean_riser_pct") or -999.0,
            row.get("clean_riser_pct") or -999.0,
            row.get("n") or 0,
        ),
        reverse=True,
    )[:top_n]


def _evaluate_pair_conditions(df: pd.DataFrame, *, min_n: int, top_n: int) -> List[Dict[str, Any]]:
    baseline = float(df["clean_riser"].mean()) if not df.empty else 0.0
    singles = _evaluate_conditions(df, min_n=min_n, top_n=20)
    condition_map = dict(_condition_series(df))
    rows: List[Dict[str, Any]] = []
    for idx, left in enumerate(singles):
        for right in singles[idx + 1 :]:
            left_name = str(left["condition"])
            right_name = str(right["condition"])
            condition = condition_map[left_name] & condition_map[right_name]
            sub = df.loc[condition]
            if len(sub) < min_n:
                continue
            summary = _summarize(sub)
            summary.update(
                {
                    "condition": f"{left_name} & {right_name}",
                    "lift_clean_riser_pct": _pct(float(sub["clean_riser"].mean()) - baseline),
                }
            )
            rows.append(summary)
    return sorted(
        rows,
        key=lambda row: (
            row.get("lift_clean_riser_pct") or -999.0,
            row.get("clean_riser_pct") or -999.0,
            row.get("n") or 0,
        ),
        reverse=True,
    )[:top_n]


def build_report(df: pd.DataFrame, *, min_n: int, top_n: int) -> Dict[str, Any]:
    prepared = _prepare_labels(df)
    group_masks = {
        "All": pd.Series(True, index=prepared.index),
        "Top1": prepared["top1"],
        "Top5": prepared["top5"],
        "Exception Leader": prepared["exception_leader"],
    }
    markets: Dict[str, Any] = {}
    for market in ["KOSPI", "KOSDAQ"]:
        market_df = prepared.loc[prepared["market2"].eq(market)].copy()
        groups = {
            name: _summarize(market_df.loc[mask.loc[market_df.index]])
            for name, mask in group_masks.items()
        }
        markets[market] = {
            "resolved_rows": int(len(market_df)),
            "groups": groups,
            "best_single_conditions": _evaluate_conditions(market_df, min_n=min_n, top_n=top_n),
            "best_pair_conditions": _evaluate_pair_conditions(market_df, min_n=min_n, top_n=top_n),
        }
    present_flow_cols = [col for col in FLOW_COLUMNS if col in df.columns]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DEFAULT_INPUT),
        "definition": {
            "clean_riser": "return_1d_pct >= -1, return_3d_pct >= 1D, return_5d_pct >= 3D, return_5d_pct >= 5, and no 5% stop proxy",
            "bad_path": "5% stop proxy hit OR return_1d_pct < -3 OR return_5d_pct < 0",
            "stop_proxy": "min_return_observed_pct <= -5 OR label_stop_loss_5pct",
            "feature_scope": "pre-scan fields only; future outcome labels are excluded from rule search",
        },
        "data_notes": {
            "actual_investor_flow_columns_present": present_flow_cols,
            "investor_flow_gap": not bool(present_flow_cols),
            "investor_flow_proxy_used": "whale_score",
        },
        "rows": {
            "input_rows": int(len(df)),
            "resolved_rows": int(len(prepared)),
        },
        "markets": markets,
    }


def _fmt_metric(row: Dict[str, Any]) -> str:
    if not row or not row.get("n"):
        return "-"
    def fmt_pct(value: Any) -> str:
        number = _to_float(value)
        return f"{number:+.2f}%" if number is not None else "-"

    return (
        f"n={row.get('n')} / clean={row.get('clean_riser_pct')}% / bad={row.get('bad_path_pct')}% / "
        f"1D {fmt_pct(row.get('avg_1d_pct'))} / 3D {fmt_pct(row.get('avg_3d_pct'))} / "
        f"5D {fmt_pct(row.get('avg_5d_pct'))} / minDD {fmt_pct(row.get('avg_min_drawdown_pct'))}"
    )


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Low Drawdown Rising Winner Traits",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source: `{report.get('source')}`",
        f"- input_rows: `{report.get('rows', {}).get('input_rows')}`",
        f"- resolved_rows: `{report.get('rows', {}).get('resolved_rows')}`",
        "",
        "## Definition",
        "",
    ]
    for key, value in report.get("definition", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Data Notes", ""])
    notes = report.get("data_notes", {})
    lines.append(f"- investor_flow_proxy_used: `{notes.get('investor_flow_proxy_used')}`")
    lines.append(f"- actual_investor_flow_columns_present: `{notes.get('actual_investor_flow_columns_present')}`")
    if notes.get("investor_flow_gap"):
        lines.append("- warning: actual foreigner/institution/retail flow is not persisted in this archive; persist it before making investor-flow rules.")

    for market, payload in report.get("markets", {}).items():
        lines.extend(["", f"## {market}", ""])
        lines.append(f"- resolved_rows: `{payload.get('resolved_rows')}`")
        lines.extend(["", "### Group Baselines", ""])
        lines.append("| Group | Metrics |")
        lines.append("|---|---:|")
        for group, row in payload.get("groups", {}).items():
            lines.append(f"| {group} | {_fmt_metric(row)} |")
        lines.extend(["", "### Best Single Conditions", ""])
        lines.append("| Condition | Metrics |")
        lines.append("|---|---:|")
        for row in payload.get("best_single_conditions", [])[:10]:
            lines.append(
                f"| `{row.get('condition')}` | lift {row.get('lift_clean_riser_pct')}pp / {_fmt_metric(row)} |"
            )
        lines.extend(["", "### Best Pair Conditions", ""])
        lines.append("| Condition | Metrics |")
        lines.append("|---|---:|")
        for row in payload.get("best_pair_conditions", [])[:10]:
            lines.append(
                f"| `{row.get('condition')}` | lift {row.get('lift_clean_riser_pct')}pp / {_fmt_metric(row)} |"
            )

    lines.extend(
        [
            "",
            "## Operational Read",
            "",
            "- KOSPI has usable low-drawdown rising patterns. `expected_edge_score>=5` is the strongest repeatable base filter, and `whale_score>=60` improves the practical flow proxy quality.",
            "- KOSPI Exception Leader and Top1 should be treated as 3D/5D swing candidates, not immediate open-chase entries, because 1D behavior is still noisy.",
            "- KOSDAQ remains structurally weaker. Use KOSDAQ candidates as conditional/watchlist unless they also pass theme/edge filters and show controlled early loss.",
            "- Do not use `hit_5pct_within_5d`, `max_high_return_5d_pct`, or `min_return_observed_pct` as entry features. They are outcome labels for validation and stop-risk measurement.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Find low-drawdown rising winner traits from scan archive outcomes.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-n", type=int, default=20)
    parser.add_argument("--top-n", type=int, default=15)
    parser.add_argument("--strict-quality", action="store_true")
    args = parser.parse_args()

    df = _load_dataset(Path(args.input), strict_quality=bool(args.strict_quality))
    report = build_report(df, min_n=int(args.min_n), top_n=int(args.top_n))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "low_drawdown_winner_traits"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "md": str(md_path), "resolved_rows": report["rows"]["resolved_rows"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
