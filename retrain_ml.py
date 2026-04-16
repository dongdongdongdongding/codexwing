#!/usr/bin/env python3
"""
retrain_ml.py  —  Phase 25 ML Retraining Pipeline (Resolved Outcome v2)
=======================================================================

핵심 변화:
  - yfinance로 3일 수익률을 다시 계산하지 않음
  - Supabase `market_scan_results` / `agent_realized_outcomes`에 이미 저장된
    realized return을 직접 사용
  - 미래 수익률로 시장 레짐을 역추정하던 누출성 proxy 제거
  - 시장/모드별 분리 연구 결과를 함께 저장

기본 저장:
  - 호환용 글로벌 모델: models/phase25_model.pkl
  - 세그먼트 모델: models/phase25_kr_swing.pkl, models/phase25_kr_intraday.pkl
  - 리포트: runtime_state/reports/learning/retrain_v2_report.json|md
"""

import json
import os
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager


def _pct_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_vol(value):
    try:
        return float(str(value).replace("✅", "").replace("⚠️", "").replace("x", "").strip())
    except Exception:
        return np.nan


def _infer_submarket(ticker: str, market_type: str, strategy_family: str) -> str:
    t = str(ticker or "").upper()
    mt = str(market_type or "").upper()
    sf = str(strategy_family or "").upper()
    if t.endswith(".KS"):
        return "KOSPI"
    if t.endswith(".KQ"):
        return "KOSDAQ"
    if mt == "AMEX" or sf == "AMEX_MOONSHOT":
        return "AMEX"
    if mt == "US":
        return "NASDAQ"
    if mt == "KR":
        return "KR"
    return mt or "UNKNOWN"


def load_scan_archive() -> pd.DataFrame:
    """Load enriched scan archive from Supabase with pagination."""
    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    select_cols = (
        "id,ticker,stock_name,created_at,market_type,scan_mode,strategy_family,"
        "priority_rank,decision,decision_bucket,outcome_status,"
        "alpha_score,tech_score,ml_prob,whale_score,trend,tier,volume,position,"
        "strategy,decision_score,fund_status,entry_reference_price,"
        "return_close_pct,return_1d_pct,return_2d_pct,return_3d_pct,return_5d_pct,return_7d_pct"
    )

    rows = []
    page = 0
    page_size = 1000
    while True:
        res = (
            db.client.table("market_scan_results")
            .select(select_cols)
            .order("created_at", desc=False)
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        print(f"  로드: {len(rows)} 레코드", end="\r")
        if len(batch) < page_size:
            break
        page += 1

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("market_scan_results is empty.")

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True).dt.tz_convert(None)
    df["scan_date"] = df["created_at"].dt.date
    df["scan_mode"] = df.get("scan_mode", "SWING").fillna("SWING").astype(str).str.upper()
    df["strategy_family"] = df.get("strategy_family", "").fillna("").astype(str)
    df["market_subtype"] = [
        _infer_submarket(ticker, market_type, strategy_family)
        for ticker, market_type, strategy_family in zip(
            df.get("ticker", pd.Series(dtype=str)),
            df.get("market_type", pd.Series(dtype=str)),
            df.get("strategy_family", pd.Series(dtype=str)),
        )
    ]

    # Merge duplicate archive rows for the same recommendation key by taking
    # the last non-null value per column. Outcome sync currently appends sparse
    # rows with returns, while the initial scan row has richer feature values.
    key_cols = ["run_id", "ticker", "scan_mode", "strategy_family", "priority_rank"]
    key_cols = [col for col in key_cols if col in df.columns]

    def _last_non_null(series: pd.Series):
        non_null = series.dropna()
        if not non_null.empty:
            return non_null.iloc[-1]
        return series.iloc[-1] if len(series) else None

    if key_cols:
        df = (
            df.sort_values(["created_at", "id"] if "id" in df.columns else ["created_at"])
            .groupby(key_cols, dropna=False, as_index=False)
            .agg(_last_non_null)
        )

    print(f"\n✅ 총 {len(df):,} 레코드 로드 완료")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in [
        "alpha_score",
        "tech_score",
        "ml_prob",
        "whale_score",
        "decision_score",
        "entry_reference_price",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df["vol_float"] = df.get("volume", pd.Series(index=df.index, dtype=object)).apply(_parse_vol)
    df["vol_confirmed"] = df.get("volume", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.startswith("✅").astype(int)
    df["vol_gt25x"] = (df["vol_float"] > 2.5).astype(int)
    df["vol_18_25x"] = ((df["vol_float"] > 1.8) & (df["vol_float"] <= 2.5)).astype(int)
    df["vol_08_18x"] = ((df["vol_float"] >= 0.8) & (df["vol_float"] <= 1.8)).astype(int)
    df["vol_lt05x"] = (df["vol_float"] < 0.5).astype(int)

    pos = df.get("position", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    strat = df.get("strategy", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    trend = df.get("trend", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.upper()
    tier = df.get("tier", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    fund = df.get("fund_status", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)

    df["is_rising"] = pos.str.contains("Rising", na=False).astype(int)
    df["is_peak"] = pos.str.contains("Peak", na=False).astype(int)
    df["is_resting"] = pos.str.contains("Resting", na=False).astype(int)
    df["is_bottom"] = pos.str.contains("Bottom", na=False).astype(int)

    df["is_uptrend"] = trend.eq("UP").astype(int)
    df["is_downtrend"] = trend.eq("DOWN").astype(int)
    df["is_sideways"] = trend.eq("SIDEWAYS").astype(int)

    df["is_overheat"] = strat.str.contains("단기과열|Overheat|Exhaustion", case=False, na=False).astype(int)
    df["is_rsidiv"] = strat.str.contains("RSI_DIV", na=False).astype(int)
    df["is_obvdiv"] = strat.str.contains("OBV_DIV", na=False).astype(int)
    df["is_momentum"] = strat.str.contains("Momentum", na=False).astype(int)
    df["is_contract"] = strat.str.contains("공급계약|계약|수주", na=False).astype(int)
    df["is_breakout"] = strat.str.contains("돌파|Breakout|Continuation", case=False, na=False).astype(int)

    df["tier_t0"] = tier.str.contains("⚡", na=False).astype(int)
    df["tier_t1"] = tier.str.contains("🏆", na=False).astype(int)
    df["tier_t2"] = tier.str.contains("⭐", na=False).astype(int)
    df["fund_positive"] = fund.str.contains("양호|Positive|Strong", case=False, na=False).astype(int)

    price = pd.to_numeric(df["entry_reference_price"], errors="coerce")
    df["is_sub7"] = price.gt(0) & price.le(7)
    df["price_7_15"] = price.gt(7) & price.le(15)
    df["price_gt15"] = price.gt(15)
    df["is_sub7"] = df["is_sub7"].astype(int)
    df["price_7_15"] = df["price_7_15"].astype(int)
    df["price_gt15"] = df["price_gt15"].astype(int)

    market_subtype = df["market_subtype"].fillna("UNKNOWN").astype(str)
    df["is_kospi"] = market_subtype.eq("KOSPI").astype(int)
    df["is_kosdaq"] = market_subtype.eq("KOSDAQ").astype(int)
    df["is_nasdaq"] = market_subtype.eq("NASDAQ").astype(int)
    df["is_amex"] = market_subtype.eq("AMEX").astype(int)
    df["scan_intraday"] = df["scan_mode"].eq("INTRADAY").astype(int)
    df["scan_swing"] = df["scan_mode"].eq("SWING").astype(int)

    fam = df["strategy_family"].str.upper()
    df["fam_kr_core"] = fam.eq("KR_CORE").astype(int)
    df["fam_us_main"] = fam.eq("US_MAIN").astype(int)
    df["fam_amex_moonshot"] = fam.eq("AMEX_MOONSHOT").astype(int)

    df["peak_x_highvol"] = df["is_peak"] * df["vol_gt25x"]
    df["overheat_x_uptrend"] = df["is_overheat"] * df["is_uptrend"]
    df["sub7_x_breakout"] = df["is_sub7"] * df["is_breakout"]

    # Market cap band: derive from marcap (KRW) stored in archive, or default to mid (2)
    if "marcap_band" in df.columns:
        df["marcap_band"] = pd.to_numeric(df["marcap_band"], errors="coerce").fillna(2).astype(int)
    elif "marcap" in df.columns:
        mc = pd.to_numeric(df["marcap"], errors="coerce")
        df["marcap_band"] = pd.cut(
            mc,
            bins=[0, 300e9, 1e12, 5e12, 20e12, float("inf")],
            labels=[0, 1, 2, 3, 4],
            right=False,
        ).cat.add_categories([2]).fillna(2).astype(int)
    else:
        df["marcap_band"] = 2

    return df


FEATURE_COLS = [
    "alpha_score",
    # "tech_score" removed: exact duplicate of alpha_score at inference time
    "ml_prob",
    # "whale_score" removed: 0% fill rate in RESOLVED rows — always NaN→0 noise
    # "decision_score" removed: circular reference (alpha*0.58 + ml_prob*0.32 → stored as feature for same model)
    "vol_float",
    "vol_confirmed",
    "vol_gt25x",
    "vol_18_25x",
    "vol_08_18x",
    "vol_lt05x",
    "is_rising",
    "is_peak",
    "is_resting",
    "is_bottom",
    "is_uptrend",
    "is_downtrend",
    "is_sideways",
    "is_overheat",
    "is_rsidiv",
    "is_obvdiv",
    "is_momentum",
    "is_contract",
    "is_breakout",
    "tier_t0",
    "tier_t1",
    "tier_t2",
    "fund_positive",
    "is_sub7",
    "price_7_15",
    "price_gt15",
    "is_kospi",
    "is_kosdaq",
    "is_nasdaq",
    "is_amex",
    "scan_intraday",
    "scan_swing",
    "fam_kr_core",
    "fam_us_main",
    "fam_amex_moonshot",
    "peak_x_highvol",
    "overheat_x_uptrend",
    "sub7_x_breakout",
    "marcap_band",
]


@dataclass
class SegmentSpec:
    name: str
    model_path: str
    return_col: str
    positive_threshold: float
    min_rows: int
    min_positive: int
    filter_fn: object
    description: str


def _is_resolved(df: pd.DataFrame) -> pd.Series:
    """Only train on RESOLVED outcomes — PENDING rows have no real labels yet."""
    if "outcome_status" in df.columns:
        return df["outcome_status"].fillna("").str.upper().eq("RESOLVED")
    return pd.Series(True, index=df.index)


SEGMENTS = [
    SegmentSpec(
        name="phase25_global",
        model_path="models/phase25_model.pkl",
        return_col="return_3d_pct",
        positive_threshold=5.0,
        min_rows=300,
        min_positive=60,
        filter_fn=lambda df: _is_resolved(df) & df["return_3d_pct"].notna(),
        description="Global compatibility model using realized 3D >= +5%.",
    ),
    SegmentSpec(
        name="phase25_kr_swing",
        model_path="models/phase25_kr_swing.pkl",
        return_col="return_3d_pct",
        positive_threshold=5.0,
        min_rows=120,
        min_positive=25,
        filter_fn=lambda df: _is_resolved(df) & df["market_subtype"].isin(["KOSPI", "KOSDAQ"]) & df["scan_mode"].eq("SWING") & df["return_3d_pct"].notna(),
        description="KR swing model using realized 3D >= +5%.",
    ),
    SegmentSpec(
        name="phase25_kr_intraday",
        model_path="models/phase25_kr_intraday.pkl",
        return_col="return_1d_pct",
        positive_threshold=0.0,
        min_rows=150,
        min_positive=40,
        filter_fn=lambda df: _is_resolved(df) & df["market_subtype"].isin(["KOSPI", "KOSDAQ"]) & df["scan_mode"].eq("INTRADAY") & df["return_1d_pct"].notna(),
        description="KR intraday model using next-day positive return.",
    ),
]


def _choose_model_backend():
    try:
        import lightgbm as lgb

        return "lgb", lgb
    except Exception:
        try:
            from xgboost import XGBClassifier  # noqa: F401

            return "xgb", None
        except Exception:
            return "rf", None


def _fit_model(X_train_s, y_train, backend):
    pos_ratio = max(float(y_train.mean()), 1e-6)
    class_weight = max((1 - pos_ratio) / pos_ratio, 1.0)
    if backend == "lgb":
        import lightgbm as lgb

        model = lgb.LGBMClassifier(
            n_estimators=400,
            learning_rate=0.03,
            max_depth=6,
            num_leaves=31,
            scale_pos_weight=class_weight,
            random_state=42,
            n_jobs=-1,
        )
    elif backend == "xgb":
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=350,
            learning_rate=0.03,
            max_depth=5,
            scale_pos_weight=class_weight,
            random_state=42,
            n_jobs=-1,
            eval_metric="auc",
        )
    else:
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            class_weight={0: 1, 1: class_weight},
            random_state=42,
            n_jobs=-1,
        )
    model.fit(X_train_s, y_train)
    return model


def _threshold_sweep(prob, ret, target):
    rows = []
    for th in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]:
        mask = prob >= th
        picks = int(mask.sum())
        if picks == 0:
            rows.append({"threshold": th, "picks": 0, "avg_return": None, "win_rate": None, "hit_rate": None})
            continue
        rows.append(
            {
                "threshold": th,
                "picks": picks,
                "avg_return": float(ret[mask].mean()),
                "win_rate": float((ret[mask] > 0).mean() * 100),
                "hit_rate": float((target[mask] == 1).mean() * 100),
            }
        )
    viable = [row for row in rows if row["picks"] >= 10 and row["avg_return"] is not None]
    best = max(viable, key=lambda row: (row["avg_return"], row["hit_rate"])) if viable else None
    return rows, best


def train_segment(df_all: pd.DataFrame, spec: SegmentSpec, backend: str):
    segment_df = df_all[spec.filter_fn(df_all)].copy()
    if segment_df.empty:
        return {"name": spec.name, "status": "skipped", "reason": "no_rows"}

    segment_df = segment_df.sort_values("created_at").copy()
    segment_df["target"] = (pd.to_numeric(segment_df[spec.return_col], errors="coerce") >= spec.positive_threshold).astype(int)

    total_rows = len(segment_df)
    positive_rows = int(segment_df["target"].sum())
    if total_rows < spec.min_rows:
        return {"name": spec.name, "status": "skipped", "reason": "insufficient_rows", "rows": total_rows}
    if positive_rows < spec.min_positive:
        return {"name": spec.name, "status": "skipped", "reason": "insufficient_positive_rows", "rows": total_rows, "positives": positive_rows}

    feat_cols = [col for col in FEATURE_COLS if col in segment_df.columns]
    X = segment_df[feat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = segment_df["target"].astype(int)

    split_idx = int(len(segment_df) * 0.7)
    if split_idx <= 0 or split_idx >= len(segment_df):
        return {"name": spec.name, "status": "skipped", "reason": "invalid_split", "rows": total_rows}

    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
    ret_val = pd.to_numeric(segment_df[spec.return_col], errors="coerce").iloc[split_idx:]

    if y_train.nunique() < 2 or y_val.nunique() < 2:
        return {"name": spec.name, "status": "skipped", "reason": "single_class_validation", "rows": total_rows}

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    model = _fit_model(X_train_s, y_train, backend)
    y_prob = model.predict_proba(X_val_s)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc = float(roc_auc_score(y_val, y_prob))
    report = classification_report(y_val, y_pred, target_names=["negative", "positive"], output_dict=True)
    sweep_rows, best_row = _threshold_sweep(y_prob, ret_val.to_numpy(), y_val.to_numpy())

    model_payload = {
        "model": model,
        "scaler": scaler,
        "features": feat_cols,
        "trained_at": datetime.now().isoformat(),
        "auc": auc,
        "segment": spec.name,
        "return_col": spec.return_col,
        "positive_threshold": spec.positive_threshold,
        "recommended_probability_threshold": (best_row or {}).get("threshold", 0.5),
        "description": spec.description,
    }
    os.makedirs(Path(spec.model_path).parent, exist_ok=True)
    joblib.dump(model_payload, spec.model_path)

    try:
        importances = getattr(model, "feature_importances_", None)
        feature_importance = (
            sorted(
                [{"feature": f, "importance": float(i)} for f, i in zip(feat_cols, importances)],
                key=lambda row: -row["importance"],
            )[:15]
            if importances is not None
            else []
        )
    except Exception:
        feature_importance = []

    return {
        "name": spec.name,
        "status": "trained",
        "rows": total_rows,
        "positives": positive_rows,
        "negative": int(total_rows - positive_rows),
        "return_col": spec.return_col,
        "positive_threshold": spec.positive_threshold,
        "auc": auc,
        "accuracy": float(report["accuracy"]),
        "positive_precision": float(report["positive"]["precision"]),
        "positive_recall": float(report["positive"]["recall"]),
        "recommended_probability_threshold": (best_row or {}).get("threshold"),
        "threshold_sweep": sweep_rows,
        "best_threshold_row": best_row,
        "feature_importance_top15": feature_importance,
        "model_path": spec.model_path,
        "description": spec.description,
    }


def _report_md(report):
    lines = ["# Retrain V2 Report", ""]
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- rows_loaded: `{report['rows_loaded']}`")
    lines.append(f"- backend: `{report['backend']}`")
    lines.append("")
    lines.append("## Segment Results")
    for row in report["segments"]:
        lines.append(f"- `{row['name']}`: `{row['status']}`")
        if row["status"] != "trained":
            reason = row.get("reason", "unknown")
            lines.append(f"  reason: `{reason}`")
            continue
        lines.append(f"  rows={row['rows']} positives={row['positives']} auc={row['auc']:.4f} acc={row['accuracy']:.4f}")
        best = row.get("best_threshold_row")
        if best:
            lines.append(
                f"  best_th={best['threshold']:.2f} picks={best['picks']} avg_return={best['avg_return']:+.2f}% "
                f"win_rate={best['win_rate']:.1f}% hit_rate={best['hit_rate']:.1f}%"
            )
    return "\n".join(lines) + "\n"


def main():
    print("=" * 60)
    print("  Phase 25 ML Retraining Pipeline (Resolved Outcome v2)")
    print("=" * 60)

    print("\n[1/3] DB에서 enriched scan archive 로드...")
    df = load_scan_archive()

    print("\n[2/3] 피처 엔지니어링...")
    df_feat = engineer_features(df)
    print(f"  사용 가능한 피처: {[col for col in FEATURE_COLS if col in df_feat.columns]}")

    backend, _ = _choose_model_backend()
    print(f"\n[3/3] 세그먼트별 모델 훈련... backend={backend}")
    segment_reports = []
    for spec in SEGMENTS:
        result = train_segment(df_feat, spec, backend)
        segment_reports.append(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    report = {
        "generated_at": datetime.now().isoformat(),
        "rows_loaded": int(len(df_feat)),
        "backend": backend,
        "segments": segment_reports,
    }
    report_dir = PROJECT_ROOT / "runtime_state" / "reports" / "learning"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "retrain_v2_report.json"
    report_md = report_dir / "retrain_v2_report.md"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_report_md(report), encoding="utf-8")

    trained = [row for row in segment_reports if row.get("status") == "trained"]
    if trained:
        primary = next((row for row in trained if row["name"] == "phase25_global"), trained[0])
        print("\n" + "=" * 60)
        print(f"  primary model: {primary['name']}  auc={primary['auc']:.4f}")
        print(f"  model path: {primary['model_path']}")
        print(f"  report path: {report_json}")
        print("=" * 60)
    else:
        print("\n⚠️  훈련 가능한 세그먼트가 없습니다.")


if __name__ == "__main__":
    main()
