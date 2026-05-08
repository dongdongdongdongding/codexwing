"""US → KR theme transfer graph.

Builds and loads a versioned artifact that maps US close-session theme states
to KR open-session theme priors, so the scanner can fold overnight overseas
momentum into KR pre-open scoring without hard-coded heuristics.

Artifact schema: multi_agent/schemas/theme_transfer.schema.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules.theme_catalog import THEME_CANONICAL_MAP, THEME_ID_MAP


ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "models" / "theme_transfer_us_to_kr.json"
SCHEMA_VERSION = "us_to_kr_v1"


# Seeded cross-market edges. Each tuple: (us_theme_id, kr_theme_id, relationship, seed_confidence, evidence_notes).
# Confidence is a subjective prior in [0, 1]; builder refines it via empirical archive signals.
_SEED_EDGES: List[Tuple[str, str, str, float, List[str]]] = [
    (
        "semiconductor",
        "semiconductor",
        "CO_MOVE",
        0.85,
        [
            "NVDA/AVGO/AMD 강세 → 삼성전자·SK하이닉스 HBM 수혜 파급",
            "Philadelphia Semiconductor Index(SOX) 1d change와 KR 반도체 섹터 익일 상관 높음",
        ],
    ),
    (
        "ai_datacenter",
        "semiconductor",
        "CO_MOVE",
        0.78,
        [
            "미국 AI 인프라(Hyperscaler capex) → HBM/메모리 수요 → KR 반도체 수혜",
        ],
    ),
    (
        "ai_datacenter",
        "it_platform",
        "CO_MOVE",
        0.62,
        [
            "MSFT/GOOG/META 강세 → KR SaaS·AI 솔루션 심리 동반",
        ],
    ),
    (
        "ev",
        "secondary_battery",
        "CO_MOVE",
        0.72,
        [
            "TSLA/리비안 강세 → LG에너지솔루션·삼성SDI·에코프로 전해액 수혜",
            "단, 중국 CATL/BYD 동향도 중요 confounder",
        ],
    ),
    (
        "ev",
        "automobile",
        "CO_MOVE",
        0.55,
        [
            "TSLA 급등 → 현대차·기아 전기차 라인업 재평가",
        ],
    ),
    (
        "biotech",
        "bio",
        "CO_MOVE",
        0.55,
        [
            "XBI/IBB ETF 강세 → 셀트리온/한미약품/유한양행 심리 동반",
            "FDA 승인/임상 결과는 종목별 특이성 크므로 confidence 중간",
        ],
    ),
    (
        "oil_energy",
        "정유_에너지",
        "CO_MOVE",
        0.68,
        [
            "WTI/Brent 급등 → SK이노베이션·S-Oil·GS·에쓰오일 정제마진 상승",
        ],
    ),
    (
        "oil_energy",
        "shipbuilding",
        "CO_MOVE",
        0.48,
        [
            "유가 상승 → LNG·유조선 신조 수주 기대 → 현대중공업·삼성중공업",
        ],
    ),
    (
        "defense",
        "defense",
        "CO_MOVE",
        0.82,
        [
            "LMT/NOC/GD 강세 → 한화에어로·LIG넥스원·한국항공우주 동반 상승 경향",
            "지정학 이벤트(중동/우크라이나) 확대 시 KR 방산주 funding flow 관찰",
        ],
    ),
    (
        "robotics",
        "robotics",
        "CO_MOVE",
        0.65,
        [
            "ROK/BOTZ ETF, ISRG, TER → 두산로보틱스·레인보우로보틱스 심리 동반",
        ],
    ),
    (
        "quantum",
        "quantum",
        "CO_MOVE",
        0.62,
        [
            "IONQ/RGTI/QBTS/QTUM 등 미국 양자 테마 급등락 → KR 양자암호·양자컴퓨팅 테마 심리 전이",
            "표본이 얇고 변동성이 커서 confidence는 중간값으로 시작하고 실현성과로 보정 필요",
        ],
    ),
    (
        "nuclear",
        "친환경/에너지",
        "CO_MOVE",
        0.58,
        [
            "미국 SMR(NuScale, BWXT) 뉴스 → 두산에너빌리티·한전기술 수혜",
        ],
    ),
    (
        "power_grid",
        "친환경/에너지",
        "CO_MOVE",
        0.54,
        [
            "미국 전력망/AI 전력 인프라 강세 → KR 전력기기·전력 인프라 테마 심리 전이",
        ],
    ),
    (
        "crypto",
        "가상자산/블록체인",
        "CO_MOVE",
        0.46,
        [
            "COIN/MSTR/Bitcoin proxy 강세 → KR 가상자산·블록체인·STO 테마 동반 심리",
            "국내 규제 뉴스 영향이 크므로 confidence는 낮게 시작",
        ],
    ),
    (
        "finance",
        "finance",
        "CO_MOVE",
        0.40,
        [
            "미국 은행주 실적/금리 이슈 → KR 금융지주 동반, 단 KR-특이 regulation 이벤트 confounder",
        ],
    ),
    (
        "consumer_retail",
        "consumer_retail",
        "CO_MOVE",
        0.35,
        [
            "미국 소비재(PG/KO/WMT) 약세 → KR 화장품·유통 심리 보수화",
        ],
    ),
    (
        "game_content_ent",
        "game_content_ent",
        "CO_MOVE",
        0.42,
        [
            "디즈니/넷플릭스/로블록스 → 크래프톤·엔씨·카카오게임즈 — 동조성은 계절성/실적 의존",
        ],
    ),
    (
        "high_yield_risk_off",
        "semiconductor",
        "INVERSE",
        0.55,
        [
            "미국 하이일드 스프레드 급격 확대(risk-off) → KR 반도체 등 고베타 익일 약세",
        ],
    ),
    (
        "high_yield_risk_off",
        "secondary_battery",
        "INVERSE",
        0.50,
        [
            "리스크오프 → KR 2차전지 고베타 섹터 약세",
        ],
    ),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_kr_theme_id(candidate: str) -> str:
    candidate = (candidate or "").strip()
    if not candidate:
        return ""
    if candidate in THEME_ID_MAP:
        return THEME_ID_MAP[candidate]
    if candidate in THEME_ID_MAP.values():
        return candidate
    if candidate in THEME_CANONICAL_MAP:
        mapped = THEME_CANONICAL_MAP[candidate]
        return THEME_ID_MAP.get(mapped, candidate)
    return candidate


def _load_archive_theme_returns(archive_csv: Path) -> Dict[str, Dict[str, float]]:
    """Aggregate KR realized 3d return stats per primary_theme from the archive CSV.

    Returns { kr_theme_id: { "n": int, "avg_3d": float, "win_rate": float, "hit5": float } }.
    """
    try:
        import pandas as pd
    except Exception:
        return {}
    if not archive_csv.exists():
        return {}
    df = pd.read_csv(archive_csv, low_memory=False)
    df = df[df["market"].isin(["KOSPI", "KOSDAQ"])]
    df["return_3d_pct"] = pd.to_numeric(df["return_3d_pct"], errors="coerce")
    df["label_hit_5pct"] = pd.to_numeric(df["label_hit_5pct"], errors="coerce")
    df = df[df["return_3d_pct"].notna() & df["primary_theme"].notna()]
    stats: Dict[str, Dict[str, float]] = {}
    for theme_name, group in df.groupby("primary_theme"):
        theme_id = _canonical_kr_theme_id(str(theme_name))
        if not theme_id:
            continue
        r = group["return_3d_pct"].astype(float)
        stats[theme_id] = {
            "n": int(len(group)),
            "avg_3d": round(float(r.mean()), 4),
            "win_rate": round(float((r >= 0).mean()), 4),
            "hit5": round(float(group["label_hit_5pct"].fillna(0).mean()), 4),
        }
    return stats


def _refine_confidence(seed_conf: float, target_stats: Optional[Dict[str, float]]) -> Tuple[float, Dict[str, Any]]:
    """Blend seed prior with empirical KR-side performance to produce a calibrated confidence.

    Target themes with stronger, more consistent KR outcomes get a modest boost;
    weak/empty buckets get a modest penalty. Capped so no edge becomes overconfident
    on thin evidence.
    """
    if not target_stats or target_stats.get("n", 0) < 30:
        return round(seed_conf * 0.9, 3), {"adjustment": "insufficient_sample", "n": target_stats.get("n") if target_stats else 0}
    win = float(target_stats.get("win_rate", 0.5) or 0.5)
    avg = float(target_stats.get("avg_3d", 0.0) or 0.0)
    # Scale win/avg into a [-0.2, +0.2] adjustment band.
    win_delta = (win - 0.55) * 0.8     # win=0.55 neutral, win=0.80 → +0.2
    avg_delta = max(-0.1, min(0.1, avg * 0.02))
    boost = max(-0.2, min(0.2, win_delta + avg_delta))
    refined = max(0.05, min(0.95, seed_conf + boost))
    return round(refined, 3), {
        "seed_confidence": seed_conf,
        "boost": round(boost, 3),
        "sample_n": int(target_stats.get("n", 0)),
        "sample_win_rate": win,
        "sample_avg_3d": avg,
    }


def build_transfer_artifact(
    *,
    archive_csv: Optional[Path] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the US→KR theme transfer artifact (does not write to disk)."""
    archive_csv = archive_csv or Path("runtime_state/reports/archive/scan_archive_learning_dataset_all.csv")
    target_stats = _load_archive_theme_returns(archive_csv)

    edges: List[Dict[str, Any]] = []
    for us_theme, kr_theme, relationship, seed_conf, evidence in _SEED_EDGES:
        kr_id = _canonical_kr_theme_id(kr_theme)
        stats = target_stats.get(kr_id)
        refined, calibration = _refine_confidence(seed_conf, stats)
        edges.append(
            {
                "source_theme_id": us_theme,
                "target_theme_id": kr_id or kr_theme,
                "relationship": relationship,
                "confidence": refined,
                "evidence": list(evidence),
                "notes": json.dumps(calibration, ensure_ascii=False),
            }
        )

    return {
        "version": version or f"{SCHEMA_VERSION}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "source_market": "US",
        "target_market": "KR",
        "generated_at": _now_iso(),
        "edges": edges,
    }


def write_transfer_artifact(artifact: Dict[str, Any], out_path: Path = ARTIFACT_PATH) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def load_transfer_artifact(path: Path = ARTIFACT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"version": "missing", "edges": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "invalid", "edges": []}


def project_kr_priors(
    us_theme_states: Iterable[Dict[str, Any]],
    artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Project US theme states into KR-side priors via the transfer graph.

    Args:
        us_theme_states: Iterable of { "theme_id": str, "direction": "BENEFICIARY|HEADWIND|NEUTRAL",
                         "strength_score": float 0-100 }.
        artifact: optional loaded artifact; falls back to on-disk file.

    Returns:
        Mapping kr_theme_id → { direction, strength_score, contributing_edges: [...] }.
    """
    art = artifact or load_transfer_artifact()
    edges = art.get("edges", []) if isinstance(art, dict) else []
    us_index: Dict[str, Dict[str, Any]] = {}
    for row in us_theme_states or []:
        tid = str(row.get("theme_id", "")).strip()
        if tid:
            us_index[tid] = row

    priors: Dict[str, Dict[str, Any]] = {}
    for edge in edges:
        src = edge.get("source_theme_id")
        tgt = edge.get("target_theme_id")
        rel = str(edge.get("relationship", "CO_MOVE")).upper()
        conf = float(edge.get("confidence", 0.0) or 0.0)
        if src not in us_index or not tgt:
            continue
        us_row = us_index[src]
        us_dir = str(us_row.get("direction", "NEUTRAL")).upper()
        us_strength = float(us_row.get("strength_score", 0.0) or 0.0)
        if us_dir == "NEUTRAL" or us_strength <= 0:
            continue
        flip = (rel == "INVERSE")
        effective_dir = us_dir if not flip else ("HEADWIND" if us_dir == "BENEFICIARY" else "BENEFICIARY")
        contribution = us_strength * conf * (1.0 if not flip else 1.0)
        block = priors.setdefault(
            tgt,
            {
                "target_theme_id": tgt,
                "direction_score": 0.0,
                "contributing_edges": [],
            },
        )
        signed = contribution if effective_dir == "BENEFICIARY" else -contribution
        block["direction_score"] += signed
        block["contributing_edges"].append(
            {
                "source_theme_id": src,
                "relationship": rel,
                "confidence": conf,
                "us_direction": us_dir,
                "us_strength": us_strength,
                "effective_dir": effective_dir,
                "signed_contribution": round(signed, 3),
            }
        )

    # Normalize direction_score → direction + strength.
    for block in priors.values():
        score = float(block.pop("direction_score", 0.0))
        if score > 1.0:
            block["direction"] = "BENEFICIARY"
        elif score < -1.0:
            block["direction"] = "HEADWIND"
        else:
            block["direction"] = "NEUTRAL"
        block["strength_score"] = round(min(100.0, abs(score)), 2)
    return priors
