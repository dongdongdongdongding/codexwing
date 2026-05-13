from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .commands import FULL_KR_SCAN_MAX


def _load_local_env() -> None:
    for candidate in (Path(".env.local"), Path(".env")):
        if not candidate.exists():
            continue
        try:
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _split_ids(value: str) -> List[str]:
    out: List[str] = []
    for raw in str(value or "").replace(";", ",").split(","):
        item = raw.strip()
        if item and item not in out:
            out.append(item)
    return out


def _is_snowflake(value: str) -> bool:
    text = str(value or "").strip()
    return text.isdigit() and 15 <= len(text) <= 25


@dataclass(frozen=True)
class DiscordIntegrationConfig:
    bot_token: str = ""
    application_id: str = ""
    guild_id: str = ""
    result_channel_id: str = ""
    allowed_user_ids: List[str] = field(default_factory=list)
    allowed_role_ids: List[str] = field(default_factory=list)
    dry_run: bool = True
    enable_scan_execution: bool = False
    command_scope: str = "guild"
    web_base_url: str = "http://localhost:8501"
    scan_max: int = FULL_KR_SCAN_MAX

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        if not self.bot_token:
            errors.append("DISCORD_BOT_TOKEN is required before running the bot")
        if not self.application_id:
            errors.append("DISCORD_APPLICATION_ID is required for command registration")
        elif not _is_snowflake(self.application_id):
            errors.append("DISCORD_APPLICATION_ID must be a Discord snowflake")
        if self.command_scope not in {"guild", "global"}:
            errors.append("DISCORD_COMMAND_SCOPE must be guild or global")
        if self.command_scope == "guild" and not self.guild_id:
            errors.append("DISCORD_GUILD_ID is required when DISCORD_COMMAND_SCOPE=guild")
        if self.guild_id and not _is_snowflake(self.guild_id):
            errors.append("DISCORD_GUILD_ID must be a Discord snowflake")
        if self.result_channel_id and not _is_snowflake(self.result_channel_id):
            errors.append("DISCORD_RESULT_CHANNEL_ID must be a Discord snowflake")
        if self.enable_scan_execution and not self.result_channel_id:
            errors.append("DISCORD_RESULT_CHANNEL_ID is required when scan execution is enabled")
        for user_id in self.allowed_user_ids:
            if not _is_snowflake(user_id):
                errors.append(f"DISCORD_ALLOWED_USER_IDS contains invalid snowflake: {user_id}")
        for role_id in self.allowed_role_ids:
            if not _is_snowflake(role_id):
                errors.append(f"DISCORD_ALLOWED_ROLE_IDS contains invalid snowflake: {role_id}")
        if not self.allowed_user_ids and not self.allowed_role_ids:
            warnings.append("No allowlist set; execution commands should stay disabled until users or roles are restricted")
        if self.scan_max != FULL_KR_SCAN_MAX:
            errors.append(f"Discord KR scans must stay fixed at {FULL_KR_SCAN_MAX}")
        if self.dry_run:
            warnings.append("DISCORD_DRY_RUN=1: command registration/execution should be simulated only")
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "config": {
                "application_id_set": bool(self.application_id),
                "guild_id_set": bool(self.guild_id),
                "result_channel_id_set": bool(self.result_channel_id),
                "allowed_user_count": len(self.allowed_user_ids),
                "allowed_role_count": len(self.allowed_role_ids),
                "dry_run": bool(self.dry_run),
                "enable_scan_execution": bool(self.enable_scan_execution),
                "command_scope": self.command_scope,
                "web_base_url": self.web_base_url,
                "scan_max": self.scan_max,
            },
        }


def load_discord_config(*, load_env: bool = True) -> DiscordIntegrationConfig:
    if load_env:
        _load_local_env()
    return DiscordIntegrationConfig(
        bot_token=os.getenv("DISCORD_BOT_TOKEN", "").strip(),
        application_id=os.getenv("DISCORD_APPLICATION_ID", "").strip(),
        guild_id=os.getenv("DISCORD_GUILD_ID", "").strip(),
        result_channel_id=os.getenv("DISCORD_RESULT_CHANNEL_ID", "").strip(),
        allowed_user_ids=_split_ids(os.getenv("DISCORD_ALLOWED_USER_IDS", "")),
        allowed_role_ids=_split_ids(os.getenv("DISCORD_ALLOWED_ROLE_IDS", "")),
        dry_run=_env_bool("DISCORD_DRY_RUN", True),
        enable_scan_execution=_env_bool("DISCORD_ENABLE_SCAN_EXECUTION", False),
        command_scope=os.getenv("DISCORD_COMMAND_SCOPE", "guild").strip().lower() or "guild",
        web_base_url=os.getenv("DISCORD_WEB_BASE_URL", "http://localhost:8501").strip() or "http://localhost:8501",
        scan_max=FULL_KR_SCAN_MAX,
    )


__all__ = ["DiscordIntegrationConfig", "load_discord_config"]
