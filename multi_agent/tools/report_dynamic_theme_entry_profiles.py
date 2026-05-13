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

BOOL_COLUMNS = [
    "is_dummy_data",
    "validation_excluded",
    "label_stop_loss_5pct",
]


def _as_bool(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "yes", "y"})


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


def _pct(value: Any) -> float | None:
    number = _round(value, 6)
    return round(number * 100.0, 3) if number is not None else None


def _quantile(series: pd.Series, q: float, default: float | None = None) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return default
    return _round(values.quantile(q), 2)


def _load_rows(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in BOOL_COLUMNS:
        if col in df.columns:
            df[f"{col}_bool"] = _as_bool(df[col])
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    mask = scan_mode.eq("SWING") & (ticker.str.endswith(".KS") | ticker.str.endswith(".KQ"))
    if "is_dummy_data_bool" in df.columns:
        mask &= ~df["is_dummy_data_bool"]
    out = df.loc[mask].copy()
    out["market2"] = "KOSDAQ"
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    raw_date = out.get("base_trade_date", pd.Series("", index=out.index)).copy()
    if "recommended_at" in out.columns:
        raw_date = raw_date.where(raw_date.fillna("").astype(str).str.strip().ne(""), out["recommended_at"])
    out["scan_date"] = pd.to_datetime(raw_date, errors="coerce", utc=True)
    return out


def _prepare_labels(df: pd.DataFrame) -> pd.DataFrame:
    required = [col for col in ["return_1d_pct", "return_3d_pct", "return_5d_pct"] if col in df.columns]
    out = df.dropna(subset=required).copy()
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
    return out


def _window_rows(df: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    dated = df.dropna(subset=["scan_date"])
    if dated.empty:
        return df
    latest = dated["scan_date"].max()
    start = latest - pd.Timedelta(days=lookback_days)
    window = df.loc[df["scan_date"].ge(start)].copy()
    return window if len(window) >= 100 else df


def _theme_name(series: pd.Series) -> pd.Series:
    out = series.fillna("").astype(str).str.strip()
    blocked = {"", "-", "nan", "none", "unknown", "unclassified", "미분류", "기타"}
    return out.mask(out.str.lower().isin(blocked), "")


def _profile_level(summary: Dict[str, Any]) -> str:
    n = summary["sample_n"]
    practical = summary["practical_win_pct"] or 0.0
    win5 = summary["win5_pct"] or 0.0
    bad = summary["bad_path_pct"] if summary["bad_path_pct"] is not None else 100.0
    avg5 = summary["avg_5d_pct"] or 0.0
    if n >= 30 and practical >= 78.0 and win5 >= 78.0 and bad <= 25.0 and avg5 > 3.0:
        return "pass"
    if n >= 30 and practical >= 72.0 and win5 >= 75.0 and bad <= 32.0 and avg5 > 2.0:
        return "near"
    if 12 <= n < 30 and practical >= 80.0 and win5 >= 80.0 and bad <= 20.0 and avg5 > 3.0:
        return "small_sample"
    if n >= 20 and practical >= 70.0 and win5 >= 75.0 and bad <= 35.0 and avg5 > 2.0:
        return "watch"
    return "fail"


def _condition_candidates(group: pd.DataFrame) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = [
        {"name": "theme_only", "mask": pd.Series(True, index=group.index), "thresholds": {}, "required": {}}
    ]

    def add_numeric(name: str, col: str, op: str, threshold: float, threshold_key: str) -> None:
        if col not in group.columns:
            return
        series = pd.to_numeric(group[col], errors="coerce")
        mask = series.ge(threshold) if op == ">=" else series.le(threshold)
        thresholds = {threshold_key: threshold}
        candidates.append({"name": f"{col}{op}{threshold:g}", "mask": mask.fillna(False), "thresholds": thresholds, "required": {}})

    for threshold in [45, 50, 55, 60]:
        add_numeric("prob_clean", "prob_clean", ">=", threshold, "min_prob_clean")
    for threshold in [4, 5, 6, 8, 10]:
        add_numeric("expected_edge_score", "expected_edge_score", ">=", threshold, "min_expected_edge_score")
    for threshold in [80, 85, 90, 95]:
        add_numeric("decision_score", "decision_score", ">=", threshold, "min_decision_score")
    for threshold in [70, 80, 90]:
        add_numeric("tech_score", "tech_score", ">=", threshold, "min_tech_score")
    for threshold in [50, 60, 70]:
        add_numeric("whale_score", "whale_score", ">=", threshold, "min_whale_score")
    for threshold in [30, 40, 50, 60, 65]:
        add_numeric("loss_risk_score", "loss_risk_score", "<=", threshold, "max_loss_risk_score")
    for threshold in [1, 3, 5]:
        add_numeric("priority_rank", "priority_rank", "<=", threshold, "max_priority_rank")

    trend = group.get("trend", pd.Series("", index=group.index)).fillna("").astype(str).str.upper().str.strip()
    for value in sorted(v for v in trend.unique().tolist() if v):
        candidates.append(
            {
                "name": f"trend=={value}",
                "mask": trend.eq(value),
                "thresholds": {},
                "required": {"trend": value},
            }
        )

    singles = list(candidates[1:])
    for left_idx, left in enumerate(singles):
        for right in singles[left_idx + 1 :]:
            thresholds = {**left.get("thresholds", {}), **right.get("thresholds", {})}
            required = {**left.get("required", {}), **right.get("required", {})}
            if len(thresholds) + len(required) > 2:
                continue
            candidates.append(
                {
                    "name": f"{left['name']} + {right['name']}",
                    "mask": (left["mask"] & right["mask"]).fillna(False),
                    "thresholds": thresholds,
                    "required": required,
                }
            )
    return candidates


def _summarize_theme(group: pd.DataFrame) -> Dict[str, Any]:
    resolved = group.dropna(subset=["return_1d_pct", "return_3d_pct", "return_5d_pct"])
    summary = {
        "sample_n": int(len(resolved)),
        "win1_pct": _pct(resolved["return_1d_pct"].gt(0).mean()) if len(resolved) else None,
        "win3_pct": _pct(resolved["return_3d_pct"].gt(0).mean()) if len(resolved) else None,
        "win5_pct": _pct(resolved["return_5d_pct"].gt(0).mean()) if len(resolved) else None,
        "practical_win_pct": _pct(resolved["practical_win"].mean()) if len(resolved) else None,
        "clean_riser_pct": _pct(resolved["clean_riser"].mean()) if len(resolved) else None,
        "bad_path_pct": _pct(resolved["bad_path"].mean()) if len(resolved) else None,
        "avg_1d_pct": _round(resolved["return_1d_pct"].mean(), 4) if len(resolved) else None,
        "avg_3d_pct": _round(resolved["return_3d_pct"].mean(), 4) if len(resolved) else None,
        "avg_5d_pct": _round(resolved["return_5d_pct"].mean(), 4) if len(resolved) else None,
        "avg_min_drawdown_pct": _round(resolved["min_return_observed_pct"].mean(), 4)
        if "min_return_observed_pct" in resolved.columns and len(resolved)
        else None,
    }
    summary["level"] = _profile_level(summary)
    return summary


def _best_theme_profile(group: pd.DataFrame) -> Dict[str, Any] | None:
    best: Dict[str, Any] | None = None
    rank = {"pass": 0, "near": 1, "small_sample": 2, "watch": 3, "fail": 9}
    for candidate in _condition_candidates(group):
        sliced = group.loc[candidate["mask"]].copy()
        if len(sliced) < 12:
            continue
        evidence = _summarize_theme(sliced)
        level = evidence.pop("level")
        if level == "fail":
            continue
        score = (
            rank.get(level, 9),
            -(evidence.get("practical_win_pct") or 0.0),
            evidence.get("bad_path_pct") if evidence.get("bad_path_pct") is not None else 100.0,
            -(evidence.get("avg_5d_pct") or 0.0),
            -(evidence.get("sample_n") or 0),
        )
        payload = {
            "level": level,
            "condition": candidate["name"],
            "evidence": evidence,
            "thresholds": candidate["thresholds"],
            "required": candidate["required"],
            "selection_logic": "최근 누적 스캔 성과에서 테마+스캔시점 조건 조합을 탐색해 5D 승률, 실전승률, 손실경로가 통과한 프로필",
            "_score": score,
        }
        if best is None or score < best["_score"]:
            best = payload
    if best:
        best.pop("_score", None)
    return best


def build_report(df: pd.DataFrame, *, lookback_days: int) -> Dict[str, Any]:
    prepared = _prepare_labels(df)
    windowed = _window_rows(prepared, lookback_days)

    markets: Dict[str, Any] = {}

    def market_profiles(source_df: pd.DataFrame, market: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
        theme_series = _theme_name(source_df.get("primary_theme", pd.Series("", index=source_df.index)))
        scoped = source_df.loc[theme_series.ne("")].copy()
        scoped["theme_key"] = theme_series.loc[scoped.index]
        market_df = scoped.loc[scoped["market2"].eq(market)].copy()
        profiles: Dict[str, Any] = {}
        for theme, group in market_df.groupby("theme_key"):
            profile = _best_theme_profile(group)
            if profile:
                profiles[str(theme)] = profile
        return market_df, profiles

    for market in ["KOSPI", "KOSDAQ"]:
        market_df, selected = market_profiles(windowed, market)
        profile_source = "recent_window"
        if not selected:
            fallback_df, fallback_selected = market_profiles(prepared, market)
            if fallback_selected:
                market_df = fallback_df
                selected = fallback_selected
                profile_source = "historical_fallback"
        markets[market] = {
            "rows": int(len(market_df)),
            "profile_source": profile_source,
            "selected_theme_count": int(len(selected)),
            "themes": dict(
                sorted(
                    selected.items(),
                    key=lambda item: (
                        {"pass": 0, "near": 1, "small_sample": 2, "watch": 3}.get(item[1].get("level"), 9),
                        -(item[1].get("evidence", {}).get("sample_n") or 0),
                    ),
                )
            ),
            "all_profile_count": int(len(selected)),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DEFAULT_INPUT),
        "lookback_days": lookback_days,
        "definition": {
            "no_fixed_theme_names": True,
            "runtime_rule": "row primary_theme must match a currently validated dynamic profile and pass scan-time strength thresholds",
            "pass": "n>=30, practical>=78%, 5D win>=78%, bad_path<=25%, avg5>3%",
            "near": "n>=30, practical>=72%, 5D win>=75%, bad_path<=32%, avg5>2%",
            "small_sample": "12<=n<30, practical>=80%, 5D win>=80%, bad_path<=20%, avg5>3%",
            "watch": "n>=20, practical>=70%, 5D win>=75%, bad_path<=35%, avg5>2%",
        },
        "rows": {
            "input_rows": int(len(df)),
            "prepared_rows": int(len(prepared)),
            "window_rows": int(len(windowed)),
        },
        "markets": markets,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Dynamic Theme Entry Profiles",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- lookback_days: `{report.get('lookback_days')}`",
        f"- source: `{report.get('source')}`",
        "",
        "## Definition",
        "",
    ]
    for key, value in report.get("definition", {}).items():
        lines.append(f"- {key}: `{value}`")
    for market, payload in report.get("markets", {}).items():
        lines.extend(["", f"## {market}", ""])
        lines.append(f"- rows: `{payload.get('rows')}`")
        lines.append(f"- profile_source: `{payload.get('profile_source')}`")
        lines.append(f"- selected_theme_count: `{payload.get('selected_theme_count')}`")
        lines.extend(["", "| Theme | Level | Condition | N | 1D Win | 5D Win | Practical | Bad Path | Avg 5D | Thresholds | Required |", "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|"])
        for theme, profile in payload.get("themes", {}).items():
            ev = profile.get("evidence", {})
            th = profile.get("thresholds", {})
            required = profile.get("required", {})
            lines.append(
                f"| {theme} | {profile.get('level')} | {profile.get('condition')} | {ev.get('sample_n')} | "
                f"{ev.get('win1_pct')}% | {ev.get('win5_pct')}% | {ev.get('practical_win_pct')}% | "
                f"{ev.get('bad_path_pct')}% | {ev.get('avg_5d_pct')}% | `{json.dumps(th, ensure_ascii=False)}` | "
                f"`{json.dumps(required, ensure_ascii=False)}` |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dynamic practical-entry theme profiles from scan archive outcomes.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--lookback-days", type=int, default=60)
    args = parser.parse_args()

    df = _load_rows(Path(args.input))
    report = build_report(df, lookback_days=args.lookback_days)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dynamic_theme_entry_profiles.json"
    md_path = output_dir / "dynamic_theme_entry_profiles.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    selected = sum(m.get("selected_theme_count", 0) for m in report.get("markets", {}).values())
    print(json.dumps({"json": str(json_path), "md": str(md_path), "selected_theme_count": selected}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
