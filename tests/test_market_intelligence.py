import unittest
from unittest.mock import patch
import urllib.error
import os

from modules import market_intelligence


class MarketIntelligenceTests(unittest.TestCase):
    def setUp(self):
        market_intelligence._intelligence_cache.clear()

    def test_no_api_key_uses_rule_based_source_with_headlines(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False), patch(
            "modules.market_intelligence._fetch_global_headlines", return_value=["h1", "h2"]
        ), patch(
            "modules.market_intelligence._build_rule_fallback_result",
            side_effect=lambda headlines, market, source, insight_suffix: {
                "source": source,
                "headline_count": len(headlines),
                "key_insight": insight_suffix,
            },
        ):
            result = market_intelligence.get_market_intelligence("KOSPI", api_key="", force_refresh=True)
        self.assertEqual(result["source"], "rss_rule_based")
        self.assertEqual(result["headline_count"], 2)
        self.assertEqual(result["_display_origin"], "live")

    def test_http_429_falls_back_to_rate_limited_source(self):
        http_429 = urllib.error.HTTPError("https://example.com", 429, "Too Many Requests", hdrs=None, fp=None)
        with patch("modules.market_intelligence._fetch_global_headlines", return_value=["h1", "h2"]), patch(
            "urllib.request.urlopen",
            side_effect=http_429,
        ), patch(
            "modules.market_intelligence._build_rule_fallback_result",
            side_effect=lambda headlines, market, source, insight_suffix: {
                "source": source,
                "headline_count": len(headlines),
                "key_insight": insight_suffix,
            },
        ):
            result = market_intelligence.get_market_intelligence("KOSPI", api_key="test-key", force_refresh=True)
        self.assertEqual(result["source"], "rss_rule_based_rate_limited")
        self.assertEqual(result["headline_count"], 2)
        self.assertEqual(result["_display_origin"], "live")

    def test_cached_response_is_labeled_as_cached(self):
        market_intelligence._intelligence_cache["KR"] = {
            "data": {"source": "gemini", "headline_count": 15},
            "timestamp": __import__("time").time(),
            "ttl": 1800,
        }
        result = market_intelligence.get_market_intelligence("KOSPI", api_key="ignored", force_refresh=False)
        self.assertEqual(result["source"], "gemini")
        self.assertEqual(result["_display_origin"], "cache")

    def test_select_balanced_headlines_limits_dart_bias_for_kr(self):
        collected = []
        for idx in range(6):
            collected.append((100 - idx, f"[DART 20260419] 기업{idx} - 단일판매ㆍ공급계약체결 | 전자공시"))
        collected.extend(
            [
                (200, "[Sat, 19 Apr 2026 09:00:00 GMT] 코스피 외국인 순매수 확대 | 연합뉴스"),
                (199, "[Sat, 19 Apr 2026 08:45:00 GMT] 원달러 환율 안정세, 코스피 대형주 강세 | 한국경제"),
                (198, "[Sat, 19 Apr 2026 08:30:00 GMT] 반도체 업황 회복 기대에 증시 위험선호 개선 | 매일경제"),
                (197, "[주달 상승테마] 반도체 | 주달"),
            ]
        )
        rows = market_intelligence._select_balanced_headlines(collected, "KOSPI", max_items=6)
        self.assertLessEqual(sum(1 for row in rows if row.startswith("[DART")), 2)
        self.assertTrue(any("코스피" in row or "증시" in row for row in rows))

    def test_finalize_intelligence_payload_backfills_empty_market_lists(self):
        payload = market_intelligence._finalize_intelligence_payload(
            {
                "driver_scores": {"LIQUIDITY": 3, "OIL": -2, "FX": -1},
                "beneficiary_sectors": [],
                "victim_sectors": [],
                "beneficiary_keywords": [],
                "victim_keywords": [],
                "risk_flags": [],
                "evidence_headlines": [],
            },
            headlines=["코스피 외국인 수급 개선", "유가 상승 부담"],
            market="KOSPI",
        )
        self.assertIn("수급/유동성", payload["beneficiary_sectors"])
        self.assertIn("유가", payload["victim_sectors"])
        self.assertEqual(payload["evidence_headlines"], ["코스피 외국인 수급 개선", "유가 상승 부담"])


if __name__ == "__main__":
    unittest.main()
