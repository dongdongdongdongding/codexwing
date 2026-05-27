from __future__ import annotations

from typing import Any, Dict, List


MAX_EMBEDS_PER_MESSAGE = 10
MAX_MESSAGE_CHARS = 6000
SAFE_MESSAGE_CHARS = 4800
MAX_EMBED_TITLE_CHARS = 256
MAX_EMBED_DESCRIPTION_CHARS = 4096
MAX_EMBED_FIELD_NAME_CHARS = 256
MAX_EMBED_FIELD_VALUE_CHARS = 1024
MAX_CONTENT_CHARS = 2000


def prepare_embeds_for_discord(embeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    safe: List[Dict[str, Any]] = []
    for embed in embeds or []:
        safe.extend(split_embed_for_discord(embed))
    return safe


def chunk_embeds_for_discord(embeds: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_chars = 0
    for embed in embeds or []:
        embed_chars = discord_embed_char_count(embed)
        if embed_chars > SAFE_MESSAGE_CHARS:
            for split_embed in split_embed_for_discord(embed):
                chunks.extend(chunk_embeds_for_discord([split_embed]))
            continue
        if current and (
            len(current) >= MAX_EMBEDS_PER_MESSAGE
            or current_chars + embed_chars > SAFE_MESSAGE_CHARS
        ):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(embed)
        current_chars += embed_chars
    if current:
        chunks.append(current)
    return chunks


def split_embed_for_discord(embed: Dict[str, Any]) -> List[Dict[str, Any]]:
    base = embed_base_for_discord(embed)
    base_chars = discord_embed_char_count({**base, "fields": []})
    if base_chars > SAFE_MESSAGE_CHARS:
        non_desc_chars = base_chars - len(str(base.get("description") or ""))
        available_desc = max(0, SAFE_MESSAGE_CHARS - non_desc_chars)
        base["description"] = clip_text(base.get("description"), available_desc)

    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    normalized_fields = [field_for_discord(field) for field in fields if isinstance(field, dict)]
    if not normalized_fields:
        return [{**base, "fields": []}]

    pages: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []
    for field in normalized_fields:
        fitted = fit_single_field(base, field)
        candidate_fields = current + [fitted]
        candidate = {**base, "fields": candidate_fields}
        if current and (
            len(candidate_fields) > 25
            or discord_embed_char_count(candidate) > SAFE_MESSAGE_CHARS
        ):
            pages.append({**base, "fields": current[:25]})
            current = []
        current.append(fitted)
    if current:
        pages.append({**base, "fields": current[:25]})
    return pages


def embed_base_for_discord(embed: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(embed)
    safe["title"] = clip_text(safe.get("title"), MAX_EMBED_TITLE_CHARS)
    safe["description"] = clip_text(safe.get("description"), MAX_EMBED_DESCRIPTION_CHARS)
    footer = safe.get("footer") if isinstance(safe.get("footer"), dict) else None
    if footer:
        safe["footer"] = {**footer, "text": clip_text(footer.get("text"), 2048)}
    author = safe.get("author") if isinstance(safe.get("author"), dict) else None
    if author:
        safe["author"] = {**author, "name": clip_text(author.get("name"), 256)}
    safe.pop("fields", None)
    return safe


def field_for_discord(field: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": clip_text(field.get("name"), MAX_EMBED_FIELD_NAME_CHARS) or "-",
        "value": clip_text(field.get("value"), MAX_EMBED_FIELD_VALUE_CHARS) or "-",
        "inline": bool(field.get("inline", False)),
    }


def fit_single_field(base: Dict[str, Any], field: Dict[str, Any]) -> Dict[str, Any]:
    candidate = {**base, "fields": [field]}
    if discord_embed_char_count(candidate) <= SAFE_MESSAGE_CHARS:
        return field
    base_chars = discord_embed_char_count({**base, "fields": []})
    name_len = len(str(field.get("name") or ""))
    available = max(1, SAFE_MESSAGE_CHARS - base_chars - name_len)
    clipped = dict(field)
    clipped["value"] = clip_text(clipped.get("value"), min(MAX_EMBED_FIELD_VALUE_CHARS, available))
    return clipped


def embed_to_content_chunks(embed: Dict[str, Any]) -> List[str]:
    title = str(embed.get("title") or "Discord embed fallback")
    description = str(embed.get("description") or "").strip()
    lines = [f"**{title}**"]
    if description:
        lines.append(description)
    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "-").strip() or "-"
        value = str(field.get("value") or "-").strip() or "-"
        lines.append(f"{name}: {value}")
    text = "\n".join(lines)
    chunks: List[str] = []
    while text:
        chunks.append(clip_text(text, MAX_CONTENT_CHARS))
        if len(text) <= MAX_CONTENT_CHARS:
            break
        text = text[MAX_CONTENT_CHARS - 1 :].lstrip()
    return chunks or ["자동 스캔 결과 요약을 생성하지 못했습니다."]


def clip_text(value: Any, limit: int) -> str:
    text = str(value or "")
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1] + "…"


def discord_embed_char_count(embed: Dict[str, Any]) -> int:
    total = len(str(embed.get("title") or "")) + len(str(embed.get("description") or ""))
    footer = embed.get("footer") if isinstance(embed.get("footer"), dict) else {}
    author = embed.get("author") if isinstance(embed.get("author"), dict) else {}
    total += len(str(footer.get("text") or "")) + len(str(author.get("name") or ""))
    fields = embed.get("fields") if isinstance(embed.get("fields"), list) else []
    for field in fields:
        if isinstance(field, dict):
            total += len(str(field.get("name") or "")) + len(str(field.get("value") or ""))
    return total


__all__ = [
    "MAX_CONTENT_CHARS",
    "SAFE_MESSAGE_CHARS",
    "chunk_embeds_for_discord",
    "clip_text",
    "discord_embed_char_count",
    "embed_to_content_chunks",
    "prepare_embeds_for_discord",
    "split_embed_for_discord",
]
