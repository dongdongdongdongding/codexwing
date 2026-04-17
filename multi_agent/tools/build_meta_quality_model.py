#!/usr/bin/env python3
"""
build_meta_quality_model.py
────────────────────────────────────────────────────────────
Meta-Quality Model 훈련:
  - P(clean_hit): 손절 없이 깔끔하게 목표 도달 확률 (분류)
  - P(fast_hit):  1~3일 내 빠르게 도달 확률 (분류)
  - Expected MAE: 보유 중 최대 낙폭 예측 (회귀)

최종 활용:
  risk_adjusted_score = hit_prob × clean_hit_prob
                        × expected_return / max(|expected_MAE|, 0.01)

사용:
  python multi_agent/tools/build_meta_quality_model.py
  python multi_agent/tools/build_meta_quality_model.py --universe KOSPI --years 3
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score, mean_absolute_error
from sklearn.model_selection import train_test_split

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backtest_framework import walk_forward_optimize, DEFAULT_UNIVERSE, fetch_universe, _backtest_period, _calc_indicators, HOLD_DAYS

FEATURES = [
    "alpha_score",
    "vol_ratio",
    "atr_pct",
    "price_to_ma20",
    "price_to_ma50",
]

MODEL_DIR = ROOT / "models" / "meta_quality"


def collect_labeled_trades(universe: list[str], years: int = 2) -> pd.DataFrame:
    """백테스트를 실행해 품질 라벨이 붙은 트레이드 데이터를 수집한다."""
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years + 120)

    print(f"[1/3] 데이터 수집: {len(universe)} tickers, {years}년 기간")
    data = fetch_universe(
        universe,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )
    if not data:
        print("ERROR: 데이터 없음")
        return pd.DataFrame()

    # 전체 기간 단일 백테스트로 라벨 수집 (최적화 목적 아님, 데이터 수집 목적)
    print("[2/3] 트레이드 시뮬레이션 (품질 라벨 수집)")
    result = _backtest_period(
        data,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        atrs=1.5,   # 기본 ATR 손절 배수
        atrt=2.5,   # 기본 ATR 목표 배수
        volm=1.0,   # 기본 거래량 배수
        alpha_thr=40,
    )

    trades = result.get("trades", [])
    if not trades:
        print("WARNING: 수집된 트레이드 없음")
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    print(f"  수집된 트레이드: {len(df)}개")
    print(f"  clean_hit율: {df['clean_hit'].mean() * 100:.1f}%")
    print(f"  fast_hit율:  {df['fast_hit'].mean() * 100:.1f}%")
    print(f"  stop_first율:{df['stop_first'].mean() * 100:.1f}%")
    return df


def train_quality_model(df: pd.DataFrame, target: str) -> tuple:
    """단일 품질 라벨에 대한 분류 모델을 훈련한다."""
    valid = df[FEATURES + [target]].dropna()
    if len(valid) < 50:
        print(f"WARNING: {target} 훈련 데이터 부족 ({len(valid)}개)")
        return None, None

    X = valid[FEATURES].values
    y = valid[target].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.sum() > 5 else None
    )

    model = HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.05,
        max_depth=4,
        min_samples_leaf=10,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob) if len(np.unique(y_test)) > 1 else 0.5
    print(f"\n  [{target}] AUC={auc:.3f}  n_train={len(X_train)}  n_test={len(X_test)}")
    print(f"  Positive rate: train={y_train.mean():.2f}  test={y_test.mean():.2f}")

    return model, auc


def main() -> None:
    parser = argparse.ArgumentParser(description="Meta-Quality Model 훈련")
    parser.add_argument("--universe", choices=["KOSPI", "DEFAULT"], default="DEFAULT")
    parser.add_argument("--years", type=int, default=2, help="백테스트 기간 (년)")
    args = parser.parse_args()

    universe = DEFAULT_UNIVERSE

    print(f"\n{'=' * 60}")
    print(f"  Meta-Quality Model 훈련")
    print(f"  Universe: {args.universe}  Years: {args.years}")
    print(f"{'=' * 60}")

    df = collect_labeled_trades(universe, args.years)
    if df.empty:
        print("ERROR: 트레이드 데이터 없음. 종료.")
        sys.exit(1)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[3/3] 모델 훈련")
    results = {}

    # ── 분류 모델: P(clean_hit), P(fast_hit) ──
    for target in ("clean_hit", "fast_hit"):
        model, auc = train_quality_model(df, target)
        if model is None:
            continue
        out_path = MODEL_DIR / f"meta_quality_{target}.pkl"
        joblib.dump({"model": model, "features": FEATURES, "auc": auc, "type": "classifier"}, out_path)
        results[target] = {"auc": round(auc, 4), "path": str(out_path)}
        print(f"  저장: {out_path}")

    # ── 회귀 모델: Expected MAE ──
    valid_mae = df[FEATURES + ["mae_pct"]].dropna()
    if len(valid_mae) >= 50:
        X = valid_mae[FEATURES].values
        y = valid_mae["mae_pct"].values  # 음수 (낙폭)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        reg = HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_depth=4, min_samples_leaf=10, random_state=42
        )
        reg.fit(X_tr, y_tr)
        mae_score = mean_absolute_error(y_te, reg.predict(X_te))
        print(f"\n  [expected_mae] MAE error={mae_score:.4f}%  n_train={len(X_tr)}")
        out_path = MODEL_DIR / "meta_quality_expected_mae.pkl"
        joblib.dump({"model": reg, "features": FEATURES, "mae_error": mae_score, "type": "regressor"}, out_path)
        results["expected_mae"] = {"mae_error": round(mae_score, 4), "path": str(out_path)}
        print(f"  저장: {out_path}")
    else:
        print(f"  [expected_mae] 데이터 부족 ({len(valid_mae)}개), 스킵")

    # 메타데이터 저장
    meta = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "universe_size": len(universe),
        "years": args.years,
        "n_trades": len(df),
        "features": FEATURES,
        "models": results,
    }
    meta_path = MODEL_DIR / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 60}")
    print(f"완료. 모델 메타데이터: {meta_path}")
    for target, info in results.items():
        print(f"  {target}: AUC={info['auc']}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
