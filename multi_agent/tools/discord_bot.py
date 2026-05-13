#!/usr/bin/env python3
"""Discord bot entrypoint for remote scanner control."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.discord_integration.config import load_discord_config
from modules.discord_integration.permissions import is_authorized_user
from modules.discord_integration.renderers import (
    build_archive_embed,
    build_scan_ack_embed,
    build_status_embed,
    build_top_deep_embeds,
)


def _embed(discord_module, payload):
    return discord_module.Embed.from_dict(payload)


def _role_ids(interaction) -> Iterable[str]:
    roles = getattr(getattr(interaction, "user", None), "roles", []) or []
    return [str(getattr(role, "id", "")) for role in roles if getattr(role, "id", None)]


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

    async def _guard(interaction) -> bool:
        user_id = str(getattr(getattr(interaction, "user", None), "id", "") or "")
        if is_authorized_user(config, user_id=user_id, role_ids=_role_ids(interaction)):
            return True
        await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
        return False

    @client.event
    async def on_ready():
        print(f"Discord bot ready as {client.user} (dry_run={config.dry_run})")

    @tree.command(name="status", description="Discord 연동 설정, 최근 Run, 서버 상태를 확인합니다.")
    async def status(interaction):
        if not await _guard(interaction):
            return
        await interaction.response.send_message(embed=_embed(discord, build_status_embed(config)), ephemeral=True)

    @tree.command(name="top_deep", description="최근 자동 정밀분석 이력과 종목별 상세 매수 판단을 조회합니다.")
    @app_commands.describe(ticker="선택 종목 티커 예: 005930.KS", run_id="선택 Run ID 예: RUN-XXXXXXXX")
    async def top_deep(interaction, ticker: str = "", run_id: str = ""):
        if not await _guard(interaction):
            return
        embeds = [_embed(discord, payload) for payload in build_top_deep_embeds(ticker=ticker, run_id=run_id)]
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)

    @tree.command(name="archive", description="최근 스캔 아카이브와 realized outcome 상태를 조회합니다.")
    @app_commands.describe(market="시장 필터", ticker="선택 종목 티커 예: 005930.KS", run_id="선택 Run ID 예: RUN-XXXXXXXX")
    async def archive(interaction, market: str = "", ticker: str = "", run_id: str = ""):
        if not await _guard(interaction):
            return
        payload = build_archive_embed(market=market, ticker=ticker, run_id=run_id)
        await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)

    @tree.command(name="kospi_scan", description="KOSPI 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.")
    async def kospi_scan(interaction):
        if not await _guard(interaction):
            return
        payload = build_scan_ack_embed(config, market="KOSPI")
        await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)

    @tree.command(name="kosdaq_scan", description="KOSDAQ 전체 스윙 스캔을 실행합니다. max_scan은 2000으로 고정됩니다.")
    async def kosdaq_scan(interaction):
        if not await _guard(interaction):
            return
        payload = build_scan_ack_embed(config, market="KOSDAQ")
        await interaction.response.send_message(embed=_embed(discord, payload), ephemeral=True)

    @tree.command(name="macro_refresh", description="매크로/마켓 게이트 컨텍스트를 새로고침하고 요약을 표시합니다.")
    async def macro_refresh(interaction):
        if not await _guard(interaction):
            return
        await interaction.response.send_message("매크로 새로고침 실행 연결은 다음 단계에서 활성화됩니다.", ephemeral=True)

    client.run(config.bot_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
