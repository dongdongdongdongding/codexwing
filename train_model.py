"""
train_model.py
═══════════════════════════════════════════════════════
Pillar 3: XGBoost Precision (정밀도) 모델

목적:
  - 기존 RandomForest(Accuracy 기준) → XGBoost(Precision 기준) 교체
  - 타겟: "3일 내 당일 종가 대비 +5% 이상 급등 도달 여부" (0/1)
  - Precision > 80% 달성 시 Alpha Score V32에 통합
  - 이 모델의 확률 반환값이 app.py의 '급등예측' 태그(3%, 5%, 10%)를 직접 결정함.
  - Confidence Threshold (0.80~0.90) 조정으로 승률 제어

사용법:
  python train_model.py          # 학습 + 저장
  python train_model.py predict  # Streamlit용 로드 + 예측
"""

import os
import sys
import json
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
import joblib

warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGB_OK = True
except Exception:
    XGB_OK = False
    xgb = None

try:
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import precision_score, recall_score, classification_report
    from sklearn.preprocessing import StandardScaler
    SK_OK = True
except ImportError:
    SK_OK = False

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'xgb_precision.pkl')
SCALER_PATH= os.path.join(BASE_DIR, 'models', 'xgb_scaler.pkl')
META_PATH  = os.path.join(BASE_DIR, 'models', 'xgb_meta.json')

OPTIMAL_JSON = os.path.join(BASE_DIR, 'optimal_params.json')

# 최적 파라미터 로드 (WFO 결과 반영)
def _load_optimal():
    if os.path.exists(OPTIMAL_JSON):
        with open(OPTIMAL_JSON) as f:
            p = json.load(f)
        return p.get('ATR_stop_mult', 1.5), p.get('ATR_target_mult', 2.5), p.get('Vol_mult', 1.5)
    return 1.5, 2.5, 1.5


# ══════════════════════════════════════════════════════════
# 데이터 파이프라인
# ══════════════════════════════════════════════════════════
UNIVERSE = [
    '005930.KS','000660.KS','005380.KS','051910.KS','006400.KS',
    '003670.KS','035720.KS','035420.KS','068270.KS','011200.KS',
    '028260.KS','207940.KS','012330.KS','000270.KS','018260.KS',
    '259960.KQ','028300.KQ','103140.KQ','042700.KS','095660.KQ',
    '086520.KQ','035900.KQ','293490.KQ','145020.KQ','214370.KQ',
]

FEATURE_COLS = [
    'RSI', 'MACD_norm', 'MACD_cross',
    'BB_pct', 'MA20_gap', 'MA50_gap', 'MA_cross',
    'Vol_ratio', 'ATR_pct',
    'ROC_1', 'ROC_3', 'ROC_5',
    'TechScore', 'Mkt_ROC_20', 'Sector_ROC_20'
]


def _build_features(df: pd.DataFrame, atr_tgt: float, vol_m: float, mkt_s: pd.Series = None, sec_s: pd.Series = None) -> pd.DataFrame:
    """피처 엔지니어링 + 레이블 생성 (미래 데이터 누수 없음)"""
    close  = df['Close']
    high   = df['High']
    low    = df['Low']
    volume = df['Volume']

    # ── 지표 계산 ─────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    sig   = macd.ewm(span=9, adjust=False).mean()

    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    std20 = close.rolling(20).std()
    bbu   = ma20 + 2 * std20
    bbl   = ma20 - 2 * std20

    tr    = pd.concat([high - low,
                        (high - close.shift(1)).abs(),
                        (low  - close.shift(1)).abs()], axis=1).max(axis=1)
    atr   = tr.rolling(14).mean()
    vol20 = volume.rolling(20).mean()

    # ── 피처 행렬 ─────────────────────────────────────────
    out = pd.DataFrame(index=df.index)
    out['RSI']       = rsi
    out['MACD_norm'] = (macd - sig) / close.replace(0, np.nan) * 100
    out['MACD_cross']= ((macd > sig) & (macd.shift(1) <= sig.shift(1))).astype(int)
    denom = (bbu - bbl).replace(0, 0.001)
    out['BB_pct']    = (close - bbl) / denom
    out['MA20_gap']  = (close - ma20) / ma20 * 100
    out['MA50_gap']  = (close - ma50) / ma50 * 100
    out['MA_cross']  = ((ma20 > ma50) & (ma20.shift(1) <= ma50.shift(1))).astype(int)
    out['Vol_ratio'] = volume / vol20.replace(0, 1)
    out['ATR_pct']   = atr / close * 100
    out['ROC_1']     = close.pct_change(1) * 100
    out['ROC_3']     = close.pct_change(3) * 100
    out['ROC_5']     = close.pct_change(5) * 100

    # 기술 점수 재계산
    score = pd.Series(0.0, index=df.index)
    score += np.where(rsi < 30,  20, 0)
    score += np.where((rsi > 50) & (rsi < 70), 10, 0)
    score += np.where(macd > sig, 20, 0)
    score += np.where(out['BB_pct'] < 0.2, 20, 0)
    score += np.where(out['Vol_ratio'] > 1.5, 15, 0)
    score += np.where(out['ROC_5'] > 0, 10, 0)
    out['TechScore'] = score.clip(0, 100)

    # ── Market & Sector Variables ──────────────
    if mkt_s is not None:
        out['Mkt_ROC_20'] = mkt_s.reindex(out.index, method='ffill').fillna(0)
    else:
        out['Mkt_ROC_20'] = 0.0
        
    if sec_s is not None:
        out['Sector_ROC_20'] = sec_s.reindex(out.index, method='ffill').fillna(0)
    else:
        out['Sector_ROC_20'] = 0.0

    # ── 레이블: 3일 내 +5% 초과 상승 도달 = 1 ──────────────
    # 타겟을 "T+1~T+3 일 내 최고가가 현재 종가 대비 5% 이상 상승하는가?" 로 완전히 고정합니다.
    target_price = close * 1.05
    labels = []
    arr_c  = close.values
    arr_h  = high.values
    arr_tp = target_price.values
    for i in range(len(df)):
        hit = 0
        # Check next 3 days
        for j in range(1, 4):
            if i + j < len(df) and arr_h[i + j] >= arr_tp[i]:
                hit = 1
                break
        labels.append(hit)
    out['Label'] = labels

    return out.dropna()


def collect_training_data() -> pd.DataFrame:
    atr_s, atr_t, vol_m = _load_optimal()
    print(f"  Optimal params: ATRs={atr_s}x  ATRt={atr_t}x  Vol={vol_m}x")

    all_dfs = []
    end_dt  = datetime.now()
    start_dt= end_dt - timedelta(days=365 * 2 + 60)
    start_str = start_dt.strftime('%Y-%m-%d')
    end_str   = end_dt.strftime('%Y-%m-%d')

    print(f"  Downloading Market Index (^KS11)...")
    try:
        mkt_df = yf.download('^KS11', start=start_str, end=end_str, progress=False, auto_adjust=True)
        if isinstance(mkt_df.columns, pd.MultiIndex):
            mkt_df.columns = [c[0] for c in mkt_df.columns]
        if not mkt_df.empty and mkt_df.index.tz is not None:
            mkt_df.index = mkt_df.index.tz_localize(None)
        mkt_roc_20 = mkt_df['Close'].pct_change(20) * 100 if not mkt_df.empty else None
    except Exception as e:
        print(f"  Market data fail: {e}")
        mkt_roc_20 = None
        
    print(f"  Downloading Sector ETFs...")
    import sys
    sys.path.append(BASE_DIR)
    try:
        # Use canonical names from sector_analysis.py and keep local aliases.
        from sector_analysis import SECTOR_ETFS as SECTOR_ETF_MAPPING, TICKER_SECTOR as TICKER_SECTOR_MAP
    except ImportError:
        SECTOR_ETF_MAPPING = {}
        TICKER_SECTOR_MAP = {}
        
    sector_data = {}
    for sec, etf in SECTOR_ETF_MAPPING.items():
        try:
            sec_df = yf.download(etf, start=start_str, end=end_str, progress=False, auto_adjust=True)
            if isinstance(sec_df.columns, pd.MultiIndex):
                sec_df.columns = [c[0] for c in sec_df.columns]
            if not sec_df.empty:
                if sec_df.index.tz is not None:
                    sec_df.index = sec_df.index.tz_localize(None)
                sector_data[sec] = sec_df['Close'].pct_change(20) * 100
        except Exception:
            pass

    import warnings
    warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

    for idx, t in enumerate(UNIVERSE, 1):
        try:
            print(f"  [{idx}/{len(UNIVERSE)}] Fetching {t}...", end="\r")
            df = yf.download(t, start=start_str, end=end_str, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if df.empty or len(df) < 60:
                continue
                
            sec_name = TICKER_SECTOR_MAP.get(t, "기타")
            sec_roc = sector_data.get(sec_name, None)
            
            feat = _build_features(df, atr_t, vol_m, mkt_s=mkt_roc_20, sec_s=sec_roc)
            feat['Ticker'] = t
            all_dfs.append(feat)
        except Exception as e:
            pass

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n  Dataset: {len(combined):,} rows | Positive rate: {combined['Label'].mean()*100:.1f}%")
    return combined


# ══════════════════════════════════════════════════════════
# 학습
# ══════════════════════════════════════════════════════════
def train(confidence_threshold: float = 0.80):
    if not SK_OK:
        print("sklearn 미설치")
        return

    print("\n" + "="*55)
    print("📚 Pillar 3: Precision Model 학습 시작 (Target: +5% Surge)")
    print("="*55)

    print("\n[1/4] 데이터 수집...")
    df = collect_training_data()
    if df.empty:
        print("데이터 없음")
        return

    X = df[FEATURE_COLS].values
    y = df['Label'].values

    # 불균형 보정
    pos_rate = y.mean()
    scale_pw  = (1 - pos_rate) / pos_rate if pos_rate > 0 else 1.0

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    # 모델 선택: XGBoost 우선, sklearn GradientBoosting 대체
    if XGB_OK:
        print(f"\n[2/4] XGBoost 모델 학습 (scale_pos_weight={scale_pw:.1f})...")
        clf = xgb.XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=scale_pw,
            objective='binary:logistic', eval_metric='aucpr',
            use_label_encoder=False, random_state=42, n_jobs=-1,
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        print(f"\n[2/4] sklearn GradientBoosting 모델 학습 (XGBoost 대체)...")
        # sample_weight로 불균형 보정
        clf = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42,
        )

    # TimeSeriesSplit CV (순방향 교차검증, lookahead 없음)
    print(f"\n[3/4] 시계열 교차검증 (5-fold) 및 최적 임계치 탐색 (Target Precision: {confidence_threshold:.2f})...")
    tscv  = TimeSeriesSplit(n_splits=5)
    
    thresholds = np.arange(0.50, 0.96, 0.05)
    fold_results = {float(th): {'prec': [], 'signals': []} for th in thresholds}
    
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_sc)):
        clf.fit(X_sc[tr_idx], y[tr_idx])
        y_prob = clf.predict_proba(X_sc[val_idx])[:, 1]
        
        for th in thresholds:
            th = float(th)
            y_pred = (y_prob >= th).astype(int)
            prec   = precision_score(y[val_idx], y_pred, zero_division=0)
            n_preds = y_pred.sum()
            fold_results[th]['prec'].append(prec)
            fold_results[th]['signals'].append(n_preds)
            
        print(f"   Fold {fold+1}: {len(val_idx)} 샘플 검증 완료.")

    # 최적 임계치 선정 로직
    best_th = 0.80
    best_prec = 0.0
    
    print("\n   [ 임계치 대역별 성능 ]")
    valid_ths = []
    
    for th in thresholds:
        th = float(th)
        avg_prec = float(np.mean(fold_results[th]['prec']))
        avg_sig  = float(np.mean(fold_results[th]['signals']))
        print(f"   Threshold {th:.2f}: Precision={avg_prec:.3f} | Avg Signals={avg_sig:.1f}")
        
        # 최소 유효 조건: 폴드당 평균 1개 이상 신호 발생
        if avg_sig >= 1.0:
            valid_ths.append((th, avg_prec))
    
    if not valid_ths:
        print("\n   ⚠️ 모든 Threshold에서 유효한 Signal이 부족합니다. 기본값(0.80) 적용.")
        best_th = 0.80
        best_prec = float(np.mean(fold_results[best_th]['prec'])) if best_th in fold_results else 0.0
    else:
        # 1순위: Precision >= 0.80 인 최소 Threshold
        # 2순위: 그 중 최대 Precision
        target_met = [(th, p) for th, p in valid_ths if p >= confidence_threshold]
        if target_met:
            # 최소 Threshold 선택 (Precision 요구사항 충족 시, 재현율 극대화를 위해)
            target_met.sort(key=lambda x: x[0])
            best_th = target_met[0][0]
            best_prec = target_met[0][1]
            print(f"\n   🌟 목표 Precision({confidence_threshold}) 달성! 최소 임계치 {best_th:.2f} 선택.")
        else:
            # 목표 미달 시 최고 Precision 선택
            valid_ths.sort(key=lambda x: x[1], reverse=True)
            best_th = valid_ths[0][0]
            best_prec = valid_ths[0][1]
            print(f"\n   ⚠️ 목표 Precision 도달 실패. 최고 Precision({best_prec:.3f})인 {best_th:.2f} 선택.")

    # 저장 및 후속 절차를 위해 최종 설정
    confidence_threshold = float(best_th)
    prec_scores = fold_results[best_th]['prec']

    # 전체 데이터로 최종 학습
    clf.fit(X_sc, y)

    # 저장
    os.makedirs(os.path.join(BASE_DIR, 'models'), exist_ok=True)
    joblib.dump(clf,    MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    meta = {
        "feature_cols": FEATURE_COLS,
        "confidence_threshold": confidence_threshold,
        "avg_cv_precision": round(np.mean(prec_scores), 4),
        "pos_rate": round(float(pos_rate), 4),
        "trained_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2)

    print(f"\n[4/4] 모델 저장 완료")
    print(f"   {MODEL_PATH}")
    print(f"   {SCALER_PATH}")

    avg_prec = np.mean(prec_scores)
    if avg_prec >= 0.80:
        print(f"\n🏆 목표 달성! Precision {avg_prec:.3f} ≥ 0.80")
    else:
        print(f"\n⚠️  미달 ({avg_prec:.3f}). Confidence Threshold 상향 또는 피처 추가 권고")
    return avg_prec


# ══════════════════════════════════════════════════════════
# 추론 (Streamlit 통합용)
# ══════════════════════════════════════════════════════════
def predict_proba(features: dict) -> float:
    """
    Returns: 0.0~1.0 (익절 도달 확률)
    features: FEATURE_COLS 키:값 dict
    """
    if not os.path.exists(MODEL_PATH):
        return 0.5  # 모델 없으면 중립

    try:
        clf    = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        with open(META_PATH) as f:
            meta = json.load(f)

        feat_arr = np.array([[features.get(c, 0) for c in meta['feature_cols']]])
        feat_sc  = scaler.transform(feat_arr)
        prob     = clf.predict_proba(feat_sc)[0, 1]
        return float(prob)
    except Exception:
        return 0.5


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'predict':
        # 테스트 예측
        test_feat = {c: 50.0 for c in FEATURE_COLS}
        p = predict_proba(test_feat)
        print(f"Test prediction: {p:.3f}")
    else:
        train(confidence_threshold=0.80)
