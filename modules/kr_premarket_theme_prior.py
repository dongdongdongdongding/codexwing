"""KR pre-market theme prior builder.

This module turns overnight US lead/macro context into KR theme priors. The
output is explicitly pre-market only; actionable scan publication still belongs
to the post-open confirmed scan after intraday volume/leadership can be seen.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from modules.theme_transfer import load_transfer_artifact, project_kr_priors

DEFAULT_OUTPUT_DIR = Path("runtime_state/shared/theme_prior")
KST_CONFIRM_AFTER = "09:30"


def build_premarket_theme_prior(
    macro_ctx: Dict[str, Any],
    *,
    transfer_artifact: Dict[str, Any] | None = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """Build KR pre-market theme priors from US lead context.

    The result is a ranked watchlist of likely KR themes, not a buy signal.
    Intraday confirmation should decide whether those themes become actionable.
    """
    artifact = transfer_artifact or load_transfer_artifact()
    us_theme_states = _build_us_theme_states(macro_ctx)
    projected = project_kr_priors(us_theme_states, artifact)
    priors = sorted(
        (_prior_row(theme_id, row) for theme_id, row in projected.items()),
        key=lambda row: (row["direction"] != "BENEFICIARY", -float(row["strength_score"] or 0.0), row["theme_id"]),
    )
    if top_n > 0:
        priors = priors[:top_n]

    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "kr_premarket_theme_prior_v1",
        "generated_at": generated_at,
        "actionability": "PREMARKET_PRIOR_ONLY",
        "confirm_after_kst": KST_CONFIRM_AFTER,
        "source": {
            "macro_state": macro_ctx.get("macro_state"),
            "macro_risk_score": macro_ctx.get("macro_risk_score"),
            "us_lead_score": macro_ctx.get("us_lead_score"),
            "us_lead_state": macro_ctx.get("us_lead_state"),
            "transfer_version": artifact.get("version") if isinstance(artifact, dict) else "missing",
        },
        "us_theme_states": us_theme_states,
        "kr_theme_priors": priors,
        "warnings": [
            "개장 전 테마 prior는 매수 후보가 아닙니다.",
            "09:30 이후 거래대금, 테마 내 동반상승, 대장주 유지 여부로 확정해야 합니다.",
        ],
    }


def write_premarket_theme_prior(
    payload: Dict[str, Any],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dated = output_dir / f"kr_premarket_theme_prior_{stamp}.json"
    latest = output_dir / "kr_premarket_theme_prior_latest.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    dated.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return {"dated": str(dated), "latest": str(latest)}


def _build_us_theme_states(macro_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    states: List[Dict[str, Any]] = []
    states.extend(
        _theme_state_from_change(
            "semiconductor",
            macro_ctx.get("soxx_change_1d"),
            label="SOXX",
            evidence="미국 반도체 ETF(SOXX) 1D 변화",
            scale=12.0,
        )
    )
    states.extend(
        _theme_state_from_change(
            "ai_datacenter",
            _avg_numeric(macro_ctx.get("qqq_change_1d"), macro_ctx.get("ixic_change_1d"), macro_ctx.get("nq_futures_change_1d")),
            label="QQQ/IXIC/NQ",
            evidence="나스닥·QQQ·나스닥선물 AI/성장주 리스크온 proxy",
            scale=10.0,
        )
    )
    states.extend(
        _theme_state_from_change(
            "robotics",
            macro_ctx.get("qqq_change_1d"),
            label="QQQ",
            evidence="미국 성장주 강도 proxy",
            scale=8.0,
        )
    )
    risk_off_strength = _risk_off_strength(macro_ctx)
    if risk_off_strength > 0:
        states.append(
            {
                "theme_id": "high_yield_risk_off",
                "direction": "BENEFICIARY",
                "strength_score": risk_off_strength,
                "source_label": "US_LEAD/RISK",
                "evidence": "US lead risk-off, VIX, SPY, KR derivative proxy를 합성한 고베타 역풍 proxy",
            }
        )
    return _merge_theme_states(states)


def _theme_state_from_change(
    theme_id: str,
    change_pct: Any,
    *,
    label: str,
    evidence: str,
    scale: float,
) -> List[Dict[str, Any]]:
    change = _to_float(change_pct)
    if change is None or abs(change) < 0.5:
        return []
    direction = "BENEFICIARY" if change > 0 else "HEADWIND"
    strength = min(100.0, abs(change) * scale)
    return [
        {
            "theme_id": theme_id,
            "direction": direction,
            "strength_score": round(strength, 2),
            "source_label": label,
            "source_change_pct": round(change, 2),
            "evidence": evidence,
        }
    ]


def _risk_off_strength(macro_ctx: Dict[str, Any]) -> float:
    strength = 0.0
    us_lead_score = _to_float(macro_ctx.get("us_lead_score"))
    if us_lead_score is not None and us_lead_score < 0:
        strength += min(45.0, abs(us_lead_score) * 1.2)
    spy_change = _to_float(macro_ctx.get("spy_change_1d"))
    if spy_change is not None and spy_change < -0.8:
        strength += min(20.0, abs(spy_change) * 8.0)
    vix_change = _to_float(macro_ctx.get("vix_change_1d"))
    if vix_change is not None and vix_change > 5.0:
        strength += min(20.0, vix_change * 1.2)
    kr_derivative = _to_float(macro_ctx.get("kr_derivative_lead_score"))
    if kr_derivative is not None and kr_derivative < 0:
        strength += min(15.0, abs(kr_derivative) * 1.5)
    return round(min(100.0, strength), 2)


def _prior_row(theme_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
    edges = row.get("contributing_edges") if isinstance(row.get("contributing_edges"), list) else []
    return {
        "theme_id": theme_id,
        "direction": str(row.get("direction") or "NEUTRAL"),
        "strength_score": float(row.get("strength_score") or 0.0),
        "source_count": len(edges),
        "top_sources": edges[:3],
    }


def _merge_theme_states(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        theme_id = str(row.get("theme_id") or "").strip()
        if not theme_id:
            continue
        block = merged.setdefault(
            theme_id,
            {
                "theme_id": theme_id,
                "direction_score": 0.0,
                "sources": [],
            },
        )
        direction = str(row.get("direction") or "NEUTRAL").upper()
        strength = float(row.get("strength_score") or 0.0)
        signed = strength if direction == "BENEFICIARY" else -strength if direction == "HEADWIND" else 0.0
        block["direction_score"] += signed
        block["sources"].append(dict(row))

    out: List[Dict[str, Any]] = []
    for block in merged.values():
        score = float(block.pop("direction_score") or 0.0)
        direction = "BENEFICIARY" if score > 1.0 else "HEADWIND" if score < -1.0 else "NEUTRAL"
        out.append(
            {
                "theme_id": block["theme_id"],
                "direction": direction,
                "strength_score": round(min(100.0, abs(score)), 2),
                "sources": block["sources"],
            }
        )
    return sorted(out, key=lambda row: -float(row.get("strength_score") or 0.0))


def _avg_numeric(*values: Any) -> float | None:
    nums = [_to_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        return float(text)
    except Exception:
        return None


__all__ = ["build_premarket_theme_prior", "write_premarket_theme_prior"]
