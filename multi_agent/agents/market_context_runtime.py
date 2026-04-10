from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

from multi_agent.contracts.types import MarketContextHandoff, RunContext, WarningItem
from modules.live_scan_context import live_mode_enabled, normalize_market_key
from modules.theme_signal_engine import write_theme_cache


def _parse_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).strip())
        except Exception:
            return 0.0


def _parse_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _context_cache_path(cache_key: str) -> Path:
    base = Path("runtime_state") / "long_term" / "context_cache"
    base.mkdir(parents=True, exist_ok=True)
    key = str(cache_key or "UNKNOWN").upper()
    return base / f"{key}.json"


def _run_market_intel_snapshot_path(run_id: str) -> Path:
    return Path("runtime_state") / "shared_working" / str(run_id or "") / "market_intelligence_snapshot.json"


def _read_context_cache(cache_key: str) -> Dict[str, Any]:
    path = _context_cache_path(cache_key)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_context_cache(
    cache_key: str,
    payload: Dict[str, Any],
) -> None:
    path = _context_cache_path(cache_key)
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _cache_age_hours(cache: Dict[str, Any]) -> float:
    try:
        s = str(cache.get("generated_at") or "")
        if not s:
            return -1.0
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - t).total_seconds() / 3600.0)
    except Exception:
        return -1.0


def _read_run_market_intel_snapshot(run_id: str) -> Dict[str, Any]:
    path = _run_market_intel_snapshot_path(run_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def build_market_context_handoff(context: RunContext) -> MarketContextHandoff:
    market = (context.market or "UNKNOWN").upper()
    market_group = "KR" if market in {"KR", "KOSPI", "KOSDAQ"} else ("US" if market else "UNKNOWN")
    cache_key = market
    warnings: List[WarningItem] = []
    cache = _read_context_cache(cache_key)
    cache_age_h = _cache_age_hours(cache)
    macro_ok = False
    news_ok = False

    regime = {
        "market": market,
        "market_group": market_group,
        "status": "UNKNOWN",
        "support_score": None,
    }
    macro_overlay: Dict[str, Any] = {
        "status": "not_wired",
        "note": "Wire modules/macro_scheduler.py for live regime overlay.",
    }
    news_impact: Dict[str, Any] = {
        "status": "not_wired",
        "note": "Wire modules/market_intelligence.py and modules/news_analysis.py next.",
    }

    try:
        from modules.macro_scheduler import get_macro_context

        macro_ctx = get_macro_context(
            force_refresh=live_mode_enabled(market_group),
            market_group=normalize_market_key(market_group),
        )
        macro_state = str(macro_ctx.get("macro_state", "UNKNOWN"))
        macro_risk_score = _parse_float(macro_ctx.get("macro_risk_score", 0))
        support_score = round(max(0.0, min(100.0, 100.0 - macro_risk_score)), 2)
        regime = {
            "market": market,
            "market_group": market_group,
            "status": macro_state,
            "support_score": support_score,
        }
        macro_overlay = {
            "status": "live_macro",
            "macro_state": macro_state,
            "macro_risk_score": macro_risk_score,
            "macro_multiplier": _parse_float(macro_ctx.get("macro_multiplier", 1.0)),
            "macro_penalty": _parse_float(macro_ctx.get("macro_penalty", 0)),
            "flags": list(macro_ctx.get("flags", [])),
            "raw_context": macro_ctx,
        }
        macro_ok = True
    except Exception as e:
        warnings.append(
            WarningItem(
                code="MACRO_CONTEXT_FETCH_FAIL",
                message=f"Macro context fetch failed: {e}",
                severity="warning",
            )
        )
        cached_macro = cache.get("macro_overlay", {}) if isinstance(cache, dict) else {}
        cached_regime = cache.get("regime", {}) if isinstance(cache, dict) else {}
        if isinstance(cached_macro, dict) and cached_macro:
            macro_overlay = cached_macro
            if isinstance(cached_regime, dict) and cached_regime:
                regime = cached_regime
            age_msg = f" (cache_age_h={cache_age_h:.1f})" if cache_age_h >= 0 else ""
            warnings.append(
                WarningItem(
                    code="MACRO_CONTEXT_CACHE_FALLBACK",
                    message=f"Macro context fallback from cache{age_msg}.",
                    severity="warning",
                )
            )

    try:
        intel_snapshot = _read_run_market_intel_snapshot(context.run_id)
        intel = intel_snapshot.get("intel_data") if isinstance(intel_snapshot, dict) else None
        if not isinstance(intel, dict) or not intel:
            from modules.market_intelligence import get_market_intelligence

            intel_market = market
            intel = get_market_intelligence(
                market=intel_market,
                force_refresh=True,
            )
        sentiment_score = int(_parse_int(intel.get("sentiment_score", 0)))
        news_impact = {
            "status": "live_intel" if intel.get("source") != "fallback" else "fallback_intel",
            "market_sentiment": str(intel.get("market_sentiment", "NEUTRAL")),
            "sentiment_score": sentiment_score,
            "headline_count": int(intel.get("headline_count", len(intel.get("raw_headlines", []) or [])) or 0),
            "evidence_headlines": list(intel.get("evidence_headlines", [])),
            "raw_headlines": list(intel.get("raw_headlines", [])),
            "beneficiary_sectors": list(intel.get("beneficiary_sectors", [])),
            "victim_sectors": list(intel.get("victim_sectors", [])),
            "theme_states": list(intel.get("theme_states", [])),
            "beneficiary_themes": list(intel.get("beneficiary_themes", [])),
            "headwind_themes": list(intel.get("headwind_themes", [])),
            "theme_evidence": dict(intel.get("theme_evidence", {})),
            "macro_drivers": list(intel.get("macro_drivers", [])),
            "driver_scores": dict(intel.get("driver_scores", {})),
            "cross_asset_signals": list(intel.get("cross_asset_signals", [])),
            "risk_flags": list(intel.get("risk_flags", [])),
            "news_quality": str(intel.get("news_quality", "LOW")),
            "key_insight": str(intel.get("key_insight", "")),
            "source": str(intel.get("source", "unknown")),
            "model": str(intel.get("model", "")),
            "raw": intel,
        }
        if intel.get("source") == "fallback":
            warnings.append(
                WarningItem(
                    code="NEWS_INTEL_FALLBACK",
                    message="News intelligence returned fallback payload.",
                    severity="warning",
                )
            )
        news_ok = True
        write_theme_cache(
            market,
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "market": market,
                "theme_states": list(intel.get("theme_states", [])),
                "beneficiary_themes": list(intel.get("beneficiary_themes", [])),
                "headwind_themes": list(intel.get("headwind_themes", [])),
                "theme_evidence": dict(intel.get("theme_evidence", {})),
                "source": str(intel.get("source", "unknown")),
            },
        )
    except Exception as e:
        warnings.append(
            WarningItem(
                code="NEWS_CONTEXT_FETCH_FAIL",
                message=f"News context fetch failed: {e}",
                severity="warning",
            )
        )
        cached_news = cache.get("news_impact", {}) if isinstance(cache, dict) else {}
        if isinstance(cached_news, dict) and cached_news:
            news_impact = cached_news
            age_msg = f" (cache_age_h={cache_age_h:.1f})" if cache_age_h >= 0 else ""
            warnings.append(
                WarningItem(
                    code="NEWS_CONTEXT_CACHE_FALLBACK",
                    message=f"News context fallback from cache{age_msg}.",
                    severity="warning",
                )
            )

    if not warnings and macro_overlay.get("status") == "not_wired" and news_impact.get("status") == "not_wired":
        warnings.append(
            WarningItem(
                code="MARKET_CONTEXT_NOT_WIRED",
                message="Market/news context is placeholder in this bridge stage.",
                severity="warning",
            )
        )

    # Persist last usable context snapshot for resilience in later runs.
    if macro_ok or news_ok:
        _write_context_cache(
            cache_key,
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "market": market,
                "market_group": market_group,
                "regime": regime,
                "macro_overlay": macro_overlay,
                "news_impact": news_impact,
            },
        )

    return MarketContextHandoff(
        run_context=context,
        regime=regime,
        macro_overlay=macro_overlay,
        news_impact=news_impact,
        warnings=warnings,
    )
