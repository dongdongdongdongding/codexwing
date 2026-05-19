from __future__ import annotations

import html
from typing import Any, Dict, List, Tuple

import streamlit as st

from ui.view_chrome import coerce_text_rows


def theme_tone(direction: Any) -> Tuple[str, str]:
    direction_key = str(direction or "NEUTRAL").upper()
    if direction_key == "BENEFICIARY":
        return "good", "수혜"
    if direction_key == "HEADWIND":
        return "risk", "역풍"
    return "neutral", "중립"


def build_intelligence_highlights(intel_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    highlights: List[Tuple[str, str]] = []
    key_insight = str(intel_data.get("key_insight") or "").strip()
    if key_insight:
        highlights.append(("핵심", key_insight))
    beneficiary = intel_data.get("beneficiary_themes") or []
    headwind = intel_data.get("headwind_themes") or []
    if beneficiary:
        top_names = ", ".join(
            str(row.get("theme_name") or "").strip()
            for row in beneficiary[:3]
            if str(row.get("theme_name") or "").strip()
        )
        if top_names:
            highlights.append(("수혜", f"강하게 받쳐주는 테마는 {top_names} 입니다."))
    if headwind:
        top_names = ", ".join(
            str(row.get("theme_name") or "").strip()
            for row in headwind[:3]
            if str(row.get("theme_name") or "").strip()
        )
        if top_names:
            highlights.append(("역풍", f"부담 요인으로 보이는 테마는 {top_names} 입니다."))
    else:
        highlights.append(("역풍", "뚜렷한 역풍 테마는 아직 크게 보이지 않습니다."))
    risk_rows = coerce_text_rows(intel_data.get("risk_flags"), limit=2)
    if risk_rows:
        highlights.append(("리스크", " / ".join(risk_rows)))
    macro_rows = coerce_text_rows(intel_data.get("macro_drivers"), limit=2)
    if macro_rows:
        highlights.append(("매크로", " / ".join(macro_rows)))
    return highlights[:5]


def render_intelligence_highlights(highlights: List[Tuple[str, str]]) -> None:
    if not highlights:
        return
    rows_html = []
    for label, text in highlights:
        label_text = html.escape(str(label or "").strip())
        body_text = html.escape(str(text or "").strip())
        if not body_text:
            continue
        rows_html.append(
            f"""
            <div class="intel-highlight-item">
              <span class="intel-highlight-badge">{label_text}</span>
              <div class="intel-highlight-text">{body_text}</div>
            </div>
            """
        )
    if rows_html:
        st.markdown('<div class="intel-highlight-list">' + "".join(rows_html) + "</div>", unsafe_allow_html=True)


def render_theme_cards(theme_rows: List[Dict[str, Any]], *, empty_text: str, compact: bool = False) -> None:
    rows = theme_rows or []
    if not rows:
        st.caption(empty_text)
        return
    limit = 3 if compact else 6
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        tone, badge = theme_tone(row.get("direction"))
        strength = float(row.get("strength_score", 0.0) or 0.0)
        confidence = float(row.get("confidence", 0.0) or 0.0)
        momentum = str(row.get("momentum_class") or "").strip()
        evidence_rows = coerce_text_rows(row.get("evidence"), limit=2 if compact else 3)
        evidence_text = " / ".join(evidence_rows) if evidence_rows else "아직 핵심 근거가 구조화되지 않았습니다."
        meta_parts = [
            f"강도 {strength:.1f}",
            f"신뢰 {int(round(confidence * 100))}%",
        ]
        if momentum:
            meta_parts.append(f"모멘텀 {momentum}")
        if row.get("momentum_avg_change_pct") is not None:
            try:
                meta_parts.append(f"평균변화 {float(row.get('momentum_avg_change_pct')):+.2f}%")
            except Exception:
                pass
        st.markdown(
            f"""
            <div class="intel-theme-card {tone}">
              <div class="intel-theme-head">
                <div class="intel-theme-name">{html.escape(str(row.get('theme_name') or '-'))}</div>
                <div class="intel-theme-badge {tone}">{html.escape(badge)}</div>
              </div>
              <div class="intel-theme-meta">{html.escape(' · '.join(meta_parts))}</div>
              <div class="intel-theme-evidence"><strong>핵심 근거</strong>{html.escape(evidence_text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def theme_name_line(rows: List[Dict[str, Any]], limit: int = 5) -> str:
    names: List[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("theme_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return ", ".join(names[:limit])


def intelligence_driver_line(intel_data: Dict[str, Any], *, positive: bool = True, limit: int = 3) -> str:
    labels: List[str] = []
    for row in intel_data.get("macro_drivers", []) or []:
        if not isinstance(row, dict):
            continue
        signal = str(row.get("signal") or "").upper()
        impact = float(row.get("market_impact", 0) or 0)
        if positive and signal in {"BULLISH", "MIXED"} and impact > 0:
            labels.append(str(row.get("category") or "").strip())
        elif (not positive) and signal in {"BEARISH", "MIXED"} and impact < 0:
            labels.append(str(row.get("category") or "").strip())
    deduped: List[str] = []
    for label in labels:
        if label and label not in deduped:
            deduped.append(label)
    return ", ".join(deduped[:limit])


def intelligence_signal_line(intel_data: Dict[str, Any], *, kind: str = "beneficiary", limit: int = 4) -> str:
    if kind == "beneficiary":
        theme_line = theme_name_line(intel_data.get("beneficiary_themes") or [], limit=limit)
        if theme_line:
            return theme_line
        sectors = [str(row).strip() for row in (intel_data.get("beneficiary_sectors") or []) if str(row).strip()]
        if sectors:
            return ", ".join(sectors[:limit])
        driver_line = intelligence_driver_line(intel_data, positive=True, limit=limit)
        if driver_line:
            return driver_line
        return "수급/실적 버팀목 선별 구간"

    theme_line = theme_name_line(intel_data.get("headwind_themes") or [], limit=limit)
    if theme_line:
        return theme_line
    sectors = [str(row).strip() for row in (intel_data.get("victim_sectors") or []) if str(row).strip()]
    if sectors:
        return ", ".join(sectors[:limit])
    risks = [str(row).strip() for row in (intel_data.get("risk_flags") or []) if str(row).strip()]
    if risks:
        return ", ".join(risks[:limit])
    driver_line = intelligence_driver_line(intel_data, positive=False, limit=limit)
    if driver_line:
        return driver_line
    return "과열 추격보다는 리스크 점검 우선"


def intelligence_tactical_line(intel_data: Dict[str, Any]) -> str:
    evidence = coerce_text_rows(intel_data.get("macro_drivers"), limit=1)
    if evidence:
        return evidence[0]
    risk = coerce_text_rows(intel_data.get("risk_flags"), limit=2)
    if risk:
        return f"핵심 경계 요인: {' / '.join(risk)}"
    disclosure = intel_data.get("disclosure_events") or []
    if disclosure and isinstance(disclosure[0], dict):
        first = disclosure[0]
        company = str(first.get("company") or "").strip()
        label = str(first.get("label") or "").strip()
        if company and label:
            return f"{company} {label} 이슈가 단기 심리에 반영되고 있습니다."
    return "시장 전반보다 선별 대응이 중요한 구간입니다."


def build_next_session_theme_line(theme_summary: Dict[str, Any], intel_data: Dict[str, Any]) -> str:
    candidates: List[Tuple[float, str]] = []
    for row in (theme_summary.get("rows", []) if isinstance(theme_summary, dict) else []):
        if not isinstance(row, dict):
            continue
        avg_ret = row.get("avg_day_return_pct")
        strength = float(row.get("strength_score", 0.0) or 0.0)
        positive_ratio = float(row.get("positive_ratio", 0.0) or 0.0)
        score = (float(avg_ret) if avg_ret is not None else -9.0) + (strength * 0.03) + (positive_ratio * 1.2)
        candidates.append((score, str(row.get("theme_name") or "").strip()))
    if not candidates:
        return theme_name_line(intel_data.get("beneficiary_themes") or [], limit=4) or "뚜렷한 선도 테마 없음"
    deduped: List[str] = []
    for _, theme_name in sorted(candidates, reverse=True):
        if theme_name and theme_name not in deduped:
            deduped.append(theme_name)
    return ", ".join(deduped[:4]) if deduped else "뚜렷한 선도 테마 없음"


def build_intelligence_catalysts(intel_data: Dict[str, Any], theme_summary: Dict[str, Any]) -> List[str]:
    rows: List[str] = []
    top_theme_rows = (theme_summary.get("rows", []) if isinstance(theme_summary, dict) else [])[:3]
    for row in top_theme_rows:
        if not isinstance(row, dict):
            continue
        theme_name = str(row.get("theme_name") or "").strip()
        avg_ret = row.get("avg_day_return_pct")
        positive_ratio = row.get("positive_ratio")
        industry = ", ".join(row.get("industry_samples", [])[:2]) if isinstance(row.get("industry_samples"), list) else ""
        if theme_name and avg_ret is not None:
            line = f"{theme_name}: 평균 {float(avg_ret):+.2f}%"
            if positive_ratio is not None:
                line += f", 양봉 비중 {int(round(float(positive_ratio) * 100))}%"
            if industry:
                line += f", 대표 업종 {industry}"
            rows.append(line)
    for event in intel_data.get("disclosure_events", []) or []:
        if not isinstance(event, dict):
            continue
        company = str(event.get("company") or "").strip()
        label = str(event.get("label") or "").strip()
        report_name = str(event.get("report_name") or "").strip()
        if company and label:
            rows.append(f"{company}: {label} 이벤트 반영 ({report_name or '공시'})")
        if len(rows) >= 5:
            break
    for row in intel_data.get("macro_drivers", []) or []:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("description") or "").strip()
        if desc and desc not in rows:
            rows.append(desc)
        if len(rows) >= 5:
            break
    deduped: List[str] = []
    for row in rows:
        if row not in deduped:
            deduped.append(row)
    return deduped[:5]


__all__ = [
    "build_intelligence_catalysts",
    "build_intelligence_highlights",
    "build_next_session_theme_line",
    "intelligence_driver_line",
    "intelligence_signal_line",
    "intelligence_tactical_line",
    "render_intelligence_highlights",
    "render_theme_cards",
    "theme_name_line",
    "theme_tone",
]
