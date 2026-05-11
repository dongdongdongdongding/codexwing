"""재사용 가능한 UI 컴포넌트.

3-depth 정보 구조에 맞게 작은 헬퍼들을 모아둔다.

* L0 — ``compact_status_bar`` : 상단 한 줄에 Macro/Gate/Market 등을 통합 표시
* L1 — ``kpi_strip`` : 탭 진입 시 4~6 개 지표 카드 가로 배치
* 공통 — ``section_intro`` / ``status_banner`` : 기존 호출과 호환되는 헤더/배너

이 모듈은 Streamlit의 ``st.markdown`` 만 사용한다. 로직(데이터 가공)은 절대 포함하지
않고, 호출부에서 만들어진 dict 리스트를 받아 HTML 로 렌더한다.
"""

from __future__ import annotations

import html
from typing import Iterable, Mapping, Sequence

import streamlit as st


_VALID_TONES = {"good", "caution", "risk", "danger", "focus", "neutral", ""}


def _tone(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text if text in _VALID_TONES else ""


def section_intro(
    kicker: str,
    title: str,
    body: str,
    chips: Sequence[str] | None = None,
) -> None:
    """L1 섹션 진입 헤더(기존 ``_render_section_intro`` 와 동일 스타일)."""

    chip_html = ""
    if chips:
        chip_html = '<div class="section-chip-row">' + "".join(
            f'<span class="section-chip">{html.escape(str(chip))}</span>'
            for chip in chips
            if str(chip).strip()
        ) + "</div>"
    st.markdown(
        f'<section class="section-intro">'
        f'<div class="section-kicker">{html.escape(str(kicker))}</div>'
        f'<div class="section-title">{html.escape(str(title))}</div>'
        f'<div class="section-body">{html.escape(str(body))}</div>'
        f'{chip_html}'
        f'</section>',
        unsafe_allow_html=True,
    )


def status_banner(
    title: str,
    body: str,
    tone: str = "good",
    caption: str | None = None,
) -> None:
    """기존 status banner 와 동일. tone: good / caution / risk / danger."""

    caption_html = (
        f'<div class="status-caption" style="margin-top:0.45rem;">{html.escape(str(caption))}</div>'
        if caption
        else ""
    )
    st.markdown(
        f'<section class="status-banner {html.escape(_tone(tone) or "good")}">'
        f'<div class="status-title">{html.escape(str(title))}</div>'
        f'<div class="status-body">{html.escape(str(body))}</div>'
        f'{caption_html}'
        f'</section>',
        unsafe_allow_html=True,
    )


def compact_status_bar(items: Iterable[Mapping[str, str]]) -> None:
    """L0 한 줄 상태바. 각 item 은 dict::

        {"label": "MACRO", "value": "☀️ NORMAL", "meta": "Risk 12/100", "tone": "good"}

    label/value 만 필수. meta/tone 은 옵션. 주문 순서대로 좌→우 배치된다.
    """

    pills: list[str] = []
    for raw in items or []:
        if not isinstance(raw, Mapping):
            continue
        label = str(raw.get("label") or "").strip()
        value = str(raw.get("value") or "").strip()
        if not value:
            continue
        meta = str(raw.get("meta") or "").strip()
        tone_class = _tone(raw.get("tone"))
        meta_html = (
            f'<div class="compact-status-meta">{html.escape(meta)}</div>'
            if meta
            else ""
        )
        label_html = (
            f'<div class="compact-status-label">{html.escape(label)}</div>'
            if label
            else ""
        )
        pills.append(
            f'<div class="compact-status-pill {tone_class}">'
            f'{label_html}'
            f'<div class="compact-status-value">{html.escape(value)}</div>'
            f'{meta_html}'
            f'</div>'
        )
    if not pills:
        return
    st.markdown(
        '<div class="compact-status">' + "".join(pills) + "</div>",
        unsafe_allow_html=True,
    )


def kpi_strip(items: Iterable[Mapping[str, str]]) -> None:
    """L1 KPI 카드 스트립. 각 item ::

        {"label": "PICKED", "value": "12", "delta": "+2 vs prev", "tone": "good", "delta_tone": "pos"}

    tone: 카드 외곽 색 (good/risk/focus). delta_tone: pos/neg/(빈값).
    """

    cards: list[str] = []
    for raw in items or []:
        if not isinstance(raw, Mapping):
            continue
        label = str(raw.get("label") or "").strip()
        value = str(raw.get("value") or "").strip()
        if value == "":
            continue
        delta = str(raw.get("delta") or "").strip()
        tone_class = _tone(raw.get("tone"))
        value_tone = str(raw.get("value_tone") or "").strip().lower()
        value_tone_class = value_tone if value_tone in {"pos", "neg"} else ""
        delta_tone = str(raw.get("delta_tone") or "").strip().lower()
        delta_tone_class = delta_tone if delta_tone in {"pos", "neg"} else ""
        delta_html = (
            f'<div class="kpi-delta {delta_tone_class}">{html.escape(delta)}</div>'
            if delta
            else ""
        )
        cards.append(
            f'<div class="kpi-card {tone_class}">'
            f'<div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value {value_tone_class}">{html.escape(value)}</div>'
            f'{delta_html}'
            f'</div>'
        )
    if not cards:
        return
    st.markdown(
        '<div class="kpi-strip">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def detail_grid_hint(text: str) -> None:
    """L2 상세 그리드 위에 붙이는 짧은 안내 캡션."""

    if not text:
        return
    st.markdown(
        f'<div class="detail-grid-hint">{html.escape(str(text))}</div>',
        unsafe_allow_html=True,
    )


__all__ = [
    "compact_status_bar",
    "detail_grid_hint",
    "kpi_strip",
    "section_intro",
    "status_banner",
]
