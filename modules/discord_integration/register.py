from __future__ import annotations

from typing import Any, Dict, List

import requests

from .commands import COMMAND_SPECS
from .config import DiscordIntegrationConfig

DEFAULT_BOT_PERMISSIONS = 117760


def build_oauth_invite_url(config: DiscordIntegrationConfig, *, permissions: int = DEFAULT_BOT_PERMISSIONS) -> str:
    if not config.application_id:
        return ""
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={config.application_id}"
        f"&permissions={int(permissions)}"
        "&scope=bot%20applications.commands"
    )


def _command_options(name: str) -> List[Dict[str, Any]]:
    if name == "top_deep":
        return [
            {
                "type": 3,
                "name": "market",
                "description": "시장 필터",
                "required": False,
                "choices": [
                    {"name": "KOSPI", "value": "KOSPI"},
                    {"name": "KOSDAQ", "value": "KOSDAQ"},
                ],
            },
            {
                "type": 3,
                "name": "ticker",
                "description": "선택 종목 티커 예: 005930.KS",
                "required": False,
            },
            {
                "type": 3,
                "name": "run_id",
                "description": "선택 Run ID. 입력 중 자동완성됩니다.",
                "required": False,
                "autocomplete": True,
            },
            {
                "type": 4,
                "name": "offset",
                "description": "결과 시작 위치. 예전 결과를 보려면 5, 10처럼 입력",
                "required": False,
                "min_value": 0,
            },
            {
                "type": 4,
                "name": "limit",
                "description": "표시 개수",
                "required": False,
                "min_value": 1,
                "max_value": 10,
            },
        ]
    if name == "archive":
        return [
            {
                "type": 3,
                "name": "market",
                "description": "시장 필터",
                "required": False,
                "choices": [
                    {"name": "KOSPI", "value": "KOSPI"},
                    {"name": "KOSDAQ", "value": "KOSDAQ"},
                ],
            },
            {
                "type": 3,
                "name": "ticker",
                "description": "선택 종목 티커 예: 005930.KS",
                "required": False,
            },
            {
                "type": 3,
                "name": "run_id",
                "description": "선택 Run ID. 입력 중 자동완성됩니다.",
                "required": False,
                "autocomplete": True,
            },
            {
                "type": 4,
                "name": "offset",
                "description": "결과 시작 위치. 예전 결과를 보려면 5, 10처럼 입력",
                "required": False,
                "min_value": 0,
            },
            {
                "type": 4,
                "name": "limit",
                "description": "표시 개수",
                "required": False,
                "min_value": 1,
                "max_value": 10,
            },
        ]
    if name == "runs":
        return [
            {
                "type": 3,
                "name": "market",
                "description": "시장 필터",
                "required": False,
                "choices": [
                    {"name": "KOSPI", "value": "KOSPI"},
                    {"name": "KOSDAQ", "value": "KOSDAQ"},
                ],
            },
            {
                "type": 4,
                "name": "offset",
                "description": "목록 시작 위치",
                "required": False,
                "min_value": 0,
            },
            {
                "type": 4,
                "name": "limit",
                "description": "표시 개수",
                "required": False,
                "min_value": 1,
                "max_value": 15,
            },
        ]
    return []


def build_discord_command_payloads() -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for name, spec in COMMAND_SPECS.items():
        payload: Dict[str, Any] = {
            "name": name,
            "description": spec.description[:100],
            "type": 1,
        }
        options = _command_options(name)
        if options:
            payload["options"] = options
        payloads.append(payload)
    return payloads


def register_application_commands(config: DiscordIntegrationConfig, *, dry_run: bool | None = None) -> Dict[str, Any]:
    validation = config.validate()
    if not validation["ok"]:
        return {"ok": False, "error": "invalid_config", "validation": validation}
    effective_dry_run = config.dry_run if dry_run is None else bool(dry_run)
    payloads = build_discord_command_payloads()
    if effective_dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "scope": config.command_scope,
            "command_count": len(payloads),
            "commands": [row["name"] for row in payloads],
        }

    base = f"https://discord.com/api/v10/applications/{config.application_id}"
    if config.command_scope == "guild":
        endpoint = f"{base}/guilds/{config.guild_id}/commands"
    else:
        endpoint = f"{base}/commands"
    response = requests.put(
        endpoint,
        headers={
            "Authorization": f"Bot {config.bot_token}",
            "Content-Type": "application/json",
        },
        json=payloads,
        timeout=30,
    )
    if response.status_code >= 300:
        return {
            "ok": False,
            "dry_run": False,
            "status_code": response.status_code,
            "error": response.text[:500],
            "invite_url": build_oauth_invite_url(config) if response.status_code in {401, 403, 404} else "",
        }
    try:
        data = response.json()
    except Exception:
        data = []
    return {
        "ok": True,
        "dry_run": False,
        "scope": config.command_scope,
        "command_count": len(data) if isinstance(data, list) else len(payloads),
        "commands": [row["name"] for row in payloads],
    }


__all__ = ["build_discord_command_payloads", "build_oauth_invite_url", "register_application_commands"]
