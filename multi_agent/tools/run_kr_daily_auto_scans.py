#!/usr/bin/env python3
"""Daily KOSPI/KOSDAQ background scan runner.

Runs both KR swing scans in parallel through the same non-UI pipeline used by
Discord commands, records section performance snapshots, and posts the result
to the configured Discord result channel.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.config import DiscordIntegrationConfig, load_discord_config
from modules.discord_integration.renderers import build_scan_result_embeds
from modules.discord_integration.scan_executor import DiscordScanLock, create_scan_job, run_scan_job
from modules.signal_section_performance import (
    build_latest_performance_markdown,
    build_section_performance_metrics,
    load_archive_rows,
    write_daily_section_performance_snapshot,
)

MARKETS = ("KOSPI", "KOSDAQ")
LOG_DIR = Path("runtime_state/discord_jobs")


async def main_async() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_discord_config(load_env=True)
    started_at = datetime.now(timezone.utc).isoformat()
    await _post_embeds(
        config,
        [
            {
                "title": "KR 자동 스캔 시작",
                "description": "KST 08:20 자동 작업: KOSPI/KOSDAQ 병렬 전체 스윙 스캔을 시작합니다.",
                "color": 0x3498DB,
                "fields": [
                    {"name": "Markets", "value": ", ".join(MARKETS), "inline": True},
                    {"name": "Top Deep", "value": "Shadow + Top5 + Exception Leader", "inline": True},
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


async def _post_embeds(config: DiscordIntegrationConfig, embeds: List[Dict[str, Any]]) -> None:
    if config.dry_run:
        print("[INFO] Discord dry-run is enabled; skipping channel post.")
        return
    if not config.bot_token or not config.result_channel_id:
        print("[WARN] Discord token/channel missing; skipping channel post.", file=sys.stderr)
        return
    for idx in range(0, len(embeds), 10):
        try:
            await asyncio.to_thread(_post_embed_chunk, config, embeds[idx : idx + 10])
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
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def _summary_ok(summary: Dict[str, Any]) -> bool:
    job = summary.get("discord_job") if isinstance(summary.get("discord_job"), dict) else {}
    return bool(summary.get("run_id")) and int(job.get("returncode") if job.get("returncode") is not None else 1) == 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
