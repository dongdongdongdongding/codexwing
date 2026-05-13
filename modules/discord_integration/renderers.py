from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .commands import FULL_KR_SCAN_MAX
from .config import DiscordIntegrationConfig

TOP_DEEP_DIR = Path("runtime_state/reports/top_deep")


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        return float(value)
    except Exception:
        return None


def _fmt_num(value: Any, digits: int = 1) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric:.{digits}f}"


def _fmt_pct(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric:+.2f}%"


def _load_local_top_deep_reports(limit: int = 100) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not TOP_DEEP_DIR.exists():
        return rows
    files = sorted(TOP_DEEP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[: max(1, int(limit or 100))]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, list):
            rows.extend([row for row in payload if isinstance(row, dict)])
    return rows


def _latest_run_id(rows: List[Dict[str, Any]]) -> str:
    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        if run_id:
            return run_id
    return ""


def build_status_embed(config: DiscordIntegrationConfig) -> Dict[str, Any]:
    rows = _load_local_top_deep_reports(limit=20)
    validation = config.validate()
    return {
        "title": "Swing Bot Status",
        "description": "Discord remote control is configured.",
        "color": 0x2ECC71 if validation["ok"] else 0xE74C3C,
        "fields": [
            {"name": "Config", "value": "OK" if validation["ok"] else "Needs setup", "inline": True},
            {"name": "Dry Run", "value": str(config.dry_run), "inline": True},
            {"name": "Scan Max", "value": str(FULL_KR_SCAN_MAX), "inline": True},
            {"name": "Latest Run", "value": _latest_run_id(rows) or "-", "inline": True},
            {"name": "Top Deep Rows", "value": str(len(rows)), "inline": True},
            {"name": "Scan Exec", "value": "enabled" if config.enable_scan_execution else "disabled", "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _readiness(row: Dict[str, Any]) -> Dict[str, Any]:
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    readiness = trade_plan.get("readiness_analysis") if isinstance(trade_plan.get("readiness_analysis"), dict) else {}
    return readiness if isinstance(readiness, dict) else {}


def _field_value_for_top_deep(row: Dict[str, Any]) -> str:
    readiness = _readiness(row)
    quality = readiness.get("quality") if isinstance(readiness.get("quality"), dict) else {}
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    timing = readiness.get("timing") if isinstance(readiness.get("timing"), dict) else {}
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    lines = [
        f"액션: {judgment.get('action') or row.get('signal_label') or '-'}",
        (
            f"품질 {quality.get('grade') or '-'}({_fmt_num(quality.get('score'), 0)}) / "
            f"상승여력 {upside.get('grade') or '-'}({_fmt_num(upside.get('score'), 0)}) / "
            f"타이밍 {timing.get('grade') or '-'}({_fmt_num(timing.get('score'), 0)})"
        ),
        f"추격위험: {readiness.get('chase_risk_level') or '-'} · 손실위험 {_fmt_num(row.get('loss_risk_score'), 1)}",
        (
            f"Entry {trade_plan.get('entry_policy') or '-'} · "
            f"TP {_fmt_pct(trade_plan.get('target_tp_pct'))} · SL {_fmt_pct(trade_plan.get('stop_sl_pct'))}"
        ),
    ]
    return "\n".join(lines)[:1024]


def build_top_deep_embeds(*, ticker: str = "", run_id: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    rows = _load_local_top_deep_reports(limit=100)
    if run_id:
        rows = [row for row in rows if str(row.get("run_id") or "") == str(run_id)]
    if ticker:
        rows = [row for row in rows if str(row.get("ticker") or "").upper() == str(ticker).upper()]
    if not rows:
        return [
            {
                "title": "Top Deep Reports",
                "description": "표시할 자동 정밀분석 리포트가 없습니다.",
                "color": 0xF1C40F,
            }
        ]
    latest_run = run_id or _latest_run_id(rows)
    if latest_run and not ticker:
        rows = [row for row in rows if str(row.get("run_id") or "") == latest_run]
    rows = sorted(rows, key=lambda row: int(row.get("rank") or 9999))[: max(1, int(limit or 5))]
    fields: List[Dict[str, Any]] = []
    for row in rows:
        rank = int(row.get("rank") or 0)
        name = str(row.get("stock_name") or row.get("ticker") or "-")
        ticker_value = str(row.get("ticker") or "-")
        fields.append(
            {
                "name": f"#{rank} {name} ({ticker_value})",
                "value": _field_value_for_top_deep(row),
                "inline": False,
            }
        )
    return [
        {
            "title": "Top 자동 정밀분석",
            "description": f"Run `{latest_run or '-'}` · 웹 Top 분석과 동일한 readiness 필드 기준",
            "color": 0x3498DB,
            "fields": fields[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]


def build_archive_embed(*, market: str = "", ticker: str = "", run_id: str = "") -> Dict[str, Any]:
    rows = _load_local_top_deep_reports(limit=100)
    if market:
        rows = [row for row in rows if str(row.get("market") or "").upper() == str(market).upper()]
    if ticker:
        rows = [row for row in rows if str(row.get("ticker") or "").upper() == str(ticker).upper()]
    if run_id:
        rows = [row for row in rows if str(row.get("run_id") or "") == str(run_id)]
    latest = _latest_run_id(rows)
    run_rows = [row for row in rows if str(row.get("run_id") or "") == latest] if latest else rows[:5]
    fields = []
    for row in sorted(run_rows, key=lambda r: int(r.get("rank") or 9999))[:5]:
        fields.append(
            {
                "name": f"#{row.get('rank') or '-'} {row.get('ticker') or '-'}",
                "value": (
                    f"{row.get('decision') or row.get('signal_label') or '-'} · "
                    f"점수 {_fmt_num(row.get('buy_score'), 1)} · "
                    f"손실위험 {_fmt_num(row.get('loss_risk_score'), 1)}"
                ),
                "inline": False,
            }
        )
    return {
        "title": "스캔 아카이브 요약",
        "description": f"Run `{latest or '-'}` · rows {len(rows)}",
        "color": 0x9B59B6,
        "fields": fields or [{"name": "결과", "value": "표시할 아카이브가 없습니다.", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_scan_ack_embed(config: DiscordIntegrationConfig, *, market: str) -> Dict[str, Any]:
    enabled = bool(config.enable_scan_execution and not config.dry_run)
    return {
        "title": f"{market} 전체 스캔",
        "description": (
            f"요청 확인: `{market}` 전체 스캔은 max_scan={FULL_KR_SCAN_MAX}, scan_mode=SWING, profile=prod로 고정됩니다.\n"
            + ("실행 준비 완료 상태입니다." if enabled else "현재는 안전 모드라 실제 실행은 막혀 있습니다.")
        ),
        "color": 0x2ECC71 if enabled else 0xF1C40F,
        "fields": [
            {"name": "Dry Run", "value": str(config.dry_run), "inline": True},
            {"name": "Scan Exec", "value": str(config.enable_scan_execution), "inline": True},
            {"name": "Max Scan", "value": str(FULL_KR_SCAN_MAX), "inline": True},
        ],
    }


__all__ = [
    "build_archive_embed",
    "build_scan_ack_embed",
    "build_status_embed",
    "build_top_deep_embeds",
]
