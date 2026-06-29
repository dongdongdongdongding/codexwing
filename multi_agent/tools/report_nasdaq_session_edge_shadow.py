#!/usr/bin/env python3
"""NASDAQ regular-close session edge operational scan lane.

This promotes the strongest recent NASDAQ session candidate into the operator-enabled
new-web scan lane while preserving the sample-limit trace. It records regular-close
picks from the yfinance 5m pre/post session panel, writes a forward ledger, and
settles outcomes once 5D daily bars are available.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.research_nasdaq_daily_edge import DEFAULT_PANEL
from multi_agent.tools.research_nasdaq_production_edge import evaluate_nasdaq_promotion_gate
from multi_agent.tools.research_nasdaq_session_edge import (
    DEFAULT_CACHE_DIR,
    DEFAULT_OUT_DIR,
    DEFAULT_RAW_OHLCV_DIR,
    OUTCOME_COLUMNS,
    _condition_specs,
    _mask,
    _ranked_pick,
    _read_daily_context,
    add_ranks_and_alpha,
    build_session_panel,
    select_symbols,
)

REPORT_VERSION = "nasdaq_session_edge_operational_scan_v1"
MODEL_VERSION = "nasdaq_session_regular_close_strength_liq_trend_top1_v1"
STRATEGY_FAMILY = "NASDAQ_SESSION_EDGE"
SIGNAL_CLASS = "NASDAQ_SWING_SESSION_MODEL"
OPERATIONAL_STATUS = "operator_enabled_live_scan"
SAMPLE_LIMIT_WARNING = "recent_60d_yfinance_5m_intraday_only; multi_year_overnight_provider_not_loaded"
DEFAULT_LEDGER = DEFAULT_OUT_DIR / "nasdaq_session_edge_operational_ledger.jsonl"
DEFAULT_MODEL_BUNDLE = PROJECT_ROOT / "runtime_state" / "models" / "nasdaq_session_edge" / "nasdaq_session_edge_operational_latest.pkl"
DEFAULT_SOURCE_REPORT = DEFAULT_OUT_DIR / "nasdaq_session_edge_search_20260630_020945.json"

SCORING_SESSIONS = {"nasdaq_regular_close", "regular_close", "manual_regular_close"}

POLICIES: Tuple[Dict[str, Any], ...] = (
    {
        "candidate_id": "nasdaq_session_regular_close_strength_liq_trend_top1_v1",
        "lane": "regular_close_strength_liq_trend_top1",
        "session_mode": "regular_close",
        "condition": "regular_close_strength_liq_trend",
        "regime": "all",
        "score_col": "score_liquid_open_drive",
        "topn": 1,
        "min_session_bars": 65,
        "recent_validation_report": str(DEFAULT_SOURCE_REPORT),
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _round(value: Any, digits: int = 6) -> Optional[float]:
    out = _finite(value)
    return None if out is None else round(out, digits)


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f"Unsupported JSON type: {type(value)!r}")


def resolve_panel_path(value: str) -> Path:
    text = str(value or "").strip()
    if text and text.lower() not in {"latest", "auto"}:
        return Path(text).expanduser()
    root = Path("~/research_cache/us_daily/NASDAQ").expanduser()
    candidates = sorted(
        [path for path in root.glob("daily_features_*.parquet") if "_latest_" not in path.name and path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else Path(DEFAULT_PANEL).expanduser()


def build_session_contract(*, market_session: str, session_cutoff: str = "") -> Dict[str, Any]:
    session = str(market_session or "manual_regular_close").strip() or "manual_regular_close"
    scoring_allowed = session.lower() in SCORING_SESSIONS
    return {
        "contract_version": "nasdaq_session_edge_operational_contract_v1",
        "market_session": session,
        "session_cutoff": str(session_cutoff or "").strip(),
        "source_price_kind": "yfinance_5m_prepost",
        "scoring_allowed": bool(scoring_allowed),
        "session_blocked": not bool(scoring_allowed),
        "block_reason": "" if scoring_allowed else "regular_close_core_edge_requires_regular_close_session",
        "data_limit": "yfinance_recent_intraday_only_04_00_20_00_et",
        "operational_route": "new_web_scan_model_lane",
        "capital_status": OPERATIONAL_STATUS,
        "sample_limit_warning": SAMPLE_LIMIT_WARNING,
        "unsupported_session_warning": "20:00-04:00 ET overnight/day-market bars require a separate provider.",
    }


def _latest_source_report(out_dir: Path, explicit: str = "") -> Optional[Path]:
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    files = sorted(
        [path for path in out_dir.glob("nasdaq_session_edge_search_*.json") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if files:
        return files[0]
    return DEFAULT_SOURCE_REPORT if DEFAULT_SOURCE_REPORT.exists() else None


def _policy_match(policy: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return (
        str(candidate.get("session_mode") or "") == str(policy.get("session_mode") or "")
        and str(candidate.get("condition") or "") == str(policy.get("condition") or "")
        and str(candidate.get("regime") or "all") == str(policy.get("regime") or "all")
        and str(candidate.get("score") or "") == str(policy.get("score_col") or "")
        and int(candidate.get("topn") or 0) == int(policy.get("topn") or 0)
    )


def _blocked_validation(reason: str) -> Dict[str, Any]:
    gate = evaluate_nasdaq_promotion_gate({})
    gate["gate_version"] = "nasdaq_session_recent_shadow_gate_v1"
    gate["status"] = "blocked"
    gate["capital_status"] = OPERATIONAL_STATUS
    gate["promotion_ready"] = False
    gate["blocking_reasons"] = [reason] + list(gate.get("blocking_reasons") or [])
    return {
        "source_report": None,
        "metrics": {},
        "recent_shadow_gate": gate,
        "promotion_gate": evaluate_nasdaq_promotion_gate({}),
        "recent_shadow_ready": False,
        "promotion_ready": False,
    }


def load_policy_validation(out_dir: Path, *, source_report: str = "", policies: Sequence[Mapping[str, Any]] = POLICIES) -> Dict[str, Any]:
    report_path = _latest_source_report(out_dir, explicit=source_report)
    if report_path is None:
        return {"source_report": None, "policies": {str(p["candidate_id"]): _blocked_validation("source_report_missing") for p in policies}}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {"source_report": str(report_path), "policies": {str(p["candidate_id"]): _blocked_validation("source_report_unreadable") for p in policies}}
    candidates = payload.get("top_candidates") if isinstance(payload.get("top_candidates"), list) else []
    by_policy: Dict[str, Any] = {}
    for policy in policies:
        candidate_id = str(policy["candidate_id"])
        match = next((row for row in candidates if isinstance(row, dict) and _policy_match(policy, row)), None)
        if not match:
            item = _blocked_validation("validated_candidate_missing")
            item["source_report"] = str(report_path)
            by_policy[candidate_id] = item
            continue
        by_policy[candidate_id] = {
            "source_report": str(report_path),
            "metrics": match.get("metrics") or {},
            "recent_shadow_gate": match.get("recent_shadow_gate") or {},
            "promotion_gate": match.get("promotion_gate") or {},
            "recent_shadow_ready": bool(match.get("recent_shadow_ready")),
            "promotion_ready": bool(match.get("promotion_ready")),
            "condition": match.get("condition"),
            "score": match.get("score"),
            "topn": match.get("topn"),
            "regime": match.get("regime", "all"),
        }
    return {"source_report": str(report_path), "policies": by_policy}


def _condition_lookup() -> Dict[str, Tuple[str, Tuple[Tuple[str, float], ...]]]:
    return {name: (mode, specs) for name, mode, specs in _condition_specs()}


def select_shadow_picks(
    panel: pd.DataFrame,
    *,
    policies: Sequence[Mapping[str, Any]] = POLICIES,
    validation: Mapping[str, Any],
    session_contract: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    if panel.empty or not session_contract.get("scoring_allowed"):
        return []
    conditions = _condition_lookup()
    validations = validation.get("policies") if isinstance(validation.get("policies"), dict) else {}
    rows: List[Dict[str, Any]] = []
    for policy in policies:
        candidate_id = str(policy["candidate_id"])
        gate = validations.get(candidate_id) if isinstance(validations, dict) else None
        if not isinstance(gate, dict) or not gate.get("recent_shadow_ready"):
            continue
        condition_name = str(policy["condition"])
        if condition_name not in conditions:
            continue
        mode, specs = conditions[condition_name]
        score_col = str(policy["score_col"])
        mode_frame = panel[panel["session_mode"].eq(mode)].copy()
        if mode_frame.empty or score_col not in mode_frame.columns:
            continue
        min_bars = int(policy.get("min_session_bars") or 0)
        if min_bars > 0:
            mode_frame = mode_frame[pd.to_numeric(mode_frame["session_bars"], errors="coerce").ge(min_bars)]
        mode_frame = mode_frame[_mask(mode_frame, specs)]
        if mode_frame.empty:
            continue
        score_date = pd.to_datetime(mode_frame["date"], errors="coerce").max().normalize()
        latest = mode_frame[pd.to_datetime(mode_frame["date"], errors="coerce").dt.normalize().eq(score_date)].copy()
        selected = _ranked_pick(latest, score_col, int(policy["topn"]))
        for rank, row in enumerate(selected.sort_values(score_col, ascending=False).to_dict("records"), start=1):
            ticker = str(row.get("symbol") or "").strip()
            date_key = pd.Timestamp(row.get("date")).date().isoformat()
            ledger_key = f"{candidate_id}:{date_key}:{ticker}:{mode}"
            metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
            model_hit_prob = _round(
                metrics.get("ft55", metrics.get("touch3", metrics.get("ret5_pos_rate", 0.0)))
            )
            rows.append(
                {
                    "ledger_key": ledger_key,
                    "candidate_id": candidate_id,
                    "strategy_family": STRATEGY_FAMILY,
                    "signal_class": SIGNAL_CLASS,
                    "model_version": MODEL_VERSION,
                    "lane": str(policy["lane"]),
                    "market": "NASDAQ",
                    "scan_mode": "SWING",
                    "session_mode": mode,
                    "ticker": ticker,
                    "stock_name": str(row.get("name") or ticker),
                    "date": date_key,
                    "score_date": date_key,
                    "rank": rank,
                    "p": model_hit_prob,
                    "model_hit_prob": model_hit_prob,
                    "model_hit_prob_source": "validation_ft55",
                    "score_col": score_col,
                    "score": _round(row.get(score_col)),
                    "entry_gate": condition_name,
                    "condition_specs": list(specs),
                    "entry_reference_price": _round(row.get("entry_price")),
                    "day_change": _round(row.get("session_ret")),
                    "session_ret": _round(row.get("session_ret")),
                    "anchor_ret": _round(row.get("anchor_ret")),
                    "session_close_loc": _round(row.get("session_close_loc")),
                    "session_bars": int(row.get("session_bars") or 0),
                    "liq20": _round(row.get("liq20"), 2),
                    "ret_20d": _round(row.get("ret_20d")),
                    "r_liq20": _round(row.get("r_liq20")),
                    "r_ret_20d": _round(row.get("r_ret_20d")),
                    "r_session_ret": _round(row.get("r_session_ret")),
                    "r_session_close_loc": _round(row.get("r_session_close_loc")),
                    "mkt_ret20_mean": _round(row.get("mkt_ret20_mean")),
                    "mkt_breadth20": _round(row.get("mkt_breadth20")),
                    "target_horizon_days": 5,
                    "target_pct": 5.0,
                    "stop_pct": 5.0,
                    "cost_pct": 0.20,
                    "status": "open",
                    "capital_status": OPERATIONAL_STATUS,
                    "operator_enabled": True,
                    "operational_route": "new_web_scan_model_lane",
                    "sample_limit_warning": SAMPLE_LIMIT_WARNING,
                    "promotion_ready": False,
                    "recent_shadow_ready": True,
                    "validation_metrics": metrics,
                    "ret5_pos_rate": _round(metrics.get("ret5_pos_rate")),
                    "touch3_rate": _round(metrics.get("touch3")),
                    "ft55_rate": _round(metrics.get("ft55")),
                    "dd3_rate": _round(metrics.get("dd3")),
                    "expected_ret5_pct": _round(metrics.get("ret5")),
                    "expected_net_pct": _round(metrics.get("alpha5_net_cost_0_2")),
                    "validation_source_report": gate.get("source_report"),
                    "market_session": session_contract.get("market_session"),
                    "session_cutoff": session_contract.get("session_cutoff"),
                    "source_price_kind": session_contract.get("source_price_kind"),
                    "logged_at": _utc_now(),
                }
            )
    return rows


def read_ledger(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_ledger(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=_json_default) + "\n" for row in rows),
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


def settle_ledger_rows(rows: Sequence[Mapping[str, Any]], panel: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int]:
    out = [dict(row) for row in rows]
    if panel.empty or not out:
        return out, 0
    labelled = panel.copy()
    labelled["date_key"] = pd.to_datetime(labelled["date"], errors="coerce").dt.date.astype(str)
    labelled["symbol_key"] = labelled["symbol"].astype(str)
    labelled["mode_key"] = labelled["session_mode"].astype(str)
    indexed = labelled.set_index(["symbol_key", "date_key", "mode_key"], drop=False)
    changed = 0
    for row in out:
        if str(row.get("status") or "open") != "open":
            continue
        key = (str(row.get("ticker") or ""), str(row.get("date") or ""), str(row.get("session_mode") or ""))
        if key not in indexed.index:
            continue
        hit = indexed.loc[key]
        if isinstance(hit, pd.DataFrame):
            hit = hit.iloc[-1]
        if _finite(hit.get("fwd_close_ret_5d")) is None:
            continue
        row.update(
            {
                "status": "settled",
                "settled_at": _utc_now(),
                "ret3": _round(hit.get("fwd_close_ret_3d")),
                "ret5": _round(hit.get("fwd_close_ret_5d")),
                "alpha5_session_liq": _round(hit.get("alpha5_session_liq")),
                "alpha5_net_cost_0_20": _round(hit.get("alpha5_net")),
                "touch3": _round(hit.get("touch5_3d")),
                "touch5": _round(hit.get("touch5_5d")),
                "ft55": _round(hit.get("ft_5_5")),
                "dd3": _round(hit.get("dd5_3d")),
                "dd5": _round(hit.get("dd5_5d")),
                "mfe3": _round(hit.get("fwd_high_ret_3d")),
                "mae3": _round(hit.get("fwd_low_ret_3d")),
            }
        )
        changed += 1
    return out, changed


def summarize_ledger(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "rows": len(rows),
        "open": int(sum(1 for row in rows if row.get("status") == "open")),
        "settled": int(sum(1 for row in rows if row.get("status") == "settled")),
        "by_candidate": [],
    }
    if not rows:
        return summary
    frame = pd.DataFrame(rows)
    for candidate_id, group in frame.groupby("candidate_id", dropna=False):
        item = {
            "candidate_id": str(candidate_id),
            "rows": int(len(group)),
            "open": int((group.get("status") == "open").sum()) if "status" in group else 0,
            "settled": int((group.get("status") == "settled").sum()) if "status" in group else 0,
        }
        done = group[group["status"].eq("settled")] if "status" in group else pd.DataFrame()
        if not done.empty:
            for col in ("ret5", "alpha5_net_cost_0_20", "touch3", "ft55", "dd3"):
                vals = pd.to_numeric(done.get(col), errors="coerce")
                if vals.notna().any():
                    item[f"{col}_avg"] = _round(vals.mean())
            vals = pd.to_numeric(done.get("alpha5_net_cost_0_20"), errors="coerce")
            if vals.notna().any():
                item["alpha5_net_cost_0_20_win_pct"] = _round(vals.gt(0.0).mean() * 100.0, 2)
        summary["by_candidate"].append(item)
    return summary


def save_model_bundle(path: Path, payload: Mapping[str, Any]) -> str:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(payload), path)
    return str(path)


def write_report(path_json: Path, path_md: Path, report: Mapping[str, Any]) -> None:
    path_json.parent.mkdir(parents=True, exist_ok=True)
    path_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    contract = report.get("session_contract") if isinstance(report.get("session_contract"), dict) else {}
    lines = [
        "# NASDAQ Session Edge Operational Scan Lane",
        "",
        f"- report_version: `{report.get('report_version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- model_version: `{report.get('model_version')}`",
        f"- market_session: `{contract.get('market_session')}`",
        f"- source_price_kind: `{contract.get('source_price_kind')}`",
        f"- scoring_allowed: `{contract.get('scoring_allowed')}`",
        f"- score_date: `{report.get('score_date')}`",
        f"- pick_count: `{report.get('pick_count')}`",
        f"- ledger_appended: `{report.get('ledger_appended')}`",
        f"- ledger_settled: `{report.get('ledger_settled')}`",
        f"- capital_status: `{report.get('capital_status')}`",
        f"- source_report: `{report.get('source_report')}`",
        f"- unsupported_session_warning: `{contract.get('unsupported_session_warning')}`",
        "",
        "## Policies",
        "",
    ]
    for policy in report.get("policies", []):
        validation = (report.get("validation", {}).get("policies", {}) or {}).get(policy.get("candidate_id"), {})
        metrics = validation.get("metrics") or {}
        lines.append(
            f"- `{policy.get('candidate_id')}` `{policy.get('condition')}` / `{policy.get('score_col')}` top{policy.get('topn')} "
            f"recent_validated `{validation.get('recent_shadow_ready')}` production `{validation.get('promotion_ready')}` "
            f"ret5 `{metrics.get('ret5')}` win `{metrics.get('ret5_pos_rate')}` net `{metrics.get('alpha5_net_cost_0_2')}` "
            f"touch `{metrics.get('touch3')}` ft `{metrics.get('ft55')}` dd `{metrics.get('dd3')}`"
        )
    lines.extend(["", "## Picks", "", "| Rank | Ticker | Score | Entry | SessionRet | r_liq20 | r_ret20 |"])
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for row in report.get("picks", []):
        lines.append(
            f"| {row.get('rank')} | {row.get('ticker')} | {row.get('score')} | {row.get('entry_reference_price')} | "
            f"{row.get('session_ret')} | {row.get('r_liq20')} | {row.get('r_ret_20d')} |"
        )
    if report.get("session_blocked"):
        lines.extend(["", "## Session Gate", "", f"- blocked_reason: `{report.get('session_block_reason')}`"])
    lines.extend(["", "## Ledger", "", "```json", json.dumps(report.get("ledger_summary"), ensure_ascii=False, indent=2), "```"])
    path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_model(args: argparse.Namespace) -> Dict[str, Any]:
    out_dir = Path(args.out_dir)
    contract = build_session_contract(
        market_session=getattr(args, "market_session", ""),
        session_cutoff=getattr(args, "session_cutoff", ""),
    )
    validation = load_policy_validation(out_dir, source_report=str(args.source_report or ""))
    ledger_path = Path(args.ledger)
    existing = read_ledger(ledger_path)

    panel = pd.DataFrame(columns=["date", "symbol", "session_mode", *OUTCOME_COLUMNS])
    fetch_stats: Dict[str, Any] = {"skipped": True, "reason": ""}
    picks: List[Dict[str, Any]] = []
    settled_rows = existing
    settled_count = 0
    score_date: Optional[str] = None
    model_bundle_path: Optional[str] = None

    should_build_panel = bool(contract.get("scoring_allowed")) or bool(args.settle_blocked_session)
    if should_build_panel:
        panel_path = resolve_panel_path(str(args.panel))
        daily = _read_daily_context(panel_path)
        symbols = select_symbols(daily, max_symbols=int(args.max_symbols), min_liq20=float(args.min_liq20))
        panel, fetch_stats = build_session_panel(
            daily=daily,
            symbols=symbols,
            cache_dir=Path(args.cache_dir),
            raw_dir=Path(args.raw_dir),
            period=str(args.period),
            interval=str(args.interval),
            timeout=int(args.timeout),
            refresh=bool(args.refresh_cache),
            fetch=not bool(args.no_fetch),
            require_outcome=False,
        )
        panel = add_ranks_and_alpha(panel)
        settled_rows, settled_count = settle_ledger_rows(existing, panel)
        if bool(contract.get("scoring_allowed")) and not args.settle_only:
            picks = select_shadow_picks(panel, validation=validation, session_contract=contract)
            if picks:
                score_date = str(picks[0].get("score_date") or "")
    else:
        fetch_stats = {"skipped": True, "reason": str(contract.get("block_reason") or "session_blocked")}

    ledger_rows, appended = upsert_ledger_rows(settled_rows, picks)
    if not args.no_ledger and not args.dry_run:
        write_ledger(ledger_path, ledger_rows)

    bundle = {
        "report_version": REPORT_VERSION,
        "model_version": MODEL_VERSION,
        "strategy_family": STRATEGY_FAMILY,
        "signal_class": SIGNAL_CLASS,
        "policies": list(POLICIES),
        "validation": validation,
        "session_contract": contract,
        "capital_status": OPERATIONAL_STATUS,
        "operational_route": "new_web_scan_model_lane",
        "sample_limit_warning": SAMPLE_LIMIT_WARNING,
    }
    if not args.no_model_bundle and not args.dry_run:
        model_bundle_path = save_model_bundle(Path(args.model_bundle), bundle)

    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _utc_now(),
        "model_version": MODEL_VERSION,
        "strategy_family": STRATEGY_FAMILY,
        "signal_class": SIGNAL_CLASS,
        "mode": "operator_enabled_new_web_scan_forward_ledger",
        "session_contract": contract,
        "market_session": contract.get("market_session"),
        "session_blocked": bool(contract.get("session_blocked")),
        "session_block_reason": contract.get("block_reason") or "",
        "source_report": validation.get("source_report"),
        "validation": validation,
        "policies": list(POLICIES),
        "score_date": score_date,
        "fetch_stats": fetch_stats,
        "picks": picks,
        "pick_count": len(picks),
        "ledger_path": str(ledger_path),
        "ledger_appended": appended,
        "ledger_settled": settled_count,
        "ledger_summary": summarize_ledger(ledger_rows),
        "model_bundle_path": model_bundle_path,
        "capital_status": OPERATIONAL_STATUS,
        "operational_route": "new_web_scan_model_lane",
        "sample_limit_warning": SAMPLE_LIMIT_WARNING,
        "promotion_ready": False,
        "promotion_note": (
            "Operator-enabled for the new-web NASDAQ/SWING scan lane. Position sizing remains conservative because "
            "the validation sample is recent 5m intraday only; multi-year/overnight provider expansion is still traced."
        ),
    }
    if not args.dry_run:
        write_report(
            out_dir / "nasdaq_session_edge_operational_latest.json",
            out_dir / "nasdaq_session_edge_operational_latest.md",
            report,
        )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NASDAQ regular-close session edge operational scan lane.")
    parser.add_argument("--panel", default=os.getenv("AG_NASDAQ_SESSION_EDGE_PANEL", "latest"))
    parser.add_argument("--raw-dir", default=os.getenv("AG_NASDAQ_SESSION_EDGE_RAW_DIR", str(DEFAULT_RAW_OHLCV_DIR)))
    parser.add_argument("--cache-dir", default=os.getenv("AG_NASDAQ_SESSION_EDGE_CACHE_DIR", str(DEFAULT_CACHE_DIR)))
    parser.add_argument("--out-dir", default=os.getenv("AG_NASDAQ_SESSION_EDGE_OUT_DIR", str(DEFAULT_OUT_DIR)))
    parser.add_argument("--ledger", default=os.getenv("AG_NASDAQ_SESSION_EDGE_LEDGER", str(DEFAULT_LEDGER)))
    parser.add_argument("--model-bundle", default=os.getenv("AG_NASDAQ_SESSION_EDGE_MODEL_BUNDLE", str(DEFAULT_MODEL_BUNDLE)))
    parser.add_argument("--source-report", default=os.getenv("AG_NASDAQ_SESSION_EDGE_SOURCE_REPORT", ""))
    parser.add_argument(
        "--market-session",
        default=os.getenv("AG_NASDAQ_SESSION_EDGE_MARKET_SESSION") or os.getenv("AG_PRIMARY_SESSION_ID") or "manual_regular_close",
    )
    parser.add_argument(
        "--session-cutoff",
        default=os.getenv("AG_NASDAQ_SESSION_EDGE_SESSION_CUTOFF") or os.getenv("AG_PRIMARY_SESSION_CUTOFF") or "",
    )
    parser.add_argument("--max-symbols", type=int, default=int(os.getenv("AG_NASDAQ_SESSION_EDGE_MAX_SYMBOLS", "120")))
    parser.add_argument("--min-liq20", type=float, default=float(os.getenv("AG_NASDAQ_SESSION_EDGE_MIN_LIQ20", "100000000")))
    parser.add_argument("--period", default=os.getenv("AG_NASDAQ_SESSION_EDGE_PERIOD", "60d"))
    parser.add_argument("--interval", default=os.getenv("AG_NASDAQ_SESSION_EDGE_INTERVAL", "5m"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("AG_NASDAQ_SESSION_EDGE_TIMEOUT", "20")))
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--settle-only", action="store_true")
    parser.add_argument("--settle-blocked-session", action="store_true")
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--no-model-bundle", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    report = run_model(parse_args())
    print(
        json.dumps(
            {
                "report_version": report.get("report_version"),
                "pick_count": report.get("pick_count"),
                "score_date": report.get("score_date"),
                "ledger_appended": report.get("ledger_appended"),
                "ledger_settled": report.get("ledger_settled"),
                "capital_status": report.get("capital_status"),
                "session_blocked": report.get("session_blocked"),
                "source_report": report.get("source_report"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
