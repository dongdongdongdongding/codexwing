import requests
from bs4 import BeautifulSoup
import re
import html
from datetime import datetime, timedelta

# 키워드 사전 (가중치)
POSITIVE_KEYWORDS = {
    "수주": 5, "승인": 5, "공급": 4, "상한가": 4, "호실적": 5, "흑자": 5,
    "MOU": 3, "체결": 4, "돌파": 3, "인수": 4, "특허": 3, "개발": 3,
    "상승": 2, "급등": 3, "합병": 4, "출시": 3, "최대": 3, "신고가": 3
}

NEGATIVE_KEYWORDS = {
    "유상증자": -8, "횡령": -10, "배임": -10, "적자": -5, "하한가": -5, 
    "조사": -5, "상장폐지": -10, "급락": -5, "소송": -4, "불성실": -6, 
    "하향": -4, "매도": -3, "위기": -4, "하락": -2, "우려": -3
}

class NaverNewsScraper:
    def __init__(self):
        self.base_url = "https://finance.naver.com/item/news_news.naver?code={code}&page={page}"
        # 브라우저 차단 우회를 위한 헤더
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
        }
    
    def extract_code(self, ticker: str) -> str:
        """'005930.KS' -> '005930'"""
        return re.sub(r'[^0-9]', '', ticker)

    @staticmethod
    def _clean_title(title: str) -> str:
        text = html.unescape(str(title or "")).strip()
        return re.sub(r"\s+", " ", text)
        
    def get_news_sentiment(self, ticker: str, days: int = 3) -> dict:
        """
        종목의 최근 뉴스를 수집하여 긍정/부정 감성 점수를 계산
        return: {"score": 0, "pos_count": 0, "neg_count": 0, "titles": []}
        """
        code = self.extract_code(ticker)
        if not code:
            return {"score": 0, "pos_count": 0, "neg_count": 0, "titles": [], "recent_titles": [], "msg": "Invalid ticker"}
            
        target_date = datetime.now() - timedelta(days=days)
        score = 0
        pos_count = 0
        neg_count = 0
        collected_titles = []
        recent_titles = []
        headline_items = []
        seen_titles = set()
        
        try:
            # 네이버 모바일 증권 API 활용 (JSON 반환)
            url = f"https://m.stock.naver.com/api/news/stock/{code}?pageSize=20&page=1"
            resp = requests.get(url, headers=self.headers, timeout=5)
            
            if resp.status_code == 429:
                # Triggering specific error for the backoff system to catch
                raise Exception("API_RATE_LIMIT_429")
            
            if resp.status_code != 200:
                return {"score": 0, "pos_count": 0, "neg_count": 0, "titles": [], "recent_titles": [], "msg": f"Request failed: {resp.status_code}"}
                
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                # 뉴스가 없는 경우
                return {"score": 0, "pos_count": 0, "neg_count": 0, "titles": [], "recent_titles": []}
                
            for group in data:
                items = group.get('items', [])
                for item in items:
                    title_text = item.get('titleFull') or item.get('title', '')
                    date_str = item.get('datetime', '') # e.g. "202603161741"
                    office_name = str(item.get("officeName", "") or "").strip()
                    mobile_url = str(item.get("mobileNewsUrl", "") or "").strip()
                    
                    if not title_text or not date_str:
                        continue
                        
                    title_text = self._clean_title(title_text)
                    if not title_text:
                        continue
                        
                    try:
                        news_date = datetime.strptime(date_str[:12], "%Y%m%d%H%M")
                        if news_date < target_date:
                            continue
                    except:
                        pass

                    dedup_key = title_text.lower()
                    if dedup_key in seen_titles:
                        continue
                    seen_titles.add(dedup_key)

                    # 키워드 매칭
                    row_score = 0
                    for pos_kw, weight in POSITIVE_KEYWORDS.items():
                        if pos_kw in title_text:
                            row_score += weight
                            pos_count += 1
                            
                    for neg_kw, weight in NEGATIVE_KEYWORDS.items():
                        if neg_kw in title_text:
                            row_score += weight
                            neg_count += 1

                    headline_items.append(
                        {
                            "title": title_text,
                            "datetime": date_str,
                            "source": office_name,
                            "url": mobile_url,
                            "score": row_score,
                        }
                    )
                            
                    if row_score != 0:
                        score += row_score
                        collected_titles.append(f"[{row_score:+d}] {title_text}")
            headline_items.sort(key=lambda row: str(row.get("datetime", "")), reverse=True)
            recent_titles = [row.get("title") for row in headline_items[:8] if row.get("title")]

            # 점수 캡핑 (Max +15, Min -15)
            final_score = max(-15, min(15, score))
            
            return {
                "score": final_score,
                "raw_score": score,
                "pos_count": pos_count,
                "neg_count": neg_count,
                "titles": collected_titles[:5],  # 점수 반영된 상위 5개
                "recent_titles": recent_titles[:8],  # 최근 기사 제목 원문
                "headline_items": headline_items[:20],
            }
            
        except Exception as e:
            return {"score": 0, "pos_count": 0, "neg_count": 0, "titles": [], "recent_titles": [], "headline_items": [], "msg": str(e)}

# 간단한 테스트
if __name__ == "__main__":
    scraper = NaverNewsScraper()
    for t in ["005930.KS", "000660.KS", "068270.KS", "035420.KS", "035720.KS", "005380.KS"]:
        print(f"Testing {t}")
        res = scraper.get_news_sentiment(t)
        print(res)
