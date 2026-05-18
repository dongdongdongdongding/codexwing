from multi_agent.tools.run_kr_daily_auto_scans import (
    DISCORD_SAFE_MESSAGE_CHARS,
    _chunk_embeds_for_discord,
    _discord_embed_char_count,
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
