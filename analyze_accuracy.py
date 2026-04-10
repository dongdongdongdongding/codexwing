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
                
        return {
            'max_return_5d': max_return,
            'min_return_5d': min_return,
            'close_return_5d': close_return,
            'clean_3pct_win': clean_3pct_win
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

def print_summary(data_list, title):
    if not data_list: return
    df = pd.DataFrame(data_list)
    print(f"\n============= {title} =============")
    print(f"Total analyzed: {len(df)}")
    print(f"Avg Max Return: {df['max_return_5d'].mean():.2f}%")
    print(f"Avg Min Return (Max Drawdown): {df['min_return_5d'].mean():.2f}%")
    print(f"Win Rate (Max > 3%): {(df['max_return_5d'] > 3).mean() * 100:.2f}%")
    print(f"Clean Win Rate (+3% 도달 전 -2% 하락 안함): {df['clean_3pct_win'].mean() * 100:.2f}%")
    
    print("\n--- By ML Probability ---")
    bins = [0, 30, 40, 50, 60, 100]
    labels = ['<30%', '30-40%', '40-50%', '50-60%', '>60%']
    df['prob_bucket'] = pd.cut(df['ml_prob'], bins=bins, labels=labels)
    for bucket in labels:
        b_df = df[df['prob_bucket'] == bucket]
        if not b_df.empty:
            wr_3 = (b_df['max_return_5d'] > 3).mean() * 100
            c_wr = b_df['clean_3pct_win'].mean() * 100
            avg_max = b_df['max_return_5d'].mean()
            avg_min = b_df['min_return_5d'].mean()
            print(f"[{bucket}] count:{len(b_df):>3} | MaxRet: {avg_max:>5.2f}% | MinRet(DD): {avg_min:>6.2f}% | Win(>3%): {wr_3:>5.2f}% | CleanWin: {c_wr:>5.2f}%")

print_summary(results, "Auto Bot Signals Report (5-day)")
print_summary(scan_results, "Web Scanner Report (5-day)")
