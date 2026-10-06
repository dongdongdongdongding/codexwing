"""나스닥 세션테이프 레인의 전진 수치가 **어느 구성을 채점했는지** 드러내게 한다.

실측(2026-08-28): 정산 56건 중 **55건이 편입컷 도입 이전** 픽인데 `ev_net_avg` −0.28 이
A1 셀의 성적처럼 읽혔다. KR 스윙 레인에서 같은 결함을 이미 고쳤다(`c8bb51b`).

표지는 `xq` — 편입자격 컷이 **발행 시점에** 쓰는 필드다. `contract_h` 는 표지가 아니다:
정산 시점에도 찍혀 전환 이전 픽에 붙는다.
"""
import inspect

from multi_agent.tools import report_nasdaq_session_tape as N

SRC = inspect.getsource(N)


def test_epoch_marker_is_the_admission_field_not_contract_h():
    body = SRC[SRC.index("def resolve_pending"):]
    assert 'r.get("xq") is not None' in body
    assert 'r.get("contract_h") is not None' not in body, "contract_h 는 정산 시점에도 찍힌다"


def test_summary_carries_both_epochs():
    body = SRC[SRC.index("def resolve_pending"):]
    assert '"epoch"' in body and '"current"' in body and '"previous"' in body


def test_a_thin_current_epoch_says_it_is_not_a_verdict_sample():
    body = SRC[SRC.index("def resolve_pending"):]
    assert "len(cur) < 30" in body, "레인 자체 승격 기준(n>=30)과 같은 문턱이어야 한다"
    assert "판정 표본이 아니다" in body


def test_the_lane_states_its_own_promotion_rule():
    """승격 기준이 코드에 남아 있어야 한다 — 이 경계의 문턱 근거다."""
    assert "no capital before forward n>=30" in SRC


def test_report_separates_training_score_contract_and_user_objective():
    metadata = N.report_evidence()
    assert metadata['contract_info']['horizon_sessions'] == 20
    assert metadata['contract_info']['tp'] == .05
    assert metadata['contract_info']['entry_reference'] == 'signal_session_close'
    assert metadata['score_semantics']['model_label'] == 't15_20'
    assert metadata['score_semantics']['calibrated_contract_probability'] is False
    assert metadata['evidence_scope']['h10_tp5_probability_verified'] is False
    assert metadata['evidence_scope']['legacy_hourly_study_applicable'] is False
    assert metadata['evidence_scope']['weekly_2_to_3_cadence_verified'] is False
    assert '79.3%' not in metadata['expectation']


def test_rendered_perfect_thin_epoch_is_not_presented_as_certified_probability():
    import copy
    report = {'as_of': '2026-10-06', 'generated_at': 'original',
              'metadata_updated_at': 'correction', 'status': 'no_candidates', 'picks': [],
              'forward_summary': {'resolved': 64, 'epoch': {
                  'current': {'resolved': 3, 'touch5_pct': 100},
                  'previous': {'resolved': 61}, 'current_picks': 7}},
              **N.report_evidence()}
    before = copy.deepcopy(report)
    text = N.render_report(report)
    assert report == before
    assert 'no certified H10 touch probability' in text
    assert 'TP +5% / 20 sessions' in text
    assert 'Current composition:' in text and "'resolved': 3" in text
    assert 'Previous composition:' in text and "'resolved': 61" in text
    assert 't15_20 model score' in text
    assert 'No new scan or settlement.' in text
    assert 'original run: original' in text
