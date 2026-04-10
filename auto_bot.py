import schedule
import pandas as pd
import os
from modules import db_manager
from modules.scanner_bridge import run_legacy_agent_bridge
from modules.scanner_runtime import (
    collect_universe_scan_candidates,
    collect_hourly_signals,
    fetch_hourly_regime_status,
    format_hourly_signal_message,
    resolve_hourly_market_candidates,
)
import FinanceDataReader as fdr
from datetime import datetime

# Initialize DB
db = db_manager.DBManager()

WATCHLIST_FILE = "watchlist_today.json"

import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

# Telegram Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):
    """Send a message to the configured Telegram Chat (Disabled per user request)"""
    print(message)
    return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram Message Sent!")
        else:
            print(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram Request Error: {e}")

def _scan_and_save(df_tickers, market_name, market_code='US'):
    """
    Helper to scan a list of tickers and overwrite watchlist.
    market_code: 'KR' or 'US'
    """
    msg = f"🌅 **[Start]** {market_name} Universe Scan ({len(df_tickers)} tickers)..."
    print(msg)
    send_telegram_message(msg)
    
    candidates = collect_universe_scan_candidates(
        df_tickers=df_tickers,
        market_code=market_code,
        save_scan_result_fn=db.save_scan_result,
        logger=print,
    )
            
    pd.DataFrame(candidates).to_json(WATCHLIST_FILE)

    # Multi-agent bridge: persist structured handoffs (additive, non-blocking).
    run_legacy_agent_bridge(
        results=candidates,
        market=market_code,
        strategy_version="legacy-bot-v1",
        model_version="legacy",
        code_version="bridge-v1",
        logger=print,
    )
    
    msg_end = f"✅ **[Finish]** {market_name} Scan Complete. Found {len(candidates)} candidates saved to Watchlist."
    print(msg_end)
    send_telegram_message(msg_end)

def job_scan_kr_universe():
    """08:00 AM: Scan KOSPI/KOSDAQ (Full + Top 100 Matches)"""
    print("📥 Fetching KR Market Data...")
    
    # Due to KRX API issues, we use KRX-DESC which doesn't have Marcap
    desc_df = fdr.StockListing('KRX-DESC')
    
    df_ks = desc_df[desc_df['Market'] == 'KOSPI'].copy()
    df_ks['Code'] = df_ks['Code'] + ".KS"
    
    df_kq = desc_df[desc_df['Market'].str.contains('KOSDAQ', na=False)].copy()
    df_kq['Code'] = df_kq['Code'] + ".KQ"
    
    full_df = pd.concat([df_ks, df_kq])
    full_df['Marcap'] = 0 # Dummy value to prevent NoneType/KeyError later
    full_df = full_df[['Code', 'Name', 'Marcap']]
    full_df = full_df[~full_df['Name'].str.contains('스팩|ETN|ETF', case=False)]
    
    _scan_and_save(full_df, "🇰🇷 KR Market", market_code='KR')

def job_scan_us_universe():
    """21:00 PM: Scan S&P500/NASDAQ"""
    # S&P500
    df_sp = fdr.StockListing('S&P500').head(50)[['Symbol', 'Name']]
    df_sp.columns = ['Code', 'Name']
    
    _scan_and_save(df_sp, "🇺🇸 US Market (S&P500)", market_code='US')
    df_sp.rename(columns={'Symbol': 'Code'}, inplace=True)
    # NASDAQ
    df_nq = fdr.StockListing('NASDAQ').head(50)[['Symbol', 'Name']]
    df_nq.rename(columns={'Symbol': 'Code'}, inplace=True)
    
    full_df = pd.concat([df_sp, df_nq])
    _scan_and_save(full_df, "🇺🇸 US Market")

def job_hourly_active_scan():
    """
    Hourly (09:00 - 15:00): Scan candidates for Buy Signals.
    Smart Filter: Only scan variable markets based on time.
    """
    now = datetime.now()
    hour = now.hour
    print(f"⏰ Hourly Scan Started: {now} (Hour: {hour})")
    
    if not os.path.exists(WATCHLIST_FILE):
        print("⚠️ No watchlist found. Running appropriate universe scan...")
        if hour < 18:
            job_scan_kr_universe()
        else:
            job_scan_us_universe()
        
    try:
        # Load Candidates (DataFrame: ticker, name)
        df_candidates = pd.read_json(WATCHLIST_FILE)
        all_candidates = df_candidates.to_dict('records') # List of dicts
    except:
        all_candidates = []
    market_ctx = resolve_hourly_market_candidates(
        all_candidates=all_candidates,
        hour=hour,
        logger=print,
    )
    active_candidates = market_ctx["active_candidates"]
    market_status = market_ctx["market_status"]
    market_name = market_ctx["market_name"]

    if not active_candidates:
        msg = f"⚠️ **[Skip]** {market_name} Open, but 0 candidates in watchlist."
        print(msg)
        send_telegram_message(msg)
        return

    start_msg = f"🏃‍♂️ **[Start]** Scanning {market_name} ({len(active_candidates)} active stocks)..."
    print(start_msg)
    send_telegram_message(start_msg)
    
    regime_status = fetch_hourly_regime_status(
        market_status=market_status,
        logger=print,
    )
    signals_to_report = collect_hourly_signals(
        active_candidates=active_candidates,
        regime_status=regime_status,
        save_signal_fn=db.save_signal,
        logger=print,
    )
            
    # --- Send Top 10 Alerts ---
    # Sort by Score Descending
    signals_to_report.sort(key=lambda x: x['score'], reverse=True)
    
    for i, s in enumerate(signals_to_report):
        if i >= 10:
            break
        msg = format_hourly_signal_message(s)
        send_telegram_message(msg)
    
    finish_msg = f"🏁 **[Finish]** Scan Completed for {market_name}. Found {len(signals_to_report)} signals. Sent alerts for Top {min(10, len(signals_to_report))}."
    print(finish_msg)
    send_telegram_message(finish_msg)

def run_schedule():
    # Schedule
    schedule.every().day.at("07:00").do(job_scan_kr_universe) # KR Morning
    schedule.every().day.at("21:00").do(job_scan_us_universe) # US Morning
    schedule.every().hour.do(job_hourly_active_scan)
    
    # Also update performance stats every 6 hours
    schedule.every(6).hours.do(db.update_performance)

    print("🤖 Auto-Bot Started. Waiting for schedule...")
    
    # For Demo purposes, run a quick scan immediately if user asks?
    # Startup check: if no watchlist, run active scan (which triggers universe scan if needed)
    # Always run immediate scan on startup (for user feedback)
    print("🚀 [Auto Bot] Starting Single Execution...")
    try:
        # Assuming 'job' here refers to the main task, which in the original context was job_hourly_active_scan
        job_hourly_active_scan() 
    except Exception as e:
        print(f"Error during job execution: {e}")
    print("✅ [Auto Bot] Execution Finished.")

if __name__ == "__main__":
    run_schedule()
