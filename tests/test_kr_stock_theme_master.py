import json

from modules import kr_stock_theme_master as master


def test_candidate_paths_do_not_use_downloads_without_opt_in(monkeypatch, tmp_path):
    local_path = tmp_path / "missing.jsonl"
    monkeypatch.setattr(master, "LOCAL_MASTER_PATH", local_path)
    monkeypatch.delenv("AG_KR_STOCK_THEME_MASTER_PATH", raising=False)
    monkeypatch.delenv("AG_ALLOW_EXTERNAL_KR_THEME_MASTER", raising=False)

    paths = master._candidate_paths()

    assert master.DEFAULT_MASTER_PATH not in paths


def test_load_master_falls_back_to_runtime_membership(monkeypatch, tmp_path):
    local_path = tmp_path / "missing.jsonl"
    runtime_path = tmp_path / "KR.json"
    runtime_path.write_text(
        json.dumps(
            {
                "version": "runtime-test",
                "records": [
                    {
                        "symbol": "005930",
                        "market": "KR",
                        "market_scope": "KOSPI",
                        "name": "삼성전자",
                        "primary_theme": "반도체",
                        "secondary_themes": ["IT서비스/플랫폼"],
                        "memberships": [
                            {
                                "theme_id": "semiconductor",
                                "theme_source": "official_text_match",
                                "theme_inference_status": "official_text_match",
                            }
                        ],
                        "official_classification": {
                            "official_sector": "일반기업부",
                            "official_industry": "반도체 제조업",
                            "official_products": "메모리 반도체",
                            "classification_source": "test",
                        },
                    },
                    {
                        "symbol": "123456",
                        "market_scope": "KONEX",
                        "name": "제외",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(master, "LOCAL_MASTER_PATH", local_path)
    monkeypatch.setattr(master, "RUNTIME_THEME_MEMBERSHIP_PATH", runtime_path)
    monkeypatch.delenv("AG_KR_STOCK_THEME_MASTER_PATH", raising=False)
    monkeypatch.delenv("AG_ALLOW_EXTERNAL_KR_THEME_MASTER", raising=False)
    master.load_kr_stock_theme_master.cache_clear()

    payload = master.load_kr_stock_theme_master()

    assert payload["records_by_ticker"]["005930.KS"]["primary_theme"] == "반도체"
    assert payload["records_by_ticker"]["005930.KS"]["stock_name"] == "삼성전자"
    assert "123456" not in payload["records_by_ticker"]
    assert "theme_membership" in payload["source_path"] or "KR.json" in payload["source_path"]
