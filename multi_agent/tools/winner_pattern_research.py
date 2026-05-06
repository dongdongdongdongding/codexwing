#!/usr/bin/env python3
"""Winner-vs-loser feature analysis for KOSPI/KOSDAQ swing.

Goal
----
The user reports realized losses on names the live UI promoted (OBSERVE
rows shown as Top-5). The model's binary objective (5d ≥ +5%) is what we
trained on, but realized winners follow specific feature distributions
the model may not yet weight correctly. This tool runs Mann-Whitney +
Cohen's d univariate tests to surface which features actually separate
winners from losers, with bias safeguards (FDR, holdout validation).

Winner definitions (per user 2026-05-05)
----------------------------------------
- W1: return_1d_pct ≥ +5%
- W2: return_3d_pct ≥ +7%
- W3: return_5d_pct ≥ +10%

Loser: bottom 30% of the same horizon's distribution (negative tail).

Segments
--------
- KOSPI swing  : market_subtype=KOSPI  & scan_mode=SWING
- KOSDAQ swing : market_subtype=KOSDAQ & scan_mode=SWING

Method
------
1. Load archive via load_scan_archive() (the same path retrain uses).
2. engineer_features + derive_ohlcv_features (KR + RESOLVED + alpha-bearing).
3. For each segment × winner-definition:
   - Build winner / loser groups
   - For every numeric feature: Mann-Whitney U + Cohen's d
   - Multiple testing correction (Benjamini-Hochberg FDR @ q=0.05)
   - Discovery / validation split (70/30 by scan_date)
   - Keep features that pass FDR on discovery AND replicate in validation

Output
------
runtime_state/reports/learning/winner_pattern_research.json + .md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

from retrain_ml import (  # noqa: E402
    FEATURE_COLS,
    derive_ohlcv_features,
    engineer_features,
    load_scan_archive,
)


WINNER_DEFS = [
    {"key": "1d_5pct",  "horizon": "return_1d_pct",  "threshold": 5.0},
    {"key": "3d_7pct",  "horizon": "return_3d_pct",  "threshold": 7.0},
    {"key": "5d_10pct", "horizon": "return_5d_pct", "threshold": 10.0},
]

# Features to exclude from testing because they leak from the outcome itself
LEAKAGE_BLOCKLIST = {
    "return_close_pct", "return_1d_pct", "return_2d_pct", "return_3d_pct",
    "return_5d_pct", "return_7d_pct", "latest_return_pct",
    "outcome_status",
}


def _benjamini_hochberg(pvalues: List[float], q: float = 0.05) -> List[bool]:
    n = len(pvalues)
    if n == 0:
        return []
    order = np.argsort(pvalues)
    ranked = np.array(pvalues)[order]
    thresholds = (np.arange(1, n + 1) / n) * q
    significant = ranked <= thresholds
    if not significant.any():
        cutoff = -1
    else:
        cutoff = np.where(significant)[0].max()
    keep_sorted = np.zeros(n, dtype=bool)
    keep_sorted[: cutoff + 1] = True
    keep = np.zeros(n, dtype=bool)
    keep[order] = keep_sorted
    return keep.tolist()


def _cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or len(y) < 2:
        return 0.0
    mx, my = np.nanmean(x), np.nanmean(y)
    vx, vy = np.nanvar(x, ddof=1), np.nanvar(y, ddof=1)
    pooled = np.sqrt(((len(x) - 1) * vx + (len(y) - 1) * vy) / max(len(x) + len(y) - 2, 1))
    if pooled == 0 or np.isnan(pooled):
        return 0.0
    return float((mx - my) / pooled)


def _candidate_features(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        if c in LEAKAGE_BLOCKLIST:
            continue
        if c.startswith("_") or c in ("ticker", "stock_name", "id", "run_id", "scan_date",
                                       "market", "market_type", "market_subtype",
                                       "scan_mode", "strategy_family", "decision",
                                       "decision_bucket", "primary_theme", "feature_origin",
                                       "feature_quality", "feature_missing_fields",
                                       "validation_excluded_reason"):
            continue
        s = df[c]
        if s.dtype.kind not in ("i", "u", "f", "b"):
            continue
        if s.notna().sum() < 30:
            continue
        cols.append(c)
    return cols


def _split_disc_val(df: pd.DataFrame, frac: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
    sub = df.sort_values("scan_date").reset_index(drop=True)
    cut = int(len(sub) * frac)
    return sub.iloc[:cut], sub.iloc[cut:]


def _test_features(df: pd.DataFrame, winner_mask: pd.Series, loser_mask: pd.Series,
                    features: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    win_df = df.loc[winner_mask]
    los_df = df.loc[loser_mask]
    if len(win_df) < 10 or len(los_df) < 10:
        return rows
    for f in features:
        x = pd.to_numeric(win_df[f], errors="coerce").dropna().values
        y = pd.to_numeric(los_df[f], errors="coerce").dropna().values
        if len(x) < 10 or len(y) < 10:
            continue
        try:
            stat, p = mannwhitneyu(x, y, alternative="two-sided")
        except Exception:
            continue
        d = _cohens_d(x, y)
        rows.append({
            "feature": f,
            "n_winner": int(len(x)),
            "n_loser": int(len(y)),
            "winner_median": float(np.nanmedian(x)),
            "loser_median": float(np.nanmedian(y)),
            "winner_mean": float(np.nanmean(x)),
            "loser_mean": float(np.nanmean(y)),
            "cohens_d": round(d, 4),
            "u_stat": float(stat),
            "p_value": float(p),
        })
    if not rows:
        return rows
    fdr_keep = _benjamini_hochberg([r["p_value"] for r in rows], q=0.05)
    for r, keep in zip(rows, fdr_keep):
        r["fdr_significant"] = bool(keep)
    rows.sort(key=lambda r: (-abs(r["cohens_d"]), r["p_value"]))
    return rows


def _segment_analysis(df: pd.DataFrame, segment_label: str, segment_mask: pd.Series,
                        verbose: bool = True) -> Dict[str, Any]:
    sub = df.loc[segment_mask].copy()
    if verbose:
        print(f"\n=== {segment_label}: total {len(sub)} rows ===")
    out: Dict[str, Any] = {"segment": segment_label, "total_rows": int(len(sub)), "winners": {}}
    features = _candidate_features(sub)
    for wd in WINNER_DEFS:
        horizon = wd["horizon"]
        thr = wd["threshold"]
        if horizon not in sub.columns:
            continue
        ret = pd.to_numeric(sub[horizon], errors="coerce")
        valid = sub[ret.notna()].copy()
        if len(valid) < 100:
            continue
        ret_valid = pd.to_numeric(valid[horizon], errors="coerce")
        loser_threshold = float(np.nanquantile(ret_valid, 0.30))
        winner_mask = ret_valid >= thr
        loser_mask = ret_valid <= loser_threshold
        n_w, n_l = int(winner_mask.sum()), int(loser_mask.sum())
        if verbose:
            print(f"  [{wd['key']}] winners (>={thr}%): {n_w}  losers (<={loser_threshold:.2f}%): {n_l}")
        if n_w < 30 or n_l < 30:
            out["winners"][wd["key"]] = {
                "skipped": True,
                "reason": "insufficient_sample",
                "n_winner": n_w, "n_loser": n_l,
            }
            continue

        # Discovery / validation split by time
        disc, val = _split_disc_val(valid)
        disc_ret = pd.to_numeric(disc[horizon], errors="coerce")
        val_ret = pd.to_numeric(val[horizon], errors="coerce")
        disc_loser_thr = float(np.nanquantile(disc_ret, 0.30))
        val_loser_thr = float(np.nanquantile(val_ret, 0.30))

        disc_results = _test_features(
            disc,
            winner_mask=disc_ret >= thr,
            loser_mask=disc_ret <= disc_loser_thr,
            features=features,
        )
        val_results = _test_features(
            val,
            winner_mask=val_ret >= thr,
            loser_mask=val_ret <= val_loser_thr,
            features=features,
        )

        # Replication: a feature is "real" if FDR-significant on discovery
        # AND in validation has cohens_d sign matching disc AND |d| >= 0.2
        val_by_feat = {r["feature"]: r for r in val_results}
        replicated: List[Dict[str, Any]] = []
        for r in disc_results:
            if not r.get("fdr_significant"):
                continue
            v = val_by_feat.get(r["feature"])
            if not v:
                continue
            same_sign = np.sign(r["cohens_d"]) == np.sign(v["cohens_d"]) and abs(v["cohens_d"]) >= 0.2
            if same_sign:
                replicated.append({
                    "feature": r["feature"],
                    "disc_cohens_d": r["cohens_d"],
                    "disc_p": r["p_value"],
                    "val_cohens_d": v["cohens_d"],
                    "val_p": v["p_value"],
                    "winner_median_disc": r["winner_median"],
                    "loser_median_disc": r["loser_median"],
                })

        out["winners"][wd["key"]] = {
            "horizon": horizon,
            "threshold": thr,
            "n_winner": n_w,
            "n_loser": n_l,
            "loser_quantile_threshold": round(loser_threshold, 4),
            "disc_top10": disc_results[:10],
            "val_top10": val_results[:10],
            "replicated": replicated,
            "n_replicated": len(replicated),
        }
        if verbose:
            print(f"    discovery FDR-sig: {sum(1 for r in disc_results if r.get('fdr_significant'))}, replicated in val: {len(replicated)}")
            for r in replicated[:5]:
                print(f"      {r['feature']:>28}: disc d={r['disc_cohens_d']:+.2f} (p={r['disc_p']:.1e}) val d={r['val_cohens_d']:+.2f}")
    return out


def main() -> int:
    print("Loading archive…")
    df = load_scan_archive()
    print("Engineering features…")
    df = engineer_features(df)

    if "market_subtype" in df.columns:
        kr_mask = df["market_subtype"].isin(["KOSPI", "KOSDAQ"])
        kr_mask &= df.get("outcome_status", pd.Series(index=df.index)).fillna("").str.upper().eq("RESOLVED")
        kr_mask &= pd.to_numeric(df.get("alpha_score", pd.Series(index=df.index)), errors="coerce").notna()
        if kr_mask.any():
            print(f"OHLCV derive on {int(kr_mask.sum()):,} KR rows…")
            df = derive_ohlcv_features(df, target_mask=kr_mask, verbose=False)

    segments = []
    if "scan_mode" in df.columns and "market_subtype" in df.columns:
        segments.append(("KOSPI_SWING",
                          (df["market_subtype"].eq("KOSPI") & df["scan_mode"].eq("SWING") &
                           df.get("outcome_status", pd.Series(index=df.index)).fillna("").str.upper().eq("RESOLVED"))))
        segments.append(("KOSDAQ_SWING",
                          (df["market_subtype"].eq("KOSDAQ") & df["scan_mode"].eq("SWING") &
                           df.get("outcome_status", pd.Series(index=df.index)).fillna("").str.upper().eq("RESOLVED"))))

    output: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "winner_definitions": WINNER_DEFS,
        "segments": [],
    }
    for label, mask in segments:
        seg_out = _segment_analysis(df, label, mask, verbose=True)
        output["segments"].append(seg_out)

    out_dir = PROJECT_ROOT / "runtime_state" / "reports" / "learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "winner_pattern_research.json"
    out_json.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote: {out_json}")

    # Quick MD summary
    lines = [f"# Winner pattern research", f"_Generated: {output['generated_at']}_", ""]
    for seg in output["segments"]:
        lines.append(f"## {seg['segment']} (rows={seg['total_rows']:,})")
        for wkey, wres in (seg.get("winners") or {}).items():
            if wres.get("skipped"):
                lines.append(f"- **{wkey}**: skipped — {wres.get('reason')} (n_w={wres.get('n_winner')}, n_l={wres.get('n_loser')})")
                continue
            lines.append(f"- **{wkey}** (winners {wres['n_winner']}, losers {wres['n_loser']}): replicated={wres['n_replicated']}")
            for r in wres.get("replicated", [])[:5]:
                lines.append(f"  - `{r['feature']}` disc d={r['disc_cohens_d']:+.2f} val d={r['val_cohens_d']:+.2f}  win_med={r['winner_median_disc']:.2f} los_med={r['loser_median_disc']:.2f}")
        lines.append("")
    (out_dir / "winner_pattern_research.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
