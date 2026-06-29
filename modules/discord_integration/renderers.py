from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .commands import FULL_KR_SCAN_MAX
from .config import DiscordIntegrationConfig
from .scan_executor import DiscordScanJob
from modules.admission_metric_copy import metric_label
from modules.candidate_interpretation import LANE_PROFILE, build_candidate_interpretation
from modules.operational_candidate_scoring import MODEL_VALIDATED_LANES
from modules.ticker_names import display_label
from modules.execution_stop_display import build_execution_stop_display
from modules.model_governance import active_policy_metadata
from modules.next_day_explosive_radar import build_next_day_radar_records
from modules.portfolio_exposure import build_portfolio_exposure_summary, render_portfolio_exposure_lines
from modules.runtime_artifact_store import load_runtime_artifact_payload, list_runtime_artifact_payloads
from modules.kis_theme_news_evidence import (
    build_kis_theme_news_evidence,
    format_kis_theme_news_summary,
)
from modules.scan_universe_admission import (
    ADMISSION_SECTION,
    KIS_SHADOW_SECTION,
    NEAR_MISS_SECTION,
    admission_model_summary,
    admission_run_status,
    build_kis_shadow_admission_records,
    build_scan_universe_admission_input_rows,
    build_scan_universe_admission_records,
    kis_shadow_gate_status,
    merge_kis_prefilter_evidence_into_rows,
)
from modules.ui_helpers import enrich_signal_rows_with_planner_trace, merge_profile_exception_leaders_into_planner

TOP_DEEP_DIR = Path("runtime_state/reports/top_deep")
ARTIFACT_DIR = Path("runtime_state/artifacts")
TOP_DEEP_DISCORD_LIMIT = 15
# Discord rejects embeds above 6000 aggregate chars. Keep a conservative local
# budget because Discord's server-side count includes fields we may undercount.
DISCORD_EMBED_SAFE_CHARS = 4800


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


def _fmt_flow(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric:+,.0f}"


def _fmt_flow_line(flow: Dict[str, Any]) -> str:
    window = str(flow.get("flow_window") or "").lower()
    label = "당일" if window in {"1d", "day"} else "수급"
    whale_1d = flow.get("whale_flow_1d", flow.get("whale_flow"))
    whale_3d = flow.get("whale_flow_3d")
    whale_10d = flow.get("whale_flow_10d")
    tail = []
    if whale_3d is not None:
        tail.append(f"3일 외+기 {_fmt_flow(whale_3d)}")
    if whale_10d is not None:
        tail.append(f"10일 외+기 {_fmt_flow(whale_10d)}")
    context = " · " + " / ".join(tail) if tail else ""
    label_prefix = f"{label} " if label != "수급" else ""
    return (
        f"수급: {label_prefix}외인 {_fmt_flow(flow.get('foreigner_1d', flow.get('foreigner')))} / "
        f"기관 {_fmt_flow(flow.get('institution_1d', flow.get('institution')))} / "
        f"개인 {_fmt_flow(flow.get('retail_1d', flow.get('retail')))} · "
        f"외+기 {_fmt_flow(whale_1d)} · 점수 {_fmt_num(flow.get('whale_score'), 0)}{context}"
    )


def _fmt_pct(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "-"
    return f"{numeric:+.2f}%"


def _execution_gate_line(gate: Dict[str, Any]) -> str:
    if not isinstance(gate, dict) or not gate:
        return "실매수 게이트: 근거 부족"
    label = str(gate.get("label") or gate.get("lane") or "-")
    touch = "터치포착" if gate.get("touch_model_found") else "터치근거 약함"
    parts = [
        f"실매수 게이트: {label}",
        touch,
        f"+{_fmt_num(gate.get('buy_premium_pct'), 1)}%매수 기준",
    ]
    if gate.get("return_5d_pct") is not None:
        parts.append(f"5D종가 {_fmt_pct(gate.get('return_5d_pct'))}")
    if gate.get("max_high_return_5d_pct") is not None:
        parts.append(f"5D최고 {_fmt_pct(gate.get('max_high_return_5d_pct'))}")
    if gate.get("touch_rate_pct") is not None:
        parts.append(f"검증터치 {_fmt_num(gate.get('touch_rate_pct'), 1)}%")
    if gate.get("stop_first_risk_pct") is not None:
        parts.append(f"stop-first {_fmt_num(gate.get('stop_first_risk_pct'), 1)}%")
    reasons = gate.get("why_not_buy_ready") or gate.get("block_reasons") or gate.get("scout_reasons") or []
    if isinstance(reasons, list) and reasons:
        parts.append("이유 " + " / ".join(str(reason) for reason in reasons[:2]))
    return " · ".join(parts)[:1024]


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _row_day_change(row: Dict[str, Any]) -> Any:
    admission = row.get("scan_universe_admission") if isinstance(row.get("scan_universe_admission"), dict) else {}
    features = admission.get("feature_values") if isinstance(admission.get("feature_values"), dict) else {}
    price = row.get("price") if isinstance(row.get("price"), dict) else {}
    return _first_present(
        row.get("day_change_pct"),
        row.get("day_return_pct"),
        row.get("prev_pct_change"),
        row.get("Change %"),
        row.get("Day Change"),
        row.get("1D Change"),
        row.get("전일비"),
        features.get("day_return_pct"),
        price.get("day_change_pct"),
    )


def _embed_char_count(embed: Dict[str, Any]) -> int:
    total = len(str(embed.get("title") or "")) + len(str(embed.get("description") or ""))
    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    for field in fields:
        if isinstance(field, dict):
            total += len(str(field.get("name") or "")) + len(str(field.get("value") or ""))
    return total


def _split_embed_fields(
    *,
    title: str,
    description: str,
    color: int,
    fields: List[Dict[str, Any]],
    timestamp: str,
    safe_chars: int = DISCORD_EMBED_SAFE_CHARS,
) -> List[Dict[str, Any]]:
    base = {"title": title, "description": description, "color": color, "timestamp": timestamp}
    if _embed_char_count({**base, "fields": fields}) <= safe_chars:
        return [{**base, "fields": fields[:25]}]

    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for field in fields:
        candidate = current + [field]
        if current and _embed_char_count({**base, "fields": candidate}) > safe_chars:
            chunks.append(current)
            current = []
        clipped = dict(field)
        if _embed_char_count({**base, "fields": [clipped]}) > safe_chars:
            available = max(100, safe_chars - _embed_char_count({**base, "fields": []}) - len(str(clipped.get("name") or "")) - 20)
            clipped["value"] = str(clipped.get("value") or "")[:available]
        current.append(clipped)
    if current:
        chunks.append(current)

    total_pages = len(chunks)
    out: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks, start=1):
        page_desc = description if total_pages == 1 else f"{description} · page {idx}/{total_pages}"
        out.append({**base, "description": page_desc, "fields": chunk[:25]})
    return out


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


def _load_top_deep_reports(limit: int = 100, *, market: str = "", run_id: str = "", ticker: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from modules.db_manager import DBManager

        db = DBManager()
        if db.client:
            query = db.client.table("scan_deep_reports").select("*")
            if market:
                query = query.eq("market", str(market).upper())
            if run_id:
                query = query.eq("run_id", str(run_id))
            if ticker:
                query = query.eq("ticker", str(ticker).upper())
            rows = (
                query.order("generated_at", desc=True)
                .limit(max(1, int(limit or 100)))
                .execute()
                .data
                or []
            )
    except Exception:
        rows = []
    if rows:
        return [row for row in rows if isinstance(row, dict)]
    return _load_local_top_deep_reports(limit=limit)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_pipeline_summary_for_run(run_id: str, base: Dict[str, Any] | None = None) -> Dict[str, Any]:
    summary = dict(base) if isinstance(base, dict) else {}
    local = _load_json(ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json")
    if isinstance(local, dict):
        summary.update(local)
    return summary


def _load_scan_context_for_run(run_id: str) -> Dict[str, Any]:
    if not run_id:
        return {}
    summary_payload = load_runtime_artifact_payload(
        run_id,
        "scan_pipeline_summary",
        local_path=ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json",
    )
    summary = summary_payload if isinstance(summary_payload, dict) else {}
    summary = _load_pipeline_summary_for_run(run_id, summary)
    scanner_payload: Dict[str, Any] = {}
    manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
    scanner_path = manifest.get("scanner_handoff")
    payload = load_runtime_artifact_payload(run_id, "scanner_handoff", local_path=scanner_path)
    if isinstance(payload, dict):
        scanner_payload = payload
    if not scanner_payload:
        payload = _load_json(Path("runtime_state/shared_working") / str(run_id) / "scanner_handoff.json")
        if isinstance(payload, dict):
            scanner_payload = payload
    scanner_summary = scanner_payload.get("summary") if isinstance(scanner_payload.get("summary"), dict) else {}
    market_gate = scanner_summary.get("market_gate")
    if not isinstance(market_gate, dict):
        input_meta = scanner_summary.get("input_meta") if isinstance(scanner_summary.get("input_meta"), dict) else {}
        market_gate = input_meta.get("market_gate") if isinstance(input_meta.get("market_gate"), dict) else {}
    return {
        "summary": summary,
        "scanner_summary": scanner_summary,
        "market_gate": market_gate if isinstance(market_gate, dict) else {},
    }


def _scan_integrity_from_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    integrity = summary.get("scan_integrity") if isinstance(summary.get("scan_integrity"), dict) else {}
    report = integrity.get("report") if isinstance(integrity.get("report"), dict) else {}
    if report:
        return report
    manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
    report_path = manifest.get("scan_integrity_report")
    if not report_path:
        artifact_dir = summary.get("artifact_dir")
        if artifact_dir:
            report_path = str(Path(str(artifact_dir)) / "scan_integrity_report.json")
    payload = load_runtime_artifact_payload(
        str(summary.get("run_id") or ""),
        "scan_integrity_report",
        local_path=report_path,
    ) if report_path or summary.get("run_id") else None
    return payload if isinstance(payload, dict) else {}


def _integrity_status_lines(report: Dict[str, Any]) -> List[str]:
    if not isinstance(report, dict) or not report:
        return ["무결성 리포트: 없음"]
    completeness = _safe_float(report.get("feature_completeness"))
    completeness_text = "-" if completeness is None else f"{completeness * 100:.1f}%"
    flags = report.get("quality_flags") if isinstance(report.get("quality_flags"), list) else []
    return [
        f"무결성: {completeness_text} · snapshot {report.get('snapshot_count', 0)} / raw {report.get('raw_result_count', 0)}",
        f"raw pass {report.get('picked_count', 0)} · deep {report.get('top_deep_report_count', '-')}",
        "flags: " + (", ".join(str(flag) for flag in flags[:5]) if flags else "OK"),
    ]


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


def _parse_ts(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def collect_run_index(*, market: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    runs: Dict[str, Dict[str, Any]] = {}
    market_filter = str(market or "").upper()

    for payload in list_runtime_artifact_payloads(
        artifact_key="scan_pipeline_summary",
        market=market_filter,
        limit=max(1, int(limit or 200)),
    ):
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            continue
        run_market = str(payload.get("market") or "")
        if market_filter and run_market.upper() != market_filter:
            continue
        row = runs.setdefault(run_id, {"run_id": run_id})
        row.update(
            {
                "market": run_market or row.get("market") or "",
                "scan_mode": str(payload.get("scan_mode") or row.get("scan_mode") or ""),
                "result_count": _safe_int(payload.get("result_count"), _safe_int(row.get("result_count"), 0)),
                "total_scans": _safe_int(payload.get("total_scans"), _safe_int(row.get("total_scans"), 0)),
                "filtered_count": _safe_int(payload.get("filtered_count"), _safe_int(row.get("filtered_count"), 0)),
                "artifact_dir": str(payload.get("artifact_dir") or row.get("artifact_dir") or ""),
                "summary_path": "supabase:runtime_artifacts:scan_pipeline_summary",
                "mtime": max(
                    float(row.get("mtime") or 0),
                    _parse_ts(payload.get("updated_at") or payload.get("created_at")),
                ),
                "latest_generated_at": payload.get("created_at") or payload.get("updated_at") or row.get("latest_generated_at"),
            }
        )

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
    rows = _load_top_deep_reports(limit=20)
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
    execution_stop = row.get("execution_stop") if isinstance(row.get("execution_stop"), dict) else {}
    if not execution_stop and isinstance(trade_plan.get("execution_stop"), dict):
        execution_stop = trade_plan["execution_stop"]
    if not execution_stop:
        execution_stop = build_execution_stop_display(row, trade_plan)
    readiness = trade_plan.get("readiness_analysis") if isinstance(trade_plan.get("readiness_analysis"), dict) else {}
    return readiness if isinstance(readiness, dict) else {}


def _field_value_model_lane(interp: Dict[str, Any]) -> str:
    """Concise card for model-validated lanes (swing ensemble / KOSPI intraday).

    The legacy 17-line block is mostly '-' for these price/intraday models (no flow/theme/
    policy/admission axes), which buried the signal. This surfaces only the actionable key
    point: buy + hit-probability + entry→target + hold."""
    def _money(v: Any) -> str:
        try:
            return f"{float(v):,.0f}"
        except Exception:
            return "-"
    prob = interp.get("model_hit_prob_pct")
    prob_s = f"{prob:.0f}%" if isinstance(prob, (int, float)) else "-"
    tp = interp.get("target_tp_pct") or 5.0
    dc = interp.get("day_change_pct")
    scan_mode = str(interp.get("scan_mode") or "").upper()
    badge = interp.get("lane_badge") or ("인트라데이" if scan_mode == "INTRADAY" else "스윙")
    mode_tag = "🟢장중" if scan_mode == "INTRADAY" else "🔵스윙"
    entry_label = interp.get("entry_label")
    entry_str = f"{entry_label} {_money(interp.get('entry_reference_price'))}" if entry_label and entry_label != "종가" else _money(interp.get("entry_reference_price"))
    lines = [
        f"[{mode_tag}·{badge}] 🎯 {interp.get('action_label') or '모델 매수'} · 적중확률 {prob_s}",
        f"진입 {entry_str} → 목표 +{tp:.0f}% {_money(interp.get('target_price'))}"
        f" · {interp.get('hold_note') or '종가 보유'}",
        f"{interp.get('model_prob_label') or '적중확률'} {prob_s} (모델 상위픽)"
        + (f" · 전일비 {dc:+.1f}%" if isinstance(dc, (int, float)) else ""),
        f"구분 {interp.get('section') or 'Top5'} #{interp.get('section_rank') or '-'} · 손절 분산(타이트 X)",
    ]
    return "\n".join(line for line in lines if line)[:1024]


def _field_value_for_top_deep(row: Dict[str, Any]) -> str:
    interpretation = row.get("candidate_interpretation") if isinstance(row.get("candidate_interpretation"), dict) else build_candidate_interpretation(row)
    if interpretation.get("model_lane"):
        return _field_value_model_lane(interpretation)
    data_quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}
    readiness = _readiness(row)
    quality = readiness.get("quality") if isinstance(readiness.get("quality"), dict) else {}
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    timing = readiness.get("timing") if isinstance(readiness.get("timing"), dict) else {}
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    trade_plan = row.get("trade_plan") if isinstance(row.get("trade_plan"), dict) else {}
    execution_stop = row.get("execution_stop") if isinstance(row.get("execution_stop"), dict) else {}
    if not execution_stop and isinstance(trade_plan.get("execution_stop"), dict):
        execution_stop = trade_plan["execution_stop"]
    if not execution_stop:
        execution_stop = build_execution_stop_display(row, trade_plan)
    alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
    winner_profile = alignment.get("validated_winner_profile") if isinstance(alignment.get("validated_winner_profile"), dict) else {}
    flow = row.get("flow") if isinstance(row.get("flow"), dict) else {}
    prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
    practical_gate = row.get("practical_entry_gate") if isinstance(row.get("practical_entry_gate"), dict) else {}
    gate_evidence = practical_gate.get("evidence") if isinstance(practical_gate.get("evidence"), dict) else {}
    display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
    policy_metadata = row.get("policy_metadata") if isinstance(row.get("policy_metadata"), dict) else {}
    if not policy_metadata:
        policy_metadata = active_policy_metadata(market=str(row.get("market") or row.get("Market") or ""), scan_mode=str(row.get("scan_mode") or row.get("Scan Mode") or ""))
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    regime_theme_adjustment = admission.get("regime_theme_adjustment") if isinstance(admission.get("regime_theme_adjustment"), dict) else {}
    section = interpretation.get("section") or alignment.get("analysis_section") or row.get("analysis_section") or ADMISSION_SECTION
    section_rank = interpretation.get("section_rank") or alignment.get("analysis_section_rank") or row.get("rank")
    admission_model = row.get("scan_universe_admission") if isinstance(row.get("scan_universe_admission"), dict) else {}
    scan_interpretation = row.get("scan_result_interpretation") if isinstance(row.get("scan_result_interpretation"), dict) else {}
    kis_theme_news = row.get("kis_theme_news_evidence") if isinstance(row.get("kis_theme_news_evidence"), dict) else {}
    if not kis_theme_news:
        theme_block = row.get("theme") if isinstance(row.get("theme"), dict) else {}
        kis_theme_news = (
            theme_block.get("kis_theme_news_evidence")
            if isinstance(theme_block.get("kis_theme_news_evidence"), dict)
            else build_kis_theme_news_evidence(row)
        )
    kis_theme_news_summary = format_kis_theme_news_summary(kis_theme_news)
    lines = [
        f"구분: {section} #{section_rank or '-'}",
        (
            f"표시계약: {display_contract.get('display_status') or 'VISIBLE'}"
            f" · 원본#{interpretation.get('original_rank') or display_contract.get('original_scan_rank') or alignment.get('raw_scan_rank') or '-'}"
            f" · 기대순위#{interpretation.get('planner_rank') or display_contract.get('planner_priority_rank') or alignment.get('planner_priority_rank') or '-'}"
        ),
        f"액션: {interpretation.get('action_label') or judgment.get('action') or row.get('signal_label') or '-'}",
        (
            f"품질 {quality.get('grade') or '-'}({_fmt_num(quality.get('score'), 0)}) / "
            f"상승여력 {upside.get('grade') or '-'}({_fmt_num(upside.get('score'), 0)}) / "
            f"타이밍 {timing.get('grade') or '-'}({_fmt_num(timing.get('score'), 0)})"
        ),
        f"추격위험: {readiness.get('chase_risk_level') or '-'} · 손실위험 {_fmt_num(row.get('loss_risk_score'), 1)}",
        f"정책: {policy_metadata.get('active_policy_version') or '-'} · {policy_metadata.get('promotion_status') or '-'}",
        (
            f"데이터: {data_quality.get('display_warning_level') or interpretation.get('data_quality_level') or '-'} · "
            f"필수 {_fmt_num(data_quality.get('required_present_pct') or interpretation.get('data_required_present_pct'), 0)}% · "
            f"경고 {', '.join((data_quality.get('visible_warnings') or interpretation.get('data_warnings') or [])[:3]) or '-'}"
        ),
        f"예상순수익(3D): {_fmt_pct(prediction.get('expected_net_return_3d_pct'))} · 모델 {prediction.get('tradable_pnl_model_version') or '-'}",
        (
            f"Admission 지표: {metric_label('candidate_pass_prob_5d')} {_fmt_pct(interpretation.get('realized_expectancy_5d_prob'))} · "
            f"{metric_label('validation_avg_return_5d')} {_fmt_pct(interpretation.get('base_expected_value_5d_pct') or interpretation.get('expected_value_5d_pct'))} · "
            f"{metric_label('validation_worst_return_5d')} {_fmt_pct(interpretation.get('stress_expected_value_5d_pct'))} · "
            f"{metric_label('candidate_model_score_5d')} {_fmt_num(interpretation.get('ranking_score_5d'), 1)}"
        ),
        (
            f"운영검증: {interpretation.get('operational_action_label') or '-'} · "
            f"운영점수 {_fmt_num(interpretation.get('operational_total_score'), 1)} · "
            f"차트비중 {_fmt_pct(interpretation.get('chart_dominance_pct'))} · "
            f"+{_fmt_num(interpretation.get('buy_premium_pct'), 1)}%매수 후 avg5D {_fmt_pct(interpretation.get('buy_premium_base_expected_value_5d_pct'))} / "
            f"worst5D {_fmt_pct(interpretation.get('buy_premium_stress_expected_value_5d_pct'))}"
        ),
        _execution_gate_line(interpretation.get("buy_premium_execution_gate") if isinstance(interpretation.get("buy_premium_execution_gate"), dict) else {}),
        (
            f"국면/테마: 확률x{_fmt_num(regime_theme_adjustment.get('prob_multiplier'), 2)} · "
            f"수익x{_fmt_num(regime_theme_adjustment.get('return_multiplier'), 2)} · "
            f"손절x{_fmt_num(regime_theme_adjustment.get('stop_risk_multiplier'), 2)} · "
            f"신뢰도 {_fmt_num((_safe_float(regime_theme_adjustment.get('confidence')) or 0.0) * 100.0, 0)}%"
        ),
        f"KIS테마/뉴스: {kis_theme_news_summary}" if kis_theme_news_summary else "",
        f"전일비: {_fmt_pct(_row_day_change(row))}",
        _fmt_flow_line(flow),
        (
            f"Entry {trade_plan.get('entry_policy') or '-'} {_fmt_num(interpretation.get('entry_reference_price'), 0)} · "
            f"TP {_fmt_pct(interpretation.get('target_tp_pct'))} · SL {_fmt_pct(interpretation.get('stop_sl_pct'))}"
        ),
    ]
    if execution_stop.get("display_stop_source"):
        stop_line = f"표시손절: {execution_stop.get('display_stop_source')}"
        if execution_stop.get("stop_conflict"):
            stop_line += " · raw/dynamic 충돌, 더 엄격한 값 표시"
        lines.append(stop_line)
    if practical_gate.get("level") in {"pass", "near", "small_sample", "watch"}:
        lines.append(
            "80%필터: "
            f"{practical_gate.get('label') or '-'}"
            f" · n={gate_evidence.get('sample_n', '-')}"
            f" · 실전승률 {gate_evidence.get('practical_win_pct', '-')}%"
        )
    if winner_profile.get("level") in {"pass", "near"}:
        lines.append(
            f"검증프로필: {winner_profile.get('label') or '-'} · "
            f"{winner_profile.get('metrics') or '-'}"
        )
    if admission_model:
        lines.append(
            "Admission 모델: "
            f"{admission_model.get('model_name') or '-'} · "
            f"{metric_label('candidate_pass_prob_5d')} {_fmt_num(admission_model.get('probability_pct'), 1)}% / "
            f"기준 {_fmt_num(admission_model.get('prob_threshold_pct'), 1)}% · "
            f"{admission_model.get('selection_rule') or '-'} · "
            f"{admission_model.get('objective') or admission_model.get('label') or '-'}"
        )
    if scan_interpretation:
        drivers = " / ".join(str(item) for item in (scan_interpretation.get("drivers") or [])[:3]) or "-"
        warnings = " / ".join(str(item) for item in (scan_interpretation.get("warnings") or [])[:2]) or "-"
        lines.append(
            f"모델해석: {scan_interpretation.get('model_decision') or '-'} · "
            f"기준차 {_fmt_num(scan_interpretation.get('threshold_gap_pct_points'), 1)}%p · "
            f"{scan_interpretation.get('action') or '-'}"
        )
        lines.append(f"근거: {drivers}")
        if warnings != "-":
            lines.append(f"경고: {warnings}")
    return "\n".join(line for line in lines if line)[:1024]


def build_top_deep_embeds(
    *,
    ticker: str = "",
    run_id: str = "",
    market: str = "",
    offset: int = 0,
    limit: int = TOP_DEEP_DISCORD_LIMIT,
) -> List[Dict[str, Any]]:
    safe_offset = _normalize_offset(offset)
    safe_limit = _normalize_limit(limit, default=TOP_DEEP_DISCORD_LIMIT, maximum=TOP_DEEP_DISCORD_LIMIT)
    rows = _load_top_deep_reports(limit=500, market=market, run_id=run_id, ticker=ticker)
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
    all_rows = list(rows)
    section_counts: Dict[str, int] = {}
    for row in all_rows:
        alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
        section = str(alignment.get("analysis_section") or row.get("analysis_section") or ADMISSION_SECTION)
        section_counts[section] = section_counts.get(section, 0) + 1
    scan_context = _load_scan_context_for_run(latest_run)
    scan_summary = scan_context.get("summary") if isinstance(scan_context.get("summary"), dict) else {}
    market_gate = scan_context.get("market_gate") if isinstance(scan_context.get("market_gate"), dict) else {}
    integrity_report = _scan_integrity_from_summary(scan_summary)
    exposure_summary = scan_summary.get("portfolio_exposure_summary") if isinstance(scan_summary.get("portfolio_exposure_summary"), dict) else {}
    if not exposure_summary:
        exposure_summary = build_portfolio_exposure_summary(all_rows, run_id=latest_run)
    result_count = _safe_int(scan_summary.get("result_count"), section_counts.get(ADMISSION_SECTION, 0))
    filtered_count = _safe_int(scan_summary.get("filtered_count"), 0)
    gate_name = str(market_gate.get("gate") or "").upper()
    gate_msg = str(market_gate.get("msg") or "")
    zero_primary = section_counts.get(ADMISSION_SECTION, 0) == 0 and section_counts.get(NEAR_MISS_SECTION, 0) > 0
    admission_sorted_rows = sorted(
        all_rows,
        key=lambda row: -float(
            (
                row.get("scan_universe_admission")
                if isinstance(row.get("scan_universe_admission"), dict)
                else {}
            ).get("probability_pct")
            or 0.0
        ),
    )
    admission_summary = {}
    for row in admission_sorted_rows:
        model = row.get("scan_universe_admission") if isinstance(row.get("scan_universe_admission"), dict) else {}
        if model:
            admission_summary = {
                "prob_threshold_pct": model.get("prob_threshold_pct"),
                "has_probability_floor": model.get("has_probability_floor"),
                "threshold_label": model.get("threshold_label"),
                "topn": model.get("topn"),
            }
            break
    admission_status = admission_run_status(
        {
            "summary": admission_summary,
            "passed": [
                row
                for row in admission_sorted_rows
                if isinstance(row.get("scan_universe_admission"), dict)
                and row.get("scan_universe_admission", {}).get("passed")
            ],
            "near_miss": [
                row
                for row in admission_sorted_rows
                if isinstance(row.get("scan_universe_admission"), dict)
                and not row.get("scan_universe_admission", {}).get("passed")
            ],
        }
    )

    def _top_deep_sort_key(row: Dict[str, Any]) -> tuple[int, int, int]:
        alignment = row.get("selection_alignment") if isinstance(row.get("selection_alignment"), dict) else {}
        section = str(alignment.get("analysis_section") or row.get("analysis_section") or ADMISSION_SECTION)
        section_order = {
            KIS_SHADOW_SECTION: -250,
            ADMISSION_SECTION: 0,
            NEAR_MISS_SECTION: 10,
        }.get(section, 50)
        section_rank = (
            _safe_int(
                alignment.get("analysis_section_rank")
                or row.get("analysis_section_rank")
                or row.get("_analysis_section_rank"),
                _safe_int(row.get("rank"), 9999),
            )
            if section in {KIS_SHADOW_SECTION, ADMISSION_SECTION, NEAR_MISS_SECTION}
            else _safe_int(row.get("rank"), 9999)
        )
        return (
            section_order,
            section_rank,
            _safe_int(row.get("rank"), 9999),
        )

    rows = sorted(rows, key=_top_deep_sort_key)[safe_offset : safe_offset + safe_limit]
    fields: List[Dict[str, Any]] = []
    if safe_offset == 0 and not ticker and (zero_primary or gate_name):
        status_lines = [
            f"원본 통과: {result_count}개 · 필터: {filtered_count}개",
            (
                f"섹션: KIS 쉐도우 {section_counts.get(KIS_SHADOW_SECTION, 0)} / "
                f"Admission {section_counts.get(ADMISSION_SECTION, 0)} / "
                f"NearMiss {section_counts.get(NEAR_MISS_SECTION, 0)}"
            ),
        ]
        if gate_msg:
            status_lines.append(f"시장 게이트: {gate_msg}")
        if zero_primary:
            status_lines.append(admission_status.get("message") or "Admission 모델 통과 후보가 없습니다.")
            status_lines.append("의미: 상승 종목이 없다는 확정이 아니라, 이번 후보가 운영 컷을 넘지 못했다는 뜻입니다.")
        status_lines.extend(_integrity_status_lines(integrity_report))
        status_lines.append("포트폴리오 노출: " + " / ".join(render_portfolio_exposure_lines(exposure_summary)[:3]))
        fields.append({"name": "운영 상태", "value": "\n".join(status_lines)[:1024], "inline": False})
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
    if safe_offset == 0 and not ticker and not (zero_primary or gate_name):
        fields.append(
            {
                "name": "데이터 무결성",
                "value": (
                    "\n".join(_integrity_status_lines(integrity_report))
                    + "\n\n포트폴리오 노출\n"
                    + "\n".join(render_portfolio_exposure_lines(exposure_summary))
                )[:1024],
                "inline": False,
            }
        )
    return _split_embed_fields(
        title="Admission 모델 자동 정밀분석",
        description=(
            f"Run `{latest_run or '-'}` · offset {safe_offset} · "
            f"KIS 쉐도우 {section_counts.get(KIS_SHADOW_SECTION, 0)} / "
            f"Admission {section_counts.get(ADMISSION_SECTION, 0)} / "
            f"NearMiss {section_counts.get(NEAR_MISS_SECTION, 0)}"
        ),
        color=0xF1C40F if zero_primary or gate_name == "RED" else 0x3498DB,
        fields=fields,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


_SIGNALS_VIEW = {
    "": {
        "title": "🎯 모델 시그널 (라이브 레인)",
        "description": (
            "🟢장중: 코스피 인트라데이(3일 +5% 터치) · 코스닥 인트라데이(15:00 VWAP가드) | "
            "🔵스윙: 가격앙상블(5일 ft_5_5) · 모델 상위픽 · 목표 +5% · 분산(타이트 손절 X)"
        ),
        "color": 0x2ECC71,
        "empty": "표시할 모델 레인 픽이 없습니다.",
    },
    "INTRADAY": {
        "title": "🟢 인트라데이 시그널 (장중 모델 레인)",
        "description": "코스피 인트라데이(3일 +5% 터치) · 코스닥 인트라데이(15:00 VWAP가드) · 목표 +5% · 분산(타이트 손절 X)",
        "color": 0x2ECC71,
        "empty": "표시할 인트라데이 모델 픽이 없습니다.",
    },
    "SWING": {
        "title": "🔵 스윙 시그널 (스윙 모델 레인)",
        "description": "가격앙상블(5일 ft_5_5) · 진입 종가 · 목표 +5% · 분산(타이트 손절 X)",
        "color": 0x3498DB,
        "empty": "표시할 스윙 모델 픽이 없습니다.",
    },
}


def build_model_signals_embed(*, market: str = "", limit: int = 10, scan_mode: str = "") -> List[Dict[str, Any]]:
    """Concise read of the live model-validated lanes (swing ensemble / KOSPI+KOSDAQ intraday).

    These run in daily ops and write to scan_deep_reports. Surfaces ONLY their picks (planner
    /top_deep mixes in admission rows), latest run per lane, with the model-lane card.
    scan_mode "" = all (/signals), "INTRADAY" = /intraday, "SWING" = /swing — filtered by the
    canonical LANE_PROFILE scan_mode so stale row values can't leak the wrong lane."""
    mode = str(scan_mode or "").upper()
    view = _SIGNALS_VIEW.get(mode, _SIGNALS_VIEW[""])
    rows = _load_top_deep_reports(limit=500, market=market)
    rows = [r for r in rows if isinstance(r, dict) and str(r.get("decision_bucket") or "") in MODEL_VALIDATED_LANES]
    if mode:
        rows = [r for r in rows if str(LANE_PROFILE.get(str(r.get("decision_bucket")), {}).get("scan_mode") or "").upper() == mode]
    if market:
        rows = [r for r in rows if str(r.get("market") or "").upper() == str(market).upper()]
    if not rows:
        return [{"title": view["title"], "description": view["empty"], "color": 0xF1C40F}]
    # keep only the latest run per (lane, market) so a per-market web scan (swing_ensemble routed
    # under SWING-ENS-...-KOSPI vs -KOSDAQ) doesn't hide one market; daily_ops' single combined
    # run_id still works (both markets share it).
    latest: Dict[tuple, tuple] = {}
    for r in rows:
        bucket = str(r.get("decision_bucket") or "")
        key = (bucket, str(r.get("market") or "").upper())
        stamp = str(r.get("generated_at") or "")
        if bucket and (key not in latest or stamp > latest[key][1]):
            latest[key] = (str(r.get("run_id") or ""), stamp)
    keep_runs = {run for run, _ in latest.values()}
    rows = [r for r in rows if str(r.get("run_id") or "") in keep_runs]
    bucket_order = {"kospi_intraday": 0, "kosdaq_intraday_3d_t5_vwap_guard": 1, "swing_ensemble": 2}
    rows.sort(key=lambda r: (bucket_order.get(str(r.get("decision_bucket")), 9), int(r.get("rank") or 0)))
    rows = rows[: max(1, int(limit or 10))]
    fields = []
    for r in rows:
        header = display_label(r.get("ticker"), r.get("stock_name"))   # 종목명 폴백 해석(빈 stock_name 보완)
        interp = r.get("candidate_interpretation") if isinstance(r.get("candidate_interpretation"), dict) else build_candidate_interpretation(r)
        fields.append({"name": header, "value": _field_value_model_lane(interp), "inline": False})
    return _split_embed_fields(
        title=view["title"],
        description=view["description"],
        color=view["color"],
        fields=fields,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _load_archive_rows_from_artifact(run_id: str) -> List[Dict[str, Any]]:
    payload = load_runtime_artifact_payload(
        run_id,
        "raw_scan_results",
        local_path=ARTIFACT_DIR / str(run_id) / "raw_scan_results.json",
    )
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results_sorted")
    if not isinstance(rows, list):
        scan_result = payload.get("scan_result") if isinstance(payload.get("scan_result"), dict) else {}
        rows = scan_result.get("results")
    return [row for row in rows or [] if isinstance(row, dict)]


def _load_planner_payload_for_run(run_id: str) -> Dict[str, Any]:
    summary_payload = load_runtime_artifact_payload(
        run_id,
        "scan_pipeline_summary",
        local_path=ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json",
    )
    summary = summary_payload if isinstance(summary_payload, dict) else {}
    if isinstance(summary, dict):
        manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
        planner_path = manifest.get("planner_handoff")
        payload = load_runtime_artifact_payload(run_id, "planner_handoff", local_path=planner_path)
        if isinstance(payload, dict):
            return payload
    fallback = Path("runtime_state/shared_working") / str(run_id) / "planner_handoff.json"
    payload = _load_json(fallback)
    return payload if isinstance(payload, dict) else {}


def _load_profile_payload_for_run(run_id: str) -> Dict[str, Any]:
    summary_payload = load_runtime_artifact_payload(
        run_id,
        "scan_pipeline_summary",
        local_path=ARTIFACT_DIR / str(run_id) / "scan_pipeline_summary.json",
    )
    summary = summary_payload if isinstance(summary_payload, dict) else {}
    if isinstance(summary, dict):
        manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
        profile_path = manifest.get("profile_diagnostics")
        payload = load_runtime_artifact_payload(run_id, "profile_diagnostics", local_path=profile_path)
        if isinstance(payload, dict):
            return payload
    fallback = Path("runtime_state/shared_working") / str(run_id) / "profile_diagnostics.json"
    payload = _load_json(fallback)
    return payload if isinstance(payload, dict) else {}


def _infer_kr_market_key(market: str = "", scan_summary: Dict[str, Any] | None = None, rows: List[Dict[str, Any]] | None = None) -> str:
    market_key = str(market or (scan_summary or {}).get("market") or "").upper()
    if market_key in {"KOSPI", "KOSDAQ"}:
        return market_key
    tickers = [
        str(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "").upper()
        for row in rows or []
        if isinstance(row, dict)
    ]
    tickers = [ticker for ticker in tickers if ticker]
    if tickers and all(ticker.endswith(".KS") for ticker in tickers):
        return "KOSPI"
    if tickers and all(ticker.endswith(".KQ") for ticker in tickers):
        return "KOSDAQ"
    return ""


def _build_admission_result_for_run(
    run_id: str,
    *,
    market: str = "",
    scan_summary: Dict[str, Any] | None = None,
    limit: int = 5,
) -> Dict[str, Any]:
    if not run_id or run_id == "-":
        return {}
    artifact_rows = _load_archive_rows_from_artifact(run_id)
    summary = scan_summary if isinstance(scan_summary, dict) else {}
    summary = _load_pipeline_summary_for_run(run_id, summary)
    artifact_raw = load_runtime_artifact_payload(
        run_id,
        "raw_scan_results",
        local_path=ARTIFACT_DIR / str(run_id) / "raw_scan_results.json",
    )
    diagnostics = artifact_raw.get("diagnostics") if isinstance(artifact_raw, dict) and isinstance(artifact_raw.get("diagnostics"), dict) else {}
    reject_details = diagnostics.get("reject_details_by_symbol") if isinstance(diagnostics.get("reject_details_by_symbol"), dict) else {}
    if not artifact_rows and not reject_details:
        return {}
    market_key = _infer_kr_market_key(market, summary, artifact_rows)
    if market_key not in {"KOSPI", "KOSDAQ"}:
        return {}
    planner_payload = _load_planner_payload_for_run(run_id)
    profile_payload = _load_profile_payload_for_run(run_id)
    planner_payload = merge_profile_exception_leaders_into_planner(planner_payload, profile_payload)
    enriched_rows = enrich_signal_rows_with_planner_trace(artifact_rows, planner_payload)
    universe_input = build_scan_universe_admission_input_rows(
        enriched_rows,
        diagnostics=diagnostics,
        market=market_key,
    )
    universe_rows = universe_input.get("rows", enriched_rows)
    universe_rows = merge_kis_prefilter_evidence_into_rows(universe_rows, summary)
    result = build_scan_universe_admission_records(
        universe_rows,
        market=market_key,
        limit=max(1, int(limit or 5)),
        include_near_miss=True,
        input_summary=universe_input,
    )
    kis_shadow = build_kis_shadow_admission_records(
        universe_rows,
        market=market_key,
        limit=max(3, _safe_int(limit, 5)),
        include_blocked_watch=True,
    )
    shadow_tickers = {
        str(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "").upper()
        for row in kis_shadow
        if isinstance(row, dict)
    }
    result["kis_shadow"] = kis_shadow
    result["display_records"] = kis_shadow + [
        row
        for row in result.get("all_records", []) or []
        if str(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "").upper()
        not in shadow_tickers
    ]
    return result


def _low_liquidity_rows_value(rows: List[Dict[str, Any]], *, limit: int = 5) -> str:
    lines: List[str] = []
    for idx, row in enumerate(rows[: max(1, int(limit or 5))], start=1):
        ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "-"
        name = row.get("stock_name") or row.get("Stock Name") or row.get("name") or row.get("종목명") or ticker
        admission = row.get("scan_universe_admission") if isinstance(row.get("scan_universe_admission"), dict) else {}
        features = admission.get("feature_values") if isinstance(admission.get("feature_values"), dict) else {}
        interpretation = row.get("scan_result_interpretation") if isinstance(row.get("scan_result_interpretation"), dict) else {}
        reason = admission.get("promotion_block_reason") or admission.get("legacy_reject_reason") or "LIQUIDITY_FILTER_FAIL"
        turnover = _safe_float(features.get("turnover"))
        turnover_text = "-" if turnover is None else f"{turnover / 100_000_000.0:.1f}억"
        lines.append(
            f"#{idx} {name}({ticker}) · 후보확률 {_fmt_num(admission.get('probability_pct'), 1)}% · "
            f"기준차 {_fmt_num(interpretation.get('threshold_gap_pct_points'), 1)}%p · "
            f"거래대금 {turnover_text} · 거래량x{_fmt_num(features.get('volume_ratio'), 2)} · {reason}"
        )
    return ("\n".join(lines) or "저유동성 차단 후보 없음.")[:1024]


def _kis_shadow_rows_value(rows: List[Dict[str, Any]], *, limit: int = 3) -> str:
    lines: List[str] = []
    for idx, row in enumerate(rows[: max(1, int(limit or 3))], start=1):
        ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "-"
        name = row.get("stock_name") or row.get("Stock Name") or row.get("name") or row.get("종목명") or ticker
        admission = row.get("scan_universe_admission") if isinstance(row.get("scan_universe_admission"), dict) else {}
        expectancy = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
        shadow = row.get("kis_shadow_candidate") if isinstance(row.get("kis_shadow_candidate"), dict) else {}
        exit_policy = shadow.get("dynamic_exit_policy") if isinstance(shadow.get("dynamic_exit_policy"), dict) else {}
        if not exit_policy and isinstance(row.get("trade_plan"), dict):
            exit_policy = row["trade_plan"].get("dynamic_exit_policy") if isinstance(row["trade_plan"].get("dynamic_exit_policy"), dict) else {}
        model_rank = shadow.get("runtime_model_rank") or admission.get("model_rank") or "-"
        gate_status = shadow.get("gate_status") or expectancy.get("kis_model_gate_status") or "shadow"
        risk_review = " · risk_review" if shadow.get("risk_review_required") or expectancy.get("risk_review_required") else ""
        exit_text = ""
        if exit_policy:
            exit_text = (
                f" · TP {_fmt_pct(exit_policy.get('target_tp_pct'))}"
                f"/SL {_fmt_pct(exit_policy.get('stop_sl_pct'))}"
                f"/{exit_policy.get('hold_days') or '-'}일"
                f" · {exit_policy.get('risk_level') or 'risk'}"
            )
        theme_news_summary = format_kis_theme_news_summary(
            row.get("kis_theme_news_evidence") if isinstance(row.get("kis_theme_news_evidence"), dict) else build_kis_theme_news_evidence(row)
        )
        theme_news_tail = f" · {theme_news_summary}" if theme_news_summary else ""
        lines.append(
            f"#{idx} {name}({ticker}) · KIS 쉐도우 · score {_fmt_num(admission.get('probability_pct'), 1)}% "
            f"(model#{model_rank}) · 5D win {_fmt_num(expectancy.get('5d_prob'), 1)}% · "
            f"avg5D {_fmt_pct(expectancy.get('base_expected_value_5d_pct'))} · "
            f"min5D {_fmt_pct(expectancy.get('stress_expected_value_5d_pct'))} · "
            f"gate {gate_status}{risk_review}{exit_text} · shadow_only{theme_news_tail}"
        )
    return ("\n".join(lines) or "KIS 쉐도우 후보 없음.")[:1024]


def _kis_shadow_gate_block_value(gate: Dict[str, Any]) -> str:
    gate = gate if isinstance(gate, dict) else {}
    blockers = gate.get("blocking_reasons") if isinstance(gate.get("blocking_reasons"), list) else []
    risk_reasons = gate.get("risk_review_reasons") if isinstance(gate.get("risk_review_reasons"), list) else []
    near = gate.get("near_production_candidate") if isinstance(gate.get("near_production_candidate"), dict) else {}
    near_metrics = near.get("metrics") if isinstance(near.get("metrics"), dict) else {}
    high = (
        gate.get("high_precision_shadow_candidate")
        if isinstance(gate.get("high_precision_shadow_candidate"), dict)
        else {}
    )
    high_metrics = high.get("metrics") if isinstance(high.get("metrics"), dict) else {}
    high_progress = high.get("sample_progress") if isinstance(high.get("sample_progress"), dict) else {}
    lines = [
        f"상태: {gate.get('status') or '-'} · shadow_display_allowed={bool(gate.get('shadow_display_allowed'))} · production_ready={bool(gate.get('production_ready'))}",
        f"프로필: {gate.get('profile') or '-'}",
        f"검증: {gate.get('metrics') or '-'}",
    ]
    if near:
        lines.append(
            "승격근접: "
            f"{near.get('selection_rule') or '-'}"
            f" · n={near_metrics.get('n', '-')}"
            f" · active_days={near_metrics.get('active_days', '-')}"
            f" · hit5 {_fmt_pct(near_metrics.get('hit5_dd10_5d_pct'))}"
            f" · avg5 {_fmt_pct(near_metrics.get('avg_5d_pct'))}"
            f" · min_low {_fmt_pct(near_metrics.get('min_min_low_5d_pct'))}"
            f" · 남은차단 {' / '.join(str(item) for item in (near.get('sample_blockers') or [])[:3]) or '-'}"
        )
    sample = (
        gate.get("sample_progress_shadow_candidate")
        if isinstance(gate.get("sample_progress_shadow_candidate"), dict)
        else {}
    )
    sample_metrics = sample.get("metrics") if isinstance(sample.get("metrics"), dict) else {}
    sample_progress = sample.get("sample_progress") if isinstance(sample.get("sample_progress"), dict) else {}
    if sample:
        lines.append(
            "표본진행관찰: "
            f"{sample.get('selection_rule') or '-'}"
            f" · n={sample_metrics.get('n', '-')}"
            f" · active_days={sample_metrics.get('active_days', '-')}"
            f" · hit5 {_fmt_pct(sample_metrics.get('hit5_dd10_5d_pct'))}"
            f" · avg5 {_fmt_pct(sample_metrics.get('avg_5d_pct'))}"
            f" · min_low {_fmt_pct(sample_metrics.get('min_min_low_5d_pct'))}"
            f" · 표본진행 {_fmt_pct(sample_progress.get('completion_pct'))}"
        )
    if high:
        lines.append(
            "고정밀관찰: "
            f"{high.get('selection_rule') or '-'}"
            f" · n={high_metrics.get('n', '-')}"
            f" · active_days={high_metrics.get('active_days', '-')}"
            f" · hit5 {_fmt_pct(high_metrics.get('hit5_dd10_5d_pct'))}"
            f" · avg5 {_fmt_pct(high_metrics.get('avg_5d_pct'))}"
            f" · min_low {_fmt_pct(high_metrics.get('min_min_low_5d_pct'))}"
            f" · 표본진행 {_fmt_pct(high_progress.get('completion_pct'))}"
        )
    if blockers:
        lines.append("차단: " + " / ".join(str(item) for item in blockers[:5]))
    if risk_reasons:
        lines.append("위험검토: " + " / ".join(str(item) for item in risk_reasons[:3]))
    lines.append("의미: KIS 모델이 상승 터치 후보를 찾더라도 운영 승격/표시는 별도 게이트 통과 전까지 차단합니다.")
    return "\n".join(lines)[:1024]


def _archive_row_name(row: Dict[str, Any], rank: int) -> str:
    ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("Symbol") or row.get("티커") or "-"
    name = row.get("stock_name") or row.get("Stock Name") or row.get("Name") or row.get("name") or row.get("종목명") or ticker
    return f"#{rank} {name} ({ticker})"


def _archive_row_value(row: Dict[str, Any]) -> str:
    interpretation = row.get("candidate_interpretation") if isinstance(row.get("candidate_interpretation"), dict) else build_candidate_interpretation(row)
    if interpretation.get("model_lane"):
        return _field_value_model_lane(interpretation)
    data_quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}
    decision = row.get("decision") or row.get("Decision") or row.get("signal_label") or row.get("Strategy") or row.get("전략") or "-"
    score = row.get("buy_score") or row.get("Decision Score") or row.get("Score")
    loss = row.get("loss_risk_score") or row.get("Loss Risk")
    day = _row_day_change(row)
    section = interpretation.get("section") or row.get("_analysis_section")
    display_contract = row.get("display_contract") if isinstance(row.get("display_contract"), dict) else {}
    policy_metadata = row.get("policy_metadata") if isinstance(row.get("policy_metadata"), dict) else {}
    if not policy_metadata:
        policy_metadata = active_policy_metadata(market=str(row.get("market") or row.get("Market") or ""), scan_mode=str(row.get("scan_mode") or row.get("Scan Mode") or ""))
    admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
    scan_interpretation = row.get("scan_result_interpretation") if isinstance(row.get("scan_result_interpretation"), dict) else {}
    visible = display_contract.get("display_status") or "VISIBLE"
    raw_rank = interpretation.get("original_rank") or display_contract.get("original_scan_rank") or row.get("_raw_scan_rank") or row.get("rank") or row.get("Rank")
    policy_version = interpretation.get("policy_version") or policy_metadata.get("active_policy_version") or "-"
    regime_theme_adjustment = admission.get("regime_theme_adjustment") if isinstance(admission.get("regime_theme_adjustment"), dict) else {}
    text = (
        f"{section or '후보'} · {visible} · 원본#{raw_rank or '-'} · {decision} · "
        f"정책 {policy_version} · {metric_label('candidate_pass_prob_5d')} {_fmt_pct(interpretation.get('realized_expectancy_5d_prob'))} · "
        f"{metric_label('validation_avg_return_5d')} {_fmt_pct(interpretation.get('base_expected_value_5d_pct') or interpretation.get('expected_value_5d_pct'))} · "
        f"{metric_label('validation_worst_return_5d')} {_fmt_pct(interpretation.get('stress_expected_value_5d_pct'))} · "
        f"데이터 {data_quality.get('display_warning_level') or interpretation.get('data_quality_level') or '-'} · "
        f"국면/테마x{_fmt_num(regime_theme_adjustment.get('prob_multiplier'), 2)} · "
        f"점수 {_fmt_num(score, 1)} · 손실위험 {_fmt_num(loss, 1)} · 당일 {_fmt_pct(day)}"
    )
    if scan_interpretation:
        drivers = " / ".join(str(item) for item in (scan_interpretation.get("drivers") or [])[:3]) or "-"
        text += (
            f"\n모델해석 {scan_interpretation.get('model_decision') or '-'} · "
            f"기준차 {_fmt_num(scan_interpretation.get('threshold_gap_pct_points'), 1)}%p · "
            f"{scan_interpretation.get('action') or '-'}\n근거 {drivers}"
        )
    gate = interpretation.get("buy_premium_execution_gate") if isinstance(interpretation.get("buy_premium_execution_gate"), dict) else {}
    if gate:
        text += "\n" + _execution_gate_line(gate)
    return text[:1024]


def _radar_row_name(row: Dict[str, Any], rank: int) -> str:
    ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "-"
    name = row.get("stock_name") or row.get("Stock Name") or row.get("name") or row.get("종목명") or ticker
    return f"레이더 #{rank} {name} ({ticker})"


def _radar_row_value(row: Dict[str, Any]) -> str:
    radar = row.get("next_day_radar") if isinstance(row.get("next_day_radar"), dict) else {}
    reasons = ", ".join(str(value) for value in (radar.get("feature_reasons") or [])[:4]) or "-"
    missing = ", ".join(str(value) for value in (radar.get("unavailable_features") or [])[:3]) or "-"
    return (
        f"score {_fmt_num(radar.get('radar_score'), 1)} · "
        f"익일+5 {_fmt_num(radar.get('next_day_plus5_prob'), 1)} · "
        f"익일+10 {_fmt_num(radar.get('next_day_plus10_prob'), 1)} · "
        f"근거 {reasons} · 미확보 {missing} · shadow_only"
    )[:1024]


def build_next_day_radar_embed(run_id: str, *, market: str = "", limit: int = 5) -> Dict[str, Any]:
    rows = _load_archive_rows_from_artifact(run_id)
    if market:
        rows = [
            row for row in rows
            if str(row.get("market") or row.get("market_subtype") or "").upper() in {"", str(market).upper()}
        ]
    radar_rows = build_next_day_radar_records(rows, limit=limit)
    fields = [
        {"name": _radar_row_name(row, idx), "value": _radar_row_value(row), "inline": False}
        for idx, row in enumerate(radar_rows, start=1)
    ]
    if not fields:
        fields = [{"name": "후보 없음", "value": "별도 급등 레이더 후보가 없습니다.", "inline": False}]
    return {
        "title": "별도 급등 레이더",
        "description": f"Run `{run_id or '-'}` · Admission 모델과 별도인 검증 전 레이더 참고값",
        "color": 0xE67E22,
        "fields": fields[:10],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
    rows = _load_top_deep_reports(limit=500, market=market, run_id=run_id, ticker=ticker)
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
    scan_context = _load_scan_context_for_run(selected_run) if selected_run else {}
    scan_summary = scan_context.get("summary") if isinstance(scan_context.get("summary"), dict) else {}
    integrity_report = _scan_integrity_from_summary(scan_summary)
    exposure_summary = scan_summary.get("portfolio_exposure_summary") if isinstance(scan_summary.get("portfolio_exposure_summary"), dict) else {}
    source = "top_deep"
    admission_result: Dict[str, Any] = {}
    if selected_run:
        artifact_rows = _load_archive_rows_from_artifact(selected_run)
        if artifact_rows:
            source = "scan_universe_admission(raw+planner)"
            admission_result = _build_admission_result_for_run(
                selected_run,
                market=market,
                scan_summary=scan_summary,
                limit=safe_offset + safe_limit,
            )
            run_rows = (
                admission_result.get("display_records")
                or admission_result.get("all_records", [])
            ) if admission_result else []
            top_deep_by_ticker = {
                str(row.get("ticker") or row.get("Ticker") or row.get("티커") or "").upper(): row
                for row in rows
                if str(row.get("run_id") or "") == selected_run
            }
            for row in run_rows:
                key = str(row.get("ticker") or row.get("Ticker") or row.get("티커") or "").upper()
                top_deep_row = top_deep_by_ticker.get(key) or {}
                if top_deep_row.get("policy_metadata") and not row.get("policy_metadata"):
                    row["policy_metadata"] = top_deep_row.get("policy_metadata")
                if top_deep_row.get("realized_expectancy_admission") and not row.get("realized_expectancy_admission"):
                    row["realized_expectancy_admission"] = top_deep_row.get("realized_expectancy_admission")
            if ticker:
                run_rows = [
                    row
                    for row in run_rows
                    if str(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커") or "").upper()
                    == str(ticker).upper()
                ]
            if not exposure_summary:
                exposure_summary = build_portfolio_exposure_summary(run_rows, run_id=selected_run)
    if selected_run and not exposure_summary:
        exposure_summary = build_portfolio_exposure_summary(run_rows, run_id=selected_run)
    fields = []
    ordered_rows = (
        run_rows
        if "scan_universe_admission" in str(source)
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
    if selected_run:
        fields.append(
            {
                "name": "무결성",
                "value": "\n".join(_integrity_status_lines(integrity_report))[:1024],
                "inline": False,
            }
        )
        liquidity_rows = admission_result.get("liquidity_blocked", []) if isinstance(admission_result, dict) else []
        if liquidity_rows:
            fields.append(
                {
                    "name": "저유동성 차단 후보",
                    "value": _low_liquidity_rows_value(liquidity_rows),
                    "inline": False,
                }
            )
        fields.append(
            {
                "name": "포트폴리오 노출",
                "value": "\n".join(render_portfolio_exposure_lines(exposure_summary))[:1024],
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
    model_label = "스윙 앙상블 (ft_5_5)"
    source_price_kind = "close"
    session_contract = "regular_close"
    finality_contract = "finalized session"
    try:
        from modules.model_lane_scan import model_lane_for

        bucket = model_lane_for(market, "SWING")
        if bucket == "nasdaq_swing_daily_edge":
            model_label = "NASDAQ SWING daily edge shadow"
            source_price_kind = "daily_eod_close"
            session_contract = "manual_eod_latest / nasdaq_regular_close only; cutoff 16:05 America/New_York"
            finality_contract = "latest_eod_panel_scored / finalized_eod_session; non-final sessions blocked"
    except Exception:
        pass
    return {
        "title": f"{market} 검증 모델 스캔",
        "description": (
            f"요청 확인: `{market}` 검증 모델 레인({model_label})을 실행합니다. 결과 티커는 daily_ops 모델 픽과 100% 동일합니다.\n"
            + ("실행 준비 완료 상태입니다." if enabled else "현재는 안전 모드라 실제 실행은 막혀 있습니다.")
        ),
        "color": 0x2ECC71 if enabled else 0xF1C40F,
        "fields": [
            {"name": "Dry Run", "value": str(config.dry_run), "inline": True},
            {"name": "Scan Exec", "value": str(config.enable_scan_execution), "inline": True},
            {"name": "모델", "value": model_label, "inline": True},
            {"name": "Source", "value": source_price_kind, "inline": True},
            {"name": "Session", "value": session_contract, "inline": True},
            {"name": "Finality", "value": finality_contract, "inline": False},
        ],
    }


def build_scan_started_embed(config: DiscordIntegrationConfig, *, job: DiscordScanJob) -> Dict[str, Any]:
    return {
        "title": f"{job.market} 검증 모델 스캔 접수",
        "description": (
            f"Job `{job.job_id}` 검증 모델 레인(스윙 앙상블) 실행을 시작했습니다.\n"
            f"결과 티커는 daily_ops 모델 픽과 100% 동일하며, 완료 시 `/signals` 형식 카드로 표시됩니다."
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
    scan_context = _load_scan_context_for_run(run_id)
    market_gate = scan_context.get("market_gate") if isinstance(scan_context.get("market_gate"), dict) else {}
    scan_summary = scan_context.get("summary") if isinstance(scan_context.get("summary"), dict) else {}
    integrity_report = _scan_integrity_from_summary(scan_summary or summary)
    result_count = _safe_int(summary.get("result_count"), 0)
    warnings = summary.get("warnings") if isinstance(summary.get("warnings"), list) else []
    warning_text = "\n".join(
        f"- {item.get('code')}: {item.get('message')}"
        for item in warnings[:3]
        if isinstance(item, dict)
    )
    gate_msg = str(market_gate.get("msg") or "")
    if result_count == 0 and ok:
        extra = "원본 스캔 통과 후보 0개. 신규 admission 모델 판정과 저유동성 차단 후보는 아래 섹션에서 확인하세요."
        warning_text = f"{warning_text}\n- {extra}" if warning_text and warning_text != "-" else f"- {extra}"
    if not warning_text:
        warning_text = "-"
    fields = [
        {"name": "Run", "value": run_id, "inline": True},
        {"name": "Market", "value": market, "inline": True},
        {"name": "Status", "value": "완료" if ok else f"실패/확인 필요 ({returncode})", "inline": True},
        {"name": "Scanned", "value": str(summary.get("total_scans") or 0), "inline": True},
        {"name": "Passed", "value": str(result_count), "inline": True},
        {"name": "Filtered", "value": str(summary.get("filtered_count") or 0), "inline": True},
    ]
    market_key = str(market or "").upper()
    if market_key in {"KOSPI", "KOSDAQ"}:
        try:
            admission_result = _build_admission_result_for_run(
                run_id,
                market=market_key,
                scan_summary=scan_summary or summary,
                limit=5,
            )
            model_summary = (
                admission_result.get("summary")
                if isinstance(admission_result.get("summary"), dict)
                else admission_model_summary(market_key)
            )
            validation = model_summary.get("validation") if isinstance(model_summary.get("validation"), dict) else {}
            top_deep_rows = [
                row
                for row in _load_top_deep_reports(limit=500, market=market_key, run_id=run_id)
                if str(row.get("run_id") or "") == run_id
                and str(row.get("market") or "").upper() == market_key
            ]
            top_deep_rows = sorted(
                top_deep_rows,
                key=lambda row: -float(
                    (
                        row.get("scan_universe_admission")
                        if isinstance(row.get("scan_universe_admission"), dict)
                        else {}
                    ).get("probability_pct")
                    or 0.0
                ),
            )
            status_payload = (
                admission_result
                if admission_result
                else {
                    "summary": model_summary,
                    "passed": [
                        row
                        for row in top_deep_rows
                        if isinstance(row.get("scan_universe_admission"), dict)
                        and row.get("scan_universe_admission", {}).get("passed")
                    ],
                    "near_miss": [
                        row
                        for row in top_deep_rows
                        if isinstance(row.get("scan_universe_admission"), dict)
                        and not row.get("scan_universe_admission", {}).get("passed")
                    ],
                }
            )
            current_status = admission_run_status(status_payload)
            status_line = current_status.get("message") or "-"
            if current_status.get("best_probability_pct") is not None:
                status_line += (
                    f"\n관찰 1순위: {current_status.get('best_name') or current_status.get('best_ticker') or '-'} "
                    f"({current_status.get('best_ticker') or '-'}) · "
                    f"{metric_label('candidate_top_prob_5d')} {_fmt_num(current_status.get('best_probability_pct'), 1)}% · "
                    f"{metric_label('admission_threshold')} "
                    f"{_fmt_num(current_status.get('threshold_pct'), 1) + '%' if current_status.get('threshold_pct') is not None else (model_summary.get('threshold_label') or '-')}"
                )
            kis_shadow_rows = admission_result.get("kis_shadow", []) if admission_result else []
            if kis_shadow_rows:
                fields.append(
                    {
                        "name": "KIS 쉐도우 후보",
                        "value": _kis_shadow_rows_value(kis_shadow_rows, limit=3),
                        "inline": False,
                    }
                )
            else:
                gate = kis_shadow_gate_status(market_key)
                if gate and not gate.get("shadow_display_allowed"):
                    fields.append(
                        {
                            "name": "KIS 쉐도우 차단",
                            "value": _kis_shadow_gate_block_value(gate),
                            "inline": False,
                        }
                    )
            fields.append(
                {
                    "name": "Admission 모델 기준",
                    "value": (
                        f"모델 {model_summary.get('model_name') or '-'} · 목적 {model_summary.get('objective') or model_summary.get('label') or '-'} · "
                        f"선택규칙 {model_summary.get('selection_rule') or '-'} · "
                        f"통과기준 {model_summary.get('threshold_label') or (str(model_summary.get('prob_threshold_pct')) + '%' if model_summary.get('prob_threshold_pct') is not None else '-')}\n"
                        f"검증 목표터치: label {validation.get('label_win_pct') or '-'}% · "
                        f"hit5 {validation.get('hit5_5d_pct') or '-'}% · hit10 {validation.get('hit10_5d_pct') or '-'}%\n"
                        f"검증 5D고가상승: 평균 {validation.get('avg_max_high_5d_pct') or '-'}% · "
                        f"최저 {validation.get('min_max_high_5d_pct') or '-'}% · 최고 {validation.get('max_max_high_5d_pct') or '-'}% · "
                        f"stop5 {validation.get('stop5_pct') or '-'}% · "
                        f"표본 n={validation.get('n') or '-'}, active days={validation.get('active_days') or '-'}\n"
                        "주의: 검증 터치율/고가상승은 후보 개별 확정 수익이 아니라 이 모델 선택규칙의 과거 표본 성과입니다."
                    )[:1024],
                    "inline": False,
                }
            )
            fields.append({"name": "이번 스캔 판정", "value": status_line[:1024], "inline": False})
            liquidity_rows = admission_result.get("liquidity_blocked", []) if admission_result else []
            if liquidity_rows:
                fields.append(
                    {
                        "name": "저유동성 차단 후보",
                        "value": _low_liquidity_rows_value(liquidity_rows),
                        "inline": False,
                    }
                )
        except Exception as exc:
            fields.append({"name": "Admission 모델 기준", "value": f"모델 요약 로드 실패: {exc}"[:1024], "inline": False})
    if gate_msg:
        fields.append({"name": "Market Gate", "value": gate_msg[:1024], "inline": False})
    fields.append({"name": "Data Integrity", "value": "\n".join(_integrity_status_lines(integrity_report))[:1024], "inline": False})
    fields.extend(
        [
            {"name": "Warnings", "value": warning_text[:1024], "inline": False},
            {"name": "Web", "value": config.web_base_url or "-", "inline": False},
        ]
    )
    log_path = str(job.get("log_path") or "")
    if log_path:
        fields.append({"name": "Log", "value": log_path, "inline": False})

    embeds = [
        {
            "title": f"{market} 전체 스캔 결과",
            "description": (
                f"Job `{job.get('job_id') or '-'}` · 웹/아카이브와 같은 run artifact 기준으로 표시합니다."
            ),
            "color": 0xF1C40F if ok and result_count == 0 else (0x2ECC71 if ok else 0xE74C3C),
            "fields": fields[:14],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]
    if ok:
        embeds.extend(build_top_deep_embeds(run_id=run_id, limit=TOP_DEEP_DISCORD_LIMIT))
    return embeds


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
    "build_next_day_radar_embed",
    "build_top_deep_embeds",
    "collect_run_index",
    "run_id_choices",
]
