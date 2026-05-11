import unittest
import time
from unittest.mock import Mock, patch

from modules.market_intelligence import _normalize_headline_title, _collect_kr_stock_headlines
from modules.news_analysis import NewsAnalyzer


class HeadlineNormalizationTests(unittest.TestCase):
    def test_normalize_headline_title_strips_duplicate_source_suffix(self):
        self.assertEqual(
            _normalize_headline_title("코스피 상승 마감 - 연합뉴스", "연합뉴스"),
            "코스피 상승 마감",
        )

    def test_news_analyzer_google_rss_cleans_and_dedupes_titles(self):
        analyzer = NewsAnalyzer("AAPL", stock_name="Apple", max_results=5)
        feed = Mock()
        newer = time.gmtime(time.time() - 60 * 60)
        older = time.gmtime(time.time() - 2 * 60 * 60)
        newer_text = time.strftime("%a, %d %b %Y %H:%M:%S GMT", newer)
        older_text = time.strftime("%a, %d %b %Y %H:%M:%S GMT", older)
        feed.entries = [
            {
                "title": "Apple rallies after earnings beat - Reuters",
                "link": "https://example.com/1",
                "published": newer_text,
                "published_parsed": newer,
                "source": {"title": "Reuters"},
            },
            {
                "title": "Apple rallies after earnings beat - Reuters",
                "link": "https://example.com/2",
                "published": older_text,
                "published_parsed": older,
                "source": {"title": "Reuters"},
            },
        ]
        with patch("modules.news_analysis.feedparser.parse", return_value=feed):
            headlines, _, count, source = analyzer._fetch_google_rss("Apple stock")
        self.assertEqual(source, "Google RSS")
        self.assertEqual(count, 1)
        self.assertEqual(headlines[0]["title"], "Apple rallies after earnings beat")
        self.assertEqual(headlines[0]["source"], "Reuters")

    def test_news_analyzer_prefers_naver_items_for_kr_ticker(self):
        analyzer = NewsAnalyzer("005930.KS", stock_name="삼성전자", max_results=5)
        with patch.object(
            analyzer,
            "_fetch_naver_stock_news",
            return_value=(
                [
                    {
                        "title": "삼성전자, AI TV 위크 개최",
                        "score": 0.4,
                        "url": "https://example.com/news",
                        "date": "202604191631",
                        "source": "SBS Biz",
                        "timestamp": 1_766_000_000.0,
                    }
                ],
                0.4,
                1,
                "Naver Stock",
            ),
        ):
            result = analyzer.get_news_sentiment()
        self.assertEqual(result["status"], "OK (Naver Stock)")
        self.assertEqual(result["headlines"][0]["title"], "삼성전자, AI TV 위크 개최")

    def test_parse_timestamp_supports_compact_naver_datetime(self):
        ts = NewsAnalyzer._parse_timestamp("202604191631")
        self.assertIsNotNone(ts)

    def test_collect_kr_stock_headlines_uses_raw_naver_titles(self):
        fake_scraper = Mock()
        fake_scraper.get_news_sentiment.return_value = {
            "headline_items": [
                {
                    "title": "&quot;삼성&quot; AI TV 위크 개최",
                    "datetime": "202604191631",
                    "source": "SBS Biz",
                    "url": "https://example.com/naver",
                    "score": 3,
                }
            ]
        }
        with patch("modules.market_intelligence._dynamic_kr_market_leaders", return_value=["005930.KS"]), patch(
            "modules.naver_news_scraper.NaverNewsScraper", return_value=fake_scraper
        ):
            rows = _collect_kr_stock_headlines("KOSPI")
        self.assertEqual(len(rows), 1)
        self.assertIn('"삼성" AI TV 위크 개최', rows[0][1])
        self.assertNotIn("[+3]", rows[0][1])


if __name__ == "__main__":
    unittest.main()
