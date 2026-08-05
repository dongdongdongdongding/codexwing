#!/usr/bin/env python3
"""A4: Live meta-calibration 2-layer learning, first pass (observation-only).

Pre-registered 2026-07-07: learn a second-layer calibrator that predicts
forward (live-settled) outcomes from pick-time meta features
(lane, tier, regime, p, market, liquidity) -- i.e. learn the
live-vs-backtest gap itself.

Data: settled rows of the live shadow ledgers in
runtime_state/reports/experimental/ (plus the retired swing_ensemble
ledger as extra training sample, distinguished by a lane dummy).

Nested model comparison (logistic, 5-fold date-grouped CV, 3 seeds):
  (a) lane base rate only
  (b) lane + p
  (c) lane + p + meta (tier, mkt_state, market, log-liquidity)
  (bn) lane + p + noise placebo  (per Section-19 discipline: a meta
       increment only counts if it beats the noise increment)
Shallow GBM run as robustness for (b)/(c).

Observation-only: writes a report, changes no display/consumer code.
Outputs:
  runtime_state/reports/validation/live_meta_calibration_latest.md
  runtime_state/reports/validation/live_meta_calibration_latest.json
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "runtime_state" / "reports" / "experimental"
OUT_DIR = REPO / "runtime_state" / "reports" / "validation"
SEEDS = [0, 1, 2]
N_FOLDS = 5

# lane -> (file, gross-return field, round-trip cost in %, live flag)
LANES = {
    "kr_swing_candidate": ("kr_swing_candidate_ledger.jsonl", "policy_ret", 0.30, True),
    "kospi_intraday": ("kospi_intraday_swing_ledger.jsonl", "exit_t5_h5", 0.30, True),
    "kosdaq_intraday_vwap": ("kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl", "exit_t10_h5", 0.33, True),
    "swing_ensemble(retired)": ("swing_ensemble_ledger.jsonl", "first_touch_ret", 0.30, False),
}


def load_rows() -> pd.DataFrame:
    recs = []
    for lane, (fname, ret_field, cost, live) in LANES.items():
        for line in (EXP / fname).open():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            gross = r.get(ret_field)
            if gross is None:
                continue  # unsettled
            liq = r.get("liq_eok", r.get("liq억", r.get("liq_prev_eok")))
            recs.append(
                {
                    "lane": lane,
                    "live": live,
                    "date": r["date"],
                    "ticker": r.get("ticker"),
                    "p": float(r["p"]),
                    "p_raw": r.get("p_raw"),
                    "tier": r.get("tier") or "NONE",
                    "mkt_state": r.get("mkt_state") or "UNKNOWN",
                    "market": r.get("market") or "NA",
                    "liq_eok": float(liq) if liq is not None else np.nan,
                    "gross": float(gross),
                    "net": float(gross) - cost,
                }
            )
    df = pd.DataFrame(recs)
    df["win"] = (df["net"] > 0).astype(int)
    df["log_liq"] = np.log10(df["liq_eok"].clip(lower=1.0))
    df["log_liq"] = df["log_liq"].fillna(df["log_liq"].median())
    return df


# ---------------------------------------------------------------- features
def onehot(df: pd.DataFrame, col: str, cats: list[str]) -> np.ndarray:
    return np.column_stack([(df[col] == c).astype(float).to_numpy() for c in cats[:-1]])


def build_design(df: pd.DataFrame, spec: str, noise: np.ndarray | None = None):
    lanes = sorted(df["lane"].unique())
    tiers = sorted(df["tier"].unique())
    states = sorted(df["mkt_state"].unique())
    markets = sorted(df["market"].unique())
    blocks = [onehot(df, "lane", lanes)] if len(lanes) > 1 else [np.ones((len(df), 1))]
    if spec in ("lane_p", "lane_p_meta", "lane_p_noise"):
        blocks.append(df[["p"]].to_numpy())
    if spec == "lane_p_meta":
        if len(tiers) > 1:
            blocks.append(onehot(df, "tier", tiers))
        if len(states) > 1:
            blocks.append(onehot(df, "mkt_state", states))
        if len(markets) > 1:
            blocks.append(onehot(df, "market", markets))
        blocks.append(df[["log_liq"]].to_numpy())
    if spec == "lane_p_noise":
        assert noise is not None
        blocks.append(noise.reshape(-1, 1))
    return np.column_stack(blocks)


# ---------------------------------------------------------------- CV engine
def oof_predict(df: pd.DataFrame, spec: str, seed: int, model_kind: str = "logit") -> np.ndarray:
    """Out-of-fold win-probability predictions, date-grouped 5-fold CV."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(df))
    y = df["win"].to_numpy()
    oof = np.full(len(df), np.nan)
    gkf = GroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    groups = df["date"].to_numpy()
    for tr, te in gkf.split(df, y, groups):
        tr_df, te_df = df.iloc[tr], df.iloc[te]
        if spec == "lane_base":
            # pure lane base rate from training fold (Laplace-smoothed)
            gm = (tr_df["win"].sum() + 1) / (len(tr_df) + 2)
            rates = tr_df.groupby("lane")["win"].agg(["sum", "count"])
            lane_rate = {ln: (s + 1) / (c + 2) for ln, (s, c) in rates.iterrows()}
            oof[te] = [lane_rate.get(ln, gm) for ln in te_df["lane"]]
            continue
        if spec == "tier_base":
            # current-display analogue: lane x tier measured win rate
            gm = (tr_df["win"].sum() + 1) / (len(tr_df) + 2)
            rates = tr_df.groupby(["lane", "tier"])["win"].agg(["sum", "count"])
            grp_rate = {k: (s + 1) / (c + 2) for k, (s, c) in rates.iterrows()}
            lrates = tr_df.groupby("lane")["win"].agg(["sum", "count"])
            lane_rate = {ln: (s + 1) / (c + 2) for ln, (s, c) in lrates.iterrows()}
            oof[te] = [
                grp_rate.get((ln, ti), lane_rate.get(ln, gm))
                for ln, ti in zip(te_df["lane"], te_df["tier"])
            ]
            continue
        if spec == "raw_p":
            oof[te] = te_df["p"].clip(0.01, 0.99).to_numpy()
            continue
        Xtr = build_design(tr_df, spec, noise[tr] if spec == "lane_p_noise" else None)
        Xte_full = build_design(df, spec, noise if spec == "lane_p_noise" else None)
        # rebuild train/test from a single global design so category maps match
        Xtr, Xte = Xte_full[tr], Xte_full[te]
        if tr_df["win"].nunique() < 2:
            oof[te] = tr_df["win"].mean()
            continue
        if model_kind == "logit":
            m = LogisticRegression(C=1.0, max_iter=2000, random_state=seed)
        else:
            m = GradientBoostingClassifier(
                n_estimators=100, max_depth=2, learning_rate=0.05,
                subsample=0.8, random_state=seed,
            )
        m.fit(Xtr, tr_df["win"])
        oof[te] = m.predict_proba(Xte)[:, 1]
    return oof


def score(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    out = {
        "brier": float(brier_score_loss(y, p)),
        "logloss": float(log_loss(y, p)),
    }
    out["auc"] = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan")
    return out


def run_suite(df: pd.DataFrame, label: str) -> dict:
    y = df["win"].to_numpy()
    specs = [
        ("raw_p", "logit"),
        ("lane_base", "-"),
        ("tier_base", "-"),
        ("lane_p", "logit"),
        ("lane_p_noise", "logit"),
        ("lane_p_meta", "logit"),
        ("lane_p", "gbm"),
        ("lane_p_meta", "gbm"),
    ]
    res = {}
    for spec, kind in specs:
        per_seed = []
        for seed in SEEDS:
            oof = oof_predict(df, spec, seed, kind if kind != "-" else "logit")
            per_seed.append(score(y, oof))
        key = f"{spec}[{kind}]" if kind == "gbm" else spec
        res[key] = {
            m: {
                "mean": float(np.mean([s[m] for s in per_seed])),
                "std": float(np.std([s[m] for s in per_seed])),
            }
            for m in ("brier", "logloss", "auc")
        }
    return {"label": label, "n": int(len(df)), "win_rate": float(y.mean()), "models": res}


# ---------------------------------------------------------------- regression
def regression_suite(df: pd.DataFrame) -> dict:
    """OOF corr / R^2 of net-return regression, same nested feature sets."""
    from sklearn.linear_model import Ridge

    y = df["net"].to_numpy()
    out = {}
    for spec in ("lane_base", "lane_p", "lane_p_meta", "lane_p_noise"):
        per_seed = []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            noise = rng.standard_normal(len(df))
            oof = np.full(len(df), np.nan)
            gkf = GroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
            for tr, te in gkf.split(df, y, df["date"].to_numpy()):
                tr_df = df.iloc[tr]
                if spec == "lane_base":
                    gm = tr_df["net"].mean()
                    lane_mean = tr_df.groupby("lane")["net"].mean().to_dict()
                    oof[te] = [lane_mean.get(ln, gm) for ln in df.iloc[te]["lane"]]
                    continue
                X = build_design(df, spec, noise if spec == "lane_p_noise" else None)
                m = Ridge(alpha=1.0)
                m.fit(X[tr], y[tr])
                oof[te] = m.predict(X[te])
            ss_res = float(np.sum((y - oof) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            corr = float(np.corrcoef(oof, y)[0, 1]) if np.std(oof) > 1e-9 else float("nan")
            per_seed.append({"r2_oof": 1 - ss_res / ss_tot, "corr": corr})
        out[spec] = {
            k: {"mean": float(np.mean([s[k] for s in per_seed])),
                "std": float(np.std([s[k] for s in per_seed]))}
            for k in ("r2_oof", "corr")
        }
    return out


# ---------------------------------------------------------------- diagnostics
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def per_lane_diagnostics(df: pd.DataFrame) -> dict:
    out = {}
    bins = [(0.0, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]
    for lane, g in df.groupby("lane"):
        y, p = g["win"].to_numpy(), g["p"].to_numpy()
        d = {
            "n": int(len(g)),
            "win_rate": float(y.mean()),
            "mean_net": float(g["net"].mean()),
            "mean_p": float(p.mean()),
            "auc_p": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 and len(np.unique(p)) > 1 else float("nan"),
            "spearman_p_net": float(g[["p", "net"]].corr(method="spearman").iloc[0, 1]) if len(np.unique(p)) > 1 else float("nan"),
            "curve": [],
        }
        for lo, hi in bins:
            m = (p >= lo) & (p < hi)
            n, k = int(m.sum()), int(y[m].sum())
            if n == 0:
                continue
            lo_ci, hi_ci = wilson(k, n)
            d["curve"].append(
                {"bin": f"[{lo:.1f},{hi if hi <= 1 else 1.0:.1f})", "n": n,
                 "mean_p": float(p[m].mean()), "win_rate": k / n,
                 "ci_lo": lo_ci, "ci_hi": hi_ci}
            )
        out[lane] = d
    return out


def tier_regime_diagnostics(df: pd.DataFrame) -> dict:
    out = {}
    for col in ("tier", "mkt_state"):
        rows = []
        for (lane, v), g in df.groupby(["lane", col]):
            k, n = int(g["win"].sum()), len(g)
            lo, hi = wilson(k, n)
            rows.append({"lane": lane, col: v, "n": n, "win_rate": k / n,
                         "ci_lo": lo, "ci_hi": hi, "mean_net": float(g["net"].mean())})
        out[col] = rows
    return out


# ---------------------------------------------------------------- report
def fmt_models(res: dict) -> str:
    lines = ["| model | Brier | logloss | AUC |", "|---|---|---|---|"]
    for name, m in res["models"].items():
        lines.append(
            f"| {name} | {m['brier']['mean']:.4f} ± {m['brier']['std']:.4f} "
            f"| {m['logloss']['mean']:.4f} ± {m['logloss']['std']:.4f} "
            f"| {m['auc']['mean']:.3f} ± {m['auc']['std']:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    df = load_rows()
    live = df[df["live"]].reset_index(drop=True)
    pooled = df.reset_index(drop=True)

    results = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "seeds": SEEDS, "folds": N_FOLDS, "cv": "date-grouped GroupKFold",
        "win_def": "gross_ret > round-trip cost (0.30 / 0.33 kosdaq_vwap)",
        "live": run_suite(live, "LIVE lanes only"),
        "pooled": run_suite(pooled, "LIVE + retired ensemble"),
        "regression_live": regression_suite(live),
        "per_lane": per_lane_diagnostics(live),
        "tier_regime": tier_regime_diagnostics(live),
        "lane_counts": df.groupby(["lane", "live"]).size().reset_index(name="n").to_dict("records"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "live_meta_calibration_latest.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=float)
    )
    print(json.dumps(results["live"]["models"], indent=2))
    print("live n =", results["live"]["n"], "pooled n =", results["pooled"]["n"])


if __name__ == "__main__":
    main()
