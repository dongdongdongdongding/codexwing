"""만료 5일이 지난 픽을 화면에서 내린다 (운영자 결정 2026-08-31).

`expired` 마킹은 이미 있었지만 **표시만 하고 계속 보여줬다.** 하루이틀 지난 픽은
「왜 못 사는지」가 정보지만, 닷새 넘게 지난 픽은 정보가 아니라 잡동사니다.

⚠️ `overview` 주석이 「빼면 왜 없는지 알 수 없다」고 적어 둔 원칙을 지키려면
숨긴 개수가 보여야 한다 — 조용히 사라지면 안 된다.
"""
from web.backend import services as S


def _row(stale=None, prob=0.8):
    r = {"prob": prob, "signal_class": "A", "ticker": "T", "market": "KOSPI"}
    if stale is not None:
        r["stale_days"] = stale
        r["expired"] = True
    return r


class TestThreshold:
    def test_fresh_and_briefly_expired_picks_survive(self):
        rows = [_row(), _row(1), _row(5)]
        kept, hidden = S._drop_long_expired(rows)
        assert len(kept) == 3 and hidden == 0, "5일까지는 남는다 — 경계 포함"

    def test_past_five_days_is_dropped(self):
        kept, hidden = S._drop_long_expired([_row(6), _row(30)])
        assert kept == [] and hidden == 2

    def test_threshold_is_five(self):
        assert S.EXPIRED_HIDE_DAYS == 5

    def test_missing_stale_days_counts_as_fresh(self):
        """`stale_days` 가 없는 픽(만료 아님)을 실수로 지우면 안 된다."""
        kept, hidden = S._drop_long_expired([{"prob": 0.5}])
        assert len(kept) == 1 and hidden == 0


class TestHonesty:
    def test_overview_reports_how_many_it_hid(self):
        import inspect

        src = inspect.getsource(S.overview)
        assert "hidden_expired" in src, "숨긴 개수를 안 세면 화면이 누락으로 거짓말한다"

    def test_every_picks_path_applies_the_filter(self):
        import inspect

        src = inspect.getsource(S.picks)
        assert src.count("_drop_long_expired") >= 3, "레인별·B·전체 세 경로 모두"
