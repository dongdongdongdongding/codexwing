from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def build_report(shared_working_root: Path, market: str, limit_runs: int) -> Dict[str, Any]:
    runs = sorted([p for p in shared_working_root.glob("RUN-*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    considered = 0
    theme_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    leader_examples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total_candidates = 0
    unclassified_count = 0
    routed_candidates = 0
    routed_stock_master = 0
    performance_buckets: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    route_status_counts: Dict[str, Counter[str]] = defaultdict(Counter)

    for run_dir in runs:
        if considered >= limit_runs:
            break
        scanner_path = run_dir / "scanner_handoff.json"
        if not scanner_path.exists():
            continue
        payload = _read_json(scanner_path)
        run_context = payload.get("run_context", {})
        if str(run_context.get("market", "")).upper() != str(market).upper():
            continue
        considered += 1
        for cand in payload.get("candidates", []) or []:
            if not isinstance(cand, dict):
                continue
            total_candidates += 1
            theme_context = cand.get("theme_context", {}) if isinstance(cand.get("theme_context"), dict) else {}
            leader_metrics = cand.get("leader_metrics", {}) if isinstance(cand.get("leader_metrics"), dict) else {}
            primary_theme = str(theme_context.get("primary_theme") or "").strip()
            theme_source = str(theme_context.get("theme_source") or "").strip() or "unknown"
            routing_path = str(cand.get("routing_path") or theme_context.get("routing_path") or "").strip() or "core_only"
            if primary_theme.lower() == "unclassified":
                unclassified_count += 1
            if primary_theme and primary_theme.lower() != "unclassified":
                theme_counts[primary_theme] += 1
                leader_examples[primary_theme].append(
                    {
                        "ticker": cand.get("ticker"),
                        "score": cand.get("score"),
                        "theme_rank": leader_metrics.get("theme_rank"),
                        "leader_score": leader_metrics.get("leader_score"),
                        "routing_path": routing_path,
                        "theme_source": theme_source,
                    }
                )
            route_counts[routing_path] += 1
            source_counts[theme_source] += 1
            if routing_path != "core_only":
                routed_candidates += 1
                if theme_source == "stock_master":
                    routed_stock_master += 1

        outcomes_path = run_dir / "realized_outcomes.json"
        if outcomes_path.exists():
            outcome_payload = _read_json(outcomes_path)
            for row in outcome_payload.get("outcomes", []) or []:
                if not isinstance(row, dict):
                    continue
                if str(row.get("market", "")).upper() != str(market).upper():
                    continue
                route = str(row.get("theme_routing_path") or "").strip() or "core_only"
                route_status_counts[route][str(row.get("status") or "UNKNOWN").upper()] += 1
                for horizon in ("1d", "3d", "5d"):
                    val = _safe_float(row.get(f"return_{horizon}_pct"))
                    if val is not None:
                        performance_buckets[route][horizon].append(val)

    top_themes = []
    for theme_name, count in theme_counts.most_common(10):
        rows = sorted(leader_examples.get(theme_name, []), key=lambda row: float(row.get("leader_score", 0.0) or 0.0), reverse=True)
        top_themes.append(
            {
                "theme_name": theme_name,
                "candidate_count": count,
                "leaders": rows[:3],
            }
        )

    performance_by_route: Dict[str, Dict[str, Any]] = {}
    for route, horizons in performance_buckets.items():
        route_block: Dict[str, Any] = {
            "status_counts": dict(route_status_counts.get(route, {})),
        }
        for horizon, values in horizons.items():
            wins = sum(1 for value in values if value > 0.0)
            route_block[horizon] = {
                "n": len(values),
                "avg_return_pct": round(sum(values) / len(values), 4) if values else 0.0,
                "win_rate": round((wins / len(values)) * 100.0, 2) if values else 0.0,
            }
        performance_by_route[route] = route_block

    return {
        "market": str(market).upper(),
        "runs_considered": considered,
        "route_distribution": dict(route_counts),
        "theme_source_distribution": dict(source_counts),
        "theme_distribution": dict(theme_counts),
        "unclassified_ratio": round((unclassified_count / total_candidates), 4) if total_candidates else 0.0,
        "theme_routed_stock_master_ratio": round((routed_stock_master / routed_candidates), 4) if routed_candidates else 0.0,
        "performance_by_route": performance_by_route,
        "top_themes": top_themes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True)
    parser.add_argument("--limit-runs", type=int, default=20)
    args = parser.parse_args()

    root = Path("runtime_state") / "shared_working"
    report = build_report(root, args.market, args.limit_runs)
    out_dir = Path("runtime_state") / "reports" / "theme_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"theme_shadow_validation_{str(args.market).lower()}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# Theme Shadow Validation ({report['market']})",
        "",
        f"- runs_considered: {report['runs_considered']}",
        f"- route_distribution: {report['route_distribution']}",
        f"- theme_source_distribution: {report['theme_source_distribution']}",
        f"- unclassified_ratio: {report['unclassified_ratio']}",
        f"- theme_routed_stock_master_ratio: {report['theme_routed_stock_master_ratio']}",
        "",
        "## Performance By Route",
    ]
    for route_name, route_block in sorted(report.get("performance_by_route", {}).items()):
        lines.append(f"- {route_name}: {route_block.get('status_counts', {})}")
        for horizon in ("1d", "3d", "5d"):
            metrics = route_block.get(horizon)
            if not isinstance(metrics, dict):
                continue
            lines.append(
                f"  - {horizon.upper()}: n={metrics.get('n', 0)} | avg_return_pct={metrics.get('avg_return_pct', 0.0)} | win_rate={metrics.get('win_rate', 0.0)}"
            )
    lines.extend([
        "",
        "## Top Themes",
    ])
    for row in report["top_themes"]:
        lines.append(f"- {row['theme_name']}: {row['candidate_count']}")
        for leader in row["leaders"]:
            lines.append(f"  - {leader['ticker']} | leader_score={leader['leader_score']} | theme_rank={leader['theme_rank']} | route={leader['routing_path']}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "md": str(md_path), "runs_considered": report["runs_considered"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
