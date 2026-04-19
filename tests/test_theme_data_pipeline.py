import unittest
from unittest.mock import patch

import pandas as pd

from modules.theme_catalog import resolve_theme_memberships
from modules.theme_data_pipeline import (
    build_catalog_from_membership_payload,
    build_instrument_master_payload,
    build_theme_membership_payload,
)


class InstrumentMasterBuilderTests(unittest.TestCase):
    def test_build_kr_instrument_master_normalizes_desc_fields(self):
        frame = pd.DataFrame(
            [
                {
                    "Code": "005930",
                    "Name": "삼성전자",
                    "Market": "KOSPI",
                    "Sector": "",
                    "Industry": "반도체 제조업",
                    "Products": "메모리 반도체",
                    "ListingDate": pd.Timestamp("1975-06-11"),
                    "HomePage": "https://example.com",
                    "Region": "경기도",
                }
            ]
        )
        payload = build_instrument_master_payload("KR", listing_frames={"KRX-DESC": frame})
        row = payload["records"][0]
        self.assertEqual(payload["market"], "KR")
        self.assertEqual(row["symbol"], "005930.KS")
        self.assertEqual(row["official_industry"], "반도체 제조업")
        self.assertEqual(row["official_products"], "메모리 반도체")

    def test_build_us_instrument_master_uses_sp500_sector_overlay(self):
        payload = build_instrument_master_payload(
            "US",
            listing_frames={
                "NASDAQ": pd.DataFrame(
                    [{"Symbol": "AAPL", "Name": "Apple Inc", "IndustryCode": "57106020", "Industry": "전화 및 소형 장치"}]
                ),
                "NYSE": pd.DataFrame([]),
                "AMEX": pd.DataFrame([]),
                "S&P500": pd.DataFrame([{"Symbol": "AAPL", "Name": "Apple Inc", "Sector": "Information Technology", "Industry": "Technology Hardware"}]),
            },
        )
        row = payload["records"][0]
        self.assertEqual(row["symbol"], "AAPL")
        self.assertEqual(row["official_sector"], "Information Technology")
        self.assertIn("S&P500", row["source_listings"])


class ThemeMembershipBuilderTests(unittest.TestCase):
    @patch("modules.theme_data_pipeline.get_stock_theme_record")
    def test_build_theme_membership_prefers_stock_master_for_kr(self, get_stock_theme_record_mock):
        get_stock_theme_record_mock.return_value = {
            "primary_theme": "반도체",
            "secondary_themes": ["IT서비스/플랫폼"],
            "theme_inference_status": "inferred",
        }
        instrument_payload = {
            "version": "instrument-master::KR::test",
            "market": "KR",
            "records": [
                {
                    "symbol": "005930.KS",
                    "name": "삼성전자",
                    "market_scope": "KOSPI",
                    "official_sector": "",
                    "official_industry": "반도체 제조업",
                    "official_products": "메모리 반도체",
                    "industry_code": "",
                    "classification_source": "FDR_KRX_DESC",
                }
            ],
        }
        payload = build_theme_membership_payload("KR", instrument_payload=instrument_payload)
        row = payload["records"][0]
        self.assertEqual(row["primary_theme"], "반도체")
        self.assertEqual(row["memberships"][0]["theme_source"], "stock_master")
        self.assertGreaterEqual(row["memberships"][0]["confidence"], 0.88)

    def test_build_catalog_from_membership_payload_groups_tickers_by_theme(self):
        payload = {
            "version": "theme-membership::KR::test",
            "market": "KR",
            "record_count": 2,
            "records": [
                {
                    "symbol": "005930.KS",
                    "market_scope": "KOSPI",
                    "memberships": [{"theme_id": "semiconductor", "theme_name": "반도체", "confidence": 0.96}],
                },
                {
                    "symbol": "000660.KS",
                    "market_scope": "KOSPI",
                    "memberships": [{"theme_id": "semiconductor", "theme_name": "반도체", "confidence": 0.92}],
                },
            ],
            "primary_source_distribution": {"stock_master": 2},
        }
        catalog = build_catalog_from_membership_payload("KR", payload)
        self.assertEqual(catalog["themes"][0]["theme_name"], "반도체")
        self.assertEqual(len(catalog["themes"][0]["ticker_memberships"]), 2)


class ThemeResolutionTests(unittest.TestCase):
    @patch("modules.theme_catalog.get_theme_membership_record")
    def test_resolve_theme_memberships_prefers_artifact_record(self, get_theme_membership_record_mock):
        get_theme_membership_record_mock.return_value = {
            "secondary_themes": ["IT서비스/플랫폼"],
            "official_classification": {
                "official_sector": "",
                "official_industry": "반도체 제조업",
                "official_products": "메모리 반도체",
                "classification_source": "FDR_KRX_DESC",
            },
            "memberships": [
                {
                    "theme_id": "semiconductor",
                    "theme_name": "반도체",
                    "confidence": 0.95,
                    "theme_source": "stock_master",
                    "theme_inference_status": "inferred",
                    "reasons": ["stock_master:inferred"],
                    "driver_categories": ["EARNINGS"],
                }
            ],
        }
        rows = resolve_theme_memberships("005930.KS", "삼성전자", "KR")
        self.assertEqual(rows[0]["theme_name"], "반도체")
        self.assertEqual(rows[0]["theme_source"], "stock_master")
        self.assertEqual(rows[0]["official_industry"], "반도체 제조업")


if __name__ == "__main__":
    unittest.main()
