import os

from modules.discord_integration.commands import COMMAND_SPECS, FULL_KR_SCAN_MAX, command_contract
from modules.discord_integration.config import load_discord_config


def test_kr_scan_commands_are_fixed_to_full_universe(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    contract = command_contract()

    assert contract["full_kr_scan_max"] == 2000
    assert COMMAND_SPECS["kospi_scan"].max_scan == FULL_KR_SCAN_MAX
    assert COMMAND_SPECS["kosdaq_scan"].max_scan == FULL_KR_SCAN_MAX
    assert COMMAND_SPECS["kospi_scan"].fixed_options["scan_mode"] == "SWING"
    assert COMMAND_SPECS["kosdaq_scan"].fixed_options["profile"] == "prod"


def test_discord_config_validation_requires_secret_and_allowlist(monkeypatch):
    for key in list(os.environ):
        if key.startswith("DISCORD_"):
            monkeypatch.delenv(key, raising=False)

    config = load_discord_config(load_env=False)
    validation = config.validate()

    assert validation["ok"] is False
    assert any("DISCORD_BOT_TOKEN" in item for item in validation["errors"])
    assert any("allowlist" in item for item in validation["warnings"])
    assert validation["config"]["scan_max"] == 2000


def test_discord_config_accepts_private_guild_setup(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "x" * 40)
    monkeypatch.setenv("DISCORD_APPLICATION_ID", "123456789012345678")
    monkeypatch.setenv("DISCORD_GUILD_ID", "223456789012345678")
    monkeypatch.setenv("DISCORD_RESULT_CHANNEL_ID", "323456789012345678")
    monkeypatch.setenv("DISCORD_ALLOWED_USER_IDS", "423456789012345678,523456789012345678")
    monkeypatch.setenv("DISCORD_DRY_RUN", "0")
    monkeypatch.setenv("DISCORD_COMMAND_SCOPE", "guild")

    validation = load_discord_config(load_env=False).validate()

    assert validation["ok"] is True
    assert validation["errors"] == []
    assert validation["config"]["allowed_user_count"] == 2
    assert validation["config"]["dry_run"] is False
