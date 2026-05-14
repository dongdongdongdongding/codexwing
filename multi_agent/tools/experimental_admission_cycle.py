#!/usr/bin/env python3
"""Internal admission-rule search for high target-touch win-rate cohorts.

This is a shadow-only research cycle. It does not update scanner ranking,
model artifacts, Supabase rows, Discord, or Streamlit output.

The objective is deliberately stricter than close-return win rate:

    Did the candidate show meaningful upside while staying inside the stop?

For archive-only runs the 5D labels are conservative path proxies:
``max_high_return_5d_pct >= target`` and ``min_return_observed_pct > -stop``.
That means a stock that reached target and later hit stop is not counted as a
clean winner unless ordered OHLCV validation is run separately.
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
DEFAULT_OUTPUT = ROOT / "runtime_state/reports/experimental/admission_cycle_70pct.json"

EXPERIMENT_VERSION = "admission_cycle_target_touch_v1"


@dataclass(frozen=True)
class LabelProfile:
    name: str
    horizon_days: int
    target_pct: float
    stop_pct: float
    reward_risk: float
    label_kind: str


LABEL_PROFILES: Tuple[LabelProfile, ...] = (
    LabelProfile("1D_close_3v3_no_5d_stop", 1, 3.0, 3.0, 1.0, "close_and_no_stop_proxy"),
    LabelProfile("3D_close_5v3_no_5d_stop", 3, 5.0, 3.0, 1.67, "close_and_no_stop_proxy"),
    LabelProfile("5D_clean_10v5", 5, 10.0, 5.0, 2.0, "mfe_without_stop_proxy"),
    LabelProfile("5D_clean_15v5", 5, 15.0, 5.0, 3.0, "mfe_without_stop_proxy"),
)

NUMERIC_FEATURES: Tuple[str, ...] = (
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "decision_score",
    "whale_score",
    "volume_ratio",
    "expected_edge_score",
    "expected_return_1d_pct",
    "expected_return_3d_pct",
    "relative_rank_score",
    "relative_rank_pct",
    "loss_risk_score",
    "low_model_prob_score",
    "low_prob_high_score",
    "expected_edge_inversion_score",
    "priority_rank",
    "day_return_pct",
    "conviction_score",
    "regime_breadth_pct",
    "regime_avg_chg",
    "regime_volatility_20d",
    "model_prob_mean",
    "phase25_prob",
    "phase25_shadow_prob",
)

CATEGORICAL_FEATURES: Tuple[str, ...] = (
    "trend",
    "position",
    "tier",
    "selection_lane",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "feature_quality",
    "feature_origin",
    "market_gate",
    "volume_confirmed",
    "explosive_leader_flag",
    "core_trend_flag",
    "explosive_eligible",
)


def _safe_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value: Any, digits: int = 4) -> float | None:
    number = _safe_float(value)
    return round(number, digits) if number is not None else None


def _load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"input not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in NUMERIC_FEATURES + (
        "return_1d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "max_high_return_5d_pct",
        "min_return_observed_pct",
        "entry_reference_price",
    ):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    scan_mode = df.get("scan_mode", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    ticker = df.get("ticker", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    market_type = df.get("market_type", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    kr_ticker = ticker.str.endswith(".KS") | ticker.str.endswith(".KQ")
    mask = scan_mode.eq("SWING") & (kr_ticker | market_type.eq("KR"))
    if "is_dummy_data" in df.columns:
        mask &= ~_safe_bool(df["is_dummy_data"])
    out = df.loc[mask].copy()
    out["market2"] = "UNKNOWN"
    out.loc[ticker.loc[out.index].str.endswith(".KS"), "market2"] = "KOSPI"
    out.loc[ticker.loc[out.index].str.endswith(".KQ"), "market2"] = "KOSDAQ"
    if "market" in out.columns:
        market = out["market"].fillna("").astype(str).str.upper()
        out.loc[out["market2"].eq("UNKNOWN") & market.isin(["KOSPI", "KOSDAQ"]), "market2"] = market

    rec = out.get("recommended_at", pd.Series(index=out.index, dtype=object))
    created = out.get("created_at", pd.Series(index=out.index, dtype=object))
    base = out.get("base_trade_date", pd.Series(index=out.index, dtype=object))
    rec = rec.where(rec.notna() & rec.astype(str).str.len().gt(0), base)
    rec = rec.where(rec.notna() & rec.astype(str).str.len().gt(0), created)
    out["trade_date"] = pd.to_datetime(rec, errors="coerce").dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    return out.sort_values(["trade_date", "ticker", "run_id"], na_position="last").copy()


def _decision_masks(df: pd.DataFrame) -> Dict[str, pd.Series]:
    decision = df.get("decision", pd.Series("", index=df.index)).fillna("").astype(str).str.upper()
    bucket = df.get("decision_bucket", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    rank = df.get("priority_rank", pd.Series(float("nan"), index=df.index))
    exception = bucket.eq("exception_leader") | decision.eq("EXCEPTION_LEADER")
    top5 = rank.between(1, 5, inclusive="both") & ~exception
    return {
        "All": pd.Series(True, index=df.index),
        "Top1": rank.eq(1) & ~exception,
        "Top3": rank.between(1, 3, inclusive="both") & ~exception,
        "Top5": top5,
        "Exception Leader": exception,
        "Top5+Exception": top5 | exception,
    }


def _label_series(df: pd.DataFrame, profile: LabelProfile) -> Tuple[pd.Series, pd.Series]:
    stop = df.get("min_return_observed_pct", pd.Series(float("nan"), index=df.index))
    no_stop = stop.gt(-abs(profile.stop_pct))
    if profile.label_kind == "mfe_without_stop_proxy":
        mfe = df.get("max_high_return_5d_pct", pd.Series(float("nan"), index=df.index))
        valid = mfe.notna() & stop.notna()
        label = mfe.ge(profile.target_pct) & no_stop
        return label.fillna(False), valid
    close_col = f"return_{profile.horizon_days}d_pct"
    close_ret = df.get(close_col, pd.Series(float("nan"), index=df.index))
    valid = close_ret.notna() & stop.notna()
    label = close_ret.ge(profile.target_pct) & no_stop
    return label.fillna(False), valid


def _split_train_test(df: pd.DataFrame, train_ratio: float) -> Tuple[pd.Series, pd.Series, str | None]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < 3:
        return pd.Series(False, index=df.index), pd.Series(False, index=df.index), None
    cut_idx = max(1, min(len(days) - 1, int(len(days) * train_ratio)))
    cut_day = days[cut_idx]
    train = df["trade_date"].astype(str).lt(cut_day)
    test = df["trade_date"].astype(str).ge(cut_day)
    return train, test, cut_day


def _condition_candidates(df: pd.DataFrame, base_mask: pd.Series, *, max_conditions: int) -> List[Tuple[str, pd.Series]]:
    rows: List[Tuple[str, pd.Series]] = []

    def add(name: str, series: pd.Series) -> None:
        mask = series.fillna(False) & base_mask
        if int(mask.sum()) > 0:
            rows.append((name, mask))

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            continue
        values = df.loc[base_mask, col].dropna()
        if len(values) < 20:
            continue
        thresholds = sorted(set(float(v) for v in values.quantile([0.2, 0.35, 0.5, 0.65, 0.8]).round(6).tolist()))
        for threshold in thresholds:
            add(f"{col}>={threshold:g}", df[col].ge(threshold))
            add(f"{col}<={threshold:g}", df[col].le(threshold))

    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            continue
        text = df[col].fillna("").astype(str)
        for value in text.loc[base_mask].value_counts().head(10).index.tolist():
            if not value or value.lower() in {"nan", "none", "null", "unknown"}:
                continue
            add(f"{col}={value}", text.eq(value))

    return rows[:max_conditions]


def _metrics(df: pd.DataFrame, mask: pd.Series, label: pd.Series, valid: pd.Series) -> Dict[str, Any]:
    idx = mask & valid
    sub = df.loc[idx]
    wins = label.loc[idx]
    n = int(len(sub))
    if n == 0:
        return {
            "n": 0,
            "win_rate_pct": None,
            "avg_return_5d_pct": None,
            "avg_mfe_5d_pct": None,
            "avg_mae_5d_pct": None,
            "stop5_pct": None,
            "avg_1d_pct": None,
            "avg_3d_pct": None,
        }
    stop = sub.get("min_return_observed_pct", pd.Series(float("nan"), index=sub.index)).le(-5.0)
    return {
        "n": n,
        "win_rate_pct": round(float(wins.mean() * 100.0), 3),
        "avg_return_5d_pct": _round(sub.get("return_5d_pct", pd.Series(index=sub.index)).mean(), 4),
        "avg_mfe_5d_pct": _round(sub.get("max_high_return_5d_pct", pd.Series(index=sub.index)).mean(), 4),
        "avg_mae_5d_pct": _round(sub.get("min_return_observed_pct", pd.Series(index=sub.index)).mean(), 4),
        "stop5_pct": round(float(stop.mean() * 100.0), 3),
        "avg_1d_pct": _round(sub.get("return_1d_pct", pd.Series(index=sub.index)).mean(), 4),
        "avg_3d_pct": _round(sub.get("return_3d_pct", pd.Series(index=sub.index)).mean(), 4),
    }


def _score_candidate(test_metrics: Dict[str, Any]) -> Tuple[float, float, int]:
    win = float(test_metrics.get("win_rate_pct") or 0.0)
    avg_ret = float(test_metrics.get("avg_return_5d_pct") or -999.0)
    n = int(test_metrics.get("n") or 0)
    return (win, avg_ret, n)


def _search_rules(
    df: pd.DataFrame,
    *,
    profile: LabelProfile,
    market: str,
    cohort: str,
    base_mask: pd.Series,
    max_depth: int,
    beam_width: int,
    min_train: int,
    min_test: int,
    max_conditions: int,
    train_ratio: float,
) -> List[Dict[str, Any]]:
    label, valid = _label_series(df, profile)
    working = df.loc[base_mask & valid].copy()
    if len(working) < min_train + min_test:
        return []
    train_mask, test_mask, cut_day = _split_train_test(working, train_ratio)
    train_mask = train_mask.reindex(df.index, fill_value=False)
    test_mask = test_mask.reindex(df.index, fill_value=False)
    candidates = _condition_candidates(df, base_mask & valid, max_conditions=max_conditions)

    baseline = {
        "market": market,
        "cohort": cohort,
        "profile": profile.name,
        "conditions": ["BASE"],
        "condition_count": 0,
        "split_cut_day": cut_day,
        "train": _metrics(df, base_mask & train_mask, label, valid),
        "test": _metrics(df, base_mask & test_mask, label, valid),
        "label_profile": asdict(profile),
    }
    rows: List[Dict[str, Any]] = [baseline]
    beam: List[Tuple[Tuple[str, ...], pd.Series]] = [(tuple(), base_mask)]
    seen = {tuple()}

    for _depth in range(1, max_depth + 1):
        next_beam: List[Tuple[Tuple[str, ...], pd.Series, Dict[str, Any]]] = []
        for names, mask in beam:
            start = 0
            if names:
                last_name = names[-1]
                for idx, (candidate_name, _candidate_mask) in enumerate(candidates):
                    if candidate_name == last_name:
                        start = idx + 1
                        break
            for name, cond in candidates[start:]:
                combo = tuple(list(names) + [name])
                if combo in seen:
                    continue
                seen.add(combo)
                combo_mask = mask & cond
                train_metrics = _metrics(df, combo_mask & train_mask, label, valid)
                test_metrics = _metrics(df, combo_mask & test_mask, label, valid)
                if int(train_metrics["n"] or 0) < min_train or int(test_metrics["n"] or 0) < min_test:
                    continue
                row = {
                    "market": market,
                    "cohort": cohort,
                    "profile": profile.name,
                    "conditions": list(combo),
                    "condition_count": len(combo),
                    "split_cut_day": cut_day,
                    "train": train_metrics,
                    "test": test_metrics,
                    "label_profile": asdict(profile),
                }
                rows.append(row)
                next_beam.append((combo, combo_mask, row))
        next_beam.sort(key=lambda item: _score_candidate(item[2]["train"]), reverse=True)
        beam = [(names, mask) for names, mask, _row in next_beam[:beam_width]]
        if not beam:
            break

    return sorted(rows, key=lambda row: _score_candidate(row["test"]), reverse=True)


def _try_ml_shadow(
    df: pd.DataFrame,
    *,
    profile: LabelProfile,
    base_mask: pd.Series,
    market: str,
    cohort: str,
    min_train: int,
    min_test: int,
    train_ratio: float,
) -> List[Dict[str, Any]]:
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
    except Exception:
        return []

    label, valid = _label_series(df, profile)
    work = df.loc[base_mask & valid].copy()
    if len(work) < min_train + min_test:
        return []
    train_mask, test_mask, cut_day = _split_train_test(work, train_ratio)
    train_idx = work.index[train_mask]
    test_idx = work.index[test_mask]
    if len(train_idx) < min_train or len(test_idx) < min_test:
        return []
    y_train = label.loc[train_idx].astype(int)
    if y_train.nunique() < 2:
        return []

    numeric = [col for col in NUMERIC_FEATURES if col in df.columns]
    categorical = [col for col in CATEGORICAL_FEATURES if col in df.columns]
    x_train = df.loc[train_idx, numeric + categorical].copy()
    x_test = df.loc[test_idx, numeric + categorical].copy()
    for col in categorical:
        x_train[col] = x_train[col].fillna("UNKNOWN").astype(str)
        x_test[col] = x_test[col].fillna("UNKNOWN").astype(str)

    pre = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
    )
    models = {
        "extra_trees_shadow": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gb_shadow": HistGradientBoostingClassifier(
            max_iter=150,
            max_depth=3,
            learning_rate=0.05,
            l2_regularization=0.2,
            random_state=42,
        ),
    }
    rows: List[Dict[str, Any]] = []
    for name, model in models.items():
        pipe = Pipeline([("pre", pre), ("model", model)])
        try:
            pipe.fit(x_train, y_train)
            train_prob = pipe.predict_proba(x_train)[:, 1]
            test_prob = pipe.predict_proba(x_test)[:, 1]
        except Exception:
            continue
        for quantile in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9):
            threshold = float(pd.Series(train_prob).quantile(quantile))
            train_select = pd.Series(train_prob >= threshold, index=train_idx).reindex(df.index, fill_value=False)
            test_select = pd.Series(test_prob >= threshold, index=test_idx).reindex(df.index, fill_value=False)
            train_metrics = _metrics(df, train_select, label, valid)
            test_metrics = _metrics(df, test_select, label, valid)
            if int(train_metrics["n"] or 0) < min_train or int(test_metrics["n"] or 0) < min_test:
                continue
            rows.append(
                {
                    "market": market,
                    "cohort": cohort,
                    "profile": profile.name,
                    "model": name,
                    "conditions": [f"{name}_prob>=train_q{quantile:g}:{threshold:.4f}"],
                    "condition_count": 1,
                    "split_cut_day": cut_day,
                    "train": train_metrics,
                    "test": test_metrics,
                    "label_profile": asdict(profile),
                }
            )
    return sorted(rows, key=lambda row: _score_candidate(row["test"]), reverse=True)


def build_report(
    df: pd.DataFrame,
    *,
    max_depth: int,
    beam_width: int,
    min_train: int,
    min_test: int,
    max_conditions: int,
    train_ratio: float,
    top_n: int,
    run_ml: bool,
) -> Dict[str, Any]:
    markets = ["KOSPI", "KOSDAQ"]
    all_rows: List[Dict[str, Any]] = []
    baselines: List[Dict[str, Any]] = []
    for market in markets:
        market_mask = df["market2"].eq(market)
        for cohort, cohort_mask in _decision_masks(df).items():
            base = market_mask & cohort_mask
            for profile in LABEL_PROFILES:
                searched = _search_rules(
                    df,
                    profile=profile,
                    market=market,
                    cohort=cohort,
                    base_mask=base,
                    max_depth=max_depth,
                    beam_width=beam_width,
                    min_train=min_train,
                    min_test=min_test,
                    max_conditions=max_conditions,
                    train_ratio=train_ratio,
                )
                if searched:
                    baselines.append(searched[0])
                    all_rows.extend(searched)
                if run_ml:
                    all_rows.extend(
                        _try_ml_shadow(
                            df,
                            profile=profile,
                            base_mask=base,
                            market=market,
                            cohort=cohort,
                            min_train=min_train,
                            min_test=min_test,
                            train_ratio=train_ratio,
                        )
                    )

    champions = sorted(all_rows, key=lambda row: _score_candidate(row["test"]), reverse=True)[:top_n]
    above_70 = [
        row
        for row in champions
        if row.get("test", {}).get("win_rate_pct") is not None and float(row["test"]["win_rate_pct"]) >= 70.0
    ]
    stable_60_70 = [
        row
        for row in above_70
        if float(row.get("train", {}).get("win_rate_pct") or 0.0) >= 60.0
        and int(row.get("train", {}).get("n") or 0) >= min_train
        and int(row.get("test", {}).get("n") or 0) >= min_test
    ]
    strict_70_70 = [
        row for row in stable_60_70 if float(row.get("train", {}).get("win_rate_pct") or 0.0) >= 70.0
    ]
    return {
        "report_version": EXPERIMENT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_only_not_production",
        "input_rows": int(len(df)),
        "search_config": {
            "max_depth": max_depth,
            "beam_width": beam_width,
            "min_train": min_train,
            "min_test": min_test,
            "max_conditions": max_conditions,
            "train_ratio": train_ratio,
            "run_ml": run_ml,
        },
        "label_profiles": [asdict(profile) for profile in LABEL_PROFILES],
        "champions": champions,
        "above_70pct_holdout": above_70,
        "stable_60train_70test": stable_60_70,
        "strict_70train_70test": strict_70_70,
        "notes": [
            "This is an internal admission cycle only; production scanner logic is unchanged.",
            "5D clean labels use archive high/low proxy: target MFE reached and stop MAE not breached.",
            "1D/3D labels use close-return target plus no 5D stop breach, so they are conservative but not exact intraday order labels.",
            "Primary theme values are intentionally excluded from rule features because themes rotate and fixed-theme rules overfit.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Admission Cycle 70pct Shadow Search",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- mode: `{report.get('mode')}`",
        f"- input_rows: `{report.get('input_rows')}`",
        f"- config: `{report.get('search_config')}`",
        "",
        "## Holdout Champions",
        "",
    ]
    headers = [
        "rank",
        "market",
        "cohort",
        "profile",
        "test_n",
        "test_win",
        "test_avg_5d",
        "test_stop5",
        "train_n",
        "train_win",
        "conditions",
    ]
    rows = report.get("champions") if isinstance(report.get("champions"), list) else []
    if rows:
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for idx, row in enumerate(rows[:30], start=1):
            train = row.get("train") or {}
            test = row.get("test") or {}
            values = [
                idx,
                row.get("market"),
                row.get("cohort"),
                row.get("profile"),
                test.get("n"),
                test.get("win_rate_pct"),
                test.get("avg_return_5d_pct"),
                test.get("stop5_pct"),
                train.get("n"),
                train.get("win_rate_pct"),
                "<br>".join(row.get("conditions") or []),
            ]
            lines.append("| " + " | ".join(str(v) for v in values) + " |")
    else:
        lines.append("No champions found.")
    lines.extend(["", "## 70pct+ Holdout Candidates", ""])
    above = report.get("above_70pct_holdout") if isinstance(report.get("above_70pct_holdout"), list) else []
    if above:
        for row in above[:20]:
            test = row.get("test") or {}
            train = row.get("train") or {}
            lines.append(
                f"- `{row.get('market')}` / `{row.get('cohort')}` / `{row.get('profile')}`: "
                f"test win `{test.get('win_rate_pct')}`% n=`{test.get('n')}`, "
                f"train win `{train.get('win_rate_pct')}`% n=`{train.get('n')}`; "
                f"conditions={row.get('conditions')}"
            )
    else:
        lines.append("- No holdout candidate reached 70% with the current min sample constraints.")
    lines.extend(["", "## Stable Candidates", ""])
    stable = report.get("stable_60train_70test") if isinstance(report.get("stable_60train_70test"), list) else []
    if stable:
        for row in stable[:20]:
            test = row.get("test") or {}
            train = row.get("train") or {}
            lines.append(
                f"- `train>=60/test>=70`: `{row.get('market')}` / `{row.get('cohort')}` / `{row.get('profile')}` "
                f"test `{test.get('win_rate_pct')}`% n=`{test.get('n')}`, "
                f"train `{train.get('win_rate_pct')}`% n=`{train.get('n')}`, "
                f"stop5 `{test.get('stop5_pct')}`%, conditions={row.get('conditions')}"
            )
    else:
        lines.append("- No candidate met train>=60% and test>=70%.")
    strict = report.get("strict_70train_70test") if isinstance(report.get("strict_70train_70test"), list) else []
    lines.extend(["", "## Strict 70/70 Candidates", ""])
    if strict:
        for row in strict[:20]:
            test = row.get("test") or {}
            train = row.get("train") or {}
            lines.append(
                f"- `{row.get('market')}` / `{row.get('cohort')}` / `{row.get('profile')}` "
                f"test `{test.get('win_rate_pct')}`% n=`{test.get('n')}`, "
                f"train `{train.get('win_rate_pct')}`% n=`{train.get('n')}`, conditions={row.get('conditions')}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.impute")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--beam-width", type=int, default=150)
    parser.add_argument("--min-train", type=int, default=20)
    parser.add_argument("--min-test", type=int, default=8)
    parser.add_argument("--max-conditions", type=int, default=180)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--top-n", type=int, default=80)
    parser.add_argument("--no-ml", action="store_true")
    args = parser.parse_args()

    df = _load_dataset(Path(args.input))
    report = build_report(
        df,
        max_depth=int(args.max_depth),
        beam_width=int(args.beam_width),
        min_train=int(args.min_train),
        min_test=int(args.min_test),
        max_conditions=int(args.max_conditions),
        train_ratio=float(args.train_ratio),
        top_n=int(args.top_n),
        run_ml=not bool(args.no_ml),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, output.with_suffix(".md"))
    print(
        json.dumps(
            {
                "output": str(output),
                "champions": len(report["champions"]),
                "above_70pct_holdout": len(report["above_70pct_holdout"]),
                "stable_60train_70test": len(report["stable_60train_70test"]),
                "strict_70train_70test": len(report["strict_70train_70test"]),
                "best": report["champions"][0] if report["champions"] else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
