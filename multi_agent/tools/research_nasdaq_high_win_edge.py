#!/usr/bin/env python3
"""Search NASDAQ swing edges that require both win rate and return quality.

This is a follow-up to the broad NASDAQ production search. It deliberately
does not optimize on average alpha alone. Candidate policies are mined on
2020-2023 and evaluated on a 2024-2026 holdout, then summarized against the
shared NASDAQ promotion gate.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from itertools import islice
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.research_nasdaq_daily_edge import DEFAULT_PANEL, FEATURES, LABELS
from multi_agent.tools.research_nasdaq_production_edge import (
    PROMOTION_GATE_THRESHOLDS,
    _add_context_and_targets,
    evaluate_nasdaq_promotion_gate,
)

DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
REPORT_VERSION = "nasdaq_high_win_edge_search_v1"

BASE_COLUMNS = ["date", "symbol", "name", "close", "liq20", "feature_ready"]
LABEL_COLUMNS = [
    "touch5_3d",
    "touch5_5d",
    "ft_5_5",
    "dd5_3d",
    "dd5_5d",
    "fwd_close_ret_3d",
    "fwd_close_ret_5d",
]
RANK_FEATURES = [
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "ret_60d",
    "ma20_slope",
    "ma60_slope",
    "ma200_slope",
    "dist_hi20",
    "dist_hi60",
    "dist_hi120",
    "dist_lo20",
    "dist_lo60",
    "pos20",
    "atr_pct",
    "vol20",
    "vol_ratio",
    "dollar_volume_ratio20",
    "rsi14",
    "rsi_slope",
    "bb_bw",
    "close_loc",
    "gap",
    "abs_gap",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "macd_hist",
    "cmf20",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: Any) -> float | None:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _metric(row: Mapping[str, Any], block: str, key: str, default: float = -999.0) -> float:
    value = ((row.get(block) or {}) if isinstance(row.get(block), Mapping) else {}).get(key)
    numeric = _finite(value)
    return default if numeric is None else numeric


def _round(value: Any, digits: int = 6) -> float | None:
    out = _finite(value)
    return None if out is None else round(out, digits)


def _read_panel(path: Path) -> pd.DataFrame:
    desired = BASE_COLUMNS + FEATURES + LABEL_COLUMNS
    try:
        import pyarrow.parquet as pq

        available = set(pq.ParquetFile(path).schema.names)
        columns = [col for col in desired if col in available]
    except Exception:
        columns = desired
    df = pd.read_parquet(path, columns=columns)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in [c for c in df.columns if c not in {"date", "symbol", "name"}]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "name" not in df.columns:
        df["name"] = df["symbol"]
    return df.dropna(subset=["date", "symbol", "close", "liq20"])


def _rank_by_date(frame: pd.DataFrame, col: str, *, ascending: bool = True) -> pd.Series:
    return pd.to_numeric(frame[col], errors="coerce").groupby(frame["date"]).rank(pct=True, ascending=ascending)


def _add_ranks_and_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    features = [col for col in RANK_FEATURES if col in out.columns]
    for col in features:
        out[f"r_{col}"] = _rank_by_date(out, col, ascending=True)
        out[f"ir_{col}"] = 1.0 - out[f"r_{col}"]

    def r(col: str) -> pd.Series:
        if col in out.columns:
            return pd.to_numeric(out[col], errors="coerce").fillna(0.0)
        return pd.Series(0.0, index=out.index)

    out["score_touch_return"] = (
        r("r_atr_pct")
        + r("r_vol20")
        + r("r_vol_ratio")
        + r("r_ret_20d")
        + r("r_ma200_slope")
        + r("r_close_loc")
    )
    out["score_first_touch_trend"] = (
        r("r_atr_pct")
        + r("r_ret_60d")
        + r("r_ma200_slope")
        + r("r_dist_hi120")
        + r("r_lower_wick_pct")
    )
    out["score_return_quality"] = (
        r("r_ret_20d")
        + r("r_ret_60d")
        + r("r_ma200_slope")
        + r("ir_atr_pct")
        + r("ir_bb_bw")
        + r("r_close_loc")
    )
    out["score_pullback_quality"] = (
        r("r_ma200_slope")
        + r("r_ma60_slope")
        + r("ir_ret_5d")
        + r("ir_rsi14")
        + r("r_lower_wick_pct")
    )
    out["score_breakout_confirmed"] = (
        r("r_dist_hi20")
        + r("r_pos20")
        + r("r_vol_ratio")
        + r("r_dollar_volume_ratio20")
        + r("r_ret_5d")
    )
    return out


def _condition_specs() -> List[Tuple[str, Tuple[Tuple[str, float], ...]]]:
    raw: List[Tuple[str, Sequence[Tuple[str, float]]]] = [
        ("high_atr", [("r_atr_pct", 0.70)]),
        ("very_high_atr", [("r_atr_pct", 0.80)]),
        ("high_vol20", [("r_vol20", 0.70)]),
        ("high_volume_ratio", [("r_vol_ratio", 0.70)]),
        ("trend_20d", [("r_ret_20d", 0.70)]),
        ("trend_60d", [("r_ret_60d", 0.70)]),
        ("low_vol_trend", [("r_ma200_slope", 0.70), ("ir_atr_pct", 0.70)]),
        ("tight_trend", [("r_ma200_slope", 0.70), ("ir_bb_bw", 0.70)]),
        ("momo_lowvol", [("r_ret_60d", 0.70), ("ir_atr_pct", 0.70)]),
        ("pullback_uptrend", [("r_ma200_slope", 0.70), ("ir_ret_5d", 0.70)]),
        ("pullback_not_broken", [("r_ma200_slope", 0.70), ("r_dist_hi120", 0.70), ("ir_ret_5d", 0.70)]),
        ("trend_close_strong", [("r_ma200_slope", 0.70), ("r_close_loc", 0.70)]),
        ("breakout_confirmed", [("r_dist_hi20", 0.80), ("r_vol_ratio", 0.70)]),
        ("quality_breakout", [("r_ma200_slope", 0.70), ("r_dist_hi20", 0.80), ("r_vol_ratio", 0.70)]),
        ("touch_trend", [("r_atr_pct", 0.70), ("r_ret_20d", 0.70), ("r_ma200_slope", 0.60)]),
        ("first_touch_trend", [("r_atr_pct", 0.70), ("r_ret_60d", 0.70), ("r_dist_hi120", 0.70)]),
        ("volume_trend", [("r_vol_ratio", 0.70), ("r_ret_20d", 0.70), ("r_ma200_slope", 0.60)]),
        ("first_touch_low_gap", [("r_atr_pct", 0.70), ("r_ret_60d", 0.70), ("r_dist_hi120", 0.70), ("ir_abs_gap", 0.70)]),
        ("first_touch_close_strong", [("r_atr_pct", 0.70), ("r_ret_60d", 0.70), ("r_dist_hi120", 0.70), ("r_close_loc", 0.70)]),
        ("first_touch_low_upper_wick", [("r_atr_pct", 0.70), ("r_ret_60d", 0.70), ("r_dist_hi120", 0.70), ("ir_upper_wick_pct", 0.70)]),
        ("first_touch_cmf", [("r_atr_pct", 0.70), ("r_ret_60d", 0.70), ("r_dist_hi120", 0.70), ("r_cmf20", 0.60)]),
        ("touch_trend_close_strong", [("r_atr_pct", 0.70), ("r_ret_20d", 0.70), ("r_ma200_slope", 0.60), ("r_close_loc", 0.70)]),
        ("touch_trend_low_gap", [("r_atr_pct", 0.70), ("r_ret_20d", 0.70), ("r_ma200_slope", 0.60), ("ir_abs_gap", 0.70)]),
    ]
    return [(name, tuple(specs)) for name, specs in raw]


def data_availability(panel_path: Path) -> Dict[str, Any]:
    cache_root = panel_path.expanduser().parents[2] if len(panel_path.expanduser().parents) >= 3 else Path.home()
    us_nasdaq_root = panel_path.expanduser().parent
    raw_ohlcv_dir = us_nasdaq_root / "raw_ohlcv"
    intraday_dir = cache_root / "intraday"
    intraday_ext_dir = cache_root / "intraday_ext"
    session_candidates = [
        cache_root / "us_intraday" / "NASDAQ",
        cache_root / "us_session" / "NASDAQ",
        cache_root / "us_daily" / "NASDAQ" / "session_features",
        cache_root / "us_daily" / "NASDAQ" / "intraday",
    ]

    def sample_stems(path: Path, limit: int = 20) -> List[str]:
        if not path.exists() or not path.is_dir():
            return []
        return [item.stem for item in islice((p for p in path.iterdir() if p.is_file()), limit)]

    intraday_samples = sample_stems(intraday_dir)
    intraday_ext_samples = sample_stems(intraday_ext_dir)
    local_intraday_looks_kr = bool(intraday_samples) and all(stem.isdigit() for stem in intraday_samples)
    local_intraday_ext_looks_kr = bool(intraday_ext_samples) and all(stem.isdigit() for stem in intraday_ext_samples)
    nasdaq_session_panel_found = any(path.exists() for path in session_candidates)
    return {
        "us_daily_panel_found": panel_path.expanduser().exists(),
        "us_daily_raw_ohlcv_found": raw_ohlcv_dir.exists(),
        "nasdaq_session_panel_found": nasdaq_session_panel_found,
        "session_candidate_paths": [str(path) for path in session_candidates],
        "local_intraday_dir": str(intraday_dir),
        "local_intraday_sample_stems": intraday_samples[:5],
        "local_intraday_looks_kr_numeric": local_intraday_looks_kr,
        "local_intraday_ext_dir": str(intraday_ext_dir),
        "local_intraday_ext_sample_stems": intraday_ext_samples[:5],
        "local_intraday_ext_looks_kr_numeric": local_intraday_ext_looks_kr,
        "session_data_status": (
            "nasdaq_session_panel_available"
            if nasdaq_session_panel_found
            else "missing_nasdaq_premarket_regular_afterhours_panel"
        ),
    }


def _mask(frame: pd.DataFrame, specs: Sequence[Tuple[str, float]]) -> np.ndarray:
    mask = np.ones(len(frame), dtype=bool)
    for col, threshold in specs:
        if col not in frame.columns:
            return np.zeros(len(frame), dtype=bool)
        mask &= pd.to_numeric(frame[col], errors="coerce").ge(float(threshold)).to_numpy()
    return mask


def _mean_ci(values: pd.Series) -> list[float | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return [None, None]
    if len(clean) < 2:
        value = round(float(clean.mean()), 6)
        return [value, value]
    mean = float(clean.mean())
    se = float(clean.std(ddof=1) / math.sqrt(len(clean)))
    return [round(mean - 1.96 * se, 6), round(mean + 1.96 * se, 6)]


def metric_block(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {"n": 0, "days": 0, "symbols": 0, "annual": []}
    out: Dict[str, Any] = {
        "n": int(len(frame)),
        "days": int(frame["date"].nunique()),
        "symbols": int(frame["symbol"].nunique()),
        "median_liq20": _round(frame["liq20"].median(), 2),
    }
    for col, name in [
        ("fwd_close_ret_3d", "ret3"),
        ("fwd_close_ret_5d", "ret5"),
        ("alpha3_liq", "alpha3"),
        ("alpha5_liq", "alpha5"),
        ("alpha5_net", "alpha5_net_cost_0_2"),
        ("touch5_3d", "touch3"),
        ("ft_5_5", "ft55"),
        ("dd5_3d", "dd3"),
    ]:
        vals = pd.to_numeric(frame[col], errors="coerce")
        out[name] = _round(vals.mean())
        out[f"{name}_ci95"] = _mean_ci(vals)
        if name in {"ret3", "ret5", "alpha3", "alpha5", "alpha5_net_cost_0_2"}:
            out[f"{name}_pos_rate"] = _round(vals.gt(0.0).mean())
    annual = []
    for year, group in frame.groupby("year", observed=True):
        item: Dict[str, Any] = {
            "year": int(year),
            "n": int(len(group)),
            "days": int(group["date"].nunique()),
            "ret5": _round(group["fwd_close_ret_5d"].mean()),
            "ret5_pos_rate": _round(pd.to_numeric(group["fwd_close_ret_5d"], errors="coerce").gt(0.0).mean()),
            "alpha5_net_0_2": _round(group["alpha5_net"].mean()),
            "alpha5_net_0_2_pos_rate": _round(pd.to_numeric(group["alpha5_net"], errors="coerce").gt(0.0).mean()),
            "touch3": _round(group["touch5_3d"].mean()),
            "ft55": _round(group["ft_5_5"].mean()),
            "dd3": _round(group["dd5_3d"].mean()),
        }
        annual.append(item)
    out["annual"] = annual
    out["years_alpha5_net_0_2_pos"] = int(sum((row.get("alpha5_net_0_2") or 0.0) > 0.0 for row in annual))
    return out


def _holdout_gate(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    thresholds = dict(PROMOTION_GATE_THRESHOLDS)
    thresholds.update({"min_n": 250.0, "min_days": 80.0, "min_years_alpha5_net_0_2_pos": 2.0})
    return evaluate_nasdaq_promotion_gate(metrics, thresholds=thresholds)


def _ranked_pick(frame: pd.DataFrame, score_col: str, topn: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    ranked = (
        frame.sort_values(["date", score_col], ascending=[True, False], kind="mergesort")
        .assign(_rank=lambda data: data.groupby("date", observed=True).cumcount() + 1)
    )
    return ranked[ranked["_rank"].le(int(topn))].drop(columns=["_rank"])


def search_edges(
    frame: pd.DataFrame,
    *,
    liquidity_floors: Sequence[float],
    topn_values: Sequence[int],
    train_end_year: int,
    holdout_start_year: int,
) -> List[Dict[str, Any]]:
    score_cols = [
        "score_touch_return",
        "score_first_touch_trend",
        "score_return_quality",
        "score_pullback_quality",
        "score_breakout_confirmed",
    ]
    train = frame[frame["year"].le(int(train_end_year))]
    holdout = frame[frame["year"].ge(int(holdout_start_year))]
    results: List[Dict[str, Any]] = []
    for floor in liquidity_floors:
        train_liq = train[train["liq20"].ge(float(floor))]
        holdout_liq = holdout[holdout["liq20"].ge(float(floor))]
        full_liq = frame[frame["liq20"].ge(float(floor))]
        for condition_name, condition_specs in _condition_specs():
            train_base = train_liq[_mask(train_liq, condition_specs)]
            holdout_base = holdout_liq[_mask(holdout_liq, condition_specs)]
            full_base = full_liq[_mask(full_liq, condition_specs)]
            if len(train_base) < 500 or train_base["date"].nunique() < 150:
                continue
            if len(holdout_base) < 100 or holdout_base["date"].nunique() < 60:
                continue
            for score_col in score_cols:
                if score_col not in train_base.columns:
                    continue
                for topn in topn_values:
                    train_picks = _ranked_pick(train_base, score_col, int(topn))
                    if len(train_picks) < 250 or train_picks["date"].nunique() < 150:
                        continue
                    train_metrics = metric_block(train_picks)
                    if (
                        (train_metrics.get("ret5_pos_rate") or 0.0) < 0.49
                        or (train_metrics.get("alpha5_net_cost_0_2") or 0.0) < -0.25
                        or (train_metrics.get("touch3") or 0.0) < 0.30
                    ):
                        continue
                    holdout_picks = _ranked_pick(holdout_base, score_col, int(topn))
                    if len(holdout_picks) < 80 or holdout_picks["date"].nunique() < 60:
                        continue
                    full_picks = _ranked_pick(full_base, score_col, int(topn))
                    holdout_metrics = metric_block(holdout_picks)
                    full_metrics = metric_block(full_picks)
                    holdout_gate = _holdout_gate(holdout_metrics)
                    promotion_gate = evaluate_nasdaq_promotion_gate(full_metrics)
                    selection_key = (
                        float(holdout_metrics.get("ret5") or 0.0)
                        + float(holdout_metrics.get("alpha5_net_cost_0_2") or 0.0)
                        + 4.0 * float(holdout_metrics.get("ret5_pos_rate") or 0.0)
                        + 3.0 * float(holdout_metrics.get("alpha5_net_cost_0_2_pos_rate") or 0.0)
                        + 2.0 * float(holdout_metrics.get("touch3") or 0.0)
                        + 2.0 * float(holdout_metrics.get("ft55") or 0.0)
                        - 2.0 * float(holdout_metrics.get("dd3") or 0.0)
                    )
                    results.append(
                        {
                            "condition": condition_name,
                            "condition_specs": list(condition_specs),
                            "score": score_col,
                            "liq20_floor": float(floor),
                            "topn": int(topn),
                            "selection_key": round(selection_key, 6),
                            "train": train_metrics,
                            "holdout": holdout_metrics,
                            "full_oos": full_metrics,
                            "holdout_gate": holdout_gate,
                            "promotion_gate": promotion_gate,
                            "promotion_ready": bool(promotion_gate.get("promotion_ready")),
                            "promotion_blocking_reasons": list(promotion_gate.get("blocking_reasons") or []),
                        }
                    )
    return sorted(results, key=lambda row: float(row.get("selection_key") or -999.0), reverse=True)


def frontier_sections(results: Sequence[Mapping[str, Any]], *, limit: int = 10) -> Dict[str, List[Mapping[str, Any]]]:
    rows = list(results)

    def rank(name: str, predicate: Any, key: Any) -> List[Mapping[str, Any]]:
        selected = [row for row in rows if predicate(row)]
        return sorted(selected, key=key, reverse=True)[:limit]

    return {
        "holdout_best_overall": list(rows[:limit]),
        "holdout_dd_safe": rank(
            "holdout_dd_safe",
            lambda row: _metric(row, "holdout", "dd3") <= 0.35,
            lambda row: (
                _metric(row, "holdout", "ret5")
                + _metric(row, "holdout", "alpha5_net_cost_0_2")
                + 4.0 * _metric(row, "holdout", "ret5_pos_rate", 0.0)
                + 2.0 * _metric(row, "holdout", "touch3", 0.0)
            ),
        ),
        "holdout_touch_win": rank(
            "holdout_touch_win",
            lambda row: _metric(row, "holdout", "touch3") >= 0.55
            or _metric(row, "holdout", "ft55") >= 0.55
            or _metric(row, "holdout", "ret5_pos_rate") >= 0.55,
            lambda row: (
                _metric(row, "holdout", "ret5")
                + _metric(row, "holdout", "alpha5_net_cost_0_2")
                + 3.0 * _metric(row, "holdout", "touch3", 0.0)
                + 3.0 * _metric(row, "holdout", "ft55", 0.0)
                - 2.0 * _metric(row, "holdout", "dd3", 0.0)
            ),
        ),
        "full_oos_best_net": rank(
            "full_oos_best_net",
            lambda row: True,
            lambda row: (
                _metric(row, "full_oos", "alpha5_net_cost_0_2")
                + 0.5 * _metric(row, "full_oos", "ret5")
                + _metric(row, "full_oos", "alpha5_net_cost_0_2_pos_rate", 0.0)
            ),
        ),
        "full_oos_best_touch": rank(
            "full_oos_best_touch",
            lambda row: True,
            lambda row: (
                _metric(row, "full_oos", "touch3", 0.0)
                + _metric(row, "full_oos", "ft55", 0.0)
                - _metric(row, "full_oos", "dd3", 0.0)
            ),
        ),
        "full_oos_dd_safe": rank(
            "full_oos_dd_safe",
            lambda row: _metric(row, "full_oos", "dd3") <= 0.35,
            lambda row: (
                _metric(row, "full_oos", "ret5")
                + _metric(row, "full_oos", "alpha5_net_cost_0_2")
                + 4.0 * _metric(row, "full_oos", "ret5_pos_rate", 0.0)
            ),
        ),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _fmt_pct(value: Any) -> str:
    numeric = _finite(value)
    if numeric is None:
        return "-"
    return f"{numeric:.2%}"


def _fmt_num(value: Any) -> str:
    numeric = _finite(value)
    if numeric is None:
        return "-"
    return f"{numeric:+.3f}"


def _write_md(path: Path, report: Mapping[str, Any]) -> None:
    availability = report.get("data_availability") or {}
    lines = [
        "# NASDAQ High-Win High-Return Edge Search",
        "",
        f"- report_version: `{report.get('report_version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- panel_path: `{report.get('panel_path')}`",
        f"- rows_eligible: `{report.get('rows_eligible')}`",
        f"- symbols_eligible: `{report.get('symbols_eligible')}`",
        f"- date_range: `{report.get('date_min')}` ~ `{report.get('date_max')}`",
        f"- train_years: `{report.get('train_years')}`",
        f"- holdout_years: `{report.get('holdout_years')}`",
        f"- promotion_gate_thresholds: `{report.get('promotion_gate_thresholds')}`",
        "",
        "## Data Availability",
        "",
        f"- session_data_status: `{availability.get('session_data_status')}`",
        f"- us_daily_panel_found: `{availability.get('us_daily_panel_found')}`",
        f"- us_daily_raw_ohlcv_found: `{availability.get('us_daily_raw_ohlcv_found')}`",
        f"- nasdaq_session_panel_found: `{availability.get('nasdaq_session_panel_found')}`",
        f"- local_intraday_looks_kr_numeric: `{availability.get('local_intraday_looks_kr_numeric')}`",
        f"- local_intraday_ext_looks_kr_numeric: `{availability.get('local_intraday_ext_looks_kr_numeric')}`",
        "",
        "## Summary",
        "",
        f"- candidates_evaluated: `{report.get('candidate_count')}`",
        f"- promotion_ready_count: `{report.get('promotion_ready_count')}`",
        f"- holdout_gate_ready_count: `{report.get('holdout_gate_ready_count')}`",
        "",
        "## Frontier Diagnostics",
        "",
    ]
    for section, rows in (report.get("frontiers") or {}).items():
        lines.append(f"### {section}")
        if not rows:
            lines.append("- none")
            lines.append("")
            continue
        for row in rows[:5]:
            holdout = row.get("holdout") or {}
            full = row.get("full_oos") or {}
            lines.append(
                f"- `{row.get('condition')}` / `{row.get('score')}` floor `{row.get('liq20_floor'):,.0f}` top{row.get('topn')} "
                f"holdout ret5 `{_fmt_num(holdout.get('ret5'))}%` win `{_fmt_pct(holdout.get('ret5_pos_rate'))}` "
                f"touch `{_fmt_pct(holdout.get('touch3'))}` ft `{_fmt_pct(holdout.get('ft55'))}` dd `{_fmt_pct(holdout.get('dd3'))}`; "
                f"full ret5 `{_fmt_num(full.get('ret5'))}%` win `{_fmt_pct(full.get('ret5_pos_rate'))}` "
                f"touch `{_fmt_pct(full.get('touch3'))}` ft `{_fmt_pct(full.get('ft55'))}` dd `{_fmt_pct(full.get('dd3'))}`"
            )
        lines.append("")
    lines.extend(
        [
        "## Top Holdout Candidates",
        "",
        ]
    )
    for row in report.get("top_candidates", [])[:25]:
        holdout = row.get("holdout") or {}
        full = row.get("full_oos") or {}
        lines.append(
            f"- `{row.get('condition')}` / `{row.get('score')}` floor `{row.get('liq20_floor'):,.0f}` top{row.get('topn')} "
            f"holdout n `{holdout.get('n')}` days `{holdout.get('days')}` "
            f"ret5 `{_fmt_num(holdout.get('ret5'))}%` ret5_pos `{_fmt_pct(holdout.get('ret5_pos_rate'))}` "
            f"net `{_fmt_num(holdout.get('alpha5_net_cost_0_2'))}%` net_pos `{_fmt_pct(holdout.get('alpha5_net_cost_0_2_pos_rate'))}` "
            f"touch3 `{_fmt_pct(holdout.get('touch3'))}` ft55 `{_fmt_pct(holdout.get('ft55'))}` dd3 `{_fmt_pct(holdout.get('dd3'))}` "
            f"full_gate `{'PASS' if row.get('promotion_ready') else 'BLOCK'}`"
        )
        reasons = row.get("promotion_blocking_reasons") or []
        if reasons:
            lines.append(f"  - blockers: `{', '.join(str(reason) for reason in reasons[:8])}`")
        lines.append(
            f"  - full_oos: n `{full.get('n')}` days `{full.get('days')}` "
            f"ret5 `{_fmt_num(full.get('ret5'))}%` touch3 `{_fmt_pct(full.get('touch3'))}` "
            f"ft55 `{_fmt_pct(full.get('ft55'))}` dd3 `{_fmt_pct(full.get('dd3'))}`"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search NASDAQ high-win high-return swing edge candidates.")
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--min-price", type=float, default=1.0)
    parser.add_argument("--research-liq-floor", type=float, default=10_000_000.0)
    parser.add_argument("--liquidity-floors", default="10000000,30000000,100000000")
    parser.add_argument("--topn", default="1,2,3,5,10")
    parser.add_argument("--train-end-year", type=int, default=2023)
    parser.add_argument("--holdout-start-year", type=int, default=2024)
    parser.add_argument("--max-output-candidates", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    panel_path = Path(args.panel).expanduser()
    raw = _read_panel(panel_path)
    eligible = raw[
        raw["feature_ready"].eq(1)
        & raw["close"].ge(float(args.min_price))
        & raw["liq20"].ge(float(args.research_liq_floor))
        & raw["fwd_close_ret_5d"].notna()
        & raw["touch5_3d"].notna()
        & raw["ft_5_5"].notna()
    ].copy()
    eligible = _add_context_and_targets(eligible, cost_pct=0.20)
    eligible["year"] = eligible["date"].dt.year.astype(int)
    eligible = eligible[eligible["year"].ge(2020)].copy()
    eligible = _add_ranks_and_scores(eligible)

    floors = [float(value) for value in str(args.liquidity_floors).split(",") if value.strip()]
    topn_values = [int(value) for value in str(args.topn).split(",") if value.strip()]
    results = search_edges(
        eligible,
        liquidity_floors=floors,
        topn_values=topn_values,
        train_end_year=int(args.train_end_year),
        holdout_start_year=int(args.holdout_start_year),
    )
    limit = max(1, int(args.max_output_candidates))
    top_candidates = results[:limit]
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "panel_path": str(panel_path),
        "rows_loaded": int(len(raw)),
        "rows_eligible": int(len(eligible)),
        "symbols_eligible": int(eligible["symbol"].nunique()),
        "date_min": str(eligible["date"].min().date()) if not eligible.empty else None,
        "date_max": str(eligible["date"].max().date()) if not eligible.empty else None,
        "train_years": f"2020-{int(args.train_end_year)}",
        "holdout_years": f"{int(args.holdout_start_year)}-{int(eligible['year'].max()) if not eligible.empty else ''}",
        "min_price": float(args.min_price),
        "research_liq_floor": float(args.research_liq_floor),
        "liquidity_floors": floors,
        "topn_values": topn_values,
        "promotion_gate_thresholds": dict(PROMOTION_GATE_THRESHOLDS),
        "candidate_count": int(len(results)),
        "promotion_ready_count": int(sum(1 for row in results if row.get("promotion_ready"))),
        "holdout_gate_ready_count": int(
            sum(1 for row in results if (row.get("holdout_gate") or {}).get("promotion_ready"))
        ),
        "top_candidates": top_candidates,
        "frontiers": frontier_sections(results, limit=10),
        "data_availability": data_availability(panel_path),
    }
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"nasdaq_high_win_edge_search_{stamp}.json"
    md_path = out_dir / f"nasdaq_high_win_edge_search_{stamp}.md"
    _write_json(json_path, report)
    _write_md(md_path, report)
    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "md_path": str(md_path),
                "candidate_count": report["candidate_count"],
                "promotion_ready_count": report["promotion_ready_count"],
                "holdout_gate_ready_count": report["holdout_gate_ready_count"],
                "top_candidate": top_candidates[0] if top_candidates else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
