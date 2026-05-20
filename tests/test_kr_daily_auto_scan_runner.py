from multi_agent.tools.run_kr_daily_auto_scans import (
    DISCORD_MAX_CONTENT_CHARS,
    DISCORD_SAFE_MESSAGE_CHARS,
    _chunk_embeds_for_discord,
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


def test_daily_auto_scan_targets_include_kospi_intraday_observer(monkeypatch):
    monkeypatch.delenv("AG_KR_DAILY_SCAN_TARGETS", raising=False)

    assert _scan_targets() == [("KOSPI", "SWING"), ("KOSDAQ", "SWING"), ("KOSPI", "INTRADAY")]


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
