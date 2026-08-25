"""종목이 패널에서 조용히 사라지는 것을 보이게 만든다.

[W10] 실측: 758종목 KOSPI 유니버스에서 **한 종목**(042700)만 빠져도 세션당 EV 가
0.2440 → 0.1762 로 움직인다. **−0.068 은 6시드 전체 폭(0.0686)과 거의 같다.**
[W7] 은 파이프라인이 실제로 종목을 조용히 빠뜨리는 것을 관측했다(로그상 2659↔2660).
그동안 아무것도 이걸 보지 않았다.
"""
import pandas as pd

from multi_agent.tools import report_kr_swing_candidate as R


def _panel(counts_by_date, market="KOSPI"):
    rows = []
    for d, n in counts_by_date.items():
        for i in range(n):
            rows.append({"date": pd.Timestamp(d), "code": f"{i:06d}", "market": market})
    return pd.DataFrame(rows)


def _dates(n):
    return pd.bdate_range(end="2026-08-25", periods=n)


class TestUniverseIntegrity:
    def test_a_steady_panel_is_not_flagged(self):
        px = _panel({d: 900 for d in _dates(30)})
        rec = R._universe_integrity(px, pd.Timestamp("2026-08-25"))["KOSPI"]
        assert rec["anomalous"] is False and rec["shortfall"] == 0

    def test_normal_churn_within_precedent_is_not_flagged(self):
        """전례 있는 폭의 변동은 오탐이면 안 된다 — 오탐은 레인을 죽인다."""
        ds = list(_dates(30))
        counts = {d: 900 for d in ds}
        counts[ds[5]] = 896            # 전례: 4종목 빠진 적 있다
        counts[ds[-1]] = 897           # 오늘: 3종목. 전례 안이다
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is False

    def test_a_drop_beyond_all_precedent_is_flagged(self):
        ds = list(_dates(30))
        counts = {d: 900 for d in ds}
        counts[ds[5]] = 896
        counts[ds[-1]] = 880           # 20종목 — 전례(4)를 크게 넘는다
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is True
        assert rec["shortfall"] == 20 and rec["worst_before"] == 4

    def test_the_single_missing_ticker_case_is_visible(self):
        """[W10] 이 실제로 잰 상황 — 한 종목이 빠지면 기록에 남아야 한다."""
        ds = list(_dates(30))
        counts = {d: 758 for d in ds}
        counts[ds[-1]] = 757
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["shortfall"] == 1
        assert rec["anomalous"] is True, "전례가 0 이면 1종목 결손도 전례 밖이다"

    def test_markets_are_judged_separately(self):
        ds = list(_dates(30))
        a = _panel({d: 900 for d in ds}, "KOSPI")
        b = _panel({d: (1700 if d != ds[-1] else 1600) for d in ds}, "KOSDAQ")
        out = R._universe_integrity(pd.concat([a, b], ignore_index=True), ds[-1])
        assert out["KOSPI"]["anomalous"] is False
        assert out["KOSDAQ"]["anomalous"] is True

    def test_too_little_history_is_skipped_rather_than_guessed(self):
        px = _panel({d: 900 for d in _dates(5)})
        assert R._universe_integrity(px, pd.Timestamp("2026-08-25")) == {}

    def test_it_never_stops_publishing(self):
        """정상 사건(대량 상폐·휴장)도 같은 모양이라 막으면 오탐으로 레인이 죽는다."""
        ds = list(_dates(30))
        counts = {d: 900 for d in ds}
        counts[ds[-1]] = 100
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is True          # 기록은 하되
        # 예외를 던지지 않는다 — 여기까지 왔다는 것이 그 증거다
