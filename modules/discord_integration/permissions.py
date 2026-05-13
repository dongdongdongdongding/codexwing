from __future__ import annotations

from typing import Iterable

from .config import DiscordIntegrationConfig


def is_authorized_user(
    config: DiscordIntegrationConfig,
    *,
    user_id: str,
    role_ids: Iterable[str] | None = None,
) -> bool:
    allowed_users = {str(item).strip() for item in config.allowed_user_ids if str(item).strip()}
    allowed_roles = {str(item).strip() for item in config.allowed_role_ids if str(item).strip()}
    user = str(user_id or "").strip()
    roles = {str(item).strip() for item in (role_ids or []) if str(item).strip()}
    if not allowed_users and not allowed_roles:
        return False
    if user and user in allowed_users:
        return True
    return bool(roles.intersection(allowed_roles))


__all__ = ["is_authorized_user"]
