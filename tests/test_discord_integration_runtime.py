import json
from pathlib import Path

from modules.discord_integration.config import DiscordIntegrationConfig
from modules.discord_integration.permissions import is_authorized_user
from modules.discord_integration.register import (
    build_discord_command_payloads,
    build_oauth_invite_url,
    register_application_commands,
)
from modules.discord_integration import renderers
from modules.discord_integration.renderers import (
    build_scan_ack_embed,
    build_status_embed,
    build_top_deep_embeds,
)


def test_register_payloads_include_expected_commands_and_options():
    payloads = build_discord_command_payloads()
    by_name = {row["name"]: row for row in payloads}

    assert {"kospi_scan", "kosdaq_scan", "macro_refresh", "top_deep", "archive", "status"}.issubset(by_name)
    assert "options" not in by_name["kospi_scan"]
    assert any(opt["name"] == "ticker" for opt in by_name["top_deep"]["options"])
    archive_market = [opt for opt in by_name["archive"]["options"] if opt["name"] == "market"][0]
    assert [choice["value"] for choice in archive_market["choices"]] == ["KOSPI", "KOSDAQ"]


def test_register_application_commands_dry_run_does_not_post():
    config = DiscordIntegrationConfig(
        bot_token="x" * 40,
        application_id="123456789012345678",
        guild_id="223456789012345678",
        allowed_user_ids=["323456789012345678"],
        dry_run=True,
    )

    result = register_application_commands(config)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["command_count"] >= 6


def test_oauth_invite_url_contains_required_scopes():
    config = DiscordIntegrationConfig(application_id="123456789012345678")
    url = build_oauth_invite_url(config)

    assert "client_id=123456789012345678" in url
    assert "scope=bot%20applications.commands" in url
    assert "permissions=117760" in url


def test_permission_requires_user_or_role_allowlist():
    locked = DiscordIntegrationConfig()
    assert is_authorized_user(locked, user_id="1", role_ids=[]) is False

    by_user = DiscordIntegrationConfig(allowed_user_ids=["123456789012345678"])
    assert is_authorized_user(by_user, user_id="123456789012345678", role_ids=[]) is True

    by_role = DiscordIntegrationConfig(allowed_role_ids=["223456789012345678"])
    assert is_authorized_user(by_role, user_id="1", role_ids=["223456789012345678"]) is True


def test_readonly_renderers_use_top_deep_artifacts(tmp_path, monkeypatch):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    (report_dir / "RUN-TEST.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "RUN-TEST",
                    "rank": 1,
                    "ticker": "005930.KS",
                    "stock_name": "삼성전자",
                    "decision": "WATCHLIST",
                    "buy_score": 77.5,
                    "loss_risk_score": 42.0,
                    "trade_plan": {
                        "entry_policy": "open/reference",
                        "target_tp_pct": 20.0,
                        "stop_sl_pct": -5.0,
                        "readiness_analysis": {
                            "quality": {"grade": "A", "score": 88.0},
                            "upside": {"grade": "B", "score": 68.0},
                            "timing": {"grade": "B+", "score": 78.0},
                            "chase_risk_level": "낮음",
                            "final_buy_judgment": {"action": "조건부 매수 가능", "summary": "조건 양호"},
                        },
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)

    config = DiscordIntegrationConfig(
        bot_token="x" * 40,
        application_id="123456789012345678",
        guild_id="223456789012345678",
        allowed_user_ids=["323456789012345678"],
        dry_run=True,
    )
    status = build_status_embed(config)
    embeds = build_top_deep_embeds()

    assert status["fields"][3]["value"] == "RUN-TEST"
    assert embeds[0]["title"] == "Top 자동 정밀분석"
    assert "조건부 매수 가능" in embeds[0]["fields"][0]["value"]


def test_scan_ack_refuses_execution_while_dry_run():
    config = DiscordIntegrationConfig(dry_run=True, enable_scan_execution=True)
    embed = build_scan_ack_embed(config, market="KOSPI")

    assert "max_scan=2000" in embed["description"]
    assert "막혀" in embed["description"]
