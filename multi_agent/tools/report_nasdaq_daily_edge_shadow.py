#!/usr/bin/env python3
"""NASDAQ SWING model lane: daily alpha3 edge picks + forward shadow ledger.

This promotes the 2026-06-29 NASDAQ daily edge research into an operational
model lane without treating it as trade capital. It trains the same target
family used by ``research_nasdaq_production_edge.py`` on historical rows,
scores the latest feature date, writes daily picks, and settles a 5D forward
ledger as future labels become available.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.research_nasdaq_daily_edge import DEFAULT_PANEL, FEATURES, LABELS
from multi_agent.tools.research_nasdaq_production_edge import (
    _add_context_and_targets,
    _add_prediction_ranks,
    _fit_classifier,
    _fit_regressor,
    _sample_train,
)

REPORT_VERSION = "nasdaq_swing_daily_edge_shadow_v1"
MODEL_VERSION = "nasdaq_swing_alpha3_pos60_v1"
STRATEGY_FAMILY = "NASDAQ_SWING_DAILY_EDGE"
SIGNAL_CLASS = "NASDAQ_SWING_MODEL"

DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
DEFAULT_PANEL_ROOT = Path("~/research_cache/us_daily/NASDAQ").expanduser()
DEFAULT_LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "us_research" / "nasdaq_swing_daily_edge_shadow_ledger.jsonl"
DEFAULT_MODEL_BUNDLE = PROJECT_ROOT / "runtime_state" / "models" / "nasdaq_swing_daily_edge" / "nasdaq_swing_daily_edge_latest.pkl"

POLICIES: Tuple[Dict[str, Any], ...] = (
    {
        "candidate_id": "nasdaq_swing_alpha3_pos60_liq30_top10_v1",
        "lane": "primary_liq30_top10",
        "score_col": "score_alpha3",
        "entry_gate": "pred_alpha5_pos_ge_0_60",
        "pred_alpha5_pos_min": 0.60,
        "liq20_floor": 30_000_000.0,
        "topn": 10,
    },
    {
        "candidate_id": "nasdaq_swing_alpha3_pos60_liq100_top5_v1",
        "lane": "high_liquidity_liq100_top5",
        "score_col": "score_alpha3",
        "entry_gate": "pred_alpha5_pos_ge_0_60",
        "pred_alpha5_pos_min": 0.60,
        "liq20_floor": 100_000_000.0,
        "topn": 5,
    },
)

TARGETS: Tuple[Tuple[str, str, str], ...] = (
    ("reg", "alpha3_liq", "pred_alpha3"),
    ("reg", "alpha5_liq", "pred_alpha5"),
    ("clf", "alpha5_net_pos", "pred_alpha5_pos"),
    ("clf", "ft_5_5", "pred_ft55"),
    ("clf", "dd5_3d", "pred_dd3"),
)

CONTEXT_FEATURES = (
    "mkt_ret1_mean",
    "mkt_ret5_mean",
    "mkt_ret20_mean",
    "mkt_ret60_mean",
    "mkt_breadth1",
    "mkt_breadth5",
    "mkt_vol20_mean",
    "mkt_atr_mean",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _round_float(value: Any, digits: int = 6) -> Optional[float]:
    out = _finite_float(value)
    return None if out is None else round(out, digits)


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f"Unsupported JSON type: {type(value)!r}")


def _available_columns(path: Path) -> set[str]:
    try:
        import pyarrow.parquet as pq

        return set(pq.ParquetFile(path).schema.names)
    except Exception:
        return set()


def resolve_panel_path(value: str) -> Path:
    text = str(value or "").strip()
    if text and text.lower() not in {"latest", "auto"}:
        return Path(text).expanduser()
    candidates = sorted(
        [
            path
            for path in DEFAULT_PANEL_ROOT.glob("daily_features_*.parquet")
            if "_latest_" not in path.name and path.is_file()
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return Path(DEFAULT_PANEL).expanduser()


def read_panel(path: Path) -> pd.DataFrame:
    desired = [
        "date",
        "symbol",
        "name",
        "market",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "dollar_volume",
        "liq20",
        "liq60",
        "feature_ready",
    ] + FEATURES + LABELS
    available = _available_columns(path)
    cols = [col for col in desired if not available or col in available]
    df = pd.read_parquet(path, columns=cols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "symbol", "close", "liq20"])
    df["symbol"] = df["symbol"].astype(str).str.strip()
    if "name" not in df.columns:
        df["name"] = df["symbol"]
    if "market" not in df.columns:
        df["market"] = "NASDAQ"
    df["year"] = df["date"].dt.year.astype(int)
    for col in [c for c in df.columns if c not in {"symbol", "name", "market"}]:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def prepare_context_frame(
    raw: pd.DataFrame,
    *,
    min_price: float,
    research_liq_floor: float,
    cost_pct: float,
) -> pd.DataFrame:
    eligible = raw[
        raw["feature_ready"].eq(1)
        & raw["close"].ge(float(min_price))
        & raw["liq20"].ge(float(research_liq_floor))
    ].copy()
    if eligible.empty:
        return eligible
    return _add_context_and_targets(eligible, cost_pct=float(cost_pct))


def model_feature_columns(frame: pd.DataFrame) -> List[str]:
    return [
        col
        for col in list(FEATURES) + list(CONTEXT_FEATURES) + [c for c in frame.columns if c.startswith("xrank_")]
        if col in frame.columns
    ]


def _score_date(frame: pd.DataFrame, requested: str = "") -> pd.Timestamp:
    if requested:
        return pd.Timestamp(requested).normalize()
    return pd.to_datetime(frame["date"], errors="coerce").max().normalize()


def train_and_score_latest(
    frame: pd.DataFrame,
    *,
    score_date: str = "",
    feature_cols: Optional[Sequence[str]] = None,
    embargo_days: int = 20,
    min_train_rows: int = 100_000,
    max_train_rows: int = 160_000,
    estimators: int = 110,
    seed: int = 20260629,
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    if frame.empty:
        raise ValueError("empty prepared NASDAQ frame")
    score_ts = _score_date(frame, score_date)
    score_idx = frame.index[pd.to_datetime(frame["date"]).dt.normalize().eq(score_ts)]
    if len(score_idx) == 0:
        raise ValueError(f"score_date not found in panel: {score_ts.date()}")

    features = list(feature_cols or model_feature_columns(frame))
    if not features:
        raise ValueError("no model features available")

    train_cutoff = score_ts - timedelta(days=int(embargo_days))
    train_base = frame[pd.to_datetime(frame["date"]) < train_cutoff].copy()
    scored = frame.copy()
    x_score = scored.loc[score_idx, features].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    train_report: Dict[str, Any] = {
        "score_date": str(score_ts.date()),
        "train_cutoff": str(train_cutoff.date()),
        "features": features,
        "targets": {},
    }
    models: Dict[str, Any] = {}

    for offset, (kind, target, out_col) in enumerate(TARGETS):
        train_target = train_base[train_base[target].notna()].copy()
        if len(train_target) < int(min_train_rows):
            raise ValueError(f"insufficient train rows for {target}: {len(train_target)} < {min_train_rows}")
        sampled = _sample_train(train_target, int(max_train_rows), int(seed) + offset)
        if kind == "reg":
            model = _fit_regressor(sampled, features, target, int(seed) + 101 + offset, int(estimators))
            pred = model.predict(x_score)
        else:
            model = _fit_classifier(sampled, features, target, int(seed) + 101 + offset, int(estimators))
            pred = model.predict_proba(x_score)[:, 1]
        scored.loc[score_idx, out_col] = pred
        models[out_col] = model
        train_report["targets"][target] = {
            "kind": kind,
            "output_column": out_col,
            "train_rows_available": int(len(train_target)),
            "train_rows_used": int(len(sampled)),
            "target_mean": _round_float(sampled[target].mean(), 6),
            "pred_mean": _round_float(np.nanmean(pred), 6),
        }

    scored = _add_prediction_ranks(scored)
    bundle = {
        "report_version": REPORT_VERSION,
        "model_version": MODEL_VERSION,
        "strategy_family": STRATEGY_FAMILY,
        "score_date": str(score_ts.date()),
        "features": features,
        "models": models,
        "train_report": train_report,
    }
    return scored.loc[score_idx].copy(), train_report, bundle


def select_policy_picks(
    latest: pd.DataFrame,
    *,
    policies: Sequence[Mapping[str, Any]] = POLICIES,
    model_version: str = MODEL_VERSION,
) -> List[Dict[str, Any]]:
    if latest.empty:
        return []
    rows: List[Dict[str, Any]] = []
    score_date = pd.to_datetime(latest["date"].iloc[0]).date().isoformat()
    for policy in policies:
        score_col = str(policy["score_col"])
        gate_col = "pred_alpha5_pos"
        pool = latest[
            pd.to_numeric(latest["liq20"], errors="coerce").ge(float(policy["liq20_floor"]))
            & pd.to_numeric(latest[gate_col], errors="coerce").ge(float(policy["pred_alpha5_pos_min"]))
            & pd.to_numeric(latest[score_col], errors="coerce").notna()
        ].copy()
        if pool.empty:
            continue
        pool["_policy_rank"] = pd.to_numeric(pool[score_col], errors="coerce").rank(method="first", ascending=False)
        selected = pool[pool["_policy_rank"].le(int(policy["topn"]))].sort_values(score_col, ascending=False)
        for idx, row in enumerate(selected.to_dict("records"), start=1):
            ticker = str(row.get("symbol") or "").strip()
            ledger_key = f"{policy['candidate_id']}:{score_date}:{ticker}"
            rows.append(
                {
                    "ledger_key": ledger_key,
                    "candidate_id": str(policy["candidate_id"]),
                    "strategy_family": STRATEGY_FAMILY,
                    "signal_class": SIGNAL_CLASS,
                    "model_version": model_version,
                    "market": "NASDAQ",
                    "scan_mode": "SWING",
                    "ticker": ticker,
                    "stock_name": str(row.get("name") or ticker),
                    "date": score_date,
                    "score_date": score_date,
                    "rank": idx,
                    "score_col": score_col,
                    "score": _round_float(row.get(score_col), 6),
                    "p": _round_float(row.get("pred_alpha5_pos"), 6),
                    "pred_alpha3": _round_float(row.get("pred_alpha3"), 6),
                    "pred_alpha5": _round_float(row.get("pred_alpha5"), 6),
                    "pred_alpha5_net_pos": _round_float(row.get("pred_alpha5_pos"), 6),
                    "pred_ft55": _round_float(row.get("pred_ft55"), 6),
                    "pred_dd3": _round_float(row.get("pred_dd3"), 6),
                    "entry_gate": str(policy["entry_gate"]),
                    "liq20_floor": float(policy["liq20_floor"]),
                    "topn": int(policy["topn"]),
                    "lane": str(policy["lane"]),
                    "entry_reference_price": _round_float(row.get("close"), 6),
                    "liq20": _round_float(row.get("liq20"), 2),
                    "liq60": _round_float(row.get("liq60"), 2),
                    "target_horizon_days": 5,
                    "costs_pct": [0.10, 0.20, 0.35],
                    "status": "open",
                    "logged_at": _utc_now(),
                }
            )
    return rows


def build_policy_diagnostics(
    latest: pd.DataFrame,
    *,
    policies: Sequence[Mapping[str, Any]] = POLICIES,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    if latest.empty:
        return []
    diagnostics: List[Dict[str, Any]] = []
    for policy in policies:
        score_col = str(policy["score_col"])
        liq_floor = float(policy["liq20_floor"])
        pred_floor = float(policy["pred_alpha5_pos_min"])
        pool = latest[pd.to_numeric(latest["liq20"], errors="coerce").ge(liq_floor)].copy()
        if pool.empty:
            diagnostics.append(
                {
                    "candidate_id": str(policy["candidate_id"]),
                    "lane": str(policy["lane"]),
                    "pool_rows": 0,
                    "gate_pass_rows": 0,
                    "top_blocked": [],
                }
            )
            continue
        pred = pd.to_numeric(pool["pred_alpha5_pos"], errors="coerce")
        score = pd.to_numeric(pool[score_col], errors="coerce")
        gate_pass = pred.ge(pred_floor) & score.notna()
        pool["_score"] = score
        top = pool[score.notna()].sort_values("_score", ascending=False).head(max(1, int(limit)))
        blocked: List[Dict[str, Any]] = []
        for row in top.to_dict("records"):
            reasons: List[str] = []
            if _finite_float(row.get("pred_alpha5_pos")) is None or float(row.get("pred_alpha5_pos")) < pred_floor:
                reasons.append("pred_alpha5_net_pos_below_0_60")
            if _finite_float(row.get("liq20")) is None or float(row.get("liq20")) < liq_floor:
                reasons.append("liq20_below_floor")
            blocked.append(
                {
                    "ticker": str(row.get("symbol") or ""),
                    "stock_name": str(row.get("name") or row.get("symbol") or ""),
                    "score": _round_float(row.get(score_col), 6),
                    "pred_alpha5_net_pos": _round_float(row.get("pred_alpha5_pos"), 6),
                    "pred_alpha3": _round_float(row.get("pred_alpha3"), 6),
                    "pred_alpha5": _round_float(row.get("pred_alpha5"), 6),
                    "liq20": _round_float(row.get("liq20"), 2),
                    "blocking_reasons": reasons,
                }
            )
        diagnostics.append(
            {
                "candidate_id": str(policy["candidate_id"]),
                "lane": str(policy["lane"]),
                "score_col": score_col,
                "liq20_floor": liq_floor,
                "pred_alpha5_pos_min": pred_floor,
                "topn": int(policy["topn"]),
                "pool_rows": int(len(pool)),
                "gate_pass_rows": int(gate_pass.sum()),
                "max_pred_alpha5_net_pos": _round_float(pred.max(), 6),
                "max_score": _round_float(score.max(), 6),
                "top_blocked": blocked,
            }
        )
    return diagnostics


def read_ledger(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_ledger(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, default=_json_default, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def upsert_ledger_rows(existing: Sequence[Mapping[str, Any]], picks: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    out = [dict(row) for row in existing]
    seen = {str(row.get("ledger_key")) for row in out if row.get("ledger_key")}
    appended = 0
    for pick in picks:
        key = str(pick.get("ledger_key") or "")
        if not key or key in seen:
            continue
        out.append(dict(pick))
        seen.add(key)
        appended += 1
    return out, appended


def settle_ledger_rows(rows: Sequence[Mapping[str, Any]], context: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int]:
    out = [dict(row) for row in rows]
    if context.empty or not out:
        return out, 0
    lookup = context.copy()
    lookup["date_key"] = pd.to_datetime(lookup["date"], errors="coerce").dt.date.astype(str)
    lookup["symbol_key"] = lookup["symbol"].astype(str)
    indexed = lookup.set_index(["symbol_key", "date_key"], drop=False)
    changed = 0
    for row in out:
        if str(row.get("status") or "open") != "open":
            continue
        key = (str(row.get("ticker") or ""), str(row.get("date") or ""))
        if key not in indexed.index:
            continue
        hit = indexed.loc[key]
        if isinstance(hit, pd.DataFrame):
            hit = hit.iloc[-1]
        if pd.isna(hit.get("fwd_close_ret_5d")):
            continue
        row.update(
            {
                "status": "settled",
                "settled_at": _utc_now(),
                "ret3": _round_float(hit.get("fwd_close_ret_3d"), 6),
                "ret5": _round_float(hit.get("fwd_close_ret_5d"), 6),
                "alpha3_liq": _round_float(hit.get("alpha3_liq"), 6),
                "alpha5_liq": _round_float(hit.get("alpha5_liq"), 6),
                "alpha3_day": _round_float(hit.get("alpha3_day"), 6),
                "alpha5_day": _round_float(hit.get("alpha5_day"), 6),
                "alpha5_net_cost_0_10": _round_float(float(hit.get("alpha5_liq")) - 0.10, 6),
                "alpha5_net_cost_0_20": _round_float(float(hit.get("alpha5_liq")) - 0.20, 6),
                "alpha5_net_cost_0_35": _round_float(float(hit.get("alpha5_liq")) - 0.35, 6),
                "touch3": _round_float(hit.get("touch5_3d"), 6),
                "touch5": _round_float(hit.get("touch5_5d"), 6),
                "ft55": _round_float(hit.get("ft_5_5"), 6),
                "dd3": _round_float(hit.get("dd5_3d"), 6),
                "dd5": _round_float(hit.get("dd5_5d"), 6),
                "mfe3": _round_float(hit.get("fwd_high_ret_3d"), 6),
                "mae3": _round_float(hit.get("fwd_low_ret_3d"), 6),
            }
        )
        changed += 1
    return out, changed


def summarize_ledger(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    settled = [row for row in rows if row.get("status") == "settled"]
    open_rows = [row for row in rows if row.get("status") == "open"]
    summary: Dict[str, Any] = {"rows": len(rows), "open": len(open_rows), "settled": len(settled), "by_candidate": []}
    if not rows:
        return summary
    frame = pd.DataFrame(rows)
    for candidate_id, grp in frame.groupby("candidate_id", dropna=False):
        item: Dict[str, Any] = {
            "candidate_id": str(candidate_id),
            "rows": int(len(grp)),
            "open": int((grp["status"] == "open").sum()) if "status" in grp else 0,
            "settled": int((grp["status"] == "settled").sum()) if "status" in grp else 0,
        }
        done = grp[grp.get("status").eq("settled")] if "status" in grp else pd.DataFrame()
        if not done.empty:
            for col in ("ret5", "alpha5_liq", "alpha5_net_cost_0_20", "touch3", "dd3", "ft55"):
                vals = pd.to_numeric(done.get(col), errors="coerce")
                if vals.notna().any():
                    item[f"{col}_avg"] = round(float(vals.mean()), 6)
            vals = pd.to_numeric(done.get("alpha5_net_cost_0_20"), errors="coerce")
            if vals.notna().any():
                item["alpha5_net_cost_0_20_win_pct"] = round(float(vals.gt(0).mean() * 100), 2)
        summary["by_candidate"].append(item)
    return summary


def write_report(path_json: Path, path_md: Path, report: Mapping[str, Any]) -> None:
    path_json.parent.mkdir(parents=True, exist_ok=True)
    path_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default, sort_keys=True), encoding="utf-8")
    lines = [
        "# NASDAQ SWING Daily Edge Model",
        "",
        f"- report_version: `{report.get('report_version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- model_version: `{report.get('model_version')}`",
        f"- score_date: `{report.get('score_date')}`",
        f"- panel_path: `{report.get('panel_path')}`",
        f"- picks: `{report.get('pick_count')}`",
        f"- ledger_appended: `{report.get('ledger_appended')}`",
        f"- ledger_settled: `{report.get('ledger_settled')}`",
        "",
        "## Policy Picks",
        "",
        "| Lane | Rank | Ticker | Score | p(alpha5 net>0) | liq20 |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for row in report.get("picks", []):
        lines.append(
            f"| {row.get('lane')} | {row.get('rank')} | {row.get('ticker')} | "
            f"{row.get('score')} | {row.get('pred_alpha5_net_pos')} | {row.get('liq20')} |"
        )
    lines.extend(["", "## Gate Diagnostics", ""])
    for diag in report.get("policy_diagnostics", []):
        lines.append(
            f"- `{diag.get('candidate_id')}` pool `{diag.get('pool_rows')}` "
            f"gate_pass `{diag.get('gate_pass_rows')}` max_p `{diag.get('max_pred_alpha5_net_pos')}` "
            f"max_score `{diag.get('max_score')}`"
        )
        for row in diag.get("top_blocked", [])[:3]:
            lines.append(
                f"  - `{row.get('ticker')}` score `{row.get('score')}` "
                f"p `{row.get('pred_alpha5_net_pos')}` reasons `{','.join(row.get('blocking_reasons') or []) or 'pass'}`"
            )
    lines.extend(["", "## Forward Ledger", "", "```json", json.dumps(report.get("ledger_summary"), ensure_ascii=False, indent=2), "```"])
    path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_model_bundle(path: Path, bundle: Mapping[str, Any]) -> str:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(bundle), path)
    return str(path)


def run_model(args: argparse.Namespace) -> Dict[str, Any]:
    panel_path = resolve_panel_path(str(args.panel))
    raw = read_panel(panel_path)
    context = prepare_context_frame(
        raw,
        min_price=float(args.min_price),
        research_liq_floor=float(args.research_liq_floor),
        cost_pct=float(args.cost_pct),
    )
    ledger_path = Path(args.ledger)
    existing = read_ledger(ledger_path)
    settled_rows, settled_count = settle_ledger_rows(existing, context)
    picks: List[Dict[str, Any]] = []
    train_report: Dict[str, Any] = {}
    policy_diagnostics: List[Dict[str, Any]] = []
    model_bundle_path: Optional[str] = None
    score_date = str(_score_date(context, args.score_date).date()) if not context.empty else None

    if not args.settle_only:
        latest, train_report, bundle = train_and_score_latest(
            context,
            score_date=args.score_date,
            embargo_days=int(args.embargo_days),
            min_train_rows=int(args.min_train_rows),
            max_train_rows=int(args.max_train_rows),
            estimators=int(args.lgbm_estimators),
            seed=int(args.seed),
        )
        score_date = str(pd.to_datetime(latest["date"].iloc[0]).date())
        picks = select_policy_picks(latest)
        policy_diagnostics = build_policy_diagnostics(latest)
        if not args.no_model_bundle:
            model_bundle_path = save_model_bundle(Path(args.model_bundle), bundle)

    appended = 0
    ledger_rows = settled_rows
    if not args.no_ledger:
        ledger_rows, appended = upsert_ledger_rows(settled_rows, picks)
        if not args.dry_run:
            write_ledger(ledger_path, ledger_rows)

    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "model_version": MODEL_VERSION,
        "strategy_family": STRATEGY_FAMILY,
        "signal_class": SIGNAL_CLASS,
        "mode": "model_lane_forward_shadow",
        "panel_path": str(panel_path),
        "score_date": score_date,
        "policies": list(POLICIES),
        "policy_diagnostics": policy_diagnostics,
        "train_report": train_report,
        "model_bundle_path": model_bundle_path,
        "picks": picks,
        "pick_count": len(picks),
        "ledger_path": str(ledger_path),
        "ledger_appended": appended,
        "ledger_settled": settled_count,
        "ledger_summary": summarize_ledger(ledger_rows),
        "capital_status": "shadow_only_no_real_capital",
        "promotion_note": "NASDAQ SWING model lane is active for daily shadow observation; real capital requires forward alpha confirmation.",
    }
    if not args.dry_run:
        out_dir = Path(args.out_dir)
        write_report(
            out_dir / "nasdaq_swing_daily_edge_shadow_latest.json",
            out_dir / "nasdaq_swing_daily_edge_shadow_latest.md",
            report,
        )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NASDAQ SWING daily edge model lane and forward ledger.")
    parser.add_argument("--panel", default="latest")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--model-bundle", default=str(DEFAULT_MODEL_BUNDLE))
    parser.add_argument("--score-date", default="")
    parser.add_argument("--min-price", type=float, default=1.0)
    parser.add_argument("--research-liq-floor", type=float, default=10_000_000.0)
    parser.add_argument("--cost-pct", type=float, default=0.20)
    parser.add_argument("--embargo-days", type=int, default=20)
    parser.add_argument("--min-train-rows", type=int, default=100_000)
    parser.add_argument("--max-train-rows", type=int, default=160_000)
    parser.add_argument("--lgbm-estimators", type=int, default=110)
    parser.add_argument("--seed", type=int, default=20260629)
    parser.add_argument("--settle-only", action="store_true")
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--no-model-bundle", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_model(args)
    print(
        json.dumps(
            {
                "score_date": report.get("score_date"),
                "picks": report.get("pick_count"),
                "ledger_appended": report.get("ledger_appended"),
                "ledger_settled": report.get("ledger_settled"),
                "ledger_path": report.get("ledger_path"),
                "model_bundle_path": report.get("model_bundle_path"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
