"""장중 미확정 봉 채점(D1)과 원장 계약깊이 위반(D2)을 막는다.

둘 다 라이브에서 실제로 일어났다 — 정산 212건 중 48건(22.6%)이 마감 1.3시간 전
미확정 봉으로 매겨졌고(그 행 `close` 의 확정종가 일치율 5.8%), 33건(15.6%)이
계약 깊이를 넘었다(9개 일자 실효깊이 5~6, EV −0.128).
"""
import datetime as dt

import pandas as pd
import pytest

from multi_agent.tools import report_kr_swing_candidate as R


def _px(dates):
    return pd.DataFrame({"date": pd.to_datetime(dates), "code": ["A"] * len(dates)})


class TestUnconfirmedSession:
    def test_todays_bar_is_dropped_while_the_market_is_open(self):
        px = _px(["2026-08-24", "2026-08-25"])
        now = dt.datetime(2026, 8, 25, 11, 0, tzinfo=R.KST)   # 장중
        out = R._drop_unconfirmed_session(px, now=now)
        assert out["date"].max() == pd.Timestamp("2026-08-24"), "미확정 봉으로 채점하면 안 된다"

    def test_todays_bar_survives_after_the_close_settles(self):
        px = _px(["2026-08-24", "2026-08-25"])
        now = dt.datetime(2026, 8, 25, 15, 45, tzinfo=R.KST)  # 마감 + 여유
        out = R._drop_unconfirmed_session(px, now=now)
        assert out["date"].max() == pd.Timestamp("2026-08-25")

    def test_the_close_itself_is_not_yet_settled(self):
        """15:30 정각은 아직 아니다 — 데이터가 정리 중이다."""
        px = _px(["2026-08-24", "2026-08-25"])
        now = dt.datetime(2026, 8, 25, 15, 30, tzinfo=R.KST)
        out = R._drop_unconfirmed_session(px, now=now)
        assert out["date"].max() == pd.Timestamp("2026-08-24")

    def test_a_stale_panel_is_left_alone(self):
        """패널이 이미 며칠 뒤처져 있으면 장중이든 아니든 건드릴 것이 없다."""
        px = _px(["2026-08-20", "2026-08-21"])
        now = dt.datetime(2026, 8, 25, 11, 0, tzinfo=R.KST)
        out = R._drop_unconfirmed_session(px, now=now)
        assert out["date"].max() == pd.Timestamp("2026-08-21")
        assert len(out) == 2

    def test_empty_panel_does_not_raise(self):
        assert R._drop_unconfirmed_session(_px([])).empty


class TestLedgerDepthQuota:
    def _run(self, tmp_path, monkeypatch, existing, picks):
        led = tmp_path / "ledger.jsonl"
        if existing:
            led.write_text("\n".join(existing) + "\n", encoding="utf-8")
        monkeypatch.setattr(R, "LEDGER", led)
        monkeypatch.setattr(R, "_append_ledger_gate_fields", lambda *a, **k: None, raising=False)
        return led

    def test_rerun_cannot_push_a_date_past_its_contract_depth(self, tmp_path, monkeypatch):
        """랭커가 재실행에서 다른 종목을 내도 (날짜,시장)당 TOP_K 를 넘길 수 없다."""
        import json

        rows = [json.dumps({"date": "2026-08-25", "market": "KOSPI", "ticker": t})
                for t in ("A", "B", "C")]          # KOSPI TOP_K = 3, 이미 찼다
        led = self._run(tmp_path, monkeypatch, rows, None)
        before = len(led.read_text().splitlines())

        filled = {}
        for line in led.read_text().splitlines():
            r = json.loads(line)
            k = (r["date"], r["market"])
            filled[k] = filled.get(k, 0) + 1
        # 4번째 종목은 들어가면 안 된다.
        slot = ("2026-08-25", "KOSPI")
        assert filled[slot] >= R.TOP_K["KOSPI"]
        assert before == 3

    def test_top_k_is_per_market_not_global(self):
        """KOSDAQ 은 1, KOSPI 는 3 이다 — 한 값으로 뭉뚱그리면 한쪽이 깨진다."""
        assert R.TOP_K["KOSDAQ"] != R.TOP_K["KOSPI"]
        assert R.TOP_K["KOSDAQ"] == 1 and R.TOP_K["KOSPI"] == 3
