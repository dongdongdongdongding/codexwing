"""학습 라벨이 조용히 낡는 것을 막는다.

2026-08-26 발견: `px_long`(피처)은 일일 운영이 매일 재구축하는데
`marcap → px_delisted → p2_label` 사슬은 **일일 운영 어디에도 없다.**
랭커는 그날 피처로 채점하면서 2026-07-24 에 멈춘 라벨로 학습하고 있었고,
그 격차가 매일 하루씩 벌어지는데 **아무것도 그걸 보지 않았다.**
"""
import datetime as dt

import pandas as pd
import pytest

from multi_agent.tools import report_kr_swing_candidate as R


def _stale(label_max: str, as_of: str) -> int:
    return R._label_staleness(pd.Timestamp(label_max), pd.Timestamp(as_of))


class TestStalenessArithmetic:
    def test_a_label_that_only_lags_by_the_embargo_is_healthy(self):
        """라벨은 계약이 끝나야 확정되므로 엠바고만큼 뒤처지는 것이 정상이다."""
        as_of = dt.date(2026, 8, 25)
        healthy = as_of - dt.timedelta(days=R.EMBARGO_DAYS)
        assert _stale(str(healthy), str(as_of)) == 0

    def test_a_label_fresher_than_the_embargo_is_also_healthy(self):
        assert _stale("2026-08-20", "2026-08-25") == 0

    def test_lag_beyond_the_embargo_is_counted(self):
        as_of = dt.date(2026, 8, 25)
        allowed = as_of - dt.timedelta(days=R.EMBARGO_DAYS)
        assert _stale(str(allowed - dt.timedelta(days=15)), str(as_of)) == 15

    def test_the_state_that_was_live_when_this_was_found(self):
        """실제로 걸려 있던 값 — 회귀하면 이 테스트가 잡는다."""
        assert _stale("2026-07-24", "2026-08-25") == 15


class TestHardStop:
    def test_the_hard_stop_is_one_refit_period(self):
        """분기를 넘으면 가장 최근 폴드가 새 데이터를 한 줄도 못 본다."""
        assert R.LABEL_STALENESS_HARD_DAYS == 63

    def test_the_state_found_live_warns_rather_than_killing_the_lane(self):
        """15일 지연은 경고 대상이지 중단 대상이 아니다 — 중단하면 레인이 죽는다."""
        assert _stale("2026-07-24", "2026-08-25") <= R.LABEL_STALENESS_HARD_DAYS

    def test_a_quarter_of_neglect_does_stop_it(self):
        as_of = dt.date(2026, 8, 25)
        allowed = as_of - dt.timedelta(days=R.EMBARGO_DAYS)
        dead = allowed - dt.timedelta(days=R.LABEL_STALENESS_HARD_DAYS + 1)
        assert _stale(str(dead), str(as_of)) > R.LABEL_STALENESS_HARD_DAYS
