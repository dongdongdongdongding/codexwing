from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from modules.live_scan_context import normalize_market_key
from modules.theme_catalog import load_theme_catalog


def _headline_texts(intel_data: Dict[str, Any]) -> List[str]:
    rows = intel_data.get("raw_headlines") or intel_data.get("evidence_headlines") or []
    return [str(row or "").strip() for row in rows if str(row or "").strip()]


def _score_from_polarity(text: str) -> int:
    lower = text.lower()
    positives = ["상승", "강세", "호조", "수혜", "계약", "수주", "승인", "허가", "반등", "랠리", "surge", "rally", "beat", "strong"]
    negatives = ["하락", "약세", "경고", "리스크", "부담", "증자", "사채", "소송", "관리종목", "drop", "selloff", "risk", "downgrade"]
    pos = sum(1 for token in positives if token in lower)
    neg = sum(1 for token in negatives if token in lower)
    return max(-3, min(3, pos - neg))


def build_theme_intelligence(market: str, intel_data: Dict[str, Any]) -> Dict[str, Any]:
    market_key = normalize_market_key(market)
    catalog = load_theme_catalog(market_key)
    themes = catalog.get("themes", []) if isinstance(catalog, dict) else []
    headlines = _headline_texts(intel_data)
    disclosure_events = intel_data.get("disclosure_events", []) if isinstance(intel_data, dict) else []
    driver_scores = intel_data.get("driver_scores", {}) if isinstance(intel_data, dict) else {}

    states: List[Dict[str, Any]] = []
    evidence_map: Dict[str, List[str]] = {}

    for theme in themes:
        if not isinstance(theme, dict):
            continue
        score = 0.0
        evidence: List[str] = []
        theme_id = str(theme.get("theme_id") or "").strip()
        theme_name = str(theme.get("theme_name") or theme_id).strip()
        aliases = [str(x or "").strip() for x in theme.get("aliases", []) or [] if str(x or "").strip()]
        news_keywords = [str(x or "").strip() for x in theme.get("news_keywords", []) or [] if str(x or "").strip()]
        disclosure_keywords = [str(x or "").strip() for x in theme.get("disclosure_keywords", []) or [] if str(x or "").strip()]

        for row in headlines:
            lower = row.lower()
            hit = False
            for token in aliases + news_keywords:
                if token and token.lower() in lower:
                    score += 10 + (_score_from_polarity(row) * 2)
                    evidence.append(row)
                    hit = True
                    break
            if hit:
                continue

        for event in disclosure_events:
            if not isinstance(event, dict):
                continue
            report_name = str(event.get("report_name") or "")
            lower = report_name.lower()
            theme_specific_disclosure = any(token.lower() in lower for token in aliases + news_keywords)
            if theme_specific_disclosure and any(token.lower() in lower for token in disclosure_keywords):
                try:
                    score += float(event.get("event_score", 0) or 0) * 2.5
                except Exception:
                    score += 0.0
                evidence.append(f"{event.get('company','')} - {report_name}")

        for category in theme.get("driver_categories", []) or []:
            try:
                score += float(driver_scores.get(category, 0) or 0) * 3.0
            except Exception:
                pass

        score = max(-100.0, min(100.0, score))
        if abs(score) < 18.0 and not evidence:
            continue
        if score >= 18:
            direction = "BENEFICIARY"
        elif score <= -18:
            direction = "HEADWIND"
        else:
            direction = "NEUTRAL"

        confidence = min(0.95, 0.35 + min(abs(score), 80.0) / 140.0 + (0.08 if len(evidence) >= 2 else 0.0))
        row = {
            "theme_id": theme_id,
            "theme_name": theme_name,
            "direction": direction,
            "strength_score": round(abs(score), 1),
            "confidence": round(confidence, 3),
            "driver_categories": list(theme.get("driver_categories", []) or []),
            "evidence": sorted(dict.fromkeys(evidence))[:4],
            "beneficiary_keywords": aliases[:6] if direction == "BENEFICIARY" else [],
            "victim_keywords": aliases[:6] if direction == "HEADWIND" else [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        states.append(row)
        evidence_map[theme_id] = row["evidence"]

    states.sort(key=lambda item: (float(item.get("strength_score", 0.0)), float(item.get("confidence", 0.0))), reverse=True)
    beneficiary = [row for row in states if row.get("direction") == "BENEFICIARY"][:8]
    headwind = [row for row in states if row.get("direction") == "HEADWIND"][:8]
    return {
        "theme_states": states,
        "beneficiary_themes": [
            {"theme_id": row["theme_id"], "theme_name": row["theme_name"], "strength_score": row["strength_score"], "confidence": row["confidence"]}
            for row in beneficiary
        ],
        "headwind_themes": [
            {"theme_id": row["theme_id"], "theme_name": row["theme_name"], "strength_score": row["strength_score"], "confidence": row["confidence"]}
            for row in headwind
        ],
        "theme_evidence": evidence_map,
    }


def theme_state_lookup(intel_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    rows = intel_data.get("theme_states", []) if isinstance(intel_data, dict) else []
    lookup: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        theme_id = str(row.get("theme_id") or "").strip()
        theme_name = str(row.get("theme_name") or "").strip()
        if theme_id:
            lookup[theme_id] = row
        if theme_name:
            lookup[theme_name] = row
    return lookup


def write_theme_cache(market: str, payload: Dict[str, Any]) -> None:
    market_key = normalize_market_key(market)
    base = Path("runtime_state") / "long_term" / "theme_cache"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{market_key}.json"
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
