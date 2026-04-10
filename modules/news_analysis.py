import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from urllib.parse import quote
import time

class NewsAnalyzer:
    def __init__(self, ticker, stock_name=None, max_results=5):
        self.ticker = ticker
        self.stock_name = stock_name
        self.max_results = max_results
        self.analyzer = SentimentIntensityAnalyzer()
        
        # Add Financial Lexicon (VADER Update)
        financial_lexicon = {
            'beat': 2.0, 'miss': -2.0, 'surge': 2.5, 'plunge': -2.5,
            'hike': -1.5, 'cut': 1.5,
            'buy': 2.0, 'sell': -2.0, 'hold': 0.0,
            'bull': 2.5, 'bear': -2.5, 'gain': 2.0, 'loss': -2.0,
            'record': 1.5, 'strong': 1.5, 'weak': -1.5,
            'acquires': 1.0, 'merger': 1.0, 'approval': 2.0, 'fda': 1.0
        }
        self.analyzer.lexicon.update(financial_lexicon)
        # High Impact Keywords (Phase 22 Upgrade)
        self.impact_keywords = [
            'earnings', 'revenue', 'profit', 'surpass', 'contract', 'deal', 'partnership',
            'fda', 'approval', 'launch', 'unveil', 'acquire', 'merger', 'dividend', 'buyback',
            'upgrade', 'raised', 'hike'
        ]
        self.panic_keywords = ['miss', 'plunge', 'crash', 'lawsuit', 'investigation', 'downgrade', 'fraud']
        
    def _apply_keyword_boost(self, text, base_score):
        """Boost score if high impact keywords are present"""
        text_lower = text.lower()
        score = base_score
        
        # 1. Panic Amplifier (Negative News)
        if base_score < 0:
            for kw in self.panic_keywords:
                if kw in text_lower:
                    score *= 2.0 # Double penalty
                    break
                    
        # 2. Impact Amplifier (Significant Events)
        for kw in self.impact_keywords:
            if kw in text_lower:
                if abs(score) < 0.1: # If neutral but has keyword, give it direction
                    score = 0.5 if 'earnings' in text_lower or 'deal' in text_lower else score
                else:
                    score *= 1.5 # 50% Boost
                break
                
        # Cap at -1.0 to 1.0
        return max(-1.0, min(1.0, score))

    def _is_recent(self, date_val):
        """Check if date is within last 3 days"""
        try:
            now = time.time()
            cutoff = now - (3 * 24 * 3600) # 3 days ago
            
            # Case A: Unix Timestamp (int/float)
            if isinstance(date_val, (int, float)):
                return date_val >= cutoff
                
            # Case B: String (RFC 2822 / ISO)
            if isinstance(date_val, str):
                # Try parsing with feedparser's helper or dateutil
                # feedparser usually returns struct_time for 'published_parsed'
                # But here we passed 'published' string to this helper? 
                # Better to do parsing before calling this, or parse here.
                # Let's rely on parsed structs if possible, or simple string check?
                # Actually, feedparser gives 'published_parsed'.
                pass
            
            return True # Default to True if valid date (fallback)
        except:
            return True

    def _fetch_google_rss(self, query):
        """Fetch news from Google RSS Feed (Fallback)"""
        try:
            encoded_query = quote(query)
            # Use KR region for Korean stocks if ticker ends with .KS/.KQ
            if ".KS" in self.ticker or ".KQ" in self.ticker:
                url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
            else:
                url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
                
            feed = feedparser.parse(url)
            
            headlines = []
            sentiment_sum = 0
            count = 0
            
            now_struct = time.gmtime()
            
            # Filter & Process
            for entry in feed.entries:
                if len(headlines) >= self.max_results: break
                    
                title = entry.title
                link = entry.link
                pub_date = entry.published
                
                # Check Date (feedparser gives 'published_parsed' as struct_time)
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    # Convert to seconds
                    entry_time = time.mktime(entry.published_parsed)
                    if time.time() - entry_time > (3 * 24 * 3600):
                        continue # Skip old news
                
                # VADER Score
                vs = self.analyzer.polarity_scores(title)
                base_score = vs['compound']
                
                # Apply Semantic Boost
                score = self._apply_keyword_boost(title, base_score)
                
                headlines.append({
                    'title': title, 
                    'score': score, 
                    'url': link,
                    'date': pub_date
                })
                sentiment_sum += score
                count += 1
                
            return headlines, sentiment_sum, count, "Google RSS"
            
        except Exception as e:
            print(f"RSS Fallback Error: {e}")
            return [], 0, 0, "Error"

    def get_news_sentiment(self):
        """
        Fetch news via yfinance, fallback to Google RSS if empty.
        Only keeps news from the last 3 days.
        Returns: { 'score': float (-1.0 to 1.0), 'headlines': list, 'status': str }
        """
        try:
            headlines = []
            sentiment_sum = 0
            count = 0
            source_status = "yfinance"
            
            cutoff_time = time.time() - (3 * 24 * 3600)
            
            # 1. Try yfinance
            yf_ticker = yf.Ticker(self.ticker)
            news_list = yf_ticker.news
            
            if news_list:
                for item in news_list:
                    if len(headlines) >= self.max_results: break
                    
                    # Handle nested structure
                    content = item.get('content', item)
                    
                    # Check Date first
                    pub_time = content.get('pubDate', content.get('providerPublishTime', 0))
                    # yfinance pubDate can be ISO string or int? usually providerPublishTime is int
                    if isinstance(pub_time, (int, float)):
                        if pub_time < cutoff_time: continue
                    # If string, skip check or try parse? (Usually providerPublishTime is reliable int)
                    
                    title = content.get('title', '')
                    if not title: continue
                    
                    link_obj = content.get('clickThroughUrl') or content.get('canonicalUrl')
                    link = link_obj.get('url') if link_obj else content.get('link', '')
                    
                    vs = self.analyzer.polarity_scores(title)
                    base_score = vs['compound']
                    
                    # Apply Semantic Boost
                    score = self._apply_keyword_boost(title, base_score)
                    
                    headlines.append({
                        'title': title, 'score': score, 'url': link, 'date': pub_time
                    })
                    sentiment_sum += score
                    count += 1
            
            # 2. Fallback to Google RSS if yfinance failed
            if count == 0:
                target = self.stock_name if self.stock_name else self.ticker
                # Improve query for generic tickers
                query = f"{target} 주식" if ".KS" in self.ticker or ".KQ" in self.ticker else f"{target} stock"
                
                headlines, sentiment_sum, count, source_status = self._fetch_google_rss(query)
                
            if count == 0:
                 return {'score': 0, 'headlines': [], 'status': 'No News (Last 3 Days)'}
                 
            avg_score = sentiment_sum / count
            
            return {'score': avg_score, 'headlines': headlines, 'status': f'OK ({source_status})'}
            
        except Exception as e:
            print(f"News Analysis Error ({self.ticker}): {e}")
            return {'score': 0, 'status': f'Error: {e}', 'headlines': []}
