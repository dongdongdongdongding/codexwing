import urllib.error

from multi_agent.tools.run_kr_daily_auto_scans import (
    DISCORD_MAX_CONTENT_CHARS,
    DISCORD_SAFE_MESSAGE_CHARS,
    POST_SCAN_VALIDATION_COMMANDS,
    _chunk_embeds_for_discord,
    _discord_backoff_seconds,
    _discord_retry_after,
    _discord_embed_char_count,
    _embed_to_content_chunks,
    _markdown_validation_excerpt,
    _parse_last_json_line,
    _prepare_embeds_for_discord,
    _scan_targets,
    _validation_embed,
)


def test_discord_embed_chunking_respects_aggregate_character_budget():
    embeds = [
        {
            "title": f"embed-{idx}",
            "description": "x" * 1800,
            "fields": [{"name": "field", "value": "y" * 900}],
        }
        for idx in range(4)
    ]

    chunks = _chunk_embeds_for_discord(embeds)

    assert len(chunks) > 1
    assert sum(len(chunk) for chunk in chunks) == len(embeds)
    for chunk in chunks:
        assert sum(_discord_embed_char_count(embed) for embed in chunk) <= DISCORD_SAFE_MESSAGE_CHARS


def test_discord_embed_preparation_splits_and_clips_oversized_embeds():
    embeds = [
        {
            "title": "t" * 400,
            "description": "d" * 5000,
            "fields": [
                {"name": f"field-{idx}" * 50, "value": "v" * 5000, "inline": False}
                for idx in range(30)
            ],
        }
    ]

    prepared = _prepare_embeds_for_discord(embeds)

    assert len(prepared) > 1
    for embed in prepared:
        assert len(embed.get("title") or "") <= 256
        assert len(embed.get("description") or "") <= 4096
        assert len(embed.get("fields") or []) <= 25
        assert _discord_embed_char_count(embed) <= DISCORD_SAFE_MESSAGE_CHARS
        for field in embed.get("fields") or []:
            assert len(field.get("name") or "") <= 256
            assert len(field.get("value") or "") <= 1024


def test_discord_embed_text_fallback_chunks_under_content_limit():
    embed = {
        "title": "자동 스캔 완료",
        "description": "d" * 3000,
        "fields": [{"name": "결과", "value": "v" * 5000}],
    }

    chunks = _embed_to_content_chunks(embed)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= DISCORD_MAX_CONTENT_CHARS for chunk in chunks)
    assert chunks[0].startswith("**자동 스캔 완료**")


def test_discord_retry_after_reads_header_and_json_body():
    header_exc = urllib.error.HTTPError(
        "https://discord.test",
        429,
        "rate limited",
        {"Retry-After": "1.25"},
        None,
    )
    body_exc = urllib.error.HTTPError("https://discord.test", 429, "rate limited", {}, None)

    assert _discord_retry_after(header_exc, "{}") == 1.25
    assert _discord_retry_after(body_exc, '{"retry_after": 0.53}') == 0.53


def test_discord_backoff_has_conservative_floor():
    assert _discord_backoff_seconds(0.3, 0) >= 1.5
    assert _discord_backoff_seconds(2.0, 2) > 2.0


def test_daily_auto_scan_targets_include_intraday_observers(monkeypatch):
    monkeypatch.delenv("AG_KR_DAILY_SCAN_TARGETS", raising=False)

    assert _scan_targets() == [
        ("KOSPI", "SWING"),
        ("KOSDAQ", "SWING"),
        ("KOSPI", "INTRADAY"),
        ("KOSDAQ", "INTRADAY"),
    ]


def test_daily_auto_scan_targets_can_be_overridden(monkeypatch):
    monkeypatch.setenv("AG_KR_DAILY_SCAN_TARGETS", "KOSPI:SWING,KOSDAQ/SWING,KOSPI:SWING,bad")

    assert _scan_targets() == [("KOSPI", "SWING"), ("KOSDAQ", "SWING")]


def test_post_scan_validation_json_parser_reads_last_json_line():
    text = "noise\n{\"json\":\"a.json\",\"md\":\"a.md\"}\nother\n{\"segments\":8}\n"

    assert _parse_last_json_line(text) == {"segments": 8}


def test_post_scan_validation_json_parser_reads_pretty_json_tail():
    text = "warning\n{\n  \"json_path\": \"a.json\",\n  \"md_path\": \"a.md\",\n  \"segments\": 8\n}\n"

    assert _parse_last_json_line(text) == {"json_path": "a.json", "md_path": "a.md", "segments": 8}


def test_validation_embed_summarizes_post_scan_reports():
    embed = _validation_embed(
        {
            "generated_at": "now",
            "ok": False,
            "results": [
                {
                    "name": "Segment Top5 Validation",
                    "ok": False,
                    "returncode": 1,
                    "json_path": "runtime_state/reports/validation/segment_top5_validation.json",
                    "md_path": "runtime_state/reports/validation/segment_top5_validation.md",
                    "summary": "### KOSPI:SWING\n- recent top5 positive-rate: 60.00%",
                }
            ],
        }
    )

    assert embed["title"] == "스캔 후 자동 검증"
    assert embed["color"] == 0xE67E22
    assert "recent top5 positive-rate" in embed["fields"][0]["value"]


def test_validation_embed_keeps_all_registered_validation_fields():
    results = [
        {
            "name": f"Validation {idx}",
            "ok": True,
            "returncode": 0,
            "summary": f"summary {idx}",
        }
        for idx in range(len(POST_SCAN_VALIDATION_COMMANDS))
    ]

    embed = _validation_embed({"generated_at": "now", "ok": True, "results": results})

    assert len(embed["fields"]) == len(POST_SCAN_VALIDATION_COMMANDS)
    assert embed["fields"][-1]["name"] == f"Validation {len(POST_SCAN_VALIDATION_COMMANDS) - 1}"


def test_validation_embed_marks_existing_summary_fallback_as_degraded():
    embed = _validation_embed(
        {
            "generated_at": "now",
            "ok": True,
            "degraded": True,
            "results": [
                {
                    "name": "Segment Top5 Validation",
                    "ok": False,
                    "degraded": True,
                    "warning": "command_failed_existing_markdown_summary_used",
                    "returncode": 1,
                    "summary": "- recent top5 positive-rate: 80.00%",
                }
            ],
        }
    )

    assert embed["color"] == 0xF1C40F
    assert "DEGRADED" in embed["fields"][0]["value"]
    assert "existing_markdown" in embed["fields"][0]["value"]


def test_markdown_validation_excerpt_prefers_metrics_over_definitions(tmp_path):
    path = tmp_path / "scan_cohort_performance.md"
    path.write_text(
        "\n".join(
            [
                "# Scan Cohort Performance",
                "## Definitions",
                "- Top1: `priority_rank == 1`",
                "- Top5: `priority_rank between 1 and 5`",
                "## KOSPI",
                "| Cohort | 1D | 3D | 5D | Path Quality |",
                "|---|---:|---:|---:|---:|",
                "| Top1 | n=1 / win 100.0% / avg +1.00% / min +1.00% / max +1.00% | - | - | - |",
                "| Practical 80 Gate | n=1 / win 100.0% / avg +2.00% / min +2.00% / max +2.00% | - | - | - |",
            ]
        ),
        encoding="utf-8",
    )

    excerpt = _markdown_validation_excerpt(path)

    assert "priority_rank" not in excerpt
    assert "| Top1 |" in excerpt
    assert "Practical 80 Gate" in excerpt


def test_post_scan_validation_includes_loss_exclusion_guard_watch():
    names = [spec["name"] for spec in POST_SCAN_VALIDATION_COMMANDS]

    assert "Live Policy Observed" in names
    assert "Live Policy Strict" in names
    assert "Loss Exclusion Guard Watch" in names
    assert "Ordered Shadow Watch" in names
    assert "Exact Path Feature Watch" in names
    assert "Exact Path Feature Watch Strict" in names
    assert "Pinned Feature Combo Watch" in names
    assert "INTRADAY Learning Readiness" in names
    assert "INTRADAY Model Viability" in names
    assert "INTRADAY Loss Guard Watch" in names


def test_markdown_validation_excerpt_includes_guard_watch_rows(tmp_path):
    path = tmp_path / "loss_exclusion_guard_watch_latest.md"
    path.write_text(
        "\n".join(
            [
                "# Loss Exclusion Guard Mining",
                "## Top Exclusion Guards",
                "| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin |",
                "|---:|---|---|---|---|---:|---:|---:|---:|---:|",
                "| 1 | shadow_candidate | KOSDAQ | exception_leader | 3d | 2 | 0.3684 | 36.842 | 71.429 | 34.587 |",
                "## Notes",
                "- Internal research only.",
            ]
        ),
        encoding="utf-8",
    )

    excerpt = _markdown_validation_excerpt(path)

    assert "shadow_candidate" in excerpt
    assert "KOSDAQ" in excerpt


def test_markdown_validation_excerpt_includes_feature_combo_refinements(tmp_path):
    path = tmp_path / "feature_combo_watchlist_latest.md"
    path.write_text(
        "\n".join(
            [
                "# Feature Combo Watchlist",
                "## Refinement Candidates",
                "| Condition | Status | Score | Train | Test |",
                "|---|---|---:|---:|---:|",
                "| decision_score >= 60.5 | watch_refinement_candidate | 216.3 | n=16 win5=81.25% drop1d=6.25% | n=6 win5=100.0% bad=0.0% drop1d=0.0% loss5=0.0% |",
            ]
        ),
        encoding="utf-8",
    )

    excerpt = _markdown_validation_excerpt(path)

    assert "watch_refinement_candidate" in excerpt
    assert "drop1d=0.0%" in excerpt
