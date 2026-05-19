from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple


EXPOSURE_CONTRACT_VERSION = "portfolio_exposure_v1"


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _num(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        return float(value)
    except Exception:
        return None


def _nested(row: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def _section(row: Dict[str, Any]) -> str:
    alignment = _nested(row, "selection_alignment")
    return _text(row.get("_analysis_section") or alignment.get("analysis_section") or row.get("section"), "Top5")


def _market(row: Dict[str, Any]) -> str:
    ticker = _text(row.get("ticker") or row.get("Ticker") or row.get("symbol") or row.get("티커")).upper()
    market = _text(row.get("market") or row.get("Market") or row.get("market_subtype")).upper()
    if market:
        return market
    if ticker.endswith(".KS"):
        return "KOSPI"
    if ticker.endswith(".KQ"):
        return "KOSDAQ"
    return "UNKNOWN"


def _theme(row: Dict[str, Any]) -> str:
    theme = _nested(row, "theme")
    context = _nested(row, "theme_context")
    return _text(
        theme.get("primary_theme")
        or row.get("primary_theme")
        or row.get("primary_theme_archive")
        or row.get("Theme")
        or row.get("테마")
        or context.get("primary_theme"),
        "UNCLASSIFIED",
    )


def _risk_band(row: Dict[str, Any]) -> str:
    loss = _num(row.get("loss_risk_score") or row.get("Loss Risk"))
    if loss is None:
        readiness = _nested(_nested(row, "trade_plan"), "readiness_analysis")
        level = _text(readiness.get("chase_risk_level") or row.get("chase_risk_level")).lower()
        if "very" in level or "매우" in level or "high" in level or "높" in level:
            return "high"
        if "medium" in level or "보통" in level:
            return "medium"
        if "low" in level or "낮" in level:
            return "low"
        return "unknown"
    if loss >= 65:
        return "high"
    if loss >= 45:
        return "medium"
    return "low"


def _flow_direction(row: Dict[str, Any]) -> str:
    flow = _nested(row, "flow")
    foreigner = _num(flow.get("foreigner_1d", flow.get("foreigner")) or row.get("foreigner_1d") or row.get("foreigner"))
    institution = _num(flow.get("institution_1d", flow.get("institution")) or row.get("institution_1d") or row.get("institution"))
    if foreigner is None and institution is None:
        whale = _num(flow.get("whale_flow_1d", flow.get("whale_flow")) or row.get("whale_flow_1d") or row.get("whale_flow"))
    else:
        whale = (foreigner or 0.0) + (institution or 0.0)
    if whale is None:
        return "unknown"
    if whale > 0:
        return "foreign_institution_buy"
    if whale < 0:
        return "foreign_institution_sell"
    return "flat"


def _top_counts(counter: Counter[str], total: int, *, limit: int = 5) -> List[Dict[str, Any]]:
    rows = []
    for label, count in counter.most_common(limit):
        rows.append(
            {
                "label": label,
                "count": int(count),
                "share_pct": round((float(count) / float(total) * 100.0), 2) if total else 0.0,
            }
        )
    return rows


def _dominant(counter: Counter[str], total: int) -> Dict[str, Any]:
    if not counter or total <= 0:
        return {"label": "", "count": 0, "share_pct": 0.0}
    label, count = counter.most_common(1)[0]
    return {
        "label": label,
        "count": int(count),
        "share_pct": round(float(count) / float(total) * 100.0, 2),
    }


def build_portfolio_exposure_summary(rows: Iterable[Dict[str, Any]], *, run_id: str = "") -> Dict[str, Any]:
    clean_rows = [row for row in rows or [] if isinstance(row, dict)]
    total = len(clean_rows)
    markets: Counter[str] = Counter()
    sections: Counter[str] = Counter()
    themes: Counter[str] = Counter()
    risk_bands: Counter[str] = Counter()
    flow_directions: Counter[str] = Counter()
    theme_sections: Dict[str, Counter[str]] = defaultdict(Counter)
    theme_risk: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in clean_rows:
        market = _market(row)
        section = _section(row)
        theme = _theme(row)
        risk = _risk_band(row)
        flow = _flow_direction(row)
        markets[market] += 1
        sections[section] += 1
        themes[theme] += 1
        risk_bands[risk] += 1
        flow_directions[flow] += 1
        theme_sections[theme][section] += 1
        theme_risk[theme][risk] += 1

    dominant_theme = _dominant(themes, total)
    crowded_themes = [row for row in _top_counts(themes, total) if row["count"] >= 2]
    high_risk_count = int(risk_bands.get("high", 0))
    sell_flow_count = int(flow_directions.get("foreign_institution_sell", 0))
    warnings: List[str] = []
    interpretation = "diversified_or_insufficient_rows"
    if total == 0:
        warnings.append("NO_CANDIDATES")
        interpretation = "no_candidates"
    else:
        if dominant_theme.get("share_pct", 0.0) >= 50.0 and dominant_theme.get("count", 0) >= 2:
            warnings.append("THEME_CROWDED")
            interpretation = "same_theme_crowded"
        if high_risk_count / total >= 0.4:
            warnings.append("LOSS_RISK_CLUSTER")
        if sell_flow_count / total >= 0.4:
            warnings.append("FLOW_SELL_CLUSTER")
        if len(markets) == 1 and total >= 5:
            warnings.append("SINGLE_MARKET_BETA")

    theme_details = []
    for theme_row in _top_counts(themes, total):
        label = str(theme_row["label"])
        theme_details.append(
            {
                **theme_row,
                "sections": dict(theme_sections.get(label, {})),
                "risk_bands": dict(theme_risk.get(label, {})),
            }
        )

    return {
        "version": EXPOSURE_CONTRACT_VERSION,
        "run_id": str(run_id or ""),
        "candidate_count": total,
        "market_counts": dict(markets),
        "section_counts": dict(sections),
        "theme_counts": dict(themes),
        "risk_band_counts": dict(risk_bands),
        "flow_direction_counts": dict(flow_directions),
        "dominant_theme": dominant_theme,
        "crowded_themes": crowded_themes,
        "theme_details": theme_details,
        "risk_flags": warnings,
        "interpretation": interpretation,
        "operator_note": _operator_note(interpretation, warnings, dominant_theme, total),
    }


def _operator_note(interpretation: str, warnings: List[str], dominant_theme: Dict[str, Any], total: int) -> str:
    if total <= 0:
        return "표시 후보가 없어 포트폴리오 노출을 계산할 수 없습니다."
    parts = []
    if interpretation == "same_theme_crowded":
        parts.append(
            f"동일 테마 쏠림: {dominant_theme.get('label')} "
            f"{dominant_theme.get('count')}개({dominant_theme.get('share_pct')}%)."
        )
    else:
        parts.append("후보 간 테마 쏠림은 제한적입니다.")
    if "LOSS_RISK_CLUSTER" in warnings:
        parts.append("손실위험 high 후보가 묶여 있어 동시 진입 리스크를 확인해야 합니다.")
    if "FLOW_SELL_CLUSTER" in warnings:
        parts.append("외인+기관 당일 순매도 후보가 많아 수급 역풍을 확인해야 합니다.")
    if "SINGLE_MARKET_BETA" in warnings:
        parts.append("단일 시장 후보만 있어 시장 베타에 함께 노출됩니다.")
    return " ".join(parts)


def render_portfolio_exposure_lines(summary: Dict[str, Any], *, max_themes: int = 3) -> List[str]:
    if not isinstance(summary, dict) or not summary:
        return ["포트폴리오 노출: 없음"]
    lines = [
        f"후보 {summary.get('candidate_count', 0)}개 · {summary.get('interpretation') or '-'}",
        str(summary.get("operator_note") or "-"),
    ]
    dominant = summary.get("dominant_theme") if isinstance(summary.get("dominant_theme"), dict) else {}
    if dominant:
        lines.append(
            f"주요 테마: {dominant.get('label') or '-'} "
            f"{dominant.get('count', 0)}개({dominant.get('share_pct', 0)}%)"
        )
    risk = summary.get("risk_band_counts") if isinstance(summary.get("risk_band_counts"), dict) else {}
    flow = summary.get("flow_direction_counts") if isinstance(summary.get("flow_direction_counts"), dict) else {}
    lines.append(f"손실위험: high {risk.get('high', 0)} / mid {risk.get('medium', 0)} / low {risk.get('low', 0)}")
    lines.append(
        "수급방향: "
        f"외+기 매수 {flow.get('foreign_institution_buy', 0)} / "
        f"매도 {flow.get('foreign_institution_sell', 0)} / "
        f"미확보 {flow.get('unknown', 0)}"
    )
    themes = summary.get("theme_details") if isinstance(summary.get("theme_details"), list) else []
    if themes:
        theme_bits = [f"{row.get('label')} {row.get('count')}개" for row in themes[:max_themes]]
        lines.append("테마분포: " + " · ".join(theme_bits))
    flags = summary.get("risk_flags") if isinstance(summary.get("risk_flags"), list) else []
    if flags:
        lines.append("노출경고: " + ", ".join(str(flag) for flag in flags[:5]))
    return lines


__all__ = [
    "EXPOSURE_CONTRACT_VERSION",
    "build_portfolio_exposure_summary",
    "render_portfolio_exposure_lines",
]
