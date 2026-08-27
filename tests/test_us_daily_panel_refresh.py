"""US 일봉 피처 패널의 증분 갱신·보존 (audit-ledger-rewrite-pattern.md §2.2).

`~/research_cache/us_daily/NASDAQ/daily_features_*.parquet`가 2026-06-29 기록 후 동결됐고
**갱신 주체가 아예 없었다.** 그 결과 `nasdaq_swing_daily_edge_shadow_ledger.jsonl`이
승격 이래 **0행**인 채로 매일 재기록됐고(차단도 오류도 아님),
`nasdaq_session_edge`도 같은 일봉 컨텍스트를 물어 `score_date`가 06-26에 고정됐다.

생산자는 이미 존재한다: `backfill_us_daily_features.py`.
파일명 규칙이 동결된 산출물과 정확히 일치한다
(`daily_features_{start}_{end}_{stamp}.parquet` / `daily_features_latest_{stamp}.parquet`).
새로 쓰지 않고 이 스크립트를 되살린다 — 같은 스키마·같은 가정을 유지하기 위해서다.

되살리려면 두 가지를 고쳐야 한다:

1. **raw OHLCV가 5분봉 캐시와 똑같은 결함을 갖고 있다.**
       to_fetch = [sym for sym in symbols if force_raw or not _raw_path(paths, sym).exists()]
   파일이 **존재하기만 하면** 건너뛴다 — 신선도 검사가 없다. 그래서 매일 돌려도
   3,882개 raw가 전부 skip되고 06-29 데이터로 패널만 다시 만든다.
   `--force-raw`는 전 종목 전 기간 재fetch라 일일 운영에 못 쓴다.

2. **패널이 실행마다 새 타임스탬프 파일로 쌓인다.** 실측 3.4GB/회(이미 2회분 5.8GB).
   보존 정책 없이 일일 실행하면 디스크가 하루 3.4GB씩 는다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from multi_agent.tools import backfill_us_daily_features as bf

RAW_COLUMNS = ["date", "symbol", "name", "market", "open", "high", "low", "close",
               "raw_close", "adj_close", "volume", "adj_factor", "dollar_volume", "source"]


def _raw_frame(symbol: str, start: str, days: int, close: float = 10.0) -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=days)
    return pd.DataFrame({
        "date": idx, "symbol": symbol, "name": symbol, "market": "NASDAQ",
        "open": close, "high": close, "low": close, "close": close,
        "raw_close": close, "adj_close": close, "volume": 1000,
        "adj_factor": 1.0, "dollar_volume": close * 1000, "source": "yfinance",
    })[RAW_COLUMNS]


@pytest.fixture
def paths(tmp_path):
    p = bf.BackfillPaths(root=tmp_path, market="NASDAQ")
    p.raw_dir.mkdir(parents=True, exist_ok=True)
    return p


def _write_raw(paths, symbol, frame):
    frame.to_parquet(bf._raw_path(paths, symbol), index=False)


def _today_minus(days):
    return (date.today() - timedelta(days=days)).isoformat()


# --------------------------------------------------------------------------
# raw 신선도 — 5분봉 캐시와 같은 계열의 결함
# --------------------------------------------------------------------------

def test_stale_raw_is_detected(paths):
    """존재만으로 통과시키던 지점. 06-29 동결 raw는 낡은 것으로 판정돼야 한다."""
    _write_raw(paths, "AAA", _raw_frame("AAA", "2026-06-01", 20))

    assert bf._raw_stale_reason(bf._raw_path(paths, "AAA")) is not None


def test_fresh_raw_is_not_flagged(paths):
    """최신봉이 어제인 raw 는 신선하다 — 오늘이 무슨 요일이든.

    시작일을 고정하고 영업일 N 개를 세면 최신봉 나이가 요일에 따라 4~6일을 오간다.
    한계가 5일이라 특정 요일에만 깨졌다(같은 병을 `_panel_frame` 에서 이미 고쳤다).
    검사 대상은 「최신봉이 얼마나 낡았나」이므로 **끝을 어제로 고정**해서 짓는다.
    """
    end = pd.Timestamp(_today_minus(1))
    idx = pd.bdate_range(end=end, periods=5)
    if idx[-1] != end:                      # 어제가 주말이면 물러난 만큼 되돌린다
        idx = idx.append(pd.DatetimeIndex([end]))
    frame = _raw_frame("AAA", str(idx[0].date()), len(idx))
    frame["date"] = idx
    _write_raw(paths, "AAA", frame)

    assert bf._raw_stale_reason(bf._raw_path(paths, "AAA")) is None


def test_missing_raw_is_reported_as_absent(paths):
    assert bf._raw_stale_reason(bf._raw_path(paths, "NOPE")) is not None


def test_refresh_stale_raw_selects_only_stale_symbols(paths, monkeypatch):
    """신선한 심볼까지 매일 재fetch하면 3,882종목이 감당이 안 된다."""
    _write_raw(paths, "OLD", _raw_frame("OLD", "2026-06-01", 20))
    _write_raw(paths, "NEW", _raw_frame("NEW", _today_minus(6), 4))
    universe = pd.DataFrame([{"symbol": "OLD", "name": "OLD"}, {"symbol": "NEW", "name": "NEW"}])

    seen = []

    def _fake_batch(symbols, start, end, timeout):
        seen.extend(symbols)
        return pd.DataFrame()

    monkeypatch.setattr(bf, "_download_batch", _fake_batch)
    monkeypatch.setattr(bf, "_download_single", lambda s, st, e, t: _raw_frame(s, _today_minus(3), 2))

    bf.fetch_raw_ohlcv(universe, paths, start="2018-01-01", end=_today_minus(0),
                       batch_size=10, timeout=5, sleep=0, force_raw=False, refresh_stale=True)

    assert "OLD" in seen
    assert "NEW" not in seen, "신선한 심볼을 다시 받았다"


# --------------------------------------------------------------------------
# 병합 — 과거 구간을 잃지 않는다 (5분봉 캐시와 같은 원칙)
# --------------------------------------------------------------------------

def test_incremental_refresh_merges_and_keeps_history(paths, monkeypatch):
    """증분 갱신이 **과거를 잘라먹으면 안 된다**."""
    old = _raw_frame("AAA", "2018-01-01", 30, close=5.0)
    _write_raw(paths, "AAA", old)
    universe = pd.DataFrame([{"symbol": "AAA", "name": "AAA"}])
    monkeypatch.setattr(bf, "_download_batch", lambda s, st, e, t: pd.DataFrame())
    monkeypatch.setattr(bf, "_download_single",
                        lambda s, st, e, t: _raw_frame("AAA", _today_minus(5), 3, close=9.0))

    bf.fetch_raw_ohlcv(universe, paths, start="2018-01-01", end=_today_minus(0),
                       batch_size=10, timeout=5, sleep=0, force_raw=False, refresh_stale=True)

    merged = pd.read_parquet(bf._raw_path(paths, "AAA"))
    assert pd.to_datetime(merged["date"]).min() == pd.to_datetime(old["date"]).min()
    assert pd.to_datetime(merged["date"]).max() > pd.to_datetime(old["date"]).max()
    assert not merged["date"].duplicated().any()
    assert merged["date"].is_monotonic_increasing


def test_empty_fetch_leaves_raw_untouched(paths, monkeypatch):
    old = _raw_frame("AAA", "2018-01-01", 30)
    _write_raw(paths, "AAA", old)
    universe = pd.DataFrame([{"symbol": "AAA", "name": "AAA"}])
    monkeypatch.setattr(bf, "_download_batch", lambda s, st, e, t: pd.DataFrame())
    monkeypatch.setattr(bf, "_download_single", lambda s, st, e, t: pd.DataFrame())

    bf.fetch_raw_ohlcv(universe, paths, start="2018-01-01", end=_today_minus(0),
                       batch_size=10, timeout=5, sleep=0, force_raw=False, refresh_stale=True)

    assert len(pd.read_parquet(bf._raw_path(paths, "AAA"))) == len(old)


def test_fetch_exception_does_not_destroy_raw(paths, monkeypatch):
    old = _raw_frame("AAA", "2018-01-01", 30)
    _write_raw(paths, "AAA", old)
    universe = pd.DataFrame([{"symbol": "AAA", "name": "AAA"}])

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(bf, "_download_batch", _boom)
    monkeypatch.setattr(bf, "_download_single", _boom)

    bf.fetch_raw_ohlcv(universe, paths, start="2018-01-01", end=_today_minus(0),
                       batch_size=10, timeout=5, sleep=0, force_raw=False, refresh_stale=True)

    assert len(pd.read_parquet(bf._raw_path(paths, "AAA"))) == len(old)


def test_new_bars_win_on_overlapping_dates(paths, monkeypatch):
    """겹치는 날짜는 신규가 이긴다 (수정·분할 반영)."""
    _write_raw(paths, "AAA", _raw_frame("AAA", "2018-01-01", 30, close=5.0))
    universe = pd.DataFrame([{"symbol": "AAA", "name": "AAA"}])
    monkeypatch.setattr(bf, "_download_batch", lambda s, st, e, t: pd.DataFrame())
    monkeypatch.setattr(bf, "_download_single",
                        lambda s, st, e, t: _raw_frame("AAA", "2018-01-01", 3, close=77.0))

    bf.fetch_raw_ohlcv(universe, paths, start="2018-01-01", end=_today_minus(0),
                       batch_size=10, timeout=5, sleep=0, force_raw=False, refresh_stale=True)

    merged = pd.read_parquet(bf._raw_path(paths, "AAA")).sort_values("date")
    assert float(merged["close"].iloc[0]) == 77.0


# --------------------------------------------------------------------------
# 패널 보존 — 3.4GB/회가 무한 적재되면 안 된다
# --------------------------------------------------------------------------

def _touch_panel(paths, stamp):
    paths.market_root.mkdir(parents=True, exist_ok=True)
    for suffix in ("parquet",):
        (paths.market_root / f"daily_features_20180101_20260630_{stamp}.{suffix}").write_text("x")
        (paths.market_root / f"daily_features_latest_{stamp}.{suffix}").write_text("x")


def test_retention_keeps_only_the_newest_panels(paths):
    for stamp in ("20260601_010101", "20260615_010101", "20260629_113805", "20260816_010101"):
        _touch_panel(paths, stamp)

    removed = bf.prune_old_panels(paths, output_prefix="daily_features", keep=2)

    remaining = sorted(p.name for p in paths.market_root.glob("daily_features_2*.parquet"))
    assert len(remaining) == 2
    assert any("20260816_010101" in n for n in remaining)
    assert removed, "정리된 파일이 보고되지 않았다"


def test_retention_never_removes_the_newest(paths):
    _touch_panel(paths, "20260816_010101")

    bf.prune_old_panels(paths, output_prefix="daily_features", keep=1)

    assert list(paths.market_root.glob("daily_features_2*.parquet"))


def test_retention_disabled_keeps_everything(paths):
    for stamp in ("20260601_010101", "20260816_010101"):
        _touch_panel(paths, stamp)

    removed = bf.prune_old_panels(paths, output_prefix="daily_features", keep=0)

    assert removed == []
    assert len(list(paths.market_root.glob("daily_features_2*.parquet"))) == 2


# --------------------------------------------------------------------------
# 멱등성 / TTL — primary_daily_ops 가 하루 3회 돈다 (중앙값 4.46h, n=25)
# 이미 최신이면 즉시 반환해야 나머지 2회가 순수 낭비가 되지 않는다.
# 판정은 **내용 기준**(패널 최대일)이다. mtime 기준은 이번 사고들의 공통 함정이라 쓰지 않는다.
# --------------------------------------------------------------------------

def _panel_frame(max_date):
    """최대일이 **요청한 날짜 그대로**인 패널을 만든다.

    `bdate_range(end=...)` 만 쓰면 요청일이 주말일 때 금요일로 물러나서, 나이가
    요청한 것보다 하루 커진다. `_today_minus(4)` 로 경계를 시험하는 테스트가
    **오늘이 무슨 요일이냐에 따라** 통과/실패했다(수요일이면 today-4 가 토요일).
    간격은 달력일 산술이라 요일과 무관해야 한다 — 마지막 행을 요청일로 고정한다.
    """
    end = pd.Timestamp(max_date)
    idx = pd.bdate_range(end=end, periods=3)
    if idx[-1] != end:                       # 주말·휴일이면 물러난 만큼을 되돌린다
        idx = idx.append(pd.DatetimeIndex([end]))
    return pd.DataFrame({"date": idx, "symbol": "AAA", "close": 1.0})


def _write_latest_panel(paths, stamp, max_date):
    """스탬프 패널(소비자가 읽는 것) + `_latest_`(소비자가 무시하는 것)을 함께 쓴다."""
    paths.market_root.mkdir(parents=True, exist_ok=True)
    _panel_frame(max_date).to_parquet(
        paths.market_root / f"daily_features_latest_{stamp}.parquet", index=False)
    _panel_frame(max_date).to_parquet(
        paths.market_root / f"daily_features_20180101_20260630_{stamp}.parquet", index=False)


def _write_latest_only(paths, stamp, max_date):
    """`_latest_` 만 — 소비자는 이걸 절대 안 본다."""
    paths.market_root.mkdir(parents=True, exist_ok=True)
    _panel_frame(max_date).to_parquet(
        paths.market_root / f"daily_features_latest_{stamp}.parquet", index=False)


def test_panel_status_reads_content_not_mtime(paths):
    """패널 최대일로 판정한다. 파일을 새로 만져도(mtime 갱신) 내용이 낡으면 낡은 것이다."""
    _write_latest_panel(paths, "20260629_113805", "2026-06-26")
    p = paths.market_root / "daily_features_latest_20260629_113805.parquet"
    p.touch()   # mtime 을 지금으로 — 그래도 stale 이어야 한다

    status = bf.panel_status(paths, output_prefix="daily_features")

    assert status["panel_max_date"] == "2026-06-26"
    assert status["current"] is False


def test_fresh_panel_is_reported_current(paths):
    _write_latest_panel(paths, "20260816_010101", _today_minus(1))

    assert bf.panel_status(paths, output_prefix="daily_features")["current"] is True


def test_weekend_and_holiday_gap_is_still_current(paths):
    """허용 지연 경계(4일)에 정확히 걸친 패널은 최신이어야 한다 — 오탐 방지.

    동기가 된 실제 상황: 금요일 패널 · 월요일 연휴 · 화요일 조회 = 4일.
    판정은 달력일 산술(`age <= limit`)이라 오늘이 무슨 요일이든 같아야 한다.
    """
    _write_latest_panel(paths, "20260816_010101", _today_minus(4))

    assert bf.panel_status(paths, output_prefix="daily_features")["current"] is True


def test_multi_week_freeze_is_not_current(paths):
    """실제 사고(48일 동결)는 반드시 잡아야 한다."""
    _write_latest_panel(paths, "20260629_113805", _today_minus(48))

    assert bf.panel_status(paths, output_prefix="daily_features")["current"] is False


def test_missing_panel_is_not_current(paths):
    status = bf.panel_status(paths, output_prefix="daily_features")

    assert status["current"] is False
    assert status["panel_max_date"] is None


def test_daily_refresh_short_circuits_when_current(paths, monkeypatch):
    """하루 3회 실행 중 2회는 즉시 반환해야 한다 — 이게 3배 비용을 막는 장치다."""
    _write_latest_panel(paths, "20260816_010101", _today_minus(1))
    called = []
    monkeypatch.setattr(bf, "fetch_raw_ohlcv", lambda *a, **k: called.append("fetch") or (0, 0, []))

    result = bf.daily_refresh(paths, output_prefix="daily_features", force=False)

    assert result["status"] == "already_current"
    assert called == [], "이미 최신인데 fetch 를 돌렸다"


def test_daily_refresh_can_be_forced(paths, monkeypatch):
    _write_latest_panel(paths, "20260816_010101", _today_minus(1))
    monkeypatch.setattr(bf, "_run_refresh", lambda *a, **k: {"status": "refreshed"})

    assert bf.daily_refresh(paths, output_prefix="daily_features", force=True)["status"] == "refreshed"


def test_daily_refresh_runs_when_stale(paths, monkeypatch):
    _write_latest_panel(paths, "20260629_113805", _today_minus(48))
    monkeypatch.setattr(bf, "_run_refresh", lambda *a, **k: {"status": "refreshed"})

    assert bf.daily_refresh(paths, output_prefix="daily_features", force=False)["status"] == "refreshed"


# --------------------------------------------------------------------------
# 소비자와 같은 파일을 봐야 한다 (anglerfish 실측 (3))
#
# report_nasdaq_daily_edge_shadow.py:388-403 의 resolve_panel_path 는
# glob 결과에서 이름에 '_latest_' 가 든 파일을 **명시적으로 제외**한다.
# 따라서 신선도 판정도 소비자가 실제로 읽는 파일(스탬프 전량 패널)로 해야 한다.
# `_latest_` 를 보고 판정하면 goblin §3 의 함정(리포트를 보고 원장을 놓친 것)과 같은 실패다.
# --------------------------------------------------------------------------

def _write_stamped_panel(paths, stamp, max_date):
    paths.market_root.mkdir(parents=True, exist_ok=True)
    _panel_frame(max_date).to_parquet(
        paths.market_root / f"daily_features_20180101_20260630_{stamp}.parquet", index=False)


def test_panel_status_uses_the_file_the_consumer_reads(paths):
    """`_latest_` 가 신선해도 소비자가 읽는 스탬프 패널이 낡았으면 낡은 것이다."""
    _write_stamped_panel(paths, "20260629_113805", "2026-06-26")     # 소비자가 보는 것 — 낡음
    _write_latest_only(paths, "20260816_010101", _today_minus(1))    # 소비자가 무시하는 것 — 신선

    status = bf.panel_status(paths, output_prefix="daily_features")

    assert status["panel_max_date"] == "2026-06-26"
    assert status["current"] is False
    assert "_latest_" not in (status["latest_panel"] or "")


def test_panel_status_ignores_latest_only_directory(paths):
    """`_latest_` 만 있고 스탬프 패널이 없으면 소비자는 볼 게 없다 → 최신 아님."""
    _write_latest_only(paths, "20260816_010101", _today_minus(1))

    assert bf.panel_status(paths, output_prefix="daily_features")["current"] is False


def test_produced_panel_name_is_visible_to_the_consumer(paths, monkeypatch):
    """산출물 이름에 '_latest_' 가 들어가면 소비자가 영원히 못 본다 —
    '스텝은 도는데 원장은 0행'이 되고, 방금 고친 P0 와 같은 형태의 실패다."""
    import re
    _write_stamped_panel(paths, "20260816_010101", _today_minus(1))

    consumer_visible = [
        p for p in paths.market_root.glob("daily_features_*.parquet")
        if "_latest_" not in p.name and p.is_file()
    ]

    assert consumer_visible, "소비자 glob 조건에 걸리는 산출물이 없다"
    assert re.match(r"daily_features_\d{8}_\d{8}_\d{8}_\d{6}\.parquet$", consumer_visible[0].name)
