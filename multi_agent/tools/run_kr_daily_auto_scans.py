#!/usr/bin/env python3
"""Daily KOSPI/KOSDAQ background scan runner.

The 08:20 KST phase publishes only pre-market theme priors. The post-09:30
phase runs both KR swing scans in parallel through the same non-UI pipeline
used by Discord commands, records section performance snapshots, and posts the
result to the configured Discord result channel.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time as time_module
import urllib.error
import urllib.request
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.config import DiscordIntegrationConfig, load_discord_config
from modules.discord_integration.renderers import build_scan_result_embeds
from modules.discord_integration.scan_executor import DiscordScanLock, create_scan_job, run_scan_job
from modules.kr_premarket_theme_prior import build_premarket_theme_prior, write_premarket_theme_prior
from modules.macro_scheduler import get_macro_context
from modules.signal_section_performance import (
    build_latest_performance_markdown,
    build_section_performance_metrics,
    load_archive_rows,
    write_daily_section_performance_snapshot,
)

DEFAULT_SCAN_TARGETS = (
    ("KOSPI", "SWING"),
    ("KOSDAQ", "SWING"),
    ("KOSPI", "INTRADAY"),
    ("KOSDAQ", "INTRADAY"),
)
LOG_DIR = Path("runtime_state/discord_jobs")
KST = ZoneInfo("Asia/Seoul")
DISCORD_MAX_EMBEDS_PER_MESSAGE = 10
DISCORD_MAX_MESSAGE_CHARS = 6000
DISCORD_SAFE_MESSAGE_CHARS = 4800
DISCORD_MAX_EMBED_FIELDS = 25
DISCORD_MAX_EMBED_TITLE_CHARS = 256
DISCORD_MAX_EMBED_DESCRIPTION_CHARS = 4096
DISCORD_MAX_EMBED_FIELD_NAME_CHARS = 256
DISCORD_MAX_EMBED_FIELD_VALUE_CHARS = 1024
DISCORD_MAX_CONTENT_CHARS = 2000
DISCORD_INTER_MESSAGE_PAUSE_SECONDS = 1.1
DISCORD_MIN_RETRY_AFTER_SECONDS = 1.0
POST_SCAN_VALIDATION_COMMANDS = (
    {
        "name": "Scan Cohort Performance",
        "command": [sys.executable, "multi_agent/tools/report_scan_cohort_performance.py"],
        "md_path": "runtime_state/reports/validation/scan_cohort_performance.md",
        "json_path": "runtime_state/reports/validation/scan_cohort_performance.json",
    },
    {
        "name": "Segment Top1 Validation",
        "command": [sys.executable, "multi_agent/tools/report_segment_topn_validation.py", "--topn", "1"],
        "md_path": "runtime_state/reports/validation/segment_top1_validation.md",
        "json_path": "runtime_state/reports/validation/segment_top1_validation.json",
    },
    {
        "name": "Segment Top5 Validation",
        "command": [sys.executable, "multi_agent/tools/report_segment_topn_validation.py", "--topn", "5"],
        "md_path": "runtime_state/reports/validation/segment_top5_validation.md",
        "json_path": "runtime_state/reports/validation/segment_top5_validation.json",
    },
    {
        "name": "Loss Exclusion Guard Watch",
        "command": [
            sys.executable,
            "multi_agent/tools/mine_loss_exclusion_guards.py",
            "--stem",
            "loss_exclusion_guard_watch_latest",
            "--markets",
            "KOSDAQ",
            "--scopes",
            "exception_leader",
            "--horizons",
            "3d,5d",
            "--beam-width",
            "16",
            "--max-terms",
            "2",
            "--min-excluded",
            "8",
            "--min-retention",
            "0.35",
        ],
        "md_path": "runtime_state/reports/experimental/loss_exclusion_guard_watch_latest.md",
        "json_path": "runtime_state/reports/experimental/loss_exclusion_guard_watch_latest.json",
    },
    {
        "name": "Ordered Shadow Watch",
        "command": [
            sys.executable,
            "multi_agent/tools/report_ordered_shadow_watch.py",
        ],
        "md_path": "runtime_state/reports/experimental/ordered_shadow_watch_latest.md",
        "json_path": "runtime_state/reports/experimental/ordered_shadow_watch_latest.json",
    },
    {
        "name": "INTRADAY Learning Readiness",
        "command": [
            sys.executable,
            "multi_agent/tools/report_intraday_learning_readiness.py",
        ],
        "md_path": "runtime_state/reports/validation/intraday_learning_readiness.md",
        "json_path": "runtime_state/reports/validation/intraday_learning_readiness.json",
    },
)


async def main_async(*, phase: str = "confirmed", allow_before_confirm_window: bool = False) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_discord_config(load_env=True)
    phase_key = str(phase or "confirmed").strip().lower()
    if phase_key == "premarket":
        return await _run_premarket_theme_prior(config)
    if phase_key not in {"confirmed", "scan"}:
        print(f"[ERROR] unknown phase: {phase}", file=sys.stderr)
        return 2
    if not allow_before_confirm_window and _before_confirm_window():
        await _post_embeds(
            config,
            [
                {
                    "title": "KR 확정 스캔 보류",
                    "description": "확정 스캔은 KST 09:30 이후에만 실행합니다. 08:20 작업은 개장 전 테마 prior만 생성해야 합니다.",
                    "color": 0xF1C40F,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        return 75
    started_at = datetime.now(timezone.utc).isoformat()
    await _post_embeds(
        config,
        [
            {
                "title": "KR 자동 스캔 시작",
                "description": "KST 09:35 확정 작업: 09:30 이후 국장 수급 확인 구간에서 KOSPI/KOSDAQ 스윙 및 장중 스캔을 병렬 실행합니다.",
                "color": 0x3498DB,
                "fields": [
                    {"name": "Targets", "value": ", ".join(f"{m}/{mode}" for m, mode in _scan_targets()), "inline": True},
                    {"name": "Top Deep", "value": "Shadow + Top5 + Exception Leader", "inline": True},
                    {"name": "Timing Rule", "value": "08:20 prior / 09:30 이후 confirmed scan", "inline": False},
                    {"name": "Started", "value": started_at, "inline": False},
                ],
                "timestamp": started_at,
            }
        ],
    )

    scan_targets = _scan_targets()
    summaries = await asyncio.gather(*[_run_market_scan(market, scan_mode) for market, scan_mode in scan_targets])
    _refresh_archive_dataset()
    performance_payload = _record_section_performance()
    validation_payload = _record_post_scan_validation()

    result_embeds: List[Dict[str, Any]] = [
        {
            "title": "KR 자동 스캔 완료",
            "description": "KOSPI/KOSDAQ 병렬 스캔 완료. 아래 결과는 웹/아카이브와 같은 run artifact 기준입니다.",
            "color": 0x2ECC71 if all(_summary_ok(item) for item in summaries) else 0xE67E22,
            "fields": [
                {
                    "name": _summary_target_label(item),
                    "value": (
                        f"Run `{item.get('run_id') or '-'}` · "
                        f"scan {item.get('total_scans') or 0} · pass {item.get('result_count') or 0} · "
                        f"status {'OK' if _summary_ok(item) else '확인 필요'}"
                    )[:1024],
                    "inline": False,
                }
                for item in summaries
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        _performance_embed(performance_payload),
        _validation_embed(validation_payload),
    ]
    for summary in summaries:
        result_embeds.extend(build_scan_result_embeds(summary, config=config))
    await _post_embeds(config, result_embeds)

    print(
        json.dumps(
            {"summaries": summaries, "performance": performance_payload, "validation": validation_payload},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(_summary_ok(item) for item in summaries) else 1


async def _run_premarket_theme_prior(config: DiscordIntegrationConfig) -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    macro_ctx = await asyncio.to_thread(get_macro_context, True, "KR")
    payload = build_premarket_theme_prior(macro_ctx)
    paths = write_premarket_theme_prior(payload)
    payload["paths"] = paths
    await _post_embeds(config, [_premarket_theme_prior_embed(payload)])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _scan_targets() -> List[tuple[str, str]]:
    raw = os.getenv("AG_KR_DAILY_SCAN_TARGETS", "")
    if not raw.strip():
        return list(DEFAULT_SCAN_TARGETS)
    targets: List[tuple[str, str]] = []
    for token in raw.split(","):
        text = token.strip()
        if not text:
            continue
        if ":" in text:
            market, mode = text.split(":", 1)
        elif "/" in text:
            market, mode = text.split("/", 1)
        else:
            market, mode = text, "SWING"
        market_key = market.strip().upper()
        mode_key = mode.strip().upper() or "SWING"
        if market_key in {"KOSPI", "KOSDAQ"} and mode_key in {"SWING", "INTRADAY"} and (market_key, mode_key) not in targets:
            targets.append((market_key, mode_key))
    return targets or list(DEFAULT_SCAN_TARGETS)


async def _run_market_scan(market: str, scan_mode: str = "SWING") -> Dict[str, Any]:
    job = create_scan_job(market, scan_mode=scan_mode)
    lock = DiscordScanLock()
    if not lock.try_acquire(job_id=job.job_id, market=job.market, scan_mode=job.scan_mode):
        return {
            "market": market,
            "scan_mode": job.scan_mode,
            "warnings": [{"code": "SCAN_LOCK_BUSY", "message": f"{market}/{job.scan_mode} scan lock is busy"}],
            "discord_job": {
                "job_id": job.job_id,
                "market": market,
                "scan_mode": job.scan_mode,
                "returncode": 75,
                "log_path": str(job.log_path),
                "started_at": job.started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    try:
        return await run_scan_job(job)
    finally:
        lock.release()


def _summary_target_label(summary: Dict[str, Any]) -> str:
    job = summary.get("discord_job") if isinstance(summary.get("discord_job"), dict) else {}
    market = str(summary.get("market") or job.get("market") or "-")
    scan_mode = str(summary.get("scan_mode") or job.get("scan_mode") or "SWING")
    return f"{market}/{scan_mode}"


def _refresh_archive_dataset() -> None:
    cmd = [
        sys.executable,
        "multi_agent/tools/export_scan_archive_learning_dataset.py",
        "--market",
        "ALL",
        "--scan-mode",
        "ALL",
    ]
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, check=False, timeout=900)
    except Exception as exc:
        print(f"[WARN] archive dataset refresh failed: {exc}", file=sys.stderr)


def _record_section_performance() -> Dict[str, Any]:
    rows = load_archive_rows()
    metrics = build_section_performance_metrics(rows)
    paths = write_daily_section_performance_snapshot(metrics)
    return {"metrics": metrics, "paths": paths, "markdown": build_latest_performance_markdown(metrics)}


def _record_post_scan_validation() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    for spec in POST_SCAN_VALIDATION_COMMANDS:
        started_at = datetime.now(timezone.utc).isoformat()
        item: Dict[str, Any] = {
            "name": spec["name"],
            "started_at": started_at,
            "command": list(spec["command"]),
            "json_path": spec.get("json_path"),
            "md_path": spec.get("md_path"),
        }
        try:
            completed = subprocess.run(
                list(spec["command"]),
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=900,
            )
            item["returncode"] = int(completed.returncode)
            item["ok"] = completed.returncode == 0
            item["stdout_tail"] = (completed.stdout or "")[-2000:]
            item["stderr_tail"] = (completed.stderr or "")[-2000:]
            parsed = _parse_last_json_line(completed.stdout or "")
            if parsed:
                item.update({key: value for key, value in parsed.items() if key in {"json", "md", "json_path", "md_path", "prepared_rows", "segments"}})
        except Exception as exc:
            item["ok"] = False
            item["returncode"] = -1
            item["error"] = str(exc)
        md_path = PROJECT_ROOT / str(item.get("md") or item.get("md_path") or "")
        item["summary"] = _markdown_validation_excerpt(md_path)
        if not item.get("ok") and item["summary"]:
            item["degraded"] = True
            item["warning"] = "command_failed_existing_markdown_summary_used"
        item["finished_at"] = datetime.now(timezone.utc).isoformat()
        results.append(item)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": all(bool(item.get("ok") or item.get("degraded")) for item in results),
        "degraded": any(bool(item.get("degraded")) for item in results),
        "results": results,
    }


def _parse_last_json_line(text: str) -> Dict[str, Any]:
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    raw = text or ""
    for idx in [pos for pos, char in enumerate(raw) if char == "{"][::-1]:
        try:
            payload = json.loads(raw[idx:].strip())
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _markdown_validation_excerpt(path: Path, *, max_lines: int = 10) -> str:
    try:
        if not path.exists():
            return ""
        lines: List[str] = []
        in_definitions = False
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            if line == "## Definitions":
                in_definitions = True
                continue
            if line.startswith("## ") and line != "## Definitions":
                in_definitions = False
            if in_definitions:
                continue
            if line.startswith("#"):
                continue
            if line.startswith("|---"):
                continue
            if line.startswith("| Cohort") or line.startswith("| Level"):
                continue
            if any(
                token in line.lower()
                for token in (
                    "kospi",
                    "kosdaq",
                    "top1",
                    "top5",
                    "exception",
                    "positive-rate",
                    "avg return",
                    "worst/best",
                    "min/max",
                    "practical",
                    "clean",
                    "bad",
                    "guard",
                    "shadow",
                    "production",
                    "retain",
                    "win_delta",
                )
            ):
                lines.append(line)
            if len(lines) >= max_lines:
                break
        return "\n".join(lines)[:1800]
    except Exception as exc:
        return f"summary read failed: {exc}"


def _performance_embed(payload: Dict[str, Any]) -> Dict[str, Any]:
    markdown = str(payload.get("markdown") or "").strip()
    fields = []
    current_market = ""
    for line in markdown.splitlines():
        if line.startswith("## "):
            current_market = line.replace("## ", "").strip()
        elif line.startswith("- ") and current_market:
            section, _, value = line[2:].partition(":")
            fields.append({"name": f"{current_market} {section}", "value": value.strip()[:1024] or "-", "inline": False})
    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
    return {
        "title": "섹션별 성과 기록",
        "description": "Shadow / Top5 / Exception Leader 1D·3D·5D 승률과 평균수익률 스냅샷",
        "color": 0x1ABC9C,
        "fields": fields[:24]
        + [{"name": "Local Records", "value": "\n".join(str(v) for v in paths.values())[:1024] or "-", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _validation_embed(payload: Dict[str, Any]) -> Dict[str, Any]:
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    fields: List[Dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        status = "OK" if item.get("ok") else "DEGRADED" if item.get("degraded") else "FAIL"
        value_parts = [
            f"status `{status}` · rc `{item.get('returncode')}`",
            f"json `{item.get('json') or item.get('json_path') or '-'}`",
            f"md `{item.get('md') or item.get('md_path') or '-'}`",
        ]
        if item.get("warning"):
            value_parts.append(f"warning `{item.get('warning')}`")
        summary = str(item.get("summary") or "").strip()
        if summary:
            value_parts.append(summary)
        elif item.get("stderr_tail"):
            value_parts.append(str(item.get("stderr_tail"))[:800])
        fields.append({"name": str(item.get("name") or "Post Scan Validation")[:256], "value": "\n".join(value_parts)[:1024], "inline": False})
    return {
        "title": "스캔 후 자동 검증",
        "description": "Top1/Top5/Shadow/Exception 성능 리포트 갱신 결과입니다. 승률·평균·손실꼬리 확인용입니다.",
        "color": 0xF1C40F if payload.get("degraded") else 0x2ECC71 if payload.get("ok") else 0xE67E22,
        "fields": fields[:10] or [{"name": "Status", "value": "검증 결과 없음", "inline": False}],
        "timestamp": payload.get("generated_at") or datetime.now(timezone.utc).isoformat(),
    }


def _premarket_theme_prior_embed(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    priors = payload.get("kr_theme_priors") if isinstance(payload.get("kr_theme_priors"), list) else []
    fields: List[Dict[str, Any]] = [
        {
            "name": "주의",
            "value": "개장 전 테마 prior입니다. 매수 후보가 아니며 09:30 이후 확정 스캔으로 검증해야 합니다.",
            "inline": False,
        },
        {
            "name": "Market Lead",
            "value": (
                f"macro {source.get('macro_state') or '-'} · risk {source.get('macro_risk_score') or '-'} · "
                f"US lead {source.get('us_lead_state') or '-'} / {source.get('us_lead_score') or '-'}"
            )[:1024],
            "inline": False,
        },
    ]
    if priors:
        lines = []
        for idx, row in enumerate(priors[:10], start=1):
            direction = str(row.get("direction") or "-")
            arrow = "상방" if direction == "BENEFICIARY" else "역풍" if direction == "HEADWIND" else "중립"
            lines.append(f"{idx}. {row.get('theme_id') or '-'} · {arrow} · strength {row.get('strength_score') or 0}")
        fields.append({"name": "예상 테마 Prior", "value": "\n".join(lines)[:1024], "inline": False})
    else:
        fields.append({"name": "예상 테마 Prior", "value": "유의미한 개장 전 테마 prior 없음", "inline": False})
    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}
    if paths:
        fields.append({"name": "Local Artifact", "value": str(paths.get("latest") or "-")[:1024], "inline": False})
    return {
        "title": "KR 개장 전 테마 Prior",
        "description": f"08:20 준비 작업 · 09:30 이후 확정 스캔 전까지는 관찰 전용입니다. confirm_after={payload.get('confirm_after_kst') or '09:30'} KST",
        "color": 0x95A5A6,
        "fields": fields[:10],
        "timestamp": payload.get("generated_at") or datetime.now(timezone.utc).isoformat(),
    }


async def _post_embeds(config: DiscordIntegrationConfig, embeds: List[Dict[str, Any]]) -> None:
    if config.dry_run:
        print("[INFO] Discord dry-run is enabled; skipping channel post.")
        return
    if not config.bot_token or not config.result_channel_id:
        print("[WARN] Discord token/channel missing; skipping channel post.", file=sys.stderr)
        return
    safe_embeds = _prepare_embeds_for_discord(embeds)
    for idx, chunk in enumerate(_chunk_embeds_for_discord(safe_embeds)):
        if idx > 0:
            await asyncio.sleep(DISCORD_INTER_MESSAGE_PAUSE_SECONDS)
        try:
            await asyncio.to_thread(_post_embed_chunk, config, chunk)
        except Exception as exc:
            print(f"[WARN] Discord embed chunk post failed: {exc}", file=sys.stderr)
            await _post_embed_chunk_fallback(config, chunk)


def _post_embed_chunk(config: DiscordIntegrationConfig, embeds: List[Dict[str, Any]]) -> None:
    _post_discord_message(config, {"embeds": embeds})


async def _post_embed_chunk_fallback(config: DiscordIntegrationConfig, embeds: List[Dict[str, Any]]) -> None:
    for embed_idx, embed in enumerate(embeds or []):
        if embed_idx > 0:
            await asyncio.sleep(DISCORD_INTER_MESSAGE_PAUSE_SECONDS)
        try:
            await asyncio.to_thread(_post_embed_chunk, config, [embed])
            continue
        except Exception as exc:
            print(f"[WARN] Discord single embed post failed; falling back to text: {exc}", file=sys.stderr)
        for content_idx, content in enumerate(_embed_to_content_chunks(embed)):
            if content_idx > 0:
                await asyncio.sleep(DISCORD_INTER_MESSAGE_PAUSE_SECONDS)
            try:
                await asyncio.to_thread(_post_discord_content, config, content)
            except Exception as exc:
                print(f"[WARN] Discord text fallback failed: {exc}", file=sys.stderr)


def _post_discord_content(config: DiscordIntegrationConfig, content: str) -> None:
    _post_discord_message(config, {"content": _clip_text(content, DISCORD_MAX_CONTENT_CHARS)})


def _post_discord_message(config: DiscordIntegrationConfig, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = f"https://discord.com/api/v10/channels/{config.result_channel_id}/messages"
    headers = {
        "Authorization": f"Bot {config.bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "CodexSwingDailyAutoScan/1.0",
    }
    last_detail = ""
    for attempt in range(5):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
                return
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            last_detail = detail
            retry_after = _discord_retry_after(exc, detail)
            if exc.code == 429 and attempt < 4:
                time_module.sleep(_discord_backoff_seconds(retry_after, attempt))
                continue
            if 500 <= exc.code < 600 and attempt < 4:
                time_module.sleep(min(5.0, 0.5 * (attempt + 1)))
                continue
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    raise RuntimeError(f"Discord post failed after retries: {last_detail}")


def _discord_retry_after(exc: urllib.error.HTTPError, detail: str) -> float:
    header_value = exc.headers.get("Retry-After") if exc.headers else None
    try:
        if header_value is not None:
            return float(header_value)
    except Exception:
        pass
    try:
        payload = json.loads(detail)
        return float(payload.get("retry_after") or 0.0)
    except Exception:
        return 0.0


def _discord_backoff_seconds(retry_after: float, attempt: int) -> float:
    return max(DISCORD_MIN_RETRY_AFTER_SECONDS, float(retry_after or 0.0)) + 0.5 + min(2.0, 0.25 * max(0, attempt))


def _chunk_embeds_for_discord(embeds: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_chars = 0
    for embed in embeds or []:
        embed_chars = _discord_embed_char_count(embed)
        if embed_chars > DISCORD_SAFE_MESSAGE_CHARS:
            for split_embed in _split_embed_for_discord(embed):
                chunks.extend(_chunk_embeds_for_discord([split_embed]))
            continue
        if current and (
            len(current) >= DISCORD_MAX_EMBEDS_PER_MESSAGE
            or current_chars + embed_chars > DISCORD_SAFE_MESSAGE_CHARS
        ):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(embed)
        current_chars += embed_chars
    if current:
        chunks.append(current)
    return chunks


def _prepare_embeds_for_discord(embeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    safe: List[Dict[str, Any]] = []
    for embed in embeds or []:
        safe.extend(_split_embed_for_discord(embed))
    return safe


def _split_embed_for_discord(embed: Dict[str, Any]) -> List[Dict[str, Any]]:
    base = _embed_base_for_discord(embed)
    base_chars = _discord_embed_char_count({**base, "fields": []})
    if base_chars > DISCORD_SAFE_MESSAGE_CHARS:
        non_desc_chars = base_chars - len(str(base.get("description") or ""))
        available_desc = max(0, DISCORD_SAFE_MESSAGE_CHARS - non_desc_chars)
        base["description"] = _clip_text(base.get("description"), available_desc)

    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    normalized_fields = [_field_for_discord(field) for field in fields if isinstance(field, dict)]
    if not normalized_fields:
        return [{**base, "fields": []}]

    pages: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []
    for field in normalized_fields:
        candidate_fields = current + [field]
        candidate = {**base, "fields": candidate_fields}
        if current and (
            len(candidate_fields) > DISCORD_MAX_EMBED_FIELDS
            or _discord_embed_char_count(candidate) > DISCORD_SAFE_MESSAGE_CHARS
        ):
            pages.append({**base, "fields": current})
            current = []
        current.append(_fit_single_field(base, field))
    if current:
        pages.append({**base, "fields": current[:DISCORD_MAX_EMBED_FIELDS]})
    return pages


def _embed_base_for_discord(embed: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(embed)
    safe["title"] = _clip_text(safe.get("title"), DISCORD_MAX_EMBED_TITLE_CHARS)
    safe["description"] = _clip_text(safe.get("description"), DISCORD_MAX_EMBED_DESCRIPTION_CHARS)
    footer = safe.get("footer") if isinstance(safe.get("footer"), dict) else None
    if footer:
        safe["footer"] = {**footer, "text": _clip_text(footer.get("text"), 2048)}
    author = safe.get("author") if isinstance(safe.get("author"), dict) else None
    if author:
        safe["author"] = {**author, "name": _clip_text(author.get("name"), 256)}
    safe.pop("fields", None)
    return safe


def _field_for_discord(field: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": _clip_text(field.get("name"), DISCORD_MAX_EMBED_FIELD_NAME_CHARS) or "-",
        "value": _clip_text(field.get("value"), DISCORD_MAX_EMBED_FIELD_VALUE_CHARS) or "-",
        "inline": bool(field.get("inline", False)),
    }


def _fit_single_field(base: Dict[str, Any], field: Dict[str, Any]) -> Dict[str, Any]:
    candidate = {**base, "fields": [field]}
    if _discord_embed_char_count(candidate) <= DISCORD_SAFE_MESSAGE_CHARS:
        return field
    base_chars = _discord_embed_char_count({**base, "fields": []})
    name_len = len(str(field.get("name") or ""))
    available = max(1, DISCORD_SAFE_MESSAGE_CHARS - base_chars - name_len)
    clipped = dict(field)
    clipped["value"] = _clip_text(clipped.get("value"), min(DISCORD_MAX_EMBED_FIELD_VALUE_CHARS, available))
    return clipped


def _embed_to_content_chunks(embed: Dict[str, Any]) -> List[str]:
    title = str(embed.get("title") or "Discord embed fallback")
    description = str(embed.get("description") or "").strip()
    lines = [f"**{title}**"]
    if description:
        lines.append(description)
    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "-").strip() or "-"
        value = str(field.get("value") or "-").strip() or "-"
        lines.append(f"{name}: {value}")
    text = "\n".join(lines)
    chunks: List[str] = []
    while text:
        chunks.append(_clip_text(text, DISCORD_MAX_CONTENT_CHARS))
        if len(text) <= DISCORD_MAX_CONTENT_CHARS:
            break
        text = text[DISCORD_MAX_CONTENT_CHARS - 1 :].lstrip()
    return chunks or ["자동 스캔 결과 요약을 생성하지 못했습니다."]


def _clip_text(value: Any, limit: int) -> str:
    text = str(value or "")
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1] + "…"


def _discord_embed_char_count(embed: Dict[str, Any]) -> int:
    total = len(str(embed.get("title") or "")) + len(str(embed.get("description") or ""))
    footer = embed.get("footer") if isinstance(embed.get("footer"), dict) else {}
    author = embed.get("author") if isinstance(embed.get("author"), dict) else {}
    total += len(str(footer.get("text") or "")) + len(str(author.get("name") or ""))
    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    for field in fields:
        if isinstance(field, dict):
            total += len(str(field.get("name") or "")) + len(str(field.get("value") or ""))
    return total


def _summary_ok(summary: Dict[str, Any]) -> bool:
    job = summary.get("discord_job") if isinstance(summary.get("discord_job"), dict) else {}
    return bool(summary.get("run_id")) and int(job.get("returncode") if job.get("returncode") is not None else 1) == 0


def _before_confirm_window(now: datetime | None = None) -> bool:
    kst_now = (now or datetime.now(timezone.utc)).astimezone(KST)
    return kst_now.time() < time(9, 30)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["premarket", "confirmed", "scan"], default=os.getenv("AG_KR_DAILY_PHASE", "confirmed"))
    parser.add_argument("--allow-before-confirm-window", action="store_true")
    args = parser.parse_args()
    return asyncio.run(main_async(phase=args.phase, allow_before_confirm_window=args.allow_before_confirm_window))


if __name__ == "__main__":
    raise SystemExit(main())
