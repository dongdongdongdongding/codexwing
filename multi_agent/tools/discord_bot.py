#!/usr/bin/env python3
"""Discord bot entrypoint for remote scanner control."""
from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.config import load_discord_config
from modules.discord_integration.permissions import is_authorized_user
from modules.discord_integration.renderers import (
    build_archive_embed,
    build_macro_refresh_embed,
    build_runs_embed,
    build_scan_ack_embed,
    build_scan_busy_embed,
    build_scan_result_embeds,
    build_scan_started_embed,
    build_status_embed,
    build_top_deep_embeds,
    run_id_choices,
)
from modules.discord_integration.scan_executor import (
    DiscordScanLock,
    create_scan_job,
    run_scan_job,
)


def _embed(discord_module, payload):
    return discord_module.Embed.from_dict(payload)


def _role_ids(interaction) -> Iterable[str]:
    roles = getattr(getattr(interaction, "user", None), "roles", []) or []
    return [str(getattr(role, "id", "")) for role in roles if getattr(role, "id", None)]


async def _send_embed_chunks(discord_module, target, payloads):
    embeds = [_embed(discord_module, payload) for payload in payloads]
    for idx in range(0, len(embeds), 10):
        await target.send(embeds=embeds[idx : idx + 10])


async def _send_followup_chunks(discord_module, interaction, payloads):
    embeds = [_embed(discord_module, payload) for payload in payloads]
    for idx in range(0, len(embeds), 10):
        await interaction.followup.send(embeds=embeds[idx : idx + 10], ephemeral=True)


def main() -> int:
    try:
        import discord
        from discord import app_commands
    except Exception as exc:
        raise SystemExit(
            "discord.py is required. Install with: python3 -m pip install 'discord.py>=2.4'"
        ) from exc

    config = load_discord_config(load_env=True)
    validation = config.validate()
    if not validation["ok"]:
        raise SystemExit(f"Invalid Discord config: {validation['errors']}")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    async def _result_channel():
        if not config.result_channel_id:
            return None
        channel_id = int(config.result_channel_id)
        channel = client.get_channel(channel_id)
        if channel is not None:
            return channel
        return await client.fetch_channel(channel_id)

    async def _guard(interaction) -> bool:
        user_id = str(getattr(getattr(interaction, "user", None), "id", "") or "")
        if is_authorized_user(config, user_id=user_id, role_ids=_role_ids(interaction)):
            return True
        await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
        return False

    async def _run_id_autocomplete(interaction, current: str):
        namespace = getattr(interaction, "namespace", None)
        market = str(getattr(namespace, "market", "") or "")
        return [
            app_commands.Choice(name=run_id, value=run_id)
            for run_id in run_id_choices(current=current, market=market, limit=25)
        ]

    @client.event
    async def on_ready():
        print(f"Discord bot ready as {client.user} (dry_run={config.dry_run})")

    @tree.command(name="status", description="Discord 연동 설정, 최근 Run, 서버 상태를 확인합니다.")
    async def status(interaction):
        if not await _guard(interaction):
            return
        await interaction.response.send_message(embed=_embed(discord, build_status_embed(config)), ephemeral=True)

    @tree.command(name="top_deep", description="최근 자동 정밀분석 이력과 종목별 상세 매수 판단을 조회합니다.")
    @app_commands.describe(
        market="시장 필터",
        ticker="선택 종목 티커 예: 005930.KS",
        run_id="선택 Run ID. 입력 중 자동완성됩니다.",
        offset="결과 시작 위치",
        limit="표시 개수",
    )
    @app_commands.choices(
        market=[
            app_commands.Choice(name="KOSPI", value="KOSPI"),
            app_commands.Choice(name="KOSDAQ", value="KOSDAQ"),
        ]
    )
    @app_commands.autocomplete(run_id=_run_id_autocomplete)
    async def top_deep(
        interaction,
        market: str = "",
        ticker: str = "",
        run_id: str = "",
        offset: int = 0,
        limit: int = 10,
    ):
        if not await _guard(interaction):
            return
        embeds = [
            _embed(discord, payload)
            for payload in build_top_deep_embeds(
                market=market,
                ticker=ticker,
                run_id=run_id,
                offset=offset,
                limit=limit,
            )
        ]
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)

    @tree.command(name="archive", description="최근 스캔 아카이브와 realized outcome 상태를 조회합니다.")
    @app_commands.describe(
        market="시장 필터",
        ticker="선택 종목 티커 예: 005930.KS",
        run_id="선택 Run ID. 입력 중 자동완성됩니다.",
        offset="결과 시작 위치",
        limit="표시 개수",
    )
    @app_commands.choices(
        market=[
            app_commands.Choice(name="KOSPI", value="KOSPI"),
            app_commands.Choice(name="KOSDAQ", value="KOSDAQ"),
        ]
    )
    @app_commands.autocomplete(run_id=_run_id_autocomplete)
    async def archive(
        interaction,
        market: str = "",
        ticker: str = "",
        run_id: str = "",
        offset: int = 0,
        limit: int = 10,
    ):
        if not await _guard(interaction):
            return
        payload = build_archive_embed(market=market, ticker=ticker, run_id=run_id, offset=offset, limit=limit)
        await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)

    @tree.command(name="runs", description="누적된 스캔 Run 목록을 조회하고 run_id를 선택할 수 있게 표시합니다.")
    @app_commands.describe(market="시장 필터", offset="목록 시작 위치", limit="표시 개수")
    @app_commands.choices(
        market=[
            app_commands.Choice(name="KOSPI", value="KOSPI"),
            app_commands.Choice(name="KOSDAQ", value="KOSDAQ"),
        ]
    )
    async def runs(interaction, market: str = "", offset: int = 0, limit: int = 10):
        if not await _guard(interaction):
            return
        payload = build_runs_embed(market=market, offset=offset, limit=limit)
        await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)

    @tree.command(name="kospi_scan", description="KOSPI 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.")
    async def kospi_scan(interaction):
        if not await _guard(interaction):
            return
        await _handle_scan(interaction, "KOSPI")

    @tree.command(name="kosdaq_scan", description="KOSDAQ 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.")
    async def kosdaq_scan(interaction):
        if not await _guard(interaction):
            return
        await _handle_scan(interaction, "KOSDAQ")

    @tree.command(name="macro_refresh", description="매크로/마켓 게이트 컨텍스트를 새로고침하고 요약을 표시합니다.")
    async def macro_refresh(interaction):
        if not await _guard(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        payload = await asyncio.to_thread(build_macro_refresh_embed, market="KR")
        await interaction.followup.send(embed=_embed(discord, payload), ephemeral=True)

    async def _handle_scan(interaction, market: str):
        enabled = bool(config.enable_scan_execution and not config.dry_run)
        if not enabled:
            payload = build_scan_ack_embed(config, market=market)
            await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)
            return
        if not config.result_channel_id:
            await interaction.response.send_message(
                "DISCORD_RESULT_CHANNEL_ID가 없어서 전체 스캔 실행을 시작할 수 없습니다.",
                ephemeral=True,
            )
            return

        job = create_scan_job(market)
        lock = DiscordScanLock()
        if not lock.try_acquire(job_id=job.job_id, market=job.market):
            await interaction.response.send_message(embed=_embed(discord, build_scan_busy_embed()), ephemeral=True)
            return

        started = build_scan_started_embed(config, job=job)
        await interaction.response.send_message(embed=_embed(discord, started), ephemeral=True)
        client.loop.create_task(_run_scan_background(job, lock, interaction))

    async def _run_scan_background(job, lock, interaction):
        try:
            channel = None
            try:
                channel = await _result_channel()
            except Exception as exc:
                print(f"Discord result channel fetch failed for {job.job_id}: {exc}", file=sys.stderr)
            if channel is not None:
                try:
                    await channel.send(embed=_embed(discord, build_scan_started_embed(config, job=job)))
                except Exception as exc:
                    print(f"Discord start message failed for {job.job_id}: {exc}", file=sys.stderr)
            summary = await run_scan_job(job)
            payloads = build_scan_result_embeds(summary, config=config)
            if channel is not None:
                try:
                    await _send_embed_chunks(discord, channel, payloads)
                except Exception as exc:
                    print(f"Discord result channel send failed for {job.job_id}: {exc}", file=sys.stderr)
            try:
                await _send_followup_chunks(discord, interaction, payloads[:2])
            except Exception as exc:
                print(f"Discord interaction followup failed for {job.job_id}: {exc}", file=sys.stderr)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            try:
                channel = await _result_channel()
                if channel is not None:
                    await channel.send(f"Discord scan job `{job.job_id}` failed: {str(exc)[:1500]}")
            except Exception:
                pass
        finally:
            lock.release()

    client.run(config.bot_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
