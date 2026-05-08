"""Shadow validation for the US→KR theme transfer artifact.

For each edge, measure how well its prediction (US_direction × relationship)
aligns with realized KR primary_theme outcomes in the archive. Emits a JSON
and Markdown report before the transfer is wired into pre-open scoring.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from modules.theme_transfer import ARTIFACT_PATH, _canonical_kr_theme_id, load_transfer_artifact


def _load_archive(archive_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(archive_csv, low_memory=False)
    df = df[df["market"].isin(["KOSPI", "KOSDAQ"])].copy()
    df["return_3d_pct"] = pd.to_numeric(df["return_3d_pct"], errors="coerce")
    df["return_1d_pct"] = pd.to_numeric(df["return_1d_pct"], errors="coerce")
    df["label_hit_5pct"] = pd.to_numeric(df["label_hit_5pct"], errors="coerce")
    df["theme_id"] = df["primary_theme"].apply(lambda v: _canonical_kr_theme_id(str(v) if pd.notna(v) else ""))
    df = df[df["return_3d_pct"].notna() & (df["theme_id"] != "")]
    return df


def build_validation(artifact: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    grouped = df.groupby("theme_id")
    # KR-side baseline per theme_id.
    baselines: Dict[str, Dict[str, float]] = {}
    for tid, group in grouped:
        r3 = group["return_3d_pct"].astype(float)
        baselines[tid] = {
            "n": int(len(group)),
            "avg_3d": round(float(r3.mean()), 4),
            "win_rate": round(float((r3 >= 0).mean()), 4),
            "hit5": round(float(group["label_hit_5pct"].fillna(0).mean()), 4),
        }

    overall_mean = round(float(df["return_3d_pct"].mean()), 4)
    overall_win = round(float((df["return_3d_pct"] >= 0).mean()), 4)

    edge_reports: List[Dict[str, Any]] = []
    for edge in artifact.get("edges", []) or []:
        tid = edge.get("target_theme_id")
        base = baselines.get(tid)
        edge_reports.append(
            {
                "source_theme_id": edge.get("source_theme_id"),
                "target_theme_id": tid,
                "relationship": edge.get("relationship"),
                "confidence": edge.get("confidence"),
                "target_sample_n": base.get("n") if base else 0,
                "target_avg_3d": base.get("avg_3d") if base else None,
                "target_win_rate": base.get("win_rate") if base else None,
                "target_hit5": base.get("hit5") if base else None,
                "delta_vs_overall_avg_3d": (
                    round(base["avg_3d"] - overall_mean, 4) if base else None
                ),
            }
        )

    # Ranking: edges by confidence × target_sample_n × delta
    def _impact_score(row: Dict[str, Any]) -> float:
        conf = float(row.get("confidence") or 0.0)
        delta = float(row.get("delta_vs_overall_avg_3d") or 0.0)
        n = int(row.get("target_sample_n") or 0)
        return conf * max(0.0, delta) * min(n, 500) / 500.0

    ranked = sorted(edge_reports, key=_impact_score, reverse=True)

    return {
        "artifact_version": artifact.get("version"),
        "generated_from_rows": int(len(df)),
        "overall_baseline": {"avg_3d": overall_mean, "win_rate": overall_win},
        "per_edge": edge_reports,
        "top_5_impact_edges": ranked[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow validation report for theme_transfer artifact.")
    parser.add_argument("--artifact", type=str, default=str(ARTIFACT_PATH))
    parser.add_argument("--archive-csv", type=str, default="runtime_state/reports/archive/scan_archive_learning_dataset_all.csv")
    parser.add_argument("--out-dir", type=str, default="runtime_state/reports/theme_validation")
    args = parser.parse_args()

    artifact = load_transfer_artifact(Path(args.artifact))
    if not artifact.get("edges"):
        print(json.dumps({"error": "artifact missing or empty", "path": args.artifact}))
        return 1
    archive = Path(args.archive_csv)
    if not archive.exists():
        print(json.dumps({"error": "archive_csv not found", "path": str(archive)}))
        return 1

    df = _load_archive(archive)
    report = build_validation(artifact, df)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"theme_transfer_shadow_validation"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Theme Transfer Shadow Validation",
        "",
        f"- artifact_version: {report['artifact_version']}",
        f"- generated_from_rows: {report['generated_from_rows']}",
        f"- overall_baseline: avg_3d={report['overall_baseline']['avg_3d']} win_rate={report['overall_baseline']['win_rate']}",
        "",
        "## Top Impact Edges",
    ]
    for row in report.get("top_5_impact_edges", []):
        lines.append(
            f"- {row['source_theme_id']} → {row['target_theme_id']} ({row['relationship']}) "
            f"conf={row['confidence']} n={row['target_sample_n']} avg3d={row['target_avg_3d']} "
            f"win={row['target_win_rate']} Δoverall={row['delta_vs_overall_avg_3d']}"
        )
    lines.extend(["", "## All Edges", ""])
    for row in report.get("per_edge", []):
        lines.append(
            f"- {row['source_theme_id']:20} → {row['target_theme_id']:25} "
            f"rel={row['relationship']:8} conf={row['confidence']} "
            f"n={row['target_sample_n']} avg3d={row['target_avg_3d']} "
            f"win={row['target_win_rate']} hit5={row['target_hit5']}"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"json": str(json_path), "md": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
