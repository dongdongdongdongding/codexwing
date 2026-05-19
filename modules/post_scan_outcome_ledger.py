from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LEDGER_VERSION = "post_scan_outcome_ledger_v1"
SUMMARY_HORIZONS = (
    ("10m", "return_10m_pct"),
    ("30m", "return_30m_pct"),
    ("1h", "return_1h_pct"),
    ("close", "return_close_pct"),
    ("1d", "return_1d_pct"),
    ("3d", "return_3d_pct"),
    ("5d", "return_5d_pct"),
)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def _load_top_deep_section_map(run_id: str, report_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    base = report_dir or Path("runtime_state/reports/top_deep")
    path = base / f"{run_id}.json"
    if not path.exists():
        return {}
    try:
        reports = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(reports, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for item in reports:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip()
        if not ticker:
            continue
        alignment = item.get("selection_alignment") if isinstance(item.get("selection_alignment"), dict) else {}
        trade_plan = item.get("trade_plan") if isinstance(item.get("trade_plan"), dict) else {}
        out[ticker] = {
            "section": alignment.get("analysis_section") or item.get("analysis_section"),
            "section_rank": alignment.get("analysis_section_rank") or item.get("rank"),
            "source_order": alignment.get("source_order"),
            "scan_entry_reference_price": trade_plan.get("entry_reference_price"),
        }
    return out


def _fallback_section(row: Dict[str, Any]) -> str:
    decision = str(row.get("decision") or "").upper()
    bucket = str(row.get("decision_bucket") or "").lower()
    role = str(row.get("kr_universe_role") or "").upper()
    lane = str(row.get("selection_lane") or "").lower()
    if decision == "EXCEPTION_LEADER" or bucket == "exception_leader" or role == "EXPLOSIVE_LEADER":
        return "Exception Leader"
    if "shadow" in lane:
        return "Shadow"
    return "Top5"


def build_post_scan_ledger_rows(
    outcomes: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    top_deep_section_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    section_map = top_deep_section_map or {}
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []
    for idx, outcome in enumerate(outcomes or [], start=1):
        if not isinstance(outcome, dict):
            continue
        ticker = str(outcome.get("ticker") or "").strip()
        if not ticker:
            continue
        section_meta = section_map.get(ticker, {})
        rank = _safe_int(outcome.get("priority_rank"))
        section_rank = _safe_int(section_meta.get("section_rank")) or rank
        scan_entry = _safe_float(outcome.get("scan_entry_reference_price"))
        if scan_entry is None:
            scan_entry = _safe_float(section_meta.get("scan_entry_reference_price"))
        if scan_entry is None:
            scan_entry = _safe_float(outcome.get("entry_reference_price"))
        row = {
            "ledger_key": f"{run_id}:{ticker}:{rank if rank is not None else idx}:{LEDGER_VERSION}",
            "ledger_version": LEDGER_VERSION,
            "run_id": run_id,
            "ticker": ticker,
            "stock_name": outcome.get("stock_name"),
            "market": outcome.get("market"),
            "scan_mode": outcome.get("scan_mode"),
            "strategy_family": outcome.get("strategy_family"),
            "section": section_meta.get("section") or _fallback_section(outcome),
            "section_rank": section_rank,
            "priority_rank": rank,
            "decision": outcome.get("decision"),
            "decision_bucket": outcome.get("decision_bucket"),
            "recommended_at": outcome.get("recommended_at"),
            "base_trade_date": outcome.get("base_trade_date"),
            "scan_entry_reference_price": scan_entry,
            "entry_reference_price": _safe_float(outcome.get("entry_reference_price")),
            "target_tp_pct": _safe_float(outcome.get("target_tp_pct")),
            "stop_sl_pct": _safe_float(outcome.get("stop_sl_pct")),
            "hold_days": _safe_int(outcome.get("hold_days")),
            "market_gate": outcome.get("market_gate"),
            "scanner_timeframe_profile": outcome.get("scanner_timeframe_profile"),
            "kr_universe_role": outcome.get("kr_universe_role"),
            "selection_lane": outcome.get("selection_lane"),
            "relative_rank_score": _safe_float(outcome.get("relative_rank_score")),
            "loss_risk_score": _safe_float(outcome.get("loss_risk_score")),
            "mfe_intraday_pct": _safe_float(outcome.get("mfe_intraday_pct")),
            "mae_intraday_pct": _safe_float(outcome.get("mae_intraday_pct")),
            "mfe_5d_pct": _safe_float(outcome.get("mfe_5d_pct") or outcome.get("max_high_return_5d_pct")),
            "mae_5d_pct": _safe_float(outcome.get("mae_5d_pct")),
            "target_before_stop_5d": outcome.get("target_before_stop_5d"),
            "stop_before_target_5d": outcome.get("stop_before_target_5d"),
            "target_hit_at_5d": outcome.get("target_hit_at_5d"),
            "stop_hit_at_5d": outcome.get("stop_hit_at_5d"),
            "outcome_path_terminal_status": outcome.get("outcome_path_terminal_status"),
            "outcome_path_label_version": outcome.get("outcome_path_label_version"),
            "source_ref": outcome.get("source_ref"),
            "updated_at": generated_at,
        }
        for _, key in SUMMARY_HORIZONS:
            row[key] = _safe_float(outcome.get(key))
        row["ledger_status"] = "PARTIAL" if any(row.get(key) is not None for _, key in SUMMARY_HORIZONS) else "PENDING"
        if row.get("return_5d_pct") is not None or row.get("target_before_stop_5d") is not None or row.get("stop_before_target_5d") is not None:
            row["ledger_status"] = "MATURED_5D"
        rows.append(row)
    return rows


def _metric(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"n": 0, "win_pct": None, "avg_pct": None, "min_pct": None, "max_pct": None}
    return {
        "n": len(clean),
        "win_pct": round(sum(1 for value in clean if value > 0) / len(clean) * 100.0, 4),
        "avg_pct": round(sum(clean) / len(clean), 6),
        "min_pct": round(min(clean), 6),
        "max_pct": round(max(clean), 6),
    }


def summarize_post_scan_ledger(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in row_list:
        key = (
            str(row.get("market") or "-"),
            str(row.get("scan_mode") or "-"),
            str(row.get("section") or "-"),
        )
        groups.setdefault(key, []).append(row)
    summary_rows: List[Dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        item: Dict[str, Any] = {"market": key[0], "scan_mode": key[1], "section": key[2], "rows": len(group)}
        for label, field in SUMMARY_HORIZONS:
            metric = _metric([_safe_float(row.get(field)) for row in group])
            item[f"{label}_n"] = metric["n"]
            item[f"{label}_win_pct"] = metric["win_pct"]
            item[f"{label}_avg_pct"] = metric["avg_pct"]
            item[f"{label}_min_pct"] = metric["min_pct"]
            item[f"{label}_max_pct"] = metric["max_pct"]
        item["avg_mfe_5d_pct"] = _metric([_safe_float(row.get("mfe_5d_pct")) for row in group])["avg_pct"]
        item["avg_mae_5d_pct"] = _metric([_safe_float(row.get("mae_5d_pct")) for row in group])["avg_pct"]
        stop_labels = [row.get("stop_before_target_5d") for row in group if isinstance(row.get("stop_before_target_5d"), bool)]
        item["stop_first_5d_n"] = len(stop_labels)
        item["stop_first_5d_pct"] = round(sum(1 for value in stop_labels if value) / len(stop_labels) * 100.0, 4) if stop_labels else None
        summary_rows.append(item)
    return {
        "ledger_version": LEDGER_VERSION,
        "rows": len(row_list),
        "pending_rows": sum(1 for row in row_list if row.get("ledger_status") == "PENDING"),
        "partial_rows": sum(1 for row in row_list if row.get("ledger_status") == "PARTIAL"),
        "matured_5d_rows": sum(1 for row in row_list if row.get("ledger_status") == "MATURED_5D"),
        "groups": summary_rows,
    }


def write_run_post_scan_ledger(
    *,
    run_dir: Path,
    outcomes: Iterable[Dict[str, Any]],
    report_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    run_id = run_dir.name
    section_map = _load_top_deep_section_map(run_id, report_dir=report_dir)
    rows = build_post_scan_ledger_rows(outcomes, run_id=run_id, top_deep_section_map=section_map)
    payload = {
        "run_id": run_id,
        "ledger_version": LEDGER_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "storage_policy": {
            "raw_intraday_bars_persisted": False,
            "scope": "emitted_candidates_only",
            "canonical_file": "post_scan_outcome_ledger.json",
        },
        "summary": summarize_post_scan_ledger(rows),
        "rows": rows,
    }
    path = run_dir / "post_scan_outcome_ledger.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload
