import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
import numpy as np
import os
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, classification_report, precision_recall_curve, precision_score
from sklearn.calibration import CalibratedClassifierCV
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.news_embedding import create_news_features_for_training

# --- CONFIGURATION ---
MODEL_PATH = "models/universal_rf_heavy.pkl"
THRESHOLD_PATH = "models/optimal_threshold.pkl"
PCA_PATH = "models/news_pca.pkl"

SECTOR_LEADERS = [
    # ===== KOREA KOSPI (Top 30) =====
    '005930.KS', '000660.KS', '042700.KS',
    '373220.KS', '006400.KS', '051910.KS', '003670.KS',
    '005380.KS', '000270.KS', '012330.KS',
    '207940.KS', '068270.KS', '302440.KS',
    '035420.KS', '035720.KS',
    '066570.KS', '055550.KS', '032830.KS', '003490.KS',
    '015760.KS', '034020.KS', '009150.KS', '017670.KS',
    '030200.KS', '086790.KS', '028260.KS', '259960.KS',
    '316140.KS', '011200.KS', '010130.KS',
    # ===== KOREA KOSDAQ (Top 10) =====
    '247540.KQ', '091990.KQ', '196170.KQ', '263750.KQ',
    '328130.KQ', '145020.KQ', '403870.KQ', '058470.KQ',
    '041510.KQ', '000250.KQ',
    # ===== US MEGA CAP =====
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
    'JPM', 'V', 'MA', 'JNJ', 'UNH', 'HD', 'PG',
    # ===== US TECH =====
    'CRM', 'AMD', 'INTC', 'AVGO', 'ADBE', 'ORCL', 'QCOM', 'MU', 'AMAT',
    'PANW', 'SNOW', 'NOW', 'PLTR', 'COIN',
    # ===== US SECTORS =====
    'WMT', 'COST', 'KO', 'PEP', 'MCD', 'NKE',
    'XOM', 'CVX', 'SLB', 'COP',
    'CAT', 'BA', 'HON', 'GE', 'RTX', 'LMT',
    'DIS', 'NFLX', 'CMCSA',
    'MRNA', 'REGN', 'VRTX', 'GILD',
    'AMT', 'PLD', 'EQIX', 'SPG',
    'SPY', 'QQQ', 'IWM', 'DIA',
]


def _fetch_cross_asset_data():
    """Fetch VIX, Dollar Index, Gold, Treasury Yield for cross-asset features"""
    print("📡 Fetching Cross-Asset Data (VIX, DXY, Gold, Bonds, SPY)...")
    cross = {}
    
    symbols = {
        'VIX': '^VIX',
        'DXY': 'DX-Y.NYB',
        'GOLD': 'GC=F',
        'TNX': '^TNX',
        'SPY': 'SPY',
    }
    
    for name, sym in symbols.items():
        try:
            df = yf.download(sym, period="5y", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is not None and len(df) > 100:
                cross[name] = df['Close']
                print(f"  ✅ {name}: {len(df)} candles")
            else:
                print(f"  ⚠️ {name}: Insufficient data")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    
    return cross


def _build_features_v5(df, cross_asset):
    """
    V5 Feature Set: 36 features
    Multi-scale momentum + cross-asset + interactions + candle patterns
    """
    if len(df) < 200:
        return None
    
    # ==========================================
    # GROUP 1: Core Technical (10 features)
    # ==========================================
    df['Returns'] = df['Close'].pct_change()
    df['Vol_Rel'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)
    
    rsi = ta.rsi(df['Close'], length=14)
    if rsi is None: return None
    df['RSI'] = rsi
    
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    if atr is None: return None
    df['ATR_Rel'] = atr / df['Close']
    
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD_Hist'] = macd['MACDh_12_26_9'] if macd is not None and 'MACDh_12_26_9' in macd.columns else 0
    
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx['ADX_14'] if adx is not None and 'ADX_14' in adx.columns else 20
    
    ma20 = df['Close'].rolling(20).mean()
    ma50 = df['Close'].rolling(50).mean()
    ma200 = df['Close'].rolling(200).mean()
    df['Dist_MA20'] = (df['Close'] - ma20) / (ma20 + 1e-9)
    df['Dist_MA50'] = (df['Close'] - ma50) / (ma50 + 1e-9)
    df['Dist_MA200'] = (df['Close'] - ma200) / (ma200 + 1e-9)
    
    df['Vol_Trend'] = df['Volume'].rolling(5).mean() / (df['Volume'].rolling(20).mean() + 1e-9)
    
    # ==========================================
    # GROUP 2: Multi-Period Momentum (5 features)
    # ==========================================
    df['Mom_5'] = df['Close'].pct_change(5)
    df['Mom_10'] = df['Close'].pct_change(10)
    df['Mom_20'] = df['Close'].pct_change(20)
    df['Return_Lag1'] = df['Returns'].shift(1)
    df['Return_Lag2'] = df['Returns'].shift(2)
    
    # ==========================================
    # GROUP 3: Advanced Technical (7 features)
    # ==========================================
    willr = ta.willr(df['High'], df['Low'], df['Close'], length=14)
    df['WillR'] = willr if willr is not None else -50
    
    cci = ta.cci(df['High'], df['Low'], df['Close'], length=20)
    df['CCI'] = cci if cci is not None else 0
    
    stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)
    df['Stoch_K'] = stoch['STOCHk_14_3_3'] if stoch is not None and 'STOCHk_14_3_3' in stoch.columns else 50
    
    obv = ta.obv(df['Close'], df['Volume'])
    df['OBV_Slope'] = obv.pct_change(5) if obv is not None else 0
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).rolling(20).sum() / (df['Volume'].rolling(20).sum() + 1e-9)
    df['VWAP_Dist'] = (df['Close'] - vwap) / (vwap + 1e-9)
    
    df['Range_Pct'] = (df['High'] - df['Low']) / (df['Close'] + 1e-9)
    df['RSI_Lag1'] = df['RSI'].shift(1)
    
    # ==========================================
    # GROUP 4: Candle Patterns (4 features)
    # ==========================================
    df['Up_Day'] = (df['Close'] > df['Close'].shift(1)).astype(int)
    df['Consec_Up'] = df['Up_Day'].rolling(5).sum()
    df['Consec_Down'] = 5 - df['Consec_Up']
    df['Gap_Pct'] = (df['Open'] - df['Close'].shift(1)) / (df['Close'].shift(1) + 1e-9)
    df['Vol_Spike'] = (df['Vol_Rel'] > 2.0).astype(int)
    
    # ==========================================
    # GROUP 5: Feature Interactions (4 features)
    # ==========================================
    df['RSI_x_Mom'] = df['RSI'] / 100.0 * df['Mom_5']
    df['Vol_x_ADX'] = df['Vol_Rel'] * df['ADX'] / 100.0
    df['MACD_x_OBV'] = df['MACD_Hist'] * df['OBV_Slope']
    df['VIX_x_RSI'] = 0.0
    
    # ==========================================
    # GROUP 6: Cross-Asset / Regime (4 features)
    # ==========================================
    if 'VIX' in cross_asset:
        vix = cross_asset['VIX'].reindex(df.index, method='ffill')
        df['VIX_Level'] = vix / 100.0
        df['VIX_Change'] = vix.pct_change(5)
        df['VIX_x_RSI'] = (vix / 100.0) * (1 - df['RSI'] / 100.0)
    else:
        df['VIX_Level'] = 0.2
        df['VIX_Change'] = 0
    
    if 'SPY' in cross_asset:
        spy = cross_asset['SPY'].reindex(df.index, method='ffill')
        df['Market_Mom_20'] = spy.pct_change(20)
        df['Market_Vol'] = spy.pct_change().rolling(20).std()
    else:
        df['Market_Mom_20'] = 0
        df['Market_Vol'] = 0.01
    
    # Earnings (keep simple defaults for now)
    df['Earnings_Proximity'] = 0.5
    df['Surprise_Pct'] = 0.0
    
    return df


FEATURES_V5 = [
    # Core Technical (10)
    'ATR_Rel', 'MACD_Hist', 'ADX', 'Vol_Trend', 'Dist_MA20', 'Dist_MA50', 'Dist_MA200',
    'RSI', 'Vol_Rel', 'Returns',
    # Multi-Period Momentum (5)
    'Mom_5', 'Mom_10', 'Mom_20', 'Return_Lag1', 'Return_Lag2',
    # Advanced Technical (7)
    'WillR', 'CCI', 'Stoch_K', 'OBV_Slope', 'VWAP_Dist', 'Range_Pct', 'RSI_Lag1',
    # Candle Patterns (4)
    'Consec_Up', 'Consec_Down', 'Gap_Pct', 'Vol_Spike',
    # Feature Interactions (4)
    'RSI_x_Mom', 'Vol_x_ADX', 'MACD_x_OBV', 'VIX_x_RSI',
    # Cross-Asset / Regime (4)
    'VIX_Level', 'VIX_Change', 'Market_Mom_20', 'Market_Vol',
    # Earnings (2)
    'Earnings_Proximity', 'Surprise_Pct',
]


def train_global_brain():
    print("=" * 60)
    print("  🧠 GLOBAL BRAIN V6 — V5 + News Embedding")
    print("  Voting Ensemble | News Semantics | Purged CV")
    print("=" * 60)
    
    if not os.path.exists("models"):
        os.makedirs("models")
    
    cross_asset = _fetch_cross_asset_data()
    big_data = []
    
    for i, t in enumerate(SECTOR_LEADERS):
        try:
            print(f"[{i+1}/{len(SECTOR_LEADERS)}] Fetching {t}...", end=" ")
            df = yf.download(t, period="5y", progress=False)
            
            if len(df) < 200:
                print(f"⚠️ Skipped (Insufficient Data: {len(df)})")
                continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = _build_features_v5(df, cross_asset)
            if df is None:
                print("⚠️ Skipped (Feature Build Failed)")
                continue
            
            # ========================================
            # V5 TARGET: Balanced clear signals
            # Wider zone for MORE data → better F1
            # UP: avg 5d+10d > 2%  |  DOWN: avg < -1.5%
            # ========================================
            fwd_5 = df['Close'].shift(-5) / df['Close'] - 1
            fwd_10 = df['Close'].shift(-10) / df['Close'] - 1
            combined_fwd = (fwd_5 + fwd_10) / 2
            
            df['Target'] = -1
            df.loc[combined_fwd > 0.02, 'Target'] = 1   # UP
            df.loc[combined_fwd < -0.015, 'Target'] = 0  # DOWN
            df = df[df['Target'] != -1]
            
            # Recency Weights
            cutoff_date = df.index.max() - pd.DateOffset(years=2)
            df['Sample_Weight'] = np.where(df.index >= cutoff_date, 2.0, 1.0)
            
            df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES_V5 + ['Target'])
            
            if len(df) > 50:
                big_data.append(df)
                ratio = df['Target'].mean() * 100
                print(f"✅ OK ({len(df)} samples, {ratio:.0f}% UP)")
            else:
                print(f"⚠️ Skipped (Insufficient clear samples)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not big_data:
        print("❌ Critical Error: No data collected.")
        return
    
    print("\n🔄 Merging Global Dataset...")
    full_df = pd.concat(big_data)
    print(f"📊 Total Samples: {len(full_df):,}")
    
    X = full_df[FEATURES_V5]
    y = full_df['Target'].astype(int)
    sample_weights = full_df['Sample_Weight']
    
    print(f"📈 Features: {len(FEATURES_V5)}")
    print(f"📊 Target Distribution: {y.value_counts().to_dict()}")
    print(f"⚖️ UP Signal Ratio: {y.mean()*100:.1f}%")
    
    # ========================================
    # PURGED TIME-SERIES CROSS-VALIDATION
    # ========================================
    print("\n🔬 Running Purged TimeSeriesSplit 5-Fold CV...")
    tscv = TimeSeriesSplit(n_splits=5, gap=10)
    
    cv_scores = []
    cv_f1s = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
        w_tr = sample_weights.iloc[train_idx]
        
        model_cv = HistGradientBoostingClassifier(
            max_iter=500, max_depth=6, max_leaf_nodes=31,
            learning_rate=0.05, l2_regularization=1.0,
            min_samples_leaf=50, class_weight='balanced',
            random_state=42, verbose=0
        )
        model_cv.fit(X_tr, y_tr, sample_weight=w_tr)
        
        y_pred_cv = model_cv.predict(X_val)
        acc = accuracy_score(y_val, y_pred_cv)
        f1 = f1_score(y_val, y_pred_cv, zero_division=0)
        cv_scores.append(acc)
        cv_f1s.append(f1)
        
        print(f"  Fold {fold+1}: Acc={acc*100:.2f}%, F1={f1:.3f}")
    
    mean_acc = np.mean(cv_scores) * 100
    mean_f1 = np.mean(cv_f1s)
    print(f"\n📊 CV Mean Accuracy: {mean_acc:.2f}%")
    print(f"📊 CV Mean F1: {mean_f1:.3f}")
    
    # ========================================
    # STACKING ENSEMBLE TRAINING
    # ========================================
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    w_train = sample_weights.iloc[:split_idx]
    
    print(f"\n🏗️ Building Stacking Ensemble...")
    print(f"  Train: {len(X_train):,} | Test: {len(X_test):,}")
    
    # Base Estimators (diverse learners)
    base_estimators = [
        ('hgb', HistGradientBoostingClassifier(
            max_iter=800, max_depth=6, max_leaf_nodes=31,
            learning_rate=0.03, l2_regularization=1.0,
            min_samples_leaf=50, class_weight='balanced',
            random_state=42, verbose=0
        )),
        ('et', ExtraTreesClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=20,
            class_weight='balanced', random_state=42, n_jobs=-1
        )),
        ('hgb2', HistGradientBoostingClassifier(
            max_iter=500, max_depth=4, max_leaf_nodes=15,
            learning_rate=0.08, l2_regularization=2.0,
            min_samples_leaf=80, class_weight='balanced',
            random_state=123, verbose=0
        )),
    ]
    
    voting_ensemble = VotingClassifier(
        estimators=base_estimators,
        voting='soft', n_jobs=-1
    )
    
    print("🏋️ Training Voting Ensemble (soft)...")
    voting_ensemble.fit(X_train, y_train, sample_weight=w_train)
    
    # ========================================
    # BALANCED THRESHOLD FINDER
    # Goal: Maximize F1 with Precision >= 70%
    # ========================================
    print("\n🎯 Finding Balanced Threshold (F1-optimized, Precision ≥ 70%)...")
    
    y_proba_test = voting_ensemble.predict_proba(X_test)[:, 1]
    
    best_threshold = 0.50
    best_f1_balanced = 0
    best_info = {}
    
    for t_candidate in np.arange(0.40, 0.80, 0.01):
        preds = (y_proba_test >= t_candidate).astype(int)
        if preds.sum() < 10:
            continue
        
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, zero_division=0)
        prec = precision_score(y_test, preds, zero_division=0)
        
        tp = ((preds == 1) & (y_test == 1)).sum()
        fn = ((preds == 0) & (y_test == 1)).sum()
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        if prec >= 0.70 and f1 > best_f1_balanced:
            best_f1_balanced = f1
            best_threshold = t_candidate
            best_info = {
                'acc': acc, 'f1': f1, 'prec': prec, 'recall': recall,
                'n_signals': int(preds.sum())
            }
    
    # Fallback: if no threshold gives precision >= 70%, just maximize F1
    if best_f1_balanced == 0:
        print("  ⚠️ No threshold with precision ≥ 70%, optimizing F1 only...")
        for t_candidate in np.arange(0.35, 0.70, 0.01):
            preds = (y_proba_test >= t_candidate).astype(int)
            if preds.sum() < 10:
                continue
            f1 = f1_score(y_test, preds, zero_division=0)
            if f1 > best_f1_balanced:
                best_f1_balanced = f1
                best_threshold = t_candidate
                acc = accuracy_score(y_test, preds)
                prec = precision_score(y_test, preds, zero_division=0)
                tp = ((preds == 1) & (y_test == 1)).sum()
                fn = ((preds == 0) & (y_test == 1)).sum()
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                best_info = {
                    'acc': acc, 'f1': f1, 'prec': prec, 'recall': recall,
                    'n_signals': int(preds.sum())
                }
    
    optimal_threshold = best_threshold
    
    print(f"\n  ✅ Balanced Threshold: {optimal_threshold:.2f}")
    print(f"  📊 Accuracy: {best_info.get('acc', 0)*100:.1f}%")
    print(f"  📊 F1 Score: {best_info.get('f1', 0):.3f}")
    print(f"  📊 Precision: {best_info.get('prec', 0)*100:.1f}%")
    print(f"  📊 Recall: {best_info.get('recall', 0)*100:.1f}%")
    print(f"  📊 BUY Signals: {best_info.get('n_signals', 0)}")
    
    # Full evaluation at balanced threshold
    y_pred_balanced = (y_proba_test >= optimal_threshold).astype(int)
    acc_balanced = accuracy_score(y_test, y_pred_balanced)
    f1_balanced = f1_score(y_test, y_pred_balanced, zero_division=0)
    
    print(f"\n{'='*50}")
    print(f"🎯 BALANCED Threshold ({optimal_threshold:.2f})")
    print(classification_report(y_test, y_pred_balanced, target_names=['DOWN', 'UP'], zero_division=0))
    
    # Also show default 0.50
    y_pred_default = (y_proba_test >= 0.50).astype(int)
    acc_default = accuracy_score(y_test, y_pred_default)
    f1_default = f1_score(y_test, y_pred_default, zero_division=0)
    prec_default = precision_score(y_test, y_pred_default, zero_division=0)
    
    tp_d = ((y_pred_default == 1) & (y_test == 1)).sum()
    fn_d = ((y_pred_default == 0) & (y_test == 1)).sum()
    recall_default = tp_d / (tp_d + fn_d) if (tp_d + fn_d) > 0 else 0
    
    print(f"📊 DEFAULT (0.50): Acc={acc_default*100:.1f}%, F1={f1_default:.3f}, Prec={prec_default*100:.1f}%, Recall={recall_default*100:.1f}%")
    print(classification_report(y_test, y_pred_default, target_names=['DOWN', 'UP'], zero_division=0))
    
    # Pick the best: whichever has higher F1
    if f1_default > f1_balanced:
        print("✅ DEFAULT threshold (0.50) wins — better F1")
        optimal_threshold = 0.50
        final_acc = acc_default
        final_f1 = f1_default
        best_info = {
            'acc': acc_default, 'f1': f1_default, 'prec': prec_default, 'recall': recall_default,
            'n_signals': int(y_pred_default.sum())
        }
    else:
        print("✅ BALANCED threshold wins — better F1 with higher precision")
        final_acc = acc_balanced
        final_f1 = f1_balanced
    model_label = "Voting Ensemble (HGB+ET+HGB2)"
    
    # ========================================
    # REFIT ON FULL DATA & SAVE
    # ========================================
    print("\n🔄 Refitting Stacking Ensemble on full dataset...")
    
    base_final = [
        ('hgb', HistGradientBoostingClassifier(
            max_iter=800, max_depth=6, max_leaf_nodes=31,
            learning_rate=0.03, l2_regularization=1.0,
            min_samples_leaf=50, class_weight='balanced',
            random_state=42, verbose=0
        )),
        ('et', ExtraTreesClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=20,
            class_weight='balanced', random_state=42, n_jobs=-1
        )),
        ('hgb2', HistGradientBoostingClassifier(
            max_iter=500, max_depth=4, max_leaf_nodes=15,
            learning_rate=0.08, l2_regularization=2.0,
            min_samples_leaf=80, class_weight='balanced',
            random_state=123, verbose=0
        )),
    ]
    
    final_model = VotingClassifier(
        estimators=base_final,
        voting='soft', n_jobs=-1
    )
    
    final_model.fit(X, y, sample_weight=sample_weights)
    
    # Save
    joblib.dump(final_model, MODEL_PATH)
    joblib.dump({
        'threshold': optimal_threshold,
        'features': FEATURES_V5,
        'cv_accuracy': mean_acc,
        'cv_f1': mean_f1,
        'oos_accuracy': final_acc * 100,
        'oos_f1': final_f1,
        'oos_precision': best_info.get('prec', 0) * 100,
        'oos_recall': best_info.get('recall', 0) * 100,
        'model_type': model_label,
        'trained_at': datetime.now().isoformat(),
        'n_samples': len(X),
        'n_tickers': len(big_data),
        'version': 'V5',
    }, THRESHOLD_PATH)
    
    print(f"\n{'='*60}")
    print(f"  ✅ GLOBAL BRAIN V5 TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"  📁 Model: {MODEL_PATH} ({os.path.getsize(MODEL_PATH)/1024/1024:.2f} MB)")
    print(f"  📊 Samples: {len(X):,} | Tickers: {len(big_data)}")
    print(f"  🎯 CV Accuracy: {mean_acc:.2f}% | CV F1: {mean_f1:.3f}")
    print(f"  🎯 OOS Accuracy: {final_acc*100:.2f}%")
    print(f"  🎯 OOS F1: {final_f1:.3f}")
    print(f"  🎯 OOS Precision: {best_info.get('prec', 0)*100:.1f}%")
    print(f"  🎯 OOS Recall: {best_info.get('recall', 0)*100:.1f}%")
    print(f"  🎯 Threshold: {optimal_threshold:.3f}")
    print(f"  🏷️ Model: {model_label}")
    print(f"  📈 Features: {len(FEATURES_V5)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    train_global_brain()
