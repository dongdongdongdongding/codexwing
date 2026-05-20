from multi_agent.tools.run_kr_daily_auto_scans import (
    DISCORD_SAFE_MESSAGE_CHARS,
    _chunk_embeds_for_discord,
    _discord_embed_char_count,
    _prepare_embeds_for_discord,
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
