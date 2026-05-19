from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from modules import db_manager


TOP_DEEP_SECTION_ORDER = {
    "KOSDAQ Ordered Shadow": -30,
    "KOSDAQ Low-loss Shadow": -20,
    "KOSDAQ Shadow": -20,
    "KOSPI Shadow": -10,
    "Top5": 0,
    "Exception Leader": 1,
}


def load_top_deep_reports(limit: int = 500) -> Tuple[List[Dict[str, Any]], str]:
    db_rows: List[Dict[str, Any]] = []
    warning = ""
    try:
        db = db_manager.DBManager()
        if db.client:
            res = (
                db.client.table("scan_deep_reports")
                .select("*")
                .order("generated_at", desc=True)
                .limit(int(limit or 500))
                .execute()
            )
            db_rows = list(res.data or [])
    except Exception as exc:
        warning = str(exc)

    local_rows: List[Dict[str, Any]] = []
    report_dir = Path("runtime_state/reports/top_deep")
    if report_dir.exists():
        for path in sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    local_rows.extend([row for row in payload if isinstance(row, dict)])
            except Exception:
                continue
    merged_by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in list(db_rows or []) + list(local_rows or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("report_id") or "")
        if not key:
            key = f"{row.get('run_id') or ''}:{row.get('ticker') or ''}:{row.get('report_version') or ''}"
        if key and key in merged_by_key:
            existing = merged_by_key[key]
            for item_key, value in row.items():
                if item_key not in existing or existing.get(item_key) in (None, "", [], {}):
                    existing[item_key] = value
            continue
        if key:
            merged_by_key[key] = dict(row)
            order.append(key)
        else:
            fallback_key = f"__row_{len(order)}"
            merged_by_key[fallback_key] = dict(row)
            order.append(fallback_key)
    merged = [merged_by_key[key] for key in order]
    merged = sorted(
        merged,
        key=lambda row: str(row.get("generated_at") or row.get("created_at") or ""),
        reverse=True,
    )
    return merged[: int(limit or 500)], warning


def fmt_metric_pct(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "-"


def fmt_metric_num(value: Any, digits: int = 1) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def fmt_krw(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):,.0f}원"
    except Exception:
        return "-"


def fmt_flow_oku(value: Any) -> str:
    if value in (None, ""):
        return "-"
    try:
        numeric = float(value)
        if abs(numeric) >= 100000000:
            return f"{numeric / 100000000:+.1f}억"
        return f"{numeric:+,.0f}"
    except Exception:
        return "-"


def fmt_flow_value(value: Any, unit: Any = None) -> str:
    if value in (None, ""):
        return "-"
    unit_key = str(unit or "").lower()
    if unit_key == "krw":
        return fmt_flow_oku(value)
    try:
        numeric = float(value)
        suffix = "주" if unit_key == "shares" else ""
        return f"{numeric:+,.0f}{suffix}"
    except Exception:
        return "-"


def fmt_flow_leader_caption(flow: Dict[str, Any]) -> str | None:
    if not isinstance(flow, dict):
        return None
    unit = flow.get("flow_unit")
    window = str(flow.get("flow_window") or "").lower()
    primary_label = "당일 외인+기관" if window in {"1d", "day"} else "외인+기관"
    parts: List[str] = []
    flow_asof = flow.get("flow_asof")
    if flow_asof:
        parts.append(f"기준일: {flow_asof}")
    if flow.get("whale_flow_1d") is not None or flow.get("whale_flow") is not None:
        parts.append(f"{primary_label}: {fmt_flow_value(flow.get('whale_flow_1d', flow.get('whale_flow')), unit)}")
    if flow.get("whale_flow_3d") is not None:
        parts.append(f"3일 외인+기관: {fmt_flow_value(flow.get('whale_flow_3d'), unit)}")
    if flow.get("whale_flow_10d") is not None:
        parts.append(f"10일 외인+기관: {fmt_flow_value(flow.get('whale_flow_10d'), unit)}")
    return " · ".join(parts) if parts else None


def infer_top_deep_market(row: Dict[str, Any]) -> str:
    market = str(row.get("market") or "").upper()
    if market:
        return market
    ticker = str(row.get("ticker") or "").upper()
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    if ticker.endswith(".KS"):
        return "KOSPI"
    return "UNKNOWN"


def scan_display_label(run_df: pd.DataFrame) -> str:
    if run_df is None or run_df.empty:
        return "-"
    run_id = str(run_df["run_id"].dropna().iloc[0]) if "run_id" in run_df and not run_df["run_id"].dropna().empty else "-"
    market = str(run_df["_market"].dropna().iloc[0]) if "_market" in run_df and not run_df["_market"].dropna().empty else "-"
    generated = pd.to_datetime(run_df.get("generated_at"), errors="coerce", utc=True)
    generated = generated.dropna()
    if not generated.empty:
        ts = generated.max().tz_convert("Asia/Seoul").strftime("%Y-%m-%d %H:%M")
        return f"{ts} · {market} · {len(run_df)}건 · {run_id}"
    return f"{market} · {len(run_df)}건 · {run_id}"


def top_deep_section_order(value: Dict[str, Any]) -> int:
    if isinstance(value, dict):
        return TOP_DEEP_SECTION_ORDER.get(str(value.get("analysis_section") or "Top5"), 0)
    return 0


def top_deep_section_rank(value: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return value.get("analysis_section_rank")
    return None


def top_deep_section_name(value: Dict[str, Any]) -> str:
    if isinstance(value, dict):
        return str(value.get("analysis_section") or "Top5")
    return "Top5"


__all__ = [
    "TOP_DEEP_SECTION_ORDER",
    "fmt_flow_leader_caption",
    "fmt_flow_oku",
    "fmt_flow_value",
    "fmt_krw",
    "fmt_metric_num",
    "fmt_metric_pct",
    "infer_top_deep_market",
    "load_top_deep_reports",
    "scan_display_label",
    "top_deep_section_name",
    "top_deep_section_order",
    "top_deep_section_rank",
]
