from __future__ import annotations

import html
from typing import Any, List

import streamlit as st


def render_section_intro(kicker: Any, title: Any, body: Any, chips: List[Any] | None = None) -> None:
    chip_html = ""
    if chips:
        chip_html = '<div class="section-chip-row">' + "".join(
            f'<span class="section-chip">{html.escape(str(chip))}</span>'
            for chip in chips
            if str(chip).strip()
        ) + "</div>"
    st.markdown(
        f"""
        <section class="section-intro">
          <div class="section-kicker">{html.escape(str(kicker))}</div>
          <div class="section-title">{html.escape(str(title))}</div>
          <div class="section-body">{html.escape(str(body))}</div>
          {chip_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner(title: Any, body: Any, tone: str = "good", caption: Any = None) -> None:
    caption_html = (
        f'<div class="status-caption" style="margin-top:0.45rem;">{html.escape(str(caption))}</div>'
        if caption
        else ""
    )
    st.markdown(
        f"""
        <section class="status-banner {html.escape(str(tone))}">
          <div class="status-title">{html.escape(str(title))}</div>
          <div class="status-body">{html.escape(str(body))}</div>
          {caption_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def coerce_text_rows(value: Any, *, limit: int = 4) -> List[str]:
    rows: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key or "").strip()
            item_text = str(item or "").strip()
            if key_text and item_text:
                rows.append(f"{key_text}: {item_text}")
            elif key_text:
                rows.append(key_text)
            elif item_text:
                rows.append(item_text)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                if item.get("label") and item.get("value"):
                    rows.append(f"{item.get('label')}: {item.get('value')}")
                    continue
                if item.get("title") and item.get("summary"):
                    rows.append(f"{item.get('title')}: {item.get('summary')}")
                    continue
                if item.get("signal") and item.get("value") is not None:
                    rows.append(f"{item.get('signal')}: {item.get('value')}")
                    continue
                if item.get("theme_name") and item.get("strength_score") is not None:
                    rows.append(f"{item.get('theme_name')} ({item.get('strength_score')})")
                    continue
                text = " · ".join(str(v).strip() for v in item.values() if str(v).strip())
                if text:
                    rows.append(text)
            else:
                text = str(item or "").strip()
                if text:
                    rows.append(text)
    else:
        text = str(value or "").strip()
        if text:
            rows.append(text)
    deduped: List[str] = []
    for row in rows:
        if row not in deduped:
            deduped.append(row)
    return deduped[:limit]


__all__ = [
    "coerce_text_rows",
    "render_section_intro",
    "render_status_banner",
]
