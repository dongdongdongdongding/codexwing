"""Discord remote-control integration contracts.

The Discord bot must stay outside Streamlit and call the existing non-UI
pipeline/report/archive paths. This package contains setup-safe configuration
and command contracts that can be validated before a real bot token is added.
"""

from .commands import COMMAND_SPECS, FULL_KR_SCAN_MAX, WEB_EQUIVALENT_RESULT_FIELDS
from .config import DiscordIntegrationConfig, load_discord_config
from .permissions import is_authorized_user

__all__ = [
    "COMMAND_SPECS",
    "DiscordIntegrationConfig",
    "FULL_KR_SCAN_MAX",
    "WEB_EQUIVALENT_RESULT_FIELDS",
    "is_authorized_user",
    "load_discord_config",
]
