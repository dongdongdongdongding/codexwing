"""종목이 패널에서 조용히 사라지는 것을 보이게 만든다.

[W10] 실측: 758종목 KOSPI 유니버스에서 **한 종목**(042700)만 빠져도 8년 세션당 EV 가
0.2440 → 0.1762 로 움직인다. **−0.068 은 6시드 전체 폭(0.0686)과 거의 같다.**
[W7] 은 파이프라인이 실제로 종목을 조용히 빠뜨리는 것을 관측했다(로그상 2659↔2660).

첫 판은 긴 창의 중앙값에 견줬고 **실물에서 오탐이 났다** — 아래 회귀 테스트가 그 상황이다.
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
    return list(pd.bdate_range(end="2026-08-25", periods=n))


class TestNoFalseAlarms:
    def test_a_steady_panel_is_not_flagged(self):
        ds = _dates(30)
        rec = R._universe_integrity(_panel({d: 900 for d in ds}), ds[-1])["KOSPI"]
        assert rec["anomalous"] is False and rec["shortfall"] == 0

    def test_a_settled_level_shift_is_not_flagged(self):
        """🔴 실물에서 나온 오탐 — KOSPI 가 최근 5일 915·915·915·915·914 로 **안정적인데**
        60일 중앙값이 931 이라 「17종목 결손」으로 읽혔다. 몇 주 전 정상 감소를
        오늘의 사고로 오독하면 **매일 경고가 떠서 아무도 안 읽는다.**"""
        ds = _dates(40)
        counts = {d: (931 if i < 20 else 915) for i, d in enumerate(ds)}
        counts[ds[-1]] = 914                      # 오늘 −1: 정상 범위
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is False, "정착된 수준 이동을 오늘의 결손으로 읽으면 안 된다"
        assert rec["recent_level"] == 915          # 60일 중앙(931)이 아니라 최근 수준

    def test_a_slow_decline_is_not_flagged(self):
        """상폐로 매일 한둘씩 주는 것은 사고가 아니다."""
        ds = _dates(40)
        rec = R._universe_integrity(_panel({d: 940 - i for i, d in enumerate(ds)}), ds[-1])["KOSPI"]
        assert rec["anomalous"] is False


class TestItCatchesRealDropout:
    def test_a_sudden_drop_beyond_precedent_is_flagged(self):
        ds = _dates(40)
        counts = {d: 900 for d in ds}
        counts[ds[10]] = 896                       # 전례: 한 번 4종목 급락
        counts[ds[-1]] = 880                       # 오늘 20종목 — 전례 밖
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is True and rec["shortfall"] == 20

    def test_the_single_missing_ticker_case_is_visible(self):
        """[W10] 이 실제로 잰 상황 — 완벽히 안정적인 패널에서 한 종목이 빠지면 전례 밖이다."""
        ds = _dates(40)
        counts = {d: 758 for d in ds}
        counts[ds[-1]] = 757
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["shortfall"] == 1 and rec["anomalous"] is True

    def test_markets_are_judged_separately(self):
        ds = _dates(40)
        a = _panel({d: 900 for d in ds}, "KOSPI")
        b = _panel({d: (1700 if d != ds[-1] else 1600) for d in ds}, "KOSDAQ")
        out = R._universe_integrity(pd.concat([a, b], ignore_index=True), ds[-1])
        assert out["KOSPI"]["anomalous"] is False
        assert out["KOSDAQ"]["anomalous"] is True


class TestSafety:
    def test_too_little_history_is_skipped_rather_than_guessed(self):
        ds = _dates(8)
        assert R._universe_integrity(_panel({d: 900 for d in ds}), ds[-1]) == {}

    def test_it_never_stops_publishing(self):
        """대량 상폐도 사고와 같은 모양이라, 막으면 오탐으로 레인이 죽는다."""
        ds = _dates(40)
        counts = {d: 900 for d in ds}
        counts[ds[-1]] = 100
        rec = R._universe_integrity(_panel(counts), ds[-1])["KOSPI"]
        assert rec["anomalous"] is True            # 기록은 한다
        # 예외를 안 던진다 — 여기까지 온 것이 그 증거다
