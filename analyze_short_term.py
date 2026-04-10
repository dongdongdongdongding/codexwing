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
if not scans_df.empty:
    all_tickers.update(scans_df['ticker'].unique())

all_tickers = {t for t in all_tickers if not t.startswith('TEST')}

# We need only a couple of days forward
start_fetch = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
end_fetch = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')

tickers_list = list(all_tickers)
print(f"Downloading batch data for {len(tickers_list)} tickers...")
hist_data = yf.download(tickers_list, start=start_fetch, end=end_fetch, group_by='ticker', progress=False)

def get_short_term_metrics(ticker, start_date_str, days_forward=2):
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
        
        max_return = (max_high - entry_price) / entry_price * 100
        min_return = (min_low - entry_price) / entry_price * 100
        
        return {
            'max_return_2d': max_return,
            'min_return_2d': min_return
        }
    except Exception as e:
        return None

results = []
if not signals_df.empty:
    for _, row in signals_df.iterrows():
        ticker = row['ticker']
        if ticker in all_tickers:
            metrics = get_short_term_metrics(ticker, row['created_at'], 2)
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
            metrics = get_short_term_metrics(ticker, row['created_at'], 2)
            if metrics:
                scan_results.append({
                    'type': 'scan',
                    'ml_prob': row.get('ml_prob', 0),
                    **metrics
                })

def evaluate_strategy(data_list, title):
    if not data_list: return
    df = pd.DataFrame(data_list)
    print(f"\n============= {title} =============")
    print(f"Total analyzed: {len(df)}")
    
    print("\n[Strategy A: Buy at Current Price (시장가 즉시 진입)]")
    print(" - Win Rate (> 2% in 2 days):", (df['max_return_2d'] >= 2.0).mean() * 100, "%")
    print(" - Avg Drawdown (Max Drop in 2 days):", df['min_return_2d'].mean(), "%")
    
    # Strategy B: Limit Order at -2%
    # Suppose we only enter if the min_return drops <= -2%.
    # If it hits -2%, our new entry price is effectively Entry * 0.98.
    # The max return from that new entry is approx (max_return_2d - (-2.0))
    limit_hits = df[df['min_return_2d'] <= -2.0]
    if not limit_hits.empty:
        print("\n[Strategy B: Limit Order at -2% (눌림목 -2% 지정가 대기)]")
        print(" - Execution Rate (체결 확률):", (len(limit_hits) / len(df)) * 100, "%")
        new_max_rets = limit_hits['max_return_2d'] + 2.0 # Approximation
        print(" - Win Rate (> 2% from new entry):", (new_max_rets >= 2.0).mean() * 100, "%")
        
        # Calculate how many of these hits drop further below a -3% stop loss from the *new* entry
        # A -3% stop from -2% entry means the price dropped to -5% original.
        stop_outs = (limit_hits['min_return_2d'] <= -5.0).mean() * 100
        print(f" - Stop Out (% dropping > 3% below entry): {stop_outs}%")
    
evaluate_strategy(results, "Auto Bot Signals Report (1-2 Day Hold)")
evaluate_strategy(scan_results, "Web Scanner Report (1-2 Day Hold)")
