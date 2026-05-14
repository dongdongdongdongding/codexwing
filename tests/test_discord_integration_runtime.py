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
    assert embeds[0]["title"] == "Top5 + Exception Leader 자동 정밀분석"
    assert "조건부 매수 가능" in embeds[0]["fields"][0]["value"]


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
    archive = build_archive_embed(run_id="RUN-OLD", offset=1, limit=1)
    top_deep = build_top_deep_embeds(run_id="RUN-OLD")

    assert "RUN-OLD" in runs["fields"][0]["name"]
    assert run_id_choices(current="OLD") == ["RUN-OLD"]
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
            {"results_sorted": [{"Ticker": "035900.KQ", "Stock Name": "JYP Ent.", "Decision Score": 89, "Strategy": "WATCH"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "TOP_DEEP_DIR", report_dir)
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    archive = build_archive_embed(market="KOSDAQ")

    assert "RUN-RAW" in archive["description"]
    assert "shadow_plus_top5_exception" in archive["description"]
    assert "JYP Ent." in archive["fields"][0]["name"]


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

    assert "rows 2" in archive["description"]
    assert any("SK" in field["name"] for field in archive["fields"])


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
    assert embeds[1]["title"] == "Top5 + Exception Leader 자동 정밀분석"
    assert any("SK하이닉스" in field["name"] for field in embeds[1]["fields"])


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

    fields = embeds[1]["fields"]
    assert len(fields) == 15
    assert "종목10" in fields[9]["name"]
    assert "종목15" in fields[14]["name"]
    assert "Exception Leader #5" in fields[14]["value"]
