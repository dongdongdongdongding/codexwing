import asyncio
import json
from pathlib import Path

from multi_agent.tools.discord_bot import _send_interaction_chunks
from modules.discord_integration.config import DiscordIntegrationConfig
from modules.discord_integration.delivery import (
    SAFE_MESSAGE_CHARS,
    chunk_embeds_for_discord,
    discord_embed_char_count,
    prepare_embeds_for_discord,
)
from modules.discord_integration.permissions import is_authorized_user
from modules.discord_integration.register import (
    build_discord_command_payloads,
    build_oauth_invite_url,
    register_application_commands,
)
from modules.discord_integration import renderers
from modules.discord_integration.renderers import (
    build_archive_embed,
    build_runs_embed,
    build_scan_result_embeds,
    build_scan_ack_embed,
    build_status_embed,
    build_top_deep_embeds,
    run_id_choices,
)
from modules.discord_integration.scan_executor import (
    DiscordScanLock,
    build_scan_command,
    create_scan_job,
)


def test_register_payloads_include_expected_commands_and_options():
    payloads = build_discord_command_payloads()
    by_name = {row["name"]: row for row in payloads}

    assert {"kospi_scan", "kosdaq_scan", "macro_refresh", "top_deep", "archive", "runs", "status"}.issubset(by_name)
    assert "options" not in by_name["kospi_scan"]
    assert any(opt["name"] == "ticker" for opt in by_name["top_deep"]["options"])
    assert any(opt["name"] == "offset" for opt in by_name["top_deep"]["options"])
    top_limit = [opt for opt in by_name["top_deep"]["options"] if opt["name"] == "limit"][0]
    assert top_limit["max_value"] == 15
    top_run = [opt for opt in by_name["top_deep"]["options"] if opt["name"] == "run_id"][0]
    assert top_run["autocomplete"] is True
    archive_market = [opt for opt in by_name["archive"]["options"] if opt["name"] == "market"][0]
    assert [choice["value"] for choice in archive_market["choices"]] == ["KOSPI", "KOSDAQ"]


def test_shared_delivery_sanitizes_oversized_embed_payloads():
    payloads = [
        {
            "title": "t" * 500,
            "description": "d" * 7000,
            "fields": [
                {"name": f"field-{idx}" * 80, "value": "v" * 5000, "inline": False}
                for idx in range(30)
            ],
        }
    ]

    prepared = prepare_embeds_for_discord(payloads)
    chunks = chunk_embeds_for_discord(prepared)

    assert prepared
    assert chunks
    for embed in prepared:
        assert len(embed.get("title") or "") <= 256
        assert len(embed.get("description") or "") <= 4096
        assert len(embed.get("fields") or []) <= 25
        assert discord_embed_char_count(embed) <= SAFE_MESSAGE_CHARS
    for chunk in chunks:
        assert sum(discord_embed_char_count(embed) for embed in chunk) <= SAFE_MESSAGE_CHARS


def test_interaction_sender_splits_oversized_embeds_before_send():
    class FakeEmbed:
        @staticmethod
        def from_dict(payload):
            return payload

    class FakeDiscord:
        Embed = FakeEmbed

    class FakeResponse:
        def __init__(self):
            self.messages = []
            self._done = False

        def is_done(self):
            return self._done

        async def send_message(self, **kwargs):
            self._done = True
            self.messages.append(kwargs)

    class FakeFollowup:
        def __init__(self):
            self.messages = []

        async def send(self, **kwargs):
            self.messages.append(kwargs)

    class FakeInteraction:
        def __init__(self):
            self.response = FakeResponse()
            self.followup = FakeFollowup()

    payload = {
        "title": "archive",
        "description": "d" * 1000,
        "fields": [
            {"name": f"row-{idx}", "value": "v" * 1024, "inline": False}
            for idx in range(12)
        ],
    }
    interaction = FakeInteraction()

    asyncio.run(_send_interaction_chunks(FakeDiscord, interaction, [payload]))

    messages = interaction.response.messages + interaction.followup.messages
    assert len(messages) >= 2
    assert interaction.response.messages
    for message in messages:
        embeds = message.get("embeds") or [message.get("embed")]
        embeds = [embed for embed in embeds if embed]
        assert embeds
        assert sum(discord_embed_char_count(embed) for embed in embeds) <= SAFE_MESSAGE_CHARS


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
                    "day_change_pct": -3.21,
                    "loss_risk_score": 42.0,
                    "policy_metadata": {
                        "active_policy_version": "kr_scanner_policy_test",
                        "promotion_status": "production_champion",
                    },
                    "realized_expectancy_admission": {
                        "expected_value_3d_pct": 1.2,
                        "expected_value_5d_pct": 4.5,
                        "base_expected_value_5d_pct": 4.5,
                        "stress_expected_value_5d_pct": -3.2,
                        "ranking_score_5d": 72.0,
                    },
                    "flow": {
                        "foreigner": 1200000,
                        "institution": -300000,
                        "retail": -900000,
                        "whale_score": 72,
                    },
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
    assert embeds[0]["title"] == "Admission 모델 자동 정밀분석"
    assert "조건부 매수 가능" in embeds[0]["fields"][0]["value"]
    assert "전일비: -3.21%" in embeds[0]["fields"][0]["value"]
    assert "정책: kr_scanner_policy_test · production_champion" in embeds[0]["fields"][0]["value"]
    assert "Admission 지표: 후보 목표터치 확률 - · 검증 평균 5D고가상승 +4.50% · 검증 최저 5D고가상승 -3.20% · 후보 모델점수 72.0" in embeds[0]["fields"][0]["value"]
    assert "수급: 외인 +1,200,000 / 기관 -300,000 / 개인 -900,000" in embeds[0]["fields"][0]["value"]


def test_run_index_and_archive_can_select_accumulated_runs(tmp_path, monkeypatch):
    report_dir = tmp_path / "top_deep"
    artifact_dir = tmp_path / "artifacts"
    report_dir.mkdir()
    (artifact_dir / "RUN-OLD").mkdir(parents=True)
    (artifact_dir / "RUN-NEW").mkdir(parents=True)
    (report_dir / "RUN-OLD.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "RUN-OLD",
                    "market": "KOSPI",
                    "rank": 1,
                    "ticker": "005930.KS",
                    "stock_name": "삼성전자",
                    "policy_metadata": {
                        "active_policy_version": "kr_scanner_policy_old",
                        "promotion_status": "production_champion",
                    },
                    "realized_expectancy_admission": {"ranking_score_5d": 64.0},
                    "trade_plan": {"readiness_analysis": {"final_buy_judgment": {"action": "관망"}}},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (report_dir / "RUN-NEW.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "RUN-NEW",
                    "market": "KOSDAQ",
                    "rank": 1,
                    "ticker": "035900.KQ",
                    "stock_name": "JYP Ent.",
                    "trade_plan": {"readiness_analysis": {"final_buy_judgment": {"action": "눌림 대기"}}},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (artifact_dir / "RUN-OLD" / "scan_pipeline_summary.json").write_text(
        json.dumps({"run_id": "RUN-OLD", "market": "KOSPI", "scan_mode": "SWING", "total_scans": 2000, "result_count": 2}),
        encoding="utf-8",
    )
    (artifact_dir / "RUN-OLD" / "raw_scan_results.json").write_text(
        json.dumps(
            {
                "results_sorted": [
                    {"Ticker": "005930.KS", "Stock Name": "삼성전자", "Decision Score": 91, "Strategy": "BUY"},
                    {"Ticker": "000660.KS", "Stock Name": "SK하이닉스", "Decision Score": 88, "Strategy": "WATCH"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (artifact_dir / "RUN-NEW" / "scan_pipeline_summary.json").write_text(
        json.dumps({"run_id": "RUN-NEW", "market": "KOSDAQ", "scan_mode": "SWING", "total_scans": 2000, "result_count": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    runs = build_runs_embed(market="KOSPI")
    archive_top = build_archive_embed(run_id="RUN-OLD", offset=0, limit=1)
    archive = build_archive_embed(run_id="RUN-OLD", offset=1, limit=1)
    top_deep = build_top_deep_embeds(run_id="RUN-OLD")

    assert "RUN-OLD" in runs["fields"][0]["name"]
    assert run_id_choices(current="OLD") == ["RUN-OLD"]
    assert "정책 scan_universe_admission_runtime_v2_entry_touch" in archive_top["fields"][0]["value"]
    assert "Admission" in archive_top["fields"][0]["value"]
    assert "SK하이닉스" in archive["fields"][0]["name"]
    assert "삼성전자" in top_deep[0]["fields"][0]["name"]


def test_archive_embed_falls_back_to_latest_raw_artifact_without_top_deep(tmp_path, monkeypatch):
    report_dir = tmp_path / "top_deep"
    artifact_dir = tmp_path / "artifacts"
    report_dir.mkdir()
    (artifact_dir / "RUN-RAW").mkdir(parents=True)
    (artifact_dir / "RUN-RAW" / "scan_pipeline_summary.json").write_text(
        json.dumps({"run_id": "RUN-RAW", "market": "KOSDAQ", "scan_mode": "SWING", "total_scans": 1717, "result_count": 1}),
        encoding="utf-8",
    )
    (artifact_dir / "RUN-RAW" / "raw_scan_results.json").write_text(
        json.dumps(
            {"results_sorted": [{"Ticker": "035900.KQ", "Stock Name": "JYP Ent.", "Decision Score": 89, "Strategy": "WATCH", "day_return_pct": -4.32}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    archive = build_archive_embed(market="KOSDAQ")

    assert "RUN-RAW" in archive["description"]
    assert "scan_universe_admission" in archive["description"]
    assert "JYP Ent." in archive["fields"][0]["name"]
    assert "당일 -4.32%" in archive["fields"][0]["value"]
    assert "모델해석" in archive["fields"][0]["value"]
    assert "근거" in archive["fields"][0]["value"]


def test_archive_embed_includes_low_liquidity_blocked_candidates(tmp_path, monkeypatch):
    report_dir = tmp_path / "top_deep"
    artifact_dir = tmp_path / "artifacts"
    report_dir.mkdir()
    run_dir = artifact_dir / "RUN-LIQ"
    run_dir.mkdir(parents=True)
    (run_dir / "scan_pipeline_summary.json").write_text(
        json.dumps({"run_id": "RUN-LIQ", "market": "KOSPI", "scan_mode": "SWING"}),
        encoding="utf-8",
    )
    (run_dir / "raw_scan_results.json").write_text(
        json.dumps({"results_sorted": [{"ticker": "005930.KS", "stock_name": "삼성전자"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    low_row = {
        "ticker": "002410.KS",
        "stock_name": "저유동성후보",
        "scan_universe_admission": {
            "probability_pct": 64.2,
            "promotion_block_reason": "LIQUIDITY_FILTER_FAIL",
            "feature_values": {"turnover": 240000000, "volume_ratio": 0.42},
        },
        "scan_result_interpretation": {"threshold_gap_pct_points": 4.2},
    }
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)
    monkeypatch.setattr(
        renderers,
        "_build_admission_result_for_run",
        lambda *args, **kwargs: {"all_records": [], "liquidity_blocked": [low_row]},
    )

    archive = build_archive_embed(run_id="RUN-LIQ")

    low_field = next(field for field in archive["fields"] if field["name"] == "저유동성 차단 후보")
    assert "저유동성후보" in low_field["value"]
    assert "LIQUIDITY_FILTER_FAIL" in low_field["value"]


def test_archive_embed_includes_profile_only_exception_leaders(tmp_path, monkeypatch):
    report_dir = tmp_path / "top_deep"
    artifact_dir = tmp_path / "artifacts"
    shared_dir = tmp_path / "shared" / "RUN-PROFILE"
    report_dir.mkdir()
    run_dir = artifact_dir / "RUN-PROFILE"
    run_dir.mkdir(parents=True)
    shared_dir.mkdir(parents=True)
    planner_path = shared_dir / "planner_handoff.json"
    profile_path = shared_dir / "profile_diagnostics.json"
    planner_path.write_text(
        json.dumps({"decisions": [{"ticker": "005930.KS", "decision": "PRIORITY_WATCHLIST"}], "watchlist_meta": []}),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "exception_leaders": {
                    "watchlist_meta": [
                        {
                            "ticker": "034730.KS",
                            "stock_name": "SK",
                            "risk_label": "EXCEPTION_LEADER",
                            "reason": "exception_leader_watchlist",
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "scan_pipeline_summary.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-PROFILE",
                "market": "KOSPI",
                "scan_mode": "SWING",
                "manifest_paths": {
                    "planner_handoff": str(planner_path),
                    "profile_diagnostics": str(profile_path),
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "raw_scan_results.json").write_text(
        json.dumps(
            {"results_sorted": [{"ticker": "005930.KS", "stock_name": "삼성전자", "Decision Score": 91}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    archive = build_archive_embed(run_id="RUN-PROFILE", limit=10)

    assert "rows 1" in archive["description"]
    assert any("삼성전자" in field["name"] for field in archive["fields"])


def test_scan_ack_refuses_execution_while_dry_run():
    config = DiscordIntegrationConfig(dry_run=True, enable_scan_execution=True)
    embed = build_scan_ack_embed(config, market="KOSPI")

    assert "max_scan=2000" in embed["description"]
    assert "막혀" in embed["description"]


def test_scan_executor_command_is_fixed_full_kr_scan(monkeypatch, tmp_path):
    from modules.discord_integration import scan_executor

    monkeypatch.setattr(scan_executor, "JOB_DIR", tmp_path)
    job = create_scan_job("KOSDAQ")
    cmd = build_scan_command(job)

    assert "--market" in cmd
    assert cmd[cmd.index("--market") + 1] == "KOSDAQ"
    assert cmd[cmd.index("--max-scan") + 1] == "2000"
    assert cmd[cmd.index("--profile") + 1] == "prod"
    assert cmd[cmd.index("--scan-mode") + 1] == "SWING"


def test_scan_executor_command_supports_intraday_observation_mode(monkeypatch, tmp_path):
    from modules.discord_integration import scan_executor

    monkeypatch.setattr(scan_executor, "JOB_DIR", tmp_path)
    job = create_scan_job("KOSPI", scan_mode="INTRADAY")
    cmd = build_scan_command(job)

    assert job.scan_mode == "INTRADAY"
    assert "KOSPI_INTRADAY" in job.log_path.name
    assert cmd[cmd.index("--market") + 1] == "KOSPI"
    assert cmd[cmd.index("--scan-mode") + 1] == "INTRADAY"
    assert "intraday" in cmd[cmd.index("--strategy-version") + 1]


def test_scan_executor_extracts_summary_from_noisy_log():
    from modules.discord_integration.scan_executor import _extract_last_json_object

    payload = _extract_last_json_object(
        '[1/2] filtered\n{"run_id": "RUN-ABC", "market": "KOSPI", "result_count": 3, "total_scans": 2000}\nExit code: 0\n'
    )

    assert payload["run_id"] == "RUN-ABC"
    assert payload["total_scans"] == 2000


def test_scan_executor_loads_recent_artifact_summary_when_stdout_has_no_json(monkeypatch, tmp_path):
    from datetime import datetime, timezone

    from modules.discord_integration import scan_executor
    from modules.discord_integration.scan_executor import DiscordScanJob, _load_recent_artifact_summary

    artifact_dir = tmp_path / "artifacts"
    run_dir = artifact_dir / "RUN-DISCORD"
    run_dir.mkdir(parents=True)
    (run_dir / "scan_pipeline_summary.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-DISCORD",
                "market": "KOSPI",
                "total_scans": 835,
                "result_count": 56,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(scan_executor, "ARTIFACT_DIR", artifact_dir)

    job = DiscordScanJob(
        job_id="DS-TEST",
        market="KOSPI",
        log_path=tmp_path / "DS-TEST.log",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    payload = _load_recent_artifact_summary(job)

    assert payload["run_id"] == "RUN-DISCORD"
    assert payload["result_count"] == 56


def test_scan_lock_allows_cross_market_parallel_jobs(tmp_path):
    lock_path = tmp_path / "scan.lock"
    first = DiscordScanLock(path=lock_path)
    second = DiscordScanLock(path=lock_path)
    third = DiscordScanLock(path=lock_path)

    assert first.try_acquire(job_id="DS-ONE", market="KOSPI") is True
    assert second.try_acquire(job_id="DS-TWO", market="KOSDAQ") is True
    assert third.try_acquire(job_id="DS-THREE", market="KOSPI") is False

    first.release()
    second.release()
    assert third.try_acquire(job_id="DS-THREE", market="KOSPI") is True
    third.release()


def test_scan_result_renderer_includes_summary_and_top_deep(monkeypatch, tmp_path):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    (report_dir / "RUN-DISCORD.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "RUN-DISCORD",
                    "rank": 1,
                    "ticker": "000660.KS",
                    "stock_name": "SK하이닉스",
                    "trade_plan": {
                        "readiness_analysis": {
                            "quality": {"grade": "A", "score": 90},
                            "upside": {"grade": "B", "score": 70},
                            "timing": {"grade": "B+", "score": 75},
                            "chase_risk_level": "보통",
                            "final_buy_judgment": {"action": "눌림 대기"},
                        }
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    config = DiscordIntegrationConfig(web_base_url="http://localhost:8501")
    summary = {
        "run_id": "RUN-DISCORD",
        "market": "KOSPI",
        "total_scans": 2000,
        "result_count": 7,
        "filtered_count": 1993,
        "warnings": [],
        "discord_job": {
            "job_id": "DS-TEST",
            "market": "KOSPI",
            "returncode": 0,
            "log_path": "runtime_state/discord_jobs/DS-TEST.log",
        },
    }

    embeds = build_scan_result_embeds(summary, config=config)

    assert embeds[0]["title"] == "KOSPI 전체 스캔 결과"
    assert embeds[0]["fields"][0]["value"] == "RUN-DISCORD"
    assert any(field["name"] == "Admission 모델 기준" for field in embeds[0]["fields"])
    assert embeds[1]["title"] == "Admission 모델 자동 정밀분석"
    assert any("SK하이닉스" in field["name"] for field in embeds[1]["fields"])


def test_scan_result_renderer_includes_low_liquidity_blocked_candidates(monkeypatch):
    low_row = {
        "ticker": "065150.KQ",
        "stock_name": "저유동성코스닥",
        "scan_universe_admission": {
            "probability_pct": 57.7,
            "prob_threshold_pct": 55.0,
            "promotion_block_reason": "LIQUIDITY_FILTER_FAIL",
            "feature_values": {"turnover": 180000000, "volume_ratio": 0.38},
        },
        "scan_result_interpretation": {"threshold_gap_pct_points": 2.7},
    }
    monkeypatch.setattr(
        renderers,
        "_build_admission_result_for_run",
        lambda *args, **kwargs: {
            "summary": {
                "market": "KOSDAQ",
                "model_name": "fake",
                "label": "fake",
                "selection_rule": "fake_rule",
                "prob_threshold_pct": 55.0,
                "validation": {"win_1d_pct": 50.0, "win_3d_pct": 60.0, "win_5d_pct": 70.0},
            },
            "passed": [],
            "near_miss": [],
            "liquidity_blocked": [low_row],
            "threshold": 0.55,
            "topn": 1,
        },
    )
    embeds = build_scan_result_embeds(
        {
            "run_id": "RUN-LIQ-DISCORD",
            "market": "KOSDAQ",
            "total_scans": 1720,
            "result_count": 0,
            "filtered_count": 1720,
            "warnings": [],
            "discord_job": {"job_id": "DS-LIQ", "market": "KOSDAQ", "returncode": 0},
        },
        config=DiscordIntegrationConfig(web_base_url="http://localhost:8501"),
    )

    low_field = next(field for field in embeds[0]["fields"] if field["name"] == "저유동성 차단 후보")
    assert "저유동성코스닥" in low_field["value"]
    assert "LIQUIDITY_FILTER_FAIL" in low_field["value"]


def test_scan_result_renderer_clarifies_zero_pass_exception_only(monkeypatch, tmp_path):
    report_dir = tmp_path / "top_deep"
    artifact_dir = tmp_path / "artifacts"
    shared_dir = tmp_path / "shared" / "RUN-ZERO"
    report_dir.mkdir()
    (artifact_dir / "RUN-ZERO").mkdir(parents=True)
    shared_dir.mkdir(parents=True)
    (report_dir / "RUN-ZERO.json").write_text(
        json.dumps(
            [
                {
                    "run_id": "RUN-ZERO",
                    "rank": 1,
                    "ticker": "017670.KS",
                    "stock_name": "SK텔레콤",
                    "selection_alignment": {"analysis_section": "Exception Leader", "analysis_section_rank": 1},
                    "trade_plan": {"readiness_analysis": {"final_buy_judgment": {"action": "관망"}}},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    scanner_path = shared_dir / "scanner_handoff.json"
    scanner_path.write_text(
        json.dumps(
            {
                "summary": {
                    "market_gate": {
                        "gate": "RED",
                        "msg": "종가 하락장 경보: KOSPI -6.12% / KOSDAQ -5.14%",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (artifact_dir / "RUN-ZERO" / "scan_pipeline_summary.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-ZERO",
                "market": "KOSPI",
                "total_scans": 835,
                "result_count": 0,
                "filtered_count": 835,
                "manifest_paths": {"scanner_handoff": str(scanner_path)},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    summary = {
        "run_id": "RUN-ZERO",
        "market": "KOSPI",
        "total_scans": 835,
        "result_count": 0,
        "filtered_count": 835,
        "warnings": [],
        "discord_job": {"job_id": "DS-ZERO", "market": "KOSPI", "returncode": 0},
    }

    embeds = build_scan_result_embeds(summary, config=DiscordIntegrationConfig(web_base_url="http://localhost:8501"))

    assert embeds[0]["color"] == 0xF1C40F
    assert any(field["name"] == "Market Gate" for field in embeds[0]["fields"])
    warnings_field = next(field for field in embeds[0]["fields"] if field["name"] == "Warnings")
    assert "신규 admission 모델" in warnings_field["value"]
    assert "운영 상태" == embeds[1]["fields"][0]["name"]
    assert "Admission 0 / NearMiss 0" in embeds[1]["fields"][0]["value"]


def test_scan_result_renderer_includes_top10_plus_exception5(monkeypatch, tmp_path):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    rows = []
    for idx in range(1, 16):
        section = "Top5" if idx <= 10 else "Exception Leader"
        rows.append(
            {
                "run_id": "RUN-15",
                "rank": idx,
                "ticker": f"000{idx:03d}.KS",
                "stock_name": f"종목{idx}",
                "signal_label": "NO_BUY" if idx == 3 else "WAIT_CONFIRM",
                "display_contract": {
                    "display_status": "VISIBLE_RISK_ANNOTATED" if idx == 3 else "VISIBLE",
                    "original_scan_rank": idx,
                    "planner_priority_rank": idx,
                    "suppression_allowed": False,
                },
                "selection_alignment": {
                    "analysis_section": section,
                    "analysis_section_rank": idx if idx <= 10 else idx - 10,
                },
                "trade_plan": {
                    "readiness_analysis": {
                        "final_buy_judgment": {"action": "관망"},
                    }
                },
            }
        )
    (report_dir / "RUN-15.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)

    embeds = build_scan_result_embeds(
        {
            "run_id": "RUN-15",
            "market": "KOSPI",
            "total_scans": 835,
            "result_count": 65,
            "filtered_count": 770,
            "warnings": [],
            "discord_job": {"job_id": "DS-15", "market": "KOSPI", "returncode": 0},
        },
        config=DiscordIntegrationConfig(web_base_url="http://localhost:8501"),
    )

    fields = [
        field
        for embed in embeds
        if embed["title"] == "Admission 모델 자동 정밀분석"
        for field in embed["fields"]
    ]
    candidate_fields = [field for field in fields if field["name"] != "데이터 무결성"]
    assert len(candidate_fields) == 15
    assert "종목10" in candidate_fields[9]["name"]
    assert "종목15" in candidate_fields[14]["name"]
    assert "VISIBLE_RISK_ANNOTATED" in candidate_fields[2]["value"]
    assert "원본#3" in candidate_fields[2]["value"]
    assert "Exception Leader #5" in candidate_fields[14]["value"]
    assert any(field["name"] == "데이터 무결성" for field in fields)


def test_scan_result_renderer_does_not_truncate_split_top_deep_pages(monkeypatch, tmp_path):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    rows = []
    for idx in range(1, 16):
        rows.append(
            {
                "run_id": "RUN-SPLIT-15",
                "rank": idx,
                "ticker": f"001{idx:03d}.KS",
                "stock_name": f"분할종목{idx}",
                "selection_alignment": {
                    "analysis_section": "Top5" if idx <= 10 else "Exception Leader",
                    "analysis_section_rank": idx if idx <= 10 else idx - 10,
                },
                "trade_plan": {"readiness_analysis": {"final_buy_judgment": {"action": "관망"}}},
            }
        )
    (report_dir / "RUN-SPLIT-15.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "_field_value_for_top_deep", lambda _row: "x" * 4500)

    embeds = build_scan_result_embeds(
        {
            "run_id": "RUN-SPLIT-15",
            "market": "KOSPI",
            "total_scans": 835,
            "result_count": 15,
            "filtered_count": 820,
            "warnings": [],
            "discord_job": {"job_id": "DS-SPLIT-15", "market": "KOSPI", "returncode": 0},
        },
        config=DiscordIntegrationConfig(web_base_url="http://localhost:8501"),
    )

    assert len(embeds) > 10
    fields = [
        field
        for embed in embeds
        if embed["title"] == "Admission 모델 자동 정밀분석"
        for field in embed["fields"]
    ]
    candidate_fields = [field for field in fields if field["name"] != "데이터 무결성"]
    assert len(candidate_fields) == 15
    assert "분할종목15" in candidate_fields[-1]["name"]


def test_top_deep_embed_splits_before_discord_character_limit(monkeypatch, tmp_path):
    report_dir = tmp_path / "top_deep"
    report_dir.mkdir()
    rows = [
        {
            "run_id": "RUN-LONG",
            "rank": idx,
            "ticker": f"000{idx:03d}.KS",
            "stock_name": f"긴종목{idx}",
            "selection_alignment": {"analysis_section": "Top5", "analysis_section_rank": idx},
            "trade_plan": {"readiness_analysis": {"final_buy_judgment": {"action": "관망"}}},
        }
        for idx in range(1, 16)
    ]
    (report_dir / "RUN-LONG.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "_field_value_for_top_deep", lambda _row: "x" * 1000)

    embeds = build_top_deep_embeds(run_id="RUN-LONG", limit=15)

    assert len(embeds) > 1
    candidate_fields = [
        field
        for embed in embeds
        for field in embed["fields"]
        if field["name"] != "데이터 무결성"
    ]
    assert len(candidate_fields) == 15
    assert all(renderers._embed_char_count(embed) <= renderers.DISCORD_EMBED_SAFE_CHARS for embed in embeds)
