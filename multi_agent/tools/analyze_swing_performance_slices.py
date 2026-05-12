#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"

NUMERIC_COLUMNS = [
    "return_5d_pct",
    "return_3d_pct",
    "return_7d_pct",
    "priority_rank",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "decision_score",
    "whale_score",
    "volume_ratio",
    "relative_rank_score",
    "relative_rank_pct",
    "loss_risk_score",
]

SELECT_COLUMNS = ",".join(
    [
        "id",
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "feature_origin",
        "decision",
        "decision_bucket",
        "priority_rank",
        "expected_edge_score",
        "expected_return_1d_pct",
        "expected_return_3d_pct",
        "alpha_score",
        "tech_score",
        "ml_prob",
        "prob_clean",
        "decision_score",
        "whale_score",
        "volume_ratio",
        "relative_rank_score",
        "relative_rank_pct",
        "loss_risk_score",
        "return_5d_pct",
        "return_3d_pct",
        "return_7d_pct",
        "recommended_at",
    ]
)


def _load_rows(market: str) -> pd.DataFrame:
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        query = db.client.table("market_scan_results").select(SELECT_COLUMNS).eq("scan_mode", "SWING")
        if market == "KOSDAQ":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KQ")
        elif market == "KOSPI":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KS")
        else:
            query = query.eq("market", market)
        res = query.range(page * page_size, page * page_size + page_size - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[df["return_5d_pct"].notna()].copy()


def _summary(df: pd.DataFrame, name: str, mask: pd.Series) -> Dict[str, Any] | None:
    group = df[mask].copy()
    if group.empty:
        return None
    ret = group["return_5d_pct"]
    return {
        "slice": name,
        "n": int(len(group)),
        "win_5d_pct": round(float(ret.gt(0).mean() * 100.0), 3),
        "avg_5d_pct": round(float(ret.mean()), 4),
        "median_5d_pct": round(float(ret.median()), 4),
        "hit_5pct_within_close5_pct": round(float(ret.ge(5).mean() * 100.0), 3),
        "min_5d_pct": round(float(ret.min()), 4),
        "max_5d_pct": round(float(ret.max()), 4),
    }


def _slice_masks(df: pd.DataFrame) -> List[Tuple[str, pd.Series]]:
    true_mask = pd.Series(True, index=df.index)
    masks: List[Tuple[str, pd.Series]] = [
        ("all_resolved_5d", true_mask),
        ("rank_top5", df["priority_rank"].between(1, 5, inclusive="both")),
        ("rank_top3", df["priority_rank"].between(1, 3, inclusive="both")),
        ("rank_top2", df["priority_rank"].between(1, 2, inclusive="both")),
        ("rank1", df["priority_rank"].eq(1)),
        ("bucket_exception_leader", df["decision_bucket"].eq("exception_leader")),
        ("bucket_picked", df["decision_bucket"].eq("picked")),
        ("bucket_watchlist", df["decision_bucket"].eq("watchlist")),
    ]
    for edge in [4, 5, 6, 7, 8, 9, 10]:
        masks.append((f"edge_ge_{edge}", df["expected_edge_score"].ge(edge)))
    for score in [80, 85, 90, 95]:
        masks.append((f"decision_score_ge_{score}", df["decision_score"].ge(score)))
    for loss in [30, 40, 50, 60]:
        masks.append((f"loss_risk_le_{loss}", df["loss_risk_score"].le(loss)))
    for volume in [1.5, 2, 3, 5]:
        masks.append((f"volume_ratio_ge_{volume}", df["volume_ratio"].ge(volume)))
    for prob in [45, 50, 55, 60]:
        masks.append((f"prob_clean_ge_{prob}", df["prob_clean"].ge(prob)))
    for alpha in [75, 80, 85, 90]:
        masks.append((f"alpha_ge_{alpha}", df["alpha_score"].ge(alpha)))
    for whale in [50, 60, 70, 80]:
        masks.append((f"whale_ge_{whale}", df["whale_score"].ge(whale)))
    for edge in [5, 6, 7, 8]:
        for score in [85, 90, 95]:
            masks.append(
                (
                    f"edge_ge_{edge}__decision_score_ge_{score}",
                    df["expected_edge_score"].ge(edge) & df["decision_score"].ge(score),
                )
            )
    for rank_max in [3, 5]:
        for edge in [5, 6, 7]:
            masks.append(
                (
                    f"rank_top{rank_max}__edge_ge_{edge}",
                    df["priority_rank"].between(1, rank_max, inclusive="both") & df["expected_edge_score"].ge(edge),
                )
            )
    masks.extend(
        [
            (
                "edge_ge_5__or__decision_score_ge_95",
                df["expected_edge_score"].ge(5) | df["decision_score"].ge(95),
            ),
            (
                "edge_ge_6__or__decision_score_ge_95",
                df["expected_edge_score"].ge(6) | df["decision_score"].ge(95),
            ),
            (
                "rank_top5__or__edge_ge_5",
                df["priority_rank"].between(1, 5, inclusive="both") | df["expected_edge_score"].ge(5),
            ),
            (
                "exception_leader__or__edge_ge_5",
                df["decision_bucket"].eq("exception_leader") | df["expected_edge_score"].ge(5),
            ),
        ]
    )
    base_masks = [
        ("exception_leader", df["decision_bucket"].eq("exception_leader")),
        ("rank_top5", df["priority_rank"].between(1, 5, inclusive="both")),
        ("rank_top3", df["priority_rank"].between(1, 3, inclusive="both")),
        ("edge_ge_8", df["expected_edge_score"].ge(8)),
        ("score_ge_95", df["decision_score"].ge(95)),
    ]
    risk_masks = []
    for loss in [30, 40, 50, 60]:
        risk_masks.append((f"loss_le_{loss}", df["loss_risk_score"].le(loss)))
    for volume in [2, 3, 5]:
        risk_masks.append((f"volume_ge_{volume}", df["volume_ratio"].ge(volume)))
    for prob in [50, 55, 60]:
        risk_masks.append((f"prob_clean_ge_{prob}", df["prob_clean"].ge(prob)))
    for alpha in [80, 85, 90]:
        risk_masks.append((f"alpha_ge_{alpha}", df["alpha_score"].ge(alpha)))
    for whale in [60, 70, 80]:
        risk_masks.append((f"whale_ge_{whale}", df["whale_score"].ge(whale)))
    for base_name, base_mask in base_masks:
        for risk_name, risk_mask in risk_masks:
            masks.append((f"{base_name}__{risk_name}", base_mask & risk_mask))
    return masks


def build_report(market: str, min_n: int) -> Dict[str, Any]:
    df = _load_rows(market)
    summaries = [
        row
        for name, mask in _slice_masks(df)
        if (row := _summary(df, name, mask)) is not None and row["n"] >= min_n
    ]
    target_pass = [
        row
        for row in summaries
        if row["win_5d_pct"] >= 70.0 and row["avg_5d_pct"] >= 5.0
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "resolved_5d_rows": int(len(df)),
        "min_n": int(min_n),
        "target": {"win_5d_pct": 70.0, "avg_5d_pct": 5.0},
        "slices": summaries,
        "target_pass_slices": sorted(target_pass, key=lambda row: (-row["n"], -row["avg_5d_pct"])),
        "best_by_avg": sorted(summaries, key=lambda row: (-row["avg_5d_pct"], -row["win_5d_pct"]))[:10],
        "best_by_win": sorted(summaries, key=lambda row: (-row["win_5d_pct"], -row["avg_5d_pct"]))[:10],
    }


def _write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        f"# {report['market']} SWING 5D Slice Validation",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- resolved_5d_rows: `{report['resolved_5d_rows']}`",
        f"- target: `win_5d >= 70%, avg_5d >= +5%`",
        "",
        "## Target-Passing Slices",
        "",
    ]
    for row in report.get("target_pass_slices", []):
        lines.append(
            f"- {row['slice']}: n={row['n']}, win5={row['win_5d_pct']}%, "
            f"avg5={row['avg_5d_pct']}%, hit5={row['hit_5pct_within_close5_pct']}%, med5={row['median_5d_pct']}%"
        )
    lines.extend(["", "## Best By Avg", ""])
    for row in report.get("best_by_avg", []):
        lines.append(
            f"- {row['slice']}: n={row['n']}, win5={row['win_5d_pct']}%, avg5={row['avg_5d_pct']}%"
        )
    lines.extend(["", "## Best By Win", ""])
    for row in report.get("best_by_win", []):
        lines.append(
            f"- {row['slice']}: n={row['n']}, win5={row['win_5d_pct']}%, avg5={row['avg_5d_pct']}%"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="KOSPI", choices=["KOSPI", "KOSDAQ"])
    parser.add_argument("--min-n", type=int, default=30)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(args.market, min_n=args.min_n)
    stem = f"{args.market.lower()}_swing_5d_slice_validation"
    json_path = REPORT_DIR / f"{stem}.json"
    md_path = REPORT_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"json": str(json_path), "md": str(md_path), "target_pass_slices": len(report["target_pass_slices"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
