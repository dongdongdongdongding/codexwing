"""US overnight theme leadership for KR pre-open ranking.

This module converts the latest completed US daily session into theme states,
then projects them onto KR themes through ``modules.theme_transfer``.  It is a
context feature only: it never creates labels, never blocks recommendations, and
never uses KR same-day prices.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Tuple

import pandas as pd

from modules.market_data import get_history
from modules.theme_catalog import THEME_CANONICAL_MAP
from modules.theme_transfer import build_transfer_artifact, load_transfer_artifact, project_kr_priors


ProxyFetcher = Callable[..., pd.DataFrame]


US_THEME_PROXY_BASKETS: Dict[str, Dict[str, Any]] = {
    "korea_beta": {
        "theme_name": "Korea Beta",
        "symbols": ["EWY", "KORU"],
        "note": "US-listed Korea ETFs; KORU is leveraged and used only as direction/risk-amplification evidence.",
    },
    "semiconductor": {
        "theme_name": "Semiconductor/HBM",
        "symbols": ["SOXX", "SMH", "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML"],
    },
    "ai_datacenter": {
        "theme_name": "AI Datacenter",
        "symbols": ["QQQ", "NVDA", "AVGO", "MSFT", "PLTR", "ORCL"],
    },
    "quantum": {
        "theme_name": "Quantum",
        "symbols": ["QTUM", "IONQ", "RGTI", "QBTS", "QUBT"],
    },
    "robotics": {
        "theme_name": "Robotics/Automation",
        "symbols": ["BOTZ", "ROBO", "ISRG", "TER", "PATH", "SYM"],
    },
    "biotech": {
        "theme_name": "Biotech/Healthcare",
        "symbols": ["XBI", "IBB", "XLV", "MRNA", "REGN", "VRTX"],
    },
    "defense": {
        "theme_name": "Defense/Aerospace",
        "symbols": ["ITA", "XAR", "LMT", "RTX", "NOC", "GD"],
    },
    "nuclear": {
        "theme_name": "Nuclear/Power",
        "symbols": ["URA", "NLR", "CCJ", "BWXT", "SMR"],
    },
    "power_grid": {
        "theme_name": "Power Grid/Infrastructure",
        "symbols": ["PAVE", "GRID", "ETN", "GEV", "VRT"],
    },
    "secondary_battery": {
        "theme_name": "Battery/EV",
        "symbols": ["LIT", "TSLA", "ALB", "QS", "RIVN"],
    },
    "automobile": {
        "theme_name": "Auto/Mobility",
        "symbols": ["CARZ", "TSLA", "GM", "F", "RIVN"],
    },
    "crypto": {
        "theme_name": "Crypto/Blockchain",
        "symbols": ["IBIT", "COIN", "MSTR", "MARA", "RIOT"],
    },
    "finance": {
        "theme_name": "Financials",
        "symbols": ["XLF", "KBE", "JPM", "BAC", "GS"],
    },
}


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        out = float(value)
        if pd.isna(out):
            return None
        return out
    except Exception:
        return None


def _last_daily_return(hist: pd.DataFrame) -> Dict[str, Any]:
    if hist is None or hist.empty or "Close" not in hist.columns:
        return {"available": False}
    work = hist.copy()
    work["Close"] = pd.to_numeric(work["Close"], errors="coerce")
    if "Volume" in work.columns:
        work["Volume"] = pd.to_numeric(work["Volume"], errors="coerce")
    work = work.dropna(subset=["Close"])
    if len(work) < 2:
        return {"available": False}
    prev_close = _safe_float(work["Close"].iloc[-2])
    last_close = _safe_float(work["Close"].iloc[-1])
    if prev_close is None or last_close is None or prev_close <= 0:
        return {"available": False}
    last_idx = work.index[-1]
    last_date = last_idx.date().isoformat() if hasattr(last_idx, "date") else str(last_idx)[:10]
    volume_ratio = None
    if "Volume" in work.columns and len(work) >= 6:
        recent = pd.to_numeric(work["Volume"].iloc[-6:-1], errors="coerce").dropna()
        last_volume = _safe_float(work["Volume"].iloc[-1])
        if last_volume is not None and not recent.empty and float(recent.mean()) > 0:
            volume_ratio = round(float(last_volume) / float(recent.mean()), 3)
    return {
        "available": True,
        "last_trade_date": last_date,
        "return_1d_pct": round(((last_close / prev_close) - 1.0) * 100.0, 4),
        "close": round(last_close, 6),
        "volume_ratio_5d": volume_ratio,
    }


def _direction_from_return(avg_return: float, hit_ratio: float) -> str:
    if avg_return >= 0.8 and hit_ratio >= 0.45:
        return "BENEFICIARY"
    if avg_return <= -0.8 and hit_ratio <= 0.55:
        return "HEADWIND"
    return "NEUTRAL"


def _strength_score(avg_return: float, hit_ratio: float, max_abs_return: float, avg_volume_ratio: float | None) -> float:
    breadth = abs(hit_ratio - 0.5) * 40.0
    move = min(55.0, abs(avg_return) * 7.5)
    leader = min(25.0, max_abs_return * 2.0)
    volume = 0.0
    if avg_volume_ratio is not None:
        volume = min(15.0, max(0.0, avg_volume_ratio - 1.0) * 10.0)
    return round(min(100.0, move + leader + breadth + volume), 2)


def build_us_overnight_theme_states(
    *,
    fetcher: ProxyFetcher = get_history,
    baskets: Dict[str, Dict[str, Any]] | None = None,
    min_symbols: int = 2,
) -> Dict[str, Any]:
    baskets = baskets or US_THEME_PROXY_BASKETS
    states: List[Dict[str, Any]] = []
    proxy_rows: Dict[str, Any] = {}
    failures: List[Dict[str, str]] = []

    for theme_id, spec in baskets.items():
        symbols = [str(x).strip().upper() for x in list(spec.get("symbols", []) or []) if str(x).strip()]
        symbol_metrics: List[Dict[str, Any]] = []
        for symbol in symbols:
            try:
                hist = fetcher(symbol, period="10d", interval="1d", timeout=5)
                metric = _last_daily_return(hist)
            except Exception as exc:
                failures.append({"symbol": symbol, "reason": str(exc)[:120]})
                metric = {"available": False}
            if metric.get("available"):
                metric = {"symbol": symbol, **metric}
                symbol_metrics.append(metric)
                proxy_rows[symbol] = metric

        if len(symbol_metrics) < int(min_symbols):
            continue
        returns = [float(row["return_1d_pct"]) for row in symbol_metrics]
        avg_return = sum(returns) / len(returns)
        hit_ratio = sum(1 for value in returns if value > 0) / len(returns)
        max_abs_return = max(abs(value) for value in returns)
        vol_values = [float(row["volume_ratio_5d"]) for row in symbol_metrics if row.get("volume_ratio_5d") is not None]
        avg_volume_ratio = sum(vol_values) / len(vol_values) if vol_values else None
        direction = _direction_from_return(avg_return, hit_ratio)
        strength = _strength_score(avg_return, hit_ratio, max_abs_return, avg_volume_ratio)
        if direction == "NEUTRAL" and strength < 18.0:
            continue
        leader_rows = sorted(symbol_metrics, key=lambda row: abs(float(row.get("return_1d_pct", 0.0))), reverse=True)[:4]
        states.append(
            {
                "theme_id": theme_id,
                "theme_name": str(spec.get("theme_name") or theme_id),
                "direction": direction,
                "strength_score": strength,
                "confidence": round(min(0.92, 0.38 + len(symbol_metrics) / max(len(symbols), 1) * 0.25 + min(strength, 80.0) / 200.0), 3),
                "avg_proxy_return_1d_pct": round(avg_return, 4),
                "positive_proxy_ratio": round(hit_ratio, 3),
                "proxy_count": len(symbol_metrics),
                "proxy_symbols": [row["symbol"] for row in symbol_metrics],
                "leader_proxies": [
                    {
                        "symbol": row["symbol"],
                        "return_1d_pct": row["return_1d_pct"],
                        "volume_ratio_5d": row.get("volume_ratio_5d"),
                    }
                    for row in leader_rows
                ],
                "evidence": [
                    f"{row['symbol']} {float(row['return_1d_pct']):+.2f}%"
                    for row in leader_rows
                ],
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "us_overnight_proxy_basket",
            }
        )

    last_dates = sorted({str(row.get("last_trade_date")) for row in proxy_rows.values() if row.get("last_trade_date")})
    states.sort(key=lambda row: (float(row.get("strength_score", 0.0)), abs(float(row.get("avg_proxy_return_1d_pct", 0.0)))), reverse=True)
    return {
        "status": "ok" if states else "empty",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_market": "US",
        "no_leakage_asof": last_dates[-1] if last_dates else "",
        "theme_states": states,
        "proxy_returns": proxy_rows,
        "failures": failures[:20],
    }


def _canonical_theme_name(theme_id: str) -> str:
    return THEME_CANONICAL_MAP.get(theme_id, theme_id)


def _merge_theme_states(existing: Iterable[Dict[str, Any]], overnight_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in list(existing or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("theme_id") or row.get("theme_name") or "").strip()
        if not key:
            continue
        merged[key] = dict(row)
        order.append(key)
    for row in list(overnight_rows or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("theme_id") or row.get("theme_name") or "").strip()
        if not key:
            continue
        incoming = dict(row)
        if key not in merged:
            merged[key] = incoming
            order.append(key)
            continue
        current = dict(merged[key])
        current_strength = _safe_float(current.get("strength_score")) or 0.0
        incoming_strength = _safe_float(incoming.get("strength_score")) or 0.0
        if incoming_strength >= current_strength:
            incoming["previous_theme_state"] = {
                "direction": current.get("direction"),
                "strength_score": current.get("strength_score"),
                "source": current.get("source"),
            }
            merged[key] = incoming
        else:
            reasons = list(current.get("evidence", []) or [])
            reasons.extend([f"overnight:{x}" for x in list(incoming.get("evidence", []) or [])[:2]])
            current["evidence"] = sorted(dict.fromkeys(str(x) for x in reasons if str(x).strip()))[:6]
            current["overnight_theme_lead"] = {
                "direction": incoming.get("direction"),
                "strength_score": incoming.get("strength_score"),
                "source": incoming.get("source"),
            }
            merged[key] = current
    return [merged[key] for key in order if key in merged]


def enrich_kr_intel_with_us_overnight_theme_lead(
    intel_data: Dict[str, Any],
    *,
    market: str,
    fetcher: ProxyFetcher = get_history,
) -> Dict[str, Any]:
    market_key = str(market or "").upper()
    if market_key not in {"KR", "KOSPI", "KOSDAQ"}:
        return intel_data
    payload = dict(intel_data or {})
    overnight = build_us_overnight_theme_states(fetcher=fetcher)
    us_states = overnight.get("theme_states", []) if isinstance(overnight, dict) else []
    transfer_artifact = load_transfer_artifact()
    edge_sources = {
        str(edge.get("source_theme_id") or "")
        for edge in list(transfer_artifact.get("edges", []) or [])
        if isinstance(edge, dict)
    } if isinstance(transfer_artifact, dict) else set()
    state_sources = {str(row.get("theme_id") or "") for row in us_states if isinstance(row, dict)}
    if state_sources and not state_sources.issubset(edge_sources):
        transfer_artifact = build_transfer_artifact()
    kr_priors = project_kr_priors(us_states, artifact=transfer_artifact)
    projected_states: List[Dict[str, Any]] = []
    for theme_id, prior in kr_priors.items():
        direction = str(prior.get("direction") or "NEUTRAL").upper()
        strength = _safe_float(prior.get("strength_score")) or 0.0
        if direction == "NEUTRAL" or strength < 8.0:
            continue
        edges = list(prior.get("contributing_edges", []) or [])
        projected_states.append(
            {
                "theme_id": str(theme_id),
                "theme_name": _canonical_theme_name(str(theme_id)),
                "direction": direction,
                "strength_score": round(float(strength), 2),
                "confidence": round(min(0.9, 0.35 + float(strength) / 150.0 + min(len(edges), 4) * 0.04), 3),
                "source": "us_overnight_theme_transfer",
                "evidence": [
                    (
                        f"{edge.get('source_theme_id')}:{edge.get('effective_dir')}"
                        f" {float(edge.get('signed_contribution', 0.0) or 0.0):+.1f}"
                    )
                    for edge in edges[:4]
                ],
                "contributing_edges": edges[:8],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    payload["theme_states"] = _merge_theme_states(payload.get("theme_states", []), projected_states)
    payload["beneficiary_themes"] = [
        {"theme_id": row.get("theme_id"), "theme_name": row.get("theme_name"), "strength_score": row.get("strength_score"), "confidence": row.get("confidence")}
        for row in payload["theme_states"]
        if str(row.get("direction") or "").upper() == "BENEFICIARY"
    ][:10]
    payload["headwind_themes"] = [
        {"theme_id": row.get("theme_id"), "theme_name": row.get("theme_name"), "strength_score": row.get("strength_score"), "confidence": row.get("confidence")}
        for row in payload["theme_states"]
        if str(row.get("direction") or "").upper() == "HEADWIND"
    ][:10]
    payload["us_overnight_theme_lead"] = {
        "status": overnight.get("status", "empty") if isinstance(overnight, dict) else "empty",
        "generated_at": overnight.get("generated_at") if isinstance(overnight, dict) else None,
        "no_leakage_asof": overnight.get("no_leakage_asof") if isinstance(overnight, dict) else "",
        "source_market": "US",
        "projected_kr_theme_count": len(projected_states),
        "us_theme_state_count": len(us_states),
        "top_us_theme_states": us_states[:8],
        "kr_priors": kr_priors,
    }
    return payload
