#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_theme_valuechain import (  # noqa: E402
    VALUECHAIN_CONFIDENCE_FLOOR,
    VALUECHAIN_REPORT_DIR,
    build_kis_theme_valuechain_payload,
    write_kis_theme_valuechain_payload,
)
from modules.scan_artifact_archive import load_local_scan_archive_rows  # noqa: E402


def _text(value: Any) -> str:
    return str(value or "").strip()


def _hash_key(*parts: Any) -> str:
    text = "|".join(_text(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_verified_sources(path: Path) -> List[Dict[str, Any]]:
    payload = _read_json(path)
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        edges = payload.get("edges") or payload.get("verified_valuechain_sources") or payload.get("records")
        if isinstance(edges, list):
            return [dict(row) for row in edges if isinstance(row, Mapping)]
    return []


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _category_db_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    market_scope = _text(payload.get("market_scope"))
    for record in payload.get("ticker_category_records") or []:
        if not isinstance(record, Mapping):
            continue
        trade_date = _text(record.get("trade_date"))
        ticker = _text(record.get("ticker"))
        if not trade_date or not ticker:
            continue
        row = {
            "category_key": f"{trade_date}:{record.get('market_scope') or record.get('market') or market_scope}:{ticker}",
            "trade_date": trade_date,
            "market_scope": _text(record.get("market_scope") or record.get("market") or market_scope),
            "ticker": ticker,
            "stock_name": record.get("stock_name"),
            "primary_theme": record.get("primary_theme"),
            "secondary_themes": record.get("secondary_themes") or [],
            "theme_source": record.get("theme_source"),
            "theme_routing_path": record.get("theme_routing_path"),
            "sector_name": record.get("sector_name"),
            "standard_industry_code": record.get("standard_industry_code"),
            "market_name": record.get("market_name"),
            "market_code": record.get("market_code"),
            "large_sector_name": record.get("large_sector_name"),
            "mid_sector_name": record.get("mid_sector_name"),
            "small_sector_name": record.get("small_sector_name"),
            "stock_type": record.get("stock_type"),
            "kospi200_item": record.get("kospi200_item"),
            "listed_date": record.get("listed_date"),
            "per": record.get("per"),
            "pbr": record.get("pbr"),
            "roe": record.get("roe"),
            "debt_ratio": record.get("debt_ratio"),
            "revenue_growth_rate": record.get("revenue_growth_rate"),
            "value_traded": record.get("value_traded"),
            "day_return_pct": record.get("day_return_pct"),
            "volume_rank": record.get("volume_rank"),
            "fluctuation_rank": record.get("fluctuation_rank"),
            "volume_power_rank": record.get("volume_power_rank"),
            "vi_triggered": bool(record.get("vi_triggered")),
            "news_count": int(record.get("news_count") or 0),
            "raw_news_count": int(record.get("raw_news_count") or 0),
            "news_positive_tags": record.get("news_positive_tags") or [],
            "news_risk_tags": record.get("news_risk_tags") or [],
            "news_source_scope": record.get("news_source_scope"),
            "kis_evidence_strength_score": record.get("kis_evidence_strength_score"),
            "kis_evidence_strength_level": record.get("kis_evidence_strength_level"),
            "source_ref": record.get("source_ref"),
            "payload": dict(record),
            "no_dummy_data": True,
        }
        rows.append(row)
    return rows


def _theme_state_db_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    market_scope = _text(payload.get("market_scope"))
    for record in payload.get("theme_daily_state") or []:
        if not isinstance(record, Mapping):
            continue
        trade_date = _text(record.get("trade_date"))
        theme_name = _text(record.get("theme_name"))
        if not trade_date or not theme_name:
            continue
        scope = _text(record.get("market") or market_scope)
        rows.append(
            {
                "theme_state_key": f"{trade_date}:{scope}:{theme_name}",
                "trade_date": trade_date,
                "market_scope": scope,
                "theme_name": theme_name,
                "symbol_count": int(record.get("symbol_count") or 0),
                "avg_day_return_pct": record.get("avg_day_return_pct"),
                "positive_return_ratio": record.get("positive_return_ratio"),
                "total_value_traded": record.get("total_value_traded"),
                "news_count": int(record.get("news_count") or 0),
                "vi_triggered_count": int(record.get("vi_triggered_count") or 0),
                "avg_kis_evidence_strength_score": record.get("avg_kis_evidence_strength_score"),
                "top_symbols": record.get("top_symbols") or [],
                "payload": dict(record),
                "no_dummy_data": True,
            }
        )
    return rows


def _evidence_db_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record in list(payload.get("verified_valuechain_edges") or []) + list(payload.get("blocked_valuechain_edges") or []):
        if not isinstance(record, Mapping):
            continue
        from_symbol = _text(record.get("from_symbol"))
        to_symbol = _text(record.get("to_symbol"))
        relationship = _text(record.get("relationship") or "valuechain")
        if not from_symbol or not to_symbol:
            continue
        source_urls = record.get("source_urls") if isinstance(record.get("source_urls"), list) else []
        rows.append(
            {
                "evidence_key": _hash_key(from_symbol, to_symbol, relationship, record.get("source_type"), source_urls[:1]),
                "from_symbol": from_symbol,
                "to_symbol": to_symbol,
                "relationship": relationship,
                "theme_name": record.get("theme_name"),
                "confidence": record.get("confidence"),
                "source_type": record.get("source_type"),
                "source_urls": source_urls,
                "source_title": record.get("source_title"),
                "evidence_text": record.get("evidence_text"),
                "evidence_collected_at": record.get("evidence_collected_at"),
                "production_valuechain": bool(record.get("production_valuechain")),
                "blocked_reasons": record.get("blocked_reasons") or [],
                "payload": dict(record),
                "no_dummy_data": True,
            }
        )
    return rows


def _network_edge_db_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    market_scope = _text(payload.get("market_scope"))
    for record in payload.get("edges") or []:
        if not isinstance(record, Mapping):
            continue
        source = _text(record.get("source"))
        target = _text(record.get("target"))
        edge_kind = _text(record.get("edge_kind"))
        relationship = _text(record.get("relationship"))
        if not source or not target or not edge_kind:
            continue
        rows.append(
            {
                "edge_key": _hash_key(market_scope, source, target, edge_kind, relationship),
                "market_scope": market_scope,
                "source_node": source,
                "target_node": target,
                "edge_kind": edge_kind,
                "relationship": relationship,
                "confidence": record.get("confidence"),
                "weight": record.get("weight"),
                "production_valuechain": bool(record.get("production_valuechain")),
                "source_type": record.get("source_type"),
                "source_urls": record.get("source_urls") or [],
                "evidence": record.get("evidence") or [],
                "payload": dict(record),
                "no_dummy_data": True,
            }
        )
    return rows


def _upsert_table(db: Any, table_name: str, rows: List[Dict[str, Any]], *, on_conflict: str, batch_size: int) -> int:
    if not rows:
        return 0
    total = 0
    for idx in range(0, len(rows), max(1, int(batch_size or 500))):
        batch = rows[idx : idx + max(1, int(batch_size or 500))]
        if hasattr(db, "_upsert_with_schema_drift_retry"):
            db._upsert_with_schema_drift_retry(table_name, batch, on_conflict=on_conflict)
        else:
            db.client.table(table_name).upsert(batch, on_conflict=on_conflict).execute()
        total += len(batch)
    return total


def _count_table(db: Any, table_name: str, *, market_scope: str = "", production_valuechain: bool | None = None) -> int:
    query = db.client.table(table_name).select("*", count="exact").limit(1)
    if market_scope:
        if table_name == "kis_valuechain_evidence":
            pass
        else:
            query = query.eq("market_scope", market_scope)
    if production_valuechain is not None:
        query = query.eq("production_valuechain", bool(production_valuechain))
    response = query.execute()
    return int(getattr(response, "count", None) or 0)


def _verify_supabase(db: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
    market_scope = _text(payload.get("market_scope"))
    category_scope = "" if market_scope == "KR" else market_scope
    return {
        "kis_ticker_category_daily": _count_table(db, "kis_ticker_category_daily", market_scope=category_scope),
        "kis_theme_daily_state": _count_table(db, "kis_theme_daily_state", market_scope=category_scope),
        "kis_valuechain_evidence_production": _count_table(
            db, "kis_valuechain_evidence", production_valuechain=True
        ),
        "kis_theme_network_edges": _count_table(db, "kis_theme_network_edges", market_scope=market_scope),
        "kis_theme_network_edges_production": _count_table(
            db, "kis_theme_network_edges", market_scope=market_scope, production_valuechain=True
        ),
    }


def _write_supabase(payload: Mapping[str, Any], *, batch_size: int) -> Dict[str, Any]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise RuntimeError("Supabase client unavailable. Check SUPABASE_URL/SUPABASE_KEY.")
    category_rows = _category_db_rows(payload)
    theme_rows = _theme_state_db_rows(payload)
    evidence_rows = _evidence_db_rows(payload)
    edge_rows = _network_edge_db_rows(payload)
    upserted = {
        "kis_ticker_category_daily": _upsert_table(
            db, "kis_ticker_category_daily", category_rows, on_conflict="category_key", batch_size=batch_size
        ),
        "kis_theme_daily_state": _upsert_table(
            db, "kis_theme_daily_state", theme_rows, on_conflict="theme_state_key", batch_size=batch_size
        ),
        "kis_valuechain_evidence": _upsert_table(
            db, "kis_valuechain_evidence", evidence_rows, on_conflict="evidence_key", batch_size=batch_size
        ),
        "kis_theme_network_edges": _upsert_table(
            db, "kis_theme_network_edges", edge_rows, on_conflict="edge_key", batch_size=batch_size
        ),
    }
    return {"upserted": upserted, "verified_counts": _verify_supabase(db, payload)}


def _write_markdown(path: Path, payload: Mapping[str, Any], *, source_path: Path, artifact_rows: int) -> Path:
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload.get("source_policy") if isinstance(payload.get("source_policy"), Mapping) else {}
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    lines = [
        "# KIS Theme Value-Chain Snapshot",
        "",
        f"- version: `{payload.get('version')}`",
        f"- generated_at: `{payload.get('generated_at')}`",
        f"- market_scope: `{payload.get('market_scope')}`",
        f"- artifact_rows_loaded: `{artifact_rows}`",
        f"- ticker_category_records: `{summary.get('ticker_category_records', 0)}`",
        f"- theme_daily_state_rows: `{summary.get('theme_daily_state_rows', 0)}`",
        f"- nodes: `{summary.get('nodes', 0)}`",
        f"- edges: `{summary.get('edges', 0)}`",
        f"- verified_valuechain_edges: `{summary.get('verified_valuechain_edges', 0)}`",
        f"- blocked_valuechain_edges: `{summary.get('blocked_valuechain_edges', 0)}`",
        f"- verified_source_input: `{source_path}`",
        "",
        "## Source Policy",
        "",
        f"- production threshold: `{policy.get('production_valuechain_requires_confidence_gte', VALUECHAIN_CONFIDENCE_FLOOR)}`",
        "- news/search/research-only edges stay blocked candidates; they do not become production value-chain edges.",
        "- production edges require official or disclosure evidence URL plus explicit evidence text.",
        "- no dummy data is generated.",
        "",
        "## Warnings",
        "",
    ]
    lines.extend([f"- `{warning}`" for warning in warnings] or ["- none"])
    lines.extend(["", "## Top Themes", ""])
    themes = summary.get("themes") if isinstance(summary.get("themes"), Mapping) else {}
    for theme, count in sorted(themes.items(), key=lambda item: int(item[1] or 0), reverse=True)[:20]:
        lines.append(f"- {theme}: `{count}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a KIS-backed theme/category/value-chain snapshot from real scan artifacts.")
    parser.add_argument("--market", type=str, default="KR", choices=["KR", "KOSPI", "KOSDAQ"])
    parser.add_argument("--limit-runs", type=int, default=120)
    parser.add_argument(
        "--verified-valuechain-json",
        type=str,
        default="runtime_state/long_term/kis_theme_valuechain/verified_sources.json",
        help="Optional JSON list of official/disclosure-backed value-chain edge evidence.",
    )
    parser.add_argument("--output-json", type=str, default="")
    parser.add_argument("--output-md", type=str, default="")
    parser.add_argument(
        "--write-db",
        action="store_true",
        default=os.getenv("AG_KIS_THEME_VALUECHAIN_WRITE_DB", "0").strip().lower() in {"1", "true", "yes", "on"},
        help="Upsert snapshot rows into Supabase tables from docs/migration/kis_theme_valuechain_tables.sql.",
    )
    parser.add_argument("--db-batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_local_scan_archive_rows(limit_runs=max(1, int(args.limit_runs or 120)))
    source_path = PROJECT_ROOT / args.verified_valuechain_json
    verified_sources = _load_verified_sources(source_path) if source_path.exists() else []
    payload = build_kis_theme_valuechain_payload(
        rows,
        verified_valuechain_sources=verified_sources,
        market=args.market,
        confidence_floor=VALUECHAIN_CONFIDENCE_FLOOR,
    )

    output_json = Path(args.output_json) if args.output_json else None
    output_md = Path(args.output_md) if args.output_md else VALUECHAIN_REPORT_DIR / f"{payload.get('market_scope', args.market)}.md"
    if not args.dry_run:
        output_json = _write_json(output_json, payload) if output_json else write_kis_theme_valuechain_payload(payload, market=args.market)
        output_md = _write_markdown(output_md, payload, source_path=source_path, artifact_rows=len(rows))
    db_rows = {}
    if args.write_db and not args.dry_run:
        db_rows = _write_supabase(payload, batch_size=max(1, int(args.db_batch_size or 500)))

    summary = dict(payload.get("summary") or {})
    summary.update(
        {
            "market_scope": payload.get("market_scope"),
            "output_json": str(output_json) if output_json else "",
            "output_md": str(output_md) if output_md else "",
            "verified_source_input": str(source_path),
            "supabase_rows_upserted": db_rows.get("upserted", db_rows) if isinstance(db_rows, Mapping) else {},
            "supabase_verified_counts": db_rows.get("verified_counts", {}) if isinstance(db_rows, Mapping) else {},
            "warnings": payload.get("warnings") or [],
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
