from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .commands import FULL_KR_SCAN_MAX
from .config import DiscordIntegrationConfig
from .scan_executor import DiscordScanJob
from modules.ui_helpers import build_top5_plus_exception_records, merge_profile_exception_leaders_into_planner

TOP_DEEP_DIR = Path("runtime_state/reports/top_deep")
ARTIFACT_DIR = Path("runtime_state/artifacts")


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


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_limit(value: Any, *, default: int, maximum: int) -> int:
    return max(1, min(maximum, _safe_int(value, default)))


def _normalize_offset(value: Any) -> int:
    return max(0, _safe_int(value, 0))


def _run_sort_ts(path: Path | None, fallback: float = 0.0) -> float:
    if path is None:
        return fallback
    try:
        return path.stat().st_mtime
    except Exception:
        return fallback


def collect_run_index(*, market: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    runs: Dict[str, Dict[str, Any]] = {}
    market_filter = str(market or "").upper()

    if ARTIFACT_DIR.exists():
        for summary_path in ARTIFACT_DIR.glob("RUN-*/scan_pipeline_summary.json"):
            payload = _load_json(summary_path)
            if not isinstance(payload, dict):
                continue
            run_id = str(payload.get("run_id") or summary_path.parent.name).strip()
            if not run_id:
                continue
            row = runs.setdefault(run_id, {"run_id": run_id})
            row.update(
                {
                    "market": str(payload.get("market") or row.get("market") or ""),
                    "scan_mode": str(payload.get("scan_mode") or row.get("scan_mode") or ""),
                    "result_count": _safe_int(payload.get("result_count"), _safe_int(row.get("result_count"), 0)),
                    "total_scans": _safe_int(payload.get("total_scans"), _safe_int(row.get("total_scans"), 0)),
                    "filtered_count": _safe_int(payload.get("filtered_count"), _safe_int(row.get("filtered_count"), 0)),
                    "artifact_dir": str(payload.get("artifact_dir") or summary_path.parent),
                    "summary_path": str(summary_path),
                    "mtime": max(float(row.get("mtime") or 0), _run_sort_ts(summary_path)),
                }
            )

    if TOP_DEEP_DIR.exists():
        for report_path in TOP_DEEP_DIR.glob("*.json"):
            payload = _load_json(report_path)
            if not isinstance(payload, list):
                continue
            rows = [row for row in payload if isinstance(row, dict)]
            run_id = str(rows[0].get("run_id") if rows else report_path.stem).strip()
            if not run_id:
                continue
            row = runs.setdefault(run_id, {"run_id": run_id})
            row["top_deep_rows"] = len(rows)
            row["top_deep_path"] = str(report_path)
            row["mtime"] = max(float(row.get("mtime") or 0), _run_sort_ts(report_path))
            if rows:
                row["market"] = str(row.get("market") or rows[0].get("market") or "")
                row["scan_mode"] = str(row.get("scan_mode") or rows[0].get("scan_mode") or "")
                row["latest_generated_at"] = str(rows[0].get("generated_at") or row.get("latest_generated_at") or "")

    out = []
    for row in runs.values():
        if market_filter and str(row.get("market") or "").upper() != market_filter:
            continue
        out.append(row)
    out.sort(key=lambda row: float(row.get("mtime") or 0), reverse=True)
    return out[: max(1, int(limit or 200))]


def run_id_choices(*, current: str = "", market: str = "", limit: int = 25) -> List[str]:
    current_upper = str(current or "").upper()
    choices: List[str] = []
    for row in collect_run_index(market=market, limit=200):
        run_id = str(row.get("run_id") or "")
        if current_upper and current_upper not in run_id.upper():
            continue
        choices.append(run_id)
        if len(choices) >= max(1, min(25, int(limit or 25))):
            break
    return choices


def _latest_run_id(rows: List[Dict[str, Any]]) -> str:
    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        if run_id:
            return run_id
    return ""


def build_status_embed(config: DiscordIntegrationConfig) -> Dict[str, Any]:
    rows = _load_local_top_deep_reports(limit=20)
    runs = collect_run_index(limit=200)
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
            {"name": "Stored Runs", "value": str(len(runs)), "inline": True},
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
    alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
    practical_gate = row.get("practical_entry_gate") if isinstance(row.get("practical_entry_gate"), dict) else {}
    gate_evidence = practical_gate.get("evidence") if isinstance(practical_gate.get("evidence"), dict) else {}
    section = alignment.get("analysis_section") or "Top5"
    section_rank = alignment.get("analysis_section_rank") or row.get("rank")
    lines = [
        f"구분: {section} #{section_rank or '-'}",
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
    if practical_gate.get("level") in {"pass", "near", "small_sample", "watch"}:
        lines.append(
            "80%필터: "
            f"{practical_gate.get('label') or '-'}"
            f" · n={gate_evidence.get('sample_n', '-')}"
            f" · 실전승률 {gate_evidence.get('practical_win_pct', '-')}%"
        )
    return "\n".join(lines)[:1024]


def build_top_deep_embeds(
    *,
    ticker: str = "",
    run_id: str = "",
    market: str = "",
    offset: int = 0,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    safe_offset = _normalize_offset(offset)
    safe_limit = _normalize_limit(limit, default=10, maximum=10)
    rows = _load_local_top_deep_reports(limit=500)
    if market:
        rows = [row for row in rows if str(row.get("market") or "").upper() == str(market).upper()]
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
    def _top_deep_sort_key(row: Dict[str, Any]) -> tuple[int, int, int]:
        alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
        section = str(alignment.get("analysis_section") or "Top5")
        return (
            1 if section == "Exception Leader" else 0,
            _safe_int(alignment.get("analysis_section_rank"), _safe_int(row.get("rank"), 9999)),
            _safe_int(row.get("rank"), 9999),
        )

    rows = sorted(rows, key=_top_deep_sort_key)[safe_offset : safe_offset + safe_limit]
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
            "title": "Top5 + Exception Leader 자동 정밀분석",
            "description": (
                f"Run `{latest_run or '-'}` · offset {safe_offset} · "
                "Top5 메인 + Exception Leader 추가 후보"
            ),
            "color": 0x3498DB,
            "fields": fields[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]


def _load_archive_rows_from_artifact(run_id: str) -> List[Dict[str, Any]]:
    raw_path = ARTIFACT_DIR / str(run_id) / "raw_scan_results.json"
    payload = _load_json(raw_path)
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results_sorted")
    if not isinstance(rows, list):
        scan_result = payload.get("scan_result") if isinstance(payload.get("scan_result"), dict) else {}
        rows = scan_result.get("results")
    return [row for row in rows or [] if isinstance(row, dict)]


def _load_planner_payload_for_run(run_id: str) -> Dict[str, Any]:
    summary_path = ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json"
    summary = _load_json(summary_path)
    if isinstance(summary, dict):
        manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
        planner_path = manifest.get("planner_handoff")
        if planner_path:
            payload = _load_json(Path(str(planner_path)))
            if isinstance(payload, dict):
                return payload
    fallback = Path("runtime_state/shared_working") / str(run_id) / "planner_handoff.json"
    payload = _load_json(fallback)
    return payload if isinstance(payload, dict) else {}


def _load_profile_payload_for_run(run_id: str) -> Dict[str, Any]:
    summary_path = ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json"
    summary = _load_json(summary_path)
    if isinstance(summary, dict):
        manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
        profile_path = manifest.get("profile_diagnostics")
        if profile_path:
            payload = _load_json(Path(str(profile_path)))
            if isinstance(payload, dict):
                return payload
    fallback = Path("runtime_state/shared_working") / str(run_id) / "profile_diagnostics.json"
    payload = _load_json(fallback)
    return payload if isinstance(payload, dict) else {}


def _archive_row_name(row: Dict[str, Any], rank: int) -> str:
    ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("Symbol") or row.get("티커") or "-"
    name = row.get("stock_name") or row.get("Stock Name") or row.get("Name") or row.get("종목명") or ticker
    return f"#{rank} {name} ({ticker})"


def _archive_row_value(row: Dict[str, Any]) -> str:
    decision = row.get("decision") or row.get("Decision") or row.get("signal_label") or row.get("Strategy") or row.get("전략") or "-"
    score = row.get("buy_score") or row.get("Decision Score") or row.get("Score")
    loss = row.get("loss_risk_score") or row.get("Loss Risk")
    day = row.get("day_change_pct") or row.get("Change %") or row.get("Day Change") or row.get("전일비")
    section = row.get("_analysis_section")
    return f"{section or '후보'} · {decision} · 점수 {_fmt_num(score, 1)} · 손실위험 {_fmt_num(loss, 1)} · 당일 {_fmt_pct(day)}"[:1024]


def build_archive_embed(
    *,
    market: str = "",
    ticker: str = "",
    run_id: str = "",
    offset: int = 0,
    limit: int = 10,
) -> Dict[str, Any]:
    safe_offset = _normalize_offset(offset)
    safe_limit = _normalize_limit(limit, default=10, maximum=10)
    rows = _load_local_top_deep_reports(limit=500)
    if market:
        rows = [row for row in rows if str(row.get("market") or "").upper() == str(market).upper()]
    if ticker:
        rows = [row for row in rows if str(row.get("ticker") or "").upper() == str(ticker).upper()]
    if run_id:
        rows = [row for row in rows if str(row.get("run_id") or "") == str(run_id)]
    latest = _latest_run_id(rows)
    selected_run = run_id or latest
    if not selected_run:
        artifact_runs = collect_run_index(market=market, limit=1)
        if artifact_runs:
            selected_run = str(artifact_runs[0].get("run_id") or "")
    run_rows = [row for row in rows if str(row.get("run_id") or "") == selected_run] if selected_run else rows
    source = "top_deep"
    if selected_run:
        artifact_rows = _load_archive_rows_from_artifact(selected_run)
        if artifact_rows:
            source = "top5_plus_exception(raw+planner)"
            planner_payload = _load_planner_payload_for_run(selected_run)
            profile_payload = _load_profile_payload_for_run(selected_run)
            planner_payload = merge_profile_exception_leaders_into_planner(planner_payload, profile_payload)
            run_rows = build_top5_plus_exception_records(artifact_rows, planner_payload)["combined"]
            if ticker:
                run_rows = [
                    row
                    for row in run_rows
                    if str(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "").upper()
                    == str(ticker).upper()
                ]
    fields = []
    ordered_rows = (
        run_rows
        if str(source).startswith("top5_plus_exception")
        else sorted(run_rows, key=lambda r: int(r.get("rank") or r.get("Rank") or 9999))
    )
    for idx, row in enumerate(ordered_rows[safe_offset : safe_offset + safe_limit], start=safe_offset + 1):
        fields.append(
            {
                "name": _archive_row_name(
                    row,
                    int(row.get("_analysis_section_rank") or row.get("rank") or row.get("Rank") or idx),
                ),
                "value": _archive_row_value(row),
                "inline": False,
            }
        )
    return {
        "title": "스캔 아카이브 요약",
        "description": f"Run `{selected_run or '-'}` · source {source} · rows {len(run_rows)} · offset {safe_offset}",
        "color": 0x9B59B6,
        "fields": fields or [{"name": "결과", "value": "표시할 아카이브가 없습니다.", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_runs_embed(*, market: str = "", offset: int = 0, limit: int = 10) -> Dict[str, Any]:
    safe_offset = _normalize_offset(offset)
    safe_limit = _normalize_limit(limit, default=10, maximum=15)
    runs = collect_run_index(market=market, limit=500)
    selected = runs[safe_offset : safe_offset + safe_limit]
    fields = []
    for idx, row in enumerate(selected, start=safe_offset + 1):
        run_id = str(row.get("run_id") or "-")
        generated = str(row.get("latest_generated_at") or "")
        fields.append(
            {
                "name": f"#{idx} {run_id}",
                "value": (
                    f"{row.get('market') or '-'} · {row.get('scan_mode') or '-'} · "
                    f"scan {row.get('total_scans') or 0} / pass {row.get('result_count') or 0} / "
                    f"top_deep {row.get('top_deep_rows') or 0}\n"
                    f"{generated[:19] or row.get('artifact_dir') or '-'}"
                )[:1024],
                "inline": False,
            }
        )
    return {
        "title": "누적 Run 목록",
        "description": (
            f"market `{market or 'ALL'}` · rows {len(runs)} · offset {safe_offset}\n"
            "`run_id`를 `/top_deep run_id:` 또는 `/archive run_id:`에 넣어 선택 조회하세요."
        ),
        "color": 0x1ABC9C,
        "fields": fields or [{"name": "결과", "value": "표시할 누적 Run이 없습니다.", "inline": False}],
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


def build_scan_started_embed(config: DiscordIntegrationConfig, *, job: DiscordScanJob) -> Dict[str, Any]:
    return {
        "title": f"{job.market} 전체 스캔 접수",
        "description": (
            f"Job `{job.job_id}` 실행을 시작했습니다.\n"
            f"max_scan={FULL_KR_SCAN_MAX}, scan_mode=SWING, profile=prod 고정입니다."
        ),
        "color": 0x3498DB,
        "fields": [
            {"name": "Result Channel", "value": config.result_channel_id or "-", "inline": True},
            {"name": "Web", "value": config.web_base_url or "-", "inline": True},
            {"name": "Log", "value": str(job.log_path), "inline": False},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_scan_busy_embed() -> Dict[str, Any]:
    return {
        "title": "전체 스캔 실행 중",
        "description": "이미 실행 중인 KOSPI/KOSDAQ 전체 스캔이 있습니다. 완료 후 다시 요청하세요.",
        "color": 0xF1C40F,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_scan_result_embeds(summary: Dict[str, Any], *, config: DiscordIntegrationConfig) -> List[Dict[str, Any]]:
    job = summary.get("discord_job") if isinstance(summary.get("discord_job"), dict) else {}
    market = str(summary.get("market") or job.get("market") or "-")
    run_id = str(summary.get("run_id") or "-")
    returncode = int(job.get("returncode") if job.get("returncode") is not None else 1)
    ok = returncode == 0 and bool(summary.get("run_id"))
    warnings = summary.get("warnings") if isinstance(summary.get("warnings"), list) else []
    warning_text = "\n".join(
        f"- {item.get('code')}: {item.get('message')}"
        for item in warnings[:3]
        if isinstance(item, dict)
    )
    if not warning_text:
        warning_text = "-"
    fields = [
        {"name": "Run", "value": run_id, "inline": True},
        {"name": "Market", "value": market, "inline": True},
        {"name": "Status", "value": "완료" if ok else f"실패/확인 필요 ({returncode})", "inline": True},
        {"name": "Scanned", "value": str(summary.get("total_scans") or 0), "inline": True},
        {"name": "Passed", "value": str(summary.get("result_count") or 0), "inline": True},
        {"name": "Filtered", "value": str(summary.get("filtered_count") or 0), "inline": True},
        {"name": "Warnings", "value": warning_text[:1024], "inline": False},
        {"name": "Web", "value": config.web_base_url or "-", "inline": False},
    ]
    log_path = str(job.get("log_path") or "")
    if log_path:
        fields.append({"name": "Log", "value": log_path, "inline": False})

    embeds = [
        {
            "title": f"{market} 전체 스캔 결과",
            "description": (
                f"Job `{job.get('job_id') or '-'}` · 웹/아카이브와 같은 run artifact 기준으로 표시합니다."
            ),
            "color": 0x2ECC71 if ok else 0xE74C3C,
            "fields": fields[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]
    if ok:
        embeds.extend(build_top_deep_embeds(run_id=run_id, limit=10))
    return embeds[:10]


def build_macro_refresh_embed(*, market: str = "KR") -> Dict[str, Any]:
    try:
        from modules.live_scan_context import normalize_market_key
        from modules.macro_scheduler import get_macro_context
        from modules.scan_policy import compute_market_gate

        normalized = normalize_market_key(market)
        macro = get_macro_context(force_refresh=True, market_group=normalized)
        gate = compute_market_gate("KOSPI" if normalized == "KR" else normalized)
        fields = [
            {"name": "Macro State", "value": str(macro.get("macro_state") or "-"), "inline": True},
            {"name": "Risk", "value": _fmt_num(macro.get("macro_risk_score"), 1), "inline": True},
            {"name": "Penalty", "value": _fmt_num(macro.get("macro_penalty"), 1), "inline": True},
            {"name": "VIX", "value": _fmt_num(macro.get("vix"), 2), "inline": True},
            {"name": "TNX", "value": _fmt_num(macro.get("tnx"), 2), "inline": True},
            {"name": "KRW", "value": _fmt_num(macro.get("krw"), 2), "inline": True},
            {"name": "Market Gate", "value": str(gate.get("msg") or gate.get("state") or "-")[:1024], "inline": False},
        ]
        return {
            "title": "매크로 새로고침",
            "description": f"`{normalized}` 매크로/마켓 게이트 컨텍스트를 갱신했습니다.",
            "color": 0x2ECC71,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "title": "매크로 새로고침 실패",
            "description": str(exc)[:1500],
            "color": 0xE74C3C,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


__all__ = [
    "build_archive_embed",
    "build_macro_refresh_embed",
    "build_runs_embed",
    "build_scan_ack_embed",
    "build_scan_busy_embed",
    "build_scan_result_embeds",
    "build_scan_started_embed",
    "build_status_embed",
    "build_top_deep_embeds",
    "collect_run_index",
    "run_id_choices",
]
