"""만료 결과 소급 점수화 — 출처 구분·계약 준수·멱등성.

근거: 정산기/지표산출기의 이름-정렬 버그로 7,413건이 HORIZON_ELAPSED_NO_RESOLUTION 으로
만료됐다(데이터 부재가 아니라 창 초과). 소급 계산은 가능하지만 **forward 기록이 아니다.**
"""
from __future__ import annotations

import datetime as dt
import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
bf = importlib.import_module("multi_agent.tools.backfill_expired_outcome_returns")


@pytest.fixture
def prices(tmp_path):
    days = [dt.date(2026, 7, 1) + dt.timedelta(days=i) for i in range(12)]
    rows = [{"code": "005930", "date": d, "close": 100 + i * 10} for i, d in enumerate(days)]
    p = tmp_path / "px.parquet"
    pd.DataFrame(rows).to_parquet(p)
    return bf.load_prices(p)


def test_return_follows_the_trading_day_offset_contract(prices):
    got, why = bf.compute_return(prices, "005930.KS", "2026-07-01T01:00:00+00:00", "T+2D")
    assert why == "ok"
    # base=100(07-01), +2 거래일=120  →  +20%
    assert got["return_pct"] == pytest.approx(20.0)
    assert got["horizon_days"] == 2 and got["base_trade_date"] == "2026-07-01"


def test_base_date_uses_market_timezone(prices):
    """KR 티커는 Asia/Seoul 기준일이다 — UTC 로 읽으면 하루 어긋난다."""
    # 2026-07-01T16:00Z = 서울 07-02 01:00 → 기준일 07-02
    got, _ = bf.compute_return(prices, "005930.KS", "2026-07-01T16:00:00+00:00", "T+1D")
    assert got["base_trade_date"] == "2026-07-02"


def test_non_kr_rows_are_left_alone(prices):
    got, why = bf.compute_return(prices, "AAPL", "2026-07-01T01:00:00+00:00", "T+1D")
    assert got is None and why == "non_kr_no_local_prices"


def test_missing_price_series_is_reported_not_guessed(prices):
    got, why = bf.compute_return(prices, "999999.KQ", "2026-07-01T01:00:00+00:00", "T+1D")
    assert got is None and why == "no_price_series"


def test_horizon_beyond_history_is_not_backfilled(prices):
    got, why = bf.compute_return(prices, "005930.KS", "2026-07-11T01:00:00+00:00", "T+5D")
    assert got is None and why == "horizon_beyond_history"


# --- 출처 구분 (설계 제약 1) ------------------------------------------------

def test_backfilled_row_is_excluded_by_existing_consumers():
    """소비자는 status == "RESOLVED" 정확 일치로 거른다. 소급분은 그 값이 아니어야 한다.

    (run_learning_cycle.py:100 / export_scan_archive_learning_dataset.py:286,396)
    새 필드만 추가하고 status 를 RESOLVED 로 두면 전 소비자가 조용히 포함해버린다.
    """
    row = {"status": "EXPIRED"}
    bf.apply_to_row(row, {"return_pct": 1.0, "horizon_days": 1, "base_trade_date": "2026-07-01",
                          "base_close": 100.0, "target_trade_date": "2026-07-02"}, "now")
    assert row["status"] == "RESOLVED_BACKFILL"
    assert row["status"].upper() != "RESOLVED", "기존 소비자가 소급분을 조용히 포함한다"
    assert row["resolution_source"] == "backfill_px_long_v1"


def test_consumer_filter_actually_excludes_it():
    """소비자 필터 형태를 그대로 재현해 제외되는지 확인한다."""
    rows = [{"status": "RESOLVED"}, {"status": "RESOLVED_BACKFILL"}, {"status": "EXPIRED"}]
    kept = [r for r in rows if str(r.get("status", "")).upper() == "RESOLVED"]
    assert len(kept) == 1 and kept[0]["status"] == "RESOLVED"


def test_original_expiry_evidence_is_preserved():
    row = {"status": "EXPIRED", "expiry_reason": "HORIZON_ELAPSED_NO_RESOLUTION",
           "outcome_label": "EXPIRED"}
    bf.apply_to_row(row, {"return_pct": 1.0, "horizon_days": 1, "base_trade_date": "2026-07-01",
                          "base_close": 100.0, "target_trade_date": "2026-07-02"}, "now")
    assert row["expiry_reason"] == "HORIZON_ELAPSED_NO_RESOLUTION"
    assert row["outcome_label"] == "EXPIRED", "무엇이 왜 만료됐는지가 지워졌다"


def test_provenance_fields_record_how_it_was_computed():
    row = {"status": "EXPIRED"}
    bf.apply_to_row(row, {"return_pct": -2.5, "horizon_days": 5, "base_trade_date": "2026-07-01",
                          "base_close": 100.0, "target_trade_date": "2026-07-08"}, "now")
    for k in ("backfill_return_pct", "backfill_horizon_days", "backfill_base_trade_date",
              "backfill_base_close", "backfill_target_trade_date", "backfill_price_source"):
        assert k in row, f"{k} 가 없다 — 어떻게 계산했는지 추적 불가"
    assert row["return_5d_pct"] == -2.5, "계약 필드에도 기록돼야 소비자가 쓸 수 있다"


# --- 멱등성 (설계 제약 3) ----------------------------------------------------

def test_second_pass_changes_nothing():
    row = {"status": "EXPIRED"}
    c = {"return_pct": 1.0, "horizon_days": 1, "base_trade_date": "2026-07-01",
         "base_close": 100.0, "target_trade_date": "2026-07-02"}
    assert bf.apply_to_row(row, c, "t1") is True
    snapshot = dict(row)
    assert bf.apply_to_row(row, c, "t2") is False, "두 번째 실행이 또 바꿨다"
    assert row == snapshot


def test_apply_requires_a_backup_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["x", "--apply", "--shared-dir", str(tmp_path),
                                      "--px-path", "unused"])
    assert bf.main() == 1
    assert "backup-dir" in capsys.readouterr().out


def test_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    run = tmp_path / "shared" / "RUN-AA"
    run.mkdir(parents=True)
    f = run / "realized_outcomes.json"
    f.write_text(json.dumps([{"status": "EXPIRED", "ticker": "005930.KS", "horizon": "T+1D",
                              "recommended_at": "2026-07-01T01:00:00+00:00"}]), encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    px = tmp_path / "px.parquet"
    pd.DataFrame([{"code": "005930", "date": dt.date(2026, 7, 1) + dt.timedelta(days=i),
                   "close": 100 + i} for i in range(5)]).to_parquet(px)
    monkeypatch.setattr(sys, "argv", ["x", "--shared-dir", str(tmp_path / "shared"),
                                      "--px-path", str(px)])
    assert bf.main() == 0
    assert f.read_text(encoding="utf-8") == before, "dry-run 이 파일을 바꿨다"
    assert json.loads(capsys.readouterr().out)["changed_rows"] == 1
