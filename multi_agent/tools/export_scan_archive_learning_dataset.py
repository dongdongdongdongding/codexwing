from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.agents.kr_quant_reranker import is_kr_explosive_leader_eligible
from modules.db_schema import REQUIRED_FEATURE_FIELDS_FOR_TRAINING


RETURN_COLS = [
    "return_30m_pct",
    "return_1h_pct",
    "return_close_pct",
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "return_14d_pct",
    "return_30d_pct",
]


def _infer_decision_bucket(df: pd.DataFrame) -> pd.Series:
    if "decision" in df.columns:
        decision = df["decision"].fillna("").astype(str).str.upper()
        inferred = pd.Series("unknown", index=df.index, dtype="object")
        inferred = inferred.mask(decision.eq("EXCEPTION_LEADER"), "exception_leader")
        inferred = inferred.mask(decision.isin(["WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"]), "watchlist")
        inferred = inferred.mask(decision.isin(["PRIORITY_WATCHLIST"]), "picked")
        return inferred.fillna("unknown").astype(str)
    if "decision_bucket" in df.columns:
        return df["decision_bucket"].fillna("unknown").astype(str)
    return pd.Series("unknown", index=df.index, dtype="object")


def _price_band(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    out = pd.Series("unknown", index=series.index, dtype="object")
    out = out.mask(numeric.gt(0) & numeric.le(7), "le_7")
    out = out.mask(numeric.gt(7) & numeric.le(15), "7_15")
    out = out.mask(numeric.gt(15), "gt_15")
    return out


def _infer_selection_lane(df: pd.DataFrame) -> pd.Series:
    existing = df["selection_lane"] if "selection_lane" in df.columns else pd.Series(index=df.index, dtype="object")
    lane = existing.fillna("").astype(str).str.lower()
    horizon = df["target_horizon_days"] if "target_horizon_days" in df.columns else pd.Series(index=df.index, dtype="float")
    scan_mode = df["scan_mode"] if "scan_mode" in df.columns else pd.Series(index=df.index, dtype="object")
    scan_mode = scan_mode.fillna("").astype(str).str.upper()
    horizon_numeric = pd.to_numeric(horizon, errors="coerce")

    inferred = pd.Series("3d", index=df.index, dtype="object")
    inferred = inferred.mask(scan_mode.eq("INTRADAY"), "1d")
    inferred = inferred.mask(horizon_numeric.le(1), "1d")
    inferred = inferred.mask(lane.isin(["1d", "3d"]), lane)
    return inferred


def _infer_target_horizon_days(df: pd.DataFrame) -> pd.Series:
    if "target_horizon_days" in df.columns:
        existing = pd.to_numeric(df["target_horizon_days"], errors="coerce")
    else:
        existing = pd.Series(index=df.index, dtype="float")
    inferred_lane = _infer_selection_lane(df)
    fallback = inferred_lane.map({"1d": 1, "3d": 3}).fillna(3)
    return existing.fillna(fallback).astype(int)


def _infer_scanner_timeframe_profile(df: pd.DataFrame) -> pd.Series:
    existing = df["scanner_timeframe_profile"] if "scanner_timeframe_profile" in df.columns else pd.Series(index=df.index, dtype="object")
    existing = existing.fillna("").astype(str)
    scan_mode = df["scan_mode"] if "scan_mode" in df.columns else pd.Series(index=df.index, dtype="object")
    market_type = df["market_type"] if "market_type" in df.columns else pd.Series(index=df.index, dtype="object")
    inferred = pd.Series("DAILY_PRIMARY", index=df.index, dtype="object")
    inferred = inferred.mask(scan_mode.fillna("").astype(str).str.upper().eq("INTRADAY"), "INTRADAY_1H")
    kr_daily = market_type.fillna("").astype(str).str.upper().eq("KR") & ~scan_mode.fillna("").astype(str).str.upper().eq("INTRADAY")
    inferred = inferred.mask(kr_daily, "DAILY_PRIMARY_WITH_1H_REFRESH")
    inferred = inferred.mask(existing.ne(""), existing)
    return inferred


def _infer_kr_universe_role(df: pd.DataFrame) -> pd.Series:
    existing = df["kr_universe_role"] if "kr_universe_role" in df.columns else pd.Series(index=df.index, dtype="object")
    existing = existing.fillna("").astype(str).str.upper()
    market_type = df["market_type"] if "market_type" in df.columns else pd.Series(index=df.index, dtype="object")
    scan_mode = df["scan_mode"] if "scan_mode" in df.columns else pd.Series(index=df.index, dtype="object")
    lane = _infer_selection_lane(df)
    strategy = df["strategy"] if "strategy" in df.columns else pd.Series(index=df.index, dtype="object")
    context = df["context"] if "context" in df.columns else pd.Series(index=df.index, dtype="object")
    trend = df["trend"] if "trend" in df.columns else pd.Series(index=df.index, dtype="object")

    market_type = market_type.fillna("").astype(str).str.upper()
    scan_mode = scan_mode.fillna("").astype(str).str.upper()
    lane = lane.fillna("").astype(str).str.lower()
    strategy = strategy.fillna("").astype(str).str.upper()
    context = context.fillna("").astype(str).str.upper()
    trend = trend.fillna("").astype(str).str.upper()

    role = pd.Series("N/A", index=df.index, dtype="object")
    kr_mask = market_type.eq("KR")
    role = role.mask(kr_mask, "TRANSITIONAL")

    explosive = kr_mask & (
        scan_mode.eq("INTRADAY")
        | lane.eq("1d")
        | strategy.str.contains("FLOWLEADER|BREAKOUT|INTRADAY", regex=True, na=False)
        | context.str.contains("수혜|TAILWIND", regex=True, na=False)
    )
    core = kr_mask & (~explosive) & (
        lane.eq("3d")
        | (scan_mode.eq("SWING") & trend.eq("UP"))
        | strategy.str.contains("THEMEROUTE|CONTEXTTAILWIND|PROFILE", regex=True, na=False)
    )
    reject = kr_mask & (~explosive) & (~core) & trend.eq("DOWN")

    role = role.mask(explosive, "EXPLOSIVE_LEADER")
    role = role.mask(core, "CORE_TREND")
    role = role.mask(reject, "REJECT_RISK")
    role = role.mask(existing.ne(""), existing)
    return role


def _infer_explosive_eligibility(df: pd.DataFrame, market: str) -> tuple[pd.Series, pd.Series]:
    existing_flag = df["explosive_eligible"] if "explosive_eligible" in df.columns else pd.Series(index=df.index, dtype="object")
    existing_reasons = df["explosive_gate_reasons"] if "explosive_gate_reasons" in df.columns else pd.Series(index=df.index, dtype="object")
    inferred_flag = pd.Series(False, index=df.index, dtype="bool")
    inferred_reasons = pd.Series([[] for _ in range(len(df))], index=df.index, dtype="object")

    if str(market).upper() not in {"KOSPI", "KOSDAQ"}:
        if not existing_flag.empty:
            inferred_flag = existing_flag.apply(
                lambda value: bool(value) if value not in (None, "", "nan", "None") else False
            ).astype(bool)
        if not existing_reasons.empty:
            inferred_reasons = existing_reasons.apply(
                lambda value: value if isinstance(value, list) else ([] if value in (None, "", "nan") else [str(value)])
            )
        return inferred_flag, inferred_reasons

    rows_flag = []
    rows_reasons = []
    for _, row in df.iterrows():
        payload = row.to_dict()
        gate = is_kr_explosive_leader_eligible(payload, str(market).upper())
        rows_flag.append(bool(gate.get("eligible", False)))
        rows_reasons.append([str(x) for x in list(gate.get("reasons", []) or []) if str(x).strip()])

    inferred_flag = pd.Series(rows_flag, index=df.index, dtype="bool")
    inferred_reasons = pd.Series(rows_reasons, index=df.index, dtype="object")

    if not existing_flag.empty:
        existing_flag_bool = existing_flag.apply(
            lambda value: bool(value) if value not in (None, "", "nan", "None") else False
        ).astype(bool)
        inferred_flag = inferred_flag.where(~existing_flag_bool, existing_flag_bool)

    if not existing_reasons.empty:
        def _normalize_reasons(value):
            if isinstance(value, list):
                return [str(x) for x in value if str(x).strip()]
            if value in (None, "", "nan"):
                return []
            return [str(value)]

        existing_norm = existing_reasons.apply(_normalize_reasons)
        inferred_reasons = pd.Series(
            [
                existing_norm.iloc[idx] if existing_norm.iloc[idx] else inferred_reasons.iloc[idx]
                for idx in range(len(df))
            ],
            index=df.index,
            dtype="object",
        )

    return inferred_flag, inferred_reasons


def _truthy_false_or_missing(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"", "0", "false", "none", "null", "no"})


def _apply_quality_tier(df: pd.DataFrame, quality_tier: str) -> pd.DataFrame:
    """Filter exported learning data by objective data-quality tier.

    GOLD is the training-safe dataset: resolved outcome, not dummy, not
    validation-excluded, complete feature metadata, and all required training
    features present. SILVER keeps resolved non-dummy rows for diagnostics even
    if old feature metadata is incomplete. ALL preserves historical behavior.
    """
    if df.empty:
        return df
    tier = str(quality_tier or "ALL").upper()
    if tier == "ALL":
        result = df.copy()
        result["learning_quality_tier"] = "all"
        return result

    mask = pd.Series(True, index=df.index)
    if "outcome_status" in df.columns:
        mask &= df["outcome_status"].fillna("").astype(str).str.upper().eq("RESOLVED")
    else:
        available_returns = [col for col in RETURN_COLS if col in df.columns]
        mask &= df[available_returns].notna().any(axis=1) if available_returns else False

    if "is_dummy_data" in df.columns:
        mask &= _truthy_false_or_missing(df["is_dummy_data"])

    if tier == "GOLD":
        if "validation_excluded" in df.columns:
            mask &= _truthy_false_or_missing(df["validation_excluded"])
        else:
            mask &= False
        if "feature_quality" in df.columns:
            mask &= df["feature_quality"].fillna("").astype(str).str.lower().eq("complete")
        else:
            mask &= False
        for col in REQUIRED_FEATURE_FIELDS_FOR_TRAINING:
            if col in df.columns:
                mask &= df[col].notna()
            else:
                mask &= False
        result = df.loc[mask].copy()
        result["learning_quality_tier"] = "gold"
        return result

    if tier == "SILVER":
        result = df.loc[mask].copy()
        result["learning_quality_tier"] = "silver"
        return result

    raise ValueError(f"unsupported quality_tier: {quality_tier}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export enriched scan archive dataset for backtest/model learning.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ", "NASDAQ", "AMEX"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--strategy-family", default=None)
    parser.add_argument("--quality-tier", choices=["ALL", "GOLD", "SILVER"], default="ALL")
    parser.add_argument("--output-dir", type=str, default="runtime_state/reports/archive")
    args = parser.parse_args()

    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    market = str(args.market).upper()
    remaining = int(args.limit or 0)
    page_size = 1000
    page = 0
    rows = []
    while True:
        batch_size = page_size if remaining <= 0 else min(page_size, remaining)
        query = (
            db.client.table("market_scan_results")
            .select("*")
            .order("created_at", desc=True)
            .range(page * page_size, page * page_size + batch_size - 1)
        )
        if market == "KOSPI":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KS")
        elif market == "KOSDAQ":
            query = query.eq("market_type", "KR").ilike("ticker", "%.KQ")
        elif market == "NASDAQ":
            query = query.eq("market_type", "US")
        elif market == "AMEX":
            query = query.eq("market_type", "AMEX")
        if args.strategy_family:
            query = query.eq("strategy_family", str(args.strategy_family))
        res = query.execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        page += 1
        if remaining > 0:
            remaining -= len(batch)
            if remaining <= 0:
                break
    df = pd.DataFrame(rows)
    if not df.empty and str(args.scan_mode).upper() != "ALL" and "scan_mode" in df.columns:
        df = df[df["scan_mode"].fillna("SWING").str.upper() == str(args.scan_mode).upper()]
    if not df.empty:
        df["decision_bucket"] = _infer_decision_bucket(df)
        df["selection_lane"] = _infer_selection_lane(df)
        df["target_horizon_days"] = _infer_target_horizon_days(df)
        df["scanner_timeframe_profile"] = _infer_scanner_timeframe_profile(df)
        df["kr_universe_role"] = _infer_kr_universe_role(df)
        df["explosive_leader_flag"] = df["kr_universe_role"].eq("EXPLOSIVE_LEADER").astype(int)
        df["core_trend_flag"] = df["kr_universe_role"].eq("CORE_TREND").astype(int)
        explosive_eligible, explosive_gate_reasons = _infer_explosive_eligibility(df, market=market)
        df["explosive_eligible"] = explosive_eligible.astype(int)
        df["explosive_gate_reasons"] = explosive_gate_reasons
        if "entry_reference_price" in df.columns:
            df["price_band"] = _price_band(df["entry_reference_price"])
            df["is_sub7"] = (df["price_band"] == "le_7").astype(int)

    if not df.empty:
        available_return_cols = [col for col in RETURN_COLS if col in df.columns]
        # Only assign labels when outcome is RESOLVED — PENDING/EXPIRED rows get NaN
        # to prevent false-negative label bias (fillna(0) on missing returns = fabricated loss)
        is_resolved = (
            df["outcome_status"].fillna("").str.upper().eq("RESOLVED")
            if "outcome_status" in df.columns
            else pd.Series(True, index=df.index)
        )
        if available_return_cols:
            numeric = df[available_return_cols].apply(pd.to_numeric, errors="coerce")
            df["max_return_observed_pct"] = numeric.max(axis=1, skipna=True).where(is_resolved)
            # Max drawdown across the observed horizon — needed for exit-rule
            # (SL -3%) simulation: without this, SL triggers are inferred from
            # close-only returns and understate actual stop-outs.
            df["min_return_observed_pct"] = numeric.min(axis=1, skipna=True).where(is_resolved)

            def _label(series: pd.Series, condition) -> pd.Series:
                """Return 1/0 only for RESOLVED rows; NaN for others."""
                result = condition.astype("Int8")  # nullable int
                return result.where(is_resolved)

            if "max_high_return_5d_pct" in df.columns:
                high_5d = pd.to_numeric(df["max_high_return_5d_pct"], errors="coerce")
            else:
                high_5d = pd.Series(index=df.index, dtype="float")
            if "hit_5pct_within_5d" in df.columns:
                hit_text = df["hit_5pct_within_5d"].fillna("").astype(str).str.strip().str.lower()
                high_hit = hit_text.isin({"true", "1", "yes"})
                high_label = high_hit.astype("Int8").where(is_resolved & high_5d.notna())
            else:
                high_label = _label(high_5d, high_5d.ge(5))
            df["target_definition"] = "forward_high_within_5d"
            df["target_return_source"] = "source_ohlcv_high"
            df["label_hit_5pct_within_5d"] = high_label
            df["max_high_return_5d_pct"] = high_5d.where(is_resolved)

            df["label_win_close"] = _label(numeric.get("return_close_pct", pd.Series(index=df.index)), numeric.get("return_close_pct", pd.Series(index=df.index)).gt(0))
            df["label_win_1d"] = _label(numeric.get("return_1d_pct", pd.Series(index=df.index)), numeric.get("return_1d_pct", pd.Series(index=df.index)).gt(0))
            df["label_win_3d"] = _label(numeric.get("return_3d_pct", pd.Series(index=df.index)), numeric.get("return_3d_pct", pd.Series(index=df.index)).gt(0))
            df["label_hit_5pct"] = _label(df["max_return_observed_pct"], df["max_return_observed_pct"].ge(5))
            df["label_hit_10pct"] = _label(df["max_return_observed_pct"], df["max_return_observed_pct"].ge(10))
            df["label_hit_20pct"] = _label(df["max_return_observed_pct"], df["max_return_observed_pct"].ge(20))
            df["label_hit_50pct"] = _label(df["max_return_observed_pct"], df["max_return_observed_pct"].ge(50))
            df["label_hit_100pct"] = _label(df["max_return_observed_pct"], df["max_return_observed_pct"].ge(100))
            # Exit-rule (SL -3%) trigger label — only RESOLVED rows.
            df["label_stop_loss_3pct"] = _label(df["min_return_observed_pct"], df["min_return_observed_pct"].le(-3))
            df["label_stop_loss_5pct"] = _label(df["min_return_observed_pct"], df["min_return_observed_pct"].le(-5))

    # Derive marcap_band from stored marcap column if present
    if not df.empty:
        if "marcap_band" not in df.columns:
            if "marcap" in df.columns:
                mc = pd.to_numeric(df["marcap"], errors="coerce")
                df["marcap_band"] = pd.cut(
                    mc,
                    bins=[0, 300e9, 1e12, 5e12, 20e12, float("inf")],
                    labels=[0, 1, 2, 3, 4],
                    right=False,
                ).cat.add_categories([2]).fillna(2).astype(int)
            else:
                df["marcap_band"] = 2  # unknown — mid band default

    if not df.empty:
        df = _apply_quality_tier(df, args.quality_tier)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix_parts = [market.lower()]
    if str(args.scan_mode).upper() != "ALL":
        suffix_parts.append(str(args.scan_mode).lower())
    if args.strategy_family:
        suffix_parts.append(str(args.strategy_family).lower())
    if str(args.quality_tier).upper() != "ALL":
        suffix_parts.append(str(args.quality_tier).lower())
    suffix = "_".join([part for part in suffix_parts if part and part != "all"]) or "all"
    csv_path = out_dir / f"scan_archive_learning_dataset_{suffix}.csv"
    json_path = out_dir / f"scan_archive_learning_dataset_{suffix}.json"
    if not df.empty:
        df.to_csv(csv_path, index=False)
        json_path.write_text(df.to_json(orient="records", force_ascii=False), encoding="utf-8")
    else:
        csv_path.write_text("", encoding="utf-8")
        json_path.write_text("[]", encoding="utf-8")

    print(
        json.dumps(
            {
                "rows": int(len(df)),
                "csv_path": str(csv_path),
                "json_path": str(json_path),
                "market": market,
                "scan_mode": str(args.scan_mode).upper(),
                "strategy_family": args.strategy_family,
                "quality_tier": str(args.quality_tier).upper(),
                "columns": sorted(df.columns.tolist()) if not df.empty else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
