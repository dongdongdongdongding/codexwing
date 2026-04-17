import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Fetching signals from Supabase...")
res = client.table("signals").select("*").order("created_at", desc=True).limit(300).execute()
signals_df = pd.DataFrame(res.data)

print("Fetching market_scan_results from Supabase...")
res_scan = client.table("market_scan_results").select("*").order("created_at", desc=True).limit(500).execute()
scans_df = pd.DataFrame(res_scan.data)

all_tickers = set()
earliest_date = datetime.now()

if not signals_df.empty:
    all_tickers.update(signals_df['ticker'].unique())
    min_sig_date = pd.to_datetime(signals_df['created_at']).min().replace(tzinfo=None)
    if min_sig_date < earliest_date:
        earliest_date = min_sig_date

if not scans_df.empty:
    all_tickers.update(scans_df['ticker'].unique())
    min_scan_date = pd.to_datetime(scans_df['created_at']).min().replace(tzinfo=None)
    if min_scan_date < earliest_date:
        earliest_date = min_scan_date

all_tickers = {t for t in all_tickers if not t.startswith('TEST')}

start_fetch = (earliest_date - timedelta(days=5)).strftime('%Y-%m-%d')
end_fetch = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')

tickers_list = list(all_tickers)
print("Downloading batch data from Yahoo Finance...")
hist_data = yf.download(tickers_list, start=start_fetch, end=end_fetch, group_by='ticker', progress=False)

def get_forward_metrics(ticker, start_date_str, days_forward=5):
    try:
        start_date = pd.to_datetime(start_date_str).tz_localize(None)
        if len(tickers_list) == 1:
            df = hist_data.copy()
        else:
            if ticker not in hist_data.columns.levels[0]: return None
            df = hist_data[ticker].copy()
            
        df = df.dropna(subset=['Close'])
        df = df[df.index >= start_date]
        if df.empty or len(df) < 2: return None
            
        entry_price = float(df['Close'].iloc[0])
        look_forward_df = df.iloc[1:days_forward+1]
        
        if look_forward_df.empty: return None
            
        max_high = float(look_forward_df['High'].max())
        min_low = float(look_forward_df['Low'].min())
        final_close = float(look_forward_df['Close'].iloc[-1])
        
        max_return = (max_high - entry_price) / entry_price * 100
        min_return = (min_low - entry_price) / entry_price * 100
        close_return = (final_close - entry_price) / entry_price * 100
        
        # Check order: did it hit -3% before hitting +3%?
        hit_3pct = False
        hit_minus_3pct = False
        clean_3pct_win = False # Hit +3% without ever dropping below -2%
        
        for idx, row in look_forward_df.iterrows():
            daily_high_ret = (row['High'] - entry_price) / entry_price * 100
            daily_low_ret = (row['Low'] - entry_price) / entry_price * 100
            
            if daily_low_ret <= -2.0 and not hit_3pct:
                hit_minus_3pct = True
            
            if daily_high_ret >= 3.0:
                hit_3pct = True
                if not hit_minus_3pct:
                    clean_3pct_win = True
                break
                
        stop_first = hit_minus_3pct and not hit_3pct

        return {
            'max_return_5d': max_return,   # MFE proxy
            'min_return_5d': min_return,   # MAE proxy (negative)
            'close_return_5d': close_return,
            'clean_3pct_win': clean_3pct_win,
            'stop_first': stop_first,
        }
    except Exception as e:
        return None

results = []
if not signals_df.empty:
    for _, row in signals_df.iterrows():
        ticker = row['ticker']
        if ticker in all_tickers:
            metrics = get_forward_metrics(ticker, row['created_at'], 5)
            if metrics:
                results.append({
                    'type': 'signal',
                    'ml_prob': row.get('ai_prediction', 0),
                    **metrics
                })

scan_results = []
if not scans_df.empty:
    for _, row in scans_df.iterrows():
        ticker = row['ticker']
        if ticker in all_tickers:
            metrics = get_forward_metrics(ticker, row['created_at'], 5)
            if metrics:
                scan_results.append({
                    'type': 'scan',
                    'ml_prob': row.get('ml_prob', 0),
                    **metrics
                })

def _brier_score(df: pd.DataFrame, outcome_col: str, prob_col: str) -> float:
    """Mean squared error between predicted probability [0,1] and binary outcome."""
    valid = df[[prob_col, outcome_col]].dropna()
    if valid.empty:
        return float('nan')
    return float(((valid[prob_col] / 100.0 - valid[outcome_col]) ** 2).mean())


def _ece(df: pd.DataFrame, outcome_col: str, prob_col: str, n_bins: int = 10) -> float:
    """Expected Calibration Error: weighted average of |avg_prob - avg_outcome| per bin."""
    valid = df[[prob_col, outcome_col]].dropna()
    if valid.empty:
        return float('nan')
    bins = pd.cut(valid[prob_col], bins=n_bins, labels=False, include_lowest=True)
    ece_total, n_total = 0.0, len(valid)
    for b in range(n_bins):
        mask = bins == b
        if mask.sum() == 0:
            continue
        avg_prob = valid.loc[mask, prob_col].mean() / 100.0
        avg_out = valid.loc[mask, outcome_col].mean()
        ece_total += mask.sum() * abs(avg_prob - avg_out)
    return ece_total / n_total


def print_summary(data_list, title):
    if not data_list:
        return
    df = pd.DataFrame(data_list)
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(f"Total analyzed: {len(df)}")

    # --- MFE / MAE ---
    print(f"\n[MFE / MAE]")
    print(f"  Avg MFE (max_return_5d):  {df['max_return_5d'].mean():>6.2f}%")
    print(f"  Avg MAE (max_drawdown_5d): {(-df['min_return_5d']).mean():>6.2f}%")

    # --- Hit quality breakdown ---
    outcome_hit = (df['max_return_5d'] > 3).astype(int)
    df['outcome_hit'] = outcome_hit
    clean_hit_rate = df['clean_3pct_win'].mean() * 100
    stop_first_rate = df['stop_first'].mean() * 100 if 'stop_first' in df.columns else float('nan')
    win_rate = outcome_hit.mean() * 100
    print(f"\n[Hit Quality]")
    print(f"  Win Rate  (max >+3%):      {win_rate:>6.2f}%")
    print(f"  Clean Hit (no -2% first):  {clean_hit_rate:>6.2f}%")
    print(f"  Stop First (-2% before +3%): {stop_first_rate:>5.2f}%")

    # --- Expectancy ---
    pos = df[df['close_return_5d'] > 0]['close_return_5d']
    neg = df[df['close_return_5d'] <= 0]['close_return_5d']
    p_win = len(pos) / len(df)
    p_loss = len(neg) / len(df)
    avg_win = pos.mean() if not pos.empty else 0.0
    avg_loss = neg.mean() if not neg.empty else 0.0
    expectancy = p_win * avg_win + p_loss * avg_loss
    print(f"\n[Expectancy]")
    print(f"  P(win)={p_win:.2f}  avg_win={avg_win:.2f}%  |  P(loss)={p_loss:.2f}  avg_loss={avg_loss:.2f}%")
    print(f"  Expectancy per trade: {expectancy:>+.3f}%")

    # --- Brier score & ECE ---
    brier = _brier_score(df, 'outcome_hit', 'ml_prob')
    ece = _ece(df, 'outcome_hit', 'ml_prob')
    print(f"\n[Probability Calibration]")
    print(f"  Brier Score: {brier:.4f}  (lower = better, perfect = 0)")
    print(f"  ECE:         {ece:.4f}  (lower = better, perfect = 0)")

    # --- precision@5 / precision@10 (top-N by ml_prob) ---
    df_sorted = df.sort_values('ml_prob', ascending=False)
    for n in (5, 10):
        if len(df_sorted) >= n:
            topn = df_sorted.head(n)
            prec = (topn['max_return_5d'] > 3).mean() * 100
            print(f"  precision@{n:<2}: {prec:.2f}%  (top-{n} by ml_prob, Win>3%)")

    # --- Breakdown by ML probability bucket ---
    print(f"\n[By ML Probability Bucket]")
    bins = [0, 30, 40, 50, 60, 100]
    labels = ['<30%', '30-40%', '40-50%', '50-60%', '>60%']
    df['prob_bucket'] = pd.cut(df['ml_prob'], bins=bins, labels=labels)
    for bucket in labels:
        b_df = df[df['prob_bucket'] == bucket]
        if not b_df.empty:
            wr = (b_df['max_return_5d'] > 3).mean() * 100
            c_wr = b_df['clean_3pct_win'].mean() * 100
            sf = b_df['stop_first'].mean() * 100 if 'stop_first' in b_df.columns else 0.0
            exp = b_df['close_return_5d'].mean()
            print(f"  [{bucket}] n={len(b_df):>3} | MFE={b_df['max_return_5d'].mean():>5.2f}% | MAE={(-b_df['min_return_5d']).mean():>4.2f}% | Win={wr:>5.2f}% | Clean={c_wr:>5.2f}% | StopFirst={sf:>5.2f}% | E={exp:>+.2f}%")

print_summary(results, "Auto Bot Signals Report (5-day)")
print_summary(scan_results, "Web Scanner Report (5-day)")
