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

MARKETS = ("KOSPI", "KOSDAQ")
LOG_DIR = Path("runtime_state/discord_jobs")
KST = ZoneInfo("Asia/Seoul")
DISCORD_MAX_EMBEDS_PER_MESSAGE = 10
DISCORD_MAX_MESSAGE_CHARS = 6000
DISCORD_SAFE_MESSAGE_CHARS = 5400


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
                "description": "KST 09:35 확정 작업: 09:30 이후 국장 수급 확인 구간에서 KOSPI/KOSDAQ 병렬 전체 스윙 스캔을 시작합니다.",
                "color": 0x3498DB,
                "fields": [
                    {"name": "Markets", "value": ", ".join(MARKETS), "inline": True},
                    {"name": "Top Deep", "value": "Shadow + Top5 + Exception Leader", "inline": True},
                    {"name": "Timing Rule", "value": "08:20 prior / 09:30 이후 confirmed scan", "inline": False},
                    {"name": "Started", "value": started_at, "inline": False},
                ],
                "timestamp": started_at,
            }
        ],
    )

    summaries = await asyncio.gather(*[_run_market_scan(market) for market in MARKETS])
    _refresh_archive_dataset()
    performance_payload = _record_section_performance()

    result_embeds: List[Dict[str, Any]] = [
        {
            "title": "KR 자동 스캔 완료",
            "description": "KOSPI/KOSDAQ 병렬 스캔 완료. 아래 결과는 웹/아카이브와 같은 run artifact 기준입니다.",
            "color": 0x2ECC71 if all(_summary_ok(item) for item in summaries) else 0xE67E22,
            "fields": [
                {
                    "name": str(item.get("market") or item.get("discord_job", {}).get("market") or "-"),
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
    ]
    for summary in summaries:
        result_embeds.extend(build_scan_result_embeds(summary, config=config))
    await _post_embeds(config, result_embeds)

    print(json.dumps({"summaries": summaries, "performance": performance_payload}, ensure_ascii=False, indent=2))
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


async def _run_market_scan(market: str) -> Dict[str, Any]:
    job = create_scan_job(market)
    lock = DiscordScanLock()
    if not lock.try_acquire(job_id=job.job_id, market=job.market):
        return {
            "market": market,
            "warnings": [{"code": "SCAN_LOCK_BUSY", "message": f"{market} scan lock is busy"}],
            "discord_job": {
                "job_id": job.job_id,
                "market": market,
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


def _refresh_archive_dataset() -> None:
    cmd = [
        sys.executable,
        "multi_agent/tools/export_scan_archive_learning_dataset.py",
        "--market",
        "ALL",
        "--scan-mode",
        "SWING",
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
        "fields": fields[:10]
        + [{"name": "Local Records", "value": "\n".join(str(v) for v in paths.values())[:1024] or "-", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    for chunk in _chunk_embeds_for_discord(embeds):
        try:
            await asyncio.to_thread(_post_embed_chunk, config, chunk)
        except Exception as exc:
            print(f"[WARN] Discord channel post failed: {exc}", file=sys.stderr)


def _post_embed_chunk(config: DiscordIntegrationConfig, embeds: List[Dict[str, Any]]) -> None:
    body = json.dumps({"embeds": embeds}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{config.result_channel_id}/messages",
        data=body,
        headers={
            "Authorization": f"Bot {config.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "CodexSwingDailyAutoScan/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _chunk_embeds_for_discord(embeds: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_chars = 0
    for embed in embeds or []:
        embed_chars = _discord_embed_char_count(embed)
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
