import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from urllib.parse import quote
import time
import html
import re
from datetime import datetime, timezone

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

    @staticmethod
    def _clean_headline_title(title, source=""):
        text = html.unescape(str(title or "")).strip()
        text = re.sub(r"\s+", " ", text)
        src = str(source or "").strip()
        if src:
            escaped = re.escape(src)
            text = re.sub(rf"\s*[-|]\s*{escaped}\s*$", "", text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def _parse_timestamp(date_val):
        if isinstance(date_val, (int, float)):
            raw = float(date_val)
            if raw > 10_000_000_000:
                raw = raw / 1000.0
            return raw
        if isinstance(date_val, str):
            text = str(date_val).strip()
            if not text:
                return None
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
            for fmt in ("%Y%m%d%H%M", "%Y%m%d", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp()
                except Exception:
                    continue
        return None

    @staticmethod
    def _dedupe_headline_rows(rows):
        deduped = []
        seen = set()
        for row in rows:
            title = str((row or {}).get("title", "")).strip()
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    @staticmethod
    def _entry_field(entry, key, default=None):
        if isinstance(entry, dict):
            return entry.get(key, default)
        return getattr(entry, key, default)

    def _fetch_naver_stock_news(self, cutoff_time):
        try:
            from modules.naver_news_scraper import NaverNewsScraper
        except Exception:
            return [], 0.0, 0, "Error"

        payload = NaverNewsScraper().get_news_sentiment(self.ticker, days=3)
        items = list(payload.get("headline_items", []) or [])
        headlines = []
        sentiment_sum = 0.0
        count = 0
        for item in items:
            ts = self._parse_timestamp(item.get("datetime"))
            if ts is None:
                continue
            if ts < cutoff_time:
                continue
            title = self._clean_headline_title(item.get("title"), item.get("source"))
            if not title:
                continue
            score = max(-1.0, min(1.0, float(item.get("score", 0.0) or 0.0) / 15.0))
            headlines.append(
                {
                    "title": title,
                    "score": score,
                    "url": item.get("url", ""),
                    "date": item.get("datetime"),
                    "source": item.get("source", "Naver Stock"),
                    "timestamp": ts,
                }
            )
            sentiment_sum += score
            count += 1
            if len(headlines) >= self.max_results:
                break
        headlines = self._dedupe_headline_rows(headlines)
        return headlines, sentiment_sum, len(headlines), "Naver Stock"
        
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
            seen_titles = set()
            
            # Filter & Process
            for entry in feed.entries:
                if len(headlines) >= self.max_results:
                    break
                    
                entry_time = None
                source = ""
                source_meta = self._entry_field(entry, "source")
                if isinstance(source_meta, dict):
                    source = str(source_meta.get("title", "")).strip()

                title = self._clean_headline_title(self._entry_field(entry, "title", ""), source)
                if not title:
                    continue
                dedup_key = title.lower()
                if dedup_key in seen_titles:
                    continue

                link = self._entry_field(entry, "link", "")
                pub_date = self._entry_field(entry, "published", "")
                
                # Check Date (feedparser gives 'published_parsed' as struct_time)
                published_parsed = self._entry_field(entry, "published_parsed")
                if published_parsed:
                    # Convert to seconds
                    entry_time = time.mktime(published_parsed)
                    if time.time() - entry_time > (3 * 24 * 3600):
                        continue # Skip old news
                else:
                    entry_time = self._parse_timestamp(pub_date)
                    if entry_time is not None and time.time() - entry_time > (3 * 24 * 3600):
                        continue
                
                # VADER Score
                vs = self.analyzer.polarity_scores(title)
                base_score = vs['compound']
                
                # Apply Semantic Boost
                score = self._apply_keyword_boost(title, base_score)
                seen_titles.add(dedup_key)
                
                headlines.append({
                    'title': title, 
                    'score': score, 
                    'url': link,
                    'date': pub_date,
                    'source': source or "Google RSS",
                    'timestamp': entry_time if 'entry_time' in locals() else None,
                })
                sentiment_sum += score
                count += 1

            headlines.sort(key=lambda row: float(row.get("timestamp", 0.0) or 0.0), reverse=True)
            headlines = self._dedupe_headline_rows(headlines)[:self.max_results]
            sentiment_sum = sum(float(row.get("score", 0.0) or 0.0) for row in headlines)
            count = len(headlines)
                
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
            if ".KS" in self.ticker or ".KQ" in self.ticker:
                headlines, sentiment_sum, count, source_status = self._fetch_naver_stock_news(cutoff_time)

            if count == 0:
                source_status = "yfinance"
                yf_ticker = yf.Ticker(self.ticker)
                news_list = yf_ticker.news

                if news_list:
                    seen_titles = set()
                    for item in news_list:
                        if len(headlines) >= self.max_results:
                            break

                        content = item.get('content', item)
                        pub_time = content.get('pubDate', content.get('providerPublishTime', 0))
                        pub_ts = self._parse_timestamp(pub_time)
                        if pub_ts is not None and pub_ts < cutoff_time:
                            continue

                        provider = ((content.get("provider") or {}).get("displayName")) if isinstance(content.get("provider"), dict) else ""
                        title = self._clean_headline_title(content.get('title', ''), provider)
                        if not title:
                            continue
                        dedup_key = title.lower()
                        if dedup_key in seen_titles:
                            continue

                        link_obj = content.get('clickThroughUrl') or content.get('canonicalUrl')
                        link = link_obj.get('url') if link_obj else content.get('link', '')

                        vs = self.analyzer.polarity_scores(title)
                        base_score = vs['compound']
                        score = self._apply_keyword_boost(title, base_score)
                        seen_titles.add(dedup_key)

                        headlines.append({
                            'title': title,
                            'score': score,
                            'url': link,
                            'date': pub_time,
                            'source': provider or "yfinance",
                            'timestamp': pub_ts,
                        })

                    headlines.sort(key=lambda row: float(row.get("timestamp", 0.0) or 0.0), reverse=True)
                    headlines = self._dedupe_headline_rows(headlines)[:self.max_results]
                    sentiment_sum = sum(float(row.get("score", 0.0) or 0.0) for row in headlines)
                    count = len(headlines)
            
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
