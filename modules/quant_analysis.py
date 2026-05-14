import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
import numpy as np
import FinanceDataReader as fdr
from prophet import Prophet
from datetime import datetime, timedelta
import json
import os
import contextlib
import io

HAS_TALIB = False
try:
    import talib
    HAS_TALIB = True
except ImportError:
    pass
    
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.cluster import KMeans
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    HAS_ML = True
except ImportError:
    HAS_ML = False
    print("⚠️ scikit-learn not found. ML features disabled.")

try:
    from pykrx import stock
    HAS_PYKRX = True
except ImportError:
    HAS_PYKRX = False
    print("⚠️ PyKrx not found. Korean Investor data will be unavailable.")

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except Exception as e:
    HAS_XGBOOST = False
    # print(f"⚠️ XGBoost not found or failed to load. Hybrid forecasting disabled.")

import pandas_ta_classic as ta
import joblib # Phase 34: Universal Model Persistence
import time
from modules.inverted_signal_features import compute_low_prob_high_score_features
from modules.loss_risk_features import compute_loss_risk_features
from modules.live_scan_context import live_mode_enabled
from modules.market_data import get_history

# Global Macro Cache to prevent 429 Too Many Requests during Deep Dive
_GLOBAL_MACRO_CACHE = None
_GLOBAL_MACRO_CACHE_TIME = 0

class RateLimitError(Exception):
    """Custom Exception for API Rate Limiting (429)"""
    pass

class QuantStrategy:
    def __init__(self, ticker: str, is_advanced_engine: bool = False) -> None:
        self.ticker = ticker
        self.is_advanced_engine = is_advanced_engine
        self.scan_mode = "SWING"
        self.strategy_family = None
        self.df: pd.DataFrame = pd.DataFrame()
        self.df_weekly: pd.DataFrame = pd.DataFrame()

    @staticmethod
    def _fallback_us_tickers(market_type: str) -> dict:
        """Best-effort US ticker fallback when FDR/Naver listing is unavailable."""
        market_key = str(market_type or "").upper()
        result: dict[str, str] = {}

        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            profile_path = os.path.join(base_dir, "models", "regime_ticker_profiles.json")
            with open(profile_path, "r", encoding="utf-8") as fh:
                profiles = json.load(fh)
            us_profiles = ((profiles or {}).get("profiles") or {}).get("US") or {}
            if isinstance(us_profiles, dict):
                for rows in us_profiles.values():
                    if not isinstance(rows, dict):
                        continue
                    for sym, row in rows.items():
                        symbol = str(sym or "").strip().upper()
                        if not symbol or any(ch in symbol for ch in (".", "/", "^")):
                            continue
                        name = symbol
                        if isinstance(row, dict):
                            name = str(row.get("stock_name") or row.get("name") or symbol).strip() or symbol
                        result[symbol] = name
        except Exception:
            result = {}

        if result and market_key != "NASDAQ":
            return dict(sorted(result.items()))

        if market_key == "NASDAQ":
            core = {
                "AAPL": "Apple Inc.",
                "ADBE": "Adobe Inc.",
                "ADI": "Analog Devices Inc.",
                "ADP": "Automatic Data Processing",
                "ADSK": "Autodesk Inc.",
                "AMAT": "Applied Materials Inc.",
                "AMD": "Advanced Micro Devices Inc.",
                "AMGN": "Amgen Inc.",
                "AMZN": "Amazon.com Inc.",
                "ARM": "Arm Holdings plc",
                "ASML": "ASML Holding NV",
                "AVGO": "Broadcom Inc.",
                "AZN": "AstraZeneca PLC",
                "BIIB": "Biogen Inc.",
                "BKNG": "Booking Holdings Inc.",
                "CDNS": "Cadence Design Systems Inc.",
                "CEG": "Constellation Energy Corp.",
                "CHTR": "Charter Communications Inc.",
                "CMCSA": "Comcast Corp.",
                "COST": "Costco Wholesale Corp.",
                "CPRT": "Copart Inc.",
                "CRWD": "CrowdStrike Holdings Inc.",
                "CSCO": "Cisco Systems Inc.",
                "CSX": "CSX Corp.",
                "CTAS": "Cintas Corp.",
                "DDOG": "Datadog Inc.",
                "DXCM": "DexCom Inc.",
                "EA": "Electronic Arts Inc.",
                "EXC": "Exelon Corp.",
                "FANG": "Diamondback Energy Inc.",
                "FAST": "Fastenal Co.",
                "FTNT": "Fortinet Inc.",
                "GFS": "GlobalFoundries Inc.",
                "GILD": "Gilead Sciences Inc.",
                "GOOG": "Alphabet Inc.",
                "GOOGL": "Alphabet Inc.",
                "HON": "Honeywell International Inc.",
                "IDXX": "IDEXX Laboratories Inc.",
                "INTC": "Intel Corp.",
                "INTU": "Intuit Inc.",
                "ISRG": "Intuitive Surgical Inc.",
                "KDP": "Keurig Dr Pepper Inc.",
                "KLAC": "KLA Corp.",
                "LIN": "Linde plc",
                "LRCX": "Lam Research Corp.",
                "MAR": "Marriott International Inc.",
                "MCHP": "Microchip Technology Inc.",
                "MDB": "MongoDB Inc.",
                "MDLZ": "Mondelez International Inc.",
                "MELI": "MercadoLibre Inc.",
                "META": "Meta Platforms Inc.",
                "MNST": "Monster Beverage Corp.",
                "MRNA": "Moderna Inc.",
                "MRVL": "Marvell Technology Inc.",
                "MSFT": "Microsoft Corp.",
                "MU": "Micron Technology Inc.",
                "NFLX": "Netflix Inc.",
                "NVDA": "NVIDIA Corp.",
                "NXPI": "NXP Semiconductors NV",
                "ODFL": "Old Dominion Freight Line Inc.",
                "ON": "ON Semiconductor Corp.",
                "ORLY": "O'Reilly Automotive Inc.",
                "PANW": "Palo Alto Networks Inc.",
                "PAYX": "Paychex Inc.",
                "PCAR": "Paccar Inc.",
                "PEP": "PepsiCo Inc.",
                "PLTR": "Palantir Technologies Inc.",
                "PYPL": "PayPal Holdings Inc.",
                "QCOM": "Qualcomm Inc.",
                "REGN": "Regeneron Pharmaceuticals Inc.",
                "ROP": "Roper Technologies Inc.",
                "ROST": "Ross Stores Inc.",
                "SBUX": "Starbucks Corp.",
                "SNPS": "Synopsys Inc.",
                "TEAM": "Atlassian Corp.",
                "TMUS": "T-Mobile US Inc.",
                "TSLA": "Tesla Inc.",
                "TTD": "The Trade Desk Inc.",
                "TTWO": "Take-Two Interactive Software Inc.",
                "TXN": "Texas Instruments Inc.",
                "VRSK": "Verisk Analytics Inc.",
                "VRTX": "Vertex Pharmaceuticals Inc.",
                "WBD": "Warner Bros. Discovery Inc.",
                "WDAY": "Workday Inc.",
                "XEL": "Xcel Energy Inc.",
                "ZS": "Zscaler Inc.",
            }
            return core

        return result
    
    @staticmethod
    def get_market_tickers(market_type):
        """
        Fetch ticker list for major markets.
        Returns a DICT: { 'Ticker': 'Name' }
        """
        try:
            result = {}
            
            # Handle KRX markets specially due to API issues in pykrx/fdr
            if market_type in ['KOSPI', 'KOSDAQ']:
                import urllib.request as urllib_req
                import io
                from datetime import datetime
                
                url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download'
                response = urllib_req.urlopen(url)
                html_text = response.read().decode('euc-kr')
                df = pd.read_html(io.StringIO(html_text), header=0)[0]
                
                # KIND Market format: '유가' for KOSPI, '코스닥' for KOSDAQ
                target_market_str = '유가' if market_type == 'KOSPI' else '코스닥'
                df = df[df['시장구분'] == target_market_str]
                df = df.copy()

                # Keep scanner universe focused on mature common stocks.
                if '상장일' in df.columns:
                    df['상장일'] = pd.to_datetime(df['상장일'], errors='coerce')

                try:
                    min_listing_days = int(os.getenv("AG_KRX_MIN_LISTING_DAYS", "0"))
                except Exception:
                    min_listing_days = 0
                if min_listing_days < 0:
                    min_listing_days = 0

                exclude_spacs = str(os.getenv("AG_KRX_EXCLUDE_SPACS", "1")).strip().lower() not in {"0", "false", "off", "no"}
                exclude_non_numeric = str(os.getenv("AG_KRX_EXCLUDE_NON_NUMERIC_CODES", "1")).strip().lower() not in {"0", "false", "off", "no"}

                if exclude_non_numeric:
                    df = df[df['종목코드'].astype(str).str.fullmatch(r'\d{6}', na=False)]

                if exclude_spacs:
                    name_series = df['회사명'].astype(str)
                    product_series = df['주요제품'].astype(str) if '주요제품' in df.columns else ""
                    spac_mask = (
                        name_series.str.contains('스팩', case=False, na=False)
                        | name_series.str.contains('기업인수목적', case=False, na=False)
                        | pd.Series(product_series).astype(str).str.contains('기업인수', case=False, na=False)
                    )
                    df = df[~spac_mask]

                if '상장일' in df.columns and min_listing_days > 0:
                    cutoff = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=min_listing_days)
                    df = df[df['상장일'].notna() & (df['상장일'] <= cutoff)]

                if '상장일' in df.columns:
                    df = df.sort_values(by=['상장일', '종목코드'], ascending=[True, True], kind='stable')
                else:
                    df = df.sort_values(by=['종목코드'], ascending=[True], kind='stable')

                # Overlay live market metadata so the scanner starts from liquid names first.
                try:
                    live_df = fdr.StockListing(market_type)
                    if isinstance(live_df, pd.DataFrame) and not live_df.empty and 'Code' in live_df.columns:
                        live_df = live_df.copy()
                        live_df['Code'] = live_df['Code'].astype(str).str.zfill(6)
                        keep_cols = [c for c in ['Code', 'Name', 'Volume', 'Amount', 'Marcap'] if c in live_df.columns]
                        live_df = live_df[keep_cols]
                        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
                        df = df.merge(live_df, how='left', left_on='종목코드', right_on='Code')
                        if 'Name' in df.columns:
                            df['회사명'] = df['Name'].fillna(df['회사명'])
                        if 'Amount' in df.columns:
                            enforce_amount_floor = str(os.getenv("AG_KRX_ENFORCE_UNIVERSE_MIN_AMOUNT", "0")).strip().lower() in {"1", "true", "yes", "on"}
                            if enforce_amount_floor:
                                try:
                                    kospi_universe_min_amount = float(os.getenv("AG_KOSPI_UNIVERSE_MIN_AMOUNT", "12000000000"))
                                except Exception:
                                    kospi_universe_min_amount = 12_000_000_000.0
                                try:
                                    kosdaq_universe_min_amount = float(os.getenv("AG_KOSDAQ_UNIVERSE_MIN_AMOUNT", "5000000000"))
                                except Exception:
                                    kosdaq_universe_min_amount = 5_000_000_000.0
                                universe_min_amount = (
                                    kosdaq_universe_min_amount if market_type == "KOSDAQ" else kospi_universe_min_amount
                                )
                                if universe_min_amount > 0:
                                    amount_series = pd.to_numeric(df['Amount'], errors='coerce')
                                    liquid_df = df[amount_series >= universe_min_amount].copy()
                                    if not liquid_df.empty:
                                        df = liquid_df
                        sort_cols = [c for c in ['Marcap', 'Amount', 'Volume'] if c in df.columns]
                        if sort_cols:
                            asc = [False] * len(sort_cols)
                            if '상장일' in df.columns:
                                sort_cols.append('상장일')
                                asc.append(True)
                            df = df.sort_values(by=sort_cols, ascending=asc, kind='stable')
                except Exception:
                    pass
                
                suffix = ".KS" if market_type == "KOSPI" else ".KQ"
                for _, row in df.iterrows():
                    # KIND zero-pads the code to 6 digits optionally
                    code = str(row['종목코드']).zfill(6)
                    ticker = f"{code}{suffix}"
                    result[ticker] = row['회사명']
                return result
                
            df = fdr.StockListing(market_type)
            
            # FDR returns DataFrame with 'Symbol', 'Name', etc.
            if market_type in ['S&P500', 'NASDAQ']:
                # US markets
                for _, row in df.iterrows():
                    result[row['Symbol']] = row['Name']
                if not result:
                    result = QuantStrategy._fallback_us_tickers(market_type)
                return result
            
            if market_type == 'AMEX':
                # AMEX: Filter junk (ETFs/warrants have symbols with digits or >4 chars with special chars)
                for _, row in df.iterrows():
                    sym = str(row.get('Symbol', '')).strip()
                    name = str(row.get('Name', sym)).strip()
                    # Skip obvious ETFs/warrants (symbols ending in W/R/P/U or with ^ etc)
                    if not sym or any(c in sym for c in ['^', '.', '/', '-']):
                        continue
                    if len(sym) > 5:
                        continue
                    result[sym] = name
                return result

        except Exception as e:
            if str(market_type).upper() in {"NASDAQ", "S&P500"}:
                fallback = QuantStrategy._fallback_us_tickers(str(market_type))
                if fallback:
                    print(f"Error fetching tickers: {e}. Using local {market_type} fallback universe ({len(fallback)} symbols).")
                    return fallback
            print(f"Error fetching tickers: {e}")
            return {}

    # [BUG-FIX] Deleted duplicate legacy staticmethod `fetch_macro_context`.
    # Macro data is now exclusively handled by `_fetch_global_macro_data()` or the instance `fetch_macro_context()`.

    def get_intraday_volume_multiplier(self, is_korean=True):
        """
        Projects full-day volume based on elapsed time within trading hours.
        KR: 09:00 - 15:30 (390 mins)
        US: 09:30 - 16:00 EST (390 mins)
        Advanced Mode uses U-Shape curve to prevent morning false positives.
        """
        import datetime, pytz
        
        try:
            if is_korean:
                tz = pytz.timezone('Asia/Seoul')
                now = datetime.datetime.now(tz)
                if now.weekday() >= 5: return 1.0 # Weekend
                
                start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
                
            else:
                tz = pytz.timezone('US/Eastern')
                now = datetime.datetime.now(tz)
                if now.weekday() >= 5: return 1.0
                
                start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
                end_time = now.replace(hour=16, minute=0, second=0, microsecond=0)

            if now < start_time:
                return 1.0  # Pre-market
            elif now > end_time:
                return 1.0  # After-hours or closed
                
            elapsed_mins = (now - start_time).total_seconds() / 60.0
            total_mins = 390.0
            
            if elapsed_mins < 15:
                # First 15 mins too volatile, avoid huge mults. Do not project strictly yet.
                return 1.0 
                
            if getattr(self, 'is_advanced_engine', False):
                # U-Shape Volume Profile Approximation (Institutional)
                # Morning (First 90 mins): 30% of total volume
                # Mid-day (180 mins): 40% of total volume
                # Afternoon (120 mins): 30% of total volume
                
                pct_elapsed = elapsed_mins / total_mins
                
                if elapsed_mins <= 90:
                    # Linearly accumulate up to 30%
                    vol_achieved_pct = (elapsed_mins / 90.0) * 0.30
                elif elapsed_mins <= 270:
                    # 30% + accumulating the middle 40%
                    vol_achieved_pct = 0.30 + ((elapsed_mins - 90.0) / 180.0) * 0.40
                else:
                    # 70% + accumulating the final 30%
                    vol_achieved_pct = 0.70 + ((elapsed_mins - 270.0) / 120.0) * 0.30
                
                multiplier = 1.0 / max(0.05, vol_achieved_pct)
                return min(multiplier, 6.0) # Cap at 6x to avoid extreme edge cases
            else:
                # Legacy Linear Mode
                return total_mins / elapsed_mins
                
        except Exception:
            return 1.0
            
    def fetch_data(self, period="max", interval="1d"):
        """Fetch Daily/Weekly or Intraday data (supports 4h via resampling)
        Uses yf.Ticker().history() instead of yf.download() for thread-safety.
        """
        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                target_interval = interval
                fetch_interval = interval
                fetch_period = period
                
                # Handle 4h custom
                if interval == "4h":
                    fetch_interval = "1h"
                    fetch_period = "730d" # Max for hourly
                    
                # 1. Fetch Primary Data with fallback providers.
                self.df = get_history(self.ticker, period=fetch_period, interval=fetch_interval)
                
                # Handle multi-index columns (safety)
                if isinstance(self.df.columns, pd.MultiIndex):
                    self.df.columns = self.df.columns.droplevel(1)
                    
                # TZ Cleanup (Normalize to Naive execution)
                if hasattr(self.df.index, "tz") and self.df.index.tz is not None:
                    self.df.index = self.df.index.tz_localize(None)
                
                # Drop extra columns from Ticker.history() (Dividends, Stock Splits, Capital Gains)
                keep_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                self.df = self.df[[c for c in keep_cols if c in self.df.columns]]
                
                # Resample if needed (1h -> 4h)
                if target_interval == "4h":
                    self.df = self.df.resample("4h").agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                
                if len(self.df) < 50: # Minimum data required
                    return False

                self.df = self.df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

                # Intraday refresh: update today's bar with latest intraday tape while market is open.
                if target_interval == "1d" and live_mode_enabled(self.ticker):
                    try:
                        intraday_df = get_history(self.ticker, period="5d", interval="1h")
                        if not intraday_df.empty:
                            intraday_df = intraday_df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                            latest_date = intraday_df.index[-1].date()
                            session_rows = intraday_df[intraday_df.index.date == latest_date]
                            if not session_rows.empty:
                                last_daily_idx = self.df.index[-1]
                                if last_daily_idx.date() == latest_date:
                                    self.df.loc[last_daily_idx, 'Open'] = float(session_rows['Open'].iloc[0])
                                    self.df.loc[last_daily_idx, 'High'] = max(
                                        float(self.df.loc[last_daily_idx, 'High']),
                                        float(session_rows['High'].max()),
                                    )
                                    self.df.loc[last_daily_idx, 'Low'] = min(
                                        float(self.df.loc[last_daily_idx, 'Low']),
                                        float(session_rows['Low'].min()),
                                    )
                                    self.df.loc[last_daily_idx, 'Close'] = float(session_rows['Close'].iloc[-1])
                                    self.df.loc[last_daily_idx, 'Volume'] = max(
                                        float(self.df.loc[last_daily_idx, 'Volume']),
                                        float(session_rows['Volume'].sum()),
                                    )
                    except Exception:
                        pass
                
                # --- PHASE 10: Intraday Volume Projection Penetration ---
                # Apply the multiplier directly to the DataFrame's current day volume.
                # This fixes the Morning False Positive/Negative bugs for ALL downstream indicators.
                if len(self.df) > 0 and 'Volume' in self.df.columns:
                    is_korean = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ') or str(self.ticker).isdigit()
                    multiplier = self.get_intraday_volume_multiplier(is_korean=is_korean)
                    if multiplier > 1.0:
                        self.df['Volume'] = self.df['Volume'].astype(float)
                        self.df.iloc[-1, self.df.columns.get_loc('Volume')] *= float(multiplier)

                # Store metadata
                self.data_interval = target_interval
                
                return True
                
            except Exception as e:
                err_str = str(e).lower()
                if "too many requests" in err_str or "rate limit" in err_str or "429" in err_str:
                    if attempt < max_retries - 1:
                        wait_secs = 20 + (attempt * 10)  # 20s, 30s, 40s...
                        print(f"⏳ Rate Limit for {self.ticker}. Waiting {wait_secs}s... (Retry {attempt+1}/{max_retries})")
                        time.sleep(wait_secs)
                        continue
                    else:
                        print(f"❌ Rate Limit for {self.ticker}: Max retries exhausted. Skipping.")
                        return False
                
                print(f"Error fetching data for {self.ticker}: {e}")
                return False
                
        return False

    def _fetch_global_macro_data(self):
        """
        Fetch Macro Economic Indicators for Context-Aware ML.
        Uses a Global Cache to prevent Rate Limiting (429) during Deep Dive scans.
        """
        global _GLOBAL_MACRO_CACHE, _GLOBAL_MACRO_CACHE_TIME
        now = time.time()
        
        # 1-hour cache
        if _GLOBAL_MACRO_CACHE is not None and (now - _GLOBAL_MACRO_CACHE_TIME < 3600):
            return _GLOBAL_MACRO_CACHE.copy()
            
        try:
            macro_tickers = ['^VIX', '^TNX', 'KRW=X']
            frames = {}
            for mt in macro_tickers:
                try:
                    h = get_history(mt, period='2y', interval='1d')
                    if not h.empty:
                        col_name = mt.replace('^', '')  # VIX, TNX
                        frames[col_name] = h['Close']
                except:
                    pass
            
            if not frames:
                return None
            
            macro_df = pd.DataFrame(frames)
            macro_df = macro_df.ffill()
            
            # TZ Cleanup
            if hasattr(macro_df.index, "tz") and macro_df.index.tz is not None:
                macro_df.index = macro_df.index.tz_localize(None)
            
            _GLOBAL_MACRO_CACHE = macro_df.copy()
            _GLOBAL_MACRO_CACHE_TIME = now
            return macro_df
        except Exception as e:
            err_str = str(e).lower()
            if "too many requests" in err_str or "rate limit" in err_str or "429" in err_str:
                print(f"⏳ Macro Data Rate Limit. Waiting 15s...")
                time.sleep(15)
                # Return None gracefully - scanner will proceed without macro data
            return None

    def calculate_indicators(self):
        """Calculate Technical Indicators for both timeframes"""
        if self.df is None:
            return
        try:
            # 0. Macro Data Integration (Phase 18)
            if self.df.index.name != 'Date' and 'Date' in self.df.columns:
                 self.df = self.df.set_index('Date')
                 
            # Deduplicate Columns (Safety)
            self.df = self.df.loc[:, ~self.df.columns.duplicated()]

            # Only fetch for Daily TF
            if self.data_interval == "1d": 
                try:
                    # Rename function call to match definition
                    macro_df = self._fetch_global_macro_data()
                    
                    if macro_df is not None and not macro_df.empty:
                        # Reindex macro to match stock df
                        # macro_df index might be TZ-aware, strip it to match self.df (naive)
                        if hasattr(macro_df.index, "tz") and macro_df.index.tz is not None:
                            macro_df.index = macro_df.index.tz_localize(None)

                        macro_df = macro_df.reindex(self.df.index).ffill()
                        
                        # Safe Join
                        cols_to_use = macro_df.columns.difference(self.df.columns)
                        self.df = self.df.join(macro_df[cols_to_use], rsuffix='_macro')
                        
                        # Fill NaNs
                        for c in ['VIX', 'TNX', 'KRW=X']: # Changed DXY to KRW=X
                            if c in self.df.columns:
                                self.df[c] = self.df[c].ffill().fillna(0)
                        
                        # print("🌐 Macro features merged")
                except Exception as me:
                    pass # print(f"Macro Merge Failed: {me}")

            # 1. Moving Averages - Safe Assignment to prevent NoneType Error
            ma5 = ta.sma(self.df['Close'], length=5)
            if ma5 is not None: self.df['MA_5'] = ma5
            ma20 = ta.sma(self.df['Close'], length=20)
            if ma20 is not None: self.df['MA_20'] = ma20
            ma50 = ta.sma(self.df['Close'], length=50)
            if ma50 is not None: self.df['MA_50'] = ma50
            ma200 = ta.sma(self.df['Close'], length=200)
            if ma200 is not None: self.df['MA_200'] = ma200

            # 2. RSI & Volatility
            rsi = ta.rsi(self.df['Close'], length=14)
            if rsi is not None: self.df['RSI'] = rsi
            atr = ta.atr(self.df['High'], self.df['Low'], self.df['Close'], length=14)
            if atr is not None: self.df['ATR'] = atr
            
            # 3. MACD Standardized (EMA12, EMA26, Signal9)
            macd = ta.macd(self.df['Close'], fast=12, slow=26, signal=9)
            if macd is not None:
                self.df = pd.concat([self.df, macd], axis=1)
                if 'MACD_12_26_9' in self.df.columns: self.df['MACD'] = self.df['MACD_12_26_9']
                if 'MACDs_12_26_9' in self.df.columns: self.df['MACD_signal'] = self.df['MACDs_12_26_9']
                if 'MACDh_12_26_9' in self.df.columns: 
                    self.df['MACD_hist'] = self.df['MACDh_12_26_9']
                    # Normalize MACD Histogram by ATR to prevent absolute value distortion
                    if 'ATR' in self.df.columns:
                        self.df['MACD_Hist_Norm'] = self.df['MACD_hist'] / self.df['ATR'].replace(0, 0.001)
                
            # 4. Bollinger Bands (20, 2)
            bb = ta.bbands(self.df['Close'], length=20, std=2)
            if bb is not None:
                self.df = pd.concat([self.df, bb], axis=1)

            # 5. Multi-Timeframe (Weekly) - Phase 18
            self.calculate_mtf_indicators()
            
            # 6. Relative Strength (Mansfield) - Phase 18
            self.calculate_mansfield_rs()
            
            # 7. Tech Score Normalization (Phase 30)
            self.calculate_tech_score()

        except Exception as e:
            print(f"Indicator Error: {e}")
            import traceback
            traceback.print_exc()
            
    def calculate_tech_score(self):
        """
        Phase 30: Confluence Scoring Logic (0-100)
        CRITICAL: No imputation! If data is missing (NaN), the score becomes NaN.
        """
        try:
            # 1. Check Data Presence
            required_cols = ['RSI', 'MA_50', 'MA_200', 'MA_20', 'MACD', 'BBL_20_2.0']
            for col in required_cols:
                if col not in self.df.columns or self.df[col].isna().all():
                    # If any core indicator is totally missing, we cannot score this stock accurately.
                    self.df['Alpha_Score'] = np.nan
                    return
            
            # Initialize Score Series with NaN, and only calculate where data is present
            score = pd.Series(0.0, index=self.df.index)
            
            # 1. RSI Confluence (30 pts)
            rsi = self.df['RSI']
            score += np.where(rsi < 30, 20, 0) # Oversold (Reversal)
            score += np.where((rsi > 50) & (rsi < 70), 10, 0) # Bullish Zone
            
            # 2. Moving Averages (30 pts)
            ma50 = self.df['MA_50']
            ma200 = self.df['MA_200']
            score += np.where(ma50 > ma200, 20, 0) # Long Term Bull
                
            # Short Term Trend (Close > MA20)
            ma20 = self.df['MA_20']
            score += np.where(self.df['Close'] > ma20, 10, 0)
                
            # 3. MACD Momentum (20 pts)
            macd = self.df['MACD']
            macd_sig = self.df['MACD_signal'] if 'MACD_signal' in self.df.columns else self.df['MACD']
            score += np.where(macd > macd_sig, 20, 0)
                
            # 4. Bollinger Bands (20 pts)
            bbl = self.df['BBL_20_2.0']
            bbu = self.df['BBU_20_2.0'] if 'BBU_20_2.0' in self.df.columns else bbl * 1.1
            
            denom = (bbu - bbl).replace(0, 0.001)
            pb = (self.df['Close'] - bbl) / denom
            score += np.where(pb < 0.2, 20, 0)
            score += np.where(pb > 0.8, 10, 0)

            # --- Expert Refinement: Fake Breakout Penalty ---
            body = (self.df['Close'] - self.df['Open']).abs().replace(0, 0.001)
            upper_wick = self.df['High'] - self.df[['Open', 'Close']].max(axis=1)
            
            trap_mask = (upper_wick > body * 2) & (self.df['Close'] > self.df['Open'])
            score -= np.where(trap_mask, 20, 0)
            
            # --- Expert Refinement: Short-Term Momentum ---
            if 'Volume' in self.df.columns:
                vol_ma20 = self.df['Volume'].rolling(20).mean()
                vol_surge = self.df['Volume'] > (vol_ma20 * 1.5)
                score += np.where(vol_surge == True, 15, 0)
                
            # ROC_5
            roc_5 = self.df['Close'].pct_change(5)
            score += np.where(roc_5 > 0, 15, 0)
            
            # Gap Up
            prev_close = self.df['Close'].shift(1)
            gap_up = self.df['Open'] > prev_close
            score += np.where(gap_up == True, 10, 0)
            
            # Propagate NaNs: If any indicator was NaN at a specific date, the score there is NaN
            # Actually, compute final Alpha Score
            self.df['Alpha_Score'] = score.clip(0, 100)
            self.df['Antigrav_Score'] = self.df['Alpha_Score']  # Alias for scanner compatibility
            # If RSI is NaN at index i, score[i] should be NaN
            # Using bitwise OR for all NaNs across indicators
            mask = self.df[required_cols].isna().any(axis=1)
            self.df.loc[mask, 'Alpha_Score'] = np.nan
            
        except Exception as e:
            print(f"Tech Score Error: {e}")
            self.df['Alpha_Score'] = np.nan
        
        # --- Phase 30: XGBoost Features (For Strategy Lab) ---
        # These features MUST always run, regardless of Tech Score success/failure
        try:
            # 1. Volume Change (Rel Vol)
            if 'Volume' in self.df.columns:
                vol_ma20 = self.df['Volume'].rolling(20).mean().replace(0, 1)
                self.df['Vol_Change'] = self.df['Volume'] / vol_ma20
            else:
                self.df['Vol_Change'] = 1.0
                
            # 2. Price Gap
            prev_close = self.df['Close'].shift(1)
            self.df['Price_Gap'] = (self.df['Open'] - prev_close) / prev_close
            self.df['Price_Gap'] = self.df['Price_Gap'].fillna(0)
            
            # 3. BB Width
            if 'BBU_20_2.0' in self.df.columns:
                width = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0'])
                mid = self.df['MA_20'] if 'MA_20' in self.df.columns else self.df['Close']
                self.df['BB_Width'] = width / mid
            else:
                self.df['BB_Width'] = 0
                
            # 4. ROC 5
            self.df['ROC_5'] = self.df['Close'].pct_change(5) * 100
        except Exception as e:
            print(f"XGBoost Feature Error: {e}")
            
    def calculate_mtf_indicators(self):
        """Phase 18: Compute Weekly Indicators and Merge to Daily"""
        try:
            # Resample to Weekly
            df_w = self.df.resample('W').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            })
            
            # Weekly Indicators
            df_w['W_MA20'] = ta.sma(df_w['Close'], length=20)
            df_w['W_RSI'] = ta.rsi(df_w['Close'], length=14)
            
            # Weekly Trend (Slope)
            df_w['W_Trend'] = 1.0 # Default to UP if no basis for down
            w_ma20 = pd.to_numeric(df_w['W_MA20'], errors='coerce')
            df_w['W_Trend'] = np.where(w_ma20 > w_ma20.shift(1), 1, -1)
            # Mark NaNs
            df_w.loc[w_ma20.isna(), 'W_Trend'] = np.nan
            
            # Select Cols to Merge
            df_w_sub = df_w[['W_RSI', 'W_Trend']]
            
            # Reindex to Daily (Forward Fill)
            # This aligns the weekly value to all days in that week (or following week? careful with lookahead)
            # Standard: ffill. Meaning Monday knows last Friday's weekly close. 
            # Or Monday knows "Current Week so far"? No, should use "Previous Week" usually to avoid lookahead bias.
            # But resample 'W' sets date to Sunday. 
            # Simple approach: Reindex and ffill.
            
            df_w_daily = df_w_sub.reindex(self.df.index, method='ffill')
            self.df['W_RSI'] = df_w_daily['W_RSI']
            self.df['W_Trend'] = df_w_daily['W_Trend']
            
            self.df['W_RSI'] = self.df['W_RSI'].fillna(50)
            self.df['W_Trend'] = self.df['W_Trend'].fillna(0)
            
        except Exception as e:
            # print(f"MTF Error: {e}")
            pass

    def calculate_mansfield_rs(self):
        """Phase 18: Calculate Mansfield Relative Strength vs S&P500/KOSPI"""
        try:
            bench_ticker = "^KS11" if ".KS" in self.ticker or ".KQ" in self.ticker else "^GSPC"
            bench_hist = get_history(bench_ticker, period="2y", interval="1d")
            if bench_hist is None or bench_hist.empty:
                return
            bench = bench_hist['Close']
            
            if not bench.empty:
                # Align
                bench = bench.reindex(self.df.index, method='ffill')
                
                # Relative Strength Ratio = Stock / Benchmark
                rs_raw = self.df['Close'] / bench
                
                # Mansfield RS = ((RS_Raw / 50-day MA of RS_Raw) - 1) * 10
                rs_ma = rs_raw.rolling(50).mean()
                mansfield = ((rs_raw / rs_ma) - 1) * 10
                
                self.df['RS_Mansfield'] = mansfield.fillna(0)
            else:
                self.df['RS_Mansfield'] = 0
                
        except Exception as e:
            self.df['RS_Mansfield'] = 0
        # [BUG-3 FIX] Dead code removed — Weekly indicators are handled by calculate_mtf_indicators()

    def check_signals(self):
        """Generate Buy/Sell signals based on strategies + Multi-timeframe Filter"""
        if self.df is None:
            return


        # 0. Deduplicate Columns (Critical Fix for 'Operands are not aligned')
        self.df = self.df.loc[:, ~self.df.columns.duplicated()]
        
        # 1. Merge Weekly Trend into Daily Data (Forward Fill)
        # Resample daily to match daily index, filling with last available weekly data
        if 'W_Trend' in self.df.columns:
            self.df['Weekly_Trend'] = self.df['W_Trend'].fillna(0)
        else:
            self.df['Weekly_Trend'] = 0  # Default to neutral if weekly data unavailable

        self.df['Signal'] = 0
        
        # Core Strategy Logic
        
        # 1. Golden Cross (Requires MA_50 and MA_200)
        if 'MA_50' in self.df.columns and 'MA_200' in self.df.columns:
            # Check if columns are essentially empty/None
            if self.df['MA_50'].isnull().all() or self.df['MA_200'].isnull().all():
                 gc = False
            else:
                gc = (self.df['MA_50'] > self.df['MA_200']) & (self.df['MA_50'].shift(1) <= self.df['MA_200'].shift(1))
        else:
            gc = False
        
        # 2. RSI Reversal (Requires RSI)
        if 'RSI' in self.df.columns and not self.df['RSI'].isnull().all():
            rsi_rev = (self.df['RSI'] > 30) & (self.df['RSI'].shift(1) <= 30)
        else:
            rsi_rev = False
        
        # 3. Volatility Breakout (Close > Upper Band)
        # Handle case where BBands were not calculated
        bb_cols = [c for c in self.df.columns if 'BBU' in c]
        if bb_cols:
            upper_band_col = bb_cols[0]
            vola_break = self.df['Close'] > self.df[upper_band_col]
        else:
            vola_break = False

        # Combine: Only Buy if Weekly Trend is UP (1) AND (Strategy Trigger)
        if 'Weekly_Trend' in self.df.columns:
            trend_filter = self.df['Weekly_Trend'] == 1
        else:
            trend_filter = False

        # --- 4. Volume Surge Filter (The "Fuel") ---
        # Condition: Volume > 1.5 * 20-day Average Volume
        vol_ma = self.df['Volume'].rolling(window=20).mean()
        # Handle 0/NaN volume
        vol_ma = vol_ma.replace(0, 1) 
        
        # Surge: Current Volume > 1.5x Avg OR 2x Previous
        vol_surge = (self.df['Volume'] > (vol_ma * 1.5)) | (self.df['Volume'] > (self.df['Volume'].shift(1) * 2.0))
        
        # --- 5. Market Regime Filter (The "Weather") ---
        # We need to check if the broad market is safe.
        # Ideally this is passed in, but we can do a quick check here or assume specific market.
        # For efficiency in backtest loop, we might skip this or simulate it.
        # But for "Today's Signal", we check it live.
        # We will add a column 'Regime_Safe' initialized to 1 (True) and update it if possible.
        # note: checking regime for every row in backtest is expensive if fetching external data.
        # For this implementation, we will apply Regime Filter only to the LATEST signal (Live Trading).
        # Backtest will assume regime was neutral/positive or rely on stock's own beta.
        
        # --- Phase 2: Signal Generation Overhaul (Precision Swing) ---
        # Helper to ensure Series
        def to_series(obj):
            if isinstance(obj, pd.DataFrame): return obj.iloc[:, 0]
            return obj

        close_p = to_series(self.df['Close'])
        open_p = to_series(self.df['Open'])
        high_p = to_series(self.df['High'])
        low_p = to_series(self.df['Low'])
        volume = to_series(self.df['Volume'])
        ma10 = pd.to_numeric(to_series(self.df['MA_10'] if 'MA_10' in self.df.columns else self.df['MA_20']), errors='coerce').fillna(0)
        ma20 = pd.to_numeric(to_series(self.df['MA_20']), errors='coerce').fillna(0)
        ma50 = pd.to_numeric(to_series(self.df['MA_50']), errors='coerce').fillna(0)
        rsi_val = pd.to_numeric(to_series(self.df['RSI']), errors='coerce').fillna(50)
        
        # 1. Volatility Breakout & Momentum (Scalping / Short-Swing)
        # Relaxed: Volume > 1.2x Average, Green candle, closing above MA20, RSI > 50
        momentum_breakout = (volume > vol_ma * 1.2) & (close_p > open_p) & (close_p > ma20) & (rsi_val > 50)
            
        # 2. Standard MA20 Pullback (Normal Swing)
        # Price dips near MA20 but holds.
        near_ma20 = (low_p <= ma20 * 1.03) & (close_p >= ma20 * 0.97)
        trend_up = ma20 > ma50
        pullback_swing = near_ma20 & trend_up & (close_p > open_p)
        
        # 3. Trend Reversal / Moving Average Cross (Swing)
        # Price crosses above MA20 with decent RSI
        price_cross_ma20 = (close_p > ma20) & (close_p.shift(1) <= ma20.shift(1))
        trend_reversal = price_cross_ma20 & (rsi_val > 40) & (close_p > open_p)
        
        # 4. Oversold Bounce (Dead Cat / Panic Sell reversal)
        # Relaxed RSI < 40, lower wick > body
        body = (close_p - open_p).abs()
        lower_wick = pd.concat([open_p, close_p], axis=1).min(axis=1) - low_p
        hammer_candle = (lower_wick > body * 1.0) & (close_p > open_p)
        oversold_bounce = (rsi_val < 40) & hammer_candle
        
        # Combine Signals
        precision_signal = momentum_breakout | pullback_swing | trend_reversal | oversold_bounce
        
        # We still prefer some trend filter unless it's an oversold bounce or a breakout
        filtered_signal = precision_signal & (trend_filter | oversold_bounce | momentum_breakout)

        self.df['Signal'] = np.where(filtered_signal, 1, 0)
        
        # [BUG-1 FIX] Alpha_Score is now solely managed by calculate_tech_score() (Tech_Score_V30)
        # Do NOT overwrite here — the previous code was clobbering the more sophisticated Tech_Score_V30


    def calculate_kelly_fraction(self, win_rate, win_loss_ratio):
        """
        Dynamic Kelly with Risk Parity (Volatility Penalty).
        Formula: f* = (p - q/b) * (Target_Vol / Asset_Vol)
        """
        if win_loss_ratio <= 0: return 0
        
        # 1. Basic Kelly
        kelly = win_rate - (1 - win_rate) / win_loss_ratio
        
        if kelly <= 0: return 0
        
        # 2. Volatility Adjustment (Risk Parity Concept)
        # Target Annual Volatility = 20% (Aggressive)
        # We estimate Asset Volatility from ATR or StdDev
        # Simple proxy: (ATR / Price) * sqrt(252) approx annualized vol? 
        # Easier: Use Daily Return StdDev * sqrt(252)
        
        try:
            current_vol = self.df['Close'].pct_change().std() * np.sqrt(252)
            target_vol = 0.20 # 20% Target
            
            vol_scalar = target_vol / current_vol if current_vol > 0 else 1.0
            # Cap scalar at 2.0 (Double leverage max) and min 0.5
            vol_scalar = max(0.2, min(2.0, vol_scalar))
            
            final_f = kelly * vol_scalar
            return final_f
            
        except:
            return kelly

    def backtest(self, initial_capital=10000):
        """Event-Driven Backtest with ATR Stop Loss, Loop & Advanced Metrics"""
        if self.df is None: return None

        capital = initial_capital
        position = 0 # 0 or 1 (holding)
        entry_price = 0.0
        entry_idx = 0
        stop_loss = 0.0
        
        trades = [] # List of {'return': pct, 'win': bool, 'duration': days}
        equity_curve = [initial_capital] # Track daily capital for MDD calculation (simplified: only updates on trade exit for now, or we can track daily)
        dates = [self.df.index[0]]

        # Iterate strictly (skip first 200 for MA calc)
        for i in range(200, len(self.df) - 1):
            today = self.df.iloc[i]
            tomorrow = self.df.iloc[i+1] # Used for T+1 Open execution
            
            # Update Equity Curve (Mark-to-Market would be better, but Trade-based for speed)
            # For accurate MDD, we should track daily value, but let's stick to trade-based for the metrics first
            
            # EXIT LOGIC
            if position == 1:
                did_sell = False
                exit_price = 0.0
                
                # Check Stop Loss with Low of Today
                if today['Low'] < stop_loss:
                    exit_price = float(stop_loss)
                    if today['Open'] < stop_loss: exit_price = today['Open']
                    did_sell = True
                
                # Time-based Exit (2 Days Hold - Precision Strategy)
                elif (i - entry_idx) >= 2:
                    exit_price = float(today['Close'])
                    did_sell = True
                
                if did_sell:
                    if float(entry_price) > 0:
                        pct_change = (float(exit_price) - float(entry_price)) / float(entry_price)
                        
                        if getattr(self, 'is_advanced_engine', False):
                            # Advanced Frictions (Slippage + Tax) Integration
                            is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ') or str(self.ticker).isdigit()
                            friction = 0.0041 if is_kr else 0.0015
                            pct_change -= friction
                            
                        capital = capital * (1 + pct_change)
                        
                        duration = (self.df.index[i] - self.df.index[entry_idx]).days
                        trades.append({'return': float(pct_change), 'duration': int(duration), 'date': self.df.index[i]})
                    
                    equity_curve.append(capital)
                    dates.append(self.df.index[i])
                    
                    position = 0
                    continue

            # ENTRY LOGIC
            if position == 0 and today['Signal'] == 1:
                if getattr(self, 'is_advanced_engine', False):
                    # T+1 Open Execution Realism (Advanced)
                    entry_price = float(tomorrow['Open'])
                    if entry_price <= 0:
                        entry_price = float(today['Close']) # Fallback
                else:
                    # T+0 Close Execution (Legacy Illusion)
                    entry_price = float(today['Close'])
                    
                if entry_price > 0:
                    entry_idx = i + 1 if getattr(self, 'is_advanced_engine', False) else i
                    atr = float(today['ATR']) # Risk determined based on today's close ATR
                    stop_loss = entry_price - (2.0 * atr)
                    position = 1

        if position == 1 and float(entry_price) > 0:
            # Mark to market at last close
            exit_price = float(self.df['Close'].iloc[-1])
            pct_change = (exit_price - float(entry_price)) / float(entry_price)
            if getattr(self, 'is_advanced_engine', False):
                is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ') or str(self.ticker).isdigit()
                pct_change -= (0.0041 if is_kr else 0.0015)
            capital = capital * (1 + pct_change)
            trades.append({'return': float(pct_change), 'duration': int((self.df.index[-1] - self.df.index[entry_idx]).days), 'date': self.df.index[-1]})
            equity_curve.append(capital)
            dates.append(self.df.index[-1])

        # --- Calculate Metrics ---
        if not trades:
            return {"Win Rate": "0%", "Total Return": "0%", "Kelly Suggested": "0%", "Profit Factor": "0.00"}

        df_trades = pd.DataFrame(trades)
        
        # --- Advanced Analytics: Recency & Small Sample Bias ---
        if getattr(self, 'is_advanced_engine', False):
            # 1. Time-Decay Weighting (Old trades count less towards Profit Factor)
            last_date = self.df.index[-1]
            df_trades['days_ago'] = (last_date - df_trades['date']).dt.days
            # Weight = 1.0 (recent), decaying to 0.3 (> 6 months ago)
            df_trades['weight'] = np.where(df_trades['days_ago'] > 180, 0.3, 1.0)
            df_trades['weighted_return'] = df_trades['return'] * df_trades['weight']
            
            # 2. Small Sample Bias Elimination
            trade_count = len(df_trades)
            if trade_count < 3:
                # Force failure of strict filters
                df_trades['weighted_return'] = df_trades['weighted_return'] / 4.0 
        else:
            df_trades['weighted_return'] = df_trades['return']
            trade_count = len(df_trades)
            
        wins = df_trades[df_trades['return'] > 0]
        losses = df_trades[df_trades['return'] <= 0]
        
        # [Phase 15.5 / 17.5 BUG-FIX] Statistical Small Sample Shrinkage
        # We integrate the Agresti-Coull bound and Bayesian smoothing into one solid logical block 
        # to prevent overwriting the safe win_rate.
        raw_win_rate = len(wins) / len(df_trades)
        
        if getattr(self, 'is_advanced_engine', False):
            if trade_count < 3:
                # Agresti-Coull bound simulation (1 win / 1 trade != 100% confidence)
                win_rate = min(0.35, raw_win_rate)
            elif trade_count < 10:
                # Bayesian Smoothing: Shrink towards a prior mean of 40% win rate
                # Formula: (Wins + Prior_Wins) / (Total_Trades + Prior_Trades). Prior = 2 wins / 5 trades
                win_rate = (len(wins) + 2.0) / (len(df_trades) + 5.0)
            else:
                win_rate = raw_win_rate
        else:
            win_rate = raw_win_rate
            
        avg_win = wins['return'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['return'].mean()) if len(losses) > 0 else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss != 0 else 0
            
        kelly = self.calculate_kelly_fraction(win_rate, win_loss_ratio)
        final_return = (capital - initial_capital) / initial_capital
        
        # Profit Factor using weighted returns to suppress archaic 1-hit-wonder trades
        gross_profit = df_trades[df_trades['weighted_return'] > 0]['weighted_return'].sum()
        gross_loss = abs(df_trades[df_trades['weighted_return'] <= 0]['weighted_return'].sum())
        
        if gross_loss != 0:
            profit_factor = gross_profit / gross_loss
        else:
            # If no losses, heavily discount the 99.9 arbitrary score based on sample size
            profit_factor = 99.9 if trade_count >= 5 else (1.5 if trade_count >= 3 else 0.8)
        
        # MDD (Max Drawdown) - calculated from Equity Curve
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio (Simplified: Ann. Return / Ann. Volatility of Returns)
        # Using trade returns series for estimation (not perfect but valid proxy for event-driven)
        returns_std = df_trades['return'].std()
        if returns_std == 0 or np.isnan(returns_std):
            sharpe = 0
        else:
            # Assume ~252 trading days, but we have N trades. 
            # Simplified Sharpe = Mean Trade Return / Std Trade Return * sqrt(Trades per Year)
            # Let's stick to a simpler "Risk Reward" metric or basic annualised Sharpe if possible.
            # Using basic sharpe: Mean(R) / Std(R)
            sharpe = (df_trades['return'].mean() / returns_std) if returns_std != 0 else 0
        
        # Avg Duration
        avg_duration = df_trades['duration'].mean()

        return {
            "Total Return": f"{final_return:.2%}",
            "Win Rate": f"{win_rate:.2%}",
            "Win/Loss Ratio": f"{win_loss_ratio:.2f}",
            "Kelly Allocation": f"{kelly:.2%}",
            "Final Capital": f"${capital:,.2f}",
            "Total Trades": len(trades),
            "MDD": f"{max_drawdown:.2%}",
            "Profit Factor": f"{profit_factor:.2f}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Avg Duration": f"{avg_duration:.1f} Days",
            "Equity Curve": equity_series.tolist() # Pass data for plotting
        }
        
    def get_fibonacci_levels(self):
        """
        Calculate Fibonacci Retracement Levels based on recent Swing High/Low (60 days).
        Returns: Dict { '0.0': low, '0.382': price, '0.5': price, '0.618': price, '1.0': high }
        """
        if self.df is None or len(self.df) < 60: return {}
        
        try:
            recent = self.df.tail(60)
            high = recent['High'].max()
            low = recent['Low'].min()
            diff = high - low
            
            return {
                "0.0": low,
                "0.236": low + diff * 0.236,
                "0.382": low + diff * 0.382,
                "0.5": low + diff * 0.5,
                "0.618": low + diff * 0.618,
                "0.786": low + diff * 0.786,
                "1.0": high
            }
        except: return {}

    def get_pivot_points(self):
        """
        Calculate Standard Pivot Points (Floor Trader Pivots).
        Returns: Dict { 'P': val, 'R1': val, 'S1': val, ... }
        """
        if self.df is None or self.df.empty: return {}
        
        try:
            last = self.df.iloc[-1]
            high = last['High']
            low = last['Low']
            close = last['Close']
            
            p = (high + low + close) / 3
            r1 = (2 * p) - low
            s1 = (2 * p) - high
            r2 = p + (high - low)
            s2 = p - (high - low)
            
            return { 'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2 }
        except: return {}

    def get_trade_setup(self):
        """
        Calculate Actionable Trade Setup values based on technicals.
        Advanced Logic: 
        - Entry: Pullback to MA20 or Support if extended. Breakout if consolidated.
        - SL: ATR-based Dynamic Stop (Support - 1.5 ATR)
        - Target: Dynamic Risk Reward (2.0+) based on volatility
        """
        if self.df is None or self.df.empty: return {}
        
        try:
            latest = self.df.iloc[-1]
            close = float(latest['Close'])
            atr = float(latest['ATR'])
            rsi = float(latest['RSI'])
            ma20 = float(latest['MA_20'])
            
            # Identify columns for BB (pandas-ta names: BBL_20_2.0, BBU_20_2.0)
            bbl_col = [c for c in self.df.columns if 'BBL' in c][0]
            bbu_col = [c for c in self.df.columns if 'BBU' in c][0]
            lower_band = latest[bbl_col]
            upper_band = latest[bbu_col]
            
            # --- Phase 5: Advanced Confluence Logic ---
            fibs = self.get_fibonacci_levels()
            pivots = self.get_pivot_points()
            
            # 1. Base Entry (MA20 or Lower Band)
            base_entry = ma20 if close > ma20 else lower_band
            
            # 2. Find Confluence (Overlap of Fib/Pivot/MA)
            # We look for a price zone where multiple levels exist within 1% buffer
            candidates = [ma20, lower_band]
            if fibs: candidates.extend([fibs.get('0.5'), fibs.get('0.618'), fibs.get('0.382')])
            if pivots: candidates.extend([pivots.get('S1'), pivots.get('S2'), pivots.get('P')])
            candidates = [c for c in candidates if c is not None and c < close] # Only support levels below price
            
            # Cluster Algorithm: Find densest cluster
            best_cluster_price = base_entry
            max_cluster_score = 0
            
            for c in candidates:
                # Count neighbors within 1.5%
                neighbors = [x for x in candidates if abs(x - c) / c < 0.015]
                score = len(neighbors)
                if score > max_cluster_score:
                    max_cluster_score = score
                    # Average of cluster
                    best_cluster_price = sum(neighbors) / len(neighbors)
            
            # --- [Phase 2] Volume Confirmation ---
            vol_current = self.df['Volume'].iloc[-1]
            vol_avg_20 = self.df['Volume'].rolling(20).mean().iloc[-1]
            vol_avg_5  = self.df['Volume'].rolling(5, min_periods=2).mean().iloc[-1]

            # If current volume is 0 (pre-market or data glitch) and we have enough data, use yesterday's
            if vol_current == 0 and len(self.df) >= 2:
                vol_current = self.df['Volume'].iloc[-2]
                vol_avg_20 = self.df['Volume'].rolling(20).mean().iloc[-2]
                vol_avg_5  = self.df['Volume'].rolling(5, min_periods=2).mean().iloc[-2]

            # --- Intraday Volume Projection ---
            # NOTE: Volume is already projected natively in fetch_data() Phase 10 update.
            vol_current_projected = vol_current

            # 20일 평균 대비 비율 (전체 맥락)
            _val20 = vol_avg_20 if pd.notna(vol_avg_20) and vol_avg_20 > 0 else 1.0
            vol_ratio = vol_current_projected / _val20
            # 5일 평균 대비 비율 (최근 장세 반영)
            _val5 = vol_avg_5 if pd.notna(vol_avg_5) and vol_avg_5 > 0 else _val20
            vol_ratio_5d = vol_current_projected / _val5
            # 거래량 확인: 20일 평균 대비 50% 이상 (최소 유동성 체크)
            # vol_ratio >= 1.2는 "평균 이상 거래량" 신호이지만,
            # 관세 쇼크 이후처럼 최근 고거래량이 평균을 끌어올린 경우 모든 종목이 미달되므로
            # 최소 유동성(0.5x) 기준으로 변경 — 강한 거래량 신호는 vol_ratio 수치로 판단
            volume_confirmed = vol_ratio >= 0.5 or vol_ratio_5d >= 0.8
            
            # --- [Phase 3] ATR-Based Dynamic Stop/Target (WFO V2 최적) ---
            # ATR(14) = Average True Range over 14 days
            high = self.df['High']
            low = self.df['Low']
            prev_close = self.df['Close'].shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs()
            ], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean().iloc[-1]
            
            # WFO 최적 파라미터 로드 (없으면 기본값 사용)
            _atrs = 2.0  # WFO optimal (기존 1.5)
            _atrt = 2.0  # WFO optimal (기존 2.5)
            try:
                import json, os
                _params_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'optimal_params.json')
                if os.path.exists(_params_path):
                    with open(_params_path) as _f:
                        _p = json.load(_f)
                        _atrs = _p.get('ATR_stop_mult', 2.0)
                        _atrt = _p.get('ATR_target_mult', 2.0)
            except Exception:
                pass
            
            # Entry: -2% from current (dip buy)
            entry_price = close * 0.98
            
            # Dynamic Stop/Target using ATR (WFO optimized)
            # Stop: Entry - ATR × 2.0 (minimum -2%, maximum -5%)
            atr_stop_pct = min(max((atr_14 * _atrs / entry_price) * 100, 2.0), 5.0)
            stop_loss_price = entry_price * (1 - atr_stop_pct / 100)
            
            # Target: Entry + ATR × 2.0 (minimum +2%, maximum +8%)
            atr_target_pct = min(max((atr_14 * _atrt / entry_price) * 100, 2.0), 8.0)
            target_price = entry_price * (1 + atr_target_pct / 100)
            
            # Entry Zone
            entry_min = entry_price * 0.99
            entry_max = entry_price * 1.01

            # Recalculate RR (Risk/Reward)
            reward = target_price - entry_price
            risk = entry_price - stop_loss_price
            rr_ratio = reward / risk if risk > 0 else 0
            
            return {
                "Entry Price": entry_price,
                "Entry Min": entry_min,
                "Entry Max": entry_max,
                "Stop Loss": stop_loss_price,
                "Target Price": target_price,
                "Risk/Reward": f"1:{rr_ratio:.1f}",
                "Confluence Score": max_cluster_score,
                # [Phase D] Exit Strategy Metadata
                "Max Hold Days": 3,
                "Trailing Stop": f"+{atr_target_pct/2:.1f}%에서 손절 → 진입가 이동",
                "Exit Plan": "50% at 목표가, 나머지 Trailing",
                # [Phase 2] Volume info
                "Volume Confirmed": volume_confirmed,
                "Volume Ratio": round(vol_ratio, 1),
                # [Phase 3] ATR info
                "ATR Stop %": f"-{atr_stop_pct:.1f}%",
                "ATR Target %": f"+{atr_target_pct:.1f}%",
            }
            
        except Exception as e:
            print(f"Setup Error: {e}")
            c = self.df['Close'].iloc[-1]
            try:
                vol_recent = float(self.df['Volume'].tail(5).mean())
                vol_baseline = float(self.df['Volume'].tail(20).mean())
                vol_ratio_fallback = round(vol_recent / vol_baseline, 1) if vol_baseline > 0 else None
            except Exception:
                vol_ratio_fallback = None
            return {
                "Entry Price": c,
                "Entry Min": c,
                "Entry Max": c,
                "Stop Loss": c * 0.95,
                "Target Price": c * 1.1,
                "Risk/Reward": "1:2.0",
                "Volume Ratio": vol_ratio_fallback,
                "Volume Confirmed": False,
            }


    def get_latest_metrics(self):
        """Return latest indicators for display"""
        if self.df is None:
            return {}
            
        latest = self.df.iloc[-1]
        return {
            "Close": latest['Close'],
            "RSI": latest['RSI'],
            "ATR": latest['ATR'],
            "Weekly Trend": "UP" if latest.get('Weekly_Trend', 0) == 1 else "DOWN"
        }

    # --- Phase 6: Sensible ML (Supervised + Unsupervised) ---
    
    def train_ml_model(self):
        """
        Train a Random Forest Classifier to predict specific Directionality.
        Also uses KMeans to cluster Market Regimes.
        """
        if not HAS_ML or self.df is None or len(self.df) < 100:
            return {"accuracy": 0, "model": None, "cluster": None}
            
        try:
            # 1. Feature Engineering
            data = self.df.copy()
            macro = self._fetch_global_macro_data()
            
            # Merge Macro if available
            if macro is not None:
                # Align indices
                data = data.join(macro, how='left').fillna(method='ffill')
            
            # Create Features (X)
            data['Returns'] = data['Close'].pct_change()
            data['Vol_Rel'] = data['Volume'] / data['Volume'].rolling(20).mean()
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['ATR_Rel'] = ta.atr(data['High'], data['Low'], data['Close'], length=14) / data['Close']
            
            # --- FEATURE ENGINEERING UPGRADE (Phase 7) ---
            # Add Lagged Returns to capture Momentum/Mean Reversion
            data['Return_Lag1'] = data['Returns'].shift(1)
            data['Return_Lag2'] = data['Returns'].shift(2)
            data['RSI_Lag1'] = data['RSI'].shift(1)
            
            # Drop NaN
            data = data.dropna()
            
            # Create Target (Y): Next Day Return > 0
            data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
            
            # Select Features
            features = ['RSI', 'Vol_Rel', 'ATR_Rel', 'Returns', 'Return_Lag1', 'Return_Lag2', 'RSI_Lag1']
            if macro is not None:
                # Add macro features if they exist in columns
                for c in ['^VIX', '^TNX', 'KRW=X']:
                    if c in data.columns: features.append(c)
            
            X = data[features].iloc[:-1] # Drop last row (no target)
            y = data['Target'].iloc[:-1]
            
            # 2. Train Random Forest (Tuned)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
            
            # Increased estimators and depth for better pattern recognition
            rf = RandomForestClassifier(n_estimators=200, max_depth=7, min_samples_leaf=4, random_state=42)
            rf.fit(X_train, y_train)
            
            acc = accuracy_score(y_test, rf.predict(X_test))
            
            # 3. Unsupervised: Regime Clustering (KMeans)
            # Use Volatility and Returns to define regime
            X_cluster = data[['Returns', 'ATR_Rel']].copy()
            kmeans = KMeans(n_clusters=3, random_state=42)
            kmeans.fit(X_cluster)
            
            print(f"ML Trained: Acc {acc:.2f}")
            
            return {
                "accuracy": acc,
                "model": rf,
                "features": features,
                "kmeans": kmeans,
                "latest_data": data.iloc[-1] # For prediction
            }
            
        except Exception as e:
            # print(f"ML Training Error: {e}") # Silent fail for individual model
            return {"accuracy": 0, "model": None}

    def train_universal_model(self):
        """
        Phase 34: Train Universal AI Model (Zero-Failure)
        Trains a robust Random Forest on Market Indices (KOSPI, S&P500) + Top Tech.
        Saves to 'models/universal_rf.pkl'.
        """
        model_path = "models/universal_rf.pkl"
        
        # Create models dir if not exists
        if not os.path.exists("models"):
            os.makedirs("models")
            
        try:
            print("🧠 Training Universal AI Model (Global Brain)...")
            # 1. Fetch Representative Data (5 Years)
            tickers = ['^KS11', '^GSPC', '005930.KS', 'AAPL'] # KOSPI, S&P, Samsung, Apple
            big_data = []
            
            for t in tickers:
                try:
                    t_obj = yf.Ticker(t)
                    df = t_obj.history(period='5y')
                    if len(df) > 200:
                        if df.index.tz is not None:
                            df.index = df.index.tz_localize(None)
                        
                        # Feature Engineering
                        df['Returns'] = df['Close'].pct_change()
                        df['Vol_Rel'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)
                        
                        rsi = ta.rsi(df['Close'], length=14)
                        if rsi is None: continue
                        df['RSI'] = rsi
                        
                        atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
                        if atr is None: continue
                        df['ATR_Rel'] = atr / df['Close']
                        
                        # Lagged Features
                        df['Return_Lag1'] = df['Returns'].shift(1)
                        df['Return_Lag2'] = df['Returns'].shift(2)
                        df['RSI_Lag1'] = df['RSI'].shift(1)
                        
                        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
                        
                        df = df.dropna()
                        if len(df) > 100:
                            big_data.append(df)
                except: continue
                
            if not big_data: return None
            
            # Combine all data
            full_df = pd.concat(big_data)
            
            # 2. Train Model
            features = ['RSI', 'Vol_Rel', 'ATR_Rel', 'Returns', 'Return_Lag1', 'Return_Lag2', 'RSI_Lag1']
            # Note: We exclude macro here to keep it universal and simple (self-contained)
            
            X = full_df[features]
            y = full_df['Target']
            
            # Balanced Class Weight to handle market drift
            rf = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=5, random_state=42, class_weight="balanced")
            rf.fit(X, y)
            
            # Save
            joblib.dump(rf, model_path)
            print(f"✅ Universal Model Saved: {model_path} (Samples: {len(X)})")
            return rf
            
        except Exception as e:
            print(f"Universal Training Failed: {e}")
            return None

    def get_ml_prediction(self):
        """
        Phase 18.2: Regime-Aware & Trade Quality Prediction
        Routes to BULL/BEAR models dynamically based on Market_Mom_20.
        """
        if self.df is None or len(self.df) < 50:
            return {
                "prob": 50,
                "raw_prob": 50,
                "clean_prob": 50,
                "signal": "NEUTRAL",
                "regime": "Data Error",
                "accuracy": 0,
                "type": "Fail",
                "model_trace_status": "data_short",
                "inference_failed": True,
            }
        
        try:
            import os
            import sys
            import joblib

            def _safe_prob(value, default=50.0):
                try:
                    val = float(value)
                    if np.isnan(val) or np.isinf(val):
                        return float(default)
                    return max(0.0, min(100.0, val))
                except Exception:
                    return float(default)

            def _compute_universal_prob(models_dir: str):
                """Fallback when scan-specific models are missing."""
                try:
                    model_path = os.path.join(models_dir, "universal_rf.pkl")
                    if not os.path.exists(model_path):
                        return None

                    model = joblib.load(model_path)
                    close = self.df["Close"].astype(float)
                    volume = self.df["Volume"].astype(float)
                    if len(close) < 20 or len(volume) < 20:
                        return None

                    returns = close.pct_change()
                    vol_ma20 = float(volume.rolling(20).mean().iloc[-1])
                    vol_rel = float(volume.iloc[-1]) / max(vol_ma20, 1e-9)

                    if "RSI" in self.df.columns:
                        rsi_series = self.df["RSI"].astype(float)
                    else:
                        rsi_series = ta.rsi(close, length=14)
                    if rsi_series is None or len(rsi_series.dropna()) < 2:
                        return None

                    if "ATR" in self.df.columns:
                        atr_series = self.df["ATR"].astype(float)
                    else:
                        atr_series = ta.atr(self.df["High"], self.df["Low"], self.df["Close"], length=14)
                    atr_series = pd.Series(atr_series)
                    if atr_series.dropna().empty:
                        return None

                    latest_close = float(close.iloc[-1])
                    feature_row = pd.DataFrame(
                        [[
                            float(rsi_series.iloc[-1]),
                            float(vol_rel),
                            float(atr_series.iloc[-1]) / max(latest_close, 1e-9),
                            float(returns.iloc[-1] or 0.0),
                            float(returns.shift(1).iloc[-1] or 0.0),
                            float(returns.shift(2).iloc[-1] or 0.0),
                            float(rsi_series.shift(1).iloc[-1] or rsi_series.iloc[-1]),
                        ]],
                        columns=['RSI', 'Vol_Rel', 'ATR_Rel', 'Returns', 'Return_Lag1', 'Return_Lag2', 'RSI_Lag1'],
                    ).fillna(0.0)

                    prob = float(model.predict_proba(feature_row)[0][1] * 100)
                    return round(50.0 + ((prob - 50.0) * 0.7), 1)
                except Exception:
                    return None
            
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if base_dir not in sys.path: sys.path.insert(0, base_dir)
            from train_ml_targets import _build_features_v5, FEATURES_V5
            
            global _GLOBAL_MACRO_CACHE
            if _GLOBAL_MACRO_CACHE is None:
                from train_ml_targets import _fetch_cross_asset_data
                _GLOBAL_MACRO_CACHE = _fetch_cross_asset_data()
                
            df_features = _build_features_v5(self.df.copy(), _GLOBAL_MACRO_CACHE)
            if df_features is None or df_features.empty:
                return {
                    "prob": 50,
                    "raw_prob": 50,
                    "clean_prob": 50,
                    "signal": "NEUTRAL",
                    "regime": "Data Error",
                    "accuracy": 0,
                    "type": "Fail",
                    "model_trace_status": "feature_build_fail",
                    "inference_failed": True,
                }
                
            X_new = df_features[FEATURES_V5 + ['Spy_Rel_Strength']].iloc[[-1]].fillna(0)
            X_old = df_features[FEATURES_V5].iloc[[-1]].fillna(0)
            
            # Sub-Regime Router
            current_market_mom = df_features['Market_Mom_20'].iloc[-1]
            suffix = "bull" if current_market_mom > 0 else "bear"
            
            models_dir = os.path.join(base_dir, 'models')
            res = {}
            universal_prob = _compute_universal_prob(models_dir)
            phase25_trace_status = None
            phase25_error = None
            phase25_degraded = False
            
            # --- Phase 18.2 New Models ---
            # Filter features per model's training schema; FEATURES_V5 has since
            # grown (KR macro additions) and legacy models were fit on fewer cols.
            def _align_features(clf_obj):
                raw = getattr(clf_obj, 'feature_names_in_', None)
                expected = list(raw) if raw is not None else []
                if not expected:
                    expected = FEATURES_V5 + ['Spy_Rel_Strength']
                return df_features.reindex(columns=expected, fill_value=0).iloc[[-1]].fillna(0)

            model_5_path = os.path.join(models_dir, f'model_5pct_{suffix}.pkl')
            if os.path.exists(model_5_path):
                clf_5 = joblib.load(model_5_path)
                X_5 = _align_features(clf_5)
                res['5pct'] = float(round(clf_5.predict_proba(X_5)[0][1] * 100, 1))
            else:
                res['5pct'] = None

            model_clean_path = os.path.join(models_dir, f'model_5pct_clean_{suffix}.pkl')
            if os.path.exists(model_clean_path):
                clf_clean = joblib.load(model_clean_path)
                X_clean = _align_features(clf_clean)
                res['5pct_clean'] = float(round(clf_clean.predict_proba(X_clean)[0][1] * 100, 1))
            else:
                res['5pct_clean'] = None
                
            # --- Phase 25 Model Overlay ---
            # KR swing follows the latest benchmark order. Do not force a boost
            # family model when the holdout evidence currently favors logistic.
            try:
                phase25_load_errors = []

                def _transform_with_optional_scaler(df_in, scaler_obj):
                    if scaler_obj is None:
                        return df_in.to_numpy(dtype=float)
                    return scaler_obj.transform(df_in)

                def _load_bundle(path_candidates):
                    for cand in path_candidates:
                        if os.path.exists(cand):
                            try:
                                return cand, joblib.load(cand)
                            except Exception as exc:
                                phase25_load_errors.append(f"{os.path.basename(cand)}:{type(exc).__name__}:{exc}")
                                continue
                    return None, None

                scan_mode = str(getattr(self, "scan_mode", "SWING") or "SWING").strip().upper()
                is_kr = str(self.ticker).endswith(".KS") or str(self.ticker).endswith(".KQ") or str(self.ticker).isdigit()
                _is_kospi_ticker = str(self.ticker).endswith(".KS")
                _is_kosdaq_ticker = str(self.ticker).endswith(".KQ") or (is_kr and not _is_kospi_ticker)
                _market_tag = "kospi" if _is_kospi_ticker else ("kosdaq" if _is_kosdaq_ticker else None)
                primary_candidates = []
                shadow_candidates = []
                # 2026-05-08 (swing-main-01i/sl3): segment swing models were
                # weak/inverted. The unified KR swing benchmark remains primary,
                # but the current 5D holdout ranks logistic first by avg return.
                if is_kr and scan_mode == "SWING":
                    primary_candidates = [
                        os.path.join(models_dir, "phase25_kr_swing_logistic.pkl"),
                        os.path.join(models_dir, "phase25_kr_swing_lightgbm.pkl"),
                        os.path.join(models_dir, "phase25_kr_swing_xgboost.pkl"),
                        os.path.join(models_dir, "phase25_kr_swing_histgb.pkl"),
                        os.path.join(models_dir, "phase25_kr_swing.pkl"),
                        os.path.join(models_dir, "phase25_model.pkl"),
                    ]
                    # 단일 segment(_market_tag) 모델은 quintile 분석상 무용/inverted라
                    # primary 후보에서 제외. 통합 모델 4종 모두 부재 시에만 마지막
                    # fallback으로 시도.
                    if _market_tag:
                        primary_candidates.append(os.path.join(models_dir, f"phase25_{_market_tag}_swing.pkl"))
                    shadow_candidates = [
                        os.path.join(models_dir, "phase25_kr_swing_xgboost.pkl"),
                        os.path.join(models_dir, "phase25_kr_swing_histgb.pkl"),
                    ]
                elif is_kr and scan_mode == "INTRADAY":
                    # 2026-05-08: dedup 후 boost 계열 모두 auc<0.5 (random 미만).
                    # logistic만 auc 0.525로 양수. logistic을 boost 다음 fallback에 둔다.
                    primary_candidates = [
                        os.path.join(models_dir, "phase25_kr_intraday_xgboost.pkl"),
                        os.path.join(models_dir, "phase25_kr_intraday_histgb.pkl"),
                        os.path.join(models_dir, "phase25_kr_intraday_lightgbm.pkl"),
                        os.path.join(models_dir, "phase25_kr_intraday_logistic.pkl"),
                        os.path.join(models_dir, "phase25_kr_intraday.pkl"),
                        os.path.join(models_dir, "phase25_model.pkl"),
                    ]
                    if _market_tag:
                        primary_candidates.append(os.path.join(models_dir, f"phase25_{_market_tag}_intraday.pkl"))
                    shadow_candidates = [
                        os.path.join(models_dir, "phase25_kr_intraday_histgb.pkl"),
                        os.path.join(models_dir, "phase25_kr_intraday_lightgbm.pkl"),
                    ]
                else:
                    primary_candidates = [os.path.join(models_dir, "phase25_model.pkl")]

                p25_path, p25_bundle = _load_bundle(primary_candidates)
                shadow_path, shadow_bundle = _load_bundle([p for p in shadow_candidates if p != p25_path])

                if p25_bundle is not None:
                    p25_model = p25_bundle["model"]
                    p25_scaler = p25_bundle.get("scaler")
                    p25_feats = list(p25_bundle.get("features", []))

                    _closes = self.df["Close"].astype(float)
                    _vols = self.df["Volume"].astype(float)
                    _avg_v = float(_vols.rolling(20).mean().iloc[-1]) if pd.notna(_vols.rolling(20).mean().iloc[-1]) else float(_vols.iloc[-1])
                    _vf = float(_vols.iloc[-1]) / max(_avg_v, 1)
                    _trend10 = float(_closes.pct_change(10).iloc[-1] or 0) * 100
                    _mkt_mom = float(df_features["Market_Mom_20"].iloc[-1] or 0.0)

                    _position = str(self.get_price_position() or "")
                    _is_rising = int("Rising" in _position)
                    _is_peak = int("Peak" in _position)
                    _is_resting = int("Resting" in _position)
                    _is_bottom = int("Bottom" in _position)
                    _is_sideways = int(not _is_rising and not _is_peak and not _is_resting and not _is_bottom)

                    _alpha_raw = 50.0
                    try:
                        if "Alpha_Score" in self.df.columns and pd.notna(self.df["Alpha_Score"].iloc[-1]):
                            _alpha_raw = float(self.df["Alpha_Score"].iloc[-1])
                        elif "Antigrav_Score" in self.df.columns and pd.notna(self.df["Antigrav_Score"].iloc[-1]):
                            _alpha_raw = float(self.df["Antigrav_Score"].iloc[-1])
                    except Exception:
                        pass

                    _whale_score = 55.0
                    try:
                        _whale_info = self.get_investor_flows()
                        _whale_score = float(_whale_info.get("whale_score", 55.0) or 55.0)
                    except Exception:
                        pass

                    _is_uptrend = int(
                        ("MA_20" in self.df.columns and pd.notna(self.df["MA_20"].iloc[-1]) and float(_closes.iloc[-1]) >= float(self.df["MA_20"].iloc[-1]))
                        or _trend10 > 0
                    )
                    _is_downtrend = int(not _is_uptrend)
                    _is_overheat = int(_vf >= 2.5 or _trend10 >= 18 or _is_peak)
                    _is_momentum = int(_trend10 > 0 and _is_bottom == 0)

                    # RSI divergence: price higher high but RSI lower high over last 14 bars
                    _is_rsidiv = 0
                    _is_obvdiv = 0
                    try:
                        if len(_closes) >= 14:
                            _rsi_col = None
                            for _c in ("RSI", "RSI_14", "Rsi"):
                                if _c in self.df.columns:
                                    _rsi_col = self.df[_c].astype(float)
                                    break
                            if _rsi_col is None and len(_closes) >= 14:
                                _delta = _closes.diff()
                                _gain = _delta.clip(lower=0).rolling(14).mean()
                                _loss = (-_delta.clip(upper=0)).rolling(14).mean()
                                _rs = _gain / _loss.replace(0, np.nan)
                                _rsi_col = 100 - (100 / (1 + _rs))
                            if _rsi_col is not None and len(_rsi_col.dropna()) >= 10:
                                _w = 10
                                _price_now = float(_closes.iloc[-1])
                                _price_prev = float(_closes.iloc[-1 - _w])
                                _rsi_now = float(_rsi_col.iloc[-1])
                                _rsi_prev = float(_rsi_col.iloc[-1 - _w])
                                if pd.notna(_rsi_now) and pd.notna(_rsi_prev):
                                    _is_rsidiv = int(_price_now > _price_prev and _rsi_now < _rsi_prev)
                    except Exception:
                        pass
                    try:
                        if "OBV" in self.df.columns and len(self.df) >= 14:
                            _obv = self.df["OBV"].astype(float)
                        else:
                            _sign = np.sign(_closes.diff().fillna(0))
                            _obv = (_sign * _vols).cumsum()
                        if len(_obv.dropna()) >= 10:
                            _w = 10
                            _price_now = float(_closes.iloc[-1])
                            _price_prev = float(_closes.iloc[-1 - _w])
                            _obv_now = float(_obv.iloc[-1])
                            _obv_prev = float(_obv.iloc[-1 - _w])
                            if pd.notna(_obv_now) and pd.notna(_obv_prev):
                                _is_obvdiv = int(_price_now > _price_prev and _obv_now < _obv_prev)
                    except Exception:
                        pass

                    _surge = {}
                    try:
                        _surge = self.detect_pre_surge_signals() or {}
                    except Exception:
                        _surge = {}
                    _stype = str(_surge.get("strategy_type", "") or "")
                    _surge_text = json.dumps(_surge, ensure_ascii=False) if _surge else ""
                    _is_contract = int(any(tok in _surge_text for tok in ["공급계약", "계약", "수주"]))
                    _roll20 = _closes.shift(1).rolling(20).max()
                    _is_breakout = int(
                        (len(_closes) > 25 and pd.notna(_roll20.iloc[-1]) and float(_closes.iloc[-1]) >= float(_roll20.iloc[-1]))
                        or _is_rising
                        or ("Breakout" in _stype or "돌파" in _stype or "Continuation" in _stype)
                    )
                    _tier_t0 = int(_alpha_raw >= 90 and _whale_score >= 70 and _is_uptrend)
                    _tier_t1 = int(_alpha_raw >= 75 and _whale_score >= 65 and _is_uptrend and not _tier_t0)
                    _tier_t2 = int(_alpha_raw >= 65 and _whale_score >= 55 and not (_tier_t0 or _tier_t1))
                    _fund_positive = 0
                    try:
                        _fund_positive = int(bool(self.check_fundamentals()[0]))
                    except Exception:
                        pass

                    _entry_reference = float(_closes.iloc[-1])
                    _is_sub7 = int(_entry_reference > 0 and _entry_reference <= 7.0)
                    _price_7_15 = int(_entry_reference > 7.0 and _entry_reference <= 15.0)
                    _price_gt15 = int(_entry_reference > 15.0)

                    # Market cap band (KR only): use shares_outstanding * close price
                    # Bands: 0=<300B, 1=300B~1T, 2=1T~5T, 3=5T~20T, 4=>=20T (KRW)
                    _marcap_band = 2  # default mid
                    try:
                        if is_kr and "Shares" in self.df.columns and pd.notna(self.df["Shares"].iloc[-1]):
                            _shares = float(self.df["Shares"].iloc[-1])
                            _marcap_krw = _shares * _entry_reference
                            if _marcap_krw < 300_000_000_000:
                                _marcap_band = 0
                            elif _marcap_krw < 1_000_000_000_000:
                                _marcap_band = 1
                            elif _marcap_krw < 5_000_000_000_000:
                                _marcap_band = 2
                            elif _marcap_krw < 20_000_000_000_000:
                                _marcap_band = 3
                            else:
                                _marcap_band = 4
                        elif is_kr:
                            # fallback: FDR StockListing has Marcap column
                            try:
                                import FinanceDataReader as _fdr
                                _mkt = "KOSPI" if str(self.ticker).endswith(".KS") else "KOSDAQ"
                                _listing = _fdr.StockListing(_mkt)
                                _bare = str(self.ticker).replace(".KS", "").replace(".KQ", "")
                                _row = _listing[_listing["Code"] == _bare]
                                if not _row.empty and "Marcap" in _row.columns:
                                    _mc_val = float(_row["Marcap"].iloc[0])
                                    if _mc_val < 300_000_000_000:
                                        _marcap_band = 0
                                    elif _mc_val < 1_000_000_000_000:
                                        _marcap_band = 1
                                    elif _mc_val < 5_000_000_000_000:
                                        _marcap_band = 2
                                    elif _mc_val < 20_000_000_000_000:
                                        _marcap_band = 3
                                    else:
                                        _marcap_band = 4
                            except Exception:
                                pass
                    except Exception:
                        pass

                    _is_kospi = int(str(self.ticker).endswith(".KS"))
                    _is_kosdaq = int(str(self.ticker).endswith(".KQ") or (str(self.ticker).isdigit() and not _is_kospi))
                    _strategy_family = str(getattr(self, "strategy_family", "") or ("KR_CORE" if is_kr else "US_MAIN")).upper()
                    _kr_role = str(getattr(self, "kr_universe_role", "") or "").upper()
                    if not _kr_role and is_kr:
                        _kr_role = "CORE_TREND" if _is_kospi else "EXPLOSIVE_LEADER"
                    _base_prob = _safe_prob(res["5pct"] if res["5pct"] is not None else universal_prob, 50.0)
                    _clean_prob = _safe_prob(res["5pct_clean"] if res["5pct_clean"] is not None else _base_prob, _base_prob)

                    _p25_row = {
                        "alpha_score": round(_alpha_raw, 1),
                        # tech_score dropped: duplicate of alpha_score — removed from FEATURE_COLS
                        "ml_prob": round(_base_prob, 1),
                        # whale_score dropped: 0% fill in RESOLVED rows — removed from FEATURE_COLS
                        # decision_score dropped: circular (alpha+ml→decision→ml input) — removed from FEATURE_COLS
                        "vol_float": _vf,
                        "vol_confirmed": int(_vf >= 1.2),
                        "vol_gt25x": int(_vf > 2.5),
                        "vol_18_25x": int(1.8 < _vf <= 2.5),
                        "vol_08_18x": int(0.8 <= _vf <= 1.8),
                        "vol_lt05x": int(_vf < 0.5),
                        "is_rising": _is_rising,
                        "is_peak": _is_peak,
                        "is_resting": _is_resting,
                        "is_bottom": _is_bottom,
                        "is_uptrend": _is_uptrend,
                        "is_downtrend": _is_downtrend,
                        "is_sideways": _is_sideways,
                        "is_overheat": _is_overheat,
                        "is_rsidiv": _is_rsidiv,
                        "is_obvdiv": _is_obvdiv,
                        "is_momentum": _is_momentum,
                        "is_contract": _is_contract,
                        "is_breakout": _is_breakout,
                        "tier_t0": _tier_t0,
                        "tier_t1": _tier_t1,
                        "tier_t2": _tier_t2,
                        "fund_positive": _fund_positive,
                        "is_sub7": _is_sub7,
                        "price_7_15": _price_7_15,
                        "price_gt15": _price_gt15,
                        "is_kospi": _is_kospi,
                        "is_kosdaq": _is_kosdaq,
                        "is_nasdaq": int((not is_kr) and _strategy_family != "AMEX_MOONSHOT"),
                        "is_amex": int(_strategy_family == "AMEX_MOONSHOT"),
                        "scan_intraday": int(scan_mode == "INTRADAY"),
                        "scan_swing": int(scan_mode == "SWING"),
                        "fam_kr_core": int(_strategy_family == "KR_CORE"),
                        "fam_us_main": int(_strategy_family == "US_MAIN"),
                        "fam_amex_moonshot": int(_strategy_family == "AMEX_MOONSHOT"),
                        "peak_x_highvol": int(_is_peak and _vf > 2.5),
                        "overheat_x_uptrend": int(_is_overheat and _is_uptrend),
                        "sub7_x_breakout": int(_is_sub7 and _is_breakout),
                        "marcap_band": _marcap_band,
                        "marcap_micro": int(_marcap_band == 0),
                        "marcap_small": int(_marcap_band == 1),
                        "marcap_mid": int(_marcap_band == 2),
                        "marcap_large": int(_marcap_band == 3),
                        "marcap_mega": int(_marcap_band == 4),
                        "role_core_trend": int(_kr_role == "CORE_TREND"),
                        "role_explosive_leader": int(_kr_role == "EXPLOSIVE_LEADER"),
                        "role_transitional": int(_kr_role == "TRANSITIONAL"),
                        "role_reject_risk": int(_kr_role == "REJECT_RISK"),
                        # Whale supply signals (binary) — for future ML training
                        "whale_high": int(_whale_score >= 60),
                        "whale_very_high": int(_whale_score >= 70),
                        "whale_low": int(_whale_score <= 35),
                        "whale_very_low": int(_whale_score <= 25),
                    }
                    _p25_row.update(
                        compute_low_prob_high_score_features(
                            alpha_score=_alpha_raw,
                            tech_score=_alpha_raw,
                            ml_prob=_base_prob,
                            prob_clean=_clean_prob,
                            phase25_prob=None,
                            expected_edge_score=None,
                        )
                    )
                    _market_subtype = "KOSPI" if _is_kospi else ("KOSDAQ" if _is_kosdaq else "")
                    _p25_row.update(
                        compute_loss_risk_features(
                            market_subtype=_market_subtype,
                            alpha_score=_alpha_raw,
                            tech_score=_alpha_raw,
                            whale_score=_whale_score,
                            ml_prob=_base_prob,
                            prob_clean=_clean_prob,
                            volume_ratio=_vf,
                            volume_confirmed=(_vf >= 1.2),
                            position=_position,
                            tier=("T0" if _tier_t0 else "T1" if _tier_t1 else "T2" if _tier_t2 else ""),
                            trend=("UP" if _is_uptrend else "DOWN"),
                        )
                    )
                    _p25_df = pd.DataFrame([_p25_row])
                    _p25_X = _p25_df.reindex(columns=p25_feats, fill_value=0).fillna(0)
                    _p25_prob_raw = float(p25_model.predict_proba(_transform_with_optional_scaler(_p25_X, p25_scaler))[0][1] * 100)
                    _p25_direction = str(p25_bundle.get("signal_direction", "normal") or "normal").lower()
                    # 'uncertain' = CV median AUC inside 0.45–0.55 gray zone.
                    # Originally we collapsed the contribution to 50 because raw
                    # in-sample AUC is the only signal we trusted. After OHLCV
                    # + index regime features were added, KOSDAQ swing's raw_auc
                    # sits at 0.55 (still 'uncertain') yet OOS reaches win 78%
                    # / return +11.84% on the held-out 15% slice. OOS is the
                    # leakage-free production proxy, so we override 'uncertain'
                    # to 'normal' when OOS shows real edge: oos_auc >= 0.55 AND
                    # oos_win_rate_pct >= 70 AND oos_avg_return_pct >= 5. If
                    # OOS metadata is missing or weak, the original neutralize
                    # behavior stays in place.
                    _oos_auc = p25_bundle.get("oos_auc")
                    _oos_win = p25_bundle.get("oos_win_rate_pct")
                    _oos_ret = p25_bundle.get("oos_avg_return_pct")
                    _oos_validates = (
                        _oos_auc is not None and float(_oos_auc) >= 0.55 and
                        _oos_win is not None and float(_oos_win) >= 70.0 and
                        _oos_ret is not None and float(_oos_ret) >= 5.0
                    )
                    if _p25_direction == "uncertain" and _oos_validates:
                        _p25_direction = "normal"
                    if _p25_direction == "uncertain":
                        _p25_prob = 50.0
                    elif _p25_direction == "invert":
                        _p25_prob = 100.0 - _p25_prob_raw
                    else:
                        _p25_prob = _p25_prob_raw

                    _shadow_prob = None
                    if shadow_bundle is not None:
                        try:
                            _shadow_model = shadow_bundle["model"]
                            _shadow_scaler = shadow_bundle.get("scaler")
                            _shadow_feats = list(shadow_bundle.get("features", []))
                            _shadow_X = _p25_df.reindex(columns=_shadow_feats, fill_value=0).fillna(0)
                            _shadow_prob_raw = float(
                                _shadow_model.predict_proba(_transform_with_optional_scaler(_shadow_X, _shadow_scaler))[0][1] * 100
                            )
                            _shadow_direction = str(shadow_bundle.get("signal_direction", "normal") or "normal").lower()
                            _shadow_oos_auc = shadow_bundle.get("oos_auc")
                            _shadow_oos_win = shadow_bundle.get("oos_win_rate_pct")
                            _shadow_oos_ret = shadow_bundle.get("oos_avg_return_pct")
                            _shadow_oos_validates = (
                                _shadow_oos_auc is not None and float(_shadow_oos_auc) >= 0.55 and
                                _shadow_oos_win is not None and float(_shadow_oos_win) >= 70.0 and
                                _shadow_oos_ret is not None and float(_shadow_oos_ret) >= 5.0
                            )
                            if _shadow_direction == "uncertain" and _shadow_oos_validates:
                                _shadow_direction = "normal"
                            if _shadow_direction == "uncertain":
                                _shadow_prob = 50.0
                            elif _shadow_direction == "invert":
                                _shadow_prob = 100.0 - _shadow_prob_raw
                            else:
                                _shadow_prob = _shadow_prob_raw
                        except Exception:
                            _shadow_prob = None

                    _blended = round(_base_prob * 0.6 + _p25_prob * 0.4, 1)
                    res["phase25_prob"] = round(_p25_prob, 1)
                    if _shadow_prob is not None:
                        res["phase25_shadow_prob"] = round(_shadow_prob, 1)
                    res["phase25_variant"] = os.path.splitext(os.path.basename(p25_path or "phase25_model.pkl"))[0]
                    res["phase25_signal_direction"] = _p25_direction
                    try:
                        res["phase25_raw_auc"] = float(p25_bundle.get("raw_auc")) if p25_bundle.get("raw_auc") is not None else None
                        res["phase25_cv_median_auc"] = float(p25_bundle.get("cv_median_auc")) if p25_bundle.get("cv_median_auc") is not None else None
                        res["phase25_oos_auc"] = float(p25_bundle.get("oos_auc")) if p25_bundle.get("oos_auc") is not None else None
                        res["phase25_oos_win_rate_pct"] = float(p25_bundle.get("oos_win_rate_pct")) if p25_bundle.get("oos_win_rate_pct") is not None else None
                        res["phase25_oos_avg_return_pct"] = float(p25_bundle.get("oos_avg_return_pct")) if p25_bundle.get("oos_avg_return_pct") is not None else None
                        res["phase25_target_horizon_days"] = int(p25_bundle.get("target_horizon_days") or 3)
                    except Exception:
                        res["phase25_raw_auc"] = None
                        res["phase25_cv_median_auc"] = None
                        res["phase25_oos_auc"] = None
                        res["phase25_oos_win_rate_pct"] = None
                        res["phase25_oos_avg_return_pct"] = None
                        res["phase25_target_horizon_days"] = None
                    if shadow_path:
                        res["phase25_shadow_variant"] = os.path.splitext(os.path.basename(shadow_path))[0]
                    res["phase25_recommended_threshold"] = float(p25_bundle.get("recommended_probability_threshold", 0.5) or 0.5) * 100.0
                    res["prob"] = _blended
                else:
                    phase25_degraded = True
                    if phase25_load_errors:
                        phase25_trace_status = "phase25_load_fail"
                        phase25_error = "; ".join(phase25_load_errors[:3])
                    else:
                        phase25_trace_status = "phase25_missing"
                        phase25_error = (
                            f"no_phase25_bundle_for ticker={self.ticker} "
                            f"scan_mode={str(getattr(self, 'scan_mode', 'SWING') or 'SWING').upper()}"
                        )
                    res["prob"] = _safe_prob(res["5pct"] if res["5pct"] is not None else universal_prob, 50.0)
            except Exception as exc:
                phase25_degraded = True
                phase25_trace_status = "phase25_exception"
                phase25_error = f"{type(exc).__name__}: {exc}"
                res["prob"] = _safe_prob(res["5pct"] if res["5pct"] is not None else universal_prob, 50.0)

            raw_prob = res.get('5pct')
            clean_prob = res.get('5pct_clean')
            res['prob'] = _safe_prob(res.get('prob', universal_prob), 50.0)
            res['raw_prob'] = _safe_prob(raw_prob if raw_prob is not None else universal_prob, res['prob'])
            res['clean_prob'] = _safe_prob(clean_prob if clean_prob is not None else res['prob'], res['prob'])
            if universal_prob is not None:
                res['universal_prob'] = _safe_prob(universal_prob, 50.0)
            res['signal'] = "STRONG_BUY" if res['prob'] >= 60 else ("BUY" if res['prob'] >= 55 else "NEUTRAL")
            res['regime'] = f"Phase25+18.2_{suffix.upper()}"
            res['accuracy'] = res['clean_prob']
            res['model_trace_status'] = phase25_trace_status or "ok"
            if phase25_error:
                res['model_error'] = phase25_error
            res['phase25_degraded'] = bool(phase25_degraded)
            # inference_failed flags rows where NO scan-specific model produced a
            # probability and we ended up on the universal-fallback or generic path.
            # Downstream decision gates use this to exclude affected tickers from
            # PICK — see modules/scanner_services.py and planner_runtime.
            res['inference_failed'] = bool(
                raw_prob is None and clean_prob is None and not res.get('phase25_prob')
            )
            if raw_prob is None and clean_prob is None and universal_prob is not None:
                res['type'] = "Universal Fallback ML"
                res['regime'] = f"Universal_Fallback_{suffix.upper()}"
                if not phase25_trace_status:
                    res['model_trace_status'] = "universal_fallback"
            else:
                res['type'] = "Regime+Phase25 ML" if not phase25_degraded else "Regime ML + Phase25 Degraded"
            res['model_health'] = {
                "phase18_ready": bool(os.path.exists(model_5_path) or os.path.exists(model_clean_path)),
                "phase25_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_model.pkl'))),
                "phase25_kr_swing_xgboost_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_kr_swing_xgboost.pkl'))),
                "phase25_kr_swing_lightgbm_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_kr_swing_lightgbm.pkl'))),
                "phase25_kr_intraday_xgboost_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_kr_intraday_xgboost.pkl'))),
                "phase25_kr_intraday_histgb_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_kr_intraday_histgb.pkl'))),
                "phase25_kr_intraday_lightgbm_ready": bool(os.path.exists(os.path.join(models_dir, 'phase25_kr_intraday_lightgbm.pkl'))),
                "universal_ready": bool(universal_prob is not None),
            }
            return res

        except Exception as e:
            return {
                "prob": 50,
                "raw_prob": 50,
                "clean_prob": 50,
                "signal": "NEUTRAL",
                "regime": "Error",
                "accuracy": 0,
                "type": "Fail",
                "model_trace_status": "exception",
                "model_error": f"{type(e).__name__}: {e}",
                "inference_failed": True,
            }

    # --- Phase 8: Grand Synergy Report ---
    def generate_synergy_report(self):
        """
        Synthesize ALL data into a coherent Analyst Verdict.
        Returns: String (Markdown)
        """
        if self.df is None: return "데이터 부족으로 분석 불가."
        
        # 1. Gather Intelligence
        # Tech
        setup = self.get_trade_setup()
        trend = "상승" if self.df['Close'].iloc[-1] > self.df['MA_20'].iloc[-1] else "하락"
        
        # Fund
        fund_pass, fund_reason = self.check_fundamentals()
        
        # ML
        ml_pred = self.get_ml_prediction()
        ml_prob = ml_pred.get('prob', 50)
        
        # Macro
        macro = self.get_macro_context() # already implemented?
        # Re-fetch context if needed or assume safe
        
        # Whale
        whale = self.analyze_supply_demand()
        whale_score = whale.get('whale_score', 0)
        
        # RS
        rs = self.get_relative_strength()
        
        # 2. Logic Synthesis
        verdict = "### 📋 종합 AI 애널리스트 분석 (Synergy Report)\n\n"
        
        # Condition A: Perfect Storm (Bullish)
        if ml_prob > 60 and fund_pass and rs.get('is_leader') and whale_score > 60:
            verdict += f"**🚀 강력 매수 (Strong Buy)**: 완벽한 4박자(차트/재무/수급/AI)가 일치합니다.\n"
            verdict += f"- **이유**: 업종 주도주(RS>{rs.get('rs_ratio')})이며, 기관 수급({whale_score}점)과 AI 상승 확률({ml_prob:.1f}%)이 동시에 뒷받침됩니다.\n"
            
        # Condition B: Tech Good but Fund Bad (Speculative)
        elif ml_prob > 60 and not fund_pass:
            verdict += f"**⚠️ 트레이딩 관점 접근 (Speculative Buy)**: 차트와 AI 신호는 좋으나 펀더멘털 위험이 있습니다.\n"
            verdict += f"- **주의**: {fund_reason}. 장기 보유보다는 단기 시세 차익(Target 달성 시 즉시 매도)을 권장합니다.\n"
            
        # Condition C: Fund Good but Tech Bad (Value Trap?)
        elif ml_prob < 40 and fund_pass:
            verdict += f"**👀 관망 (Watch)**: 우량주이나 현재 하락 추세입니다.\n"
            verdict += f"- **전략**: AI가 상승 확률을 낮게({ml_prob:.1f}%) 보고 있습니다. 바닥 신호(Golden Cross) 대기하세요.\n"
            
        # Condition D: Bearish
        else:
            verdict += f"**🛑 보류 (Hold/Sell)**: 뚜렷한 상승 모멘텀이 포착되지 않습니다.\n"
        
        # Add Confluence Detail
        conf_score = setup.get('Confluence Score', 0)
        if conf_score > 0:
            verdict += f"\n> **Tip**: 현재 {conf_score}개의 기술적 지지선이 겹치는 자리입니다. 손익비가 유리한 구간입니다."
            
        return verdict

    def load_model_registry(self):
        """Load the model registry from JSON"""
        registry_path = "model_registry.json"
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_model_registry(self, registry):
        """Save the model registry to JSON"""
        registry_path = "model_registry.json"
        try:
            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=4)
        except Exception as e:
            print(f"Error saving registry: {e}")

    def get_macro_context(self):
        """
        Return latest Macro context (Index Value, Forex Rate, Regime Status)
        """
        macro = self.fetch_macro_context()
        context = {
            'market_index_value': 0.0,
            'forex_rate': 0.0,
            'market_regime': 'Unknown'
        }
        
        if macro is not None and not macro.empty:
            last = macro.iloc[-1]
            context['market_index_value'] = float(last['Index'])
            context['forex_rate'] = float(last['Forex'])
            
            # Simple Regime Logic: Index > MA20
            # We need to calculate MA on the macro df.
            # Assuming macro df has enough history.
            ma20 = macro['Index'].rolling(20).mean().iloc[-1]
            context['market_regime'] = 'Safe' if last['Index'] > ma20 else 'Danger'
            
        return context

    def fetch_macro_context(self):
        """
        Fetch Macro-Economic data for context:
        1. Market Index (KOSPI/KOSDAQ/S&P500)
        2. Currency/Forex (USD/KRW or DXY)
        3. VIX (Volatility)
        Returns: DataFrame with 'Index', 'Forex', '^VIX', '^TNX'
        """
        # Determine Market & Tickers
        index_ticker = "^GSPC" # Default S&P500
        forex_ticker = "DX-Y.NYB" # Default Dollar Index
        
        if ".KS" in self.ticker: # KOSPI
            index_ticker = "^KS11"
            forex_ticker = "KRW=X" # USD/KRW
        elif ".KQ" in self.ticker.upper(): # KOSDAQ
            index_ticker = "^KQ11"
            forex_ticker = "KRW=X"
            
        try:
            # Helper to download and clean (Thread-Safe)
            def get_clean(tik, name):
                d = get_history(tik, period='2y', interval='1d')
                if d.empty: return pd.Series(name=name)
                if d.index.tz is not None:
                    d.index = d.index.tz_localize(None)
                s = d['Close']
                s.name = name
                return s

            # Fetch individually to avoid MultiIndex mess
            s_idx = get_clean(index_ticker, 'Index')
            s_fx  = get_clean(forex_ticker, 'Forex')
            s_vix = get_clean('^VIX', '^VIX')
            s_tnx = get_clean('^TNX', '^TNX')
            
            # Combine
            macro_df = pd.concat([s_idx, s_fx, s_vix, s_tnx], axis=1)
            macro_df = macro_df.fillna(method='ffill').fillna(method='bfill')
            
            return macro_df
            
        except Exception as e:
            print(f"Macro Data Error: {e}")
            return None

    def fetch_hourly_data(self):
        """
        Fetch Hourly Data (Max 730 days limit by yfinance) for High-Res Prediction.
        """
        try:
            # Fetch 1h data for max allowed period (Thread-Safe)
            ticker_obj = yf.Ticker(self.ticker)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                df_h = ticker_obj.history(period='730d', interval='1h')
            if df_h.index.tz is not None:
                df_h.index = df_h.index.tz_localize(None)
            df_h = df_h[['Close']].dropna()
            return df_h
        except Exception as e:
            print(f"Hourly Fetch Error: {e}")
            return pd.DataFrame()

    def tune_hyperparameters(self, df_p, param_grid=None):
        """
        Run Grid Search to find best parameters.
        Returns: best_params dict
        """
        if param_grid is None:
            param_grid = {
                'changepoint_prior_scale': [0.01, 0.05, 0.1, 0.5],
                'seasonality_prior_scale': [0.1, 1.0, 10.0]
            }
        
        best_mape = float('inf')
        best_params = {
            'changepoint_prior_scale': 0.05, # Prophet Default
            'seasonality_prior_scale': 10.0  # Prophet Default
        }
        
        # Validation Split (Last 30 days)
        train_df = df_p.iloc[:-30]
        test_df = df_p.iloc[-30:]
        y_true = np.expm1(test_df['y'])
        
        # Manual Grid Search Loop
        import itertools
        keys, values = zip(*param_grid.items())
        total_combos = 1
        for v in values: total_combos *= len(v)
        
        # print(f"Tuning {self.ticker}: Testing {total_combos} combinations...")
        
        for v in itertools.product(*values):
            params = dict(zip(keys, v))
            
            try:
                m = Prophet(daily_seasonality=True, **params)
                m.add_regressor('RSI')
                m.add_regressor('Volume')
                if 'Index' in df_p.columns: m.add_regressor('Index')
                if 'Forex' in df_p.columns: m.add_regressor('Forex')
                
                m.fit(train_df)
                
                cols = ['ds', 'RSI', 'Volume']
                if 'Index' in df_p.columns: cols.append('Index')
                if 'Forex' in df_p.columns: cols.append('Forex')
                
                future_val = test_df[cols]
                forecast_val = m.predict(future_val)
                y_pred = np.expm1(forecast_val['yhat'])
                
                mape = np.mean(np.abs((y_true.values - y_pred.values) / y_true.values)) * 100
                
                if mape < best_mape:
                    best_mape = mape
                    best_params = params
                    
            except:
                continue
                
        return best_params, best_mape




                
    # --- IMPROVED PROPHET WITH MEAN REVERSION ---
    def predict_future(self, days=30, sentiment_score=0.0, macro_status='RISK_ON'):
        """
        Predict future price using Prophet with Mean Reversion regressors & Sentiment Bias.
        sentiment_score: -1.0 to 1.0 (from News Analysis)
        macro_status: 'RISK_ON' or 'RISK_OFF' (from Macro Analysis)
        """
        if self.df is None or len(self.df) < 50: return None
        
        # Prepare Data
        data = self.df.reset_index()
        date_col = data.columns[0]
        data.rename(columns={date_col: 'ds'}, inplace=True)
        
        df_p = data[['ds', 'Close', 'RSI', 'Volume']].copy()
        df_p.columns = ['ds', 'y', 'RSI', 'Volume']
        df_p['y'] = np.log1p(df_p['y'])
        
        # Normalize Data Dates to Midnight to ensure merge works
        df_p['ds'] = pd.to_datetime(df_p['ds']).dt.normalize()
        
        # Drop NaNs
        df_p.dropna(inplace=True) 

        try:
             # Train Model
             # Phase 3: Macro-Gated Confidence
             # If RISK_OFF (Crisis), we widen interval to 0.95 (95%) to show extreme uncertainty.
             # Default is 0.80 (80%).
            uncertainty = 0.95 if macro_status == 'RISK_OFF' else 0.80
            
            # --- Phase 7: Hybrid Graph (Prophet + Macro + ML Bias) ---
            # 1. Merge Macro Data (Regressor)
            macro = self._fetch_global_macro_data()
            if macro is not None:
                # Merge on DS. Ensure types match.
                # macro index is Datetime. df_p['ds'] is Datetime.
                df_p = df_p.merge(macro, left_on='ds', right_index=True, how='left')
                df_p = df_p.fillna(method='ffill').fillna(method='bfill') # Fill macro gaps
            
            # --- PHASE 14: Hybrid Ensemble (Prophet + XGBoost) ---
            # Concept: Prophet models Trend/Seasonality. XGBoost models the Residuals (Technical Alpha).
            
            # 1. Fit Prophet (Trend)
            m = Prophet(daily_seasonality=True, interval_width=uncertainty, changepoint_prior_scale=0.15)
            # Prophet Regressors (Macro only, remove noisy technicals from Prophet)
            # Let XGBoost handle technicals as they are non-linear shocks
            if macro is not None:
                for col in ['^VIX', '^TNX', 'KRW=X']:
                    if col in df_p.columns:
                        m.add_regressor(col)
            
            m.fit(df_p)
            
            # 2. Make Future DF
            future = m.make_future_dataframe(periods=days, freq='D', include_history=False)
            future['ds'] = pd.to_datetime(future['ds']).dt.normalize()
            future = future[future['ds'].dt.dayofweek < 5] # No weekends
            
            # Regressor Fill (Forward Fill Macro)
            last_row = df_p.iloc[-1]
            if macro is not None:
                for col in ['^VIX', '^TNX', 'KRW=X']:
                    if col in df_p.columns:
                        future[col] = last_row[col] 
                        
            # 3. Prophet Predict
            # History
            hist_pred = m.predict(df_p)
            # Future
            future_full_p = pd.concat([df_p[['ds'] + ([c for c in ['^VIX', '^TNX', 'KRW=X'] if c in df_p.columns])], future], ignore_index=True)
            forecast = m.predict(future_full_p)
            
            # --- PHASE 15: Conformal Prediction (Calibration) ---
            # Calculate Residuals on HISTORY (Calibration Set)
            y_true = df_p['y'].values
            y_pred_base = hist_pred['yhat'].values[-len(y_true):]
            
            residuals = np.abs(y_true - y_pred_base)
            
            # 95% Confidence -> We need to cover 95% of errors.
            # q_95 = 95th percentile of Absolute Errors
            q_90 = np.percentile(residuals, 90) # 90%
            q_95 = np.percentile(residuals, 95) # 95%
            
            # Use q_95 for the interval width (Robust to noise)
            conformal_width = q_95
            
            print(f"🎯 Conformal Calibration: 95% Bound = {conformal_width:.4f}")

            # 4. XGBoost Residual Learning (The Correction)
            best_config = {'name': 'Standard'}
            best_val_mape = 0
            try:
                if HAS_XGBOOST:
                    # Calculate Residuals (Log Scale)
                    train_res = df_p['y'] - hist_pred['yhat'][:len(df_p)]
                    
                    # Features (Feature Engineering 2.0)
                    # Use a helper to generate enriched features for both Train and Future
                    # We need to compute these on the FULL dataframe first to get correct rolling values
                    
                    tech_df = self.df.copy()
                    
                    # 1. Advanced Features
                    # MA Divergence (Price vs MA50) - Mean Reversion
                    if 'MA_50' in tech_df.columns:
                        tech_df['MA_Div_50'] = (tech_df['Close'] - tech_df['MA_50']) / tech_df['MA_50']
                    else:
                        tech_df['MA_Div_50'] = 0
                        
                    # Bollinger %B (Position within Bands)
                    if 'BBU_20_2.0' in tech_df.columns:
                        top = tech_df['BBU_20_2.0']
                        bot = tech_df['BBL_20_2.0']
                        tech_df['Boll_PB'] = (tech_df['Close'] - bot) / (top - bot)
                    else:
                        tech_df['Boll_PB'] = 0.5
                        
                    # Stochastic Oscillator (Fast K)
                    try:
                        low_14 = tech_df['Low'].rolling(14).min()
                        high_14 = tech_df['High'].rolling(14).max()
                        tech_df['Stoch_K'] = ((tech_df['Close'] - low_14) / (high_14 - low_14)) * 100
                    except:
                        tech_df['Stoch_K'] = 50
                        
                    # CCI (Commodity Channel Index) - Momentum
                    try:
                        if HAS_TALIB:
                            tech_df['CCI'] = talib.CCI(tech_df['High'], tech_df['Low'], tech_df['Close'], timeperiod=14)
                        else:
                            # Simple Approx
                            tp = (tech_df['High'] + tech_df['Low'] + tech_df['Close']) / 3
                            sma = tp.rolling(14).mean()
                            mad = tp.rolling(14).apply(lambda x: pd.Series(x).mad())
                            tech_df['CCI'] = (tp - sma) / (0.015 * mad)
                    except: tech_df['CCI'] = 0
                    
                    # Historical Volatility (HV) - 20 Day
                    tech_df['HV_20'] = tech_df['Close'].pct_change().rolling(20).std() * 100
                    
                    # --- Phase 30: Advanced AI Features ---
                    # 1. Volume Change (Rel Vol)
                    if 'Volume' in tech_df.columns:
                        vol_ma20 = tech_df['Volume'].rolling(20).mean().replace(0, 1)
                        tech_df['Vol_Change'] = tech_df['Volume'] / vol_ma20
                    else:
                        tech_df['Vol_Change'] = 1.0
                        
                    # 2. Price Gap (Gap % from Prev Close to Open)
                    prev_close = tech_df['Close'].shift(1)
                    tech_df['Price_Gap'] = (tech_df['Open'] - prev_close) / prev_close
                    tech_df['Price_Gap'] = tech_df['Price_Gap'].fillna(0)
                    
                    # 3. Bollinger Band Width (Vol Expansion)
                    if 'BBU_20_2.0' in tech_df.columns:
                        width = (tech_df['BBU_20_2.0'] - tech_df['BBL_20_2.0'])
                        mid = tech_df['MA_20'] if 'MA_20' in tech_df.columns else tech_df['Close']
                        tech_df['BB_Width'] = width / mid
                    else:
                        tech_df['BB_Width'] = 0
                        
                    # 4. ROC (Rate of Change 5-day)
                    tech_df['ROC_5'] = tech_df['Close'].pct_change(5) * 100
                    
                    # Fallbacks
                    if 'OBV' not in tech_df.columns: tech_df['OBV'] = tech_df['Volume']
                    tech_df = tech_df.fillna(method='ffill').fillna(0)
                    
                    # Select Features for XGBoost
                    # Select Features for XGBoost (Phase 30 Upgrade)
                    feature_cols = [
                        'RSI', 'ATR', 'OBV', 'MA_Div_50', 'Boll_PB', 'Stoch_K', 'CCI', 'HV_20',
                        'VIX', 'TNX', 'DXY', 'W_RSI', 'W_Trend', 'RS_Mansfield',
                        'Vol_Change', 'Price_Gap', 'BB_Width', 'ROC_5'
                    ]
                    # Ensure all exist
                    for c in feature_cols:
                        if c not in tech_df.columns: tech_df[c] = 0
                    
                    # Safe index alignment (dates may not match exactly)
                    common_dates = df_p['ds'][df_p['ds'].isin(tech_df.index)]
                    if len(common_dates) < 30:
                        raise ValueError(f"Not enough overlapping dates: {len(common_dates)}")
                    
                    X_train = tech_df.loc[common_dates, feature_cols].values
                    y_train_raw = train_res.iloc[:len(common_dates)].values
                    
                    # Ensure same length
                    min_len = min(len(X_train), len(y_train_raw))
                    X_train = X_train[:min_len]
                    y_train = y_train_raw[:min_len]
                    
                    # Sanitize: Remove NaNs/Infs
                    y_series = pd.Series(y_train)
                    y_series = y_series.replace([np.inf, -np.inf], np.nan)
                    valid_mask = ~y_series.isna()
                    
                    X_df = pd.DataFrame(X_train)
                    X_df = X_df.replace([np.inf, -np.inf], np.nan)
                    valid_mask_X = ~X_df.isna().any(axis=1)
                    
                    final_mask = valid_mask & valid_mask_X
                    
                    if final_mask.sum() < 10:
                        raise ValueError("Not enough clean data for XGBoost")
                         
                    X_train = X_train[final_mask]
                    y_train = y_train[final_mask]
                    
                    # --- AUTO-TUNING ENGINE (Phase 16) ---
                    # Mini-GridSearch to find best fit for this specific stock
                    presets = [
                        {'depth': 2, 'lr': 0.01, 'est': 100, 'name': 'Conservative'}, # Low Variance
                        {'depth': 3, 'lr': 0.05, 'est': 100, 'name': 'Balanced'},     # Default
                        {'depth': 5, 'lr': 0.10, 'est': 150, 'name': 'Aggressive'}    # High Variance
                    ]
                    
                    best_model = None
                    best_score = float('inf')
                    best_config = {}
                    
                    # Time-Series Split (Last 20% for Validation)
                    split_idx = int(len(X_train) * 0.8)
                    best_val_mape = 0
                    
                    if split_idx > 10: # Ensure enough data
                        X_t, X_v = X_train[:split_idx], X_train[split_idx:]
                        y_t, y_v = y_train[:split_idx], y_train[split_idx:]
                        
                        # Indices for Price Reconstruction
                        val_indices = df_p.index[split_idx:]
                        # Real Prices (Original Scale)
                        real_prices = np.expm1(df_p.loc[val_indices, 'y'])
                        # Prophet Baseline (Original Scale projection)
                        # We need base log-pred to add residuals
                        base_log_preds = hist_pred['yhat'].iloc[split_idx:len(df_p)].values

                        for p in presets:
                            model = XGBRegressor(n_estimators=p['est'], learning_rate=p['lr'], max_depth=p['depth'], objective='reg:squarederror')
                            model.fit(X_t, y_t)
                            preds = model.predict(X_v)
                            
                            # RMSE (Optimization Target)
                            rmse = np.sqrt(np.mean((y_v - preds)**2))
                            
                            # Calculate 'Honest' MAPE (Price Scale)
                            final_log_pred = base_log_preds + preds
                            final_price_pred = np.expm1(final_log_pred)
                            val_mape = np.mean(np.abs((real_prices - final_price_pred) / real_prices)) * 100
                            
                            if rmse < best_score:
                                best_score = rmse
                                best_config = p
                                best_val_mape = val_mape
                    else:
                        best_config = presets[1] # Balanced
                        best_val_mape = 0 # Not enough data
                        
                    # Retrain Winner on FULL Data
                    xgb = XGBRegressor(n_estimators=best_config['est'], learning_rate=best_config['lr'], max_depth=best_config['depth'], objective='reg:squarederror')
                    xgb.fit(X_train, y_train)
                    print(f"🧬 Selected AI Mode: {best_config['name']} (Val MAPE: {best_val_mape:.2f}%)")
                    
                    # --- Apply Correction to HISTORY (Visual Proof) ---
                    # Predict on Training Data to show Hybrid Fit
                    pred_train_res = xgb.predict(X_train)
                    
                    # Update Forecast History (indices 0 to last_idx-1)
                    # Note: forecast has more rows than df_p (it includes weekends if 'D' freq, but prophet removes them?)
                    # Prophet's forecast includes history dates.
                    # We need to match indices. df_p and forecast[:len(df_p)] should align if make_future_df included history=False?
                    # Ah, we reconstructed future_full_p which includes df_p.
                    
                    limit_idx = len(df_p)
                    forecast.iloc[:limit_idx, forecast.columns.get_loc('yhat')] += pred_train_res
                    
                    # Apply Conformal Width to History too (Show coverage)
                    forecast.iloc[:limit_idx, forecast.columns.get_loc('yhat_lower')] = forecast.iloc[:limit_idx, forecast.columns.get_loc('yhat')] - conformal_width
                    forecast.iloc[:limit_idx, forecast.columns.get_loc('yhat_upper')] = forecast.iloc[:limit_idx, forecast.columns.get_loc('yhat')] + conformal_width
                    
                    
                    # Predict X (Future) - Feature Engineering 2.0 Extrapolation
                    last_tech = tech_df.iloc[-1]
                    future_steps = len(future)
                    
                    # 1. Base Features Decay
                    f_rsi = np.linspace(last_tech['RSI'], 50, future_steps)
                    f_atr = np.full(future_steps, last_tech['ATR']) # Volatility Clustering (Persistence)
                    f_obv = np.full(future_steps, last_tech['OBV']) # Assumption: No new volume info
                    
                    # 2. Advanced Features Decay (Mean Reversion)
                    f_div = np.linspace(last_tech['MA_Div_50'], 0, future_steps) # Revert to Mean
                    f_pb = np.linspace(last_tech['Boll_PB'], 0.5, future_steps) # Revert to Middle Band
                    f_stoch = np.linspace(last_tech['Stoch_K'], 50, future_steps)
                    f_cci = np.linspace(last_tech['CCI'], 0, future_steps)
                    f_hv = np.full(future_steps, last_tech.get('HV_20', 20))
                    f_hv = np.full(future_steps, last_tech.get('HV_20', 20))
                    # 3. Macro & Context Features Decay (Phase 18)
                    f_vix = np.full(future_steps, last_tech.get('VIX', 20))
                    f_tnx = np.full(future_steps, last_tech.get('TNX', 4.0))
                    f_dxy = np.full(future_steps, last_tech.get('DXY', 100))
                    f_wrsi = np.linspace(last_tech.get('W_RSI', 50), 50, future_steps) # Decay to neutral
                    f_wtrend = np.full(future_steps, last_tech.get('W_Trend', 0)) # Trend persists
                    f_rs = np.full(future_steps, last_tech.get('RS_Mansfield', 0)) # RS persists

                    # Stack in exact order: ['RSI', 'ATR', 'OBV', 'MA_Div_50', 'Boll_PB', 'Stoch_K', 'CCI', 'HV_20', 'VIX', 'TNX', 'DXY', 'W_RSI', 'W_Trend', 'RS_Mansfield']
                    X_future = np.column_stack((
                        f_rsi, f_atr, f_obv, f_div, f_pb, f_stoch, f_cci, f_hv,
                        f_vix, f_tnx, f_dxy, f_wrsi, f_wtrend, f_rs
                    ))
                    
                    pred_res = xgb.predict(X_future)
                    
                    # Apply Correction to Prophet Forecast (Future Part)
                    last_idx = len(df_p)
                    forecast.iloc[last_idx:, forecast.columns.get_loc('yhat')] += pred_res
                    
                    # --- CONFORMAL UPDATE (Future) ---
                    # Instead of Prophet's sigma, we use the Calibrated Conformal Width
                    # New Interval = New Mean +/- q_95
                    forecast.iloc[last_idx:, forecast.columns.get_loc('yhat_lower')] = forecast.iloc[last_idx:, forecast.columns.get_loc('yhat')] - conformal_width
                    forecast.iloc[last_idx:, forecast.columns.get_loc('yhat_upper')] = forecast.iloc[last_idx:, forecast.columns.get_loc('yhat')] + conformal_width
                    
                    print(f"🧬 Hybrid Correction Applied. Mean Res: {np.mean(pred_res):.4f}")
                    
            except Exception as ml_e:
                print(f"XGBoost Error: {ml_e}")
                # Fallback: Apply Conformal Width to whole forecast (History + Future)
                forecast['yhat_lower'] = forecast['yhat'] - conformal_width
                forecast['yhat_upper'] = forecast['yhat'] + conformal_width

            # --- Apply ML Probability Bias (Legacy Tilt) ---
            ml_pred = self.get_ml_prediction()
            ml_prob = ml_pred.get('prob', 50)
            
            # Future Mask
            last_ds = df_p['ds'].max()
            future_mask = forecast['ds'] > last_ds
            
            if future_mask.sum() > 0:
                bias_slope = (ml_prob - 50) * 0.0001 
                step_indices = np.arange(1, future_mask.sum() + 1)
                
                # Apply
                forecast.loc[future_mask, 'yhat'] += (bias_slope * step_indices)
                forecast.loc[future_mask, 'yhat_lower'] += (bias_slope * step_indices)
                forecast.loc[future_mask, 'yhat_upper'] += (bias_slope * step_indices)

            # --- Apply Sentiment Bias (News) ---
            if abs(sentiment_score) > 0.1 and future_mask.sum() > 0:
                 # Sentiment ranges -1.0 to 1.0
                 # Max impact: +/- 2% over 30 days
                 sent_slope = sentiment_score * 0.0005 
                 step_indices = np.arange(1, future_mask.sum() + 1)
                 
                 forecast.loc[future_mask, 'yhat'] += (sent_slope * step_indices)
                 forecast.loc[future_mask, 'yhat_lower'] += (sent_slope * step_indices)
                 forecast.loc[future_mask, 'yhat_upper'] += (sent_slope * step_indices)
                 print(f"📰 Sentiment Bias Applied: {sentiment_score:.2f}")

            # Inverse Transform
            forecast['yhat'] = np.expm1(forecast['yhat'])
            forecast['yhat_lower'] = np.expm1(forecast['yhat_lower'])
            forecast['yhat_upper'] = np.expm1(forecast['yhat_upper'])
            
            # MAPE Calculation (on History)
            y_true = np.expm1(df_p['y'])
            y_pred = np.expm1(hist_pred['yhat'])
            final_mape = np.mean(np.abs((y_true.iloc[-30:] - y_pred.iloc[-30:]) / y_true.iloc[-30:])) * 100
            
            # --- SNIPER CHECK ---
            # If Interval Width > 25% of price (Relaxed from 10%), it's too 'Hazy'
            latest_fc = forecast.iloc[-1]
            width_pct = (latest_fc['yhat_upper'] - latest_fc['yhat_lower']) / latest_fc['yhat']
            
            sniper_status = "READY"
            if width_pct > 0.25: 
                sniper_status = "HAZY"
            elif final_mape > 25: # Relaxed from 15%
                sniper_status = "INACCURATE"
            
            return {
                'forecast': forecast, 
                'mape': final_mape, 
                'is_tuned': True,
                'sniper_status': sniper_status,
                'conformal_width': conformal_width,
                'tuning_mode': best_config.get('name', 'Standard'),
                'validation_mape': best_val_mape
            }
            
        except Exception as e:
            print(f"Hybrid Forecast Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_final_verdict(self, current_price, ai_result, alpha_score, macro_status, rs_score):
        """
        Phase 19: The Oracle (Final Verdict Engine)
        Synthesize Tech, AI, Macro, Context into a definitive judgement.
        Works even when ai_result is None (Prophet failed).
        """
        verdict = {
            "decision": "HOLD ✋",
            "confidence": 0,
            "color": "orange",
            "holding_period": "-",
            "reason": "분석 중..."
        }
        
        try:
            # 1. Gate 1: Accuracy Validation (Sniper Check)
            penalty = 0
            sniper_status = 'N/A'
            forecast = None
            upside = 0
            
            if ai_result is not None and isinstance(ai_result, dict):
                sniper_status = ai_result.get('sniper_status', 'HAZY')
                forecast = ai_result.get('forecast')
                
                if sniper_status == 'INACCURATE':
                    penalty = 30
                elif sniper_status == 'HAZY':
                    penalty = 15
            else:
                # No AI result — apply moderate penalty
                penalty = 20
            
            # 2. Integrated Confidence Score
            # Tech (30%): Alpha Score (0-100)
            score_tech = alpha_score * 0.3
            
            # AI (30%): Based on forecast or ML prediction
            score_ai = 0
            if forecast is not None:
                try:
                    last_pred = forecast['yhat'].iloc[-1]
                    upside = ((last_pred - current_price) / current_price) * 100
                    
                    if upside > 10: ai_pts = 100
                    elif upside > 5: ai_pts = 80
                    elif upside > 0: ai_pts = 60
                    else: ai_pts = 20
                    score_ai = ai_pts * 0.3
                except:
                    score_ai = 0
            else:
                # Use ML prediction as AI score fallback
                ml_pred = self.get_ml_prediction()
                ml_prob = ml_pred.get('prob', 50)
                score_ai = (ml_prob / 100) * 30  # Scale 0-30
            
            # Macro (20%): Risk On/Off
            macro_pts = 100 if macro_status == 'RISK_ON' else 60 if macro_status == 'NEUTRAL' else 40
            score_macro = macro_pts * 0.2
            
            # Context (20%): RS & Weekly Trend
            ctx_pts = 50
            if rs_score > 0: ctx_pts += 20
            w_trend = self.df['W_Trend'].iloc[-1] if 'W_Trend' in self.df.columns else 0
            if w_trend == 1: ctx_pts += 30
            elif w_trend == -1: ctx_pts -= 20
            score_ctx = min(100, ctx_pts) * 0.2
            
            total_score = score_tech + score_ai + score_macro + score_ctx - penalty
            verdict['confidence'] = max(0, int(total_score))
            
            # 3. Final Decision Matrix
            if total_score >= 85:
                verdict['decision'] = "🟢 강력 매수 (STRONG BUY)"
                verdict['color'] = "#00FF88"
                verdict['reason'] = "기술적/AI/수급 3박자 완성. 적극 매수 추천."
            elif total_score >= 70:
                verdict['decision'] = "🔵 매수 (BUY)"
                verdict['color'] = "#00B0F6"
                verdict['reason'] = "상승 추세 확인. 분할 매수 진입 권장."
            elif total_score >= 50:
                verdict['decision'] = "🟡 관망 (HOLD)"
                verdict['color'] = "orange"
                verdict['reason'] = "추세 불명확. 진입하지 마세요."
            else:
                verdict['decision'] = "🔴 매도 (SELL)"
                verdict['color'] = "#FF4444"
                verdict['reason'] = "하락 리스크 높음. 보유 중이면 매도 고려."
                
            # 4. Holding Period Estimation
            if forecast is not None and upside > 0:
                try:
                    future_fc = forecast[forecast['ds'] > pd.Timestamp.now()]
                    if not future_fc.empty:
                        peak_idx = future_fc['yhat'].idxmax()
                        peak_date = future_fc.loc[peak_idx, 'ds']
                        days_to_peak = (peak_date - pd.Timestamp.now()).days
                        
                        if days_to_peak <= 5: verdict['holding_period'] = "초단기 (1~5일)"
                        elif days_to_peak <= 20: verdict['holding_period'] = "단기 스윙 (1~3주)"
                        else: verdict['holding_period'] = "중기 추세 (1~2개월)"
                except:
                    verdict['holding_period'] = "-"
                    
            return verdict
            
        except Exception as e:
            print(f"Oracle Error: {e}")
            return verdict

    def get_pattern_recognition(self):
        """
        Identify Candlestick Patterns using TA-Lib (or Pandas-TA fallback).
        Returns: List of detected patterns (e.g. ['Doji', 'Bullish Engulfing'])
        """
        patterns = []
        if self.df is None or len(self.df) < 5: return []
        
        try:
            # Prepare data
            open_ = self.df['Open']
            high = self.df['High']
            low = self.df['Low']
            close = self.df['Close']
            
            if HAS_TALIB:
                # 1. CDLDOJI
                doji = talib.CDLDOJI(open_, high, low, close)
                if doji.iloc[-1] != 0: patterns.append("Doji (Indecision)")
                
                # 2. CDLHAMMER
                hammer = talib.CDLHAMMER(open_, high, low, close)
                if hammer.iloc[-1] != 0: patterns.append("Hammer (Reversal)")
                
                # 3. CDLENGULFING
                engulf = talib.CDLENGULFING(open_, high, low, close)
                if engulf.iloc[-1] == 100: patterns.append("Bullish Engulfing 🔥")
                elif engulf.iloc[-1] == -100: patterns.append("Bearish Engulfing ❄️")
                
            else:
                # Fallback: Manual Calculation (Simple approximation)
                latest = self.df.iloc[-1]
                prev = self.df.iloc[-2]
                
                # Doji
                body = abs(latest['Close'] - latest['Open'])
                range_ = latest['High'] - latest['Low']
                if range_ > 0 and (body / range_) < 0.1:
                    patterns.append("Doji (Indecision) [Fallback]")
                    
                # Hammer
                lower_shadow = min(latest['Open'], latest['Close']) - latest['Low']
                upper_shadow = latest['High'] - max(latest['Open'], latest['Close'])
                if range_ > 0 and (lower_shadow / range_) > 0.6 and (body / range_) < 0.2:
                    patterns.append("Hammer (Reversal) [Fallback]")
                    
                # Bullish Engulfing
                if (latest['Close'] > latest['Open']) and (prev['Close'] < prev['Open']):
                    if (latest['Close'] > prev['Open']) and (latest['Open'] < prev['Close']):
                        patterns.append("Bullish Engulfing 🔥 [Fallback]")
            
            return patterns
            
        except Exception as e:
            # print(f"Pattern Error: {e}")
            return []

    def get_investor_flows(self):
        """
        Analyze Supply/Demand (Su-geup) for Korean Stocks.
        Returns: Dict with Whale Score (0-100) and flows.
        """
        import typing
        res: typing.Dict[str, typing.Any] = {'whale_score': 50, 'foreigner': 0, 'institution': 0, 'retail': 0, 'valid': False}
        
        # 1. Determine Market Type
        is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ')
        
        # --- A. KOREAN MARKET (pykrx primary + Naver fallback) ---
        if is_kr:
            code = str(self.ticker).split('.')[0]
            sum_inst, sum_for, sum_ret = 0.0, 0.0, 0.0
            _flow_source = None

            # pykrx investor flow API is unreliable on this env — skip directly to Naver

            # Naver Finance HTML fallback
            if _flow_source is None:
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    import io

                    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
                    headers = {"User-Agent": "Mozilla/5.0"}
                    res_req = requests.get(url, headers=headers, timeout=5)
                    soup = BeautifulSoup(res_req.text, "html.parser")
                    tables = soup.find_all("table", {"class": "type2"})
                    if len(tables) >= 2:
                        df_html = pd.read_html(io.StringIO(str(tables[1])), header=1)[0]
                        df_html = df_html.dropna(subset=['날짜'])
                        df_html['Institution'] = pd.to_numeric(df_html['순매매량'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                        df_html['Foreigner'] = pd.to_numeric(df_html['순매매량.1'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                        recent = df_html.head(10)
                        sum_inst = float(recent['Institution'].sum())
                        sum_for = float(recent['Foreigner'].sum())
                        sum_ret = -1 * (sum_inst + sum_for)
                        _flow_source = 'naver'
                except Exception:
                    pass

            if _flow_source is None:
                res['reason'] = "Both pykrx and Naver scraper failed"
                return res

            res['foreigner'] = int(sum_for)
            res['institution'] = int(sum_inst)
            res['retail'] = int(sum_ret)
            res['valid'] = True
            res['type'] = 'KR'
            res['flow_source'] = _flow_source

            # Scoring (KR) — Proportional to actual flows
            whale_flow = sum_inst + sum_for  # 기관 + 외인
            total_abs = abs(sum_inst) + abs(sum_for) + abs(sum_ret)

            score = 50  # Neutral baseline

            if total_abs > 0:
                # Whale dominance ratio: how much of total flow is whale?
                whale_ratio = whale_flow / total_abs if total_abs > 0 else 0
                # Range: -1 (pure retail) to +1 (pure whale)
                score = 50 + int(whale_ratio * 50)
                # Both inst AND foreign buying = strong consensus
                if sum_inst > 0 and sum_for > 0:
                    score += 5
                # Penalty: If retail buying is 3x+ whale, it's clearly retail-driven
                if abs(sum_ret) > abs(whale_flow) * 3 and sum_ret > 0:
                    score = min(score, 40)

            # Determine dominant investor type
            if abs(sum_for) > abs(sum_inst) and abs(sum_for) > abs(sum_ret):
                res['dominant'] = '외인'
            elif abs(sum_inst) > abs(sum_for) and abs(sum_inst) > abs(sum_ret):
                res['dominant'] = '기관'
            else:
                res['dominant'] = '개인'

            # 3-Day Whale Trend Analysis (short-term acceleration/deceleration)
            # For pykrx: recompute from flow df if available; for naver: use df_html
            try:
                if _flow_source == 'pykrx' and '_flow_df' in dir():
                    _r3 = _flow_df.tail(3)
                    sum_inst_3d = float(_r3[_col_map['institution']].sum()) if 'institution' in _col_map else 0.0
                    sum_for_3d = float(_r3[_col_map['foreigner']].sum()) if 'foreigner' in _col_map else 0.0
                elif _flow_source == 'naver' and 'df_html' in dir():
                    _r3 = df_html.head(3)
                    sum_inst_3d = float(_r3['Institution'].sum())
                    sum_for_3d = float(_r3['Foreigner'].sum())
                else:
                    sum_inst_3d, sum_for_3d = 0.0, 0.0
                whale_3d = sum_inst_3d + sum_for_3d
                whale_10d_avg = whale_flow / 10 * 3  # Normalized to 3-day equivalent
                if whale_3d > 0 and whale_3d > whale_10d_avg:
                    res['whale_trend'] = '🔥 가속매수'
                    score += 5
                elif whale_3d > 0:
                    res['whale_trend'] = '↗ 순매수'
                elif whale_3d < 0 and whale_3d < whale_10d_avg:
                    res['whale_trend'] = '🔻 가속매도'
                    score -= 10
                else:
                    res['whale_trend'] = '↘ 순매도'
            except Exception:
                pass

            res['whale_confidence'] = '확정'
            res['whale_score'] = max(0, min(100, score))
            return res

        # --- B. US MARKET (Smart Money Flow Proxy via Price & Volume) ---
        else:
            try:
                res['type'] = 'US_MOMENTUM'
                res['valid'] = True
                
                if self.df is None or len(self.df) < 20:
                    res['whale_score'] = 50
                    return res
                
                # We want to measure if "Big Money" is accumulating in the short term.
                # 1. Closing near the high of the day (Conviction)
                # 2. Volume on Up days vs Down days (Accumulation)
                # 3. Proximity to Mid-Term High (Momentum)
                
                df20 = self.df.tail(20)
                
                # 1. Accumulation/Distribution Proxy (Vol on Up days vs Down days)
                up_vol = df20.loc[df20['Close'] > df20['Open'], 'Volume'].sum()
                down_vol = df20.loc[df20['Close'] < df20['Open'], 'Volume'].sum()
                acc_dist_ratio = up_vol / max(float(down_vol), 1.0)
                
                # 2. Close-to-High Ratio (Last 5 days)
                df5 = self.df.tail(5)
                high_low_range = df5['High'] - df5['Low']
                close_from_low = df5['Close'] - df5['Low']
                # Avoid division by zero
                close_location = (close_from_low / high_low_range.replace(0, 1)).mean()
                
                # 3. Proximity to local High (Momentum)
                lookback_days = min(len(self.df), 120)
                recent_high = self.df['High'].tail(lookback_days).max()
                curr_price = float(self.df['Close'].iloc[-1])
                dist_from_high = (curr_price / max(float(recent_high), 0.001))
                
                # Scoring (Max 100)
                score = 50 # Base neutral
                
                if acc_dist_ratio > 1.5: score += 20
                elif acc_dist_ratio > 1.1: score += 10
                elif acc_dist_ratio < 0.8: score -= 10
                
                if close_location > 0.7: score += 15
                elif close_location > 0.5: score += 5
                elif close_location < 0.3: score -= 10
                
                if dist_from_high > 0.90: score += 15
                elif dist_from_high > 0.80: score += 5
                elif dist_from_high < 0.60: score -= 15
                
                # Recent Spike Bonus
                today_vol = float(self.df['Volume'].iloc[-1])
                avg_vol = float(df20['Volume'].mean())
                if today_vol > avg_vol * 1.5 and curr_price > float(self.df['Open'].iloc[-1]):
                    score += 10
                    
                res['institution_own'] = 0 # Deprecated, kept for schema compat
                res['insider_own'] = 0     # Deprecated
                res['whale_score'] = max(0, min(100, int(score)))
                res['whale_trend'] = '↗ 매집/돌파우위' if score >= 65 else ('↘ 분산/하락우위' if score <= 40 else '↔ 중립/눈치')
                return res
                
            except Exception as e:
                print(f"US Whale Error: {e}")
                res['whale_score'] = 50
                return res

    def check_risk_factors(self, news_score=0):
        """
        Phase 24: Advanced Risk Analysis
        1. Short Selling (PyKrx)
        2. Material Exhaustion (News Fade)
        Returns: { 'risk_score': 0-100, 'factors': [], 'short_ratio': 0 }
        """
        import typing
        res: typing.Dict[str, typing.Any] = {'risk_score': 0, 'factors': [], 'short_ratio': 0}
        
        # 1. Short Selling Analysis (KR Only)
        is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ')
        if is_kr and HAS_PYKRX:
            try:
                code = str(self.ticker).split('.')[0]
                end_d = datetime.now().strftime("%Y%m%d")
                start_d = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
                
                # Fetch Short Volume
                # Columns: [거래량, 매매비중, 거래대금, 공매도거래량, 공매도비중, 공매도거래대금]
                # Pykrx: stock.get_shorting_status_by_date(from, to, ticker)
                df_short = stock.get_shorting_status_by_date(start_d, end_d, code)
                
                if df_short is not None and not df_short.empty:
                    # Check latest short ratio
                    # Column names might be korean: '매매비중' or '비중' depending on version
                    # Usually '비중' is short ratio.
                    # Let's rely on mapping or flexible access.
                    
                    latest_short = df_short.iloc[-1]
                    # Try to find '비중' or 'ShortRatio'
                    short_ratio = 0
                    if '비중' in latest_short: short_ratio = latest_short['비중']
                    elif '매매비중' in latest_short: short_ratio = latest_short['매매비중']
                    
                    res['short_ratio'] = short_ratio
                    
                    if short_ratio > 15.0:
                        res['risk_score'] += 30
                        res['factors'].append(f"⚠️ 공매도 과열 ({short_ratio:.1f}%)")
                    elif short_ratio > 10.0:
                        res['risk_score'] += 15
                        res['factors'].append(f"⚠️ 공매도 주의 ({short_ratio:.1f}%)")
                        
                    # Check Balance Increase? (Requires 'get_shorting_balance_by_date' - slower)
            except Exception as e:
                pass
                
        # 2. News Fade (Material Exhaustion)
        # Condition: News is Good (> 0.3) BUT Price is falling (Last 3 days < -2%)
        # Or: Massive Volume Spike 2 days ago + Price Drop now (Exhaustion)
        if news_score > 0.3:
            if self.df is not None and len(self.df) > 3:
                price_3d_chg = (self.df['Close'].iloc[-1] - self.df['Close'].iloc[-4]) / self.df['Close'].iloc[-4]
                if price_3d_chg < -0.02:
                    res['risk_score'] += 20
                    res['factors'].append("📉 재료 소진 의심 (호재에도 하락)")
                    
        # 3. Technical Overheating (RSI > 80)
        if self.df is not None:
            rsi = self.df['RSI'].iloc[-1]
            if rsi > 80:
                res['risk_score'] += 10
                res['factors'].append(f"🔥 기술적 과열 (RSI {rsi:.0f})")
                
        return res

    def check_earnings_risk(self):
        """
        Check if earnings are within next 3 days (US only).
        Drops stocks to avoid binary event gap-downs.
        """
        is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ') or str(self.ticker).isdigit()
        if is_kr:
            return False
            
        try:
            import yfinance as yf
            import datetime
            t = yf.Ticker(self.ticker)
            d = t.get_earnings_dates(limit=2)
            if d is not None and not d.empty:
                now = datetime.datetime.now(datetime.timezone.utc)
                for ts in d.index:
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.timezone.utc)
                    diff = (ts - now).days
                    if 0 <= diff <= 3:
                        return True
        except Exception:
            pass
        return False

    def get_sector_performance(self):
        """
        Analyze Sector Relative Strength using PyKrx (KR) or yfinance (US).
        Returns: { 'sector': str, 'is_leader': bool, 'rs_ratio': float }
        """
        res = {'sector': 'Unknown', 'is_leader': False, 'rs_ratio': 1.0}
        
        # Only implemented for Korean Market (PyKrx) for Phase 22
        is_kr = str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ')
        if not is_kr or not HAS_PYKRX: return res
        
        try:
            # 1. Detect Market & Benchmark (Phase 30: Sector Proxy)
            idx_ticker = self.get_sector_proxy_ticker()
            
            # Fetch Benchmark Data
            if idx_ticker.startswith('^') or idx_ticker.startswith('XL') or idx_ticker.endswith('.KS') or idx_ticker.endswith('.KQ'): 
                 df_idx = yf.Ticker(idx_ticker).history(period="3mo")
                 if df_idx is None or df_idx.empty: return res
                 idx_close = df_idx['Close']
            else: # KR Ticker (PyKrx fallback)
                 market = "KOSPI" if str(self.ticker).endswith('.KS') else "KOSDAQ"
                 idx_ticker = "1001" if market == "KOSPI" else "2001"
                 today = datetime.now().strftime("%Y%m%d")
                 date_s = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
                 df_idx = stock.get_index_ohlcv_by_date(date_s, today, idx_ticker)
                 if df_idx is None or df_idx.empty: return res
                 idx_close = df_idx['종가']
                 
            # Align Timeframes (Last 20 days)
            if len(self.df) < 21 or len(idx_close) < 21: return res
            
            # Use dataframes with shared index if possible, but for speed just use tails
            # Note: Dates might slight mismatch, but for RS it's acceptable approximation
            
            stock_p = self.df['Close'].iloc[-20:]
            bench_p = idx_close.iloc[-20:]
            
            if len(stock_p) != len(bench_p):
                # Simple alignment by length
                min_len = min(len(stock_p), len(bench_p))
                stock_p = stock_p.iloc[-min_len:]
                bench_p = bench_p.iloc[-min_len:]
                
            # --- RRG Calculation (Phase 30) ---
            # 1. RS-Ratio: (Stock / Benchmark) normalized
            # Normalized to starting point (100)
            s_norm = (stock_p / stock_p.iloc[0]) * 100
            b_norm = (bench_p / bench_p.iloc[0]) * 100
            
            rs_series = (s_norm / b_norm) * 100
            
            # 2. RS-Momentum: ROC of RS-Ratio
            # Momentum is rate of change of the ratio
            rs_mom = rs_series.pct_change(5) * 100 + 100 # Center at 100
            
            current_rs = rs_series.iloc[-1]
            current_mom = rs_mom.iloc[-1]
            if np.isnan(current_mom): current_mom = 100
            
            # 3. Determine Quadrant
            # Leading: RS > 100, Mom > 100
            # Improving: RS < 100, Mom > 100 (Target)
            # Weakening: RS > 100, Mom < 100
            # Lagging: RS < 100, Mom < 100
            
            quadrant = "Lagging"
            if current_rs > 100 and current_mom > 100: quadrant = "Leading"
            elif current_rs < 100 and current_mom > 100: quadrant = "Improving"
            elif current_rs > 100 and current_mom < 100: quadrant = "Weakening"
            
            res['sector'] = idx_ticker
            res['rs_ratio'] = round(current_rs, 2)
            res['rs_mom'] = round(current_mom, 2)
            res['quadrant'] = quadrant
            res['is_leader'] = quadrant in ['Leading', 'Improving']
            
            return res
            
        except Exception as e:
            # print(f"Sector RS Error: {e}")
            return res

    def get_sector_proxy_ticker(self):
        """Map Stock Sector to ETF/Index Ticker"""
        default_idx = "^GSPC"
        
        # Check if US
        is_us = not (str(self.ticker).endswith('.KS') or str(self.ticker).endswith('.KQ'))
        if not is_us:
            try:
                import sys, os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
                from sector_analysis import SectorRotation, SECTOR_ETFS
                sr = SectorRotation()
                sector_name = sr.get_ticker_sector_dynamic(self.ticker, self.df)
                if sector_name in SECTOR_ETFS:
                    return SECTOR_ETFS[sector_name]
            except Exception:
                pass
            return "1001" if str(self.ticker).endswith('.KS') else "2001"
        
        
        try:
            # Fetch info if not already
            t = yf.Ticker(self.ticker)
            info = t.info
            sector = info.get('sector', '')
            
            # US Sector Map (SPDR ETFs)
            sector_map = {
                'Technology': 'XLK',
                'Financial Services': 'XLF',
                'Healthcare': 'XLV',
                'Consumer Cyclical': 'XLY',
                'Industrials': 'XLI',
                'Energy': 'XLE',
                'Utilities': 'XLU',
                'Consumer Defensive': 'XLP',
                'Basic Materials': 'XLB',
                'Real Estate': 'XLRE',
                'Communication Services': 'XLC'
            }
            return sector_map.get(sector, default_idx)
        except:
             return default_idx

    def get_market_regime(self):
        """
        Phase 32: Market Regime Detection (The 'Weather' Station)
        Returns: 
        - status: [RISK_ON | NEUTRAL | RISK_OFF | CRASH]
        - score: 0-100 (Market Health)
        - details: Dict with VIX, Trend, Breadth
        """
        try:
            # 1. Fetch VIX (Fear)
            end = datetime.now()
            start = end - timedelta(days=365)
            
            # VIX & Index - Fetch individually for thread safety
            market_ticker = "^KS11" if ".KS" in self.ticker or ".KQ" in self.ticker else "SPY"
            
            vix_obj = yf.Ticker('^VIX')
            vix_h = vix_obj.history(start=start)
            if vix_h.index.tz is not None:
                vix_h.index = vix_h.index.tz_localize(None)
            vix_series = vix_h['Close'] if not vix_h.empty else pd.Series()
            
            mkt_obj = yf.Ticker(market_ticker)
            mkt_h = mkt_obj.history(start=start)
            if mkt_h.index.tz is not None:
                mkt_h.index = mkt_h.index.tz_localize(None)
            idx_series = mkt_h['Close'] if not mkt_h.empty else pd.Series()
            
            # Latest Values
            vix = vix_series.iloc[-1]
            idx_price = idx_series.iloc[-1]
            
            # 2. Index Trend (MA200)
            ma200 = idx_series.rolling(200).mean().iloc[-1]
            uptrend = idx_price > ma200
            
            # 3. Determine Regime
            regime = "NEUTRAL"
            score = 50
            
            if vix > 30:
                regime = "CRASH"
                score = 10
            elif vix > 20:
                if not uptrend:
                    regime = "RISK_OFF" # Fear + Downtrend
                    score = 30
                else:
                    regime = "NEUTRAL" # Fear but Uptrend (Correction?)
                    score = 50
            elif vix < 20:
                if uptrend:
                    regime = "RISK_ON" # Calm + Uptrend
                    score = 90
                else:
                    regime = "NEUTRAL" # Calm but Downtrend (Boring)
                    score = 60
                    
            return {
                'status': regime,
                'score': score,
                'vix': vix,
                'trend': 'Up' if uptrend else 'Down'
            }
            
        except Exception as e:
            print(f"Regime Error: {e}")
            return {'status': 'NEUTRAL', 'score': 50, 'vix': 0, 'trend': 'Unknown'}


    def calculate_antigravity_score(self, win_rate, profit_factor, ai_return, whale_score=0, rs_score=0, macro_status='RISK_ON', sector_data=None, nlp_score=None):
        """
        [Phase 15] Antigravity Score - Universal 100-point Assessment with Death Penalties
        
        Merge all AI, Backtest, Technical, Whale, and Sector components.
        Applies fatal -30 point penalties for Traps (Wicks) and Extreme Overbought indicators.
        """
        # Backward-compatible regime normalization:
        # legacy callers sometimes pass BULL/BEAR/BOX/CRASH.
        regime_alias = {
            'BULL': 'RISK_ON',
            'BEAR': 'RISK_OFF',
            'BOX': 'NEUTRAL',
            'NORMAL': 'NEUTRAL',
            'CAUTION': 'NEUTRAL',
        }
        macro_status = regime_alias.get(macro_status, macro_status)

        w = {
            'tech': 0.45,
            'backtest': 0.25,
            'ai': 0.00,
            'whale': 0.25,
            'sector': 0.05,
            'ml': 0.00
        }
        
        score_cap = 100

        # 2. Calculate Component Scores (0-100 Base)
        tech_score_raw = 0
        if self.df is not None and 'Alpha_Score' in self.df.columns:
            raw_val = self.df['Alpha_Score'].iloc[-1]
            tech_score_raw = raw_val if pd.notna(raw_val) else 0
        s_tech = tech_score_raw
        
        s_backtest = min(100, (win_rate * 100) + (min(3, profit_factor)/3 * 50))
        s_ai = min(100, max(0, ai_return * 5))
        s_whale = whale_score
        
        s_sector = 50
        if sector_data:
            quad = sector_data.get('quadrant', 'Lagging')
            if quad == 'Leading': s_sector = 100
            elif quad == 'Improving': s_sector = 80
            elif quad == 'Weakening': s_sector = 40
            else: s_sector = 20
            if sector_data.get('rs_mom', 100) > 100: s_sector = min(100, s_sector + 10)

        s_ml = 0 
        
        active_w_ai = w['ai'] if ai_return != 0 else 0
        w_sum = w['tech'] + w['backtest'] + active_w_ai + w['whale'] + w['sector'] + w['ml']
        
        # 3. Base Weighted Score (same as V30)
        base_score = (
            (s_tech * w['tech']) +
            (s_backtest * w['backtest']) +
            (s_ai * active_w_ai) +
            (s_whale * w['whale']) +
            (s_sector * w['sector']) +
            (s_ml * w['ml'])
        )
        
        if w_sum > 0:
            base_score = base_score / w_sum

        # =============================================
        # [V31 NEW] CATALYST BONUS SCORING
        # Event-driven bonuses: max +25, penalties: max -15
        # This creates wider score distribution for better discrimination
        # =============================================
        catalyst_bonus = 0
        
        if self.df is not None and len(self.df) >= 20:
            close = self.df['Close']
            
            # --- DEATH PENALTY 1: Extreme Overbought (RSI >= 75) ---
            if 'RSI' in self.df.columns:
                rsi = self.df['RSI'].iloc[-1]
                if rsi >= 75:
                    catalyst_bonus -= 30  # Fatal penalty
                elif rsi > 70:
                    catalyst_bonus -= 10
                
                rsi_prev = self.df['RSI'].iloc[-2] if len(self.df) > 1 else rsi
                if rsi_prev < 30 and rsi > rsi_prev:
                    catalyst_bonus += 8  # RSI oversold bounce
                    
            # --- PENALTY 2: Fake Breakout / Bull Trap (Dynamic Penalty) ---
            body = abs(close.iloc[-1] - self.df['Open'].iloc[-1]) or 0.001
            upper_wick = self.df['High'].iloc[-1] - max(close.iloc[-1], self.df['Open'].iloc[-1])
            if upper_wick > body * 1.5 and close.iloc[-1] > self.df['Open'].iloc[-1]:
                # Dynamic severity: -11 to -25 depending on wick size, instead of blunt -30
                severity_ratio = min(5.0, upper_wick / body)
                dynamic_penalty = 5 + (severity_ratio * 4)
                catalyst_bonus -= dynamic_penalty
            
            # --- CATALYST 2: MACD Golden Cross within 3 days (+8) ---
            macd_signal_col = None
            if 'MACD_Signal' in self.df.columns:
                macd_signal_col = 'MACD_Signal'
            elif 'MACD_signal' in self.df.columns:
                macd_signal_col = 'MACD_signal'

            if 'MACD' in self.df.columns and macd_signal_col:
                macd = self.df['MACD'].iloc[-3:]
                signal = self.df[macd_signal_col].iloc[-3:]
                for i in range(max(0, len(macd)-3), len(macd)):
                    try:
                        if i > 0 and macd.iloc[i] > signal.iloc[i] and macd.iloc[i-1] <= signal.iloc[i-1]:
                            catalyst_bonus += 8
                            break
                    except:
                        pass
            
            # --- CATALYST 3: Bollinger Band Bounce (+6) ---
            if 'BBL_20_2.0' in self.df.columns:
                bb_lower = self.df['BBL_20_2.0'].iloc[-1]
                prev_close = close.iloc[-2] if len(close) > 1 else close.iloc[-1]
                curr_close = close.iloc[-1]
                # Price touched lower band then bounced
                if pd.notna(bb_lower) and prev_close <= bb_lower * 1.01 and curr_close > bb_lower:
                    catalyst_bonus += 6
            
            # --- CATALYST 4: Volume Surge (+5) ---
            if 'Volume' in self.df.columns:
                vol = self.df['Volume'].iloc[-1]
                vol_avg = self.df['Volume'].rolling(20).mean().iloc[-1]
                if pd.notna(vol_avg) and vol_avg > 0 and vol / vol_avg >= 2.0:
                    catalyst_bonus += 5  # 2x volume = strong confirmation
            
            # --- CATALYST 5: MA_20 Support Hold (+4) ---
            if 'MA_20' in self.df.columns:
                ma20 = self.df['MA_20'].iloc[-1]
                curr = close.iloc[-1]
                prev = close.iloc[-2] if len(close) > 1 else curr
                # Price bounced off MA_20 support
                if pd.notna(ma20) and prev <= ma20 * 1.01 and curr > ma20:
                    catalyst_bonus += 4
                # Price far below MA_20 and MA_50 = momentum penalty
                if 'MA_50' in self.df.columns:
                    ma50 = self.df['MA_50'].iloc[-1]
                    if pd.notna(ma20) and pd.notna(ma50) and curr < ma20 * 0.95 and curr < ma50 * 0.95:
                        catalyst_bonus -= 10  # Strong downtrend penalty
            
            # --- CATALYST 6: 52-Week High Proximity (+3 or -3) ---
            try:
                high_52w = close.rolling(min(252, len(close))).max().iloc[-1]
                proximity = curr_close / high_52w if high_52w > 0 else 0
                if proximity >= 0.95:
                    catalyst_bonus += 3  # Near 52-week high = momentum
                elif proximity <= 0.60:
                    catalyst_bonus -= 5  # 40%+ drop from high = danger
            except:
                pass
                
            # --- CATALYST 7: NLP News Sentiment (+15 to -15) ---
            if nlp_score is None:
                try:
                    import sys, os
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from naver_news_scraper import NaverNewsScraper
                    scraper = NaverNewsScraper()
                    nlp_data = scraper.get_news_sentiment(self.ticker)
                    nlp_score = nlp_data.get('score', 0)
                except Exception as e:
                    if "API_RATE_LIMIT_429" in str(e):
                        print(f"⏳ Naver News Rate Limit for {self.ticker}. Waiting 15s...")
                        time.sleep(15)
                    # Graceful fallback: NLP score = 0 (no news impact)
                    nlp_score = 0
            
            catalyst_bonus += nlp_score

        # --- CATALYST 8: Whale / Supply-Demand Explicit Bonus & Penalty ---
        # whale_score already enters via base weighted formula (weight 0.25),
        # but explicit thresholds create stronger signal discrimination.
        if whale_score >= 70:
            catalyst_bonus += 8   # Strong institutional conviction
        elif whale_score >= 60:
            catalyst_bonus += 5   # Solid institutional support
        elif whale_score <= 25:
            catalyst_bonus -= 15  # Active retail dumping / distribution
        elif whale_score <= 35:
            catalyst_bonus -= 8   # Retail-dominated, weak supply

        # Cap catalyst bonus (Allow deeper penalties for Death Penalty)
        catalyst_bonus = max(-60, min(25, catalyst_bonus))
        
        # 4. Final Score = Base + Catalyst
        final_score = base_score + catalyst_bonus
        
        # 5. Apply Market Regime Multiplier
        regime_multiplier = {
            'CRASH': 0.30,
            'RISK_OFF': 0.70,
            'NEUTRAL': 1.00,
            'RISK_ON': 1.15
        }
        mult = regime_multiplier.get(macro_status, 1.0)
        final_score = final_score * mult
        
        if macro_status == 'CRASH':
            score_cap = 50
            
        # 6. Safety Floor/Ceiling
        final_score = min(int(score_cap), max(0, int(final_score)))
        return int(final_score)

    def calculate_alpha_score_v30(self, win_rate, profit_factor, ai_return, whale_score=0, rs_score=0, macro_status='RISK_ON', sector_data=None, nlp_score=None):
        """Compatibility shim for legacy callers.

        Older paths (notably auto_bot.py) still reference calculate_alpha_score_v30.
        Route to the maintained antigravity score implementation without changing
        legacy call sites immediately.
        """
        return self.calculate_antigravity_score(
            win_rate=win_rate,
            profit_factor=profit_factor,
            ai_return=ai_return,
            whale_score=whale_score,
            rs_score=rs_score,
            macro_status=macro_status,
            sector_data=sector_data,
            nlp_score=nlp_score,
        )


    def calculate_alpha_score(self, win_rate, profit_factor, ai_return, whale_score=0, rs_score=0, macro_status='RISK_ON', sector_data=None):
        """
        Calculate Comprehensive AI Alpha Score (0-100) (Legacy / Deep Dive)
        Weights (Phase 6 ML Integrated & Phase 22 Sector Upgrade):
        - Technical (Trend/RSI/Vol): 20%
        - Supply/Demand (Whale): 20%
        - ML Probability: 20%
        - AI Forecast (Prophet): 15%
        - Backtest Stats: 15%
        - Sector/Market RS: 10%
        
        Macro Gating: If RISK_OFF, Cap Max Score at 75.
        """
        # 1. Technical Score (Base 20 pts)
        tech_score_raw = 0
        if self.df is not None and 'Alpha_Score' in self.df.columns:
            tech_score_raw = self.df['Alpha_Score'].iloc[-1]
        
        score_tech = (tech_score_raw / 100.0) * 20
        
        # 2. Backtest Performance (15 pts)
        score_wr = min(10, (win_rate * 100) * 0.2) 
        score_pf = 0
        try:
            effective_pf = min(3.0, profit_factor)
            score_pf = (effective_pf / 3.0) * 5
        except: pass
        
        score_backtest = score_wr + score_pf
        
        # 3. AI Prophet Prediction (15 pts)
        score_ai = 0
        if ai_return > 0:
            score_ai = min(15, ai_return * 2) 
            
        # 4. Whale (Su-geup) Score (20 pts)
        score_whale = (whale_score / 100.0) * 20
        
        # 5. Relative Strength (RS) Score (10 pts)
        
        score_rs_base = (rs_score / 100.0) * 5 # Reduced base weight
        score_sector = 0
        
        if sector_data:
            # If Leader: +5 pts
            if sector_data.get('is_leader'): score_sector += 5
            # If RS Ratio positive: + up to 5 pts
            ratio = sector_data.get('rs_ratio', 0)
            if ratio > 0: score_sector += min(5, ratio) # Cap at 5
            
        score_rs_final = score_rs_base + score_sector
        
        # 6. ML Probability Score (20 pts)
        ml_data = self.get_ml_prediction()
        prob = ml_data.get('prob', 50)
        # 50% = 0, 100% = 20pts. (prob - 50) * 0.4
        score_ml = max(0, (prob - 50) * 0.4)
        
        final_score = score_tech + score_backtest + score_ai + score_whale + score_rs_final + score_ml
        
        # --- MACRO SAFETY LATCH ---
        if macro_status == 'RISK_OFF':
            final_score = min(final_score, 75)
        
        return min(100, int(final_score))

    def get_macro_metrics(self):
        """
        Fetch Global/Local Macro Metrics for Gating Logic.
        Returns: Dict { 'vix': float, 'usd_krw': float, 'status': 'RISK_ON'|'RISK_OFF' }
        """
        res = {'vix': 0, 'usd_krw': 0, 'status': 'RISK_ON'}
        
        try:
            # 1. Fetch VIX (Fear Index)
            vix = get_history("^VIX", period="5d", interval="1d")
            if not vix.empty:
                res['vix'] = vix['Close'].iloc[-1]
                
            # 2. Fetch USD/KRW (Exchange Rate)
            # Code: KRW=X
            ex = get_history("KRW=X", period="5d", interval="1d")
            if not ex.empty:
                res['usd_krw'] = ex['Close'].iloc[-1]
                
            # 3. Determine Regime Status
            # Criteria: VIX > 25 OR USD/KRW > 1420 (Crisis Level)
            is_high_vix = res['vix'] > 25
            is_high_forex = res['usd_krw'] > 1420
            
            if is_high_vix or is_high_forex:
                res['status'] = 'RISK_OFF'
                
            return res
            
        except Exception as e:
            print(f"Macro Data Error: {e}")
            return res

    def get_relative_strength(self):
        """
        Calculate Relative Strength (RS) vs Benchmark (Phase 4).
        Returns: Dict { 'rs_ratio': float, 'period': '20d', 'is_leader': bool, 'score': int }
        """
        res = {'rs_ratio': 1.0, 'is_leader': False, 'score': 0}
        
        try:
            # 1. Identify Benchmark
            if str(self.ticker).endswith('.KS'):
                bench_ticker = "^KS11" # KOSPI
            elif str(self.ticker).endswith('.KQ'):
                bench_ticker = "^KQ11" # KOSDAQ
            else:
                bench_ticker = "^GSPC" # S&P 500
            
            # 2. Get Data (Last 25 days to be safe for 20d calc)
            # We use self.df for stock (already loaded)
            if self.df is None or len(self.df) < 25:
                return res
                
            # Fetch Benchmark
            bench = get_history(bench_ticker, period="1mo", interval="1d")
            if len(bench) < 20: 
                return res
            
            # 3. Calculate Returns (20 Days)
            # Stock Return
            s_now = self.df['Close'].iloc[-1]
            s_prev = self.df['Close'].iloc[-20]
            s_ret = (s_now - s_prev) / s_prev
            
            # Market Return
            m_now = bench['Close'].iloc[-1]
            m_prev = bench['Close'].iloc[-20] # approx match
            m_ret = (m_now - m_prev) / m_prev
            
            # 4. Calculate RS Ratio
            # Logic: Avoid div by zero. If m_ret is near flat, use specific logic?
            # Standard RS: (1 + s_ret) / (1 + m_ret)
            rs_ratio = (1 + s_ret) / (1 + m_ret)
            
            res['rs_ratio'] = round(rs_ratio, 2)
            res['is_leader'] = rs_ratio > 1.05 # Outperforming by 5% margin
            
            # 5. Calculate Score (0-100 scale for consistency, weighted later)
            # > 1.0 = 50pts. > 1.1 = 80pts. < 1.0 = 20pts.
            if rs_ratio > 1.1: score = 100
            elif rs_ratio > 1.05: score = 80
            elif rs_ratio > 1.0: score = 60
            elif rs_ratio > 0.95: score = 40
            else: score = 20
            
            res['score'] = score
            return res

        except Exception as e:
            print(f"RS Error: {e}")
            return res

    def calculate_trailing_stop(self, atr_mult=3.0):
        """
        Phase 30: Smart Exit Simulation (ATR Trailing Stop)
        Returns: { 'stop_price': float, 'status': 'HOLD'|'SELL', 'risk_reward': float }
        """
        res = {'stop_price': 0, 'status': 'UNKNOWN'}
        if self.df is None or 'ATR' not in self.df.columns: return res
             
        current_price = self.df['Close'].iloc[-1]
        atr = self.df['ATR'].iloc[-1]
        
        # Simulation: Assume entry was 20 days ago (Typical Swing Hold)
        # Find Max High in last 20 days to adjust trailing stop
        window = 20
        if len(self.df) < window: window = len(self.df)
        
        highest_high = self.df['High'].iloc[-window:].max()
        stop_price = highest_high - (atr * atr_mult)
        
        status = "🔴 SELL (Exit)" if current_price < stop_price else "🟢 HOLD"
        
        return {
            'stop_price': round(stop_price, 2),
            'current_price': round(current_price, 2),
            'highest_high': round(highest_high, 2),
            'status': status,
            'atr': round(atr, 2)
        }

    def analyze_supply_demand(self):
        """
        Analyze 'Whale' Activity (Institutional/Smart Money).
        Returns: Dict { 'whale_score': int, 'signal': 'BUY'|'SELL'|'NEUTRAL' }
        """
        res = {'whale_score': 50, 'signal': 'NEUTRAL'}
        if self.df is None or len(self.df) < 20: return res
        
        try:
            # 1. Korean Stocks (PyKrx) - Real Investor Data
            if HAS_PYKRX and ".KS" in str(self.ticker) or ".KQ" in str(self.ticker):
                # Fetch recent 5 days investor data
                 try:
                    ticker_code = str(self.ticker).split('.')[0]
                    # This is slow, so maybe catch timeout/errors
                    # Simply using price/volume proxy for now to ensure speed
                    pass 
                 except: pass

            # 2. Universal Logic (Volume Analysis)
            # Accumulation Distribution Line (ADL) concept approximation
            # If Close > Open and Volume > Avg*1.5 -> Whale Buying
            
            recent = self.df.tail(10)
            avg_vol = self.df['Volume'].rolling(20).mean().iloc[-1]
            
            score = 50
            for i, row in recent.iterrows():
                # Big Candle Analysis
                if row['Volume'] > avg_vol * 1.5:
                    if row['Close'] > row['Open']:
                        score += 5 # Accumulation
                    else:
                        score -= 5 # Distribution
            
            # VWAP Logic (Price accepted above average?)
            # Simplified: Is price above 20d VWAP?
            # VWAP = Sum(P*V) / Sum(V)
            vwap = (self.df['Close'] * self.df['Volume']).rolling(20).sum() / self.df['Volume'].rolling(20).sum()
            if self.df['Close'].iloc[-1] > vwap.iloc[-1]:
                score += 10
            else:
                score -= 10
                
            res['whale_score'] = max(0, min(100, score))
            res['signal'] = "BUY" if score > 60 else "SELL" if score < 40 else "NEUTRAL"
            
            return res
            
        except Exception as e:
            print(f"Whale Analysis Error: {e}")
            return res

    def detect_pre_surge_signals(self):
        """
        Phase 12: Detect 'Pre-Surge' patterns (Leading Indicators).
        Returns: Dict { 'is_pre_surge': bool, 'type': 'SQUEEZE'|'PULLBACK'|'OBV_DIV', 'score': int }
        """
        import typing
        res: typing.Dict[str, typing.Any] = {'is_pre_surge': False, 'type': None, 'score': 0, 'details': [], 'strategy_type': 'Wait'}
        strategies = []
        if self.df is None or len(self.df) < 50: return res
        
        try:
            latest = self.df.iloc[-1]
            prev = self.df.iloc[-2]
            
            # 1. Volatility Squeeze (Bollinger Band Width)
            # Band Width = (Upper - Lower) / Middle
            # If Band Width is at 6-month low, it's a squeeze.
            
            # Calculate Band Width if not exists
            if 'BBU_20_2.0' in self.df.columns and 'BBL_20_2.0' in self.df.columns:
                u = self.df['BBU_20_2.0']
                l = self.df['BBL_20_2.0']
                m = self.df['BBM_20_2.0']
                self.df['BB_Width'] = (u - l) / m
                
                # Check recent 20 days min vs history
                current_width = self.df['BB_Width'].iloc[-1]
                min_6m = self.df['BB_Width'].tail(120).min()
                
                if current_width <= min_6m * 1.1: # Within 10% of 6m low
                    res['score'] += 30
                    res['details'].append("Volatility Squeeze (Energy Coiling)")
                    if res['score'] >= 30: res['type'] = 'SQUEEZE'

            # 2. Golden Pullback (Nulim-mok)
            # MA50 is rising (Trend Up) AND Price is near MA50 AND RSI < 45
            ma50_slope = False
            near_ma50 = False
            rsi_cool = False
            if 'MA_50' in self.df.columns and 'MA_50' in latest.index and 'RSI' in latest.index:
                ma50_now = self.df['MA_50'].iloc[-1]
                ma50_prev = self.df['MA_50'].iloc[-5]
                latest_ma50 = latest['MA_50']
                latest_rsi = latest['RSI']
                if pd.notna(ma50_now) and pd.notna(ma50_prev) and pd.notna(latest_ma50) and pd.notna(latest_rsi) and latest_ma50 not in (0, 0.0):
                    ma50_slope = (ma50_now - ma50_prev) > 0
                    near_ma50 = abs(latest['Close'] - latest_ma50) / latest_ma50 < 0.03  # Within 3%
                    rsi_cool = latest_rsi < 45

            if ma50_slope and near_ma50 and rsi_cool:
                res['score'] += 40
                res['details'].append("Golden Pullback (MA50 Support + RSI Dip)")
                res['type'] = 'PULLBACK'
                
            # 3. Hidden Accumulation (OBV Divergence) - "Flat Price, Rising OBV"
            # Price (Last 10 days) is Down/Flat, but OBV is Up
            price_change_10d = (latest['Close'] - self.df['Close'].iloc[-10]) / self.df['Close'].iloc[-10]
            
            # Calc OBV if missing
            if 'OBV' not in self.df.columns:
                import pandas_ta_classic as ta
                self.df['OBV'] = ta.obv(self.df['Close'], self.df['Volume'])
                
            obv_change_10d = (self.df['OBV'].iloc[-1] - self.df['OBV'].iloc[-10])
            
            # Divergence A: Hidden Accumulation (Trend Continuation or Reversal)
            if price_change_10d < -0.02 and obv_change_10d > 0:
                res['score'] += 50
                res['details'].append("OBV Divergence (Hidden Accumulation)")
                res['type'] = 'OBV_DIV'
                strategies.append('REVERSAL')
            elif price_change_10d < 0.01 and obv_change_10d > 0: # Flat price
                 res['score'] += 30
                 res['details'].append("OBV Accumulation (Flat Price)")
                 strategies.append('MOMENTUM')

            # --- Phase 17 New Logic ---
            # 4. RSI Divergence (Bullish) - "Lower Price, Higher RSI"
            # Lookback 15 days window
            window = 15
            if len(self.df) > window and 'RSI' in self.df.columns:
                prices = self.df['Close'].tail(window)
                rsis = self.df['RSI'].tail(window)
                
                # Check Local Mins
                p_min_idx = prices.idxmin()
                r_min_idx = rsis.idxmin()
                
                # Current Price is near Low, but current RSI is significantly higher than Min RSI
                # Logic: Current Price < Prev Low (or near), Current RSI > Prev Low RSI
                # A robust pivot detection is complex, so we use a simplified "Trend Divergence"
                
                price_trend = (prices.iloc[-1] - prices.iloc[0]) 
                rsi_trend = (rsis.iloc[-1] - rsis.iloc[0])
                
                # Divergence: Price Down substantially, RSI Flat or Up
                if price_trend < -0.05 and rsi_trend > -2: # Price dropped 5%, RSI held
                    res['score'] += 40
                    res['details'].append(f"RSI Divergence (Price Drop {price_trend:.1%}, RSI Held)")
                    res['type'] = 'RSI_DIV'
                    strategies.append('REVERSAL')

            # 5. Stochastic Hook (Oversold Bounce)
            if 'Stoch_K' in self.df.columns and 'Stoch_D' in self.df.columns:
                k = self.df['Stoch_K'].iloc[-1]
                d = self.df['Stoch_D'].iloc[-1]
                prev_k = self.df['Stoch_K'].iloc[-2]
                prev_d = self.df['Stoch_D'].iloc[-2]
                
                # Hook: Cross Up in Oversold Zone (< 20)
                if k < 25 and d < 25:
                    if prev_k < prev_d and k > d: # Golden Cross
                        res['score'] += 30
                        res['details'].append("Stochastic Hook (Oversold Bounce)")
                        strategies.append('REVERSAL')


            # Final Decision
            if res['score'] >= 50:
                res['is_pre_surge'] = True
                
            # Determine Dominant Strategy
            if 'REVERSAL' in strategies:
                res['strategy_type'] = 'REVERSAL' # Catch the bottom
            elif 'MOMENTUM' in strategies:
                 res['strategy_type'] = 'MOMENTUM'
            else:
                res['strategy_type'] = 'WAIT' # Weak signal

            return res

        except Exception as e:
            print(f"Pre-Surge Logic Error: {e}")
            return res

    @staticmethod
    def detect_market_regime(market_type='KR'):
        """
        [Phase 4] Detect overall market regime using index MA20 vs MA50.
        Returns: dict with regime ('BULL', 'NEUTRAL', 'BEAR'), emoji, and description.
        """
        try:
            key = str(market_type or "KR").upper()
            candidate_map = {
                'KR': ['^KS11'],
                'KOSPI': ['^KS11'],
                'KOSDAQ': ['^KQ11'],
                'US': ['^GSPC'],
                'NASDAQ': ['^IXIC', '^GSPC'],
                'S&P500': ['^GSPC', '^IXIC'],
                'AMEX': ['^XAX', '^IXIC', '^GSPC'],
            }
            candidates = candidate_map.get(key, ['^KS11'])
            hist = None
            for index_ticker in candidates:
                fetched = get_history(index_ticker, period='6mo', interval='1d')
                if fetched is None or fetched.empty or 'Close' not in fetched.columns:
                    continue
                valid_close = pd.to_numeric(fetched['Close'], errors='coerce').dropna()
                if len(valid_close) >= 50:
                    hist = fetched.loc[valid_close.index].copy()
                    break
            
            if hist is None or hist.empty or len(hist) < 50:
                return {'regime': 'NEUTRAL', 'emoji': '🟡', 'desc': '데이터 부족'}
            
            close = pd.to_numeric(hist['Close'], errors='coerce').dropna()
            if len(close) < 50:
                return {'regime': 'NEUTRAL', 'emoji': '🟡', 'desc': '데이터 부족'}
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1]
            current = close.iloc[-1]
            
            # Regime logic
            if current > ma20 > ma50:
                regime = 'BULL'
                emoji = '🟢'
                desc = f'상승장 (현재>{ma20:.0f}>{ma50:.0f})'
            elif current < ma20 < ma50:
                regime = 'BEAR'
                emoji = '🔴'
                desc = f'하락장 (현재<{ma20:.0f}<{ma50:.0f})'
            elif current > ma50:
                regime = 'NEUTRAL'
                emoji = '🟡'
                desc = f'횡보 (MA20과 MA50 사이)'
            else:
                regime = 'BEAR'
                emoji = '🔴'
                desc = f'약세 (현재<MA50)'
            
            return {'regime': regime, 'emoji': emoji, 'desc': desc}
            
        except Exception as e:
            print(f"Regime Detection Error: {e}")
            return {'regime': 'NEUTRAL', 'emoji': '🟡', 'desc': 'Error'}

    def get_real_trend(self):
        """
        [BUG-2 FIX] Return actual price trend based on Moving Averages.
        UP: MA20 > MA50 (bullish structure)
        DOWN: MA20 < MA50 (bearish structure)
        NEUTRAL: Within 1% of each other (ranging)
        """
        try:
            if self.df is None or len(self.df) < 50:
                return "NEUTRAL"
            
            latest = self.df.iloc[-1]
            ma20 = latest.get('MA_20', None)
            ma50 = latest.get('MA_50', None)
            
            if ma20 is None or ma50 is None or pd.isna(ma20) or pd.isna(ma50) or ma50 == 0:
                return "NEUTRAL"
            
            ratio = float(ma20) / float(ma50)
            
            if ratio > 1.01:
                return "UP"
            elif ratio < 0.99:
                return "DOWN"
            else:
                return "NEUTRAL"
        except Exception:
            return "NEUTRAL"

    def get_price_position(self):
        """
        Classify Current Position: Bottom / Rising / Peak
        Returns: str
        """
        try:
            if self.df is None or len(self.df) < 20: return "Unknown"
            
            latest = self.df.iloc[-1]
            rsi = latest['RSI'] if 'RSI' in latest else 50
            
            # BB Position
            bb_status = "Mid"
            if 'BBU_20_2.0' in self.df.columns:
                u = latest['BBU_20_2.0']
                l = latest['BBL_20_2.0']
                if latest['Close'] > u * 0.98: bb_status = "High"
                elif latest['Close'] < l * 1.02: bb_status = "Low"
            
            # Classification
            if rsi < 35 or bb_status == "Low":
                return "📉 바닥 (Bottom)"
            elif rsi > 70 or bb_status == "High":
                return "🌋 고점 (Peak)"
            elif 40 <= rsi <= 70:
                # Up or Down?
                ma20 = latest['MA_20'] if 'MA_20' in latest else 0
                ma50 = latest['MA_50'] if 'MA_50' in latest else 0
                if ma20 > ma50:
                    return "🚀 상승 (Rising)"
                else:
                    return "💤 조정 (Resting)"
            else:
                return "➡️ 중립 (Neutral)"
                
        except Exception as e:
            return "Unknown"

    def get_advanced_regime(self):
        """
        Determine Market Regime: Bull, Bear, or Box (Neutral).
        Returns: Dict { 'status': 'BULL'|'BEAR'|'BOX', 'confidence': 0.0-1.0 }
        """
        try:
            # 1. Fetch Benchmark (KOSPI/S&P500)
            tik = "^GSPC"
            if ".KS" in self.ticker or ".KQ" in self.ticker: tik = "^KS11" # KOSPI
            
            tik_obj = yf.Ticker(tik)
            df_idx = tik_obj.history(period='1y', interval='1d')
            if df_idx.index.tz is not None:
                df_idx.index = df_idx.index.tz_localize(None)
                
            if len(df_idx) < 200: return {'status': 'NEUTRAL', 'confidence': 0.5, 'reason': '데이터 부족'}
            
            curr = df_idx['Close'].iloc[-1]
            ma20 = df_idx['Close'].rolling(20).mean().iloc[-1]
            ma200 = df_idx['Close'].rolling(200).mean().iloc[-1]
            
            # Volatility (StdDev of 20d returns)
            vol = df_idx['Close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
            
            # Logic:
            # BULL: Price > MA20 & MA20 > MA200 (Golden Cross Setup)
            # BEAR: Price < MA20 & MA20 < MA200 (Death Cross Setup)
            # BOX: MA20 ~ MA200 (Flat) & Low Vol
            # CRASH: Price < MA200 & High Vol (>30%)
            
            status = "NEUTRAL"
            conf = 0.5
            reason = "방향성 탐색 중 (Neutral)"
            
            if curr > ma20 and ma20 > ma200:
                status = "BULL"
                conf = 0.8
                reason = "정배열 상승 추세 (Price > 20MA > 200MA)"
            elif curr < ma20 and ma20 < ma200:
                status = "BEAR"
                conf = 0.8
                reason = "역배열 하락 추세 (Price < 20MA < 200MA)"
                if vol > 0.30: 
                    status = "CRASH" # High Panic
                    reason = "공포 장세 (Volatility > 30%)"
            elif abs(ma20 - ma200)/ma200 < 0.05: # < 5% diff
                status = "BOX"
                conf = 0.6
                reason = "이평선 밀집 (횡보 합류)"
                
            return {'status': status, 'confidence': conf, 'volatility': vol, 'reason': reason}
            
        except Exception as e:
            print(f"Regime Check Error: {e}")
            return {'status': 'NEUTRAL', 'confidence': 0.5, 'reason': f'데이터 에러: {e}'}

    def get_realtime_price(self):
        """
        Fetch Real-Time Price from YFinance (Fast Info or Info).
        Fallback to latest DataFrame Close if failing.
        Returns: float price
        """
        try:
            t = yf.Ticker(self.ticker)
            # 1. Try Fast Info (New YFinance API - fast & accurate)
            price = t.fast_info.get('last_price')
            if price is not None and price > 0:
                print(f"⚡ Realtime Price (FastInfo): {price}")
                return price
            
            # 2. Try Standard Info (slower, but comprehensive)
            info = t.info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask')
            if price is not None and price > 0:
                print(f"⚡ Realtime Price (Info): {price}")
                return price
                
            # 3. Fallback to DF
            if self.df is not None and not self.df.empty:
                return self.df['Close'].iloc[-1]
                
            return 0.0
            
        except Exception as e:
            print(f"Realtime Price Error: {e}")
            if self.df is not None and not self.df.empty:
                 return self.df['Close'].iloc[-1]
            return 0.0

    def check_fundamentals(self):
        """
        Quality Factor Check: Revenue Growth & Profitability.
        Returns: (Passed: Bool, Reason: str)
        """
        try:
            t = yf.Ticker(self.ticker)
            info = t.info
            
            # 1. Growth: Revenue Growth (yoy)
            rev_growth = info.get('revenueGrowth', 0)
            
            # 2. Profitability: Margins or ROE
            # margins = info.get('profitMargins', 0)
            roe = info.get('returnOnEquity', 0)
            
            # Logic: Avoid 'Trash' (Negative Growth AND Negative ROE)
            # We are okay with Turnarounds (Low ROE but high Growth) or Cash Cows (Low Growth but high ROE)
            
            if rev_growth is None: rev_growth = 0
            if roe is None: roe = 0
            
            is_trash = (rev_growth < -0.10) and (roe < -0.05)
            
            if is_trash:
                return False, f"Bad Fundamentals (Rev {rev_growth:.1%}, ROE {roe:.1%})"
                
            return True, "Quality OK"
            
        except:
            return True, "No Data (Skip)"
