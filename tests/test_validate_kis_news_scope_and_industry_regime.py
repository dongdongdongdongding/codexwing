from multi_agent.tools.validate_kis_news_scope_and_industry_regime import build_validation_report


class FakeValidationKISClient:
    def stock_info(self, symbol):
        return {"output": {"pdno": symbol, "prdt_name": "삼성전자" if symbol == "005930" else "SK하이닉스"}}

    def news_titles(self, *, symbol="", trade_date="", hour=""):
        return {
            "output": [
                {
                    "mksc_shrn_iscd": symbol,
                    "hts_kor_isnm": "삼성전자" if symbol == "005930" else "SK하이닉스",
                    "hts_pbnt_titl_cntt": "AI 반도체 공급 계약 수주",
                }
            ]
        }

    def industry_price(self, *, index_code="0001"):
        return {"output": {"bstp_nmix_prpr": "1030", "bstp_nmix_prdy_ctrt": "0.8"}}

    def industry_daily_bars(self, *, index_code="0001", start_date="", end_date="", period="D", market_div="U"):
        return {
            "output2": [
                {
                    "stck_bsop_date": f"202605{idx + 1:02d}",
                    "bstp_nmix_oprc": str(1000 + idx),
                    "bstp_nmix_hgpr": str(1002 + idx),
                    "bstp_nmix_lwpr": str(998 + idx),
                    "bstp_nmix_prpr": str(1000 + idx),
                    "acml_vol": "100000",
                }
                for idx in range(22)
            ]
        }


def test_validation_report_marks_symbol_specific_news_and_industry_overlay_ready():
    report = build_validation_report(
        FakeValidationKISClient(),
        symbols=["005930"],
        trade_date="20260608",
        industry_codes=[("1001", "KOSDAQ")],
        industry_start_date="20260501",
        industry_end_date="20260608",
    )

    assert report["no_dummy_data"] is True
    assert report["verdict"] == "ready_with_symbol_specific_news"
    assert report["summary"]["news_source_scope_counts"] == {"symbol_specific": 1}
    assert report["summary"]["news_promotion_blocked_count"] == 0
    assert report["summary"]["industry_overlay_ready_count"] == 1
