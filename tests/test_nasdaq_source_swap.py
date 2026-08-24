"""나스닥 원천 교체 — 오라클 유니버스 제거 (2026-08-24, 사양 research/X/SOURCE_SWAP_SPEC.md).

현행 라이브는 `glob(hourly/*.parquet)` 로 유니버스를 잡았는데, 그 디렉터리는 **2025-08 유동성으로
한 번 뽑힌 351종목 고정 목록**이었다(내용은 매일 갱신, 구성은 불변). 그 목록으로 과거를 백테스트한 것이
오라클이고, 같은 유니버스·같은 편입규칙에서 계약만 바꿔 재면 현행 계약은 승률 관문(70%)을
**69.3%** 로 미달한다. 겉보기 우위 +0.3496 이 오라클의 몫이었다.

순수 테스트다 — 패널·T1·네트워크에 의존하지 않는다.
"""
import re

import numpy as np
import pandas as pd
import pytest

import importlib.util as _u
import pathlib as _p

_spec = _u.spec_from_file_location("nst", _p.Path("multi_agent/tools/report_nasdaq_session_tape.py"))
nst = _u.module_from_spec(_spec)
_spec.loader.exec_module(nst)


def test_universe_is_not_a_directory_glob_anymore():
    """🔴 급소. `glob(hourly/*.parquet)` 이 되살아나면 오라클이 그대로 돌아온다."""
    src = _p.Path("multi_agent/tools/report_nasdaq_session_tape.py").read_text(encoding="utf-8")
    assert "HOURD" not in src, "시간봉 디렉터리 glob 이 유니버스를 정하면 안 된다"
    assert "PANELD" in src and "_latest_panel" in src


def test_panel_pick_excludes_the_latest_alias():
    """소비자가 `_latest_` 파일을 명시적으로 제외한다. 판정도 같은 규칙이어야 한다(seaslug f2639e0)."""
    import inspect
    src = inspect.getsource(nst._latest_panel)
    assert '"_latest_" not in p' in src


def test_negative_list_catches_units_and_warrants_case_insensitively():
    """🔴 `"Common Stock"` 정확일치로 거르면 소문자 `"Common stock"` 종목이 통째로 빠진다.
    부정목록 방식이 정본이고, 대소문자를 무시해야 한다."""
    ex = nst.T1_EXCLUDE
    for name in ("ACME Corp - Warrant", "ACME Warrants", "ACME Units", "ACME - Unit",
                 "ACME 7% Preferred Series A", "ACME Notes due 2031", "ACME Subordinated Debenture"):
        assert ex.search(name), f"부정목록이 놓쳤다: {name}"
    for name in ("Apple Inc. - Common Stock", "Upstart Holdings, Inc. - Common stock",
                 "Toyota Motor Corp - American Depositary Shares", "ACME plc Ordinary Shares"):
        assert not ex.search(name), f"부정목록이 과하게 걸었다: {name}"


def test_price_floor_and_liquidity_are_pinned():
    """`close>=$5` 는 현행 라이브에 **없었다**([M] §6). 라이브 48픽 중 7건 위반, 최저 $3.38.
    궤도기권 정본이 이 전제로 측정됐는데 라이브가 안 지키고 있었다."""
    assert nst.MIN_CLOSE == 5.0
    assert nst.MIN_LIQ20 == 1e8


def test_admission_is_a_quantile_not_an_absolute_cut():
    """규율 3 — 절대임계 금지. 보드가 「절대임계 금지」 사례를 다섯 번 쌓았다."""
    assert nst.ADMIT_Q == 0.10
    src = _p.Path("multi_agent/tools/report_nasdaq_session_tape.py").read_text(encoding="utf-8")
    assert 'rank(pct=True' in src, "편입은 그날 횡단면 분위여야 한다"
    assert "univ_frac250" in src


def test_residency_is_causal_and_has_a_warmup():
    """`shift(1)` 이 빠지면 자기참조가 된다. `min_periods` 가 빠지면 이력 없는 종목이 편입된다."""
    import inspect
    src = inspect.getsource(nst._admit)
    assert ".shift(1)" in src, "당일을 제외하지 않으면 자기참조다"
    assert "min_periods=UNIV_MINP" in src
    assert (nst.UNIV_W, nst.UNIV_MINP) == (250, 60)


def test_listed_pit_restores_row_order():
    """🔴 `merge_asof` 는 왼쪽을 `on` 키로 정렬해야 하는데, 정렬 결과를 그대로 돌려주면
    호출부와 행 순서가 어긋나 **엉뚱한 종목에 판정이 붙는다.** 첫 이식에서 이 버그로 AAPL 이
    탈락했다(검증벡터 2/10). 순서 복원이 있는지 못박는다."""
    import inspect
    src = inspect.getsource(nst._listed_pit)
    assert '_ix' in src and "restored" in src, "정렬 복원 없이 merge_asof 결과를 쓰면 안 된다"


def test_contract_horizon_is_twenty_sessions():
    assert nst.CONTRACT_H == 20


def test_pending_picks_keep_their_issued_contract():
    """계약을 H5 → H20 으로 바꿔도 **미정산 과거 픽은 발행 당시 계약으로** 채점해야 한다.
    아니면 그 픽이 약속하지 않은 창으로 재는 것이고 전진 기록이 소급 변조된다.
    `contract_h` 가 없는 행 = 2026-08-24 이전 발행 = H5."""
    src = _p.Path("multi_agent/tools/report_nasdaq_session_tape.py").read_text(encoding="utf-8")
    assert '_H = int(row.get("contract_h") or 5)' in src
    assert "win5 = h.iloc[:_H]" in src and "for k in range(_H):" in src


def test_gap_bonus_still_applies_on_day_one():
    """이 레인은 **종가 진입**이라 창 1일차 시가 갭업이 실현 이익이다(`7024b7e`).
    KR 익일시가용 `k > 0` 가드가 다시 들어오면 안 된다."""
    src = _p.Path("multi_agent/tools/report_nasdaq_session_tape.py").read_text(encoding="utf-8")
    assert "if (k > 0 and np.isfinite(o) and o > 0)" not in src
