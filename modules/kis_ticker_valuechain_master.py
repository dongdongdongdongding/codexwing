from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from modules.kis_theme_valuechain import (
    VALUECHAIN_CONFIDENCE_FLOOR,
    normalize_verified_valuechain_edge,
)


KIS_TICKER_VALUECHAIN_MASTER_VERSION = "kis_ticker_valuechain_master_v1"
TICKER_VALUECHAIN_DIR = Path("runtime_state/long_term/kis_ticker_valuechain")
TICKER_VALUECHAIN_REPORT_DIR = Path("runtime_state/reports/kis_ticker_valuechain")
TICKER_VALUECHAIN_SOURCE_PATH = TICKER_VALUECHAIN_DIR / "verified_edges.json"
TICKER_VALUECHAIN_MASTER_PATH = TICKER_VALUECHAIN_DIR / "master.json"
LEGACY_VALUECHAIN_SOURCE_PATH = Path("runtime_state/long_term/kis_theme_valuechain/verified_sources.json")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _hash_key(*parts: Any) -> str:
    raw = "|".join(_text(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _json_payload(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _market_scope(symbol: str) -> str:
    text = _text(symbol).upper()
    if text.endswith(".KS"):
        return "KOSPI"
    if text.endswith(".KQ"):
        return "KOSDAQ"
    return "KR"


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [] if value in (None, "") else [value]


def _source_path(path: Optional[Path | str] = None) -> Path:
    if path:
        return Path(path)
    if TICKER_VALUECHAIN_SOURCE_PATH.exists():
        return TICKER_VALUECHAIN_SOURCE_PATH
    return LEGACY_VALUECHAIN_SOURCE_PATH


def load_verified_valuechain_sources(path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    source_path = _source_path(path)
    payload = _json_payload(source_path)
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        rows = payload.get("records") or payload.get("edges") or payload.get("verified_valuechain_sources")
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _relationship_roles(relationship: str, *, side: str) -> List[str]:
    rel = relationship.lower()
    roles: List[str] = []
    if side == "from":
        roles.append("upstream")
        if any(token in rel for token in ("supplier", "supply", "vendor", "equipment", "material")):
            roles.append("supplier")
        if "equipment" in rel:
            roles.append("equipment_supplier")
        if "material" in rel:
            roles.append("material_supplier")
    else:
        roles.append("downstream")
        if any(token in rel for token in ("customer", "client", "buyer", "supply", "equipment", "material")):
            roles.append("customer")
        if "manufacturer" in rel:
            roles.append("manufacturer")
    return list(dict.fromkeys(roles))


def _edge_record(edge: Mapping[str, Any]) -> Dict[str, Any]:
    source_urls = edge.get("source_urls") if isinstance(edge.get("source_urls"), list) else []
    return {
        "edge_id": _hash_key(edge.get("from_symbol"), edge.get("to_symbol"), edge.get("relationship"), source_urls[:1]),
        "from_symbol": edge.get("from_symbol"),
        "to_symbol": edge.get("to_symbol"),
        "relationship": edge.get("relationship"),
        "theme_name": edge.get("theme_name"),
        "confidence": edge.get("confidence"),
        "source_type": edge.get("source_type"),
        "source_urls": source_urls,
        "source_title": edge.get("source_title"),
        "evidence_text": edge.get("evidence_text"),
        "evidence_collected_at": edge.get("evidence_collected_at"),
        "production_valuechain": bool(edge.get("production_valuechain")),
        "blocked_reasons": edge.get("blocked_reasons") or [],
        "no_dummy_data": True,
    }


def _profile(
    ticker: str,
    *,
    incoming: List[Mapping[str, Any]],
    outgoing: List[Mapping[str, Any]],
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    roles: List[str] = []
    for edge in outgoing:
        roles.extend(_relationship_roles(_text(edge.get("relationship")), side="from"))
    for edge in incoming:
        roles.extend(_relationship_roles(_text(edge.get("relationship")), side="to"))
    positions = []
    if outgoing:
        positions.append("upstream")
    if incoming:
        positions.append("downstream")
    if incoming and outgoing:
        positions.append("intermediate")
    verified_edges = list(incoming) + list(outgoing)
    confidences = [float(edge.get("confidence") or 0.0) for edge in verified_edges]
    source_types = sorted({_text(edge.get("source_type")) for edge in verified_edges if _text(edge.get("source_type"))})
    themes = sorted({_text(edge.get("theme_name")) for edge in verified_edges if _text(edge.get("theme_name"))})
    return {
        "ticker": ticker,
        "market_scope": _text(metadata.get("market_scope")) or _market_scope(ticker),
        "stock_name": _text(metadata.get("stock_name")) or ticker,
        "primary_theme": _text(metadata.get("primary_theme")) or (themes[0] if themes else ""),
        "valuechain_positions": positions,
        "valuechain_roles": sorted(set(roles)),
        "upstream_symbols": sorted({_text(edge.get("from_symbol")) for edge in incoming if _text(edge.get("from_symbol"))}),
        "downstream_symbols": sorted({_text(edge.get("to_symbol")) for edge in outgoing if _text(edge.get("to_symbol"))}),
        "incoming_edges": [_edge_record(edge) for edge in incoming],
        "outgoing_edges": [_edge_record(edge) for edge in outgoing],
        "verified_edge_count": len(verified_edges),
        "max_confidence": round(max(confidences), 4) if confidences else 0.0,
        "source_types": source_types,
        "themes": themes,
        "last_verified_at": max([_text(edge.get("evidence_collected_at")) for edge in verified_edges if _text(edge.get("evidence_collected_at"))] or [""]),
        "refresh_cadence_days": 90,
        "durability": "static_until_official_evidence_changes",
        "no_dummy_data": True,
    }


def _metadata_map(records: Optional[Iterable[Mapping[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in records or []:
        if not isinstance(row, Mapping):
            continue
        ticker = _text(row.get("ticker"))
        if not ticker:
            continue
        current = out.setdefault(ticker, {})
        for key in ("market_scope", "market", "stock_name", "primary_theme"):
            if row.get(key) not in (None, "", []):
                current.setdefault("market_scope" if key == "market" else key, row.get(key))
    return out


def build_ticker_valuechain_master(
    sources: Iterable[Mapping[str, Any]],
    *,
    ticker_metadata_records: Optional[Iterable[Mapping[str, Any]]] = None,
    confidence_floor: float = VALUECHAIN_CONFIDENCE_FLOOR,
) -> Dict[str, Any]:
    generated_at = _utcnow()
    verified_edges: List[Dict[str, Any]] = []
    blocked_edges: List[Dict[str, Any]] = []
    incoming: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    outgoing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    metadata = _metadata_map(ticker_metadata_records)

    seen_edges: set[Tuple[str, str, str]] = set()
    for source in sources or []:
        if not isinstance(source, Mapping):
            continue
        edge = normalize_verified_valuechain_edge(source, confidence_floor=confidence_floor)
        edge_record = _edge_record(edge)
        edge_key = (_text(edge_record.get("from_symbol")), _text(edge_record.get("to_symbol")), _text(edge_record.get("relationship")))
        if edge.get("production_valuechain"):
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            verified_edges.append(edge_record)
            outgoing[_text(edge_record["from_symbol"])].append(edge_record)
            incoming[_text(edge_record["to_symbol"])].append(edge_record)
        else:
            blocked_edges.append(edge_record)

    tickers = sorted(set(incoming) | set(outgoing))
    profiles = [
        _profile(
            ticker,
            incoming=incoming.get(ticker, []),
            outgoing=outgoing.get(ticker, []),
            metadata=metadata.get(ticker, {}),
        )
        for ticker in tickers
    ]
    source_distribution = Counter(_text(edge.get("source_type")) or "unknown" for edge in verified_edges)
    role_distribution: Counter[str] = Counter()
    for profile in profiles:
        for role in profile.get("valuechain_roles") or []:
            role_distribution[str(role)] += 1

    return {
        "version": KIS_TICKER_VALUECHAIN_MASTER_VERSION,
        "generated_at": generated_at,
        "confidence_floor": float(confidence_floor),
        "refresh_policy": {
            "type": "slow_changing_master",
            "refresh_cadence_days": 90,
            "production_requires_official_evidence": True,
            "news_or_web_search_only_edges_blocked": True,
        },
        "summary": {
            "ticker_profiles": len(profiles),
            "verified_edges": len(verified_edges),
            "blocked_edges": len(blocked_edges),
            "source_distribution": dict(source_distribution),
            "role_distribution": dict(role_distribution),
        },
        "ticker_profiles": profiles,
        "edges": verified_edges,
        "blocked_edges": blocked_edges,
        "no_dummy_data": True,
    }


def write_ticker_valuechain_master(payload: Mapping[str, Any], path: Path | str = TICKER_VALUECHAIN_MASTER_PATH) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def load_ticker_valuechain_master(path: Path | str = TICKER_VALUECHAIN_MASTER_PATH) -> Dict[str, Any]:
    payload = _json_payload(Path(path))
    return dict(payload) if isinstance(payload, Mapping) else {}


__all__ = [
    "KIS_TICKER_VALUECHAIN_MASTER_VERSION",
    "LEGACY_VALUECHAIN_SOURCE_PATH",
    "TICKER_VALUECHAIN_DIR",
    "TICKER_VALUECHAIN_MASTER_PATH",
    "TICKER_VALUECHAIN_REPORT_DIR",
    "TICKER_VALUECHAIN_SOURCE_PATH",
    "build_ticker_valuechain_master",
    "load_ticker_valuechain_master",
    "load_verified_valuechain_sources",
    "write_ticker_valuechain_master",
]
