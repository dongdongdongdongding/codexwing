#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.phase25_governance import phase25_oos_validates, phase25_weak_oos_reasons


DEFAULT_INPUT = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "retrain_v2_report.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def build_phase25_governance_report(payload: Dict[str, Any], *, generated_at: str | None = None) -> Dict[str, Any]:
    segments = payload.get("segments") or []
    rows: List[Dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        oos = segment.get("oos_holdout") or {}
        oos_auc = _first(segment.get("oos_auc"), oos.get("auc"))
        oos_win = _first(segment.get("oos_win_rate_pct"), oos.get("win_rate_pct"))
        oos_avg = _first(segment.get("oos_avg_return_pct"), oos.get("avg_return_pct"))
        cv_auc = segment.get("cv_median_auc")
        cv_oos_auc_gap = _gap(cv_auc, oos_auc)
        oos_n = _first(segment.get("oos_n"), oos.get("picks"))
        weak_reasons = phase25_weak_oos_reasons(
            oos_auc=oos_auc,
            oos_win_rate_pct=oos_win,
            oos_avg_return_pct=oos_avg,
            oos_n=oos_n,
            signal_direction=segment.get("signal_direction"),
        )
        oos_release_ready = phase25_oos_validates(
            oos_auc=oos_auc,
            oos_win_rate_pct=oos_win,
            oos_avg_return_pct=oos_avg,
            oos_n=oos_n,
        )
        action = "allow_phase25_probability"
        if weak_reasons:
            action = "neutralize_probability_and_block_priority"
        elif not oos_release_ready:
            action = "shadow_only_until_oos_release_ready"
        rows.append(
            {
                "name": segment.get("name"),
                "status": segment.get("status"),
                "rows": segment.get("rows"),
                "target_horizon_days": segment.get("target_horizon_days"),
                "return_col": segment.get("return_col"),
                "signal_direction": segment.get("signal_direction"),
                "raw_auc": segment.get("raw_auc", segment.get("auc")),
                "cv_median_auc": cv_auc,
                "oos_auc": oos_auc,
                "cv_oos_auc_gap": cv_oos_auc_gap,
                "oos_win_rate_pct": oos_win,
                "oos_avg_return_pct": oos_avg,
                "oos_release_ready": oos_release_ready,
                "weak_oos_reasons": weak_reasons,
                "action": action,
            }
        )
    release_ready = bool(rows) and all(row["oos_release_ready"] for row in rows)
    weak_rows = [row for row in rows if row["weak_oos_reasons"]]
    return {
        "report_version": "phase25_governance_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "source_generated_at": payload.get("generated_at"),
        "source_execution_status": payload.get("execution_status"),
        "rows_loaded": payload.get("rows_loaded"),
        "backend": payload.get("backend"),
        "release_ready": release_ready,
        "trained_segments": len(rows),
        "weak_segments": len(weak_rows),
        "segments": rows,
    }


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase25 Governance Report",
        "",
        f"- release_ready: `{report.get('release_ready')}`",
        f"- trained_segments: `{report.get('trained_segments')}`",
        f"- weak_segments: `{report.get('weak_segments')}`",
        f"- rows_loaded: `{report.get('rows_loaded')}`",
        "",
        "## Segment Actions",
        "",
    ]
    for row in report.get("segments") or []:
        reasons = ", ".join(row.get("weak_oos_reasons") or []) or "-"
        lines.append(
            f"- {row.get('name')}: action=`{row.get('action')}`, "
            f"oos_auc={_fmt(row.get('oos_auc'))}, win={_fmt(row.get('oos_win_rate_pct'))}%, "
            f"avg={_fmt(row.get('oos_avg_return_pct'))}%, "
            f"cv_oos_gap={_fmt(row.get('cv_oos_auc_gap'))}, reasons={reasons}"
        )
    return "\n".join(lines).strip() + "\n"


def write_report(report: Dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "phase25_governance.json"
    md_path = out_dir / "phase25_governance.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "-"


def _gap(left: Any, right: Any) -> float | None:
    try:
        return round(float(left) - float(right), 6)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase25 model governance validation report.")
    parser.add_argument("--input-json", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--fail-on-reject", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    report = build_phase25_governance_report(payload)
    paths = write_report(report, Path(args.output_dir))
    print(json.dumps({**paths, **report}, ensure_ascii=False, indent=2))
    if args.fail_on_reject and not report["release_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
