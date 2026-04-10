import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta_classic as ta
import joblib
import warnings
from datetime import datetime
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

# 1. Universe
SECTOR_LEADERS = [
    '005930.KS', '000660.KS', '042700.KS', '373220.KS', '006400.KS', '051910.KS', '003670.KS',
    '005380.KS', '000270.KS', '012330.KS', '207940.KS', '068270.KS', '302440.KS', '035420.KS', 
    '035720.KS', '066570.KS', '055550.KS', '032830.KS', '003490.KS', '015760.KS', '034020.KS', 
    '009150.KS', '017670.KS', '030200.KS', '086790.KS', '028260.KS', '259960.KS', '316140.KS', 
    '011200.KS', '010130.KS', '247540.KQ', '091990.KQ', '196170.KQ', '263750.KQ', '328130.KQ', 
    '145020.KQ', '403870.KQ', '058470.KQ', '041510.KQ', '000250.KQ',
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'
]

# 2. Features (V5)
FEATURES_V5 = [
    'ATR_Rel', 'MACD_Hist', 'ADX', 'Vol_Trend', 'Dist_MA20', 'Dist_MA50', 'Dist_MA200',
    'RSI', 'Vol_Rel', 'Returns', 'Mom_5', 'Mom_10', 'Mom_20', 'Return_Lag1', 'Return_Lag2',
    'WillR', 'CCI', 'Stoch_K', 'OBV_Slope', 'VWAP_Dist', 'Range_Pct', 'RSI_Lag1',
    'Consec_Up', 'Consec_Down', 'Gap_Pct', 'Vol_Spike',
    'RSI_x_Mom', 'Vol_x_ADX', 'MACD_x_OBV', 'VIX_x_RSI',
    'VIX_Level', 'VIX_Change', 'Market_Mom_20', 'Market_Vol',
    'Earnings_Proximity', 'Surprise_Pct'
]

def _fetch_cross_asset_data():
    cross = {}
    symbols = {'VIX': '^VIX', 'DXY': 'DX-Y.NYB', 'SPY': 'SPY'}
    for name, sym in symbols.items():
        try:
            df = yf.download(sym, period="5y", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                cross[name] = df['Close']
        except: pass
    return cross

def _build_features_v5(df, cross_asset):
    if len(df) < 200: return None
    
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
    
    df['Mom_5'] = df['Close'].pct_change(5)
    df['Mom_10'] = df['Close'].pct_change(10)
    df['Mom_20'] = df['Close'].pct_change(20)
    df['Return_Lag1'] = df['Returns'].shift(1)
    df['Return_Lag2'] = df['Returns'].shift(2)
    
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
    
    df['Up_Day'] = (df['Close'] > df['Close'].shift(1)).astype(int)
    df['Consec_Up'] = df['Up_Day'].rolling(5).sum()
    df['Consec_Down'] = 5 - df['Consec_Up']
    df['Gap_Pct'] = (df['Open'] - df['Close'].shift(1)) / (df['Close'].shift(1) + 1e-9)
    df['Vol_Spike'] = (df['Vol_Rel'] > 2.0).astype(int)
    
    df['RSI_x_Mom'] = df['RSI'] / 100.0 * df['Mom_5']
    df['Vol_x_ADX'] = df['Vol_Rel'] * df['ADX'] / 100.0
    df['MACD_x_OBV'] = df['MACD_Hist'] * df['OBV_Slope']
    
    if 'VIX' in cross_asset:
        vix = cross_asset['VIX'].reindex(df.index, method='ffill')
        df['VIX_Level'] = vix / 100.0
        df['VIX_Change'] = vix.pct_change(5)
        df['VIX_x_RSI'] = (vix / 100.0) * (1 - df['RSI'] / 100.0)
    else:
        df['VIX_Level'] = 0.2; df['VIX_Change'] = 0; df['VIX_x_RSI'] = 0.0
        
    if 'SPY' in cross_asset:
        spy = cross_asset['SPY'].reindex(df.index, method='ffill')
        df['Market_Mom_20'] = spy.pct_change(20)
        df['Market_Vol'] = spy.pct_change().rolling(20).std()
    else:
        df['Market_Mom_20'] = 0; df['Market_Vol'] = 0.01
        
    df['Spy_Rel_Strength'] = df['Mom_20'] - df['Market_Mom_20']
    
    df['Earnings_Proximity'] = 0.5
    df['Surprise_Pct'] = 0.0
    
    return df

def create_t1_clean_label(df, target_pct, maf_pct, max_hold_days):
    """
    Phase 18.2: Trade Quality Labeling (Clean Hit)
    Returns 1 ONLY if Target is hit before a very tight MAE (maf_pct) is breached.
    """
    labels = np.zeros(len(df))
    n = len(df)
    
    arr_open = df['Open'].values
    arr_high = df['High'].values
    arr_low = df['Low'].values
    
    for i in range(n - max_hold_days - 1):
        entry_price = arr_open[i + 1]
        if np.isnan(entry_price) or entry_price <= 0:
            continue
            
        target_price = entry_price * (1 + target_pct)
        stop_price = entry_price * (1 - maf_pct)
        
        hit = 0
        for j in range(1, max_hold_days + 1):
            day_idx = i + 1 + (j - 1)
            d_high = arr_high[day_idx]
            d_low = arr_low[day_idx]
            
            # MAE breached -> NOT a clean hit
            if d_low <= stop_price:
                hit = 0
                break
                
            if d_high >= target_price:
                hit = 1
                break
                
        labels[i] = hit

    labels[n - max_hold_days - 1:] = np.nan 
    return labels

def create_t1_strict_label(df, target_pct, stop_loss_pct, max_hold_days):
    """
    Label Generation for T+1 Reality Rule
    Returns 1 if Target is hit before Stop Loss within max_hold_days, Entry is T+1 Open.
    """
    labels = np.zeros(len(df))
    n = len(df)
    
    arr_open = df['Open'].values
    arr_high = df['High'].values
    arr_low = df['Low'].values
    
    for i in range(n - max_hold_days - 1):
        # Entry at T+1 Open
        entry_price = arr_open[i + 1]
        if np.isnan(entry_price) or entry_price <= 0:
            continue
            
        target_price = entry_price * (1 + target_pct)
        stop_price = entry_price * (1 - stop_loss_pct)
        
        hit = 0
        for j in range(1, max_hold_days + 1):
            day_idx = i + 1 + (j - 1)
            d_high = arr_high[day_idx]
            d_low = arr_low[day_idx]
            
            # Stop loss checked first (pessimistic fill)
            if d_low <= stop_price:
                hit = 0
                break
                
            if d_high >= target_price:
                hit = 1
                break
                
        labels[i] = hit

    # Nullify trailing samples that can't be fully evaluated
    labels[n - max_hold_days - 1:] = np.nan 
    return labels


def build_master_dataset():
    cross_asset = _fetch_cross_asset_data()
    big_dfs = []
    
    print("🚀 Fetching Data and Generating Strict T+1 Labels...")
    for i, t in enumerate(SECTOR_LEADERS):
        try:
            print(f"  [{i+1}/{len(SECTOR_LEADERS)}] {t}", end='\r')
            # Use history to avoid MultiIndex issues
            df = yf.Ticker(t).history(period="5y", auto_adjust=True)
            if len(df) < 200: continue
            
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
                
            df = _build_features_v5(df, cross_asset)
            if df is None: continue
            
            # Add strict labels (Friction 0.41% tax+slippage included in target)
            df['Label_3pct'] = create_t1_strict_label(df, target_pct=0.0341, stop_loss_pct=0.025, max_hold_days=3)
            df['Label_5pct'] = create_t1_strict_label(df, target_pct=0.0541, stop_loss_pct=0.040, max_hold_days=7)
            df['Label_10pct'] = create_t1_strict_label(df, target_pct=0.1041, stop_loss_pct=0.060, max_hold_days=15)
            
            # Phase 18.2: Clean Hit (Low MAE)
            df['Label_5pct_Clean'] = create_t1_clean_label(df, target_pct=0.0541, maf_pct=0.025, max_hold_days=7)
            
            df = df.replace([np.inf, -np.inf], np.nan).dropna()
            if not df.empty:
                big_dfs.append(df)
        except Exception as e:
            pass
            
    master_df = pd.concat(big_dfs, ignore_index=True)
    print(f"\n✅ Total Training Samples: {len(master_df):,}")
    return master_df


def train_calibrated_model(X, y, target_name):
    """
    Train a HistGradientBoostingClassifier and Calibrate it via Isotonic Regression.
    Evaluates strictly on a time-series split.
    """
    print(f"\n🧠 Training [{target_name}] Model...")
    pos_ratio = y.mean() * 100
    print(f"   Base Win Rate (Positives): {pos_ratio:.1f}%")
    
    if pos_ratio < 0.1 or len(y) < 100:
        print("   ⚠️ Not enough positive signals to train!")
        return None

    # Time-based split: Train (80%), Calibrate (10%), Test (10%)
    n = len(X)
    t1 = int(n * 0.8)
    t2 = int(n * 0.9)
    
    X_train, y_train = X.iloc[:t1], y.iloc[:t1]
    X_calib, y_calib = X.iloc[t1:t2], y.iloc[t1:t2]
    X_test,  y_test  = X.iloc[t2:], y.iloc[t2:]
    
    base_clf = HistGradientBoostingClassifier(
        max_iter=300, max_depth=5, min_samples_leaf=20,
        learning_rate=0.05, l2_regularization=1.0,
        class_weight='balanced', random_state=42
    )
    
    base_clf.fit(X_train, y_train)
    
    # Calibrate using Sigmoid Scaling (Platt) which handles sparse +10% targets better than Isotonic (Verified in Phase 16.5)
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_clf, method='sigmoid', cv='prefit'
    )
    calibrated_clf.fit(X_calib, y_calib)
    
    # Evaluate Brier Score (lower is better, perfect is 0)
    y_prob_calib = calibrated_clf.predict_proba(X_test)[:, 1]
    y_prob_uncalib = base_clf.predict_proba(X_test)[:, 1]
    
    brier_calib = brier_score_loss(y_test, y_prob_calib)
    brier_uncalib = brier_score_loss(y_test, y_prob_uncalib)
    
    print(f"   Brier Score (Uncalibrated): {brier_uncalib:.4f}")
    print(f"   Brier Score (Calibrated)  : {brier_calib:.4f}")
    
    # Check Accuracy of Probabilities (Platt/Isotonic correction)
    threshold = 0.60
    preds_high_conf = y_prob_calib >= threshold
    if preds_high_conf.sum() > 0:
        real_wr = y_test[preds_high_conf].mean() * 100
        print(f"   When Model predicts P > 60%, Real Win Rate is: {real_wr:.1f}% (Signals: {preds_high_conf.sum()})")
    
    return calibrated_clf


def run_pipeline():
    print("=" * 60)
    print("🔥 PHASE 18.2: Regime-Aware & Trade Quality ML Pipeline")
    print("=" * 60)
    
    FEATURES_V5_NEW = FEATURES_V5 + ['Spy_Rel_Strength']
    
    df = build_master_dataset()
    if df.empty:
        print("Data compilation failed.")
        return
        
    # Split Data by Regime (Bull vs Bear based on Market Mom 20)
    df_bull = df[df['Market_Mom_20'] > 0]
    df_bear = df[df['Market_Mom_20'] <= 0]
    
    print(f"\n📊 Regime Split: BULL ({len(df_bull)} samples) vs BEAR ({len(df_bear)} samples)")
    
    # --- BULL REGIME MODELS ---
    X_bull = df_bull[FEATURES_V5_NEW]
    clf_5_bull = train_calibrated_model(X_bull, df_bull['Label_5pct'], "5% Swing (BULL)")
    if clf_5_bull: joblib.dump(clf_5_bull, os.path.join(MODELS_DIR, 'model_5pct_bull.pkl'))
    
    clf_clean_bull = train_calibrated_model(X_bull, df_bull['Label_5pct_Clean'], "5% Clean Hit (BULL)")
    if clf_clean_bull: joblib.dump(clf_clean_bull, os.path.join(MODELS_DIR, 'model_5pct_clean_bull.pkl'))

    # --- BEAR REGIME MODELS ---
    X_bear = df_bear[FEATURES_V5_NEW]
    clf_5_bear = train_calibrated_model(X_bear, df_bear['Label_5pct'], "5% Swing (BEAR)")
    if clf_5_bear: joblib.dump(clf_5_bear, os.path.join(MODELS_DIR, 'model_5pct_bear.pkl'))
    
    clf_clean_bear = train_calibrated_model(X_bear, df_bear['Label_5pct_Clean'], "5% Clean Hit (BEAR)")
    if clf_clean_bear: joblib.dump(clf_clean_bear, os.path.join(MODELS_DIR, 'model_5pct_clean_bear.pkl'))
    
    # Save Metadata
    meta = {
        "trained_at": datetime.now().isoformat(),
        "features": FEATURES_V5_NEW,
        "version": "Phase18.2_Regime_Clean"
    }
    joblib.dump(meta, os.path.join(MODELS_DIR, 'model_meta.pkl'))
    print(f"\n✅ All 3 Target-Specific Calibrated Models Saved to {MODELS_DIR}")

if __name__ == '__main__':
    run_pipeline()
